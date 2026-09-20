from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from citation_canary import ScanRequestError, scan_document

from tests.support import write_hwpx
from tools.build_zipapp import ZipappBuildError, build_zipapp


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
AS_OF = date(2024, 12, 31)


class CatalogJsonBoundaryTests(unittest.TestCase):
    def test_five_thousand_digit_json_number_has_typed_invalid_json_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            work_dir = Path(temporary_directory)
            document_path = work_dir / "request.hwpx"
            catalog_path = work_dir / "catalog.json"
            write_hwpx(document_path, ("관계 규정에 따른다.",))
            catalog_path.write_bytes(
                b'{"schema_version":' + b"9" * 5000 + b',"records":[]}'
            )

            with self.assertRaises(ScanRequestError) as raised:
                scan_document(document_path, AS_OF, catalog_path)

            self.assertEqual(raised.exception.code, "CATALOG_JSON_INVALID")
            self.assertEqual(
                str(raised.exception),
                raised.exception.safe_message,
            )


class ZipappDestinationBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name)
        self.source_root = self.work_dir / "src"
        shutil.copytree(
            SOURCE_ROOT,
            self.source_root,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )

    def test_output_equal_to_allowlisted_source_file_is_rejected_unchanged(
        self,
    ) -> None:
        target = self.source_root / "citation_canary" / "catalog.py"

        self._assert_rejected_without_source_mutation(target)

    def test_new_output_beneath_source_tree_is_rejected_unchanged(self) -> None:
        target = self.source_root / "citation-canary-test.pyz"

        self._assert_rejected_without_source_mutation(target)

    def _assert_rejected_without_source_mutation(self, target: Path) -> None:
        members_before, bytes_before = self._source_snapshot()
        raised: ZipappBuildError | None = None

        try:
            build_zipapp(self.source_root, target)
        except ZipappBuildError as error:
            raised = error

        members_after, bytes_after = self._source_snapshot()
        self.assertEqual(members_after, members_before)
        self.assertEqual(bytes_after, bytes_before)
        self.assertIsInstance(raised, ZipappBuildError)

    def _source_snapshot(self) -> tuple[tuple[str, ...], dict[str, bytes]]:
        paths = tuple(sorted(self.source_root.rglob("*")))
        members = tuple(
            path.relative_to(self.source_root).as_posix() for path in paths
        )
        file_bytes = {
            path.relative_to(self.source_root).as_posix(): path.read_bytes()
            for path in paths
            if path.is_file()
        }
        return members, file_bytes


if __name__ == "__main__":
    unittest.main()
