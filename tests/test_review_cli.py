from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
