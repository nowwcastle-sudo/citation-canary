from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from citation_canary.report import ScanRequestError
from citation_canary.review import append_event, new_ledger, review_summary, update_ledger, validate_ledger
from citation_canary.review_io import MAX_JSON_BYTES, canonical_digest, read_json


def report_fixture() -> dict[str, object]:
    return {'schema_version': '1', 'document_name': 'synthetic.hwpx',
            'document_sha256': 'a' * 64, 'catalog_sha256': 'b' * 64,
            'as_of': '2024-12-31',
            'items': [{'locator': 'section0.xml:p1',
                       'reference': {'title': title, 'provision': '제1조'},
                       'status': 'REVIEW', 'reason_code': 'SYNTHETIC_REVIEW',
                       'evidence': []} for title in ('합성법 A', '합성법 B')],
            'collection_errors': []}


class LedgerTests(unittest.TestCase):
    def test_same_locator_independent_history_and_unchanged_report(self):
        report = report_fixture()
        original = copy.deepcopy(report)
        ledger = new_ledger(report)
        ledger = append_event(ledger, report, action='decide', item_number=1,
                              disposition='confirm', stage=None, at='2026-09-20T00:00:00Z')
        self.assertEqual(ledger['events'][0]['item_number'], 1)
        self.assertEqual(report['items'][0]['status'], 'REVIEW')
        ledger = append_event(ledger, report, action='decide', item_number=1,
                              disposition='reject', stage=None, at='2026-09-20T00:01:00Z')
        ledger = append_event(ledger, report, action='decide', item_number=2,
                              disposition='defer', stage=None, at='2026-09-20T00:02:00Z')
        self.assertEqual(len(ledger['events']), 3)
        self.assertEqual(review_summary(ledger, report)['latest_decisions'], {'1': 'reject', '2': 'defer'})
        self.assertEqual(report, original)

    def test_binding_and_chain_corruption_rejected(self):
        report = report_fixture()
        ledger = append_event(new_ledger(report), report, action='decide',
                              item_number=1, disposition='confirm', stage=None,
                              at='2026-09-20T00:00:00Z')
        for field in ('report_digest', 'document_sha256', 'catalog_sha256', 'as_of'):
            broken = copy.deepcopy(ledger)
            broken[field] = 'x' * 64
            with self.subTest(field=field), self.assertRaises(ScanRequestError):
                validate_ledger(broken, report)
        for field, value in [('digest', 'x' * 64), ('previous_event_digest', 'x' * 64),
                             ('sequence', 2), ('item_number', True), ('at', '2026-09-20T00:00:00+01:00')]:
            broken = copy.deepcopy(ledger)
            broken['events'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ScanRequestError):
                validate_ledger(broken, report)

    def test_invalid_indexes_and_author_claim_rejected(self):
        report = report_fixture()
        for number in (True, False, 0, 3, -1):
            with self.subTest(number=number), self.assertRaises(ScanRequestError):
                append_event(new_ledger(report), report, action='decide', item_number=number,
                             disposition='confirm', stage=None, at='2026-09-20T00:00:00Z')
        forged = new_ledger(report)
        forged['author'] = 'claimed'
        with self.assertRaises(ScanRequestError):
            validate_ledger(forged, report)

    def test_timing_missing_reversed_overlap_and_valid(self):
        report = report_fixture()
        ledger = new_ledger(report)
        ledger = append_event(ledger, report, action='start', item_number=None,
                              disposition=None, stage='triage', at='2026-09-20T00:00:00Z')
        ledger = append_event(ledger, report, action='finish', item_number=None,
                              disposition=None, stage='triage', at='2026-09-20T00:00:10Z')
        self.assertEqual(review_summary(ledger, report)['timing']['triage'],
                         {'seconds': 10, 'status': 'measured'})
        ledger = append_event(ledger, report, action='finish', item_number=None,
                              disposition=None, stage='evidence', at='2026-09-20T00:00:20Z')
        self.assertEqual(review_summary(ledger, report)['timing']['evidence']['status'], 'unknown')
        ledger = append_event(ledger, report, action='start', item_number=None,
                              disposition=None, stage='decision', at='2026-09-20T00:00:30Z')
        ledger = append_event(ledger, report, action='start', item_number=None,
                              disposition=None, stage='decision', at='2026-09-20T00:00:31Z')
        ledger = append_event(ledger, report, action='finish', item_number=None,
                              disposition=None, stage='decision', at='2026-09-20T00:00:32Z')
        self.assertEqual(review_summary(ledger, report)['timing']['decision']['status'], 'unknown')

    def test_event_limit(self):
        report = report_fixture()
        ledger = new_ledger(report)
        events = ledger['events']
        previous = None
        for sequence in range(1, 50_001):
            event = {'sequence': sequence, 'action': 'decide', 'item_number': 1,
                     'disposition': 'confirm', 'stage': None, 'at': '2026-09-20T00:00:00Z',
                     'previous_event_digest': previous}
            previous = event['digest'] = canonical_digest(event)
            events.append(event)
        self.assertEqual(len(validate_ledger(ledger, report)['events']), 50_000)
        events.append({})
        with self.assertRaises(ScanRequestError):
            validate_ledger(ledger, report)

    def test_update_preserves_original_and_failed_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path, ledger_path = root / 'report.json', root / 'ledger.json'
            report_path.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            update_ledger(ledger_path, report_path, action='decide', item_number=1,
                          disposition='confirm', stage=None)
            original = ledger_path.read_bytes()
            for function in ('fsync', 'replace'):
                with self.subTest(function=function), patch('citation_canary.review.os.' + function,
                                                             side_effect=OSError('injected')):
                    with self.assertRaises(ScanRequestError):
                        update_ledger(ledger_path, report_path, action='decide', item_number=2,
                                      disposition='reject', stage=None)
                self.assertEqual(ledger_path.read_bytes(), original)
                self.assertTrue(list(root.glob('.ledger.json.*.tmp')))

    def test_output_node_budget_prevents_unreadable_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path, ledger_path = root / 'report.json', root / 'ledger.json'
            report = report_fixture()
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
            ledger = new_ledger(report)
            previous = None
            for sequence in range(1, 22_222):
                event = {'sequence': sequence, 'action': 'decide', 'item_number': 1,
                         'disposition': 'confirm', 'stage': None, 'at': '2026-09-20T00:00:00Z',
                         'previous_event_digest': previous}
                previous = event['digest'] = canonical_digest(event)
                ledger['events'].append(event)
            original = (json.dumps(ledger, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
            self.assertLess(len(original), MAX_JSON_BYTES)
            ledger_path.write_bytes(original)
            self.assertEqual(len(read_json(ledger_path)['events']), 22_221)
            with self.assertRaises(ScanRequestError):
                update_ledger(ledger_path, report_path, action='decide', item_number=1,
                              disposition='reject', stage=None)
            self.assertEqual(ledger_path.read_bytes(), original)
            self.assertEqual(len(read_json(ledger_path)['events']), 22_221)
            self.assertTrue(list(root.glob('.ledger.json.*.tmp')))

    def test_failed_new_promotion_temp_unlink_rolls_back_only_owned_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path, ledger_path = root / 'report.json', root / 'ledger.json'
            report_path.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            original_unlink = Path.unlink

            def fail_temp_unlink(candidate: Path, *args, **kwargs):
                if candidate.suffix == '.tmp':
                    raise PermissionError('injected')
                return original_unlink(candidate, *args, **kwargs)

            with patch('citation_canary.review.Path.unlink', autospec=True,
                       side_effect=fail_temp_unlink):
                with self.assertRaises(ScanRequestError) as caught:
                    update_ledger(ledger_path, report_path, action='decide', item_number=1,
                                  disposition='confirm', stage=None)
            self.assertEqual(caught.exception.code, 'REVIEW_WRITE_FAILED')
            self.assertFalse(ledger_path.exists())
            self.assertFalse((root / 'ledger.json.lock').exists())
            retained = list(root.glob('.ledger.json.*.tmp'))
            self.assertEqual(len(retained), 1)
            self.assertEqual(retained[0].stat().st_nlink, 1)
            self.assertEqual(len(read_json(retained[0])['events']), 1)

    def test_stale_lock_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path, ledger_path = root / 'report.json', root / 'ledger.json'
            report_path.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            lock = root / 'ledger.json.lock'
            lock.write_bytes(b'older-owner')
            with self.assertRaises(ScanRequestError) as caught:
                update_ledger(ledger_path, report_path, action='decide', item_number=1,
                              disposition='confirm', stage=None)
            self.assertEqual(caught.exception.code, 'REVIEW_BUSY')
            self.assertEqual(lock.read_bytes(), b'older-owner')

    def test_hardlink_ledger_rejected_without_changing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path, ledger_path, target = root / 'report.json', root / 'ledger.json', root / 'target.json'
            report_path.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            target.write_bytes(b'original')
            os.link(target, ledger_path)
            with self.assertRaises(ScanRequestError) as caught:
                update_ledger(ledger_path, report_path, action='decide', item_number=1,
                              disposition='confirm', stage=None)
            self.assertEqual(caught.exception.code, 'REVIEW_PATH_INVALID')
            self.assertEqual(target.read_bytes(), b'original')

    @unittest.skipUnless(os.name == 'nt', 'NTFS alternate streams are Windows-only')
    def test_alternate_stream_ledger_path_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path = root / 'report.json'
            report_path.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            with self.assertRaises(ScanRequestError) as caught:
                update_ledger(Path(str(root / 'ledger.json') + ':stream'), report_path,
                              action='decide', item_number=1, disposition='confirm', stage=None)
            self.assertEqual(caught.exception.code, 'REVIEW_PATH_INVALID')

    def test_two_independent_processes_append_without_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path, ledger_path = root / 'report.json', root / 'ledger.json'
            report_path.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            command = [sys.executable, '-m', 'citation_canary', 'review', '--report', str(report_path),
                       '--ledger', str(ledger_path), '--action', 'decide', '--item', '1',
                       '--disposition', 'confirm']
            environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
            processes = [subprocess.Popen(command, env=environment, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE) for _ in range(2)]
            outcomes = [process.communicate(timeout=10) for process in processes]
            exits = [process.returncode for process in processes]
            self.assertIn(sorted(exits), ([0, 2], [0, 0]), outcomes)
            self.assertEqual(len(json.loads(ledger_path.read_text(encoding='utf-8'))['events']), exits.count(0))

    def test_reversed_and_cross_stage_overlap_are_unknown(self):
        report = report_fixture()
        ledger = new_ledger(report)
        for action, stage, at in [('start', 'triage', '2026-09-20T00:00:10Z'),
                                  ('finish', 'triage', '2026-09-20T00:00:00Z'),
                                  ('start', 'evidence', '2026-09-20T00:01:00Z'),
                                  ('start', 'decision', '2026-09-20T00:01:01Z'),
                                  ('finish', 'decision', '2026-09-20T00:01:03Z'),
                                  ('finish', 'evidence', '2026-09-20T00:01:04Z')]:
            ledger = append_event(ledger, report, action=action, item_number=None,
                                  disposition=None, stage=stage, at=at)
        self.assertTrue(all(value['status'] == 'unknown' for value in
                            review_summary(ledger, report)['timing'].values()))


if __name__ == '__main__':
    unittest.main()
