# Catalog schema version 1

The catalog is a local UTF-8 JSON file prepared and reviewed by the operator.
It lists the citation titles/provisions and dated source metadata that the
scanner is allowed to match. Citation Canary checks this structure and records
its SHA-256. It never fetches the URL or verifies that the source is official,
complete, fresh, or applicable to an institution.

For a first synthetic run, use the packaged `--demo` command in the
[README](../README.md). That command creates this catalog and its matching
synthetic HWPX together. No repository checkout or test helper is required.

## Exact fields

Every listed field is required, including fields whose value may be `null`.
Additional fields are rejected at every level. JSON keys must not be repeated,
including inside nested objects. Comments, trailing commas, `NaN` and infinity
are not JSON accepted by this scanner.

| Object | Field | Accepted value |
|---|---|---|
| Root | `schema_version` | Exactly the string `"1"`; the number `1` is different |
| Root | `records` | Nonempty array of record objects |
| Record | `record_id` | Nonempty string, unique across records |
| Record | `official_source` | Object containing exactly `url` and `retrieved_at` |
| Record | `versions` | Nonempty array of version objects |
| Official source | `url` | Absolute HTTPS URL with a hostname, no username/password, whitespace, control characters or backslash |
| Official source | `retrieved_at` | Valid RFC3339 timestamp including seconds and `Z` or an offset, for example `2026-09-04T00:00:00+09:00` |
| Version | `effective_from` | Strict calendar date `YYYY-MM-DD` |
| Version | `effective_to` | Strict calendar date `YYYY-MM-DD`, or JSON `null` |
| Version | `title` | Nonempty string; retain the exact source title |
| Version | `provisions` | Nonempty array of provision objects |
| Provision | `canonical_id` | Nonempty stable string identifying the same provision across versions |
| Provision | `label` | Nonempty provision label, for example `제7조` |

Strings consisting only of whitespace are invalid. Other strings are not
trimmed or normalized by the loader: accidental surrounding spaces can prevent
an exact match. Both `canonical_id` and `label` must be unique within each
version. IDs can repeat across versions to express continuity, but do not
reuse an ID for unrelated provisions.

## Date and version rules

- An interval includes `effective_from` and excludes `effective_to`:
  `[2020-01-01, 2025-02-01)` applies through 2025-01-31.
- If there is an end date, the start must be earlier than the end.
- Versions must be ordered and must not overlap. Gaps are allowed but provide
  no evidence for the uncovered dates.
- The final version must be open-ended: `effective_to` must be `null`.
  An open-ended version cannot precede another version.
- The review date comes from explicit `--as-of`; document modification time,
  the current date and `retrieved_at` are not substitutes.
- `retrieved_at` is source-retrieval metadata, not an effective date. The
  scanner does not enforce a freshness deadline; the operator must review it.

## Complete synthetic example

All names, effective intervals, retrieval times and URLs below are fictional
teaching data. `example.invalid` is not an official legal source and must not
be used as evidence for a real document. The packaged demo uses this exact
JSON value; indentation does not affect its meaning, but file bytes affect its
SHA-256.

```json
{
  "schema_version": "1",
  "records": [
    {
      "record_id": "synthetic-current-001",
      "official_source": {
        "url": "https://example.invalid/official-source/synthetic-current-001",
        "retrieved_at": "2026-09-04T00:00:00+09:00"
      },
      "versions": [
        {
          "effective_from": "2020-01-01",
          "effective_to": null,
          "title": "가상현행규정",
          "provisions": [
            {"canonical_id": "article-1", "label": "제1조"}
          ]
        }
      ]
    },
    {
      "record_id": "synthetic-history-001",
      "official_source": {
        "url": "https://example.invalid/official-source/synthetic-history-001",
        "retrieved_at": "2026-09-04T00:00:00+09:00"
      },
      "versions": [
        {
          "effective_from": "2020-01-01",
          "effective_to": "2025-02-01",
          "title": "가상행정규칙",
          "provisions": [
            {"canonical_id": "article-7", "label": "제7조"}
          ]
        },
        {
          "effective_from": "2025-02-01",
          "effective_to": null,
          "title": "가상업무규정",
          "provisions": [
            {"canonical_id": "article-7", "label": "제9조"}
          ]
        }
      ]
    }
  ]
}
```

`article-7` stays the same when the synthetic title and provision number change.
That explicit continuity lets the report show a historical transition. The
scanner cannot determine continuity from legal meaning on its own.

## Create, save and review a catalog

1. For learning, generate the matching pair with `--demo`. For real review,
   create a separate working catalog rather than converting a synthetic report
   into purported official evidence.
2. Confirm the review date and official current/history source outside the
   scanner. Verify title, provision identity, effective intervals and access
   permission. Preserve source provenance under the institution's procedure.
3. Enter the exact fields above in a plain-text editor. Keep credentials,
   institution data and source HWPX paragraphs out of the catalog. Do not add a
   `notes` field: unknown fields are rejected.
4. Save as `catalog.json`, UTF-8 **without BOM**, not UTF-16 or an editor's
   legacy encoding. On Windows, verify that the actual filename is not
   `catalog.json.txt`. Avoid Windows PowerShell 5.1's default `Out-File` encoding
   when creating this file.
5. Read it back in the editor and review every required field, interval and
   timestamp. For a real scan, a human must approve the source provenance and
   freshness before interpreting a substantive status.
6. Run the documented scan with a separate report output. A successful schema
   check proves structure, not official authority or legal applicability.
   Compare the report's `catalog_sha256` to the catalog bytes used for review.

## What extraction can and cannot find

Extraction starts with titles already present in this catalog. It looks in each
XML text node and binds the first following `제N조` or `제N조의N` within 32
characters and before the next matched title. It does not perform broad legal
NLP, fuzzy title matching, OCR, or exhaustive statute discovery, and it does
not join citations split across separate text nodes.

An unmatched citation marker can produce `UNKNOWN`. Some unsupported text can
produce no candidate at all. **Zero candidates is not a statement that the
document has no citations or legal issues.** `REVIEW` and `UNKNOWN` are useful
review routing outcomes and do not cause a successful scan to exit nonzero.

## Safe catalog errors

The Python interface raises `ScanRequestError` with the code below. The CLI
exits 2 and prints only the safe message, with no JSON report or raw input.

| Code | CLI message | Next check |
|---|---|---|
| `CATALOG_NOT_FOUND` | `Catalog file was not found.` | File exists and the supplied path is correct |
| `CATALOG_NOT_READABLE` | `Catalog file is not readable.` | A regular readable file was selected |
| `CATALOG_JSON_INVALID` | `Catalog is not valid UTF-8 JSON.` | Encoding/BOM, duplicate keys, JSON syntax and numeric limits |
| `CATALOG_SCHEMA_UNSUPPORTED` | `Catalog schema version is unsupported.` | `schema_version` is exactly `"1"` |
| `CATALOG_SCHEMA_INVALID` | `Catalog does not conform to schema version 1.` | Exact fields, nonempty values, dates, URL, timestamp, intervals and IDs |

Do not upload the catalog, source HWPX or report body to a support issue. Supply
only a synthetic reproduction, safe error, command form and exit code under
the support procedure in the README. Keep real catalog hashes private.
