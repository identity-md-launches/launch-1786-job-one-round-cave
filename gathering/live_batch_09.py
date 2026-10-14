#!/usr/bin/env python3
"""One-shot real ZTO batch trial through an explicitly supplied read transport."""
import argparse
import importlib.util
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport', required=True,
                        help='approved routing URL; never recorded as evidence source')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        'gathering_batch09', ROOT / 'line-1/tools/batched-zto-snapshot/batch.py')
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), batch.B['NoRedirect']())

    def exchange(requests):
        request = urllib.request.Request(args.transport, data=batch.P['canonical'](requests),
            headers={'User-Agent': 'Pepeolithic-Gathering09-ZTO/1.0',
                     'Content-Type': 'application/json', 'Accept-Encoding': 'identity'})
        with opener.open(request, timeout=15) as response:
            raw = response.read(100001)
            if len(raw) > 100000:
                raise ValueError('RPC response exceeds byte bound')
            content_type = response.headers.get('Content-Type', '')
        return content_type, batch.B['parse_json'](raw)

    def read(method, params, timeout):
        batch.P['validate_request'](method, params)
        content_type, answer = exchange({'jsonrpc': '2.0', 'id': 1,
                                        'method': method, 'params': params})
        batch.B['validate_response'](answer)
        return {'method': method, 'params': params, 'content_type': content_type,
                'response': answer, 'response_sha256': batch.P['digest'](answer)}

    def read_batch(requests, timeout):
        block_hash = requests[0]['params'][1]['blockHash']
        if not batch.P['HASH'].fullmatch(block_hash) or requests != batch.requests_for(block_hash):
            raise ValueError('only the two fixed hash-pinned ZTO reads are permitted')
        return exchange(requests)

    try:
        bundle, result = batch.capture(read=read, batch_read=read_batch)
        raw = (json.dumps(bundle, indent=2, sort_keys=True) + '\n').encode()
        batch.SAFE['write_bytes']('gathering/live-batch-09.json', raw, 100000)
        trial = {'passed': True, 'source': batch.P['SOURCE'], 'result': result,
                 'savedBytes': len(raw), 'mode': 'one-shot live read, no polling'}
    except (ValueError, OSError, batch.P['PinnedError'], batch.B['SnapshotError']):
        trial = {'passed': False, 'source': batch.P['SOURCE'],
                 'reason': 'Read transport, response validation or evidence byte bound failed; no value inferred.'}
    (ROOT / 'gathering/live-batch-trial-09.json').write_text(json.dumps(trial, indent=2)+'\n')
    print(json.dumps(trial, indent=2))
    return 0 if trial['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
