from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from citation_canary.__main__ import main
from citation_canary.review_io import canonical_digest
from tests.test_review_ledger import report_fixture


class ReviewCliTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
