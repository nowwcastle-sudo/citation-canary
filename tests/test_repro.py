from __future__ import annotations

import hashlib
import json
import socket
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from citation_canary import ScanReport, Status, scan_document

from tests.support import write_catalog, write_synthetic_hwpx


AS_OF = date(2024, 12, 31)


class FutureScannerReproductionTests(unittest.TestCase):
    """Executable acceptance seam for the first offline citation report."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name)
        self.hwpx_path = self.work_dir / "private-employee-review.hwpx"
        self.catalog_path = self.work_dir / "catalog.json"
        write_synthetic_hwpx(self.hwpx_path)
        write_catalog(self.catalog_path)
        self.before_digest = self._sha256(self.hwpx_path)
        self.before_files = sorted(path.name for path in self.work_dir.iterdir())

    def test_reference_renamed_and_moved_after_as_of_has_reviewable_history(self) -> None:
        report = self._scan()

        self.assertIs(report.items[0].status, Status.HISTORY)
        self.assertEqual(report.items[0].evidence[0].as_of, "2024-12-31")
        self.assertEqual(
            report.items[0].evidence[0].official_source,
            "https://example.invalid/official-source/synthetic-rule-001",
        )
        transition = report.items[0].evidence[0].version_transition
        self.assertIsNotNone(transition)
        self.assertEqual(transition.title, "가상업무규정")

    def test_ambiguous_reference_is_unknown(self) -> None:
        report = self._scan()

        self.assertIs(report.items[1].status, Status.UNKNOWN)
        self.assertEqual(report.items[1].reason_code, "AMBIGUOUS_CITATION")
        self.assertNotIn("legal_judgment", report.to_dict()["items"][1])

    def test_scan_does_not_modify_or_write_beside_original(self) -> None:
        self._scan()

        self.assertEqual(self._sha256(self.hwpx_path), self.before_digest)
        self.assertEqual(
            sorted(path.name for path in self.work_dir.iterdir()),
            self.before_files,
        )

    def test_success_report_uses_sha_derived_document_identifier(self) -> None:
        report = self._scan()
        serialized = json.dumps(report.to_dict(), ensure_ascii=False)

        self.assertEqual(
            report.document_name,
            f"document-{self.before_digest[:12]}.hwpx",
        )
        self.assertNotIn(self.hwpx_path.name, serialized)

    def _scan(self) -> ScanReport:
        with patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("The reproduction must not access the network."),
        ):
            return scan_document(self.hwpx_path, AS_OF, self.catalog_path)

    @staticmethod
    def _sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
