"""Offline, read-only HTML from a validated report and optional bound ledger."""

from __future__ import annotations

from html import escape
from unicodedata import category
from urllib.parse import urlsplit

from .review import new_ledger, review_summary
from .review_io import canonical_digest, validate_report

_ORDER = ('REVIEW', 'UNKNOWN', 'HISTORY', 'CURRENT')


def _safe_source(value: str) -> bool:
    # urlsplit strips some controls before parsing; reject the original first.
    if any(char.isspace() or category(char) == 'Cc' for char in value) or \
            any(char in value for char in ('"', "'", '<', '>', '\\')):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == 'https' and bool(parsed.hostname) and \
            parsed.username is None and parsed.password is None and '@' not in parsed.netloc and \
            parsed.port != 0
    except ValueError:
        return False


def _evidence(entry: dict[str, object]) -> str:
    source = entry['official_source']
    label = escape(entry['record_id'])
    if _safe_source(source):
        label = f'<a href="{escape(source, quote=True)}" rel="noopener noreferrer">{label}</a>'
    else:
        label += ' (source link unavailable)'
    dates = f"effective {escape(entry['matched_effective_from'])} to {escape(entry['matched_effective_to'] or 'open')}"
    transition = entry['version_transition']
    transition_label = (f' · transition {escape(transition["effective_from"])} '
                        f'{escape(transition["title"])} {escape(transition["provision"] or "")}'
                        if transition is not None else '')
    return (f'<li>{label} · {dates} · retrieved {escape(entry["retrieved_at"])}'
            f' · matched {escape(entry["matched_title"])} '
            f'{escape(entry["matched_provision"] or "")}{transition_label}</li>')


def render_review(report: dict[str, object], ledger: dict[str, object] | None = None) -> str:
    """All source strings are text; a source URL becomes a link only after validation."""
    report = validate_report(report)
    summary = review_summary(new_ledger(report) if ledger is None else ledger, report)
    counts = {status: sum(item['status'] == status for item in report['items'])
              for status in _ORDER}
    errors = report['collection_errors']
    banner = ('<section class="alert"><h2>Collection errors — incomplete evidence</h2><ul>' +
              ''.join(f'<li>{escape(error["code"])} ({escape(error["stage"])}) — '
                      f'{escape(error["message"])}</li>' for error in errors) + '</ul></section>') if errors else ''
    empty = '<p class="alert">No candidates is not completion. Check extraction scope and source evidence.</p>' if not report['items'] else ''
    status_counts = ' · '.join(f'{status}: {counts[status]}' for status in _ORDER)
    disposition = ' · '.join(f'{name}: {count}' for name, count in summary['disposition_counts'].items())
    timing = ' · '.join(f'{stage}: {detail["seconds"]} seconds' if detail['status'] == 'measured'
                        else f'{stage}: unknown' for stage, detail in summary['timing'].items())
    sections = []
    for status in _ORDER:
        rows = []
        for number, item in enumerate(report['items'], 1):
            if item['status'] != status:
                continue
            reference = item['reference']
            latest = summary['latest_decisions'].get(str(number), 'unreviewed')
            evidence = ''.join(_evidence(entry) for entry in item['evidence'])
            rows.append(f'<article><h3>item {number} · {escape(reference["title"] or "unidentified")} '
                        f'{escape(reference["provision"] or "")}</h3>'
                        f'<p>Reason: {escape(item["reason_code"])} · disposition: {escape(latest)}</p>'
                        f'<ul>{evidence}</ul></article>')
        sections.append(f'<section><h2>{status} ({counts[status]})</h2>{"".join(rows)}</section>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Citation Canary local review</title><style>'
            'body{font:16px/1.55 system-ui,sans-serif;max-width:72rem;margin:2rem auto;padding:0 1rem;color:#182230}'
            'section{margin:1.5rem 0}article{border-top:1px solid #aab4c0;padding:.7rem 0}'
            '.alert{border:2px solid #8c3b20;padding:1rem;background:#fff2e9}'
            'a{color:#064f91}a:focus-visible{outline:3px solid #a85800}'
            '</style></head><body><main><h1>Citation Canary local review</h1>'
            '<p class="alert">Sensitive: citation identifiers and evidence are not anonymized. '
            'Keep this local file private. No legal conclusion or source authentication is implied.</p>'
            f'<p>Report digest (SHA-256): <code>{canonical_digest(report)}</code> · as of {escape(report["as_of"])}</p>'
            f'<details><summary>Document label (show only when needed)</summary><p>{escape(report["document_name"])}</p></details>'
            f'{banner}<p>Statuses — {status_counts}</p>'
            f'<p>unreviewed: {summary["unreviewed_count"]} · dispositions — {disposition}</p>'
            f'<p>Recorded timing — {timing}</p>{empty}{"".join(sections)}'
            '</main></body></html>')
