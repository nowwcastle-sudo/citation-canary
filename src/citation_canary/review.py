"""Bound, report-bound human review events; never changes a scan report."""

from __future__ import annotations

import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from .report import ScanRequestError
from .review_io import (MAX_JSON_BYTES, _identity, _safe_path, canonical_digest,
                        read_json, validate_report)

MAX_EVENTS = 50_000
_ENVELOPE = {'schema', 'report_digest', 'document_sha256', 'catalog_sha256', 'as_of', 'events'}
_EVENT = {'sequence', 'action', 'item_number', 'disposition', 'stage', 'at',
          'previous_event_digest', 'digest'}
_DISPOSITIONS = {'confirm', 'reject', 'investigate', 'defer'}
_STAGES = ('triage', 'evidence', 'decision')
_UTC = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _invalid() -> ScanRequestError:
    return ScanRequestError('REVIEW_LEDGER_INVALID', 'Review ledger is invalid or does not match the report.')


def _conflict() -> ScanRequestError:
    return ScanRequestError('REVIEW_CONFLICT', 'Review ledger changed during update.')


def _ledger_path(path: Path) -> os.stat_result | None:
    info = _safe_path(path, existing=False)
    if info is not None and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
        raise ScanRequestError('REVIEW_PATH_INVALID', 'Review path is not a safe regular path.')
    return info


def _time(value: object) -> datetime:
    if type(value) is not str or _UTC.fullmatch(value) is None:
        raise _invalid()
    try:
        return datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        raise _invalid() from None


def new_ledger(report: dict[str, object]) -> dict[str, object]:
    report = validate_report(report)
    return {'schema': 'citation-review/1', 'report_digest': canonical_digest(report),
            'document_sha256': report['document_sha256'],
            'catalog_sha256': report['catalog_sha256'], 'as_of': report['as_of'],
            'events': []}


def validate_ledger(ledger: object, report: dict[str, object]) -> dict[str, object]:
    expected = new_ledger(report)
    if type(ledger) is not dict or set(ledger) != _ENVELOPE:
        raise _invalid()
    if any(ledger[key] != expected[key] for key in _ENVELOPE - {'events'}):
        raise _invalid()
    events = ledger['events']
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise _invalid()
    count = len(report['items'])
    previous = None
    for sequence, event in enumerate(events, 1):
        if type(event) is not dict or set(event) != _EVENT:
            raise _invalid()
        if type(event['sequence']) is not int or event['sequence'] != sequence:
            raise _invalid()
        if event['previous_event_digest'] != previous:
            raise _invalid()
        action, number, disposition, stage = (event[key] for key in
                                               ('action', 'item_number', 'disposition', 'stage'))
        if action == 'decide':
            if type(number) is not int or not 1 <= number <= count or \
                    type(disposition) is not str or disposition not in _DISPOSITIONS or stage is not None:
                raise _invalid()
        elif action in ('start', 'finish'):
            if number is not None or disposition is not None or type(stage) is not str or stage not in _STAGES:
                raise _invalid()
        else:
            raise _invalid()
        _time(event['at'])
        digest = event['digest']
        try:
            calculated = canonical_digest({key: value for key, value in event.items() if key != 'digest'})
        except ScanRequestError:
            raise _invalid() from None
        if type(digest) is not str or _SHA.fullmatch(digest) is None or digest != calculated:
            raise _invalid()
        previous = digest
    return json.loads(json.dumps(ledger, ensure_ascii=False, allow_nan=False))


def append_event(ledger: dict[str, object], report: dict[str, object], *, action: str,
                 item_number: int | None, disposition: str | None, stage: str | None,
                 at: str) -> dict[str, object]:
    result = validate_ledger(ledger, report)
    events = result['events']
    if len(events) >= MAX_EVENTS:
        raise _invalid()
    event = {'sequence': len(events) + 1, 'action': action, 'item_number': item_number,
             'disposition': disposition, 'stage': stage, 'at': at,
             'previous_event_digest': events[-1]['digest'] if events else None}
    event['digest'] = canonical_digest(event)
    events.append(event)
    return validate_ledger(result, report)


def review_summary(ledger: dict[str, object], report: dict[str, object]) -> dict[str, object]:
    ledger = validate_ledger(ledger, report)
    decisions: dict[str, str] = {}
    starts: dict[str, datetime | None] = {stage: None for stage in _STAGES}
    intervals: dict[str, list[tuple[datetime, datetime]]] = {stage: [] for stage in _STAGES}
    bad = {stage: False for stage in _STAGES}
    for event in ledger['events']:
        if event['action'] == 'decide':
            decisions[str(event['item_number'])] = event['disposition']
            continue
        stage = event['stage']
        instant = _time(event['at'])
        if event['action'] == 'start':
            if starts[stage] is not None:
                bad[stage] = True
            starts[stage] = instant
        elif starts[stage] is None:
            bad[stage] = True
        else:
            if instant < starts[stage]:
                bad[stage] = True
            else:
                intervals[stage].append((starts[stage], instant))
            starts[stage] = None
    all_intervals = sorted((start, end, stage) for stage, pairs in intervals.items()
                           for start, end in pairs)
    longest = None
    for interval in all_intervals:
        if longest is not None and interval[0] < longest[1]:
            bad[longest[2]] = bad[interval[2]] = True
        if longest is None or interval[1] > longest[1]:
            longest = interval
    timing = {}
    for stage in _STAGES:
        if starts[stage] is not None or not intervals[stage] or bad[stage]:
            timing[stage] = {'seconds': None, 'status': 'unknown'}
        else:
            timing[stage] = {'seconds': sum((end - start).total_seconds()
                                              for start, end in intervals[stage]),
                             'status': 'measured'}
    return {'latest_decisions': decisions,
            'unreviewed_count': len(report['items']) - len(decisions),
            'disposition_counts': {name: sum(value == name for value in decisions.values())
                                   for name in sorted(_DISPOSITIONS)},
            'timing': timing}


def update_ledger(path: Path, report_path: Path, *, action: str,
                  item_number: int | None, disposition: str | None, stage: str | None) -> None:
    """Serialize one event under an exclusive sibling lock; retain failed temp files."""
    path, report_path = Path(path), Path(report_path)
    _safe_path(report_path, existing=True)
    original = _ledger_path(path)
    if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(report_path)):
        raise ScanRequestError('REVIEW_PATH_INVALID', 'Review path is not a safe regular path.')
    if original is not None:
        try:
            same = os.path.samefile(path, report_path)
        except OSError:
            raise ScanRequestError('REVIEW_PATH_INVALID', 'Review path is not a safe regular path.') from None
        if same:
            raise ScanRequestError('REVIEW_PATH_INVALID', 'Review path is not a safe regular path.')
    lock_path = path.with_name(path.name + '.lock')
    _ledger_path(lock_path)
    try:
        lock = lock_path.open('xb')
    except FileExistsError:
        raise ScanRequestError('REVIEW_BUSY', 'Review ledger is locked by another writer.') from None
    except OSError:
        raise ScanRequestError('REVIEW_WRITE_FAILED', 'Review ledger could not be written.') from None
    lock_identity = _identity(os.fstat(lock.fileno()))
    try:
        report = validate_report(read_json(report_path))
        before = _ledger_path(path)
        if before is None:
            ledger = new_ledger(report)
            original_digest = None
        else:
            ledger = validate_ledger(read_json(path), report)
            original_digest = canonical_digest(ledger)
        at = datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
        updated = append_event(ledger, report, action=action, item_number=item_number,
                               disposition=disposition, stage=stage, at=at)
        payload = (json.dumps(updated, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
        if len(payload) > MAX_JSON_BYTES:
            raise _invalid()
        with NamedTemporaryFile(mode='wb', dir=path.parent, prefix='.' + path.name + '.',
                                suffix='.tmp', delete=False) as temporary:
            temp_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        temp_info = _safe_path(temp_path, existing=True)
        try:
            if read_json(temp_path) != updated:
                raise _invalid()
        except ScanRequestError as error:
            if error.code == 'REVIEW_JSON_INVALID':
                raise _invalid() from None
            raise
        current = _ledger_path(path)
        if before is None:
            if current is not None:
                raise _conflict()
            try:
                os.link(temp_path, path)
            except FileExistsError:
                raise _conflict() from None
            try:
                temp_path.unlink()
            except OSError:
                try:
                    linked = path.lstat()
                    retained = temp_path.lstat()
                    if temp_info is not None and linked.st_nlink >= 2 and \
                            _identity(linked) == _identity(retained) == _identity(temp_info):
                        path.unlink()
                except OSError:
                    pass
                raise ScanRequestError('REVIEW_WRITE_FAILED', 'Review ledger could not be written.') from None
        else:
            if current is None or _identity(current) != _identity(before):
                raise _conflict()
            try:
                current_digest = canonical_digest(read_json(path))
            except ScanRequestError:
                raise _conflict() from None
            if current_digest != original_digest:
                raise _conflict()
            os.replace(temp_path, path)
    except ScanRequestError:
        raise
    except OSError:
        raise ScanRequestError('REVIEW_WRITE_FAILED', 'Review ledger could not be written.') from None
    finally:
        lock.close()
        try:
            if _identity(os.stat(lock_path, follow_symlinks=False)) == lock_identity:
                lock_path.unlink()
        except OSError:
            pass
