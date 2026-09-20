# Contributing

Contributions to this experimental OSS project are welcome through GitHub
Issues and pull requests against main. Start with a synthetic reproduction or
a concrete proposal. Preserve attribution and keep changes focused.

## Before a change

- Read `CONTEXT.md` and the relevant ADR first.
- Use synthetic HWPX and schema-v1 catalog fixtures only.
- Never commit source documents, catalog secrets, account details, or tokens.
- Preserve `CURRENT`, `HISTORY`, `REVIEW`, `UNKNOWN`, and fixed exit contracts.
- The project already uses Apache License 2.0; preserve the root `LICENSE`
  and its inclusion in the current-source zipapp.

## Verification

From the repository root with Python 3.11 or newer:

```powershell
$env:PYTHONPATH = (Resolve-Path 'src').Path
python -m unittest discover -s tests -p "test_*.py"
python -m unittest tests.test_zipapp
```

Record native exits and keep failing artifacts. Do not weaken a test or turn a
collection error into a successful scan.

## Review

Describe the input/output contract, privacy impact, and rollback path. Do not
fetch official sources, edit HWPX files, submit documents, change repository
visibility, publish an artifact, or change the selected license without a
separate owner decision. For local artifact preparation, follow the
[current-source candidate guide](docs/release/public-candidate.md).
