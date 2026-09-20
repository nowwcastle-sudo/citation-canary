from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from .report import (
    Evidence,
    Resolution,
    ScanRequestError,
    Status,
    VersionTransition,
)

if TYPE_CHECKING:
    from .references import ReferenceCandidate


_RFC3339_TIMESTAMP = re.compile(
    r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\Z",
    re.ASCII,
)


@dataclass(frozen=True)
class Provision:
    canonical_id: str
    label: str


@dataclass(frozen=True)
class CatalogVersion:
    effective_from: date
    effective_to: date | None
    title: str
    provisions: tuple[Provision, ...]


@dataclass(frozen=True)
class CatalogRecord:
    record_id: str
    official_source: str
    retrieved_at: str
    versions: tuple[CatalogVersion, ...]


@dataclass(frozen=True)
class Catalog:
    schema_version: str
    records: tuple[CatalogRecord, ...]
    sha256: str


class _CatalogSchemaError(ValueError):
    """An expected schema failure that is safe to convert at the boundary."""


class _CatalogSchemaUnsupported(_CatalogSchemaError):
    """A syntactically valid catalog uses an unsupported schema version."""


class _CatalogJsonError(ValueError):
    """Catalog bytes are not strict JSON with unique object keys."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, member in pairs:
        if key in value:
            raise _CatalogJsonError("Duplicate JSON object key")
        value[key] = member
    return value


def _reject_json_constant(value: str) -> object:
    raise _CatalogJsonError(f"Unsupported JSON constant: {value}")


def _expect_keys(value: dict[str, Any], allowed: set[str], context: str) -> None:
    if set(value) != allowed:
        raise _CatalogSchemaError(f"Invalid {context} fields")


def _non_empty_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _CatalogSchemaError(f"Invalid {context}")
    return value


def _parse_date(value: object, context: str) -> date:
    raw = _non_empty_string(value, context)
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as error:
        raise _CatalogSchemaError(f"Invalid {context}") from error
    if parsed.isoformat() != raw:
        raise _CatalogSchemaError(f"Invalid {context}")
    return parsed


def _parse_provisions(value: object) -> tuple[Provision, ...]:
    if not isinstance(value, list) or not value:
        raise _CatalogSchemaError("Invalid provisions")
    provisions: list[Provision] = []
    labels: set[str] = set()
    canonical_ids: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict):
            raise _CatalogSchemaError("Invalid provision")
        _expect_keys(entry, {"canonical_id", "label"}, "provision")
        canonical_id = _non_empty_string(entry["canonical_id"], "canonical_id")
        label = _non_empty_string(entry["label"], "provision label")
        if canonical_id in canonical_ids or label in labels:
            raise _CatalogSchemaError("Duplicate provision identifier")
        canonical_ids.add(canonical_id)
        labels.add(label)
        provisions.append(Provision(canonical_id=canonical_id, label=label))
    return tuple(provisions)


def _parse_versions(value: object) -> tuple[CatalogVersion, ...]:
    if not isinstance(value, list) or not value:
        raise _CatalogSchemaError("Invalid versions")
    versions: list[CatalogVersion] = []
    for entry in value:
        if not isinstance(entry, dict):
            raise _CatalogSchemaError("Invalid catalog version")
        _expect_keys(
            entry,
            {"effective_from", "effective_to", "title", "provisions"},
            "catalog version",
        )
        effective_from = _parse_date(entry["effective_from"], "effective_from")
        effective_to_value = entry["effective_to"]
        effective_to = (
            None
            if effective_to_value is None
            else _parse_date(effective_to_value, "effective_to")
        )
        if effective_to is not None and effective_from >= effective_to:
            raise _CatalogSchemaError("Invalid catalog version interval")
        versions.append(
            CatalogVersion(
                effective_from=effective_from,
                effective_to=effective_to,
                title=_non_empty_string(entry["title"], "title"),
                provisions=_parse_provisions(entry["provisions"]),
            )
        )

    for previous, current in zip(versions, versions[1:]):
        if previous.effective_to is None:
            raise _CatalogSchemaError("Open-ended catalog version must be last")
        if current.effective_from < previous.effective_to:
            raise _CatalogSchemaError("Catalog version intervals overlap")
    if versions[-1].effective_to is not None:
        raise _CatalogSchemaError("Last catalog version must be open-ended")
    return tuple(versions)


def _parse_record(value: object) -> CatalogRecord:
    if not isinstance(value, dict):
        raise _CatalogSchemaError("Invalid catalog record")
    _expect_keys(value, {"record_id", "official_source", "versions"}, "record")
    source = value["official_source"]
    if not isinstance(source, dict):
        raise _CatalogSchemaError("Invalid official source")
    _expect_keys(source, {"url", "retrieved_at"}, "official source")
    url = _non_empty_string(source["url"], "official source URL")
    if "\\" in url or any(
        character.isspace() or ord(character) < 0x20 or ord(character) == 0x7F
        for character in url
    ):
        raise _CatalogSchemaError("Official source URL must be absolute HTTPS")
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        parsed_url.port
    except ValueError as error:
        raise _CatalogSchemaError(
            "Official source URL must be absolute HTTPS"
        ) from error
    if (
        parsed_url.scheme != "https"
        or not parsed_url.netloc
        or hostname is None
        or parsed_url.username is not None
        or parsed_url.password is not None
    ):
        raise _CatalogSchemaError("Official source URL must be absolute HTTPS")
    retrieved_at = _non_empty_string(source["retrieved_at"], "retrieved_at")
    if _RFC3339_TIMESTAMP.fullmatch(retrieved_at) is None:
        raise _CatalogSchemaError("Invalid retrieved_at")
    try:
        timestamp = datetime.fromisoformat(retrieved_at)
    except ValueError as error:
        raise _CatalogSchemaError("Invalid retrieved_at") from error
    if timestamp.utcoffset() is None:
        raise _CatalogSchemaError("retrieved_at must include an offset")
    return CatalogRecord(
        record_id=_non_empty_string(value["record_id"], "record_id"),
        official_source=url,
        retrieved_at=retrieved_at,
        versions=_parse_versions(value["versions"]),
    )


def load_catalog(path: Path) -> Catalog:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as error:
        raise ScanRequestError(
            "CATALOG_NOT_FOUND",
            "Catalog file was not found.",
        ) from error
    except OSError as error:
        raise ScanRequestError(
            "CATALOG_NOT_READABLE",
            "Catalog file is not readable.",
        ) from error

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_json_constant,
        )
    except (ValueError, RecursionError) as error:
        raise ScanRequestError(
            "CATALOG_JSON_INVALID",
            "Catalog is not valid UTF-8 JSON.",
        ) from error

    try:
        if not isinstance(value, dict):
            raise _CatalogSchemaError("Invalid catalog")
        _expect_keys(value, {"schema_version", "records"}, "catalog")
        if value["schema_version"] != "1":
            raise _CatalogSchemaUnsupported("Unsupported catalog schema")
        records_value = value["records"]
        if not isinstance(records_value, list) or not records_value:
            raise _CatalogSchemaError("Invalid catalog records")
        records = tuple(_parse_record(record) for record in records_value)
        record_ids = [record.record_id for record in records]
        if len(record_ids) != len(set(record_ids)):
            raise _CatalogSchemaError("Duplicate record_id")
    except _CatalogSchemaUnsupported as error:
        raise ScanRequestError(
            "CATALOG_SCHEMA_UNSUPPORTED",
            "Catalog schema version is unsupported.",
        ) from error
    except _CatalogSchemaError as error:
        raise ScanRequestError(
            "CATALOG_SCHEMA_INVALID",
            "Catalog does not conform to schema version 1.",
        ) from error

    return Catalog(
        schema_version="1",
        records=records,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def _effective(version: CatalogVersion, as_of: date) -> bool:
    return version.effective_from <= as_of and (
        version.effective_to is None or as_of < version.effective_to
    )


def _latest_provision(
    record: CatalogRecord,
    canonical_id: str,
) -> tuple[CatalogVersion, Provision] | None:
    latest = record.versions[-1]
    for provision in latest.provisions:
        if provision.canonical_id == canonical_id:
            return latest, provision
    return None


def _transition(
    record: CatalogRecord,
    version: CatalogVersion,
    provision: Provision,
) -> VersionTransition | None:
    latest_match = _latest_provision(record, provision.canonical_id)
    if latest_match is None:
        return None
    latest, latest_provision = latest_match
    if latest.title == version.title and latest_provision.label == provision.label:
        return None
    return VersionTransition(
        effective_from=latest.effective_from.isoformat(),
        title=latest.title,
        provision=latest_provision.label,
    )


def _evidence(
    record: CatalogRecord,
    version: CatalogVersion,
    as_of: date,
    provision: Provision | None,
) -> Evidence:
    return Evidence(
        record_id=record.record_id,
        official_source=record.official_source,
        retrieved_at=record.retrieved_at,
        as_of=as_of.isoformat(),
        matched_effective_from=version.effective_from.isoformat(),
        matched_effective_to=(
            version.effective_to.isoformat()
            if version.effective_to is not None
            else None
        ),
        matched_title=version.title,
        matched_provision=provision.label if provision is not None else None,
        version_transition=(
            _transition(record, version, provision)
            if provision is not None
            else None
        ),
    )


def resolve_reference(
    candidate: ReferenceCandidate,
    as_of: date,
    catalog: Catalog,
) -> Resolution:
    if candidate.title is None:
        return Resolution(Status.UNKNOWN, "AMBIGUOUS_CITATION", ())

    title_matches: list[tuple[CatalogRecord, CatalogVersion]] = []
    exact_matches: list[tuple[CatalogRecord, CatalogVersion, Provision]] = []
    historical_matches: list[tuple[CatalogRecord, CatalogVersion, Provision]] = []
    for record in catalog.records:
        for version in record.versions:
            if version.title != candidate.title:
                continue
            for provision in version.provisions:
                if provision.label == candidate.provision:
                    historical_matches.append((record, version, provision))
            if not _effective(version, as_of):
                continue
            title_matches.append((record, version))
            for provision in version.provisions:
                if provision.label == candidate.provision:
                    exact_matches.append((record, version, provision))

    if len(title_matches) > 1:
        evidence = tuple(
            _evidence(
                record,
                version,
                as_of,
                next(
                    (
                        provision
                        for provision in version.provisions
                        if provision.label == candidate.provision
                    ),
                    None,
                ),
            )
            for record, version in title_matches
        )
        return Resolution(Status.REVIEW, "CONFLICTING_EVIDENCE", evidence)

    if len(exact_matches) == 1:
        record, version, provision = exact_matches[0]
        evidence = (_evidence(record, version, as_of, provision),)
        latest_match = _latest_provision(record, provision.canonical_id)
        if latest_match is None:
            return Resolution(Status.REVIEW, "CONFLICTING_EVIDENCE", evidence)
        latest, latest_provision = latest_match
        if latest.title == candidate.title and latest_provision.label == candidate.provision:
            return Resolution(Status.CURRENT, "EXACT_CURRENT_MATCH", evidence)
        return Resolution(Status.HISTORY, "EXACT_HISTORICAL_MATCH", evidence)

    if title_matches:
        evidence = tuple(
            _evidence(record, version, as_of, None)
            for record, version in title_matches
        )
        return Resolution(Status.REVIEW, "PROVISION_MISMATCH", evidence)

    if historical_matches:
        evidence = tuple(
            _evidence(record, version, as_of, provision)
            for record, version, provision in historical_matches
        )
        return Resolution(Status.REVIEW, "CONFLICTING_EVIDENCE", evidence)

    return Resolution(Status.UNKNOWN, "CATALOG_NO_MATCH", ())
