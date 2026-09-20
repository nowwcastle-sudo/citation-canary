from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZIP_STORED, ZipFile

from citation_canary import CollectionError, ScanRequestError, scan_document
from citation_canary import hwpx
from citation_canary import scanner

from tests.support import SECTION_PATH, write_catalog, write_hwpx


AS_OF = date(2024, 12, 31)


class RequestErrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name)
        self.document_path = self.work_dir / "request.hwpx"
        self.catalog_path = self.work_dir / "catalog.json"
        write_hwpx(self.document_path, ("관계 규정에 따른다.",))
        write_catalog(self.catalog_path)
        self.valid_catalog_value = json.loads(
            self.catalog_path.read_text(encoding="utf-8")
        )

    def test_request_error_codes_and_safe_messages(self) -> None:
        cases = (
            (
                "DOCUMENT_NOT_FOUND",
                lambda: scan_document(
                    self.work_dir / "missing.hwpx",
                    AS_OF,
                    self.catalog_path,
                ),
            ),
            (
                "DOCUMENT_NOT_READABLE",
                lambda: scan_document(self.work_dir, AS_OF, self.catalog_path),
            ),
            (
                "AS_OF_TYPE_INVALID",
                lambda: scan_document(
                    self.document_path,
                    "2024-12-31",  # type: ignore[arg-type]
                    self.catalog_path,
                ),
            ),
            (
                "CATALOG_NOT_FOUND",
                lambda: scan_document(
                    self.document_path,
                    AS_OF,
                    self.work_dir / "missing.json",
                ),
            ),
            (
                "CATALOG_NOT_READABLE",
                lambda: scan_document(self.document_path, AS_OF, self.work_dir),
            ),
        )

        for expected_code, operation in cases:
            with self.subTest(code=expected_code):
                self._assert_request_error(expected_code, operation)

    def test_invalid_catalog_encodings_and_json_have_one_stable_code(self) -> None:
        invalid_values = (b"\xff", b'{"schema_version":')
        for raw in invalid_values:
            with self.subTest(raw=raw):
                self.catalog_path.write_bytes(raw)
                self._assert_request_error(
                    "CATALOG_JSON_INVALID",
                    lambda: scan_document(
                        self.document_path,
                        AS_OF,
                        self.catalog_path,
                    ),
                )

    def test_duplicate_json_keys_at_root_and_nested_levels_are_rejected(self) -> None:
        raw = json.dumps(
            self.valid_catalog_value,
            ensure_ascii=False,
        )
        source_url = self.valid_catalog_value["records"][0]["official_source"][  # type: ignore[index]
            "url"
        ]
        url_field = f'"url": "{source_url}"'
        duplicate_values = (
            raw.replace(
                '"schema_version": "1"',
                '"schema_version": "1", "schema_version": "1"',
                1,
            ),
            raw.replace(url_field, f"{url_field}, {url_field}", 1),
        )

        for duplicate_json in duplicate_values:
            with self.subTest(duplicate_json=duplicate_json[:80]):
                self.catalog_path.write_text(duplicate_json, encoding="utf-8")
                self._assert_request_error(
                    "CATALOG_JSON_INVALID",
                    lambda: scan_document(
                        self.document_path,
                        AS_OF,
                        self.catalog_path,
                    ),
                )

    def test_invalid_https_url_syntax_is_a_typed_schema_error(self) -> None:
        invalid_urls = (
            "https://[invalid-host",
            "https://example.invalid:not-a-port/source",
        )
        for invalid_url in invalid_urls:
            with self.subTest(url=invalid_url):
                value = self._catalog_value()
                value["records"][0]["official_source"]["url"] = invalid_url  # type: ignore[index]
                self._write_catalog_value(value)
                self._assert_request_error(
                    "CATALOG_SCHEMA_INVALID",
                    lambda: scan_document(
                        self.document_path,
                        AS_OF,
                        self.catalog_path,
                    ),
                )

    def test_unsupported_catalog_schema_has_stable_code(self) -> None:
        value = self._catalog_value()
        value["schema_version"] = "2"
        self._write_catalog_value(value)

        self._assert_request_error(
            "CATALOG_SCHEMA_UNSUPPORTED",
            lambda: scan_document(
                self.document_path,
                AS_OF,
                self.catalog_path,
            ),
        )

    def test_schema_failures_and_unknown_fields_have_one_stable_code(self) -> None:
        def missing_records(value: dict[str, object]) -> None:
            del value["records"]

        def root_extra(value: dict[str, object]) -> None:
            value["extra"] = True

        def record_extra(value: dict[str, object]) -> None:
            value["records"][0]["extra"] = True  # type: ignore[index]

        def source_extra(value: dict[str, object]) -> None:
            value["records"][0]["official_source"]["extra"] = True  # type: ignore[index]

        def version_extra(value: dict[str, object]) -> None:
            value["records"][0]["versions"][0]["extra"] = True  # type: ignore[index]

        def provision_extra(value: dict[str, object]) -> None:
            value["records"][0]["versions"][0]["provisions"][0][  # type: ignore[index]
                "extra"
            ] = True

        def timestamp_without_offset(value: dict[str, object]) -> None:
            value["records"][0]["official_source"][  # type: ignore[index]
                "retrieved_at"
            ] = "2026-09-04T00:00:00"

        def timestamp_with_non_rfc3339_separator(value: dict[str, object]) -> None:
            value["records"][0]["official_source"][  # type: ignore[index]
                "retrieved_at"
            ] = "2026-09-04 00:00:00+09:00"

        def timestamp_with_offset_seconds(value: dict[str, object]) -> None:
            value["records"][0]["official_source"][  # type: ignore[index]
                "retrieved_at"
            ] = "2026-09-04T00:00:00+09:00:30"

        def basic_effective_date(value: dict[str, object]) -> None:
            value["records"][0]["versions"][0][  # type: ignore[index]
                "effective_from"
            ] = "20200101"

        mutations = (
            missing_records,
            root_extra,
            record_extra,
            source_extra,
            version_extra,
            provision_extra,
            timestamp_without_offset,
            timestamp_with_non_rfc3339_separator,
            timestamp_with_offset_seconds,
            basic_effective_date,
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate.__name__):
                value = self._catalog_value()
                mutate(value)
                self._write_catalog_value(value)
                self._assert_request_error(
                    "CATALOG_SCHEMA_INVALID",
                    lambda: scan_document(
                        self.document_path,
                        AS_OF,
                        self.catalog_path,
                    ),
                )

    def _assert_request_error(self, expected_code: str, operation: object) -> None:
        with self.assertRaises(ScanRequestError) as raised:
            operation()  # type: ignore[operator]
        error = raised.exception
        self.assertEqual(error.code, expected_code)
        self.assertEqual(str(error), error.safe_message)
        self.assertNotIn(str(self.work_dir.resolve()), error.safe_message)
        for forbidden_field in ("document", "catalog", "payload"):
            self.assertFalse(hasattr(error, forbidden_field))

    def _catalog_value(self) -> dict[str, object]:
        return json.loads(json.dumps(self.valid_catalog_value, ensure_ascii=False))

    def _write_catalog_value(self, value: dict[str, object]) -> None:
        self.catalog_path.write_text(
            json.dumps(value, ensure_ascii=False),
            encoding="utf-8",
        )


class CollectionErrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name)
        self.document_path = self.work_dir / "collection.hwpx"
        self.catalog_path = self.work_dir / "catalog.json"
        write_catalog(self.catalog_path)

    def test_document_not_zip_is_fatal(self) -> None:
        self.document_path.write_bytes(b"not a zip archive")

        self._assert_fatal("DOCUMENT_NOT_ZIP", "parse")

    def test_invalid_hwpx_mimetype_is_fatal(self) -> None:
        self._write_archive(
            mimetype=b"application/zip",
            section=b"<section />",
        )

        self._assert_fatal("HWPX_MIMETYPE_INVALID", "parse")

    def test_missing_hwpx_section_is_fatal(self) -> None:
        self._write_archive(mimetype=b"application/hwp+zip", section=None)

        self._assert_fatal("HWPX_SECTION_MISSING", "parse")

    def test_each_archive_ceiling_is_fatal(self) -> None:
        write_hwpx(self.document_path, ("관계 규정에 따른다.",))
        ceilings = (
            ("MAX_COMPRESSED_BYTES", 0),
            ("MAX_ENTRIES", 1),
            ("MAX_SECTION_BYTES", 1),
            ("MAX_TOTAL_UNCOMPRESSED_BYTES", 1),
        )
        for constant, value in ceilings:
            with self.subTest(constant=constant):
                with patch.object(hwpx, constant, value):
                    self._assert_fatal("HWPX_LIMIT_EXCEEDED", "parse")

    def test_invalid_xml_and_declarations_are_fatal(self) -> None:
        invalid_sections = (
            b"<section><t></section>",
            b'<!DOCTYPE section [<!ENTITY unsafe "value">]><section />',
        )
        for xml_bytes in invalid_sections:
            with self.subTest(xml_bytes=xml_bytes):
                self._write_archive(
                    mimetype=b"application/hwp+zip",
                    section=xml_bytes,
                )
                self._assert_fatal("HWPX_XML_INVALID", "parse")

    def test_unsupported_and_encrypted_zip_members_fail_closed(self) -> None:
        section = b"<section><t>relation rule</t></section>"

        with ZipFile(
            self.document_path,
            mode="w",
            compression=ZIP_BZIP2,
        ) as archive:
            archive.writestr("mimetype", b"application/hwp+zip")
            archive.writestr(SECTION_PATH, section)
        self._assert_fatal("DOCUMENT_NOT_ZIP", "parse")

        self._write_archive(
            mimetype=b"application/hwp+zip",
            section=section,
        )
        self._mark_members_encrypted(self.document_path)
        self._assert_fatal("DOCUMENT_NOT_ZIP", "parse")

    def test_member_crc_read_error_fails_closed(self) -> None:
        section = b"<section><t>relation rule</t></section>"
        with ZipFile(
            self.document_path,
            mode="w",
            compression=ZIP_STORED,
        ) as archive:
            archive.writestr("mimetype", b"application/hwp+zip")
            archive.writestr(SECTION_PATH, section)

        archive_bytes = bytearray(self.document_path.read_bytes())
        section_offset = archive_bytes.find(section)
        self.assertGreaterEqual(section_offset, 0)
        archive_bytes[section_offset + len("<section><t>")] ^= 1
        self.document_path.write_bytes(archive_bytes)

        self._assert_fatal("DOCUMENT_NOT_ZIP", "parse")

    def test_unknown_xml_encoding_is_fatal(self) -> None:
        self._write_archive(
            mimetype=b"application/hwp+zip",
            section=(
                b'<?xml version="1.0" encoding="x-private-unknown"?>'
                b"<section><t>relation rule</t></section>"
            ),
        )

        self._assert_fatal("HWPX_XML_INVALID", "parse")

    def test_oversized_numeric_section_suffix_is_fatal(self) -> None:
        with ZipFile(
            self.document_path,
            mode="w",
            compression=ZIP_DEFLATED,
        ) as archive:
            archive.writestr("mimetype", b"application/hwp+zip")
            archive.writestr(
                f"Contents/section{'9' * 5000}.xml",
                b"<section><t>relation rule</t></section>",
            )

        self._assert_fatal("HWPX_LIMIT_EXCEEDED", "parse")

    def test_duplicate_canonical_section_names_are_fatal(self) -> None:
        with ZipFile(
            self.document_path,
            mode="w",
            compression=ZIP_DEFLATED,
        ) as archive:
            archive.writestr("mimetype", b"application/hwp+zip")
            archive.writestr(
                "Contents/section0.xml",
                b"<section><t>first</t></section>",
            )
            archive.writestr(
                "Contents/section00.xml",
                b"<section><t>second</t></section>",
            )

        self._assert_fatal("HWPX_XML_INVALID", "parse")

    def test_utf16_entity_declaration_is_rejected_before_elementtree(self) -> None:
        xml_bytes = (
            '<?xml version="1.0" encoding="UTF-16"?>'
            '<!DOCTYPE section [<!ENTITY unsafe "expanded">]>'
            "<section><t>&unsafe;</t></section>"
        ).encode("utf-16")
        self._write_archive(
            mimetype=b"application/hwp+zip",
            section=xml_bytes,
        )

        with patch.object(
            hwpx.ElementTree,
            "iterparse",
            side_effect=AssertionError("ElementTree must not see UTF-16 XML"),
        ):
            self._assert_fatal("HWPX_XML_INVALID", "parse")

    def test_bomless_utf16_entity_declarations_are_rejected_before_elementtree(
        self,
    ) -> None:
        xml_text = (
            '<?xml version="1.0" encoding="UTF-16"?>'
            '<!DOCTYPE section [<!ENTITY unsafe "expanded">]>'
            "<section><t>&unsafe;</t></section>"
        )
        for encoding in ("utf-16-le", "utf-16-be"):
            with self.subTest(encoding=encoding):
                self._write_archive(
                    mimetype=b"application/hwp+zip",
                    section=xml_text.encode(encoding),
                )
                with patch.object(
                    hwpx.ElementTree,
                    "iterparse",
                    side_effect=AssertionError(
                        "ElementTree must not see BOM-less UTF-16 XML"
                    ),
                ):
                    self._assert_fatal("HWPX_XML_INVALID", "parse")

    def test_source_change_from_parser_is_fatal(self) -> None:
        write_hwpx(self.document_path, ("관계 규정에 따른다.",))
        parse_result = hwpx.ParseResult(
            document_name=self.document_path.name,
            document_sha256="0" * 64,
            nodes=(),
            errors=(
                CollectionError(
                    code="SOURCE_CHANGED_DURING_SCAN",
                    stage="parse",
                    fatal=True,
                    locator=self.document_path.name,
                    message="Source changed during scan.",
                ),
            ),
        )

        with patch("citation_canary.scanner.parse_hwpx", return_value=parse_result):
            self._assert_fatal("SOURCE_CHANGED_DURING_SCAN", "parse")

    def test_parser_rehashes_and_fails_closed_when_source_changes(self) -> None:
        write_hwpx(self.document_path, ("관계 규정에 따른다.",))

        with patch.object(
            hwpx,
            "_sha256_file",
            side_effect=("0" * 64, "1" * 64),
        ) as sha256_file:
            result = hwpx.parse_hwpx(self.document_path)

        self.assertEqual(sha256_file.call_count, 2)
        self.assertEqual(result.nodes, ())
        self.assertEqual(
            tuple(error.code for error in result.errors),
            ("SOURCE_CHANGED_DURING_SCAN",),
        )

    def test_final_rehash_failure_is_safe_source_change(self) -> None:
        write_hwpx(self.document_path, ("관계 규정에 따른다.",))

        with patch.object(
            hwpx,
            "_sha256_file",
            side_effect=(
                "0" * 64,
                FileNotFoundError(
                    f"source disappeared: {self.document_path.resolve()}"
                ),
            ),
        ) as sha256_file:
            result = hwpx.parse_hwpx(self.document_path)

        self.assertEqual(sha256_file.call_count, 2)
        self.assertEqual(result.nodes, ())
        self.assertEqual(
            tuple(error.code for error in result.errors),
            ("SOURCE_CHANGED_DURING_SCAN",),
        )

    def test_source_mutation_during_extraction_is_caught_at_public_return(
        self,
    ) -> None:
        write_hwpx(self.document_path, ("관계 규정에 따른다.",))
        original_extract = scanner.extract_references

        def mutate_then_extract(nodes: object, catalog: object) -> object:
            self.document_path.write_bytes(
                self.document_path.read_bytes() + b"external mutation"
            )
            return original_extract(nodes, catalog)  # type: ignore[arg-type]

        with patch(
            "citation_canary.scanner.extract_references",
            side_effect=mutate_then_extract,
        ):
            report = scan_document(
                self.document_path,
                AS_OF,
                self.catalog_path,
            )

        self._assert_source_changed_report(report)

    def test_source_mutation_during_resolution_is_caught_at_public_return(
        self,
    ) -> None:
        write_hwpx(self.document_path, ("가상행정규칙 제7조에 따른다.",))
        original_resolve = scanner.resolve_reference

        def mutate_then_resolve(
            candidate: object,
            as_of: object,
            catalog: object,
        ) -> object:
            self.document_path.write_bytes(
                self.document_path.read_bytes() + b"external mutation"
            )
            return original_resolve(  # type: ignore[arg-type]
                candidate,
                as_of,
                catalog,
            )

        with patch(
            "citation_canary.scanner.resolve_reference",
            side_effect=mutate_then_resolve,
        ):
            report = scan_document(
                self.document_path,
                AS_OF,
                self.catalog_path,
            )

        self._assert_source_changed_report(report)

    def test_decisive_final_source_read_failure_is_safe_source_change(self) -> None:
        write_hwpx(self.document_path, ("관계 규정에 따른다.",))
        real_sha256_file = hwpx._sha256_file
        call_count = 0

        def fail_on_public_final_read(path: Path) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise FileNotFoundError(
                    f"source disappeared: {self.document_path.resolve()}"
                )
            return real_sha256_file(path)

        with patch.object(
            hwpx,
            "_sha256_file",
            side_effect=fail_on_public_final_read,
        ):
            report = scan_document(
                self.document_path,
                AS_OF,
                self.catalog_path,
            )

        self.assertEqual(call_count, 3)
        self._assert_source_changed_report(report)

    def test_error_report_uses_pseudonymous_name_and_safe_locator(self) -> None:
        self.document_path = self.work_dir / "private-payroll-secret.hwpx"
        self.document_path.write_bytes(b"not a zip archive")
        expected_digest = hashlib.sha256(self.document_path.read_bytes()).hexdigest()

        report = scan_document(
            self.document_path,
            AS_OF,
            self.catalog_path,
        )
        serialized = json.dumps(report.to_dict(), ensure_ascii=False)

        self.assertEqual(
            report.document_name,
            f"document-{expected_digest[:12]}.hwpx",
        )
        self.assertIsNone(report.collection_errors[0].locator)
        self.assertNotIn(self.document_path.name, serialized)

    def test_reference_extraction_failure_is_fatal(self) -> None:
        write_hwpx(self.document_path, ("관계 규정에 따른다.",))

        with patch(
            "citation_canary.scanner.extract_references",
            side_effect=scanner._ReferenceExtractionError(
                f"sensitive {self.document_path.resolve()}"
            ),
        ):
            self._assert_fatal("REFERENCE_EXTRACTION_FAILED", "extract")

    def test_catalog_resolution_failure_is_fatal(self) -> None:
        write_hwpx(self.document_path, ("가상행정규칙 제7조에 따른다.",))

        with patch(
            "citation_canary.scanner.resolve_reference",
            side_effect=scanner._CatalogResolutionError(
                f"sensitive {self.catalog_path.resolve()}"
            ),
        ):
            self._assert_fatal("CATALOG_RESOLUTION_FAILED", "resolve")

    def test_unrelated_value_errors_propagate_from_transform_seams(self) -> None:
        write_hwpx(self.document_path, ("가상행정규칙 제7조에 따른다.",))
        seams = (
            "citation_canary.scanner.extract_references",
            "citation_canary.scanner.resolve_reference",
        )
        for seam in seams:
            with self.subTest(seam=seam):
                with patch(seam, side_effect=ValueError("programmer error")):
                    with self.assertRaisesRegex(ValueError, "programmer error"):
                        scan_document(
                            self.document_path,
                            AS_OF,
                            self.catalog_path,
                        )

    def test_unexpected_library_errors_propagate(self) -> None:
        write_hwpx(self.document_path, ("가상행정규칙 제7조에 따른다.",))
        seams = (
            "citation_canary.scanner.parse_hwpx",
            "citation_canary.scanner.extract_references",
            "citation_canary.scanner.resolve_reference",
        )
        for seam in seams:
            with self.subTest(seam=seam):
                with patch(seam, side_effect=RuntimeError("programmer error")):
                    with self.assertRaisesRegex(RuntimeError, "programmer error"):
                        scan_document(
                            self.document_path,
                            AS_OF,
                            self.catalog_path,
                        )

    def test_parser_never_extracts_archive_members(self) -> None:
        write_hwpx(self.document_path, ("관계 규정에 따른다.",))

        with (
            patch.object(ZipFile, "extract", side_effect=AssertionError),
            patch.object(ZipFile, "extractall", side_effect=AssertionError),
        ):
            report = scan_document(
                self.document_path,
                AS_OF,
                self.catalog_path,
            )

        self.assertEqual(report.collection_errors, ())

    def _assert_fatal(self, expected_code: str, expected_stage: str) -> None:
        before_files = sorted(path.name for path in self.work_dir.iterdir())
        report = scan_document(
            self.document_path,
            AS_OF,
            self.catalog_path,
        )

        self.assertEqual(len(report.collection_errors), 1)
        error = report.collection_errors[0]
        self.assertEqual(error.code, expected_code)
        self.assertEqual(error.stage, expected_stage)
        self.assertTrue(error.fatal)
        self.assertEqual(report.items, ())
        self.assertNotIn(str(self.document_path.resolve()), error.message)
        self.assertNotIn(str(self.catalog_path.resolve()), error.message)
        self.assertEqual(
            sorted(path.name for path in self.work_dir.iterdir()),
            before_files,
        )

    def _assert_source_changed_report(self, report: object) -> None:
        self.assertEqual(report.items, ())  # type: ignore[attr-defined]
        self.assertEqual(  # type: ignore[attr-defined]
            tuple(error.code for error in report.collection_errors),
            ("SOURCE_CHANGED_DURING_SCAN",),
        )
        serialized = json.dumps(report.to_dict(), ensure_ascii=False)  # type: ignore[attr-defined]
        self.assertNotIn(self.document_path.name, serialized)

    @staticmethod
    def _mark_members_encrypted(path: Path) -> None:
        archive_bytes = bytearray(path.read_bytes())
        signatures = (
            (b"PK\x03\x04", 6),
            (b"PK\x01\x02", 8),
        )
        for signature, flag_offset in signatures:
            search_from = 0
            while (header := archive_bytes.find(signature, search_from)) != -1:
                offset = header + flag_offset
                flags = int.from_bytes(archive_bytes[offset : offset + 2], "little")
                archive_bytes[offset : offset + 2] = (flags | 1).to_bytes(2, "little")
                search_from = header + len(signature)
        path.write_bytes(archive_bytes)

    def _write_archive(self, *, mimetype: bytes, section: bytes | None) -> None:
        with ZipFile(
            self.document_path,
            mode="w",
            compression=ZIP_DEFLATED,
        ) as archive:
            archive.writestr("mimetype", mimetype)
            if section is not None:
                archive.writestr(SECTION_PATH, section)


if __name__ == "__main__":
    unittest.main()
