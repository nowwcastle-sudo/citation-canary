from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .catalog import Catalog
    from .hwpx import TextNode


_PROVISION = re.compile(r"제\d+조(?:의\d+)?")
_PROVISION_LOOKAHEAD = 32
_AMBIGUOUS_MARKERS = ("법", "규정", "고시", "훈령", "예규")
MAX_MATCHES_PER_NODE = 100_000
MAX_MATCHES = 100_000
MAX_CANDIDATES_PER_NODE = 10_000
MAX_CANDIDATES = 10_000


class _ReferenceLimitExceeded(ValueError):
    """Reference extraction exceeded a fixed work or output budget."""


@dataclass(frozen=True)
class ReferenceCandidate:
    locator: str
    title: str | None
    provision: str | None


def _title_occurrences(
    text: str,
    titles: list[str],
    match_limit: int,
    candidate_limit: int,
) -> tuple[list[tuple[int, int, str]], bytearray, int]:
    selected: list[tuple[int, int, str]] = []
    # One byte per character replaces a scan of all earlier intervals.
    covered = bytearray(len(text))
    matches = 0
    for title in titles:
        search_from = 0
        while (start := text.find(title, search_from)) != -1:
            matches += 1
            if matches > match_limit:
                raise _ReferenceLimitExceeded
            end = start + len(title)
            if covered.find(b"\x01", start, end) == -1:
                if len(selected) >= candidate_limit:
                    raise _ReferenceLimitExceeded
                selected.append((start, end, title))
                covered[start:end] = b"\x01" * len(title)
            search_from = end
    return sorted(selected, key=lambda occurrence: occurrence[0]), covered, matches


def extract_references(
    nodes: tuple[TextNode, ...],
    catalog: Catalog,
) -> tuple[ReferenceCandidate, ...]:
    titles = sorted(
        {
            version.title
            for record in catalog.records
            for version in record.versions
        },
        key=lambda title: (-len(title), title),
    )
    candidates: list[ReferenceCandidate] = []
    document_matches = 0
    for node in nodes:
        match_limit = min(MAX_MATCHES_PER_NODE, MAX_MATCHES - document_matches)
        candidate_limit = min(
            MAX_CANDIDATES_PER_NODE, MAX_CANDIDATES - len(candidates),
        )
        occurrences, covered, matches = _title_occurrences(
            node.text, titles, match_limit, candidate_limit,
        )
        ordered_candidates: list[tuple[int, ReferenceCandidate]] = []
        for index, (title_start, title_end, matched_title) in enumerate(occurrences):
            next_title_start = (
                occurrences[index + 1][0]
                if index + 1 < len(occurrences)
                else len(node.text)
            )
            # Bind the first provision after this title, before the next title,
            # and no farther than the approved local lookahead.
            association_end = min(
                title_end + _PROVISION_LOOKAHEAD,
                next_title_start,
            )
            provision_match = _PROVISION.search(
                node.text,
                title_end,
                association_end,
            )
            ordered_candidates.append(
                (
                    title_start,
                    ReferenceCandidate(
                        locator=node.locator,
                        title=matched_title,
                        provision=(
                            provision_match.group(0)
                            if provision_match is not None
                            else None
                        ),
                    ),
                )
            )

        ambiguous_start: int | None = None
        for marker in _AMBIGUOUS_MARKERS:
            search_from = 0
            while (start := node.text.find(marker, search_from)) != -1:
                matches += 1
                if matches > match_limit:
                    raise _ReferenceLimitExceeded
                end = start + len(marker)
                if covered.find(b"\x01", start, end) == -1:
                    ambiguous_start = (
                        start if ambiguous_start is None else min(ambiguous_start, start)
                    )
                    # Only the first uncovered occurrence of each marker matters.
                    break
                search_from = end
        document_matches += matches
        if ambiguous_start is not None:
            if len(ordered_candidates) >= candidate_limit:
                raise _ReferenceLimitExceeded
            ordered_candidates.append(
                (
                    ambiguous_start,
                    ReferenceCandidate(
                        locator=node.locator,
                        title=None,
                        provision=None,
                    ),
                )
            )
        candidates.extend(
            candidate
            for _, candidate in sorted(
                ordered_candidates,
                key=lambda located: located[0],
            )
        )
    return tuple(candidates)
