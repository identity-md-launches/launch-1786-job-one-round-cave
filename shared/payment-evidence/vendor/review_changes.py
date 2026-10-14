#!/usr/bin/env python3
"""Explain changes against a previously pinned EIP-712 review, offline."""
import argparse
import json
import sys

from request_set_check import compare_set
from review_pin import verify_pin
from typed_digest import INTEGER, TypedDataError, load_workspace_json

MAX_REPORT_BYTES = 1_048_576


def display(node):
    """Human-readable local inputs, without repeating containing hash preimages.

    Integer output is decimal text, so consumers cannot round large integers.
    Strings remain exact Unicode; the CLI escapes them in ASCII JSON.
    """
    kind = node['kind']
    result = {'type': node['type'], 'kind': kind}
    if kind == 'struct':
        result['typeEncoding'] = node['typeEncoding']
    elif kind == 'array':
        result['length'] = (len(node['preimage']) - 2) // 64
    elif kind == 'dynamic':
        raw = bytes.fromhex(node['preimage'][2:])
        result['value'] = raw.decode('utf-8') if node['type'] == 'string' else node['preimage']
        result['inputBytes'] = len(raw)
    else:
        value = int(node['word'][2:], 16)
        integer = INTEGER.fullmatch(node['type'])
        if integer:
            if integer.group(1) == 'int' and value >= 1 << 255:
                value -= 1 << 256
            result['value'] = str(value)
        elif node['type'] == 'address':
            result['value'] = '0x' + node['word'][-40:]
        elif node['type'] == 'bool':
            result['value'] = bool(value)
        else:
            result['value'] = node['word'][:2 + 2 * int(node['type'][5:])]
    return result


def explain_item(item):
    """Every ancestor difference is direct, added/removed, or propagated.

    Retain raw encoding bytes as a fallback if a difference cannot be explained
    locally or by a descendant. Never infer equality from the reduced display.
    """
    changes, propagated = [], []
    differences = item['differences']
    paths = {d['path'] for d in differences}
    for difference in differences:
        path = difference['path']
        left, right = difference['intended'], difference['client']
        if path == '/primaryType':
            changes.append({'path': path, 'reason': 'primary_type', 'before': left, 'after': right})
            continue
        if left is None or right is None:
            changes.append({'path': path, 'reason': 'node_added' if left is None else 'node_removed',
                            'before': display(left) if left else None,
                            'after': display(right) if right else None})
            continue
        before, after = display(left), display(right)
        found = False
        for key, reason in (('type', 'declared_type'), ('kind', 'encoding_kind'),
                            ('typeEncoding', 'struct_schema'), ('length', 'array_length'),
                            ('value', 'value')):
            if before.get(key) != after.get(key):
                changes.append({'path': path, 'reason': reason,
                                'before': before.get(key), 'after': after.get(key)})
                found = True
        if not found:
            if any(p.startswith(path + '/') for p in paths):
                propagated.append(path)
            else:
                changes.append({'path': path, 'reason': 'encoding_bytes',
                                'before': left, 'after': right})
    if not item['accountMatches']:
        changes.insert(0, {'path': '/params/0', 'reason': 'public_account',
                          'before': item['intendedAccount'], 'after': item['clientAccount']})
    return {
        'reviewId': item['reviewId'], 'matches': item['accepted'],
        'digestMatches': item['digestMatches'], 'encodingMatches': item['encodingMatches'],
        'accountMatches': item['accountMatches'],
        'beforeDigest': item['intended']['digest'], 'afterDigest': item['client']['digest'],
        'encodingDifferenceCount': item['differenceCount'],
        'changes': changes, 'propagatedEncodingPaths': propagated,
    }


def render(report):
    text = json.dumps(report, ensure_ascii=True, indent=2) + '\n'
    if len(text.encode('ascii')) > MAX_REPORT_BYTES:
        raise TypedDataError('change review exceeds 1048576-byte report limit')
    return text


def finish(report, intended, candidate):
    # This helper also refuses a failed pin for direct Python callers.
    report = dict(report, accepted=False)
    if not report['pinMatches']:
        return report
    compared = compare_set(intended, candidate)
    report.update(
        accepted=compared['accepted'],
        membershipMatches=compared['membershipMatches'], orderMatches=compared['orderMatches'],
        beforeOrder=compared['intendedOrder'], afterOrder=compared['clientOrder'],
        missing=compared['missing'], added=compared['added'],
        requests=[explain_item(item) for item in compared['items']],
        interpretation='accepted means unchanged against the pinned review, not approval of a change',
        pathScope='domain/message paths are inside parsed typed data; /params/0 is the public account',
        limits='labels and capture order are caller assertions; no ownership, consent or contract support proven',
    )
    render(report)
    return report


def review(intended, candidate, expected):
    return finish(verify_pin(intended, expected), intended, candidate)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('intended', help='previously reviewed collection beneath cwd')
    parser.add_argument('candidate', help='candidate collection beneath cwd')
    parser.add_argument('--expect', required=True, help='independently retained prior review pin')
    args = parser.parse_args(argv)
    try:
        intended = load_workspace_json(args.intended)
        report = verify_pin(intended, args.expect)
        # Do not open candidate files until the prior reviewed inputs are pinned.
        if report['pinMatches']:
            report = finish(report, intended, load_workspace_json(args.candidate))
        else:
            report['accepted'] = False
        print(render(report), end='')
        return 0 if report['accepted'] else 1
    except (ValueError, OSError, RecursionError) as exc:
        # ASCII escaping prevents terminal controls inside malformed input errors.
        print('review-changes: ' + json.dumps(str(exc), ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
