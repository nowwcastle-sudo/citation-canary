"""Explicit local setup for fictional, package-only onboarding inputs."""

from __future__ import annotations

import json
import stat
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile


DEMO_AS_OF = "2024-12-31"
DEMO_FILENAMES = ("synthetic-review.hwpx", "catalog.json", "README.txt")
_TEXTS = (
    "가상현행규정 제1조에 따른다.",
    "가상행정규칙 제7조에 따른다.",
    "가상현행규정 제99조를 검토한다.",
    "관계 규정에 따른다.",
)
_CATALOG = {
    "schema_version": "1",
    "records": [
        {
            "record_id": "synthetic-current-001",
            "official_source": {
                "url": "https://example.invalid/official-source/synthetic-current-001",
                "retrieved_at": "2026-09-04T00:00:00+09:00",
            },
            "versions": [
                {
                    "effective_from": "2020-01-01",
                    "effective_to": None,
                    "title": "가상현행규정",
                    "provisions": [{"canonical_id": "article-1", "label": "제1조"}],
                },
            ],
        },
        {
            "record_id": "synthetic-history-001",
            "official_source": {
                "url": "https://example.invalid/official-source/synthetic-history-001",
                "retrieved_at": "2026-09-04T00:00:00+09:00",
            },
            "versions": [
                {
                    "effective_from": "2020-01-01",
                    "effective_to": "2025-02-01",
                    "title": "가상행정규칙",
                    "provisions": [{"canonical_id": "article-7", "label": "제7조"}],
                },
                {
                    "effective_from": "2025-02-01",
                    "effective_to": None,
                    "title": "가상업무규정",
                    "provisions": [{"canonical_id": "article-7", "label": "제9조"}],
                },
            ],
        },
    ],
}
_README = """SYNTHETIC_DEMO_ONLY

This is fictional learning data, not an institutional document or legal source.
All titles, dates and example.invalid URLs are synthetic. No URL is fetched.
The minimal HWPX demonstrates the scanner; it is not an editable Hancom form.

Run these separate commands in PowerShell from the folder containing your
verified citation-canary-0.2.0-experimental.2.pyz. They assume the documented --demo directory
is .\\citation-demo; substitute your chosen demo directory if different.

python .\\citation-canary-0.2.0-experimental.2.pyz --document .\\citation-demo\\synthetic-review.hwpx --as-of 2024-12-31 --catalog .\\citation-demo\\catalog.json
python .\\citation-canary-0.2.0-experimental.2.pyz --document .\\citation-demo\\synthetic-review.hwpx --as-of 2024-12-31 --catalog .\\citation-demo\\catalog.json --output .\\citation-report.json

Expected ordered statuses: CURRENT, HISTORY, REVIEW, UNKNOWN.
These route human review; none is a legal decision or an instruction to edit.
The review date is exactly 2024-12-31. Ordinary scanning preserves source bytes.
See docs/catalog-schema-v1.md in the public repository for the input contract.

Demo setup writes only explicitly requested synthetic files. Do not reuse a
demo destination. If setup fails, keep its partial files for inspection and
choose a different new directory; the tool does not remove or overwrite them.
Keep generated reports separate and never attach a real HWPX/catalog/report
body to a support issue.
"""


class DemoDestinationError(ValueError):
    """The requested local demo directory is not a safe new destination."""


def _claim_destination(destination: Path) -> Path:
    if ".." in destination.parts:
        raise DemoDestinationError
    destination = destination.absolute()
    # Reject network/extended UNC forms before touching their filesystem.
    if destination.drive.startswith("\\\\"):
        raise DemoDestinationError
    for path in (destination, *destination.parents):
        try:
            metadata = path.lstat()
        except (FileNotFoundError, NotADirectoryError):
            if path == destination:
                continue
            raise DemoDestinationError from None
        reparse = getattr(metadata, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0,
        )
        if path == destination or stat.S_ISLNK(metadata.st_mode) or reparse:
            raise DemoDestinationError
        if not stat.S_ISDIR(metadata.st_mode):
            raise DemoDestinationError
    try:
        destination.mkdir(parents=False, exist_ok=False)
    except (FileExistsError, FileNotFoundError, NotADirectoryError):
        raise DemoDestinationError from None
    return destination


def create_demo(destination: Path) -> dict[str, object]:
    """Exclusively create fictional inputs; preserve partial creation failures."""
    namespace = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    section = ElementTree.Element(f"{{{namespace}}}section")
    for text in _TEXTS:
        ElementTree.SubElement(section, f"{{{namespace}}}t").text = text
    xml_bytes = ElementTree.tostring(section, encoding="utf-8", xml_declaration=True)
    destination = _claim_destination(Path(destination))
    with (destination / DEMO_FILENAMES[0]).open("xb") as handle:
        with ZipFile(handle, mode="w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("mimetype", b"application/hwp+zip")
            archive.writestr("Contents/section0.xml", xml_bytes)
    with (destination / DEMO_FILENAMES[1]).open(
        "x", encoding="utf-8", newline="\n",
    ) as handle:
        handle.write(json.dumps(_CATALOG, ensure_ascii=False, indent=2) + "\n")
    with (destination / DEMO_FILENAMES[2]).open(
        "x", encoding="utf-8", newline="\n",
    ) as handle:
        handle.write(_README)
    return {
        "schema_version": "1",
        "notice": "SYNTHETIC_DEMO_ONLY",
        "as_of": DEMO_AS_OF,
        "document": DEMO_FILENAMES[0],
        "catalog": DEMO_FILENAMES[1],
        "readme": DEMO_FILENAMES[2],
        "expected_statuses": ["CURRENT", "HISTORY", "REVIEW", "UNKNOWN"],
    }
