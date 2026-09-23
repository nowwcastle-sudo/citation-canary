from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from citation_canary.__main__ import main
from citation_canary.review_io import canonical_digest
from tests.test_review_ledger import report_fixture


class ReviewCliTests(unittest.TestCase):
    def test_review_help_process_succeeds_and_duplicate_guards_remain(self):
        environment = os.environ.copy()
        source = str(Path(__file__).resolve().parents[1] / 'src')
        environment['PYTHONPATH'] = source + os.pathsep + environment.get('PYTHONPATH', '')
        completed = subprocess.run([sys.executable, '-m', 'citation_canary', 'review', '--help'],
                                   capture_output=True, text=True, env=environment)
        self.assertEqual(completed.returncode, 0)
        self.assertIn('--action', completed.stdout)
        self.assertIn('--report', completed.stdout)
        self.assertEqual(completed.stderr, '')
        duplicate = subprocess.run([sys.executable, '-m', 'citation_canary', 'review',
                                    '--report', 'missing', '--report', 'missing', '--ledger', 'missing',
                                    '--action', 'decide', '--item', '1', '--disposition', 'confirm'],
                                   capture_output=True, text=True, env=environment)
        self.assertEqual(duplicate.returncode, 2)
        self.assertEqual(duplicate.stderr, 'ARGUMENT_ERROR\n')

    def test_compare_and_render_do_not_change_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before, after, output = root / 'before.json', root / 'after.json', root / 'review.html'
            raw = json.dumps(report_fixture(), ensure_ascii=False).encode('utf-8')
            before.write_bytes(raw)
            after.write_bytes(raw)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                self.assertEqual(main(['compare', '--before', str(before), '--after', str(after)]), 0)
            self.assertFalse(json.loads(stream.getvalue())['decision_transfer'])
            self.assertEqual(main(['render', '--report', str(before), '--output', str(output)]), 0)
            self.assertIn(b'<!doctype html>', output.read_bytes())
            self.assertEqual((before.read_bytes(), after.read_bytes()), (raw, raw))
            self.assertFalse(list(root.glob('*.lock')))

    def test_render_rejects_existing_and_input_alias_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, output = root / 'report.json', root / 'review.html'
            original = json.dumps(report_fixture(), ensure_ascii=False).encode('utf-8')
            report.write_bytes(original)
            output.write_bytes(b'old output')
            for destination in (report, output):
                with self.subTest(destination=destination):
                    self.assertEqual(main(['render', '--report', str(report), '--output', str(destination)]), 2)
            self.assertEqual(report.read_bytes(), original)
            self.assertEqual(output.read_bytes(), b'old output')

    def test_invalid_ledger_and_duplicate_flags_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, ledger, output = root / 'report.json', root / 'ledger.json', root / 'review.html'
            report.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            ledger.write_text('{"schema":"wrong"}', encoding='utf-8')
            self.assertEqual(main(['render', '--report', str(report), '--ledger', str(ledger),
                                   '--output', str(output)]), 2)
            self.assertFalse(output.exists())
            self.assertEqual(main(['compare', '--before', str(report), '--before', str(report),
                                   '--after', str(report)]), 2)

    def test_render_rejects_hardlink_and_reparse_parent_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, alias = root / 'report.json', root / 'alias.json'
            report.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            original = report.read_bytes()
            os.link(report, alias)
            self.assertEqual(main(['render', '--report', str(report), '--output', str(alias)]), 2)
            self.assertEqual(report.read_bytes(), original)
            link = root / 'linked-parent'
            try:
                link.symlink_to(root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlink creation unavailable')
            self.assertEqual(main(['render', '--report', str(report),
                                   '--output', str(link / 'new.html')]), 2)
            self.assertFalse((root / 'new.html').exists())

    def test_compare_render_do_not_open_network_sockets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, output = root / 'report.json', root / 'review.html'
            report.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            with patch('socket.socket', side_effect=AssertionError('network attempted')):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(['compare', '--before', str(report), '--after', str(report)]), 0)
                self.assertEqual(main(['render', '--report', str(report), '--output', str(output)]), 0)

    def test_decide_creates_bound_ledger_without_report_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'report.json'
            ledger = Path(directory) / 'ledger.json'
            report.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            before = report.read_bytes()
            self.assertEqual(main(['review', '--report', str(report), '--ledger', str(ledger),
                                   '--action', 'decide', '--item', '1', '--disposition', 'confirm']), 0)
            self.assertEqual(report.read_bytes(), before)
            value = json.loads(ledger.read_text(encoding='utf-8'))
            self.assertEqual(value['report_digest'], canonical_digest(report_fixture()))
            self.assertEqual(value['events'][0]['item_number'], 1)

    def test_invalid_mixed_and_duplicate_arguments(self):
        for args in (['--action', 'decide', '--item', '1', '--disposition', 'confirm', '--stage', 'triage'],
                     ['--action', 'start', '--stage', 'triage', '--item', '1'],
                     ['--action', 'decide', '--item', '1', '--item', '2', '--disposition', 'confirm'],
                     ['--action=decide', '--item=1', '--item=2', '--disposition=confirm']):
            with self.subTest(args=args):
                self.assertEqual(main(['review', '--report', 'missing', '--ledger', 'missing2', *args]), 2)

    def test_fsync_failure_is_exit_one_with_fixed_code_and_retained_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, ledger = root / 'report.json', root / 'ledger.json'
            report.write_text(json.dumps(report_fixture(), ensure_ascii=False), encoding='utf-8')
            args = ['review', '--report', str(report), '--ledger', str(ledger),
                    '--action', 'decide', '--item', '1', '--disposition', 'confirm']
            self.assertEqual(main(args), 0)
            before = ledger.read_bytes()
            errors = io.StringIO()
            with patch('citation_canary.review.os.fsync', side_effect=OSError('injected')):
                with contextlib.redirect_stderr(errors):
                    code = main(args)
            self.assertEqual(code, 1)
            self.assertEqual(errors.getvalue(), 'REVIEW_WRITE_FAILED\n')
            self.assertEqual(ledger.read_bytes(), before)
            self.assertTrue(list(root.glob('.ledger.json.*.tmp')))


if __name__ == '__main__':
    unittest.main()
