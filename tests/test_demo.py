from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools.build_zipapp import build_zipapp


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2024-12-31"
EXPECTED_STATUSES = ["CURRENT", "HISTORY", "REVIEW", "UNKNOWN"]
EXPECTED_DEMO_FILES = {"synthetic-review.hwpx", "catalog.json", "README.txt"}


class PackagedDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Retain artifacts and failed inputs for independent review.
        cls.work_dir = Path(tempfile.mkdtemp(prefix="citation-demo-regression-"))
        cls.archive_path = cls.work_dir / "citation-canary-0.2.0.pyz"
        build_zipapp(REPOSITORY_ROOT / "src", cls.archive_path)
        cls.environment = os.environ.copy()
        cls.environment.pop("PYTHONPATH", None)
        cls.environment["PYTHONIOENCODING"] = "cp1252"
        cls.environment["PYTHONDONTWRITEBYTECODE"] = "1"

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, "-B", str(self.archive_path), *arguments],
            cwd=self.work_dir,
            env=self.environment,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def _generate(self, name: str) -> Path:
        destination = self.work_dir / name
        completed = self._run("--demo", str(destination))
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b"")
        return destination

    @staticmethod
    def _snapshot(directory: Path) -> dict[str, bytes]:
        return {
            path.name: path.read_bytes()
            for path in directory.iterdir()
            if path.is_file()
        }

    def _assert_rejected(
        self, completed: subprocess.CompletedProcess[bytes], token: bytes,
    ) -> None:
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, b"")
        self.assertEqual(completed.stderr.replace(b"\r\n", b"\n"), token + b"\n")

    def test_pyz_alone_generates_a_runnable_four_status_demo(self) -> None:
        demo_dir = self.work_dir / "synthetic demo"
        generated = self._run("--demo", str(demo_dir))
        self.assertEqual(
            generated.returncode,
            0,
            "Packaged --demo must succeed without repository fixtures; "
            f"observed native exit {generated.returncode}.",
        )
        self.assertEqual(generated.stderr, b"")
        manifest = json.loads(generated.stdout.decode("utf-8"))
        self.assertEqual(
            manifest,
            {
                "schema_version": "1",
                "notice": "SYNTHETIC_DEMO_ONLY",
                "as_of": AS_OF,
                "document": "synthetic-review.hwpx",
                "catalog": "catalog.json",
                "readme": "README.txt",
                "expected_statuses": EXPECTED_STATUSES,
            },
        )
        self.assertEqual({path.name for path in demo_dir.iterdir()}, EXPECTED_DEMO_FILES)
        self.assertIn("SYNTHETIC_DEMO_ONLY", (demo_dir / "README.txt").read_text("utf-8"))
        catalog = json.loads((demo_dir / "catalog.json").read_text("utf-8"))
        self.assertTrue(catalog["records"])
        self.assertTrue(
            all(
                record["official_source"]["url"].startswith("https://example.invalid/")
                for record in catalog["records"]
            )
        )
        input_hashes = {
            name: hashlib.sha256((demo_dir / name).read_bytes()).hexdigest()
            for name in EXPECTED_DEMO_FILES
        }

        scanned = self._run(
            "--document", str(demo_dir / "synthetic-review.hwpx"),
            "--as-of", AS_OF,
            "--catalog", str(demo_dir / "catalog.json"),
        )
        self.assertEqual(scanned.returncode, 0, "Generated pair must scan successfully.")
        self.assertEqual(scanned.stderr, b"")
        report = json.loads(scanned.stdout.decode("utf-8"))
        self.assertEqual(report["collection_errors"], [])
        self.assertEqual([item["status"] for item in report["items"]], EXPECTED_STATUSES)
        self.assertEqual(
            [item["reason_code"] for item in report["items"]],
            ["EXACT_CURRENT_MATCH", "EXACT_HISTORICAL_MATCH", "PROVISION_MISMATCH", "AMBIGUOUS_CITATION"],
        )
        self.assertEqual(report["as_of"], AS_OF)
        self.assertEqual(report["document_sha256"], input_hashes["synthetic-review.hwpx"])
        self.assertEqual(report["catalog_sha256"], input_hashes["catalog.json"])
        self.assertRegex(report["document_name"], r"^document-[0-9a-f]{12}\.hwpx$")
        self.assertNotIn("synthetic-review.hwpx", scanned.stdout.decode("utf-8"))
        self.assertEqual(
            {name: hashlib.sha256((demo_dir / name).read_bytes()).hexdigest() for name in EXPECTED_DEMO_FILES},
            input_hashes,
        )
        self.assertEqual({path.name for path in demo_dir.iterdir()}, EXPECTED_DEMO_FILES)

    def test_destination_reuse_and_unsafe_paths_preserve_existing_files(self) -> None:
        demo_dir = self._generate("collision-demo")
        empty_dir = self.work_dir / "existing-empty"
        empty_dir.mkdir()
        before = self._snapshot(demo_dir)
        cases = (
            demo_dir, empty_dir, demo_dir / "synthetic-review.hwpx",
            demo_dir / "catalog.json", self.work_dir / "missing" / "child",
            demo_dir / "catalog.json" / "child",
            self.work_dir / "unused" / ".." / "unsafe-demo",
        )
        for destination in cases:
            with self.subTest(case=destination.name):
                self._assert_rejected(
                    self._run("--demo", str(destination)), b"DEMO_DESTINATION_INVALID",
                )
                self.assertEqual(self._snapshot(demo_dir), before)
        self.assertEqual(tuple(empty_dir.iterdir()), ())
        self.assertFalse((self.work_dir / "missing").exists())
        self.assertFalse((self.work_dir / "unsafe-demo").exists())

    def test_regular_file_parent_is_an_invalid_demo_destination(self) -> None:
        from citation_canary.__main__ import main

        parent = self.work_dir / "regular-file-parent"
        parent.write_bytes(b"keep synthetic input unchanged")
        destination = parent / "new-demo"
        real_lstat = Path.lstat

        def lstat_with_not_directory(path: Path):
            if path == destination:
                raise NotADirectoryError
            return real_lstat(path)

        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.object(Path, "lstat", lstat_with_not_directory),
            redirect_stdout(stdout), redirect_stderr(stderr),
        ):
            exit_code = main(["--demo", str(destination)])
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue().replace("\r\n", "\n"), "DEMO_DESTINATION_INVALID\n")
        self.assertEqual(parent.read_bytes(), b"keep synthetic input unchanged")

    def test_demo_and_scan_arguments_are_exclusive_before_writes(self) -> None:
        destination = self.work_dir / "mixed-mode"
        for option in ("--document", "--as-of", "--catalog", "--output"):
            with self.subTest(option=option):
                self._assert_rejected(
                    self._run("--demo", str(destination), option, "private-value"),
                    b"ARGUMENT_ERROR",
                )
                self.assertFalse(destination.exists())

    def test_unicode_paths_stdout_file_output_and_input_collisions(self) -> None:
        demo_dir = self._generate("가상 검토 (demo)")
        document = demo_dir / "synthetic-review.hwpx"
        catalog = demo_dir / "catalog.json"
        output = self.work_dir / "보고서.json"
        before = self._snapshot(demo_dir)
        arguments = (
            "--document", str(document), "--as-of", AS_OF, "--catalog", str(catalog),
        )
        stdout_run = self._run(*arguments)
        file_run = self._run(*arguments, "--output", str(output))
        self.assertEqual(stdout_run.returncode, 0)
        self.assertEqual(file_run.returncode, 0)
        self.assertEqual(stdout_run.stderr, b"")
        self.assertEqual(file_run.stderr, b"")
        self.assertEqual(file_run.stdout, b"")
        report = json.loads(stdout_run.stdout.decode("utf-8"))
        self.assertEqual([item["status"] for item in report["items"]], EXPECTED_STATUSES)
        self.assertEqual(report, json.loads(output.read_text("utf-8")))
        for input_path in (document, catalog):
            self._assert_rejected(
                self._run(*arguments, "--output", str(input_path)),
                b"Output path must differ from document and catalog.",
            )
        self.assertEqual(self._snapshot(demo_dir), before)

    def test_symlink_ancestors_and_dangling_destinations_are_rejected(self) -> None:
        outside = self.work_dir / "link-target"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_bytes(b"unchanged synthetic sentinel")
        linked = self.work_dir / "linked-parent"
        dangling = self.work_dir / "dangling-destination"
        try:
            linked.symlink_to(outside, target_is_directory=True)
            dangling.symlink_to(self.work_dir / "absent-target", target_is_directory=True)
        except OSError:
            self.skipTest("Host does not permit creating symbolic links.")
        before = self._snapshot(outside)
        for destination in (linked / "child", dangling):
            self._assert_rejected(
                self._run("--demo", str(destination)), b"DEMO_DESTINATION_INVALID",
            )
        self.assertEqual(self._snapshot(outside), before)
        self.assertFalse((outside / "child").exists())

    def test_help_describes_generation_scan_date_and_catalog_guide(self) -> None:
        completed = self._run("--help")
        self.assertEqual(completed.returncode, 0)
        text = completed.stdout.decode("utf-8")
        for marker in ("--demo", "2024-12-31", "catalog-schema-v1.md", "generate", "scan"):
            self.assertIn(marker, text)
        self.assertEqual(completed.stderr, b"")

    def test_partial_creation_failure_is_retained_and_cli_error_is_safe(self) -> None:
        from citation_canary.demo import create_demo
        from citation_canary.__main__ import main

        destination = self.work_dir / "partial-failure"
        real_open = Path.open

        def fail_catalog(path: Path, *args: object, **kwargs: object):
            if path.name == "catalog.json":
                raise OSError("private path must not appear in safe errors")
            return real_open(path, *args, **kwargs)

        with patch.object(Path, "open", fail_catalog):
            with self.assertRaises(OSError):
                create_demo(destination)
        self.assertEqual({path.name for path in destination.iterdir()}, {"synthetic-review.hwpx"})
        self.assertGreater((destination / "synthetic-review.hwpx").stat().st_size, 0)
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch("citation_canary.__main__.create_demo", side_effect=OSError("private value")),
            redirect_stdout(stdout), redirect_stderr(stderr),
        ):
            exit_code = main(["--demo", str(self.work_dir / "other-failure")])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue().replace("\r\n", "\n"), "DEMO_CREATE_FAILED\n")

    def test_catalog_guide_example_and_generated_readme_match_the_package(self) -> None:
        demo_dir = self._generate("documented-example")
        guide = (REPOSITORY_ROOT / "docs/catalog-schema-v1.md").read_text("utf-8")
        example = guide.split("```json\n", 1)[1].split("```", 1)[0]
        self.assertEqual(
            json.loads(example),
            json.loads((demo_dir / "catalog.json").read_text("utf-8")),
        )
        readme = (demo_dir / "README.txt").read_text("utf-8")
        self.assertTrue(readme.startswith("SYNTHETIC_DEMO_ONLY\n"))
        for required in (
            "citation-canary-0.2.0.pyz", "--as-of 2024-12-31",
            "--output", "example.invalid", "CURRENT, HISTORY, REVIEW, UNKNOWN",
        ):
            self.assertIn(required, readme)
        self.assertNotIn("citation-canary-0.1.0.pyz", readme)


if __name__ == "__main__":
    unittest.main()
