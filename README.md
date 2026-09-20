# Citation Canary — experimental OSS

[English](https://github.com/nowwcastle-sudo/citation-canary/blob/main/README.md) · [한국어](https://github.com/nowwcastle-sudo/citation-canary/blob/main/README.ko.md)

Citation Canary reviews citation candidates in an existing local HWPX document
without modifying the file or accessing the network. It matches candidates
against an operator-supplied, dated official-source catalog and produces an
evidence report for human review. This is **experimental open-source software**.
Legal correctness, case authenticity and real human adoption are unverified.
Use it to assemble a local review queue before checking citations yourself.
`--demo` creates fictional inputs; a real scan reads your inputs and writes a
report only to stdout or the requested output file.

License: Apache License 2.0. See [`LICENSE`](LICENSE).

## What it does

| Stage | Input and behavior | Result or boundary |
| --- | --- | --- |
| Read | One HWPX ZIP/XML document and one local catalog | Collects section text nodes; no HWP, PDF, DOCX or image/OCR input |
| Find | Exact titles already in the catalog | Associates the first following `제N조` or `제N조의N` within 32 characters, before the next title, in the same text node |
| Match | Explicit review date and catalog version intervals | Assigns `CURRENT`, `HISTORY`, `REVIEW` or `UNKNOWN`, with a reason |
| Report | Candidate locations, catalog evidence and source hashes | JSON for human review; no automatic corrections |

Titles split across text nodes, spelling variants, and detailed paragraph/item
semantics are outside this narrow matching rule. An unmatched marker such as
`법`, `규정`, `고시`, `훈령` or `예규` can produce an ambiguous candidate. Some
unsupported citations produce no candidate. The scanner checks source identity
again before returning a report; a changed source yields
`SOURCE_CHANGED_DURING_SCAN` with no evidence items.

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
The fixed `v0.2.0-experimental.1` release archive has eleven entries,
including the Apache license. A build from the current source has a different
allowlist; see the candidate section below.

The tag and assets for `v0.2.0-experimental.1` remain fixed. Repository `main`
documentation may be newer than the README at that fixed release tag;
`README.ko.md` is a repository-only translation and is not an extra zipapp entry.
Use the tagged documentation when checking exactly what a downloaded release
contains.

## Local review candidate (source build, not the tagged release)

The current source tree adds a separate human-decision ledger, conservative
report comparison, and an offline HTML view. These commands are **not** in the
fixed `v0.2.0-experimental.1` download above. Build a local candidate from
this source tree; its exact package has 15 members rather than that release's
11. No new release or remote availability is implied. From the repository
root in PowerShell, choose unused output names and run one line at a time:

```powershell
python .\tools\build_zipapp.py --source .\src --output .\local-review-candidate.pyz
python .\local-review-candidate.pyz --demo .\local-review-demo
python .\local-review-candidate.pyz --document .\local-review-demo\synthetic-review.hwpx --as-of 2024-12-31 --catalog .\local-review-demo\catalog.json --output .\local-review-report.json
python .\local-review-candidate.pyz review --report .\local-review-report.json --ledger .\local-review-ledger.json --action decide --item 1 --disposition investigate
python .\local-review-candidate.pyz render --report .\local-review-report.json --ledger .\local-review-ledger.json --output .\local-review.html
python .\local-review-candidate.pyz compare --before .\local-review-report.json --after .\local-review-report.json
```

The same-report comparison is a command check, not proof of a reviewed
revision. To compare changed document hashes, provide two reports and
`--related-versions` only when you know their relationship; matches remain
candidates and decisions do not transfer. The report, ledger and HTML can
carry sensitive citation identifiers. Keep them local and do not attach them
to issues. See [local review and recovery](docs/local-review.md) and the
[local verification ledger](docs/local-completion-verification.md).

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

You need a terminal and Python 3.11 or newer. On Windows, open PowerShell in the
download folder. If `python` is unavailable, install Python from
[python.org](https://www.python.org/downloads/), reopen PowerShell, and confirm
the version before continuing. Hancom Office and an API key are not required
to run the scanner. The examples below use Windows PowerShell paths.

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

## Scan your own document

Prepare a separate catalog using the [schema guide](docs/catalog-schema-v1.md).
Confirm the official source outside this program, then enter its exact title,
provision labels, stable provision IDs, version intervals, HTTPS source URL and
retrieval timestamp. The root has `schema_version` (the string `"1"`) and a
nonempty `records` array. Each record has `record_id`, `official_source`, and
`versions`; the guide lists every required nested field and a complete example.
Extra fields and duplicate JSON keys are rejected.

Version intervals include `effective_from` and exclude `effective_to`. Versions
must be ordered without overlap; the last version must have `effective_to: null`.
Keep the same `canonical_id` only when human review establishes that a provision
continues across versions. Save the file as UTF-8 without BOM. The scanner
does not authenticate official authority, decide continuity, or enforce freshness.
The fictional demo catalog is unsuitable as evidence for a real document.

Place the reviewed document at `review-input.hwpx` and the separately prepared
catalog at `review-catalog.json` in the verified zipapp folder. Keep a copy of
the original document. Run the following block there; it asks for the review
date explicitly. Choose an unused report name before repeating it.

```powershell
$reviewDate=Read-Host 'Review date (YYYY-MM-DD)'
python .\citation-canary-0.2.0.pyz --document .\review-input.hwpx --as-of $reviewDate --catalog .\review-catalog.json --output .\review-report.json
$LASTEXITCODE
Get-Content -Raw -Encoding UTF8 -LiteralPath '.\review-report.json'
```

Check the exit code before reading a saved report. A failed run may leave an
older report at the same path. Confirm `as_of`, `document_sha256` and
`catalog_sha256`, inspect `collection_errors`, then review the items. A scan
cannot decide which date applies to your document.

Current-source scans also enforce [structural and reference-processing limits](docs/runtime-resource-limits.md).
Large or repetitive inputs fail with `HWPX_LIMIT_EXCEEDED` or
`REFERENCE_LIMIT_EXCEEDED` and no partial evidence items. These limits can reject
a valid large document; they are not a legal finding. Use a reviewed small
catalog and preserve the original input for a separately scoped review.

The current source limits compressed input to 100 MiB, archive entries to
10,000, each section to 20 MiB, and total uncompressed members to 200 MiB.
Across sections it permits 200,000 XML elements, 100,000 text elements and
20 × 1,024 × 1,024 retained characters; nesting depth is limited to 128 and
section-number suffixes to 32 digits. Reference extraction permits 100,000
examined matches and 10,000 candidates, both per text node and per document.
These limits do not bound independently supplied catalog loading/resolution or
promise a fixed runtime or peak memory use. See the linked guide for counting
rules and release-specific source details.

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

The report root contains `schema_version`, `document_name`, `document_sha256`,
`as_of`, `catalog_sha256`, `items`, and `collection_errors`. Each item includes
`locator`, `reference`, `status`, `reason_code`, and `evidence`.
Collection errors include `code`, `stage`, `fatal`, `locator`, and `message`.
Start with collection errors: an empty `items` array after a fatal failure
means the scan could not supply evidence.

## Troubleshooting

| Symptom or message | What to check |
| --- | --- |
| Checksum mismatch | Stop; preserve the files and download the matching pair into a new folder. |
| `ARGUMENT_ERROR` | Supply all three scan inputs, or use `--demo` alone. Option abbreviations are not accepted. |
| `Invalid --as-of date. Expected YYYY-MM-DD.` | Use a real calendar date in that exact format. |
| `Document file was not found.` / `Catalog file was not found.` | Check the working folder and actual filename; quote paths containing spaces. |
| `Catalog is not valid UTF-8 JSON.` | Check UTF-8 without BOM, JSON syntax and duplicate keys. |
| `Catalog does not conform to schema version 1.` | Check exact fields, dates, intervals, URLs, timestamps and unique IDs against the schema guide. |
| `DEMO_DESTINATION_INVALID` | Choose a new directory under an existing parent; preserve previous or partial demo files. |
| `DEMO_CREATE_FAILED` | Check write access and storage; partial files remain. Retry with a new directory. |
| `HWPX_LIMIT_EXCEEDED` / `REFERENCE_LIMIT_EXCEEDED` | Preserve the original; arrange a separately scoped review. Do not treat empty items as clearance. |
| `SOURCE_CHANGED_DURING_SCAN` | Stop concurrent editing and scan a stable local copy. |
| `UNEXPECTED_ERROR` | Check output-parent existence, write access and storage; record the safe message and exit code for support. |
| Exit `0` with `REVIEW`, `UNKNOWN`, or no items | Inspect the reasons and extraction limits. Exit `0` describes execution, not legal correctness. |

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
