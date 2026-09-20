from __future__ import annotations

import os
import stat
from datetime import date
from pathlib import Path

from . import hwpx as _hwpx
from .catalog import load_catalog, resolve_reference
from .hwpx import parse_hwpx
from .references import _ReferenceLimitExceeded, extract_references
from .report import CollectionError, ScanReport, ScanRequestError, build_item


class _ReferenceExtractionError(ValueError):
    """An expected failure at the internal reference-extraction seam."""


class _CatalogResolutionError(ValueError):
    """An expected failure at the internal catalog-resolution seam."""


def _validate_file_request(
    value: str | os.PathLike[str],
    *,
    not_found_code: str,
    not_found_message: str,
    not_readable_code: str,
    not_readable_message: str,
) -> Path:
    path = Path(value)
    try:
        metadata = path.stat()
    except FileNotFoundError as error:
        raise ScanRequestError(not_found_code, not_found_message) from error
    except OSError as error:
        raise ScanRequestError(not_readable_code, not_readable_message) from error
    if not stat.S_ISREG(metadata.st_mode):
        raise ScanRequestError(not_readable_code, not_readable_message)
    try:
        with path.open("rb") as source:
            source.read(0)
    except FileNotFoundError as error:
        raise ScanRequestError(not_found_code, not_found_message) from error
    except OSError as error:
        raise ScanRequestError(not_readable_code, not_readable_message) from error
    return path


def validate_document_request(path: str | os.PathLike[str]) -> Path:
    return _validate_file_request(
        path,
        not_found_code="DOCUMENT_NOT_FOUND",
        not_found_message="Document file was not found.",
        not_readable_code="DOCUMENT_NOT_READABLE",
        not_readable_message="Document file is not readable.",
    )


def validate_catalog_request(path: str | os.PathLike[str]) -> Path:
    return _validate_file_request(
        path,
        not_found_code="CATALOG_NOT_FOUND",
        not_found_message="Catalog file was not found.",
        not_readable_code="CATALOG_NOT_READABLE",
        not_readable_message="Catalog file is not readable.",
    )


def validate_as_of(as_of: date) -> None:
    if type(as_of) is not date:
        raise ScanRequestError(
            "AS_OF_TYPE_INVALID",
            "As-of value must be a date.",
        )


def _fatal_error(
    code: str,
    stage: str,
    locator: str | None,
    message: str,
) -> CollectionError:
    return CollectionError(
        code=code,
        stage=stage,
        fatal=True,
        locator=locator,
        message=message,
    )


def _finalize_report(document_path: Path, report: ScanReport) -> ScanReport:
    """Make source identity the last check before every public report return."""
    report = ScanReport(
        schema_version=report.schema_version,
        document_name=_hwpx.document_identifier(report.document_sha256),
        document_sha256=report.document_sha256,
        as_of=report.as_of,
        catalog_sha256=report.catalog_sha256,
        items=report.items,
        collection_errors=report.collection_errors,
    )
    try:
        final_sha256 = _hwpx._sha256_file(document_path)
    except OSError:
        final_sha256 = None
    if final_sha256 == report.document_sha256:
        return report
    return ScanReport(
        schema_version=report.schema_version,
        document_name=_hwpx.document_identifier(report.document_sha256),
        document_sha256=report.document_sha256,
        as_of=report.as_of,
        catalog_sha256=report.catalog_sha256,
        items=(),
        collection_errors=(
            _fatal_error(
                "SOURCE_CHANGED_DURING_SCAN",
                "parse",
                None,
                "Source changed during scan.",
            ),
        ),
    )


def scan_document(
    path: str | os.PathLike[str],
    as_of: date,
    catalog: str | os.PathLike[str],
) -> ScanReport:
    document_path = validate_document_request(path)
    catalog_path = validate_catalog_request(catalog)
    validate_as_of(as_of)
    loaded_catalog = load_catalog(catalog_path)
    parsed = parse_hwpx(document_path)
    if parsed.errors:
        return _finalize_report(
            document_path,
            ScanReport(
                schema_version="1",
                document_name=parsed.document_name,
                document_sha256=parsed.document_sha256,
                as_of=as_of.isoformat(),
                catalog_sha256=loaded_catalog.sha256,
                items=(),
                collection_errors=parsed.errors,
            ),
        )

    try:
        candidates = extract_references(parsed.nodes, loaded_catalog)
    except (_ReferenceExtractionError, _ReferenceLimitExceeded) as error:
        limit_exceeded = isinstance(error, _ReferenceLimitExceeded)
        return _finalize_report(
            document_path,
            ScanReport(
                schema_version="1",
                document_name=parsed.document_name,
                document_sha256=parsed.document_sha256,
                as_of=as_of.isoformat(),
                catalog_sha256=loaded_catalog.sha256,
                items=(),
                collection_errors=(
                    _fatal_error(
                        "REFERENCE_LIMIT_EXCEEDED" if limit_exceeded
                        else "REFERENCE_EXTRACTION_FAILED",
                        "extract",
                        None,
                        "Reference extraction exceeds a safety limit." if limit_exceeded
                        else "Reference extraction failed.",
                    ),
                ),
            ),
        )

    items = []
    for candidate in candidates:
        try:
            resolution = resolve_reference(candidate, as_of, loaded_catalog)
        except _CatalogResolutionError:
            return _finalize_report(
                document_path,
                ScanReport(
                    schema_version="1",
                    document_name=parsed.document_name,
                    document_sha256=parsed.document_sha256,
                    as_of=as_of.isoformat(),
                    catalog_sha256=loaded_catalog.sha256,
                    items=(),
                    collection_errors=(
                        _fatal_error(
                            "CATALOG_RESOLUTION_FAILED",
                            "resolve",
                            candidate.locator,
                            "Catalog resolution failed.",
                        ),
                    ),
                ),
            )
        items.append(build_item(candidate, resolution, as_of))

    return _finalize_report(
        document_path,
        ScanReport(
            schema_version="1",
            document_name=parsed.document_name,
            document_sha256=parsed.document_sha256,
            as_of=as_of.isoformat(),
            catalog_sha256=loaded_catalog.sha256,
            items=tuple(items),
            collection_errors=(),
        ),
    )
