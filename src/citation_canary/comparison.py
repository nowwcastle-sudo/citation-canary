"""Conservative, decision-free comparison of bounded scan reports."""

from __future__ import annotations

from collections import Counter, defaultdict

from .review_io import validate_report


def _identity(item: dict[str, object]) -> tuple[object, object, object]:
    reference = item['reference']
    return item['locator'], reference['title'], reference['provision']


def _reference(item: dict[str, object]) -> tuple[object, object]:
    reference = item['reference']
    return reference['title'], reference['provision']


def _change(kind: str, before_number: int | None, after_number: int | None,
            before: object, after: object) -> dict[str, object]:
    return {'type': kind, 'before_item_number': before_number,
            'after_item_number': after_number, 'before': before, 'after': after}


def compare_reports(before: dict[str, object], after: dict[str, object], *,
                    related_versions: bool = False) -> dict[str, object]:
    """Do not equate moved/duplicated candidates or carry human dispositions."""
    before, after = validate_report(before), validate_report(after)
    same_document = before['document_sha256'] == after['document_sha256']
    relationship = 'same_document' if same_document else ('related_versions' if related_versions else 'unavailable')
    result: dict[str, object] = {'schema': 'citation-comparison/1', 'comparable': False,
                                 'relationship': relationship, 'changes': [],
                                 'unresolved': [], 'decision_transfer': False}
    changes: list[dict[str, object]] = result['changes']
    metadata_changes = []
    if same_document or related_versions:
        for kind, field in (('catalog', 'catalog_sha256'), ('as_of', 'as_of')):
            if before[field] != after[field]:
                metadata_changes.append(_change(kind, None, None, before[field], after[field]))
    if before['collection_errors'] or after['collection_errors']:
        changes.extend(metadata_changes)
        result['unresolved'].append({'reason': 'collection_errors', 'before_item_numbers': [],
                                     'after_item_numbers': []})
        return result
    if not before['items'] or not after['items']:
        changes.extend(metadata_changes)
        result['unresolved'].append({'reason': 'empty_report_not_completion',
                                     'before_item_numbers': [], 'after_item_numbers': []})
        return result
    if not same_document and not related_versions:
        result['unresolved'].append({'reason': 'unrelated_documents', 'before_item_numbers': [],
                                     'after_item_numbers': []})
        return result
    result['comparable'] = True
    unresolved: list[dict[str, object]] = result['unresolved']
    old_items, new_items = before['items'], after['items']
    old_counts = Counter(_identity(item) for item in old_items)
    new_counts = Counter(_identity(item) for item in new_items)
    old_refs = Counter(_reference(item) for item in old_items)
    new_refs = Counter(_reference(item) for item in new_items)
    new_by_identity: dict[tuple[object, object, object], list[int]] = defaultdict(list)
    new_by_reference: dict[tuple[object, object], list[int]] = defaultdict(list)
    for number, item in enumerate(new_items, 1):
        new_by_identity[_identity(item)].append(number)
        new_by_reference[_reference(item)].append(number)
    matched_old: set[int] = set()
    matched_new: set[int] = set()
    if same_document:
        for number, (old, new) in enumerate(zip(old_items, new_items), 1):
            key = _identity(old)
            if key != _identity(new):
                continue
            matched_old.add(number)
            matched_new.add(number)
            if old['status'] != new['status'] or old['reason_code'] != new['reason_code']:
                changes.append(_change('status', number, number,
                                       {'status': old['status'], 'reason_code': old['reason_code']},
                                       {'status': new['status'], 'reason_code': new['reason_code']}))
            if old['evidence'] != new['evidence']:
                changes.append(_change('evidence', number, number, old['evidence'], new['evidence']))
    for number, item in enumerate(old_items, 1):
        if number in matched_old:
            continue
        key, ref = _identity(item), _reference(item)
        possible = (new_by_reference[ref] if same_document else
                    new_by_identity[key] if old_refs[ref] == new_refs[ref] == 1 else [])
        candidates = [index for index in possible if index not in matched_new]
        if candidates or old_counts[key] > 1 or new_counts[key] > 1 or \
                old_refs[ref] > 1 or new_refs[ref] > 1 or not same_document:
            unresolved.append({'reason': 'candidate_identity_unconfirmed' if candidates else 'moved_or_ambiguous',
                               'before_item_numbers': [number], 'after_item_numbers': candidates})
            matched_new.update(candidates)
        else:
            changes.append(_change('removed', number, None, item, None))
    for number, item in enumerate(new_items, 1):
        if number in matched_new:
            continue
        if not same_document or old_counts[_identity(item)] or \
                new_counts[_identity(item)] > 1 or old_refs[_reference(item)] or \
                new_refs[_reference(item)] > 1:
            unresolved.append({'reason': 'candidate_identity_unconfirmed',
                               'before_item_numbers': [], 'after_item_numbers': [number]})
        else:
            changes.append(_change('added', None, number, None, item))
    changes.extend(metadata_changes)
    return result
