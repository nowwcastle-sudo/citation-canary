# Repository instructions

Citation Canary is experimental OSS for local HWPX citation review.
Read [CONTEXT.md](CONTEXT.md) and relevant [ADRs](docs/adr/README.md) before
changing domain behavior. Historical private-prototype distribution decisions
are superseded for this public repository by ADR-0006.

- Keep source HWPX local and unchanged. Use synthetic fixtures.
- Preserve exactly `CURRENT`, `HISTORY`, `REVIEW`, `UNKNOWN`, the report schema,
  source-identity checks, resource budgets and fixed exit/error contracts.
- Require an explicit review date; keep provenance and uncertainty inspectable.
  Catalog claims are operator-supplied, not authenticated by the runtime.
- Never present legal conclusions, case authentication or automatic corrections.
- Keep source bodies, secrets and personal information out of source, fixtures,
  logs, issues and shared reports. Hash-derived labels are not anonymization.
- Preserve LICENSE and attribution, the stdlib-only runtime and exact artifact allowlist.
- For contributions follow [CONTRIBUTING.md](CONTRIBUTING.md); for security
  reporting follow [SECURITY.md](SECURITY.md).
