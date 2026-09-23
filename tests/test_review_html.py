from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from citation_canary.review import append_event, new_ledger
from citation_canary.review_html import render_review
from citation_canary.report import ScanRequestError
from tests.test_review_ledger import report_fixture


class RenderTests(unittest.TestCase):
    def test_long_digest_and_escaped_dynamic_tokens_have_wrap_rule(self):
        report = report_fixture()
        report['items'][0]['reference']['title'] = '<' + 'A' * 600 + '>'
        html = render_review(report)
        self.assertIn('overflow-wrap:anywhere', html)
        self.assertIn('&lt;' + 'A' * 600 + '&gt;', html)
        self.assertIn('Report digest (SHA-256): <code>', html)
        self.assertNotIn('<' + 'A' * 600 + '>', html)

    def test_empty_report_is_unreviewed_not_complete(self):
        report = report_fixture()
        report['items'] = []
        html = render_review(report)
        self.assertNotIn('<script', html.lower())
        self.assertIn('unreviewed', html.lower())
        self.assertIn('No candidates is not completion', html)
        for status in ('REVIEW', 'UNKNOWN', 'HISTORY', 'CURRENT'):
            self.assertIn(status, html)

    def test_escaping_and_default_sensitive_fields_hidden(self):
        report = report_fixture()
        report['document_name'] = '<script>alert(1)</script>'
        report['items'][0]['locator'] = 'secret-file:p1'
        report['items'][0]['reference']['title'] = '<img src=x onerror=alert(1)>'
        with patch('socket.socket', side_effect=AssertionError('network attempted')):
            html = render_review(report)
        self.assertNotIn('<script', html.lower())
        self.assertNotIn('<img', html.lower())
        self.assertNotIn('secret-file:p1', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertIn('&lt;img', html)
        self.assertIn('item 1', html)

    def test_link_rejects_non_https_userinfo_control_and_quoted_attributes(self):
        report = report_fixture()
        evidence = {'record_id': 'fictional', 'official_source': 'https://example.invalid/a',
                    'retrieved_at': '2026-09-20T00:00:00Z', 'as_of': '2024-12-31',
                    'matched_effective_from': '2024-01-01', 'matched_effective_to': None,
                    'matched_title': 'Synthetic', 'matched_provision': 'article 1',
                    'version_transition': None}
        report['items'][0]['evidence'] = [copy.deepcopy(evidence) for _ in range(6)]
        urls = ('https://example.invalid/a', 'http://example.invalid/a',
                'https://user:password@example.invalid/a',
                'https://example.invalid/a\nsecret', 'https://example.invalid/a" onclick="evil',
                'https://example.invalid/a\u0085secret')
        for index, url in enumerate(urls):
            report['items'][0]['evidence'][index]['official_source'] = url
        html = render_review(report)
        self.assertEqual(html.count('<a href='), 1)
        self.assertNotIn('href="http://', html)
        self.assertNotIn('href="https://user:', html)
        self.assertNotIn('onclick="evil', html)

    def test_historical_transition_and_retrieval_dates_are_visible(self):
        report = report_fixture()
        report['items'][0]['status'] = 'HISTORY'
        report['items'][0]['evidence'] = [{
            'record_id': 'fictional', 'official_source': 'https://example.invalid/source',
            'retrieved_at': '2026-09-20T00:00:00Z', 'as_of': '2024-12-31',
            'matched_effective_from': '2020-01-01', 'matched_effective_to': '2024-01-01',
            'matched_title': 'Synthetic', 'matched_provision': 'article 1',
            'version_transition': {'effective_from': '2024-01-01',
                                   'title': 'Synthetic amendment', 'provision': 'article 2'},
        }]
        html = render_review(report)
        self.assertIn('2026-09-20T00:00:00Z', html)
        self.assertIn('transition 2024-01-01', html)
        self.assertIn('Synthetic amendment', html)

    def test_latest_disposition_and_timing_unknown_and_invalid_ledger(self):
        report = report_fixture()
        ledger = append_event(new_ledger(report), report, action='decide', item_number=1,
                              disposition='confirm', stage=None, at='2026-09-20T00:00:00Z')
        html = render_review(report, ledger)
        self.assertIn('confirm', html)
        self.assertIn('unknown', html)
        self.assertIn('unreviewed', html)
        invalid = copy.deepcopy(ledger)
        invalid['report_digest'] = '0' * 64
        with self.assertRaises(ScanRequestError):
            render_review(report, invalid)

    def test_error_banner_original_numbers_priority_and_no_locator(self):
        report = report_fixture()
        report['items'][0]['status'] = 'CURRENT'
        report['items'][1]['status'] = 'REVIEW'
        report['collection_errors'] = [{'code': 'SYNTHETIC_ERROR', 'stage': 'parse',
                                        'fatal': True, 'locator': None, 'message': 'synthetic'}]
        html = render_review(report)
        self.assertIn('SYNTHETIC_ERROR', html)
        self.assertLess(html.index('item 2'), html.index('item 1'))
        self.assertNotIn('section0.xml:p1', html)


if __name__ == '__main__':
    unittest.main()
