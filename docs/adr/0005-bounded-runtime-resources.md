# ADR-0005: Bound XML structure and citation-extraction work

- Date: 2026-09-20
- Status: accepted for the bounded security remediation; publication remains separate
- Context: the user requested continued public-release preparation; source scan at659b4b79b730c7ef11ec7920d62633e510dda352 established two malicious-HWPX resource-amplification paths.

## Problem

Archive byte limits admitted a highly repetitive text node that triggered
quadratic overlap comparisons, and dense empty XML text elements that created
a large document-wide collection of Python objects. Neither case requires
changing the operator's catalog. Source analysis established the mechanisms;
large denial-of-service payloads were not executed on the workstation.

## Decision

Preserve the standard-library architecture, report schema, four evidence
statuses, longest-title precedence and original text-node locator ordinals.
Use per-character coverage lookup instead of repeatedly scanning prior
intervals. Stop with a fixed fatal collection error before exceeding a
structural, retained-text, match or candidate budget; never truncate into
apparently complete evidence.

| Resource | Limit |
| --- | ---: |
| XML start elements across sections | 200,000 |
| Text elements across sections, including empty elements | 100,000 |
| XML nesting depth per section, root = 1 | 128 |
| Retained text across sections | 20 × 1,024 × 1,024 Unicode characters |
| Examined title/marker matches per node and per document | 100,000 |
| Reference candidates per node and per document | 10,000 |

Original archive byte/member/suffix ceilings remain unchanged. Empty text
elements keep their ordinal and budget cost but do not allocate retained
TextNode records. XML-budget rejection uses HWPX_LIMIT_EXCEEDED at parse.
Extraction-budget rejection uses REFERENCE_LIMIT_EXCEEDED at extract. Both
return no partial items, fixed safe messages and the existing final source
identity check.

## Tradeoffs and scope

Large otherwise valid documents may now be rejected. This is an intentional
fail-closed limit, not evidence of invalid law or unsafe documents. The
limits do not certify a fixed runtime or total process-memory bound, and
operator-supplied catalog size/resolution cost remains a separate limit.
No network, new dependencies, source-document correction, or publication
capability is introduced.

Small synthetic boundary fixtures establish exact acceptance/rejection,
cumulative accounting, source preservation and locator/precedence behavior.
Operation-count checks cover the known quadratic mechanism without timing
assertions or enormous input. Full customer corpus compatibility remains
unverified.

## Revisit condition

Raise limits only with representative measured inputs, an explicit resource
budget and review of the affected controls. Any new hosting or unattended
batch service needs its own process isolation and operational resource limits.
See [runtime resource limits](../runtime-resource-limits.md).
