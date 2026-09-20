# Local citation review (source-built candidate)

This procedure applies to a candidate built from the current source tree. The
fixed `v0.2.0-experimental.1` release has only scan/demo commands and an
11-member archive. It does not contain `review`, `render`, or `compare`.

From the repository root in PowerShell, with Python 3.11 or newer, use unused
output paths. Run one line at a time and check `$LASTEXITCODE` after each
program call. The synthetic catalog uses fictional `example.invalid` sources.

```powershell
python .\tools\build_zipapp.py --source .\src --output .\local-review-candidate.pyz
python .\local-review-candidate.pyz --demo .\local-review-demo
python .\local-review-candidate.pyz --document .\local-review-demo\synthetic-review.hwpx --as-of 2024-12-31 --catalog .\local-review-demo\catalog.json --output .\local-review-report.json
python .\local-review-candidate.pyz review --report .\local-review-report.json --ledger .\local-review-ledger.json --action decide --item 1 --disposition investigate
python .\local-review-candidate.pyz review --report .\local-review-report.json --ledger .\local-review-ledger.json --action start --stage evidence
python .\local-review-candidate.pyz review --report .\local-review-report.json --ledger .\local-review-ledger.json --action finish --stage evidence
python .\local-review-candidate.pyz render --report .\local-review-report.json --ledger .\local-review-ledger.json --output .\local-review.html
python .\local-review-candidate.pyz compare --before .\local-review-report.json --after .\local-review-report.json
```

The `review` action must name a report, a separate ledger, and an original
one-based item number. `decide` takes `confirm`, `reject`, `investigate`, or
`defer`; it changes only the latest human disposition in the separate ledger,
not the report status. Its older events remain in the ledger. `start` and
`finish` take one of `triage`, `evidence`, or `decision`. Only valid recorded
pairs produce measured seconds. Missing, reversed, and overlapping intervals
remain `unknown`; no time saving is inferred. The ledger's hash chain detects
accidental alteration and is not an author signature.

`render` writes a new, no-clobber, standalone HTML file. Open it locally in a
browser. It groups items by REVIEW, UNKNOWN, HISTORY, CURRENT, preserving the
original item numbers for subsequent `review` commands. It shows counts,
latest dispositions, collection errors, evidence retrieval timestamps, and
unmeasured stages. It omits the raw locator from rows and keeps the escaped
document label in a collapsed disclosure outside the headings and rows.
Citation identifiers and evidence still are **not anonymized**. It contains
no scripts, remote assets, or automatic network
requests. Clicking a validated HTTPS evidence link is a separate user action.

`compare` writes JSON to standard output. For the same document hash, an exact
item number, locator, title, and provision match is compared even if another
item has identical citation fields. Moved or otherwise unmatched references
remain unresolved. Different source hashes are unavailable unless you supply
`--related-versions` based on your knowledge of the documents; even then a
unique unchanged-locator title/provision pairing is only a candidate; duplicate
references cannot be paired by position across changed document hashes. The
comparison does not read or transfer dispositions. Catalog changes, review
date changes, evidence and status changes are separate records. Collection
errors make the comparison unavailable for resolution claims. A zero-item
report or empty change list is not a completed legal review.

Input reports use scan schema string `"1"`; ledgers use
`"citation-review/1"`; comparisons emit `"citation-comparison/1"`. Saved
JSON inputs are strictly UTF-8 and capped at 8 MiB per file, 32 levels and
200,000 nodes; reports allow at most 10,000 items and ledgers at most 50,000
events. Exact fields, valid dates, no duplicate keys and finite numbers are
required. An event-count allowance does not override the byte/node budgets.
The supplied catalog is not authenticated or fetched. Independently verify
official provenance, effective dates, current availability, and permitted use
before relying on it. No status or disposition is a legal conclusion, case
authentication, or instruction to edit an HWPX. Scan never edits the source.

On `ARGUMENT_ERROR`, fix flags without reusing an old output as proof. On
`REVIEW_REPORT_INVALID`, `REVIEW_LEDGER_INVALID`, or `REVIEW_JSON_INVALID`,
preserve the input and generate a fresh report or investigate the ledger;
do not edit a hash chain by hand. `REVIEW_OUTPUT_EXISTS` means choose a new
HTML output path; it never overwrites an existing file or input alias.
`REVIEW_PATH_INVALID` includes symlink/reparse paths, hardlinks and unsafe
parents. Use a regular local directory. `REVIEW_WRITE_FAILED` or
`REVIEW_OUTPUT_FAILED` can leave a failed temporary output: retain it and
the previous ledger for diagnosis. Unexpected I/O failures exit 1; invalid
requests and conflicts exit 2. Fixed error codes avoid printing local paths.

If `REVIEW_BUSY` appears and a sibling `.lock` remains, inspect the exact
ledger path, lock ownership, and active writer manually. The tool never
assumes a lock is stale and never removes another writer's lock. Do not
delete a lock just to retry. Only the operator can decide a recovered path
after verifying no writer is active and preserving the ledger and failed
artifacts. A cooperating-writer lock and checked paths do not provide
OS-wide isolation against an adversarial concurrent process.

Keep HWPX, catalog, report, ledger, HTML, and raw hashes out of public
issues and logs. The synthetic demo proves only the command path, not
adoption, official evidence, legal accuracy, or a remote CI matrix result.
