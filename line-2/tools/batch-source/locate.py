#!/usr/bin/env python3
"""Check multiple JSON files and locate each violation in exact source bytes."""
import argparse
import json
from pathlib import Path
import sys
import types


MAX_DOCUMENTS = 256


def dependencies():
    """Load the trusted bounded reader and source-locator through that reader."""
    source = Path(__file__).absolute().parent.parent / 'source-locator' / 'locate.py'
    try:
        relative = source.relative_to(Path.cwd()).as_posix()
    except ValueError:
        raise ValueError('run inside a workspace containing the sibling tools')
    if any(not part or part.startswith('.') for part in relative.split('/')):
        raise ValueError('run inside a workspace containing the sibling tools')

    # The first fixed bootstrap is opened component by component without links.
    import os
    import stat
    bounded_path = source.parent.parent / 'bounded-contract' / 'check.py'
    try:
        bounded_relative = bounded_path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        raise ValueError('run inside a workspace containing the sibling tools')
    parts = bounded_relative.split('/')
    if any(not part or part.startswith('.') for part in parts):
        raise ValueError('run inside a workspace containing the sibling tools')
    directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    leaf = None
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=directory)
        if not stat.S_ISREG(os.fstat(leaf).st_mode):
            raise ValueError('trusted sibling must be a regular file')
        chunks, remaining = [], 1_000_001
        while remaining:
            chunk = os.read(leaf, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        code = b''.join(chunks)
        if len(code) > 1_000_000:
            raise ValueError('trusted sibling exceeds byte limit')
    finally:
        if leaf is not None:
            os.close(leaf)
        os.close(directory)

    bounded = types.ModuleType('batch_source_bounded_contract')
    bounded.__file__ = str(bounded_path)
    exec(compile(code, str(bounded_path), 'exec'), bounded.__dict__)
    module = types.ModuleType('batch_source_single_locator')
    module.__file__ = str(source)
    exec(compile(bounded.read_bytes(relative), str(source), 'exec'), module.__dict__)
    secure_reader, engine, rules = module.dependencies()
    return secure_reader, engine, module, rules


def locate_prepared(engine, explain, contract, document, prepared):
    """Reuse source-locator rule mapping with one prepared contract per batch."""
    errors = engine.validate(document.value, prepared)
    detailed = []
    for error in errors:
        rule_path = explain.rule_pointer(engine, contract.value, error)
        contract_source = contract.location(rule_path)
        if not contract_source['present']:
            raise ValueError('rule pointer has no contract source token')
        item = {**error, 'contract_path': rule_path,
                'constraint': explain.describe(explain.at(contract.value, rule_path)),
                'observed': explain.describe(explain.at(document.value, error['path']))}
        item['document_source'] = document.location(error['path'])
        item['contract_source'] = contract_source
        detailed.append(item)
    result = {'valid': not errors, 'error_count': len(errors), 'errors': detailed,
              'sources': {'contract': contract.identity(),
                          'document': document.identity()},
              'coordinates': {
                  'lines': 'one-based; LF begins each new line',
                  'columns': 'one-based Unicode code points, not display cells or UTF-16 units',
                  'offsets': 'zero-based; ranges include start and exclude end',
                  'encoding': 'UTF-8; source bytes and CRLF are preserved'}}
    return result


def check_all(reader, engine, source, explain, contract, names):
    prepared = engine.prepare(contract.value)
    rows = []
    failed = unreadable = 0
    for name in names:
        try:
            document = source.Source(reader.read_bytes(name), name)
            result = locate_prepared(engine, explain, contract, document, prepared)
            failed += not result['valid']
            rows.append({'file': name, **result})
        except (ValueError, OSError, RecursionError, KeyError, IndexError) as exc:
            unreadable += 1
            rows.append({'file': name, 'valid': False, 'error_count': 0,
                         'errors': [], 'error': str(exc)})
    report = {'valid': failed == 0 and unreadable == 0,
              'summary': {'checked': len(rows), 'passed': len(rows)-failed-unreadable,
                          'failed': failed, 'unreadable': unreadable},
              'contract': contract.identity(), 'files': rows}
    return report, 2 if unreadable else (1 if failed else 0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', help='trusted explicit contract, workspace-relative')
    parser.add_argument('documents', nargs='+', help='JSON paths in the order to check')
    args = parser.parse_args(argv)
    if len(args.documents) > MAX_DOCUMENTS:
        print(json.dumps({'error': f'at most {MAX_DOCUMENTS} documents per invocation'}))
        return 2
    try:
        reader, engine, source, explain = dependencies()
        contract = source.Source(reader.read_bytes(args.contract), args.contract)
        report, code = check_all(reader, engine, source, explain, contract, args.documents)
        print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))
        return code
    except (ValueError, OSError, RecursionError, KeyError, IndexError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
