from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from citation_canary import Status, scan_document

from tests.support import (
    write_catalog,
    write_hwpx,
    write_provision_conflict_catalog,
    write_synthetic_hwpx,
)


class StatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name)
        self.hwpx_path = self.work_dir / "status.hwpx"
        self.catalog_path = self.work_dir / "catalog.json"

    def test_latest_exact_match_is_current(self) -> None:
        write_hwpx(self.hwpx_path, ("가상업무규정 제9조에 따른다.",))
        write_catalog(self.catalog_path)

        report = scan_document(
            self.hwpx_path,
            date(2025, 2, 1),
            self.catalog_path,
        )

        self.assertIs(report.items[0].status, Status.CURRENT)
        self.assertEqual(report.items[0].reason_code, "EXACT_CURRENT_MATCH")
        self.assertEqual(report.items[0].evidence[0].matched_title, "가상업무규정")

    def test_exact_historical_match_is_history(self) -> None:
        write_synthetic_hwpx(self.hwpx_path)
        write_catalog(self.catalog_path)

        report = scan_document(
            self.hwpx_path,
            date(2024, 12, 31),
            self.catalog_path,
        )

        self.assertIs(report.items[0].status, Status.HISTORY)
        self.assertEqual(report.items[0].reason_code, "EXACT_HISTORICAL_MATCH")
        self.assertEqual(
            report.items[0].evidence[0].version_transition.provision,
            "제9조",
        )

    def test_competing_catalog_matches_require_review(self) -> None:
        write_synthetic_hwpx(self.hwpx_path)
        write_catalog(self.catalog_path, conflict=True)

        report = scan_document(
            self.hwpx_path,
            date(2024, 12, 31),
            self.catalog_path,
        )

        self.assertIs(report.items[0].status, Status.REVIEW)
        self.assertEqual(report.items[0].reason_code, "CONFLICTING_EVIDENCE")
        self.assertEqual(
            tuple(item.record_id for item in report.items[0].evidence),
            ("synthetic-rule-001", "synthetic-rule-002"),
        )

    def test_exact_and_mismatched_as_of_records_require_review(self) -> None:
        write_synthetic_hwpx(self.hwpx_path)
        write_provision_conflict_catalog(self.catalog_path)

        report = scan_document(
            self.hwpx_path,
            date(2024, 12, 31),
            self.catalog_path,
        )

        self.assertIs(report.items[0].status, Status.REVIEW)
        self.assertEqual(report.items[0].reason_code, "CONFLICTING_EVIDENCE")
        self.assertEqual(
            tuple(item.record_id for item in report.items[0].evidence),
            ("synthetic-rule-001", "synthetic-rule-002"),
        )


if __name__ == "__main__":
    unittest.main()
