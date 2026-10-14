#!/usr/bin/env python3
"""Recheck a retained paired Ethereum payment checkpoint against timely evidence."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

_spec = importlib.util.spec_from_file_location(
    'recheck_pair_freshness', Path(__file__).resolve().parent.parent / 'paired-freshness' / 'paired.py')
p = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p)
f, r, a, w, s = p.f, p.r, p.a, p.w, p.s
LIMIT = ('Historical provider observations, not consensus, receipt proofs or source authentication. '
         'A retained digest detects replacement only if retained independently. Source labels do not '
         'prove independent operators. Caller time and provider timestamps are trusted. '
         'No ancestry proof connects different-height anchors; later reorgs remain possible.')


def singles(sample, policy):
    if (not isinstance(sample, dict) or set(sample) != {'version', 'policy', 'providers'}
            or type(sample['version']) is not int or sample['version'] != 1
            or a.validate_policy(sample['policy']) != policy):
        raise w.Error('invalid pair or independently chosen policy mismatch')
    providers = sample['providers']
    if not isinstance(providers, list) or len(providers) != 2:
        raise w.Error('two observations required')
    result = []
    for source, item in zip(a.PROVIDERS, providers):
        if (not isinstance(item, dict) or set(item) != {'source', 'reads'}
                or item['source'] != source):
            raise w.Error('documented sources required in order')
        result.append({'version': 1, 'policy': policy, 'reads': item['reads']})
    return result


def block_facts(samples):
    """Legacy checkpoints lack timestamps; always compare their block identities."""
    facts = {}
    for sample in samples:
        for read in sample['reads']:
            if read['method'] != 'eth_getBlockByNumber':
                continue
            header = read['result']
            if not isinstance(header, dict):
                raise w.Error('missing block header')
            number, block_hash = s.quantity(header.get('number')), s.hash32(header.get('hash'))
            stamp = None
            if 'timestamp' in header:
                stamp = f.integer(s.quantity(header['timestamp']), 'block timestamp')
            facts.setdefault(number, []).append((block_hash, stamp))
    return facts


def conflicts(facts):
    return sorted(number for number, entries in facts.items()
                  if len({value[0] for value in entries}) > 1
                  or len({value[1] for value in entries if value[1] is not None}) > 1)


def checkpoint(baseline, baseline_sha256, expected_policy):
    if (not isinstance(baseline_sha256, str)
            or re.fullmatch('[0-9a-f]{64}', baseline_sha256) is None
            or r.digest(baseline) != baseline_sha256):
        raise w.Error('retained checkpoint digest mismatch')
    old = singles(baseline, expected_policy)
    reports = [r.checkpoint(sample)[1] for sample in old]
    if not a.compare(reports, expected_policy)['accepted'] or conflicts(block_facts(old)):
        raise w.Error('baseline must be a consistent accepted pair')
    return old


def validate(baseline, baseline_sha256, expected_policy, as_of,
             max_head_age, max_finalized_age, future_skew):
    policy, bounds = f.validate(expected_policy, as_of, max_head_age, max_finalized_age, future_skew)
    old = checkpoint(baseline, baseline_sha256, policy)
    return policy, bounds, old


def compare(baseline, current, baseline_sha256, expected_policy, as_of,
            max_head_age, max_finalized_age, future_skew=0):
    policy, bounds, old = validate(baseline, baseline_sha256, expected_policy, as_of,
                                  max_head_age, max_finalized_age, future_skew)
    timely = p.evaluate(current, policy, as_of, max_head_age, max_finalized_age, future_skew)
    new = singles(current, policy)
    continuity = [r.compare(before, after) for before, after in zip(old, new)]
    alerts = ['current:' + alert for alert in timely['alerts']]
    for index, report in enumerate(continuity, 1):
        alerts.extend('provider_' + str(index) + ':' + alert for alert in report['alerts'])
    conflicting = conflicts(block_facts(old + new))
    if conflicting:
        alerts.append('checkpoint_header_conflict')
    no_progress = ['provider_1:head_unchanged', 'provider_2:head_unchanged']
    return {'accepted': not alerts,
            'state': 'paired_continued_within_time_budget' if not alerts else
                     'no_new_heads' if alerts == no_progress else 'review_required',
            'alerts': alerts, 'policy': policy, 'timePolicy': bounds,
            'baselineSha256': baseline_sha256, 'currentSha256': r.digest(current),
            'conflictingBlockNumbers': conflicting,
            'continuity': [dict(source=source, **report)
                           for source, report in zip(a.PROVIDERS, continuity)],
            'currentFreshness': timely,
            'evidenceMode': 'offline historical paired recheck at explicit time',
            'evidenceLimit': LIMIT}


def collect(baseline, baseline_sha256, expected_policy, as_of,
            max_head_age, max_finalized_age, future_skew=0, rpc_factory=s.RPC):
    # Refuse an invalid pin, baseline, policy or clock before transport construction.
    validate(baseline, baseline_sha256, expected_policy, as_of,
             max_head_age, max_finalized_age, future_skew)
    observed = p.collect(expected_policy, as_of, max_head_age, max_finalized_age,
                         future_skew, rpc_factory=rpc_factory)
    if 'sample' not in observed:
        return {'accepted': False, 'state': 'provider_error',
                'reason': 'Both complete observations required; no fallback.', 'evidenceLimit': LIMIT}
    result = compare(baseline, observed['sample'], baseline_sha256, expected_policy,
                     as_of, max_head_age, max_finalized_age, future_skew)
    result.update(currentSample=observed['sample'],
                  evidenceMode='live sequential read-only paired recheck at explicit time')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo', action='store_true')
    mode.add_argument('--current', help='workspace-relative current paired transcript')
    mode.add_argument('--live', action='store_true')
    parser.add_argument('--baseline', help='workspace-relative retained paired transcript')
    parser.add_argument('--baseline-sha256', help='independently retained canonical JSON digest')
    parser.add_argument('--policy', help='workspace-relative independently chosen payment policy')
    parser.add_argument('--as-of', type=int)
    parser.add_argument('--max-head-age', type=int)
    parser.add_argument('--max-finalized-age', type=int)
    parser.add_argument('--future-skew', type=int)
    args = parser.parse_args(argv)
    try:
        if args.demo:
            if any(value is not None for value in (args.baseline, args.baseline_sha256, args.policy,
                    args.as_of, args.max_head_age, args.max_finalized_age, args.future_skew)):
                raise w.Error('demo refuses overrides')
            folder = Path(__file__).resolve().parent.relative_to(Path.cwd())
            trial = w.load_workspace_json(folder / 'trial.json')
            baseline = w.load_workspace_json(folder.parent / 'provider-agreement' / 'paired-evidence.json')
            current = w.load_workspace_json(folder.parent / 'paired-freshness' / 'paired-evidence.json')
            policy = w.load_workspace_json(folder.parent / 'paired-freshness' / 'observed-policy.json')
            result = compare(baseline, current, trial['baselineSha256'], policy, **trial['timeArguments'])
            result['demoNote'] = ('Real historical ZTO pairs. Demo pin and recipient/amount are illustrative, '
                                  'not independently retained approval, an invoice or present freshness.')
        else:
            if args.baseline is None or args.baseline_sha256 is None or args.policy is None:
                raise w.Error('baseline, retained digest and expected policy required')
            baseline = w.load_workspace_json(args.baseline)
            policy = w.load_workspace_json(args.policy)
            inputs = (args.baseline_sha256, policy, args.as_of, args.max_head_age,
                      args.max_finalized_age, args.future_skew if args.future_skew is not None else 0)
            validate(baseline, *inputs)  # Check the pin before opening current evidence.
            result = collect(baseline, *inputs) if args.live else compare(
                baseline, w.load_workspace_json(args.current), *inputs)
        p.emit(result)
        return p.exit_code(result)
    except (w.Error, ValueError, TypeError, KeyError, OSError, RecursionError):
        p.emit({'accepted': False, 'state': 'input_error',
                'reason': 'Invalid retained checkpoint, digest, policy, clock, transcript or output size'})
        return 2


if __name__ == '__main__':
    sys.exit(main())
