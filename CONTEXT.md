# Citation Canary domain context

## Purpose

Citation Canary supports human review of law and administrative-rule citations in existing HWPX 업무문서. It organizes date-aware official evidence and review priority. It does not render legal judgments and does not edit documents.

## Current implementation boundary

The experimental runtime matches narrow citation candidates against a local,
operator-supplied dated catalog. It does not retrieve or authenticate official
sources or establish case authenticity. The evidence definitions below describe
the intended human-reviewed basis; a successful catalog match alone does not
establish that basis. Explicit `--demo` setup creates fictional inputs.
See [ADR-0006](docs/adr/0006-experimental-oss-publication.md) for public scope.

## Core model

```text
local HWPX + 기준일
        ↓
인용 후보 + 비민감 위치정보
        ↓
공식 원천의 현행/연혁 증거
        ↓
CURRENT | HISTORY | REVIEW | UNKNOWN
        ↓
사람의 확인·기각·추가조사·보류
```

## Glossary

### 로컬 HWPX

A user-selected `.hwpx` file processed on the operator’s machine. It is not a repository asset, cloud upload, issue attachment, or reusable test fixture.

### 인용 후보

A detected reference to a statute, article/paragraph/item, administrative rule, notice, directive, precedent number, or version marker. Detection is not validation.

### 기준일

The date against which a citation is evaluated. It must be supplied or explicitly derived under an agreed rule and shown in the report. A file modification time is not automatically the 기준일.

### 공식 원천

An identified government or public-authority source used as evidence for current or historical text, effective dates, titles, article numbers, or issuance metadata. A search result snippet or unofficial summary is not sufficient by itself.

### CURRENT

Official evidence supports that the cited identity and referenced provision align with the version effective on the 기준일, within the narrow checks performed. It does not mean the document is legally valid, complete, or compliant.

### HISTORY

Official historical evidence supports that the citation existed in a prior version relevant to the review, while the current version differs. The report must show the relevant historical/effective dates. It is not automatically an error because historical citations can be intentional.

### REVIEW

Evidence shows a discrepancy, conflict, ambiguity, or date-sensitive condition that a human should inspect. `REVIEW` never means “illegal,” “invalid,” or “must change.”

### UNKNOWN

The available basis is insufficient to assign another status—for example, the 기준일 is missing, the citation is ambiguous, an official source is unavailable, or relevant history cannot be established. The reason must be explicit.

### 검토 항목

One report row containing a citation locator, 기준일, official-source provenance, status, reason, and retrieval time. It should contain no more source text than a human needs to locate the passage safely.

### 사람의 처분

The user’s separate follow-up choice: confirm, reject, investigate, or defer. It is not an evidence status and must not be converted into an automatic document edit.

## Trust boundaries

- The source document may contain confidential or personal data even when pattern scanning finds none.
- The extractor can identify candidates but cannot determine legal meaning.
- Official sources provide evidence but can be unavailable or change over time.
- The human user owns legal, policy, and document-change decisions.

## Rules that must remain visible

- No raw source-document body, secrets, or personal data in Git, logs, issues, or review artifacts.
- No status without a visible reason and official-source provenance; otherwise use `UNKNOWN`.
- No automatic edits or legal conclusions.
- Preserve the original file unchanged and keep derived material separate.
