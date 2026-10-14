"""Local tests for the multi-document source locator."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path.cwd()
HERE = ROOT / 'line-2/tools/batch-source'
SCRATCH = ROOT / 'test/scratch/batch-source'
SCRIPT = HERE / 'locate.py'


def write(name, data):
    path = SCRATCH / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return 'test/scratch/batch-source/' + name


def run(contract, *documents):
    return subprocess.run([sys.executable, '-B', str(SCRIPT), contract, *documents],
                          cwd=ROOT, text=True, capture_output=True, check=False)


class BatchSource(unittest.TestCase):
    def test_real_records_keep_order_and_hashes(self):
        names = ['dist/line-2/27.json', 'dist/line-2/28.json']
        result = run('line-2/tools/ordered-deliverables/record.strict.contract.json', *names)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['valid'])
        self.assertEqual(report['summary'],
                         {'checked': 2, 'passed': 2, 'failed': 0, 'unreadable': 0})
        self.assertEqual([row['file'] for row in report['files']], names)
        for name, row in zip(names, report['files']):
            self.assertEqual(row['sources']['document']['sha256'],
                             hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
            self.assertEqual(row['sources']['contract']['sha256'], report['contract']['sha256'])

    def test_errors_point_into_exact_contract_and_document_bytes(self):
        contract = b'{\n "type":"object",\n "required":["name"],\n "additionalProperties":false,\n "properties":{"name":{"type":"string"}}\n}\n'
        document = b'{\n  "extra": false,\n  "name": 7\n}\n'
        c = write('shape.json', contract)
        d = write('bad.json', document)
        result = run(c, d)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        row = json.loads(result.stdout)['files'][0]
        self.assertEqual([item['path'] for item in row['errors']], ['/extra', '/name'])
        for error, expected_document, expected_rule in zip(
                row['errors'], (b'false', b'7'), (b'false', b'"string"')):
            span = error['document_source']['value']
            start, end = span['start']['byte_offset'], span['end']['byte_offset']
            self.assertEqual(document[start:end], expected_document)
            rule = error['contract_source']['value']
            start, end = rule['start']['byte_offset'], rule['end']['byte_offset']
            self.assertEqual(contract[start:end], expected_rule)
        self.assertEqual(row['errors'][0]['contract_path'], '/additionalProperties')
        self.assertEqual(row['errors'][1]['contract_path'], '/properties/name/type')

    def test_malformed_document_is_counted_and_later_file_runs(self):
        c = write('any-string.json', b'{"type":"string"}')
        malformed = write('broken.json', b'{')
        good = write('ok.json', b'"ok"')
        result = run(c, malformed, good)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['summary'],
                         {'checked': 2, 'passed': 1, 'failed': 0, 'unreadable': 1})
        self.assertFalse(report['files'][0]['valid'])
        self.assertTrue(report['files'][1]['valid'])

    def test_invalid_contract_fails_before_documents(self):
        c = write('bad-contract.json', b'{"type":"object","unknown":true}')
        result = run(c, 'dist/line-2/27.json')
        self.assertEqual(result.returncode, 2)
        self.assertIn('unsupported rules', json.loads(result.stdout)['error'])

    def test_refuses_symlink_document(self):
        c = write('safe.json', b'{"type":"null"}')
        target = SCRATCH / 'ok.json'
        target.write_bytes(b'null')
        link = SCRATCH / 'link.json'
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(target.name)
        result = run(c, 'test/scratch/batch-source/link.json')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['summary']['unreadable'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
