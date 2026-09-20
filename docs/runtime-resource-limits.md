# Local scan resource limits

The scanner rejects documents that exceed a fixed resource budget. It never
truncates a scan into an apparently complete report: a rejection produces a fatal
collection error and an empty `items` array. Schema version and the four evidence
statuses are unchanged. The final source-hash check also runs for rejected scans.

These are conservative local-review limits, not a guarantee that every admitted
document has a particular runtime or peak memory use. Large valid documents may
be rejected; raising a limit requires a measured representative fixture and review.

## XML collection

Existing archive limits remain: 100 MiB compressed input, 10,000 archive entries,
20 MiB per section, 200 MiB total uncompressed archive members, and 32 digits in a
section-number suffix. In addition, section XML has the following limits:

| Resource | Limit | Scope |
| --- | ---: | --- |
| XML elements | 200,000 | All sections combined, counted on start events |
| Text elements (`t`) | 100,000 | All sections combined, including empty elements |
| XML nesting depth | 128 | Each section, with root at depth 1 |
| Retained text characters | 20 × 1,024 × 1,024 | All section text nodes combined |

The parser checks structural counts before retaining text-node objects and checks
the text budget before appending each nonempty text node. Empty text nodes are
not retained, but still count toward the limit and their original per-section
ordinal. For example, a nonempty node after an empty first `t` remains `t[2]`.
The character budget counts Python Unicode string length, not UTF-8 bytes or
measured heap size. Per-section byte limits still bound parser input allocation.

Exceeding any archive or XML budget returns `HWPX_LIMIT_EXCEEDED` at the `parse`
stage, with the fixed message `HWPX archive exceeds a safety limit.`

## Reference extraction

| Resource | Per text node | Whole document |
| --- | ---: | ---: |
| Title/marker matches examined | 100,000 | 100,000 |
| Reference candidates | 10,000 | 10,000 |

Examined matches include title occurrences discarded because a longer title
already covers them, plus marker matches covered by a selected title. Extraction
stops searching a marker after its first uncovered occurrence, since the output
contains only the earliest ambiguous reference per text node. Known titles retain
longest-title precedence, and results retain document order.

Overlap checks use one byte of coverage per character in the current text node.
A match checks only its own character range; it does not scan every previously
selected occurrence. Accepted title ranges are marked once. Candidate limits
apply before creating an additional candidate or resolving catalog evidence.

Exceeding an extraction budget returns `REFERENCE_LIMIT_EXCEEDED` at the
`extract` stage, with the fixed message
`Reference extraction exceeds a safety limit.` No source body or exception text
is included. These budgets do not bound loading or resolving an independently
supplied catalog; use a small, locally reviewed catalog.

## Verification

`tests/test_resource_limits.py` uses small synthetic inputs and reduced budgets
to exercise both the exact boundary and rejection above it, including cumulative
limits across sections and text nodes. It also checks empty-node ordinals,
longest-title precedence, reference ordering, source preservation, the final
source-hash guard, and bounded overlap lookup work without timing assertions.

The implementation uses the standard library's
[bytearray search and mutable sequence operations](https://docs.python.org/3/library/stdtypes.html#bytearray.find)
and [ElementTree start/end parse events](https://docs.python.org/3/library/xml.etree.elementtree.html#xml.etree.ElementTree.iterparse).
