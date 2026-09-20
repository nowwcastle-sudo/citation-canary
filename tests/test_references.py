from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from citation_canary import scan_document

from tests.support import write_catalog, write_hwpx


class ReferenceOccurrenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name)
        self.hwpx_path = self.work_dir / "references.hwpx"
        self.catalog_path = self.work_dir / "catalog.json"
        write_catalog(self.catalog_path)

    def test_two_titles_in_one_node_keep_text_order(self) -> None:
        write_hwpx(
            self.hwpx_path,
            ("가상업무규정 제9조와 가상행정규칙 제7조를 확인한다.",),
        )

        report = scan_document(
            self.hwpx_path,
            date(2024, 12, 31),
            self.catalog_path,
        )

        self.assertEqual(
            tuple(item.reference.title for item in report.items),
            ("가상업무규정", "가상행정규칙"),
        )
        self.assertEqual(
            tuple(item.reference.provision for item in report.items),
            ("제9조", "제7조"),
        )

    def test_repeated_title_occurrences_keep_distinct_provisions(self) -> None:
        write_hwpx(
            self.hwpx_path,
            ("가상행정규칙 제7조와 가상행정규칙 제8조를 비교한다.",),
        )

        report = scan_document(
            self.hwpx_path,
            date(2024, 12, 31),
            self.catalog_path,
        )

        self.assertEqual(
            tuple(item.reference.title for item in report.items),
            ("가상행정규칙", "가상행정규칙"),
        )
        self.assertEqual(
            tuple(item.reference.provision for item in report.items),
            ("제7조", "제8조"),
        )

    def test_provision_after_title_wins_over_earlier_unrelated_provision(self) -> None:
        write_hwpx(
            self.hwpx_path,
            ("제3조 검토 후 가상행정규칙 제7조를 적용한다.",),
        )

        report = scan_document(
            self.hwpx_path,
            date(2024, 12, 31),
            self.catalog_path,
        )

        self.assertEqual(report.items[0].reference.title, "가상행정규칙")
        self.assertEqual(report.items[0].reference.provision, "제7조")

    def test_mixed_known_and_separate_ambiguous_marker_keeps_unknown(self) -> None:
        write_hwpx(
            self.hwpx_path,
            ("가상행정규칙 제7조와 관계 규정에 따른다.",),
        )

        report = scan_document(
            self.hwpx_path,
            date(2024, 12, 31),
            self.catalog_path,
        )

        self.assertEqual(
            tuple(item.reference.title for item in report.items),
            ("가상행정규칙", None),
        )
        self.assertEqual(
            tuple(item.reason_code for item in report.items),
            ("EXACT_HISTORICAL_MATCH", "AMBIGUOUS_CITATION"),
        )


if __name__ == "__main__":
    unittest.main()
