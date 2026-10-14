#!/usr/bin/env python3
"""Recheck two-provider ZTO evidence and explain a pinned request's changes."""
import argparse
import sys

from check import load, module
from paired_pinned_review import render, review as paired_review
import review_pin
import review_changes

recheck = module('shared_checkpoint_recheck', 'vendor/paired-recheck/recheck_pair.py')


def preflight(baseline, policy, intended, baseline_pin, request_pin,
              as_of, max_head_age, max_finalized_age, future_skew=0):
    pin = review_pin.verify_pin(intended, request_pin)
    if not pin['pinMatches']:
        return {'accepted': False, 'state': 'request_pin_mismatch', 'pin': pin}
    recheck.validate(baseline, baseline_pin, policy, as_of, max_head_age,
                     max_finalized_age, future_skew)
    return None


def review(baseline, current, policy, intended, client, baseline_pin,
           request_pin, as_of, max_head_age, max_finalized_age, future_skew=0):
    bounds = (as_of, max_head_age, max_finalized_age, future_skew)
    rejected = preflight(baseline, policy, intended, baseline_pin, request_pin, *bounds)
    if rejected:
        return rejected
    continuity = recheck.compare(baseline, current, baseline_pin, policy, *bounds)
    binding = paired_review(current, policy, intended, client, request_pin, *bounds)
    changes = review_changes.review(intended, client, request_pin)
    accepted = continuity['accepted'] and binding['accepted'] and changes['accepted']
    result = {
        'accepted': accepted,
        'state': 'checkpoint_and_pinned_request_match' if accepted else 'review_required',
        'checkpointAccepted': continuity['accepted'],
        'currentEvidenceAndRequestAccepted': binding['accepted'],
        'baselineSha256': continuity['baselineSha256'],
        'currentSha256': continuity['currentSha256'],
        'checkpointState': continuity['state'],
        'checkpointAlerts': continuity['alerts'],
        'timePolicy': continuity['timePolicy'],
        'intendedBindsExactCurrentEvidenceAndPolicy': binding['intendedBindsExactSampleAndPolicy'],
        'requestChanges': changes,
        'limits': ('Historical observations and caller time remain trusted. Retain both pins '
                   'independently. Unchanged means comparison passed, not authorization. '
                   'No invoice, source authentication, ancestry proof, signature or current chain truth.')}
    render(result)  # Bound the complete combined report, including change explanations.
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'current', 'policy', 'intended', 'client'):
        parser.add_argument(name, help='visible workspace-relative JSON file')
    parser.add_argument('--baseline-pin', required=True)
    parser.add_argument('--request-pin', required=True)
    for name in ('as-of', 'max-head-age', 'max-finalized-age'):
        parser.add_argument('--' + name, type=int, required=True)
    parser.add_argument('--future-skew', type=int, default=0)
    args = parser.parse_args(argv)
    try:
        intended = load(args.intended)
        # Reject a replaced intended review before opening evidence or candidate files.
        pin = review_pin.verify_pin(intended, args.request_pin)
        if not pin['pinMatches']:
            print(render({'accepted': False, 'state': 'request_pin_mismatch', 'pin': pin}), end='')
            return 1
        baseline, policy = load(args.baseline), load(args.policy)
        bounds = (args.as_of, args.max_head_age, args.max_finalized_age, args.future_skew)
        preflight(baseline, policy, intended, args.baseline_pin, args.request_pin, *bounds)
        result = review(baseline, load(args.current), policy, intended, load(args.client),
                        args.baseline_pin, args.request_pin, *bounds)
        print(render(result), end='')
        return 0 if result['accepted'] else 1
    except (ValueError, OSError, TypeError, KeyError, IndexError, RecursionError):
        print(render({'accepted': False, 'state': 'input_error',
                      'reason': 'Invalid retained pin, checkpoint, policy, time, evidence, request or output bound.'}), end='')
        return 2


if __name__ == '__main__':
    sys.exit(main())
