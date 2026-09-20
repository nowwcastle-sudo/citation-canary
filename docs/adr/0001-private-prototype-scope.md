# ADR-0001: Private local prototype before product implementation

- Status: Historical; public OSS distribution superseded by [ADR-0006](0006-experimental-oss-publication.md). Local/privacy/legal invariants remain.
- Date: 2026-09-04
- Decision owners: Product owner approval is required to reverse this boundary

## Context

The validation audit found real date-sensitive citation discrepancies and showed fast local HWPX extraction, but did not observe repeat use or willingness to pay. Building a hosted or automated product now would commit to data handling, official-source integration, status semantics, and legal-risk language before the riskiest product assumptions are tested.

The source documents can contain confidential or personal data. The audit’s final corpus pattern scan found no resident-registration-number, Korean mobile-number, or email patterns, but that limited observation cannot be generalized to institution documents.

## Decision

The next product test is a **private, local, read-only manual prototype**.

- HWPX files remain local and are not copied into the repository, issues, or a cloud corpus.
- The prototype produces a separate evidence report; it does not alter the HWPX.
- Every substantive item uses an explicit 기준일, official-source provenance, and one of `CURRENT`, `HISTORY`, `REVIEW`, or `UNKNOWN`.
- Statuses route human review and are not legal determinations.
- Source-document secrets and personal data are excluded from logs and outputs.
- Product implementation originally required an explicit design approval; that private planning workflow is not a public repository dependency.

## Consequences

### Benefits

- Tests review-time reduction, actual correction behavior, repeat use, and payment conversations before architecture is fixed.
- Minimizes exposure of real institution documents.
- Keeps failure and uncertainty visible and preserves a reversible path.

### Costs

- Manual operation limits throughput and does not establish production scalability.
- Official-source lookups and status assignment may be slower or less consistent until pilot rules are refined.
- No hosted access, collaboration, automated correction, or long-term history is available.

## Rejected for now

- Public upload or SaaS workflow: data handling and demand are unvalidated.
- Automatic HWPX correction: conflicts with the human-review boundary and increases asymmetric error cost.
- Legal correctness score: compresses date-sensitive evidence into a misleading verdict.
- Broad or hosted product build before pilot: does not test the largest remaining product risks. A minimal local private prototype is authorized after the staged design gate because it is the pilot instrument.

## Revisit conditions

Reopen the public/product-release boundary only after the pilot provides measured end-to-end review time, user dispositions, second-use behavior, and a concrete payment signal, and after privacy/data-flow plus official-source access designs are explicitly approved. Reversal must state what changed and preserve the no-legal-judgment and no-silent-auto-correction constraints unless the product owner separately approves those product-policy changes.
