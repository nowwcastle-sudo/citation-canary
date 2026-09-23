# Citation Canary Local Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind human decisions and timing to unchanged scan reports, compare reports conservatively, and render offline review HTML.

**Architecture:** Four focused standard-library modules own bounded report IO, review events, comparison and HTML. New CLI commands dispatch before the existing scan/demo parser. No changes to scanner classification or source documents.

**Tech Stack:** Python 3.11+, unittest, standard library, existing zipapp builder.

**Spec:** `docs/superpowers/specs/2026-09-20-local-completion-design.md` (owner approved 2026-09-20).

## Global Constraints

- Preserve `scan_document`, scan/demo CLI and schema-1 ScanReport. No network, database, HWPX mutation, legal verdict or automatic decision transfer.
- New JSON input: 8 MiB/file; 10000 report items; 50000 ledger events. Reject duplicate keys, nonfinite numbers, unknown fields/schema, invalid types/enums/indexes; bool is not an integer index.
- All outputs explicit; reject input aliases, hardlinks and reparse/symlink paths, including parents. HTML is no-clobber. Only `review` may replace a validated ledger.
- Preserve failed temporary writes and the previous valid ledger. Error output uses fixed codes, never raw paths or exception messages.
- Verify APIs against Python official documentation or Context7 before implementation; use ponytail full and karpathy-guidelines. Back up existing files outside the source tree before editing. Test, scan staged changes for credentials, then commit; never commit failed verification.
- Existing tag/assets remain immutable. New packages are local candidates until a separate release decision. Full regressions are expressly requested.

## Review Focus

1. Two references share a locator: item numbers remain independent (Task 2).
2. Boolean indexes and duplicate escaped JSON keys cannot bypass validation (Task 1).
3. Concurrent writer or interrupted replacement must preserve previous bytes, with no stale-lock auto-deletion (Task 2).
4. Reordered or duplicated references across document versions cannot inherit decisions or imply resolution (Task 3).
5. A source URL containing quotes, userinfo or a non-HTTPS scheme cannot inject HTML or expose credentials (Task 3).

## File and interface map

Create `src/citation_canary/review_io.py`, `review.py`, `comparison.py`, `review_html.py`; respectively own strict IO, ledger, pure comparison and pure rendering. Modify only CLI dispatch and package contracts outside these modules. Public JSON values are `dict[str, object]`; arrays are lists, never dataclass instances at this boundary. Validation returns owned deep copies.

## Task 1: Strict saved-report input and safe fresh output

**Files:** Create `src/citation_canary/review_io.py`, `tests/test_review_io.py`.

**Interfaces:** `read_json(path: Path) -> dict[str, object]`; `validate_report(value: object) -> dict[str, object]`; `canonical_digest(value: object) -> str`; `write_new(path: Path, payload: bytes, protected: tuple[Path, ...]) -> None`. All expected failures raise existing `ScanRequestError(code, safe_message)` with identical fixed code/message.

- [ ] Add failing tests using the real existing report serializer:

```python
import unittest
from citation_canary.report import ScanReport, ScanRequestError
from citation_canary.review_io import validate_report, canonical_digest

class ReviewInputTests(unittest.TestCase):
    def test_empty_report_is_valid_but_not_review_complete(self):
        value = ScanReport('1', 'synthetic.hwpx', 'a'*64, '2024-12-31',
                           'b'*64, (), ()).to_dict()
        self.assertEqual(validate_report(value), value)
        self.assertEqual(canonical_digest(value), canonical_digest(dict(reversed(list(value.items())))))
    def test_boolean_schema_is_not_version(self):
        with self.assertRaises(ScanRequestError):
            validate_report({'schema_version': True})
```

- [ ] Run `python -m unittest tests.test_review_io -v` with `PYTHONPATH=src`; expected initial failure: new module missing. The existing scanner's schema literal is the string `'1'`; never alter scanner to satisfy fixture.
- [ ] Implement schema by walking every field in `report.py::ScanReport.to_dict`: exact keys at each level, enum statuses, SHA-256 strings, canonical dates, evidence transitions and collection errors. Impose depth 32 and 200000 JSON nodes in addition to byte/item limits. Parse duplicate keys via `object_pairs_hook`, reject constants via `parse_constant`, catch nesting/UTF-8 errors into fixed codes.

```python
def canonical_digest(value: object) -> str:
    import hashlib, json
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()
```

- [ ] Add and execute tests for 8 MiB exact/over, 10000/10001 items, malformed UTF-8, escaped duplicate keys, NaN, unknown nested fields, 33-depth input, file replaced while reading, source-byte invariance. Read through one handle, compare identity/size/mtime before and after and current path identity; reject nonregular/reparse inputs.
- [ ] Implement `write_new` using exclusive creation and checked regular parent paths, reject all protected aliases before opening, write/flush/fsync without overwriting. Retain failed artifact; report fixed failure. Test existing destination, hardlink input, parent junction and source hashes. Do not reuse `_write_atomic` for fresh output because it overwrites.
- [ ] Run `python -m unittest tests.test_review_io -v`; require assertions executed and exit 0. Scan staged diff for secrets. Commit only these files: `git add src/citation_canary/review_io.py tests/test_review_io.py`; `git commit -m "feat: validate bounded local review inputs"`.

## Task 2: Bound append-only decision events and measured intervals

**Files:** Create `src/citation_canary/review.py`, `tests/test_review_ledger.py`; modify `src/citation_canary/__main__.py`; create `tests/test_review_cli.py`.

**Interfaces:** Consume Task 1 IO/digest and existing `ScanRequestError`. Produce `new_ledger(report: dict[str, object]) -> dict[str, object]`, `validate_ledger(ledger: object, report: dict[str, object]) -> dict[str, object]`, `append_event(ledger: dict[str, object], report: dict[str, object], *, action: str, item_number: int | None, disposition: str | None, stage: str | None, at: str) -> dict[str, object]`, `review_summary(ledger: dict[str, object], report: dict[str, object]) -> dict[str, object]`, `update_ledger(path: Path, report_path: Path, *, action: str, item_number: int | None, disposition: str | None, stage: str | None) -> None`.

- [ ] Add failing test: build two ScanItem dictionaries with the same locator but distinct references, bind new ledger, append `decide` twice for item 1 then once for item 2. Assert three events, final dispositions independently keyed by `'1'`/`'2'`, report unchanged. Include this minimal real invocation:

```python
ledger = new_ledger(report)
ledger = append_event(ledger, report, action='decide', item_number=1,
    disposition='confirm', stage=None, at='2026-09-20T00:00:00Z')
assert ledger['events'][0]['item_number'] == 1
assert report['items'][0]['status'] == 'REVIEW'
```

Construct `report` before the invocation as follows; use this same explicit construction in Task 3 cases that need a populated report:

```python
report = {'schema_version':'1', 'document_name':'synthetic.hwpx',
    'document_sha256':'a'*64, 'catalog_sha256':'b'*64, 'as_of':'2024-12-31',
    'items':[{'locator':'section0.xml:p1',
        'reference':{'title':title,'provision':'제1조'},
        'status':'REVIEW','reason_code':'SYNTHETIC_REVIEW','evidence':[]}
        for title in ('합성법 A','합성법 B')], 'collection_errors':[]}
```
- [ ] Run `python -m unittest tests.test_review_ledger tests.test_review_cli -v`; expect missing review module/unsupported command.
- [ ] Implement ledger envelope keys `schema='citation-review/1', report_digest, document_sha256, catalog_sha256, as_of, events`. Every event has `sequence, action, item_number, disposition, stage, at, previous_event_digest, digest`. Sequence starts 1, first previous digest null; digest covers the other event fields using canonical_digest. Validate the whole chain, exact keys, report binding, positive non-bool item range, UTC timestamps and enum disposition. `decide` requires item/disposition and null stage; `start`/`finish` require null item/disposition and stage in `triage|evidence|decision`. Timing state is separate from decisions.

```python
event['previous_event_digest'] = events[-1]['digest'] if events else None
event['sequence'] = len(events) + 1
event['digest'] = canonical_digest(event)
```

- [ ] Implement summary keys `latest_decisions` (decimal item-number keys), `unreviewed_count`, `disposition_counts`, `timing` (stage -> `{seconds: number|null, status: measured|unknown}`). Only paired intervals count; missing, reversed or overlapping intervals make affected timing unknown, never estimated. No claim of author authentication.
- [ ] Implement `update_ledger`: exclusive sibling `.lock` creation; capture original identity/digest; validate report+ledger; append with current UTC; sibling temp complete write+flush/fsync; recheck original identity/digest; atomic replace while holding lock. New ledger uses no-clobber promotion. Reject concurrent lock with `REVIEW_BUSY`, mismatch with `REVIEW_CONFLICT`; leave failed temp and old ledger. Close/remove only the lock owned by this call. Never auto-remove someone else's/stale lock. Check all ancestor reparse components and link count before replacement; disclose remaining adversarial path-race limitations instead of promising OS-wide isolation.
- [ ] Dispatch first CLI token `review` before legacy parser. Syntax: `review --report FILE --ledger FILE --action decide --item N --disposition ENUM` or `--action start|finish --stage triage|evidence|decision`. Reject mixed/duplicate flags. Success 0, invalid/busy/conflict 2, unexpected IO failure 1. Existing scan/demo path untouched.
- [ ] Run tests for corruption of each binding/hash, out-of-range and bool indexes, two independent concurrent processes, interrupted fsync/replace, stale lock preservation, 50000/50001 events, time gaps/reversal/overlap, original report hash, forged author claims rejection. Execute `python -m unittest tests.test_review_io tests.test_review_ledger tests.test_review_cli tests.test_cli -v`; require exit 0. Credential-scan staged files then `git add src/citation_canary/review.py src/citation_canary/__main__.py tests/test_review_ledger.py tests/test_review_cli.py`; `git commit -m "feat: record bound review decisions and timing"`.

## Task 3: Conservative comparison, static HTML and distributable commands

**Files:** Create `src/citation_canary/comparison.py`, `src/citation_canary/review_html.py`, `tests/test_review_compare.py`, `tests/test_review_html.py`; modify `src/citation_canary/__main__.py`, `tests/test_review_cli.py`, `tools/build_zipapp.py`, `tests/test_zipapp.py`, `README.md`, `README.ko.md`; create `docs/local-review.md`, `docs/local-completion-verification.md`.

**Interfaces:** Consume validated reports/ledgers and review_summary. Produce `compare_reports(before: dict[str, object], after: dict[str, object], *, related_versions: bool = False) -> dict[str, object]`; `render_review(report: dict[str, object], ledger: dict[str, object] | None = None) -> str`. CLI `compare --before FILE --after FILE [--related-versions]` writes JSON stdout; `render --report FILE [--ledger FILE] --output NEW_HTML` uses write_new. No network or ledger writes from either command.

- [ ] Add failing comparison/HTML tests:

```python
result = compare_reports(report, report)
assert result['changes'] == []
assert result['decision_transfer'] is False
html = render_review(report)
assert '<script' not in html.lower()
assert 'unreviewed' in html.lower()
```

Each test constructs a complete synthetic schema-1 report; a second injects `<script>alert(1)</script>` into document_name and asserts escaped text and no executable element.
- [ ] Run `python -m unittest tests.test_review_compare tests.test_review_html -v`; expect import failure before implementation.
- [ ] Implement compare result keys `schema='citation-comparison/1', comparable, relationship, changes, unresolved, decision_transfer=false`. Same-document matching key is `(item_number, locator, reference.title, reference.provision)`; reorder breaks exact match and is reported unresolved rather than resolved. Different document hashes require explicit related_versions; only unique title/provision pairs at unchanged locators become candidate matches, never confirmed same identity. Duplicate or moved references become unresolved. Emit separate `added`, `removed`, `status`, `evidence`, `catalog`, `as_of` change records with old/new item numbers. Collection errors set comparable false and forbid resolved classifications. Unrelated documents yield comparison unavailable, not mass deletions. Never load/transfer decisions into comparison.
- [ ] Implement escaped HTML with inline static CSS, no JS/assets/forms. Display error banner, all four status counts, unreviewed/disposition counts, timing unknowns and numbered items ordered REVIEW, UNKNOWN, HISTORY, CURRENT without renumbering. Evidence source anchors require parsed HTTPS URL, hostname, no userinfo/control characters; escape attribute and label separately. Hide document_name and raw locator from default heading/rows (item numbers identify items); show report digest and explicit sensitivity warning because citation identifiers are not anonymized.
- [ ] Add cases: catalog-only change, as_of only, additions/removals, duplicate/moved references, error report, empty report not completed, non-HTTPS/userinfo/quoted URL, escaped markup, invalid supplied ledger, output input-alias/exists/reparse, source hashes, render/compare attempting no socket access, scan bytes unchanged. Run new modules plus existing CLI tests and require exit 0.
- [ ] Add exactly four new module paths to SOURCE_ALLOWLIST and archive assertions: `citation_canary/review_io.py`, `citation_canary/review.py`, `citation_canary/comparison.py`, `citation_canary/review_html.py`. New candidate has 15 entries (12 runtime files + package directory + launcher + LICENSE); historical artifact stays 11. Test actual built zipapp commands, not only imports. Keep version/release changes outside this task.
- [ ] Document working synthetic scan -> review -> render -> compare commands in both READMEs, schema/limits/error recovery/no-authenticity and manual stale-lock inspection in `docs/local-review.md`. Read humanize-korean/no-ai-slop instructions before Korean prose changes. Record CC-L01/02/05 -> Task 2, CC-L03/04 -> Task 3, all IO -> Task 1 in verification table with source SHA, command, assertion count, exit and actual result; leave unexecuted rows explicitly not-run.
- [ ] Run `python -m unittest discover -s tests -v` and exact zipapp suite from existing CI on all configured Windows/Python combinations after authorized branch publication. Local result is not remote matrix proof. Review diff, scan credentials, then `git add src/citation_canary tools/build_zipapp.py tests README.md README.ko.md docs/local-review.md docs/local-completion-verification.md`; `git commit -m "feat: compare and render local citation reviews"` only after passing local verification.

## Self-review / execution boundary

All CC-L01–05 map to tasks above; Review Focus has an owning task and negative test. No product changes or test results are represented by this plan. Compare/render never write ledger; all new runtime files are included in the package contract. Before implementation, obtain plan review and preserve the selected execution method. External catalog integration remains conditional on demonstrated missing evidence, not automatic phase expansion.
