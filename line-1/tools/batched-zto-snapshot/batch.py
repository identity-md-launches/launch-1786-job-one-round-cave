#!/usr/bin/env python3
"""Capture and replay two hash-pinned ZTO reads in one JSON-RPC batch."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import sys
import urllib.error
import urllib.request

P = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                       'hash-pinned-zto' / 'pinned.py'))
B = P['B']
SAFE = P['SAFE']
SCHEMA = 'line1-batched-zto-v1'
MAX_BYTES = 100000
SELECTORS = ('0x18160ddd', '0x313ce567')


class BatchError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise BatchError(message)


def requests_for(block_hash):
    pin = {'blockHash': block_hash, 'requireCanonical': True}
    return [
        {'jsonrpc': '2.0', 'id': index,
         'method': 'eth_call',
         'params': [{'to': P['ZTO'], 'data': selector}, dict(pin)]}
        for index, selector in enumerate(SELECTORS, 1)
    ]


def validate_batch(requests, responses, block_hash):
    require(requests == requests_for(block_hash),
            'batch requests are not the two hash-pinned ZTO reads')
    require(isinstance(responses, list) and len(responses) == 2,
            'batch must contain exactly two responses')
    by_id = {}
    for response in responses:
        require(isinstance(response, dict) and
                set(response) == {'jsonrpc', 'id', 'result'} and
                response['jsonrpc'] == '2.0' and
                type(response['id']) is int and response['id'] in (1, 2),
                'batch response has an invalid envelope or ID')
        require(response['id'] not in by_id, 'duplicate batch response ID')
        value = response['result']
        require(isinstance(value, str) and P['HASH'].fullmatch(value),
                'batch result is not one ABI word')
        by_id[response['id']] = int(value, 16)
    require(set(by_id) == {1, 2}, 'batch response ID is missing')
    require(by_id[2] <= 255, 'decimals result exceeds uint8')
    return by_id[1], by_id[2]


def rpc_batch(requests, timeout):
    require(isinstance(requests, list) and len(requests) == 2 and
            isinstance(requests[0], dict) and
            isinstance(requests[0].get('params'), list) and
            len(requests[0]['params']) == 2 and
            isinstance(requests[0]['params'][1], dict) and
            isinstance(requests[0]['params'][1].get('blockHash'), str),
            'invalid batch request shape')
    require(P['HASH'].fullmatch(requests[0]['params'][1]['blockHash']),
            'invalid batch block hash')
    require(requests == requests_for(requests[0]['params'][1]['blockHash']),
            'unsafe batch request')
    require(type(timeout) in (int, float) and 0 < timeout <= 60,
            'timeout must be within (0, 60] seconds')
    body = P['canonical'](requests)
    require(len(body) < 16384, 'batch request exceeds byte limit')
    request = urllib.request.Request(
        P['SOURCE'], data=body, method='POST',
        headers={'User-Agent': 'Pepeolithic-Line1-BatchedZTO/1.0',
                 'Content-Type': 'application/json',
                 'Accept': 'application/json',
                 'Accept-Encoding': 'identity'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                         B['NoRedirect']())
    try:
        with opener.open(request, timeout=timeout) as response:
            require(response.status == 200, 'RPC HTTP response was not 200')
            raw = response.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, 'batch response exceeds byte limit')
            content_type = response.headers.get('Content-Type', '')
    except urllib.error.HTTPError as exc:
        raise BatchError('RPC HTTP error ' + str(exc.code)) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BatchError('RPC transport failed') from exc
    parsed = B['parse_json'](raw)
    validate_batch(requests, parsed, requests[0]['params'][1]['blockHash'])
    return content_type, parsed


def validate_bundle(bundle):
    require(isinstance(bundle, dict) and set(bundle) == {
        'schema', 'rpc_url', 'captured_at_utc', 'chain', 'anchor',
        'batch', 'recheck', 'transcript_sha256'},
        'bundle fields differ from schema')
    require(bundle['schema'] == SCHEMA and bundle['rpc_url'] == P['SOURCE'],
            'unexpected schema or public RPC source')
    stamp = bundle['captured_at_utc']
    require(isinstance(stamp, str) and len(stamp) <= 64,
            'invalid capture timestamp')
    try:
        moment = datetime.fromisoformat(stamp)
    except ValueError as exc:
        raise BatchError('invalid capture timestamp') from exc
    require(moment.utcoffset() is not None and
            moment.utcoffset().total_seconds() == 0,
            'capture timestamp must be UTC')
    chain = bundle['chain']
    anchor = bundle['anchor']
    recheck = bundle['recheck']
    for read in (chain, anchor, recheck):
        P['validate_read'](read)
    require(chain['method'] == 'eth_chainId' and chain['params'] == [] and
            chain['response']['result'] == '0x1',
            'chain read must report Ethereum mainnet')
    require(anchor['method'] == 'eth_getBlockByNumber' and
            anchor['params'] == ['finalized', False],
            'anchor must select the finalized block')
    number, block_hash = P['block_identity'](anchor['response']['result'])
    require(recheck['method'] == 'eth_getBlockByNumber' and
            recheck['params'] == [number, False] and
            P['block_identity'](recheck['response']['result']) == (number, block_hash),
            'anchor changed around the batch')
    batch = bundle['batch']
    require(isinstance(batch, dict) and set(batch) == {
        'requests', 'content_type', 'responses', 'responses_sha256'},
        'batch fields differ from schema')
    require(isinstance(batch['content_type'], str) and
            len(batch['content_type']) <= 200,
            'invalid batch content type')
    supply, decimals = validate_batch(batch['requests'], batch['responses'],
                                      block_hash)
    require(batch['responses_sha256'] == P['digest'](batch['responses']),
            'batch response checksum mismatch')
    transcript = {key: bundle[key] for key in
                  ('chain', 'anchor', 'batch', 'recheck')}
    require(bundle['transcript_sha256'] == P['digest'](transcript),
            'transcript checksum mismatch')
    digits = str(supply).rjust(decimals + 1, '0')
    human = digits if decimals == 0 else digits[:-decimals] + '.' + digits[-decimals:]
    return {
        'status': 'two_hash_pinned_reads_correlated_by_id',
        'block_number': P['quantity'](number), 'block_hash': block_hash,
        'zto_address': P['ZTO'], 'total_supply_raw': str(supply),
        'decimals': decimals, 'total_supply_tokens': human,
        'batch_response_order': [r['id'] for r in batch['responses']],
        'transcript_sha256': bundle['transcript_sha256'],
        'evidence': 'Provider observations, not an atomic read or state proof',
    }


def capture(timeout=15, read=None, batch_read=None):
    read = P['rpc_read'] if read is None else read
    batch_read = rpc_batch if batch_read is None else batch_read
    chain = read('eth_chainId', [], timeout)
    require(P['validate_read'](chain) == '0x1', 'provider did not report mainnet')
    anchor = read('eth_getBlockByNumber', ['finalized', False], timeout)
    number, block_hash = P['block_identity'](P['validate_read'](anchor))
    requests = requests_for(block_hash)
    content_type, responses = batch_read(requests, timeout)
    validate_batch(requests, responses, block_hash)
    batch = {'requests': requests, 'content_type': content_type,
             'responses': responses, 'responses_sha256': P['digest'](responses)}
    recheck = read('eth_getBlockByNumber', [number, False], timeout)
    transcript = {'chain': chain, 'anchor': anchor,
                  'batch': batch, 'recheck': recheck}
    bundle = {'schema': SCHEMA, 'rpc_url': P['SOURCE'],
              'captured_at_utc': datetime.now(timezone.utc).isoformat(),
              **transcript, 'transcript_sha256': P['digest'](transcript)}
    return bundle, validate_bundle(bundle)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--capture', metavar='OUTPUT',
                        help='capture to a new visible workspace file')
    action.add_argument('--verify', metavar='FILE', help='check saved bytes offline')
    parser.add_argument('--timeout', type=float, default=15)
    args = parser.parse_args(argv)
    try:
        if args.verify:
            raw = SAFE['read_bytes'](args.verify, MAX_BYTES)
            result = validate_bundle(B['parse_json'](raw))
        else:
            SAFE['parts'](args.capture)
            bundle, result = capture(args.timeout)
            raw = (json.dumps(bundle, indent=2, sort_keys=True,
                              allow_nan=False) + '\n').encode()
            SAFE['write_bytes'](args.capture, raw, MAX_BYTES)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (BatchError, P['PinnedError'], B['SnapshotError'],
            OSError, ValueError, RecursionError) as exc:
        print('batched-zto-snapshot: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
