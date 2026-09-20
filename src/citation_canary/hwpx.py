from __future__ import annotations

import hashlib
import re
import zlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile, ZipInfo

from .report import CollectionError


MAX_COMPRESSED_BYTES = 100 * 1024 * 1024
MAX_ENTRIES = 10_000
MAX_SECTION_BYTES = 20 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_SECTION_SUFFIX_DIGITS = 32
MAX_XML_ELEMENTS = 200_000
MAX_TEXT_NODES = 100_000
MAX_XML_DEPTH = 128
MAX_RETAINED_TEXT_CHARS = 20 * 1024 * 1024

_HWPX_MIMETYPE = b"application/hwp+zip"
_SUPPORTED_COMPRESSION = {ZIP_STORED, ZIP_DEFLATED}
_XML_DECLARATION_ENCODING = re.compile(
    r"\bencoding\s*=\s*(['\"])([^'\"]+)\1",
    re.IGNORECASE,
)


class _SectionSuffixTooLong(ValueError):
    """A section name exceeds the bounded numeric metadata shape."""


class _XmlLimitExceeded(ValueError):
    """Section XML exceeded a structural or retained-text budget."""


@dataclass(frozen=True)
class TextNode:
    locator: str
    text: str


@dataclass(frozen=True)
class ParseResult:
    document_name: str
    document_sha256: str
    nodes: tuple[TextNode, ...]
    errors: tuple[CollectionError, ...]


def _section_key(entry_name: str) -> tuple[int, str] | None:
    parts = PurePosixPath(entry_name).parts
    if len(parts) != 2 or parts[0] != "Contents":
        return None
    filename = parts[1]
    prefix = "section"
    suffix = ".xml"
    if not filename.startswith(prefix) or not filename.endswith(suffix):
        return None
    section_number = filename[len(prefix) : -len(suffix)]
    if (
        not section_number
        or not section_number.isascii()
        or not section_number.isdigit()
    ):
        return None
    if len(section_number) > MAX_SECTION_SUFFIX_DIGITS:
        raise _SectionSuffixTooLong
    canonical = section_number.lstrip("0") or "0"
    return len(canonical), canonical


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def document_identifier(document_sha256: str) -> str:
    return f"document-{document_sha256[:12]}.hwpx"


def _decode_supported_xml(xml_bytes: bytes) -> str | None:
    if b"\x00" in xml_bytes:
        return None
    try:
        xml_text = xml_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    if xml_text.startswith("<?xml"):
        declaration_end = xml_text.find("?>")
        if declaration_end != -1:
            declaration = xml_text[: declaration_end + 2]
            encoding = _XML_DECLARATION_ENCODING.search(declaration)
            if encoding is not None and encoding.group(2).casefold() not in {
                "utf-8",
                "utf8",
            }:
                return None
    return xml_text


def _collection_error(
    code: str,
    message: str,
    locator: str | None,
) -> CollectionError:
    return CollectionError(
        code=code,
        stage="parse",
        fatal=True,
        locator=locator,
        message=message,
    )


def _result(
    path: Path,
    document_sha256: str,
    *,
    nodes: tuple[TextNode, ...] = (),
    error: CollectionError | None = None,
) -> ParseResult:
    return ParseResult(
        document_name=document_identifier(document_sha256),
        document_sha256=document_sha256,
        nodes=() if error is not None else nodes,
        errors=() if error is None else (error,),
    )


def _finalize(
    path: Path,
    document_sha256: str,
    *,
    nodes: tuple[TextNode, ...] = (),
    error: CollectionError | None = None,
) -> ParseResult:
    try:
        final_sha256 = _sha256_file(path)
    except OSError:
        final_sha256 = None
    if final_sha256 != document_sha256:
        return _result(
            path,
            document_sha256,
            error=_collection_error(
                "SOURCE_CHANGED_DURING_SCAN",
                "Source changed during scan.",
                None,
            ),
        )
    return _result(
        path,
        document_sha256,
        nodes=nodes,
        error=error,
    )


def _inspect_entries(
    entries: list[ZipInfo],
) -> tuple[
    tuple[tuple[tuple[int, str], ZipInfo], ...],
    ZipInfo | None,
    CollectionError | None,
]:
    if len(entries) > MAX_ENTRIES or sum(
        entry.file_size for entry in entries
    ) > MAX_TOTAL_UNCOMPRESSED_BYTES:
        return (), None, _collection_error(
            "HWPX_LIMIT_EXCEEDED",
            "HWPX archive exceeds a safety limit.",
            None,
        )

    filenames: set[str] = set()
    for entry in entries:
        if (
            entry.compress_type not in _SUPPORTED_COMPRESSION
            or entry.flag_bits & 0x1
            or entry.filename in filenames
        ):
            return (), None, _collection_error(
                "DOCUMENT_NOT_ZIP",
                "Document is not a supported readable ZIP archive.",
                None,
            )
        filenames.add(entry.filename)

    sections: list[tuple[tuple[int, str], ZipInfo]] = []
    canonical_sections: set[tuple[int, str]] = set()
    for entry in entries:
        try:
            section_key = _section_key(entry.filename)
        except _SectionSuffixTooLong:
            return (), None, _collection_error(
                "HWPX_LIMIT_EXCEEDED",
                "HWPX archive exceeds a safety limit.",
                None,
            )
        if section_key is None:
            continue
        if section_key in canonical_sections:
            return (), None, _collection_error(
                "HWPX_XML_INVALID",
                "HWPX section layout is ambiguous.",
                None,
            )
        canonical_sections.add(section_key)
        sections.append((section_key, entry))

    if any(entry.file_size > MAX_SECTION_BYTES for _, entry in sections):
        return (), None, _collection_error(
            "HWPX_LIMIT_EXCEEDED",
            "HWPX archive exceeds a safety limit.",
            None,
        )

    mimetype_entries = [
        entry for entry in entries if entry.filename == "mimetype"
    ]
    if len(mimetype_entries) != 1:
        return (), None, _collection_error(
            "HWPX_MIMETYPE_INVALID",
            "HWPX mimetype is missing or invalid.",
            None,
        )
    if not sections:
        return (), None, _collection_error(
            "HWPX_SECTION_MISSING",
            "HWPX contains no section XML.",
            None,
        )
    return (
        tuple(
            sorted(
                sections,
                key=lambda item: (item[0][0], item[0][1], item[1].filename),
            )
        ),
        mimetype_entries[0],
        None,
    )


def parse_hwpx(path: Path) -> ParseResult:
    compressed_size = path.stat().st_size
    document_sha256 = _sha256_file(path)
    if compressed_size > MAX_COMPRESSED_BYTES:
        return _finalize(
            path,
            document_sha256,
            error=_collection_error(
                "HWPX_LIMIT_EXCEEDED",
                "HWPX archive exceeds a safety limit.",
                None,
            ),
        )

    nodes: list[TextNode] = []
    xml_elements = 0
    text_nodes = 0
    retained_text_chars = 0
    parse_error: CollectionError | None = None
    try:
        with ZipFile(path, mode="r") as archive:
            entries = archive.infolist()
            sections, mimetype_entry, parse_error = _inspect_entries(entries)
            if parse_error is None and mimetype_entry is not None:
                with archive.open(mimetype_entry, "r") as member:
                    mimetype = member.read(len(_HWPX_MIMETYPE) + 1)
                if mimetype != _HWPX_MIMETYPE:
                    parse_error = _collection_error(
                        "HWPX_MIMETYPE_INVALID",
                        "HWPX mimetype is missing or invalid.",
                        None,
                    )

            if parse_error is None:
                for _, entry in sections:
                    with archive.open(entry, "r") as member:
                        xml_bytes = member.read(MAX_SECTION_BYTES + 1)
                    if len(xml_bytes) > MAX_SECTION_BYTES:
                        parse_error = _collection_error(
                            "HWPX_LIMIT_EXCEEDED",
                            "HWPX archive exceeds a safety limit.",
                            entry.filename,
                        )
                        break
                    xml_text = _decode_supported_xml(xml_bytes)
                    if xml_text is None:
                        parse_error = _collection_error(
                            "HWPX_XML_INVALID",
                            "HWPX section XML is invalid.",
                            entry.filename,
                        )
                        break
                    upper_xml = xml_text.upper()
                    if "<!DOCTYPE" in upper_xml or "<!ENTITY" in upper_xml:
                        parse_error = _collection_error(
                            "HWPX_XML_INVALID",
                            "HWPX section XML is invalid.",
                            entry.filename,
                        )
                        break
                    ordinal = 0
                    depth = 0
                    try:
                        for event, element in ElementTree.iterparse(
                            BytesIO(xml_bytes),
                            events=("start", "end"),
                        ):
                            if event == "start":
                                xml_elements += 1
                                depth += 1
                                if _local_name(element.tag) == "t":
                                    text_nodes += 1
                                if (
                                    xml_elements > MAX_XML_ELEMENTS
                                    or text_nodes > MAX_TEXT_NODES
                                    or depth > MAX_XML_DEPTH
                                ):
                                    raise _XmlLimitExceeded
                                continue
                            depth -= 1
                            if _local_name(element.tag) == "t":
                                ordinal += 1
                                text = element.text or ""
                                retained_text_chars += len(text)
                                if retained_text_chars > MAX_RETAINED_TEXT_CHARS:
                                    raise _XmlLimitExceeded
                                if text:
                                    nodes.append(
                                        TextNode(
                                            locator=f"{entry.filename}:t[{ordinal}]",
                                            text=text,
                                        )
                                    )
                            element.clear()
                    except _XmlLimitExceeded:
                        parse_error = _collection_error(
                            "HWPX_LIMIT_EXCEEDED",
                            "HWPX archive exceeds a safety limit.",
                            entry.filename,
                        )
                        break
                    except (ElementTree.ParseError, LookupError):
                        parse_error = _collection_error(
                            "HWPX_XML_INVALID",
                            "HWPX section XML is invalid.",
                            entry.filename,
                        )
                        break
    except (
        BadZipFile,
        EOFError,
        NotImplementedError,
        OSError,
        RuntimeError,
        UnicodeDecodeError,
        zlib.error,
    ):
        parse_error = _collection_error(
            "DOCUMENT_NOT_ZIP",
            "Document is not a readable ZIP archive.",
            None,
        )

    return _finalize(
        path,
        document_sha256,
        nodes=tuple(nodes) if parse_error is None else (),
        error=parse_error,
    )
