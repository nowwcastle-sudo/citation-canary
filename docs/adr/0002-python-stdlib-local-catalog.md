# ADR-0002: Python standard-library local scanner with explicit catalog

**Date**: 2026-09-04
**Status**: accepted; private-only distribution superseded by [ADR-0006](0006-experimental-oss-publication.md)
**Deciders**: Product owner through the explicit S3 design instruction

## Context

The private pilot needs a real scanner but must keep HWPX local, preserve original bytes, and avoid legal verdicts. Repeat use and procurement are unproven, while live official-source access, privacy operations, and editor integration would add irreversible commitments. The repository has no existing runtime or dependencies.

## Decision

We use Python 3.11+ standard library, one public `scan_document(path, as_of, catalog) -> ScanReport` interface, one CLI, and one explicit dated catalog JSON adapter. We distribute v0.1 as a `.pyz` in a private GitHub Release. Runtime network, auth, database, upload, auto-correction, legal verdict, and third-party dependencies are excluded.

## Alternatives considered

### Hosted SaaS with live law interface

- **Pros**: centralized data freshness and deployment.
- **Cons**: requires upload, auth, retention, hosting, API terms, retries, monitoring, and an operator.
- **Why not**: conflicts with private/local scope before repeat use and procurement are proven.

### HWPX editor plugin

- **Pros**: evidence can appear in the authoring context.
- **Cons**: editor/platform coupling, UI/distribution work, and a blurred auto-correction boundary.
- **Why not**: adds complexity without improving the first pilot’s evidence test.

## Consequences

### Positive

- Offline deterministic tests and simple local data flow.
- One install-free artifact and no dependency supply chain.
- Source documents never cross a network boundary.
- Catalog provenance and status evidence are explicit.

### Negative

- Catalog freshness is manual and bounded by recorded metadata.
- Citation grammar and HWPX coverage start narrow.
- Python 3.11+ must be present on the operator machine.

### Risks

- **Stale catalog**: include catalog hash, retrieval metadata, and dated evidence in every report.
- **Misleading partial scan**: fatal ZIP/XML/source-change errors return no items.
- **Large/malicious ZIP**: bounded archive/member sizes and no extraction to disk.
- **Verdict drift**: four evidence statuses only, with no legal or auto-fix fields.
