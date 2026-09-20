# ADR-0004: Explicit packaged synthetic onboarding

- Date: 2026-09-05
- Status: accepted; private-only distribution superseded by [ADR-0006](0006-experimental-oss-publication.md)
- Extends: ADR-0002 CLI scope and ADR-0003 exact source allowlist; all ordinary scan/privacy invariants remain in force

## Context

All three virtual Citation Canary users acquired the private release and reached
help but could not prepare its mandatory catalog from the release instructions.
The runtime was tested through repository-only fixture builders; recipients of
the pyz had no equivalent documented first-success path. Existing UTF-8 output
and its cp1252 subprocess regression already pass.

## Decision

- Add an explicit `--demo NEW_DIRECTORY` mode, separate from ordinary scanning.
  It cannot be combined with scan options and never runs as automatic recovery.
- Add one internal `demo.py` module. It exclusively creates a synthetic HWPX,
  a schema-v1 catalog and a README in a new, previously nonexistent directory.
- Use fixed fictional metadata and `https://example.invalid/` source labels.
  At explicit demo date 2024-12-31, the real scanner returns the four existing
  evidence statuses. These examples do not establish official legal facts.
- Emit a separate safe creation manifest with relative filenames only. Preserve
  the existing `scan_document` signature, ScanReport schema, source pseudonym,
  status meanings and ordinary exit/error behavior.
- Reject existing destinations, path traversal components and observed
  symlink/reparse ancestry. Use exclusive creation and preserve partial failure
  artifacts instead of deleting or overwriting them. This is a local setup
  operation explicitly requested by the operator.
- Extend the exact source allowlist from seven to eight files with
  `citation_canary/demo.py`; the archive has exactly ten members including the
  package directory and generated root entrypoint. Keep independent archive
  test expectations and all deterministic/path/bytecode protections.
- Provide the exact user catalog contract in `docs/catalog-schema-v1.md` and
  link it from README/help. Keep HTML documentation outside runtime source.
- Target the new private candidate `v0.2.0-private.1` with artifact
  `citation-canary-0.2.0.pyz`; historical tags/assets are not modified.

## Consequences and limits

Recipients can demonstrate an end-to-end scan without repository test helpers
or real institution documents. Ordinary scanning still has no write, upload,
network, legal-decision or document-change capability.

Synthetic generation is an explicit exception to the former read-only CLI
surface. It is not a new public scanner API. Catalog freshness, permitted
official-source access, real use/procurement evidence, public privacy/licensing
and release authorization remain separate gates.

The minimal synthetic HWPX is a scanner fixture, not an editor-compatible form.
Portable preflight checks and exclusive creation do not claim to defeat a
hostile concurrent filesystem replacement attacker; a stronger platform threat
model would require a separately reviewed design.
