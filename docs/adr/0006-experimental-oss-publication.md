# ADR-0006: Experimental OSS publication

- Date: 2026-09-20
- Status: accepted by the owner for experimental open-source distribution
- Supersedes: private-only distribution clauses of ADR-0001, ADR-0002 and ADR-0004

Publish Citation Canary at https://github.com/nowwcastle-sudo/citation-canary
with a clean public history, branch `main`, and first experimental tag
`v0.2.0-experimental.1`. Earlier private history and evidence remain separate;
they are not dependencies of this public source tree.

Public availability is permission to inspect and try experimental software,
not evidence of human adoption, repeat use, procurement, legal correctness or
case authenticity. No hosted service or sensitive-document upload is approved.
The local stdlib runtime, unchanged source inputs, pseudonymous reports,
four evidence statuses, fail-closed limits and exact packaging allowlist remain.
The synthetic demo is fictional; the operator must independently review real
catalog provenance, freshness and permitted source use.

Preserve Apache License 2.0 and attribution. A release must identify its public
source commit, pass the configured CI, contain the exact eleven-member zipapp
including LICENSE, provide its SHA-256 sidecar, and expose a private security
reporting channel. Verify anonymous download of both release assets after
publication. Keep old verified artifacts for rollback without altering inputs.

Revisit product claims only with separately reviewed real-use evidence. Revisit
data handling or automation only through an explicit design decision retaining
human legal review and the source-document preservation boundary.
