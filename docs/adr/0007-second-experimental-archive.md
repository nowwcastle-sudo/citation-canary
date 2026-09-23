# ADR-0007: Second experimental archive

- Date: 2026-09-24
- Status: accepted for release preparation; publication requires the release gates below
- Follows: ADR-0006

Prepare `v0.2.0-experimental.2` as a new prerelease with
`citation-canary-0.2.0-experimental.2.pyz` and its same-name `.sha256`
sidecar. Keep the `v0.2.0-experimental.1` tag, release and original assets
unchanged. ADR-0006's eleven-entry count describes that first archive, not the
new one.

The new archive has exactly fifteen entries: twelve allowlisted runtime Python
files, the package directory, generated root entrypoint and unchanged Apache
`LICENSE`. It adds the local review ledger, static HTML rendering and
conservative report comparison already implemented in source. It retains
offline operation, separate outputs, explicit review dates, source preservation,
fixed evidence statuses and resource guards. It does not authenticate official
sources, decide legal correctness or prove human adoption.

Before publication, identify the final source commit, verify the configured
Windows/Python CI on that commit, complete scoped source and security review,
rebuild and compare exact archive members and SHA-256, and confirm the private
vulnerability-reporting channel. Publish the new tag and both assets only after
those gates. Then verify anonymous downloads and matching checksums. Keep the
earlier verified asset for rollback; never replace it in place.
