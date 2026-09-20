from __future__ import annotations

import io
import json
import os
import socket
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

from citation_canary import CollectionError, ScanReport, ScanRequestError
from citation_canary.__main__ import main

from tests.support import write_catalog, write_synthetic_hwpx


AS_OF = date(2024, 12, 31)


class CitationCanaryCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name)
        self.document_path = self.work_dir / "synthetic-review.hwpx"
        self.catalog_path = self.work_dir / "catalog.json"
        write_synthetic_hwpx(self.document_path)
        write_catalog(self.catalog_path)

    def test_successful_scan_writes_deterministic_json_to_stdout(self) -> None:
        expected_report = self._report(document_name="검토문서.hwpx")
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch(
                "citation_canary.__main__.scan_document",
                return_value=expected_report,
            ) as scanner,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main(self._args())

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected_report.to_dict())
        self.assertEqual(
            stdout.getvalue(),
            json.dumps(
                expected_report.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
        )
        self.assertEqual(stderr.getvalue(), "")
        scanner.assert_called_once_with(
            str(self.document_path),
            AS_OF,
            str(self.catalog_path),
        )

    def test_explicit_output_is_utf8_atomic_and_silent(self) -> None:
        expected_report = self._report(document_name="검토문서.hwpx")
        output_path = self.work_dir / "report.json"
        before_names = {path.name for path in self.work_dir.iterdir()}
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch(
                "citation_canary.__main__.scan_document",
                return_value=expected_report,
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main(self._args("--output", str(output_path)))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            output_path.read_text(encoding="utf-8"),
            json.dumps(
                expected_report.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
        )
        self.assertEqual(
            {path.name for path in self.work_dir.iterdir()},
            before_names | {output_path.name},
        )

    def test_failed_atomic_replace_preserves_existing_output_and_cleans_temp(self) -> None:
        output_path = self.work_dir / "report.json"
        output_path.write_text("existing report\n", encoding="utf-8")
        before_names = {path.name for path in self.work_dir.iterdir()}
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch(
                "citation_canary.__main__.scan_document",
                return_value=self._report(),
            ),
            patch(
                "citation_canary.__main__.os.replace",
                side_effect=RuntimeError("replace failed at a sensitive path"),
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main(self._args("--output", str(output_path)))

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "UNEXPECTED_ERROR\n")
        self.assertEqual(output_path.read_text(encoding="utf-8"), "existing report\n")
        self.assertEqual(
            {path.name for path in self.work_dir.iterdir()},
            before_names,
        )

    def test_control_flow_interrupts_propagate_and_clean_atomic_temp(self) -> None:
        control_flows = (
            ("keyboard_interrupt", KeyboardInterrupt()),
            ("system_exit", SystemExit(17)),
        )

        for label, control_flow in control_flows:
            with self.subTest(control_flow=label):
                case_dir = self.work_dir / label
                case_dir.mkdir()
                output_path = case_dir / "report.json"
                output_path.write_text("existing report\n", encoding="utf-8")
                stdout = io.StringIO()
                stderr = io.StringIO()

                with (
                    patch(
                        "citation_canary.__main__.scan_document",
                        return_value=self._report(),
                    ),
                    patch(
                        "citation_canary.__main__.os.replace",
                        side_effect=control_flow,
                    ),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    with self.assertRaises(type(control_flow)) as raised:
                        main(self._args("--output", str(output_path)))

                self.assertIs(raised.exception, control_flow)
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(stderr.getvalue(), "")
                self.assertEqual(
                    output_path.read_text(encoding="utf-8"),
                    "existing report\n",
                )
                self.assertEqual(
                    sorted(path.name for path in case_dir.iterdir()),
                    [output_path.name],
                )

    def test_missing_required_arguments_use_generic_non_echoing_exit_two(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        sentinel_path = str(
            (self.work_dir / "private-operator-input-do-not-echo.hwpx").resolve()
        )

        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                main(["--document", sentinel_path])

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "ARGUMENT_ERROR\n")
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertNotIn(sentinel_path, stderr.getvalue())

    def test_unknown_argument_uses_generic_non_echoing_exit_two(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        sentinel_path = str(
            (self.work_dir / "private-operator-option-do-not-echo").resolve()
        )

        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                main(self._args("--unexpected-option", sentinel_path))

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "ARGUMENT_ERROR\n")
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertNotIn(sentinel_path, stderr.getvalue())

    def test_output_resolving_to_document_is_rejected_without_mutation(self) -> None:
        before = self.document_path.read_bytes()
        stdout = io.StringIO()
        stderr = io.StringIO()
        equivalent_output = self.work_dir / "unused" / ".." / self.document_path.name

        with (
            patch("citation_canary.__main__.scan_document") as scanner,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main(self._args("--output", str(equivalent_output)))

        self.assertEqual(exit_code, 2)
        self.assertEqual(self.document_path.read_bytes(), before)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn(str(self.document_path.resolve()), stderr.getvalue())
        scanner.assert_not_called()

    def test_output_resolving_to_catalog_is_rejected_without_mutation(self) -> None:
        before = self.catalog_path.read_bytes()
        stdout = io.StringIO()
        stderr = io.StringIO()
        equivalent_output = self.work_dir / "unused" / ".." / self.catalog_path.name

        with (
            patch("citation_canary.__main__.scan_document") as scanner,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main(self._args("--output", str(equivalent_output)))

        self.assertEqual(exit_code, 2)
        self.assertEqual(self.catalog_path.read_bytes(), before)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn(str(self.catalog_path.resolve()), stderr.getvalue())
        scanner.assert_not_called()

    def test_non_strict_or_invalid_date_is_an_argument_error(self) -> None:
        invalid_values = ("2024-2-01", "2024-02-30", "2024-12-31T00:00:00")

        for value in invalid_values:
            with self.subTest(value=value):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with (
                    patch("citation_canary.__main__.scan_document") as scanner,
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    exit_code = main(self._args(as_of=value))

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(
                    stderr.getvalue(),
                    "Invalid --as-of date. Expected YYYY-MM-DD.\n",
                )
                scanner.assert_not_called()

    def test_scan_request_error_has_only_its_safe_message(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        safe_message = "Document file was not found."

        with (
            patch(
                "citation_canary.__main__.scan_document",
                side_effect=ScanRequestError("DOCUMENT_NOT_FOUND", safe_message),
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main(self._args())

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), safe_message + "\n")

    def test_report_with_collection_errors_is_emitted_and_exits_one(self) -> None:
        expected_report = self._report(
            collection_errors=(
                CollectionError(
                    code="DOCUMENT_NOT_ZIP",
                    stage="parse",
                    fatal=True,
                    locator="synthetic-review.hwpx",
                    message="Document is not a ZIP archive.",
                ),
            )
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch(
                "citation_canary.__main__.scan_document",
                return_value=expected_report,
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main(self._args())

        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(stdout.getvalue()), expected_report.to_dict())
        self.assertEqual(stderr.getvalue(), "")

    def test_unexpected_failure_is_generic_without_traceback_or_path(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        sensitive_path = str(self.document_path.resolve())

        with (
            patch(
                "citation_canary.__main__.scan_document",
                side_effect=RuntimeError(f"failed at {sensitive_path}"),
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main(self._args())

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "UNEXPECTED_ERROR\n")
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertNotIn(sensitive_path, stderr.getvalue())

    def test_real_scan_remains_offline(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("The CLI must not access the network."),
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main(self._args())

        self.assertEqual(exit_code, 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual(
            [item["status"] for item in report["items"]],
            ["HISTORY", "UNKNOWN"],
        )
        self.assertEqual(stderr.getvalue(), "")

    def _args(self, *extra: str, as_of: str = "2024-12-31") -> list[str]:
        return [
            "--document",
            str(self.document_path),
            "--as-of",
            as_of,
            "--catalog",
            str(self.catalog_path),
            *extra,
        ]

    @staticmethod
    def _report(
        *,
        document_name: str = "synthetic-review.hwpx",
        collection_errors: tuple[CollectionError, ...] = (),
    ) -> ScanReport:
        return ScanReport(
            schema_version="1",
            document_name=document_name,
            document_sha256="a" * 64,
            as_of="2024-12-31",
            catalog_sha256="b" * 64,
            items=(),
            collection_errors=collection_errors,
        )


if __name__ == "__main__":
    unittest.main()
