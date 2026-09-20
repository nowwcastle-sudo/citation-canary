from __future__ import annotations

import hashlib
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from citation_canary import hwpx, references, scan_document, scanner
from citation_canary.catalog import load_catalog

from tests.support import write_catalog, write_hwpx


class ResourceLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.document = self.root / "resource.hwpx"
        self.catalog = self.root / "catalog.json"
        write_catalog(self.catalog)

    def _scan(self):
        before = self.document.read_bytes()
        report = scan_document(self.document, date(2024, 12, 31), self.catalog)
        self.assertEqual(self.document.read_bytes(), before)
        self.assertEqual(report.document_sha256, hashlib.sha256(before).hexdigest())
        return report

    def _assert_limit(self, code: str, stage: str, message: str) -> None:
        report = self._scan()
        self.assertEqual(report.items, ())
        self.assertEqual(len(report.collection_errors), 1)
        error = report.collection_errors[0]
        self.assertEqual((error.code, error.stage, error.fatal), (code, stage, True))
        self.assertEqual(error.message, message)

    def test_xml_budgets_are_cumulative_and_fail_closed(self) -> None:
        cases = (
            ("MAX_XML_ELEMENTS", 6, (b"<s><t/><t/></s>",) * 2),
            ("MAX_TEXT_NODES", 4, (b"<s><t/><t/></s>",) * 2),
            ("MAX_XML_DEPTH", 3, (b"<s><p><t/></p></s>",)),
            ("MAX_RETAINED_TEXT_CHARS", 4, (b"<s><t>ab</t></s>",) * 2),
        )
        for name, boundary, sections in cases:
            with self.subTest(budget=name):
                with ZipFile(self.document, "w", compression=ZIP_DEFLATED) as archive:
                    archive.writestr("mimetype", "application/hwp+zip")
                    for index, xml in enumerate(sections):
                        archive.writestr(f"Contents/section{index}.xml", xml)
                with patch.object(hwpx, name, boundary, create=True):
                    self.assertEqual(self._scan().collection_errors, ())
                with patch.object(hwpx, name, boundary - 1, create=True):
                    self._assert_limit(
                        "HWPX_LIMIT_EXCEEDED", "parse",
                        "HWPX archive exceeds a safety limit.",
                    )

    def test_empty_text_is_not_retained_but_locator_ordinals_are_preserved(self) -> None:
        write_hwpx(self.document, ("", "가상행정규칙 제7조", "", "규정"))
        parsed = hwpx.parse_hwpx(self.document)
        self.assertEqual(tuple(node.text for node in parsed.nodes), ("가상행정규칙 제7조", "규정"))
        self.assertEqual(
            tuple(node.locator for node in parsed.nodes),
            ("Contents/section0.xml:t[2]", "Contents/section0.xml:t[4]"),
        )

    def test_candidate_limits_reject_without_partial_results(self) -> None:
        for name, texts in (
            ("MAX_CANDIDATES_PER_NODE", ("가상행정규칙 " * 3,)),
            ("MAX_CANDIDATES", ("가상행정규칙",) * 3),
            ("MAX_CANDIDATES_PER_NODE", ("가상행정규칙 가상행정규칙 관계 고시",)),
            ("MAX_CANDIDATES", ("관계 고시",) * 3),
        ):
            with self.subTest(budget=name, texts=texts):
                write_hwpx(self.document, texts)
                with patch.object(references, name, 3, create=True):
                    self.assertEqual(len(self._scan().items), 3)
                with patch.object(references, name, 2, create=True):
                    self._assert_limit(
                        "REFERENCE_LIMIT_EXCEEDED", "extract",
                        "Reference extraction exceeds a safety limit.",
                    )

    def test_match_limits_include_title_and_covered_marker_work(self) -> None:
        for name, texts in (
            ("MAX_MATCHES_PER_NODE", ("가상업무규정 가상업무규정",)),
            ("MAX_MATCHES", ("가상업무규정", "가상업무규정")),
        ):
            with self.subTest(budget=name):
                write_hwpx(self.document, texts)
                with patch.object(references, name, 4, create=True):
                    self.assertEqual(len(self._scan().items), 2)
                with patch.object(references, name, 3, create=True):
                    self._assert_limit(
                        "REFERENCE_LIMIT_EXCEEDED", "extract",
                        "Reference extraction exceeds a safety limit.",
                    )

    def test_longest_title_precedence_and_earliest_ambiguity_keep_document_order(self) -> None:
        catalog = load_catalog(self.catalog)
        record = catalog.records[0]
        catalog = replace(catalog, records=(replace(record, versions=(
            replace(record.versions[0], title="가상규정고시"),
            replace(record.versions[1], title="규정"),
        )),))
        nodes = (hwpx.TextNode("Contents/section0.xml:t[1]", "예규 가상규정고시 제7조 규정 제9조 관계 법"),)
        candidates = references.extract_references(nodes, catalog)
        self.assertEqual(
            tuple((item.title, item.provision) for item in candidates),
            ((None, None), ("가상규정고시", "제7조"), ("규정", "제9조")),
        )

    def test_overlap_work_scales_with_matches_without_scanning_prior_intervals(self) -> None:
        catalog = load_catalog(self.catalog)
        widths: list[int] = []

        class CountedCoverage(bytearray):
            def find(self, value, start=0, end=None):
                widths.append(end - start)
                return super().find(value, start, end)

        for count in (32, 64):
            with self.subTest(repetitions=count):
                widths.clear()
                nodes = (hwpx.TextNode("Contents/section0.xml:t[1]", "가상업무규정 " * count),)
                with patch.object(references, "bytearray", CountedCoverage, create=True):
                    candidates = references.extract_references(nodes, catalog)
                self.assertEqual(len(candidates), count)
                # Each title and its covered marker requires one bounded lookup.
                self.assertEqual(len(widths), 2 * count)
                self.assertEqual(sum(widths), count * (len("가상업무규정") + len("규정")))

    def test_budget_rejection_still_performs_final_source_hash_check(self) -> None:
        write_hwpx(self.document, ("가상행정규칙",))

        def reject_after_mutation(*args):
            self.document.write_bytes(b"synthetic changed source")
            raise references._ReferenceLimitExceeded("private body must not escape")

        with patch.object(scanner, "extract_references", side_effect=reject_after_mutation):
            report = scan_document(self.document, date(2024, 12, 31), self.catalog)
        self.assertEqual(report.items, ())
        self.assertEqual(len(report.collection_errors), 1)
        self.assertEqual(report.collection_errors[0].code, "SOURCE_CHANGED_DURING_SCAN")
        self.assertEqual(report.collection_errors[0].message, "Source changed during scan.")


if __name__ == "__main__":
    unittest.main()
