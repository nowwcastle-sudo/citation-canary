# Local completion verification ledger

Scope: source-built local candidate only; no new public release, remote matrix,
official-source authentication, or legal outcome is asserted. Baseline source
commit before Task 3: `d2416bc653f0087c51c4ef5797871264b148146f`.
The Task 3 baseline rows below preserve the observed `b17425ba` source identity;
the fix-round row identifies newer local bytes separately. SHA-256 values are
local source-file bytes checked after the named code tests.
Assertion counts are observed `unittest.TestCase.assert*` method calls in a
separate instrumented local run (nested assertion calls count separately);
the ordinary full-suite run below was not instrumented. `not-run` is not a pass.

| Requirement | Owner / source SHA-256 | Executed command / assertions | Exit | Actual result |
| --- | --- | --- | ---: | --- |
| Shared strict IO, path and limits | Task 1 / `review_io.py` `16e6a740884021eb9ba76b4cfdf6c5c8034fa3afa16b4ad95d9e9fa9a04f723e` | `python -m unittest tests.test_review_io` / 14 tests, 75 assertion calls | 0 | OK; strict input and no-clobber path tests |
| CC-L01 human disposition | Task 2 / `review.py` `6cc5c2539284dad18ed8da76a0f878dfab3161f893b3080d9f95fba5eec146bf` | `python -m unittest tests.test_review_ledger tests.test_review_cli` / 13+8 tests, 85+40 assertion calls across shared suite | 0 | OK; item-number binding and separate decision events |
| CC-L02 retained events and binding | Task 2 / same `review.py` SHA above | same Task 2 suite / shared 13+8 tests, 85+40 calls | 0 | OK; chain, report binding and failed-write preservation |
| CC-L05 explicit measured intervals | Task 2 / same `review.py` SHA above | same Task 2 suite / shared 13+8 tests, 85+40 calls | 0 | OK; valid intervals measured, missing/reversed/overlap unknown |
| CC-L03 conservative comparison, historical Task 3 baseline | Task 3 / `comparison.py` `cfe483d8b2b18e6caa207392ae9ab01056334deaff3375d2bbc30920c12c458d` | `python -m unittest tests.test_review_compare` / 9 tests, 51 calls | 0 | OK under `b17425ba`; later review found same-locator repeated items were not independently matched |
| CC-L03 same-locator fix round 1 | Task 3 fix / `comparison.py` `72ea350495815b61cc72b125ee3e10a4e9116b16a2fa216f6c5089448fb5d049` | `python -m unittest tests.test_review_compare tests.test_review_cli -v` / 18 tests, exit 0; instrumented comparison 10 tests, 61 calls, exit 0 | 0 | Same-hash exact item 1/2 status/evidence diff retained; changed-hash duplicate pairing unresolved; full-suite and final artifact identity still pending final gate |
| CC-L04 static HTML | Task 3 / `review_html.py` `55a0e72f3b568946bdf3ee32f0aebb03bf4c64f0659a5fc120d2617f9e13c9c1` | `python -m unittest tests.test_review_html` / 6 tests, 28 calls | 0 | OK; escaping, safe links, priority, digest and timing |
| CLI and 15-member source candidate | Task 3 / `__main__.py` `56f790e2ced92cb65e585fb22f51b4e4bef8244118cc2e26a9c4135f7d33734d`; `build_zipapp.py` `b60aaa458cd5053acde7f9dfb47203ea32844b025692abb512f95115b2e6bac6` | `python -m unittest tests.test_review_cli tests.test_zipapp` / 8+20 tests, 40+285 calls | 0 | OK; actual zipapp scan/review/render/compare and exact 15 members |
| Complete local regression, historical Task 3 baseline | All / pre-fix `b17425ba` source SHAs above | `python -m unittest discover -s tests -v` / 145 tests, assertion calls not instrumented for this run | 0 | OK on pre-fix source; not rerun for same-locator fix yet |
| Complete regression after consolidated final fix | `comparison.py` `ec6b3fd47afcf74e43d8a15b826903e526c5879236ba6afa20758aa1d3c0a213`; `review_html.py` `2d56170b9d54409cfd8a4487c70cc3ab33e0bf692b268cbd1831fbd321ecfb4b`; CLI `8390802ca7d6f18d845c157e54d222b25987898b1880b893320b8b131710862d` | `PYTHONPATH=src python -m unittest discover -s tests -v` / 151 tests, assertion calls not instrumented | 0 | OK on local Windows; actual junction and post-close replacement tests passed; parent browser check pending |
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

Fix-round 1 separately built two fresh 15-member candidates, each exit 0,
with matching SHA-256
`30be42b0ed1fac1d48c915fae012040a89f3536dab2f284718e54d5c93506aa1`.
The focused package suite `python -m unittest tests.test_zipapp` ran 20 tests,
exit 0. This new candidate hash supersedes the pre-fix hash for current
runtime bytes; the parent final gate will establish final artifact identity
again after remaining edits. The fixed tagged 11-member release is unchanged.

Consolidated final fix candidate: two fresh builds exited 0, both exact 15
members with SHA-256
`aa0dbe04c50af6fe5ce697f1f6c955996b6b59c8c91a53f51b1584df636bebbe`.
The source-built candidate's help, demo, scan, review, render and compare
checks each exited 0, and the synthetic document's SHA-256 matched its scan
report. Focused tests: 43, exit 0; full regression: 151, exit 0. CSS output
assertion passed, but 375px actual-browser overflow is pending independent
parent recheck at the time of that fix report. No remote CI, real corpus or source-authenticity proof is claimed.

## Final local review checkpoint

Runtime source `bae78555d008113d656e80133d2081aeb0ad8a41` passed the
independent scoped re-review: all five final findings addressed, with no new
Critical/Important breakage. The full local suite was 151 tests, exit 0
(including 20 zipapp tests, not 171 tests). Parent readback confirmed both
15-member candidates have the final `aa0dbe04...` SHA-256 stated above.

The pending browser check is now complete for synthetic Chrome usage:
at 375px, document width is 375px rather than the earlier 528px. The full
digest is unchanged and wraps; keyboard focus and expanding the document
label work. axe 4.12.1 reported 22 passes, 0 violations and 0 incomplete.
Desktop rendering was also captured. A separate junction probe confirmed
target and marker identity, marker bytes and absence of unintended output
in eight checks, exit 0. This does not generalize to every filesystem race.

Dedicated static security diff scan
`c8f9669e-cc67-47ac-8edb-93d6d7aaa05e` reviewed all six changed source files
at this runtime source and was sealed with no reportable findings. It is
not a whole-repository or all-environment safety certificate. Report and
ledger authenticity remain unverified assertions, and operator-selected
network-backed paths are not an OS-wide offline isolation guarantee.
Remote Windows/Python CI, actual institution documents and new publication
are still unexecuted; the old release is unchanged.
