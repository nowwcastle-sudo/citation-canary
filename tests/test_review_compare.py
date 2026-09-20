from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from citation_canary.comparison import compare_reports
from tests.test_review_ledger import report_fixture


class CompareTests(unittest.TestCase):
    def test_identical_report_has_no_changes_or_decision_transfer(self):
        report = report_fixture()
        result = compare_reports(report, report)
        self.assertEqual(result['changes'], [])
        self.assertEqual(result['unresolved'], [])
        self.assertTrue(result['comparable'])
        self.assertFalse(result['decision_transfer'])

    def test_catalog_and_date_are_separate_from_source_changes(self):
        before = report_fixture()
        after = copy.deepcopy(before)
        after['catalog_sha256'] = 'c' * 64
        after['as_of'] = '2025-01-01'
        result = compare_reports(before, after)
        self.assertEqual([change['type'] for change in result['changes']], ['catalog', 'as_of'])
        self.assertFalse(result['decision_transfer'])

    def test_known_metadata_survives_empty_or_error_report_without_resolution(self):
        before = report_fixture()
        for condition in ('populated', 'empty', 'collection_error'):
            with self.subTest(condition=condition):
                after = copy.deepcopy(before)
                after['catalog_sha256'] = 'c' * 64
                after['as_of'] = '2025-01-01'
                if condition != 'populated':
                    after['items'] = []
                if condition == 'collection_error':
                    after['collection_errors'] = [{'code': 'SYNTHETIC_ERROR', 'stage': 'parse',
                                                   'fatal': True, 'locator': None, 'message': 'synthetic'}]
                result = compare_reports(before, after)
                self.assertEqual([row['type'] for row in result['changes']], ['catalog', 'as_of'])
                self.assertEqual([(row['before'], row['after']) for row in result['changes']],
                                 [('b' * 64, 'c' * 64), ('2024-12-31', '2025-01-01')])
                self.assertEqual(result['comparable'], condition == 'populated')
                self.assertFalse(result['decision_transfer'])
                if condition != 'populated':
                    self.assertEqual(result['unresolved'][0]['reason'],
                                     'collection_errors' if condition == 'collection_error'
                                     else 'empty_report_not_completion')
                    self.assertFalse(any(row['type'] in ('removed', 'added', 'status', 'evidence')
                                         for row in result['changes']))

    def test_unrelated_document_does_not_compare_metadata_even_when_empty(self):
        before = report_fixture()
        after = copy.deepcopy(before)
        after['document_sha256'] = 'f' * 64
        after['items'] = []
        after['catalog_sha256'] = 'c' * 64
        after['as_of'] = '2025-01-01'
        self.assertEqual(compare_reports(before, after)['changes'], [])
        self.assertEqual([row['type'] for row in compare_reports(before, after, related_versions=True)['changes']],
                         ['catalog', 'as_of'])

    def test_add_remove_and_status_evidence_are_distinct(self):
        before = report_fixture()
        after = copy.deepcopy(before)
        after['items'][0]['status'] = 'CURRENT'
        after['items'][0]['reason_code'] = 'SYNTHETIC_CURRENT'
        after['items'][0]['evidence'] = [{
            'record_id': 'fictional', 'official_source': 'https://example.invalid/source',
            'retrieved_at': '2026-09-20T00:00:00Z', 'as_of': '2024-12-31',
            'matched_effective_from': '2024-01-01', 'matched_effective_to': None,
            'matched_title': '합성법 A', 'matched_provision': '제1조', 'version_transition': None,
        }]
        addition = copy.deepcopy(after['items'][1])
        addition['locator'] = 'section0.xml:p2'
        addition['reference']['title'] = '합성법 C'
        after['items'] = after['items'][:1] + [addition]
        types = [change['type'] for change in compare_reports(before, after)['changes']]
        self.assertEqual(types, ['status', 'evidence', 'removed', 'added'])

    def test_reorder_and_duplicates_remain_unresolved(self):
        before = report_fixture()
        after = copy.deepcopy(before)
        after['items'].reverse()
        result = compare_reports(before, after)
        self.assertEqual(result['changes'], [])
        self.assertTrue(result['unresolved'])
        self.assertFalse(result['decision_transfer'])
        duplicate = copy.deepcopy(before)
        duplicate['items'].append(copy.deepcopy(duplicate['items'][0]))
        result = compare_reports(before, duplicate)
        self.assertTrue(result['unresolved'])
        self.assertFalse(any(c['type'] == 'added' for c in result['changes']))

    def test_same_hash_exact_positions_allow_repeated_references(self):
        before = report_fixture()
        before['items'][1]['reference'] = copy.deepcopy(before['items'][0]['reference'])
        before['items'][1]['locator'] = 'section0.xml:p2'
        after = copy.deepcopy(before)
        after['items'][1]['status'] = 'CURRENT'
        after['items'][1]['evidence'] = [{
            'record_id': 'fictional', 'official_source': 'https://example.invalid/source',
            'retrieved_at': '2026-09-20T00:00:00Z', 'as_of': '2024-12-31',
            'matched_effective_from': '2024-01-01', 'matched_effective_to': None,
            'matched_title': '합성법 A', 'matched_provision': '제1조', 'version_transition': None,
        }]
        after['catalog_sha256'] = 'c' * 64
        result = compare_reports(before, after)
        self.assertEqual([row['type'] for row in result['changes']], ['status', 'evidence', 'catalog'])
        self.assertEqual(result['changes'][0]['before_item_number'], 2)
        self.assertEqual(result['changes'][0]['after_item_number'], 2)
        self.assertEqual(result['unresolved'], [])
        self.assertFalse(result['decision_transfer'])

    def test_same_locator_and_reference_keep_item_numbers_independent(self):
        before = report_fixture()
        before['items'][1] = copy.deepcopy(before['items'][0])
        after = copy.deepcopy(before)
        after['items'][1]['status'] = 'CURRENT'
        after['items'][1]['reason_code'] = 'SYNTHETIC_CURRENT'
        after['items'][1]['evidence'] = [{
            'record_id': 'fictional', 'official_source': 'https://example.invalid/source',
            'retrieved_at': '2026-09-20T00:00:00Z', 'as_of': '2024-12-31',
            'matched_effective_from': '2024-01-01', 'matched_effective_to': None,
            'matched_title': '합성법 A', 'matched_provision': '제1조', 'version_transition': None,
        }]
        after['catalog_sha256'] = 'c' * 64
        result = compare_reports(before, after)
        self.assertEqual([row['type'] for row in result['changes']], ['status', 'evidence', 'catalog'])
        self.assertEqual([(row['before_item_number'], row['after_item_number'])
                          for row in result['changes'][:2]], [(2, 2), (2, 2)])
        self.assertEqual(result['unresolved'], [])
        self.assertFalse(result['decision_transfer'])

    def test_related_version_duplicate_reference_does_not_pair_candidates(self):
        before = report_fixture()
        before['items'][1] = copy.deepcopy(before['items'][0])
        after = copy.deepcopy(before)
        after['document_sha256'] = 'f' * 64
        result = compare_reports(before, after, related_versions=True)
        self.assertTrue(result['comparable'])
        self.assertTrue(result['unresolved'])
        self.assertTrue(all(not (row['before_item_numbers'] and row['after_item_numbers'])
                            for row in result['unresolved']))
        self.assertFalse(result['decision_transfer'])

    def test_related_versions_are_candidates_only(self):
        before = report_fixture()
        after = copy.deepcopy(before)
        after['document_sha256'] = 'f' * 64
        self.assertFalse(compare_reports(before, after)['comparable'])
        result = compare_reports(before, after, related_versions=True)
        self.assertTrue(result['comparable'])
        self.assertTrue(result['unresolved'])
        self.assertFalse(result['decision_transfer'])
        after['items'][0]['locator'] = 'section0.xml:p3'
        self.assertTrue(compare_reports(before, after, related_versions=True)['unresolved'])

    def test_collection_error_forbids_resolution_and_no_socket(self):
        before = report_fixture()
        after = copy.deepcopy(before)
        after['items'] = []
        after['collection_errors'] = [{'code': 'SYNTHETIC_ERROR', 'stage': 'parse',
                                       'fatal': True, 'locator': None, 'message': 'synthetic'}]
        with patch('socket.socket', side_effect=AssertionError('network attempted')):
            result = compare_reports(before, after)
        self.assertFalse(result['comparable'])
        self.assertFalse(any(c['type'] == 'removed' for c in result['changes']))
        self.assertTrue(result['unresolved'])

    def test_empty_result_is_not_completion_or_mass_resolution(self):
        before = report_fixture()
        after = copy.deepcopy(before)
        after['items'] = []
        result = compare_reports(before, after)
        self.assertFalse(result['comparable'])
        self.assertEqual(result['changes'], [])
        self.assertEqual(result['unresolved'][0]['reason'], 'empty_report_not_completion')


if __name__ == '__main__':
    unittest.main()
