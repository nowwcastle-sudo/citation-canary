from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from citation_canary.report import (
    CollectionError, Evidence, Reference, ScanItem, ScanReport, ScanRequestError,
    Status, VersionTransition,
)
from citation_canary import review_io
from citation_canary.review_io import canonical_digest, read_json, validate_report, write_new


def report() -> dict[str, object]:
    return ScanReport('1', 'synthetic.hwpx', 'a' * 64, '2024-12-31', 'b' * 64,
                      (), ()).to_dict()


class ReviewInputTests(unittest.TestCase):
    def test_empty_report_and_canonical_digest(self):
        value = report()
        self.assertEqual(validate_report(value), value)
        self.assertIsNot(validate_report(value), value)
        self.assertEqual(canonical_digest(value), canonical_digest(dict(reversed(list(value.items())))))

    def test_boolean_schema_and_nested_unknown_field_rejected(self):
        value = report()
        value['schema_version'] = True
        with self.assertRaises(ScanRequestError):
            validate_report(value)
        value = report()
        value['items'] = [{'locator': 'section0.xml:t[1]', 'reference': {'title': '합성법', 'provision': None, 'extra': 1},
                           'status': 'REVIEW', 'reason_code': 'SYNTHETIC', 'evidence': []}]
        with self.assertRaises(ScanRequestError):
            validate_report(value)

    def test_real_item_evidence_transition_and_collection_error(self):
        evidence = Evidence('synthetic-record', 'https://example.invalid', '2024-12-31T00:00:00Z',
                            '2024-12-31', '2020-01-01', None, '합성법', None,
                            VersionTransition('2024-01-01', '합성법', None))
        value = ScanReport('1', 'synthetic.hwpx', 'a' * 64, '2024-12-31', 'b' * 64,
                           (ScanItem('Contents/section0.xml:t[1]', Reference('합성법', None),
                                     Status.HISTORY, 'SYNTHETIC', (evidence,)),),
                           (CollectionError('HWPX_XML_INVALID', 'parse', True, None, 'Synthetic error.'),)).to_dict()
        self.assertEqual(validate_report(value), value)
        value['collection_errors'][0]['locator'] = 'Contents/section0.xml'
        self.assertEqual(validate_report(value), value)

    def test_items_exact_limit(self):
        value = report()
        item = {'locator': 'section0.xml:t[1]', 'reference': {'title': '합성법', 'provision': None},
                'status': 'UNKNOWN', 'reason_code': 'SYNTHETIC', 'evidence': []}
        value['items'] = [item] * 10000
        self.assertEqual(len(validate_report(value)['items']), 10000)
        value['items'].append(item)
        with self.assertRaises(ScanRequestError):
            validate_report(value)

    def test_read_limits_and_malformed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            base = json.dumps(report()).encode()
            path.write_bytes(base + b' ' * (8 * 1024 * 1024 - len(base)))
            self.assertEqual(read_json(path), report())
            path.write_bytes(base + b' ' * (8 * 1024 * 1024 + 1 - len(base)))
            with self.assertRaises(ScanRequestError):
                read_json(path)
            for raw in (b'\xff', b'{"a":1,"\\u0061":2}', b'{"x":NaN}', b'[' * 33 + b'0' + b']' * 33):
                path.write_bytes(raw)
                with self.subTest(raw=raw[:20]), self.assertRaises(ScanRequestError):
                    read_json(path)

    def test_non_json_scalar_and_surrogate_rejected_with_fixed_error(self):
        for invalid in ({'x': (1, 2)}, {'x': '\ud800'}):
            with self.subTest(invalid=repr(invalid)):
                with self.assertRaises(ScanRequestError) as caught:
                    canonical_digest(invalid)
                self.assertEqual(caught.exception.code, 'REVIEW_JSON_INVALID')

    def test_json_node_budget_exact_and_over(self):
        self.assertEqual(len(canonical_digest([None] * 199999)), 64)
        with self.assertRaises(ScanRequestError) as caught:
            canonical_digest([None] * 200000)
        self.assertEqual(caught.exception.code, 'REVIEW_JSON_INVALID')

    def test_invalid_collection_error_stage_rejected(self):
        value = report()
        value['collection_errors'] = [{'code': 'HWPX_XML_INVALID', 'stage': 'fictional',
                                       'fatal': True, 'locator': None, 'message': 'Synthetic error.'}]
        with self.assertRaises(ScanRequestError):
            validate_report(value)

    def test_successful_replacement_after_close_rejected_by_path_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            path.write_text(json.dumps(report()), encoding='utf-8')
            self.assertEqual(read_json(path), report())  # intact-path positive control
            original_identity = (path.stat().st_dev, path.stat().st_ino)
            original_safe_path = review_io._safe_path
            checks = 0

            def replace_before_revalidation(target, *, existing):
                nonlocal checks
                checks += 1
                if checks == 2:
                    replacement = path.with_suffix('.replacement')
                    replacement.write_bytes(path.read_bytes())
                    os.replace(replacement, path)  # handle has closed; real OS replacement must succeed
                return original_safe_path(target, existing=existing)

            with patch.object(review_io, '_safe_path', replace_before_revalidation):
                with self.assertRaises(ScanRequestError) as caught:
                    read_json(path)
            self.assertEqual(checks, 2)
            self.assertEqual(caught.exception.code, 'REVIEW_JSON_INVALID')
            self.assertNotEqual((path.stat().st_dev, path.stat().st_ino), original_identity)
            self.assertEqual(read_json(path), report())

    def test_write_new_no_clobber_alias_and_source_invariance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.json'
            source.write_bytes(b'original')
            before = hashlib.sha256(source.read_bytes()).digest()
            output = root / 'output.html'
            write_new(output, b'<p>safe</p>', (source,))
            self.assertEqual(output.read_bytes(), b'<p>safe</p>')
            with self.assertRaises(ScanRequestError):
                write_new(output, b'clobber', (source,))
            with self.assertRaises(ScanRequestError):
                write_new(source, b'clobber', (source,))
            alias = root / 'alias.json'
            os.link(source, alias)
            with self.assertRaises(ScanRequestError):
                write_new(alias, b'clobber', (source,))
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)

    def test_write_failure_preserves_created_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'failed.html'
            with patch('citation_canary.review_io.os.fsync', side_effect=OSError('synthetic failure')):
                with self.assertRaises(ScanRequestError) as caught:
                    write_new(output, b'partial-but-retained', ())
            self.assertEqual(caught.exception.code, 'REVIEW_OUTPUT_FAILED')
            self.assertEqual(output.read_bytes(), b'partial-but-retained')

    @unittest.skipUnless(os.name == 'nt', 'NTFS alternate stream test')
    def test_new_alternate_stream_on_protected_input_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.json'
            source.write_bytes(b'original')
            stream = Path(f'{source}:review.html')
            with self.assertRaises(ScanRequestError):
                write_new(stream, b'new stream', (source,))
            self.assertEqual(source.read_bytes(), b'original')
            with self.assertRaises(OSError):
                stream.open('rb')

    def test_samefile_io_failure_has_fixed_safe_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.json'
            output = root / 'existing.html'
            source.write_bytes(b'original')
            output.write_bytes(b'existing')
            with patch('citation_canary.review_io.os.path.samefile',
                       side_effect=OSError('synthetic raw detail')):
                with self.assertRaises(ScanRequestError) as caught:
                    write_new(output, b'new', (source,))
            self.assertEqual(caught.exception.code, 'REVIEW_OUTPUT_FAILED')
            self.assertEqual(str(caught.exception), 'Review output could not be written.')
            self.assertIsNone(caught.exception.__cause__)
            self.assertEqual(source.read_bytes(), b'original')
            self.assertEqual(output.read_bytes(), b'existing')

    @unittest.skipUnless(os.name == 'nt', 'Windows directory symlink test')
    def test_parent_directory_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'target'
            target.mkdir()
            junction = root / 'junction'
            os.symlink(target, junction, target_is_directory=True)
            with self.assertRaises(ScanRequestError):
                write_new(junction / 'out.html', b'x', ())

    @unittest.skipUnless(os.name == 'nt', 'Windows junction test')
    def test_actual_parent_junction_rejected_and_target_preserved(self):
        import subprocess
        import stat

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'target'
            target.mkdir()
            marker = target / 'marker.bin'
            marker.write_bytes(b'original target')
            junction = root / 'junction'
            created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(target)],
                                     capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, 'local junction creation failed')
            try:
                self.assertTrue(junction.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
                self.assertFalse(junction.is_symlink())
                with self.assertRaises(ScanRequestError) as caught:
                    write_new(junction / 'out.html', b'x', ())
                self.assertEqual(caught.exception.code, 'REVIEW_PATH_INVALID')
                self.assertFalse((target / 'out.html').exists())
                self.assertEqual(marker.read_bytes(), b'original target')
            finally:
                os.rmdir(junction)  # remove only the junction entry, never recurse into target
            self.assertTrue(target.is_dir())
            self.assertEqual(marker.read_bytes(), b'original target')


if __name__ == '__main__':
    unittest.main()
