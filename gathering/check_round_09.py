#!/usr/bin/env python3
"""Exercise expected rejections, live replay and a detached shared-tool copy."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PIN = 'c1f7a3ff0b7cf878d16be782f567b2bf89f88e9b962ed64210eeaeb2cf6d7023'
REQUEST_PIN = '8122b8ba057657d449c42e1c0c857be88eda97aebb8c836b07b2cf3589e8316e'
BASELINE_PIN = 'dd94a4fb3ef241db9cffbf8ccb24b4486e0eea308b1c34a7e0668f6c92f90dd4'


def main():
    if Path.cwd() != ROOT:
        raise SystemExit('run from the repository root')
    detached = ROOT / 'test/scratch/portable09'
    shutil.copytree(ROOT / 'shared/payment-evidence', detached / 'shared/payment-evidence', dirs_exist_ok=True)
    bridge = ['shared/payment-evidence/checkpoint_review.py',
        'shared/payment-evidence/checkpoint-baseline.json',
        'shared/payment-evidence/paired-pinned-evidence.json',
        'shared/payment-evidence/paired-pinned-policy.json',
        'shared/payment-evidence/paired-pinned-intended.json',
        'shared/payment-evidence/paired-pinned-intended.json',
        '--baseline-pin', BASELINE_PIN, '--request-pin', REQUEST_PIN,
        '--as-of', '1792012453', '--max-head-age', '120',
        '--max-finalized-age', '1200', '--future-skew', '60']
    commands = [
        (ROOT, 1, ['line-4/tools/review-changes/review_changes.py',
                   'line-4/tools/review-changes/zto-set.json',
                   'line-4/tools/review-changes/zto-one-unit-change.json', '--expect', PIN]),
        (ROOT, 1, ['line-2/tools/contract-change/review.py',
                   'shared/payment-evidence/policy.contract.json',
                   'line-2/tools/contract-change/proposed-policy.contract.json',
                   'shared/payment-evidence/example.policy.json']),
        (ROOT, 0, ['line-1/tools/batched-zto-snapshot/batch.py', '--verify', 'gathering/live-batch-09.json']),
        (ROOT, 0, ['shared/payment-evidence/test_checkpoint_review.py']),
        (ROOT, 0, bridge),
        (detached, 0, bridge),
    ]
    rows = []
    for cwd, expected, args in commands:
        done = subprocess.run([sys.executable, '-B', *args], cwd=cwd,
            capture_output=True, text=True, timeout=45,
            env={'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin'})
        rows.append({'command': 'python3 -B ' + ' '.join(args),
                     'workingDirectory': '.' if cwd == ROOT else cwd.relative_to(ROOT).as_posix(),
                     'expectedExit': expected, 'exitCode': done.returncode,
                     'passed': done.returncode == expected,
                     'stdout': done.stdout, 'stderr': done.stderr})
        print('PASS' if rows[-1]['passed'] else 'FAIL', args[0], done.returncode)
    raw = json.dumps(rows, indent=2)+'\n'
    if len(raw.encode()) > 100000:
        raise ValueError('check log exceeds byte limit')
    (ROOT / 'gathering/round-checks-09.json').write_text(raw)
    return 0 if all(r['passed'] for r in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
