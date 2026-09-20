"""Strict local JSON input and no-clobber output for human review."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from datetime import date, datetime
from pathlib import Path

from .report import ScanRequestError, Status

MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_REPORT_ITEMS = 10_000
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 200_000
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\Z")
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _error(code: str, message: str) -> ScanRequestError:
    return ScanRequestError(code, message)


def _safe_path(path: Path, *, existing: bool) -> os.stat_result | None:
    absolute = path.absolute()
    for ancestor in reversed((absolute, *absolute.parents)):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            if ancestor == absolute and not existing:
                return None
            raise _error("REVIEW_PATH_INVALID", "Review path is not a safe regular path.") from None
        except OSError:
            raise _error("REVIEW_PATH_INVALID", "Review path is not a safe regular path.") from None
        if stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & _REPARSE):
            raise _error("REVIEW_PATH_INVALID", "Review path is not a safe regular path.")
        if ancestor != absolute and not stat.S_ISDIR(info.st_mode):
            raise _error("REVIEW_PATH_INVALID", "Review path is not a safe regular path.")
    if existing and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
        raise _error("REVIEW_PATH_INVALID", "Review path is not a safe regular path.")
    return info


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, member in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = member
    return result


def _invalid_constant(_value: str) -> object:
    raise ValueError("nonfinite number")


def _bounded(value: object) -> None:
    stack = [(value, 1)]
    count = 0
    while stack:
        member, depth = stack.pop()
        count += 1
        if count > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.")
        if isinstance(member, dict):
            if not all(type(key) is str for key in member):
                raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.")
            if any(any(0xD800 <= ord(char) <= 0xDFFF for char in key) for key in member):
                raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.")
            stack.extend((child, depth + 1) for child in member.values())
        elif isinstance(member, list):
            stack.extend((child, depth + 1) for child in member)
        elif type(member) is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in member):
                raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.")
        elif type(member) not in (int, float, bool, type(None)) or type(member) is float and not math.isfinite(member):
            raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.")


def read_json(path: Path) -> dict[str, object]:
    """Read one stable, bounded, strict UTF-8 JSON object from a regular file."""
    path = Path(path)
    before = _safe_path(path, existing=True)
    assert before is not None
    if before.st_size > MAX_JSON_BYTES:
        raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.")
    try:
        with path.open("rb") as source:
            opened = os.fstat(source.fileno())
            if _identity(opened) != _identity(before) or not stat.S_ISREG(opened.st_mode):
                raise _error("REVIEW_PATH_INVALID", "Review path is not a safe regular path.")
            raw = source.read(MAX_JSON_BYTES + 1)
            after = os.fstat(source.fileno())
        current = _safe_path(path, existing=True)
        if len(raw) > MAX_JSON_BYTES or _identity(after) != _identity(opened) or current is None or _identity(current) != _identity(opened):
            raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.")
    except OSError:
        raise _error("REVIEW_PATH_INVALID", "Review path is not a safe regular path.") from None
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_invalid_constant)
        _bounded(value)
    except (UnicodeError, ValueError, RecursionError):
        raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.") from None
    if type(value) is not dict:
        raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.")
    return value


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")
    return value


def _string(value: object, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if type(value) is not str or not value.strip():
        raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")


def _date(value: object, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    _string(value)
    try:
        if date.fromisoformat(value).isoformat() == value:
            return
    except ValueError:
        pass
    raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")


def _timestamp(value: object) -> None:
    _string(value)
    if _TIMESTAMP.fullmatch(value) is None:
        raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")
    try:
        if datetime.fromisoformat(value).utcoffset() is not None:
            return
    except ValueError:
        pass
    raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")


def validate_report(value: object) -> dict[str, object]:
    """Check the exact ScanReport.to_dict shape and return owned JSON data."""
    _bounded(value)
    report = _object(value, {"schema_version", "document_name", "document_sha256",
                             "as_of", "catalog_sha256", "items", "collection_errors"})
    if type(report["schema_version"]) is not str or report["schema_version"] != "1":
        raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")
    _string(report["document_name"])
    for field in ("document_sha256", "catalog_sha256"):
        if type(report[field]) is not str or _SHA.fullmatch(report[field]) is None:
            raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")
    _date(report["as_of"])
    items = report["items"]
    errors = report["collection_errors"]
    if type(items) is not list or len(items) > MAX_REPORT_ITEMS or type(errors) is not list:
        raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")
    for item in items:
        entry = _object(item, {"locator", "reference", "status", "reason_code", "evidence"})
        _string(entry["locator"])
        _string(entry["reason_code"])
        reference = _object(entry["reference"], {"title", "provision"})
        _string(reference["title"], nullable=True)
        _string(reference["provision"], nullable=True)
        if type(entry["status"]) is not str or entry["status"] not in {member.value for member in Status}:
            raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")
        if type(entry["evidence"]) is not list:
            raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")
        for raw_evidence in entry["evidence"]:
            evidence = _object(raw_evidence, {"record_id", "official_source", "retrieved_at", "as_of",
                                               "matched_effective_from", "matched_effective_to", "matched_title",
                                               "matched_provision", "version_transition"})
            for field in ("record_id", "official_source", "matched_title"):
                _string(evidence[field])
            _timestamp(evidence["retrieved_at"])
            for field in ("as_of", "matched_effective_from"):
                _date(evidence[field])
            _date(evidence["matched_effective_to"], nullable=True)
            _string(evidence["matched_provision"], nullable=True)
            if evidence["version_transition"] is not None:
                transition = _object(evidence["version_transition"], {"effective_from", "title", "provision"})
                _date(transition["effective_from"])
                _string(transition["title"])
                _string(transition["provision"], nullable=True)
    for raw_error in errors:
        error = _object(raw_error, {"code", "stage", "fatal", "locator", "message"})
        for field in ("code", "stage", "message"):
            _string(error[field])
        if error["stage"] not in {"parse", "extract", "resolve"}:
            raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")
        if type(error["fatal"]) is not bool:
            raise _error("REVIEW_REPORT_INVALID", "Review report does not match schema version 1.")
        _string(error["locator"], nullable=True)
    return json.loads(json.dumps(report, ensure_ascii=False, allow_nan=False))


def canonical_digest(value: object) -> str:
    _bounded(value)
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise _error("REVIEW_JSON_INVALID", "Review input is not bounded valid JSON.") from None
    return hashlib.sha256(encoded).hexdigest()


def write_new(path: Path, payload: bytes, protected: tuple[Path, ...]) -> None:
    """Create a new regular output without replacing any existing file."""
    path = Path(path)
    _safe_path(path, existing=False)
    for source in protected:
        source = Path(source)
        _safe_path(source, existing=True)
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(source)):
            raise _error("REVIEW_OUTPUT_EXISTS", "Review output already exists or aliases an input.")
        if path.exists() and os.path.samefile(path, source):
            raise _error("REVIEW_OUTPUT_EXISTS", "Review output already exists or aliases an input.")
    try:
        with path.open("xb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError:
        raise _error("REVIEW_OUTPUT_EXISTS", "Review output already exists or aliases an input.") from None
    except OSError:
        raise _error("REVIEW_OUTPUT_FAILED", "Review output could not be written.") from None
