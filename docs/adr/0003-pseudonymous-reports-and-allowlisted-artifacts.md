# ADR-0003: Pseudonymous reports and allowlisted artifacts

**Date**: 2026-09-05
**Status**: accepted
**Deciders**: Product owner through the explicit final-review fix instruction

## Context

The v0.1 schema exposed the source basename through `document_name` and some
collection-error locators. A basename can itself contain a person, institution,
case, payroll, or other confidential identifier even when no paragraph text is
reported. The first zipapp recipe also archived the live `src` directory. Python
cache files in that directory carried absolute local build paths in compiled
code metadata, and a denylist could not prove the complete artifact contents.

The public schema field must remain compatible, source-change detection must
remain fail closed, and the prototype must still be one local stdlib-only
artifact.

## Decision

- Keep the public field name `document_name`, but set its value to
  `document-<first 12 lowercase SHA-256 hex characters>.hwpx`. The full source
  SHA-256 remains in `document_sha256`, so the short display identifier is not
  used as the sole identity or integrity proof.
- Never place the source basename in a report or collection-error locator.
  Document-level failures use `null`; section-level locators use only validated
  canonical HWPX member names and text-node ordinals.
- Perform the decisive source SHA-256 read immediately before every public
  `ScanReport` return. A mismatch or final source I/O failure replaces every
  other result with the sole fatal `SOURCE_CHANGED_DURING_SCAN` error and no
  items.
- Treat a numeric HWPX section suffix longer than 32 ASCII digits as
  `HWPX_LIMIT_EXCEEDED`; reject duplicate canonical section numbers and
  unsupported/encrypted member forms before reading member bodies.
- Build the zipapp from a fresh temporary staging tree populated from an exact
  seven-file source allowlist. Require the exact archive member set, reject
  caches/bytecode/unexpected members, and scan decompressed member bytes for
  local absolute build paths before replacing the requested artifact.

## Consequences

### Positive

- Reports and safe errors no longer reveal an operator-controlled basename.
- Repeated scans of identical bytes have a deterministic display identifier.
- The artifact contains only reviewed Python source plus the generated zipapp
  entrypoint; live caches cannot enter it.
- A source mutation during extraction or resolution cannot escape the final
  identity gate.

### Limits and trade-offs

- The pseudonym is data minimization, not anonymization. A party that already
  possesses candidate source bytes can compare hashes, and identical documents
  deliberately produce the same identifier.
- Twelve hex characters provide a compact display label, while the full SHA-256
  field remains necessary to disambiguate a rare prefix collision.
- New runtime source files require an explicit allowlist and archive-test change;
  a file is never added to a candidate merely because it exists under `src`.

## Revisit conditions

Revisit the public identifier only with a versioned schema/privacy decision and
a migration plan. Revisit the source allowlist only when a reviewed runtime file
is added or removed; do not replace the exact set with a denylist or live-tree
archive build.
