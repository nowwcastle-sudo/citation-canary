# Citation Canary — experimental OSS

Citation Canary reviews citation candidates in an existing local HWPX document
without modifying the file or accessing the network. It matches candidates
against an operator-supplied, dated official-source catalog and produces an
evidence report for human review. This is **experimental open-source software**.
Legal correctness, case authenticity and real human adoption are unverified.
The first experimental release provides explicit synthetic setup with
`--demo`; ordinary scanning remains read-only.

License: Apache License 2.0. See [`LICENSE`](LICENSE).

## Download the experimental release

Download both files from the [v0.2.0-experimental.1 release](https://github.com/nowwcastle-sudo/citation-canary/releases/tag/v0.2.0-experimental.1).
No GitHub account or token is needed for public downloads.

- [citation-canary-0.2.0.pyz](https://github.com/nowwcastle-sudo/citation-canary/releases/download/v0.2.0-experimental.1/citation-canary-0.2.0.pyz)
- [citation-canary-0.2.0.pyz.sha256](https://github.com/nowwcastle-sudo/citation-canary/releases/download/v0.2.0-experimental.1/citation-canary-0.2.0.pyz.sha256)

Save both in a new folder. Stop if either download fails; preserve the failed
files and use a fresh folder when retrying. Never substitute a checksum from
another release. SHA-256 detects mismatched bytes, not publisher authenticity.
The program itself runs offline after download.

To build from source, follow the [source build guide](docs/release/public-candidate.md).
The exact archive has eleven entries, including the Apache license.

## Boundaries

- Requires Python 3.11 or newer. The release is a Python zipapp
  (`.pyz`), so it needs no package installation.
- For a scan, the operator supplies the local HWPX, an explicit `--as-of` date, and a
  local UTF-8 catalog that conforms to catalog schema version `"1"`.
- A genuine catalog is not bundled or refreshed by the program. The separate
  `--demo` mode creates fictional learning inputs. Before a meaningful
  scan, the operator must confirm its official-source provenance and freshness.
- Source documents stay local. The program makes no network request, upload,
  telemetry call, authentication request, or update check.
- It does not edit or auto-correct an HWPX, and its evidence statuses are not
  legal, compliance, validity, or mandatory-change verdicts.

## Verify and run

Download both assets from the public
[v0.2.0-experimental.1 prerelease](https://github.com/nowwcastle-sudo/citation-canary/releases/tag/v0.2.0-experimental.1)
to the same folder, then open PowerShell in that folder:

- `citation-canary-0.2.0.pyz`
- `citation-canary-0.2.0.pyz.sha256`

Verify the downloaded artifact before running it in PowerShell:

```powershell
$checksumText=Get-Content -Raw -LiteralPath '.\citation-canary-0.2.0.pyz.sha256'
if ([string]::IsNullOrWhiteSpace($checksumText)) { throw 'Checksum file is empty.' }
$expected=$checksumText.Split("`n")[0].Split('  ')[0]
$actual=(Get-FileHash -LiteralPath '.\citation-canary-0.2.0.pyz' -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -cne $expected) { throw 'Checksum mismatch. Do not run this artifact.' }
python --version
python .\citation-canary-0.2.0.pyz --help
```

`python --version` must report 3.11 or newer. Run every line in order; stop on a
checksum mismatch before executing the artifact. Public downloads require no
authentication; the program itself has no authentication.

## First run: generate, then scan

Run from the folder containing the verified pyz. `citation-demo` must not exist
yet. This command explicitly creates fictional learning inputs; it does not
perform a scan.

```powershell
python .\citation-canary-0.2.0.pyz --demo .\citation-demo
$LASTEXITCODE
```

Expected: exit 0 and a manifest with `notice: SYNTHETIC_DEMO_ONLY`. Exactly
`synthetic-review.hwpx`, `catalog.json`, and `README.txt` are created inside the
new directory. Every source URL uses `example.invalid`; titles, effective
dates and retrieval metadata are fictional. The HWPX is a minimal scanner
sample, not an editable Hancom form or an institutional document.

The demo may print a small JSON notice to stdout; that is intentional and is
not a scan report. A scan report is written to stdout only when `--output` is
omitted. For support handoff, prefer the explicit UTF-8 `--output` path below.

An existing directory, even empty, is rejected. Keep old or partially created
files and choose a different new directory for another attempt. Missing parent
directories, `..` components, and observed symlink/reparse paths are rejected.
`--demo` cannot be combined with scan options.

Now scan the generated pair with the fixed fictional date `2024-12-31`:

```powershell
python .\citation-canary-0.2.0.pyz --document .\citation-demo\synthetic-review.hwpx --as-of 2024-12-31 --catalog .\citation-demo\catalog.json
$LASTEXITCODE
```

Expected: exit 0, `collection_errors: []`, and exactly four items in order:
`CURRENT`, `HISTORY`, `REVIEW`, `UNKNOWN`. Their reasons are
`EXACT_CURRENT_MATCH`, `EXACT_HISTORICAL_MATCH`, `PROVISION_MISMATCH`, and
`AMBIGUOUS_CITATION`. A successful scan can contain `REVIEW` or `UNKNOWN`.

Write the same report to a separate UTF-8 file:

```powershell
python .\citation-canary-0.2.0.pyz --document .\citation-demo\synthetic-review.hwpx --as-of 2024-12-31 --catalog .\citation-demo\catalog.json --output .\citation-report.json
$LASTEXITCODE
Get-Content -Raw -Encoding UTF8 -LiteralPath '.\citation-report.json'
```

Expected: exit 0, no report on stdout during the scan, and UTF-8 JSON in the
requested file. Use a new report name to preserve a prior report: an existing
explicit output is atomically replaced. The HWPX and catalog cannot be output
targets. Windows PowerShell 5.1 can decode/redirect native stdout differently;
use `--output` for the saved report and read with explicit `-Encoding UTF8`.

The complete [catalog schema-v1 guide](docs/catalog-schema-v1.md) defines every
field, provides the exact synthetic example, and gives creation/save/review
instructions. Save UTF-8 without BOM. Genuine official-source identity,
historical continuity, permitted access and freshness require human review;
the runtime only checks URL syntax and never fetches a source.

Extraction starts from titles present in the catalog and operates per XML text
node with narrow article grammar. **Zero candidates is not exhaustive clearance
or a statement that a document contains no citations or legal issues.**

Options (scan requirements apply only when `--demo` is absent):

- `--document` (required): one local `.hwpx` input.
- `--as-of` (required): explicit review date in strict `YYYY-MM-DD` form.
- `--catalog` (required): one local UTF-8 schema-v1 catalog JSON file.
- `--output` (optional): a separate JSON report path. If omitted, JSON is
  written to standard output. It must not be the document or catalog path.
- `-h` / `--help`: show the option list.
- `--demo NEW_DIRECTORY`: explicit synthetic setup, exclusive of all scan options.

Keep the original HWPX unchanged and keep report output separate from it.

Current-source scans also enforce [structural and reference-processing limits](docs/runtime-resource-limits.md).
Large or repetitive inputs fail with `HWPX_LIMIT_EXCEEDED` or
`REFERENCE_LIMIT_EXCEEDED` and no partial evidence items. These limits can reject
a valid large document; they are not a legal finding. Use a reviewed small
catalog and preserve the original input for a separately scoped review.

## Report and exit contract

Reports use a SHA-derived pseudonymous document label
(`document-<12hex>.hwpx`) plus the full document and catalog SHA-256 values.
They contain review locators and catalog evidence, not raw HWPX paragraphs or
the operator's source basename. This is data minimization, not anonymization:
do not attach HWPX files, report bodies, catalog contents, secrets, or local
paths to an issue.

Each report item has exactly one evidence-routing status:

| Status | Meaning |
| --- | --- |
| `CURRENT` | The narrow catalog identity/provision check aligns for `--as-of`; it is not a legal conclusion. |
| `HISTORY` | The citation aligns with an earlier effective version and a later catalog transition is shown; it is not automatically an error. |
| `REVIEW` | Evidence is conflicting, discrepant, or date-sensitive and needs human inspection; it does not mean invalid. |
| `UNKNOWN` | The available catalog basis is insufficient or ambiguous; the report gives the reason. |

Use the status to choose the next review action:

| Status | Next action |
| --- | --- |
| `CURRENT` | Keep the evidence for the stated date and complete any required human review. |
| `HISTORY` | Compare the stated date with the later transition before deciding whether the wording needs an update. |
| `REVIEW` | Open the cited source and document context, then record the human disposition separately. |
| `UNKNOWN` | Gather a better catalog entry or clearer citation context. Do not treat it as safe or as an automatic correction. |

Collection errors are separate from these statuses and fail closed. Process
exits are stable:

| Situation | Exit |
| --- | ---: |
| Successful scan with no collection errors | `0` |
| Scan completes with a collection error | `1` |
| Unexpected runtime/output failure | `1` |
| Argument or request error (including an invalid date or catalog) | `2` |
| Successful demo creation with a safe relative-filename manifest | `0` |
| Invalid/reused demo destination: `DEMO_DESTINATION_INVALID` | `2` |
| Demo creation I/O failure: `DEMO_CREATE_FAILED`; partial files retained | `1` |

Safe errors are written to standard error; do not expect a traceback or the
operator's raw local path.

`locator`, for example `Contents/section0.xml:t[2]`, is an XML text-node
location, not a page number. `reference` names the detected title/provision;
`evidence` contains the catalog source, retrieval timestamp and matched date
interval. A historical row can include `version_transition`. Inspect the
reason and evidence before recording a human disposition; no document edit
follows automatically.

## Support and release limits

Use [GitHub Issues](https://github.com/nowwcastle-sudo/citation-canary/issues)
for synthetic reproductions and nonsensitive bug reports. Include the release
tag, Python version, command form, exit code and fixed error code/message.
Do not publish real HWPX, report bodies, catalog contents, local paths or source
hashes: even pseudonyms and hashes can link a document to its source.
See [SECURITY.md](SECURITY.md) for private vulnerability reporting.

This repository is licensed under Apache License 2.0; the zipapp includes
the unchanged [LICENSE](LICENSE). Release ownership is with `nowwcastle-sudo`.
There is no support SLA, legal accuracy guarantee, case-authenticity guarantee,
or established human-adoption claim. Synthetic onboarding does not establish
repeat use, procurement or legal accuracy.

[Windows compatibility](docs/compatibility/windows.md) describes the CI scope.
Read [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating.
The [source build guide](docs/release/public-candidate.md) also explains update
and rollback. Public software availability does not approve hosted processing
of sensitive documents.
