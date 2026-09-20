# Local completion verification ledger

Scope: source-built local candidate only; no new public release, remote matrix,
official-source authentication, or legal outcome is asserted. Baseline source
commit before Task 3: `d2416bc653f0087c51c4ef5797871264b148146f`.
SHA-256 values below are local source-file bytes checked after the code tests.
Assertion counts are observed `unittest.TestCase.assert*` method calls in a
separate instrumented local run (nested assertion calls count separately);
the ordinary full-suite run below was not instrumented. `not-run` is not a pass.

| Requirement | Owner / source SHA-256 | Executed command / assertions | Exit | Actual result |
| --- | --- | --- | ---: | --- |
| Shared strict IO, path and limits | Task 1 / `review_io.py` `16e6a740884021eb9ba76b4cfdf6c5c8034fa3afa16b4ad95d9e9fa9a04f723e` | `python -m unittest tests.test_review_io` / 14 tests, 75 assertion calls | 0 | OK; strict input and no-clobber path tests |
| CC-L01 human disposition | Task 2 / `review.py` `6cc5c2539284dad18ed8da76a0f878dfab3161f893b3080d9f95fba5eec146bf` | `python -m unittest tests.test_review_ledger tests.test_review_cli` / 13+8 tests, 85+40 assertion calls across shared suite | 0 | OK; item-number binding and separate decision events |
| CC-L02 retained events and binding | Task 2 / same `review.py` SHA above | same Task 2 suite / shared 13+8 tests, 85+40 calls | 0 | OK; chain, report binding and failed-write preservation |
| CC-L05 explicit measured intervals | Task 2 / same `review.py` SHA above | same Task 2 suite / shared 13+8 tests, 85+40 calls | 0 | OK; valid intervals measured, missing/reversed/overlap unknown |
| CC-L03 conservative comparison | Task 3 / `comparison.py` `cfe483d8b2b18e6caa207392ae9ab01056334deaff3375d2bbc30920c12c458d` | `python -m unittest tests.test_review_compare` / 9 tests, 51 calls | 0 | OK; exact same-hash repeated positions, changed-hash duplicate ambiguity, changed catalog/date/status/evidence, error/empty guard |
| CC-L04 static HTML | Task 3 / `review_html.py` `55a0e72f3b568946bdf3ee32f0aebb03bf4c64f0659a5fc120d2617f9e13c9c1` | `python -m unittest tests.test_review_html` / 6 tests, 28 calls | 0 | OK; escaping, safe links, priority, digest and timing |
| CLI and 15-member source candidate | Task 3 / `__main__.py` `56f790e2ced92cb65e585fb22f51b4e4bef8244118cc2e26a9c4135f7d33734d`; `build_zipapp.py` `b60aaa458cd5053acde7f9dfb47203ea32844b025692abb512f95115b2e6bac6` | `python -m unittest tests.test_review_cli tests.test_zipapp` / 8+20 tests, 40+285 calls | 0 | OK; actual zipapp scan/review/render/compare and exact 15 members |
| Complete local regression | All / source SHAs above | `python -m unittest discover -s tests -v` / 145 tests, assertion calls not instrumented for this run | 0 | OK after corrected duplicate-case interpretation; local Windows interpreter only |
| Windows 2022/latest × Python 3.11/3.14 | Remote after authorized branch publication | CI matrix | not-run | local tests cannot establish remote matrix results |

The historical tagged release remains an 11-member archive; candidate build
verification belongs to this task's execution report and is not evidence that
the release asset changed. The table is updated only from observed command
exit codes and output.

Two fresh current-source candidate builds exited 0 and matched SHA-256
`fa280c2b204e9f313b031ed126eeeeee772ad0ec41d47497a427219597cb80b6`.
The archive has 15 exact members (12 runtime Python files, package directory,
generated root entrypoint, LICENSE). Separate `python -m unittest
tests.test_zipapp` ran 20 tests, exit 0. The built candidate's synthetic
demo, scan, decision, render and same-report compare each exited 0; the
comparison had zero changes and `decision_transfer=false`. Source bytes still
matched the scan report's `document_sha256`. This is local execution, not
proof for the remote Windows/Python matrix.
