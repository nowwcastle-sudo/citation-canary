# Build and manage the experimental release

This procedure builds experimental OSS from a checkout of
https://github.com/nowwcastle-sudo/citation-canary on main.
For release-equivalent source, check out tag v0.2.0-experimental.1.
A local build is not a published release; keep its output and source identity.

The fixed tagged release archive contains eleven entries: eight runtime Python
files, the package directory, the generated root entrypoint and `LICENSE`.
A build from the current source checkout contains fifteen entries: twelve
runtime Python files, the package directory, the generated root entrypoint
and `LICENSE`. The commands below build whichever checkout you selected; do
not label a current-source candidate as the historical release asset.
It includes no source HWPX, catalog, report, documentation or test fixture.
Python 3.11 or newer must already be installed; no package installation is
needed. Use synthetic inputs only for this procedure.

## Build from the checkout

Open PowerShell in the repository root, where `LICENSE`, `src` and `tools` are
visible. Run the following lines in order in the same PowerShell session and
stop on any error. The interpreter check rejects the WindowsApps launcher;
if Python is unavailable, install/configure a real Python 3.11+ interpreter
before returning to this procedure.

```powershell
$ErrorActionPreference = 'Stop'
$citationPython = (Get-Command python.exe -CommandType Application -ErrorAction Stop).Source
if ($citationPython -match '\\WindowsApps\\') { throw 'Select an installed Python interpreter, not the WindowsApps launcher.' }
& $citationPython -c 'import sys; print(sys.executable); print(sys.version); sys.exit(0 if sys.version_info >= (3, 11) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
$citationSource = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Open PowerShell in the repository checkout.' }
$citationTracked = @(git --no-optional-locks status --porcelain=v1 --untracked-files=no)
if ($LASTEXITCODE -ne 0) { throw 'Cannot record tracked checkout state.' }
$citationBuild = Join-Path (Get-Location).Path ('dist\public-candidate-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $citationBuild | Out-Null
$citationArtifact = Join-Path $citationBuild 'citation-canary-local-candidate.pyz'
& $citationPython .\tools\build_zipapp.py --source .\src --output $citationArtifact
if ($LASTEXITCODE -ne 0) { throw 'Build failed; preserve this directory for inspection.' }
$citationHash = (Get-FileHash -LiteralPath $citationArtifact -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText(($citationArtifact + '.sha256'), ($citationHash + '  citation-canary-local-candidate.pyz' + "`n"), [Text.Encoding]::ASCII)
[IO.File]::WriteAllLines((Join-Path $citationBuild 'source.txt'), @("source_commit=$citationSource", "tracked_changes=$($citationTracked.Count -gt 0)"), [Text.Encoding]::ASCII)
Get-Content -LiteralPath ($citationArtifact + '.sha256')
Get-Content -LiteralPath (Join-Path $citationBuild 'source.txt')
```

The builder returns exit `0` after verifying its exact allowlist and installing
the archive. The sidecar records the bytes just built; it is not independent
proof of publisher authenticity. `source.txt` records the checkout commit and
whether tracked changes were present. If `tracked_changes=True`, do not claim
the archive was built solely from that commit. Retain the corresponding diff
for local review and establish final source identity before publication.

## Run the packaged synthetic example

Continue in the same session. The unique build directory gives the demo and
report new destinations. `--demo` creates fictional input and is separate from
the scan.

```powershell
$citationExpected = (Get-Content -Raw -LiteralPath ($citationArtifact + '.sha256')).Split(' ')[0]
if ((Get-FileHash -LiteralPath $citationArtifact -Algorithm SHA256).Hash.ToLowerInvariant() -cne $citationExpected) { throw 'Checksum mismatch; do not run the artifact.' }
& $citationPython $citationArtifact --help
if ($LASTEXITCODE -ne 0) { throw 'Candidate help failed.' }
$citationDemo = Join-Path $citationBuild 'demo'
& $citationPython $citationArtifact --demo $citationDemo
if ($LASTEXITCODE -ne 0) { throw 'Demo failed; preserve partial files and use a new build directory next time.' }
$citationReport = Join-Path $citationBuild 'citation-report.json'
& $citationPython $citationArtifact --document (Join-Path $citationDemo 'synthetic-review.hwpx') --as-of 2024-12-31 --catalog (Join-Path $citationDemo 'catalog.json') --output $citationReport
if ($LASTEXITCODE -ne 0) { throw 'Synthetic scan failed; preserve its output.' }
Get-Content -Raw -Encoding UTF8 -LiteralPath $citationReport
```

Expected: demo exit `0` with `SYNTHETIC_DEMO_ONLY`, then scan exit `0` and a
separate UTF-8 JSON report with `collection_errors: []`. The four items are
ordered `CURRENT`, `HISTORY`, `REVIEW`, `UNKNOWN`, with reasons
`EXACT_CURRENT_MATCH`, `EXACT_HISTORICAL_MATCH`, `PROVISION_MISMATCH`,
`AMBIGUOUS_CITATION`. These are fictional examples, not legal conclusions.

Use the checkout's [catalog schema guide](../catalog-schema-v1.md). The
packaged help links the experimental release's catalog guide; local edits
may differ from that tag. An XML locator is not a page
number, and zero candidates does not prove exhaustive citation coverage.

## Before any public release

Keep the candidate hash, exact final source identity, applicable CI and scoped
security review together. Check [SECURITY.md](../../SECURITY.md) and the
[experimental publication decision](../adr/0006-experimental-oss-publication.md)
for the release scope.
This local procedure does not change visibility, create a release or replace
an existing asset. Human usability, official-source accuracy, repeat use and
procurement remain unverified. Never attach real HWPX, catalog or report bodies
to a public issue.

## Update and rollback

Download each release into a new folder and verify its own checksum before
running it. Keep the previous verified artifact and its checksum. Roll back by
running that retained artifact explicitly; do not overwrite inputs or reports.
Compare documented schema/behavior changes before reusing catalogs. Do not use
an older release with a known unresolved vulnerability on untrusted documents.
