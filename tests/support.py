from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile


SECTION_PATH = "Contents/section0.xml"


def write_hwpx(path: Path, texts: tuple[str, ...]) -> None:
    namespace = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    ElementTree.register_namespace("hp", namespace)
    section = ElementTree.Element(f"{{{namespace}}}section")
    for text in texts:
        node = ElementTree.SubElement(section, f"{{{namespace}}}t")
        node.text = text

    xml_bytes = ElementTree.tostring(
        section,
        encoding="utf-8",
        xml_declaration=True,
    )
    with ZipFile(path, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/hwp+zip")
        archive.writestr(SECTION_PATH, xml_bytes)


def write_synthetic_hwpx(path: Path) -> None:
    """Write two XML text nodes: one historical citation, one ambiguity."""
    write_hwpx(
        path,
        (
            "가상행정규칙 제7조에 따른다.",
            "관계 규정에 따른다.",
        ),
    )


def write_catalog(path: Path, *, conflict: bool = False) -> None:
    """Write UTF-8 schema-v1 JSON with one record and two dated versions."""
    versions = [
        {
            "effective_from": "2020-01-01",
            "effective_to": "2025-02-01",
            "title": "가상행정규칙",
            "provisions": [
                {"canonical_id": "article-7", "label": "제7조"},
            ],
        },
        {
            "effective_from": "2025-02-01",
            "effective_to": None,
            "title": "가상업무규정",
            "provisions": [
                {"canonical_id": "article-7", "label": "제9조"},
            ],
        },
    ]
    records = [
        {
            "record_id": "synthetic-rule-001",
            "official_source": {
                "url": "https://example.invalid/official-source/synthetic-rule-001",
                "retrieved_at": "2026-09-04T00:00:00+09:00",
            },
            "versions": versions,
        },
    ]
    if conflict:
        records.append(
            {
                "record_id": "synthetic-rule-002",
                "official_source": {
                    "url": "https://example.invalid/official-source/synthetic-rule-002",
                    "retrieved_at": "2026-09-04T01:00:00+09:00",
                },
                "versions": versions,
            }
        )

    path.write_text(
        json.dumps(
            {"schema_version": "1", "records": records},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_provision_conflict_catalog(path: Path) -> None:
    """Write two as-of title matches where only one provision matches."""
    write_catalog(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    value["records"].append(
        {
            "record_id": "synthetic-rule-002",
            "official_source": {
                "url": "https://example.invalid/official-source/synthetic-rule-002",
                "retrieved_at": "2026-09-04T01:00:00+09:00",
            },
            "versions": [
                {
                    "effective_from": "2020-01-01",
                    "effective_to": "2025-02-01",
                    "title": "가상행정규칙",
                    "provisions": [
                        {"canonical_id": "article-8", "label": "제8조"},
                    ],
                },
                {
                    "effective_from": "2025-02-01",
                    "effective_to": None,
                    "title": "가상별도규정",
                    "provisions": [
                        {"canonical_id": "article-8", "label": "제10조"},
                    ],
                },
            ],
        }
    )
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
