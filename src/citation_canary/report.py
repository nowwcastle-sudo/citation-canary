from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .references import ReferenceCandidate


class Status(StrEnum):
    CURRENT = "CURRENT"
    HISTORY = "HISTORY"
    REVIEW = "REVIEW"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class VersionTransition:
    effective_from: str
    title: str
    provision: str | None


@dataclass(frozen=True)
class Evidence:
    record_id: str
    official_source: str
    retrieved_at: str
    as_of: str
    matched_effective_from: str
    matched_effective_to: str | None
    matched_title: str
    matched_provision: str | None
    version_transition: VersionTransition | None


@dataclass(frozen=True)
class Reference:
    title: str | None
    provision: str | None


@dataclass(frozen=True)
class ScanItem:
    locator: str
    reference: Reference
    status: Status
    reason_code: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class CollectionError:
    code: str
    stage: str
    fatal: bool
    locator: str | None
    message: str


@dataclass(frozen=True)
class ScanReport:
    schema_version: str
    document_name: str
    document_sha256: str
    as_of: str
    catalog_sha256: str
    items: tuple[ScanItem, ...]
    collection_errors: tuple[CollectionError, ...]

    def to_dict(self) -> dict[str, object]:
        def transition(value: VersionTransition | None) -> dict[str, object] | None:
            if value is None:
                return None
            return {
                "effective_from": value.effective_from,
                "title": value.title,
                "provision": value.provision,
            }

        def evidence(value: Evidence) -> dict[str, object]:
            return {
                "record_id": value.record_id,
                "official_source": value.official_source,
                "retrieved_at": value.retrieved_at,
                "as_of": value.as_of,
                "matched_effective_from": value.matched_effective_from,
                "matched_effective_to": value.matched_effective_to,
                "matched_title": value.matched_title,
                "matched_provision": value.matched_provision,
                "version_transition": transition(value.version_transition),
            }

        return {
            "schema_version": self.schema_version,
            "document_name": self.document_name,
            "document_sha256": self.document_sha256,
            "as_of": self.as_of,
            "catalog_sha256": self.catalog_sha256,
            "items": [
                {
                    "locator": item.locator,
                    "reference": {
                        "title": item.reference.title,
                        "provision": item.reference.provision,
                    },
                    "status": item.status.value,
                    "reason_code": item.reason_code,
                    "evidence": [evidence(value) for value in item.evidence],
                }
                for item in self.items
            ],
            "collection_errors": [
                {
                    "code": error.code,
                    "stage": error.stage,
                    "fatal": error.fatal,
                    "locator": error.locator,
                    "message": error.message,
                }
                for error in self.collection_errors
            ],
        }


class ScanRequestError(ValueError):
    code: str
    safe_message: str

    def __init__(self, code: str, safe_message: str) -> None:
        self.code = code
        self.safe_message = safe_message
        super().__init__(safe_message)

    def __str__(self) -> str:
        return self.safe_message


@dataclass(frozen=True)
class Resolution:
    status: Status
    reason_code: str
    evidence: tuple[Evidence, ...]


def build_item(
    candidate: ReferenceCandidate,
    resolution: Resolution,
    as_of: date,
) -> ScanItem:
    return ScanItem(
        locator=candidate.locator,
        reference=Reference(candidate.title, candidate.provision),
        status=resolution.status,
        reason_code=resolution.reason_code,
        evidence=resolution.evidence,
    )
