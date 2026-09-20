# Security policy

## Supported scope

Local HWPX reading, schema-v1 catalog handling, separate evidence reports, synthetic demo generation, and deterministic PYZ packaging.

The current experimental release is v0.2.0-experimental.1. Security fixes target
current development; older releases have no backport promise. Supported runtime:
Python 3.11 or newer on the Windows versions covered by the current candidate CI.
Reports and statuses describe available evidence; they are not a security or
legal certification.

The current source rejects excessive XML structure and reference work using
the [documented resource budgets](docs/runtime-resource-limits.md). These
are input guards, not a process sandbox or a promise of a fixed peak memory.

## Report a vulnerability privately

For a published repository, use GitHub's **Security → Report a vulnerability**
control:
https://github.com/nowwcastle-sudo/citation-canary/security/advisories/new

If the control is unavailable, open an issue containing only a request for a
private reporting channel, without vulnerability details or sensitive data.
Wait for a private channel before sending the reproduction.

Include the release or source commit, runtime version, a minimal synthetic
reproduction, expected behavior, observed fixed error or exit code, and a
redacted impact summary. Do not attach credentials, customer documents, raw
workflow or catalog contents, personal information, or real incident data.

## Handling and disclosure

The repository owner triages reports on a best-effort basis; there is no
guaranteed response-time SLA. Keep reproduction artifacts private. Use a
coordinated disclosure date agreed with the reporter after impact and a fix or
mitigation are understood. Do not publish private report details automatically.

Credential exposure, unintended writes or network access, unsafe output or
archive handling, and privacy-boundary failures are in scope. Unsupported
inputs, unverified official-source content, and claims beyond the documented
evidence model are not proof of a vulnerability by themselves.

A public release requires completed source/security review, reproducible
artifact identity, a working private-reporting channel, and explicit owner
authorization. This policy does not activate GitHub features or publish a
release.
