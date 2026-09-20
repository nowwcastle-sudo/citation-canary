from __future__ import annotations

import hashlib
import inspect
import json
import marshal
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import zipapp
from pathlib import Path, PurePosixPath
from unittest import mock
from zipfile import ZipFile

from tests.support import write_catalog, write_synthetic_hwpx


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
AS_OF = "2024-12-31"
EXPECTED_ARCHIVE_MEMBERS = {
    "__main__.py",
    "LICENSE",
    "citation_canary/",
    "citation_canary/__init__.py",
    "citation_canary/__main__.py",
    "citation_canary/catalog.py",
    "citation_canary/demo.py",
    "citation_canary/hwpx.py",
    "citation_canary/references.py",
    "citation_canary/report.py",
    "citation_canary/review_io.py",
    "citation_canary/review.py",
    "citation_canary/comparison.py",
    "citation_canary/review_html.py",
    "citation_canary/scanner.py",
}
EXPECTED_SOURCE_ALLOWLIST = (
    "citation_canary/__init__.py",
    "citation_canary/__main__.py",
    "citation_canary/catalog.py",
    "citation_canary/demo.py",
    "citation_canary/hwpx.py",
    "citation_canary/references.py",
    "citation_canary/report.py",
    "citation_canary/review_io.py",
    "citation_canary/review.py",
    "citation_canary/comparison.py",
    "citation_canary/review_html.py",
    "citation_canary/scanner.py",
)


class CitationCanaryZipappTests(unittest.TestCase):
    def test_archive_runs_review_render_compare_commands_without_pythonpath(self) -> None:
        self._build_archive()
        report_path = self.work_dir / 'candidate-report.json'
        ledger_path = self.work_dir / 'candidate-ledger.json'
        html_path = self.work_dir / 'candidate-review.html'
        scan = self._run_archive('--document', str(self.document_path), '--as-of', AS_OF,
                                 '--catalog', str(self.catalog_path), '--output', str(report_path))
        self.assertEqual(scan.returncode, 0, scan.stderr)
        source_before = self.document_path.read_bytes()
        report_before = report_path.read_bytes()
        review = self._run_archive('review', '--report', str(report_path), '--ledger', str(ledger_path),
                                   '--action', 'decide', '--item', '1', '--disposition', 'confirm')
        self.assertEqual(review.returncode, 0, review.stderr)
        ledger_before = ledger_path.read_bytes()
        render = self._run_archive('render', '--report', str(report_path), '--ledger', str(ledger_path),
                                   '--output', str(html_path))
        self.assertEqual(render.returncode, 0, render.stderr)
        self.assertIn(b'<!doctype html>', html_path.read_bytes())
        compare = self._run_archive('compare', '--before', str(report_path), '--after', str(report_path))
        self.assertEqual(compare.returncode, 0, compare.stderr)
        self.assertEqual(json.loads(compare.stdout)['changes'], [])
        self.assertEqual(self.document_path.read_bytes(), source_before)
        self.assertEqual(report_path.read_bytes(), report_before)
        self.assertEqual(ledger_path.read_bytes(), ledger_before)

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name)
        self.input_dir = self.work_dir / "operator-inputs"
        self.input_dir.mkdir()
        self.document_path = self.input_dir / "private-source-do-not-package.hwpx"
        self.catalog_path = self.input_dir / "operator-catalog.json"
        self.archive_path = self.work_dir / "citation-canary-test.pyz"
        write_synthetic_hwpx(self.document_path)
        write_catalog(self.catalog_path)

    def test_self_contained_archive_runs_synthetic_scan_without_pythonpath(
        self,
    ) -> None:
        self._build_archive()
        document_before = self.document_path.read_bytes()
        document_hash_before = hashlib.sha256(document_before).hexdigest()
        input_members_before = self._input_members()

        completed = subprocess.run(
            [
                sys.executable,
                str(self.archive_path),
                "--document",
                str(self.document_path),
                "--as-of",
                AS_OF,
                "--catalog",
                str(self.catalog_path),
            ],
            cwd=self.work_dir,
            env=self._environment_without_pythonpath(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(
            completed.returncode,
            0,
            f"returncode={completed.returncode}; stderr={completed.stderr!r}; stdout={completed.stdout!r}",
        )
        self.assertEqual(completed.stderr, "")
        report = json.loads(completed.stdout)
        self.assertEqual(
            [item["status"] for item in report["items"]],
            ["HISTORY", "UNKNOWN"],
        )
        self.assertEqual(report["document_sha256"], document_hash_before)
        self.assertEqual(self.document_path.read_bytes(), document_before)
        self.assertEqual(self._input_members(), input_members_before)

    def test_archive_members_exclude_private_inputs_and_third_party_packages(
        self,
    ) -> None:
        self._build_archive()

        self.assertEqual(
            zipapp.get_interpreter(self.archive_path),
            "/usr/bin/env python3",
        )
        with ZipFile(self.archive_path) as archive:
            raw_members = tuple(archive.namelist())
            members = tuple(PurePosixPath(name) for name in archive.namelist())

        lowered = tuple(str(member).casefold() for member in members)
        self.assertEqual(set(raw_members), EXPECTED_ARCHIVE_MEMBERS)
        self.assertEqual(len(raw_members), len(EXPECTED_ARCHIVE_MEMBERS))
        path_parts = {
            part.casefold()
            for member in members
            for part in member.parts
        }
        top_level = {member.parts[0].casefold() for member in members}
        self.assertIn("citation_canary/__main__.py", lowered)
        self.assertEqual(top_level, {"citation_canary", "__main__.py", "license"})
        self.assertNotIn(self.document_path.name.casefold(), path_parts)
        self.assertFalse(any(name.endswith(".hwpx") for name in lowered))
        self.assertFalse(any(name.endswith(".json") for name in lowered))
        self.assertTrue(
            {"citation-corpus", "local-corpus"}.isdisjoint(path_parts)
        )
        self.assertTrue(
            {"site-packages", "vendor", "vendored"}.isdisjoint(path_parts)
        )

    def test_archive_contains_only_the_exact_source_allowlist_and_license(self) -> None:
        from tools.build_zipapp import METADATA_ALLOWLIST, SOURCE_ALLOWLIST

        self.assertEqual(SOURCE_ALLOWLIST, EXPECTED_SOURCE_ALLOWLIST)
        self.assertEqual(METADATA_ALLOWLIST, ("LICENSE",))
        self._build_archive()
        with ZipFile(self.archive_path) as archive:
            self.assertEqual(set(archive.namelist()), EXPECTED_ARCHIVE_MEMBERS)
            self.assertEqual(
                archive.read("LICENSE"),
                (REPOSITORY_ROOT / "LICENSE").read_bytes().replace(b"\r\n", b"\n"),
            )

    def test_archive_modules_scan_when_loaded_from_zip_path(self) -> None:
        self._build_archive()
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; from datetime import date; "
                    "sys.path.insert(0, sys.argv[1]); "
                    "from citation_canary.scanner import scan_document; "
                    "report = scan_document(sys.argv[2], date(2024, 12, 31), sys.argv[3]); "
                    "raise SystemExit(0 if len(report.items) == 2 and not report.collection_errors else 1)"
                ),
                str(self.archive_path),
                str(self.document_path),
                str(self.catalog_path),
            ],
            cwd=self.work_dir,
            env=self._environment_without_pythonpath(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"returncode={completed.returncode}; stderr={completed.stderr!r}; stdout={completed.stdout!r}",
        )

    def test_builder_supports_target_on_another_windows_volume(self) -> None:
        from tools.build_zipapp import build_zipapp

        if os.name != "nt":
            self.skipTest("cross-volume replacement is Windows-specific")
        source_anchor = Path.cwd().anchor.casefold()
        alternate_root = next(
            (
                Path(f"{drive}:\\")
                for drive in "DEFGHIJKLMNOPQRSTUVWXYZ"
                if f"{drive}:\\".casefold() != source_anchor
                and Path(f"{drive}:\\").is_dir()
            ),
            None,
        )
        if alternate_root is None:
            self.skipTest("no second filesystem volume is available")
        with tempfile.TemporaryDirectory(dir=str(alternate_root)) as directory:
            target = Path(directory) / "cross-volume.pyz"
            build_zipapp(SOURCE_ROOT, target)
            with ZipFile(target) as archive:
                self.assertEqual(set(archive.namelist()), EXPECTED_ARCHIVE_MEMBERS)

    def test_builder_is_byte_reproducible(self) -> None:
        from tools.build_zipapp import build_zipapp

        first = self.work_dir / "reproducible-first.pyz"
        second = self.work_dir / "reproducible-second.pyz"
        build_zipapp(SOURCE_ROOT, first)
        build_zipapp(SOURCE_ROOT, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_builder_normalizes_crlf_checkout_bytes(self) -> None:
        from tools.build_zipapp import build_zipapp

        with tempfile.TemporaryDirectory() as directory:
            crlf_source = Path(directory) / "src"
            shutil.copytree(SOURCE_ROOT, crlf_source)
            crlf_license = crlf_source.parent / "LICENSE"
            crlf_license.write_bytes(
                (REPOSITORY_ROOT / "LICENSE")
                .read_bytes()
                .replace(b"\r\n", b"\n")
                .replace(b"\n", b"\r\n")
            )
            for path in crlf_source.rglob("*.py"):
                path.write_bytes(
                    path.read_bytes().replace(b"\r\n", b"\n").replace(
                        b"\n", b"\r\n"
                    )
                )
            normal_archive = self.work_dir / "normal-newline.pyz"
            crlf_archive = self.work_dir / "crlf-checkout.pyz"
            build_zipapp(SOURCE_ROOT, normal_archive)
            build_zipapp(crlf_source, crlf_archive)
            self.assertEqual(normal_archive.read_bytes(), crlf_archive.read_bytes())

    def test_builder_missing_license_preserves_existing_target(self) -> None:
        from tools.build_zipapp import ZipappBuildError, build_zipapp

        with tempfile.TemporaryDirectory() as directory:
            copied_source = Path(directory) / "src"
            shutil.copytree(SOURCE_ROOT, copied_source)
            target = self.work_dir / "missing-license.pyz"
            target.write_bytes(b"preserve existing target")
            with self.assertRaises(ZipappBuildError):
                build_zipapp(copied_source, target)
            self.assertEqual(target.read_bytes(), b"preserve existing target")

    def test_builder_rejects_license_as_direct_output_without_mutation(self) -> None:
        self._assert_license_output_rejected(alias=False)

    def test_builder_rejects_license_as_alias_output_without_mutation(self) -> None:
        self._assert_license_output_rejected(alias=True)

    def _assert_license_output_rejected(self, *, alias: bool) -> None:
        from tools.build_zipapp import ZipappBuildError, build_zipapp

        with tempfile.TemporaryDirectory() as directory:
            copied_source = Path(directory) / "src"
            shutil.copytree(
                SOURCE_ROOT,
                copied_source,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
            copied_license = copied_source.parent / "LICENSE"
            license_bytes = b"synthetic test license\n"
            copied_license.write_bytes(license_bytes)
            source_bytes = {
                path.relative_to(copied_source): path.read_bytes()
                for path in copied_source.rglob("*.py")
            }
            target = copied_license
            if alias:
                alias_parent = copied_source.parent / "alias"
                alias_parent.mkdir()
                target = alias_parent / ".." / "LICENSE"

            with self.assertRaises(ZipappBuildError):
                build_zipapp(copied_source, target)
            self.assertEqual(copied_license.read_bytes(), license_bytes)
            self.assertEqual(
                {
                    path.relative_to(copied_source): path.read_bytes()
                    for path in copied_source.rglob("*.py")
                },
                source_bytes,
            )

    def test_builder_symlinked_license_preserves_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied_source = Path(directory) / "src"
            shutil.copytree(SOURCE_ROOT, copied_source)
            copied_license = copied_source.parent / "LICENSE"
            copied_license.write_bytes((REPOSITORY_ROOT / "LICENSE").read_bytes())
            alias = copied_source.parent / "alias"
            alias.mkdir()

            for label, source_spelling in (
                ("normal", copied_source),
                ("alias-parent", alias / ".." / copied_source.name),
            ):
                with self.subTest(case=label):
                    target = self.work_dir / f"symlinked-license-{label}.pyz"
                    self._assert_symlinked_license_rejected(
                        source_spelling,
                        target,
                    )

    def test_symlinked_license_regression_detects_removed_guard(self) -> None:
        import tools.build_zipapp as builder

        original = builder._copy_allowlisted_metadata
        original_source = inspect.getsource(original)
        guard = "if not source.is_file() or source.is_symlink():"
        self.assertEqual(original_source.count(guard), 1)
        mutant_source = original_source.replace(
            guard,
            "if not source.is_file():",
            1,
        )
        mutant_namespace = dict(vars(builder))
        exec(
            compile(
                mutant_source,
                "<metadata-symlink-guard-negative-control>",
                "exec",
            ),
            mutant_namespace,
        )
        mutant = mutant_namespace[original.__name__]

        with tempfile.TemporaryDirectory() as directory:
            copied_source = Path(directory) / "src"
            shutil.copytree(SOURCE_ROOT, copied_source)
            copied_license = copied_source.parent / "LICENSE"
            copied_license.write_bytes((REPOSITORY_ROOT / "LICENSE").read_bytes())
            alias = copied_source.parent / "alias"
            alias.mkdir()
            source_spelling = alias / ".." / copied_source.name
            target = self.work_dir / "missing-metadata-symlink-guard.pyz"

            with mock.patch.object(builder, original.__name__, mutant):
                with self.assertRaises(AssertionError) as failure:
                    self._assert_symlinked_license_rejected(
                        source_spelling,
                        target,
                    )

            self.assertIn("ZipappBuildError not raised", str(failure.exception))
            self.assertIs(builder._copy_allowlisted_metadata, original)

    def _assert_symlinked_license_rejected(
        self,
        source_spelling: Path,
        target: Path,
    ) -> None:
        import tools.build_zipapp as builder

        expected_license = (source_spelling.parent / "LICENSE").resolve()
        target.write_bytes(b"preserve existing target")
        real_is_symlink = Path.is_symlink
        with mock.patch.object(
            Path,
            "is_symlink",
            lambda path: path == expected_license or real_is_symlink(path),
        ):
            with self.assertRaises(builder.ZipappBuildError):
                builder.build_zipapp(source_spelling, target)
        self.assertEqual(target.read_bytes(), b"preserve existing target")

    def test_builder_rejects_metadata_staging_collision(self) -> None:
        from tools.build_zipapp import (
            ZipappBuildError,
            _copy_allowlisted_metadata,
        )

        metadata_root = self.work_dir / "metadata-root"
        staging_root = self.work_dir / "collision-staging"
        metadata_root.mkdir()
        staging_root.mkdir()
        (metadata_root / "LICENSE").write_bytes(b"canonical license\n")
        (staging_root / "LICENSE").write_bytes(b"collision\n")
        with self.assertRaises(ZipappBuildError):
            _copy_allowlisted_metadata(metadata_root, staging_root)

    def test_archive_has_no_cache_bytecode_or_absolute_source_metadata(self) -> None:
        self._build_archive()

        sensitive_roots = {
            str(REPOSITORY_ROOT.resolve()),
            str(SOURCE_ROOT.resolve()),
        }
        sensitive_spellings = {
            spelling
            for root in sensitive_roots
            for spelling in (root, root.replace("\\", "/"), root.replace("/", "\\"))
        }

        code_filenames: list[str] = []
        with ZipFile(self.archive_path) as archive:
            members = archive.infolist()
            for member in members:
                member_bytes = archive.read(member)
                for spelling in sensitive_spellings:
                    self.assertNotIn(spelling.encode("utf-8"), member_bytes)
                    self.assertNotIn(spelling.encode("utf-16-le"), member_bytes)
                if member.filename.casefold().endswith(".pyc"):
                    code = marshal.loads(member_bytes[16:])
                    code_filenames.extend(self._code_filenames(code))

        for filename in code_filenames:
            self.assertFalse(Path(filename).is_absolute(), filename)
        for member in members:
            lowered = member.filename.casefold()
            self.assertNotIn("__pycache__", lowered)
            self.assertFalse(lowered.endswith((".pyc", ".pyo")))

    def test_repository_builder_exists_for_allowlisted_staging_build(self) -> None:
        from tools.build_zipapp import build_zipapp

        alternate_archive = self.work_dir / "allowlisted-build.pyz"
        build_zipapp(SOURCE_ROOT, alternate_archive)

        with ZipFile(alternate_archive) as archive:
            self.assertEqual(set(archive.namelist()), EXPECTED_ARCHIVE_MEMBERS)

    def test_archive_preserves_safe_invalid_request_exit_code(self) -> None:
        self._build_archive()

        completed = subprocess.run(
            [
                sys.executable,
                str(self.archive_path),
                "--document",
                str(self.document_path),
                "--as-of",
                "2024-02-30",
                "--catalog",
                str(self.catalog_path),
            ],
            cwd=self.work_dir,
            env=self._environment_without_pythonpath(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(
            completed.stderr,
            "Invalid --as-of date. Expected YYYY-MM-DD.\n",
        )
        self.assertNotIn("Traceback", completed.stderr)
        self.assertNotIn(str(self.document_path), completed.stderr)

    def test_archive_collection_error_emits_report_and_exits_one(self) -> None:
        self._build_archive()
        self.document_path.write_bytes(b"not a zip archive")

        completed = self._run_archive(
            "--document",
            str(self.document_path),
            "--as-of",
            AS_OF,
            "--catalog",
            str(self.catalog_path),
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "")
        report = json.loads(completed.stdout)
        self.assertEqual(report["items"], [])
        self.assertEqual(
            [error["code"] for error in report["collection_errors"]],
            ["DOCUMENT_NOT_ZIP"],
        )
        self.assertNotIn(self.document_path.name, completed.stdout)

    def test_archive_unexpected_output_failure_is_generic_exit_one(self) -> None:
        self._build_archive()
        missing_output = self.work_dir / "missing-private-parent" / "report.json"

        completed = self._run_archive(
            "--document",
            str(self.document_path),
            "--as-of",
            AS_OF,
            "--catalog",
            str(self.catalog_path),
            "--output",
            str(missing_output),
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "UNEXPECTED_ERROR\n")
        self.assertNotIn(str(missing_output), completed.stderr)

    def test_archive_argparse_errors_are_generic_and_do_not_echo_paths(self) -> None:
        self._build_archive()
        sentinel_path = str(
            (self.work_dir / "private-operator-path-do-not-echo").resolve()
        )
        cases = (
            ("missing", ("--document", sentinel_path)),
            (
                "unknown",
                (
                    "--document",
                    str(self.document_path),
                    "--as-of",
                    AS_OF,
                    "--catalog",
                    str(self.catalog_path),
                    "--unexpected-option",
                    sentinel_path,
                ),
            ),
        )

        for label, arguments in cases:
            with self.subTest(case=label):
                completed = self._run_archive(*arguments)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertEqual(completed.stderr, "ARGUMENT_ERROR\n")
                self.assertNotIn(sentinel_path, completed.stderr)

    def _build_archive(self) -> None:
        from tools.build_zipapp import build_zipapp

        build_zipapp(SOURCE_ROOT, self.archive_path)

    def _run_archive(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.archive_path), *arguments],
            cwd=self.work_dir,
            env=self._environment_without_pythonpath(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    @classmethod
    def _code_filenames(cls, code: types.CodeType) -> tuple[str, ...]:
        filenames = [code.co_filename]
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                filenames.extend(cls._code_filenames(constant))
        return tuple(filenames)

    def _input_members(self) -> tuple[str, ...]:
        return tuple(sorted(path.name for path in self.input_dir.iterdir()))

    @staticmethod
    def _environment_without_pythonpath() -> dict[str, str]:
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        # Exercise the legacy Windows pipe encoding that previously hid a
        # valid Korean report behind UNEXPECTED_ERROR.
        environment["PYTHONIOENCODING"] = "cp1252"
        return environment


if __name__ == "__main__":
    unittest.main()
