# Architecture Decision Records

| ADR | Title | Status | Date |
| --- | --- | --- | --- |
| [0001](0001-private-prototype-scope.md) | Private local prototype before product implementation | accepted for product scope | 2026-09-04 |
| [0002](0002-python-stdlib-local-catalog.md) | Python standard-library local scanner with explicit catalog | accepted | 2026-09-04 |
| [0003](0003-pseudonymous-reports-and-allowlisted-artifacts.md) | Pseudonymous reports and allowlisted artifacts | accepted | 2026-09-05 |
| [0004](0004-packaged-synthetic-onboarding.md) | Explicit packaged synthetic onboarding | accepted; extends 0002 and the 0003 allowlist | 2026-09-05 |
| [0005](0005-bounded-runtime-resources.md) | Bound XML structure and citation-extraction work | accepted for security remediation | 2026-09-20 |
| [0006](0006-experimental-oss-publication.md) | Experimental OSS publication | accepted | 2026-09-20 |
| [0007](0007-second-experimental-archive.md) | Second experimental archive | accepted for release preparation | 2026-09-24 |

ADRs record decisions that shape implementation. If a later ADR changes one, mark the earlier record as deprecated or superseded and link both directions; do not silently rewrite the historical rationale.

ADR-0006 supersedes the private-only distribution clauses of ADRs 0001, 0002
and 0004. Their implementation safety decisions remain applicable.
ADR-0007 sets the new archive identity and 15-entry count. ADR-0006's
11-entry count remains the historical first-release requirement.
