from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Sequence

from .demo import DemoDestinationError, create_demo
from .report import ScanRequestError
from .scanner import scan_document
from .review import update_ledger


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "ARGUMENT_ERROR\n")


def _parse_as_of(value: str) -> date | None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    if parsed.isoformat() != value:
        return None
    return parsed


def _write_atomic(output_path: Path, payload: str) -> None:
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _write_stdout(payload: str) -> None:
    """Emit JSON as UTF-8 even when a Windows pipe uses a legacy code page."""
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(payload.encode("utf-8"))
        buffer.flush()
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    except (AttributeError, OSError):
        pass
    sys.stdout.write(payload)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'review':
        review_parser = _SafeArgumentParser(prog='citation-canary review', allow_abbrev=False)
        review_parser.add_argument('--report', required=True)
        review_parser.add_argument('--ledger', required=True)
        review_parser.add_argument('--action', required=True, choices=('decide', 'start', 'finish'))
        review_parser.add_argument('--item', type=int)
        review_parser.add_argument('--disposition', choices=('confirm', 'reject', 'investigate', 'defer'))
        review_parser.add_argument('--stage', choices=('triage', 'evidence', 'decision'))
        tokens = argv[1:]
        flags = [token.split('=', 1)[0] for token in tokens if token.startswith('--')]
        if any(flags.count(flag) != 1 for flag in ('--report', '--ledger', '--action')) or \
                any(flags.count(flag) > 1 for flag in ('--item', '--disposition', '--stage')):
            print('ARGUMENT_ERROR', file=sys.stderr)
            return 2
        try:
            review_args = review_parser.parse_args(tokens)
        except SystemExit as error:
            return int(error.code)
        if review_args.action == 'decide':
            valid = review_args.item is not None and review_args.disposition is not None and review_args.stage is None
        else:
            valid = review_args.item is None and review_args.disposition is None and review_args.stage is not None
        if not valid:
            print('ARGUMENT_ERROR', file=sys.stderr)
            return 2
        try:
            update_ledger(Path(review_args.ledger), Path(review_args.report),
                          action=review_args.action, item_number=review_args.item,
                          disposition=review_args.disposition, stage=review_args.stage)
            return 0
        except ScanRequestError as error:
            print(error.code, file=sys.stderr)
            return 1 if error.code == 'REVIEW_WRITE_FAILED' else 2
        except Exception:
            print('REVIEW_WRITE_FAILED', file=sys.stderr)
            return 1
    parser = _SafeArgumentParser(
        prog="citation-canary",
        allow_abbrev=False,
        description="Offline citation review with explicit local synthetic setup.",
        epilog=(
            "First generate: --demo NEW_DIRECTORY. Then scan the generated "
            "synthetic-review.hwpx and catalog.json with --as-of 2024-12-31. "
            "The demo is fictional and does not establish legal facts. "
            "Catalog guide: https://github.com/nowwcastle-sudo/citation-canary/"
            "blob/v0.2.0-experimental.1/docs/catalog-schema-v1.md"
        ),
    )
    parser.add_argument("--demo", metavar="NEW_DIRECTORY", help="generate synthetic inputs in a new directory; separate from scan")
    parser.add_argument("--document", help="local HWPX to scan (required for scan)")
    parser.add_argument("--as-of", help="explicit YYYY-MM-DD review date (required for scan)")
    parser.add_argument("--catalog", help="local UTF-8 schema-v1 catalog (required for scan)")
    parser.add_argument("--output", help="separate UTF-8 JSON output file; otherwise stdout")
    args = parser.parse_args(argv)

    if args.demo is not None:
        if any(value is not None for value in (args.document, args.as_of, args.catalog, args.output)):
            parser.error("demo and scan arguments cannot be combined")
    elif any(value is None for value in (args.document, args.as_of, args.catalog)):
        parser.error("scan requires document, as-of and catalog")

    try:
        if args.demo is not None:
            try:
                manifest = create_demo(Path(args.demo))
            except DemoDestinationError:
                print("DEMO_DESTINATION_INVALID", file=sys.stderr)
                return 2
            except OSError:
                print("DEMO_CREATE_FAILED", file=sys.stderr)
                return 1
            _write_stdout(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            return 0

        as_of = _parse_as_of(args.as_of)
        if as_of is None:
            print(
                "Invalid --as-of date. Expected YYYY-MM-DD.",
                file=sys.stderr,
            )
            return 2

        output_path: Path | None = None
        if args.output is not None:
            output_path = Path(args.output).resolve()
            input_paths = {
                Path(args.document).resolve(),
                Path(args.catalog).resolve(),
            }
            if output_path in input_paths:
                print(
                    "Output path must differ from document and catalog.",
                    file=sys.stderr,
                )
                return 2

        report = scan_document(args.document, as_of, args.catalog)
        payload = (
            json.dumps(
                report.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        )

        if output_path is None:
            _write_stdout(payload)
        else:
            _write_atomic(output_path, payload)
        return 1 if report.collection_errors else 0
    except ScanRequestError as error:
        print(error.safe_message, file=sys.stderr)
        return 2
    except Exception:
        print("UNEXPECTED_ERROR", file=sys.stderr)
        return 1


def _run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    _run()
