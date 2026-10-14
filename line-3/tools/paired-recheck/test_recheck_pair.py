"""Offline real-ZTO replay; all mutations are explicitly rejection fixtures."""
import copy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch
import recheck_pair as q

FOLDER = Path('line-3/tools/paired-recheck')


def inputs():
    baseline = q.w.load_workspace_json(FOLDER.parent / 'provider-agreement' / 'paired-evidence.json')
    current = q.w.load_workspace_json(FOLDER.parent / 'paired-freshness' / 'paired-evidence.json')
    policy = q.w.load_workspace_json(FOLDER.parent / 'paired-freshness' / 'observed-policy.json')
    trial = q.w.load_workspace_json(FOLDER / 'trial.json')
    return baseline, current, policy, trial


def flip_hash(value):
    return value[:-1] + ('1' if value[-1] != '1' else '2')


class RecheckPairTests(unittest.TestCase):
    def compare(self, baseline=None, current=None, **overrides):
        old, new, policy, trial = inputs()
        return q.compare(old if baseline is None else baseline,
                         new if current is None else current,
                         trial['baselineSha256'], policy, **dict(trial['timeArguments'], **overrides))

    def test_real_history_advances_both_sources_without_mutation(self):
        old, new, policy, trial = inputs()
        original = copy.deepcopy((old, new, policy, trial))
        result = self.compare(old, new)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['state'], 'paired_continued_within_time_budget')
        self.assertEqual(result['baselineSha256'], q.r.digest(old))
        self.assertEqual(result['currentSha256'], q.r.digest(new))
        for report in result['continuity']:
            self.assertGreater(report['current']['head']['number'], report['baseline']['head']['number'])
            self.assertEqual(report['current']['transferEvidence']['netRaw'], policy['minimum_raw'])
        self.assertEqual((old, new, policy, trial), original)

    def test_reused_pair_is_not_a_new_observation(self):
        _, new, policy, trial = inputs()
        result = q.compare(new, new, q.r.digest(new), policy, **trial['timeArguments'])
        self.assertEqual(result['state'], 'no_new_heads')
        self.assertEqual(q.p.exit_code(result), 1)

    def test_changed_baseline_is_rejected_despite_still_accepted_payment(self):
        old, _, _, _ = inputs()
        old['providers'][0]['reads'][2]['result']['logs'].reverse()
        self.assertNotEqual(q.r.digest(old), inputs()[3]['baselineSha256'])
        with self.assertRaises(q.w.Error): self.compare(baseline=old)

    def test_invalid_pin_checked_before_replay(self):
        old, new, policy, trial = inputs()
        for pin in (None, True, 'bad', trial['baselineSha256'].upper(), 'f'*64):
            with self.subTest(pin=pin), patch.object(q.r, 'checkpoint', side_effect=AssertionError('replay')):
                with self.assertRaises(q.w.Error):
                    q.compare(old, new, pin, policy, **trial['timeArguments'])

    def test_both_new_providers_can_agree_on_a_changed_sender_and_still_fail_continuity(self):
        _, current, policy, _ = inputs()
        for item in current['providers']:
            for read in item['reads']:
                if read['method'] == 'eth_getTransactionReceipt':
                    for log in read['result']['logs']:
                        if log['address'].lower() == q.w.TOKENS['ZTO'] and log['topics'][0] == q.s.TRANSFER:
                            log['topics'][1] = '0x' + '0'*24 + q.w.TOKENS['ZTO'][2:]
        result = self.compare(current=current)
        self.assertTrue(result['currentFreshness']['accepted'])
        self.assertFalse(result['accepted'])
        for index in (1, 2):
            self.assertIn('provider_' + str(index) + ':payment_events_changed', result['alerts'])

    def test_current_pair_staleness_revokes_reliance(self):
        result = self.compare(as_of=inputs()[3]['timeArguments']['as_of']+1201)
        self.assertFalse(result['accepted'])
        self.assertTrue(all(item['accepted'] for item in result['continuity']))
        self.assertIn('current:provider_1:head_too_old', result['alerts'])

    def test_one_current_provider_failure_does_not_fall_back(self):
        old, new, policy, trial = inputs()
        calls = []
        def factory(source):
            calls.append(source)
            if len(calls) == 2:
                raise OSError('rejection fixture')
            return q.r.ExactReplay(new['providers'][0]['reads'])
        result = q.collect(old, trial['baselineSha256'], policy, **trial['timeArguments'], rpc_factory=factory)
        self.assertEqual(calls, list(q.a.PROVIDERS))
        self.assertFalse(result['accepted'])
        self.assertEqual(result['state'], 'provider_error')
        self.assertNotIn('currentSample', result)

    def test_capture_replays_exact_same_decision(self):
        old, new, policy, trial = inputs()
        def factory(source):
            return q.r.ExactReplay(new['providers'][q.a.PROVIDERS.index(source)]['reads'])
        live = q.collect(old, trial['baselineSha256'], policy, **trial['timeArguments'], rpc_factory=factory)
        replay = self.compare(current=live['currentSample'])
        for key in ('accepted', 'alerts', 'state', 'baselineSha256', 'currentSha256', 'continuity'):
            self.assertEqual(live[key], replay[key])

    def test_policy_mismatch_and_invalid_clock_before_transport(self):
        old, _, policy, trial = inputs()
        for change in ({'as_of': True}, {'max_head_age': 0}, {'future_skew': 3601}):
            with self.subTest(change=change), self.assertRaises(q.w.Error):
                q.collect(old, trial['baselineSha256'], policy,
                          **dict(trial['timeArguments'], **change),
                          rpc_factory=lambda source: self.fail('transport'))
        policy['minimum_raw'] = '1'
        with self.assertRaises(q.w.Error):
            q.collect(old, trial['baselineSha256'], policy, **trial['timeArguments'],
                      rpc_factory=lambda source: self.fail('transport'))

    def test_malformed_or_unaccepted_baseline_with_matching_pin(self):
        for kind in ('extra', 'version', 'sources', 'request_type', 'unused', 'amount'):
            old, new, policy, trial = inputs()
            if kind == 'extra': old['accepted'] = True
            if kind == 'version': old['version'] = True
            if kind == 'sources': old['providers'].reverse()
            if kind == 'request_type': old['providers'][0]['reads'][1]['params'][1] = 0
            if kind == 'unused': old['providers'][0]['reads'].append(copy.deepcopy(old['providers'][0]['reads'][0]))
            if kind == 'amount':
                policy['minimum_raw'] = str(int(policy['minimum_raw'])+1)
                old['policy'] = copy.deepcopy(policy)
            with self.subTest(kind=kind), self.assertRaises(q.w.Error):
                q.compare(old, new, q.r.digest(old), policy, **trial['timeArguments'])

    def test_baseline_shared_head_conflict_even_when_payment_fingerprints_match(self):
        old, new, policy, trial = inputs()
        reads = old['providers'][1]['reads']
        height = reads[1]['result']['number']
        for read in reads:
            if read['method'] == 'eth_getBlockByNumber' and read['result']['number'] == height:
                read['result']['hash'] = flip_hash(read['result']['hash'])
        self.assertTrue(q.a.replay(old)['accepted'])
        with self.assertRaises(q.w.Error): q.compare(old, new, q.r.digest(old), policy, **trial['timeArguments'])

    def test_old_and_new_inclusion_timestamp_conflict(self):
        old, new, policy, trial = inputs()
        inclusion = new['providers'][0]['reads'][2]['result']['blockNumber']
        stamp = next(x['result']['timestamp'] for x in new['providers'][0]['reads']
                     if x['method'] == 'eth_getBlockByNumber' and x['result']['number'] == inclusion)
        for item in old['providers']:
            for read in item['reads']:
                if read['method'] == 'eth_getBlockByNumber' and read['result']['number'] == inclusion:
                    read['result']['timestamp'] = hex(int(stamp,16)+1)
        result = q.compare(old, new, q.r.digest(old), policy, **trial['timeArguments'])
        self.assertTrue(result['currentFreshness']['accepted'])
        self.assertIn('checkpoint_header_conflict', result['alerts'])

    def test_finalized_head_regression_rejected_even_when_both_payments_pass(self):
        old, new, policy, trial = inputs()
        # Rejection fixture: use the old real finalized anchor in a later baseline.
        baseline = copy.deepcopy(new)
        for index, item in enumerate(new['providers']):
            old_final = next(x['result'] for x in old['providers'][index]['reads'] if x['params'] == ['finalized', False])
            new_final_number = next(x['result']['number'] for x in item['reads'] if x['params'] == ['finalized', False])
            # Actual historical timestamp is not needed for this synthetic fixture;
            # retain a monotonic earlier timestamp from the later observed final head.
            timestamp = next(x['result']['timestamp'] for x in item['reads'] if x['params'] == ['finalized', False])
            for read in item['reads']:
                if read['method'] == 'eth_getBlockByNumber' and read['result']['number'] == new_final_number:
                    if read['params'][0] != 'finalized': read['params'][0] = old_final['number']
                    read['result'] = dict(old_final, timestamp=timestamp)
        result = q.compare(baseline, new, q.r.digest(baseline), policy, **trial['timeArguments'])
        self.assertTrue(result['currentFreshness']['accepted'])
        self.assertIn('provider_1:finalized_head_regressed', result['alerts'])

    def test_current_source_envelope_and_requests_strict(self):
        for kind in ('source', 'version', 'extra', 'request', 'unused'):
            _, new, _, _ = inputs()
            if kind == 'source': new['providers'].pop()
            if kind == 'version': new['version'] = True
            if kind == 'extra': new['accepted'] = True
            if kind == 'request': new['providers'][0]['reads'][1]['params'][1] = 0
            if kind == 'unused': new['providers'][0]['reads'].append(copy.deepcopy(new['providers'][0]['reads'][0]))
            with self.subTest(kind=kind), self.assertRaises(q.w.Error): self.compare(current=new)

    def test_event_order_does_not_change_continuity(self):
        _, new, _, _ = inputs()
        for item in new['providers']:
            for read in item['reads']:
                if read['method'] == 'eth_getTransactionReceipt': read['result']['logs'].reverse()
        self.assertTrue(self.compare(current=new)['accepted'])

    def test_one_advancing_head_cannot_cover_an_unchanged_second_head(self):
        _, new, policy, trial = inputs()
        baseline = copy.deepcopy(new)
        reads = new['providers'][0]['reads']
        old_height = reads[1]['result']['number']
        for read in reads:
            if read['method'] == 'eth_getBlockByNumber' and read['result']['number'] == old_height:
                read['result']['number'] = hex(int(old_height,16)+1)
                read['result']['hash'] = flip_hash(read['result']['hash'])
                read['result']['timestamp'] = hex(int(read['result']['timestamp'],16)+12)
                if read['params'][0] != 'latest': read['params'][0] = read['result']['number']
        result = q.compare(baseline, new, q.r.digest(baseline), policy, **trial['timeArguments'])
        self.assertTrue(result['currentFreshness']['accepted'])
        self.assertEqual(result['alerts'], ['provider_2:head_unchanged'])

    def test_old_head_conflicts_with_new_finalized_anchor(self):
        old, new, policy, trial = inputs()
        anchor = next(x['result'] for x in new['providers'][0]['reads'] if x['params'] == ['finalized',False])
        for item in old['providers']:
            reads = item['reads']
            height = reads[1]['result']['number']
            for read in reads:
                if read['method'] == 'eth_getBlockByNumber' and read['result']['number'] == height:
                    read['result'] = {'number':anchor['number'], 'hash':flip_hash(anchor['hash'])}
                    if read['params'][0] != 'latest': read['params'][0] = anchor['number']
        result = q.compare(old, new, q.r.digest(old), policy, **trial['timeArguments'])
        self.assertTrue(result['currentFreshness']['accepted'])
        self.assertTrue(all(item['accepted'] for item in result['continuity']))
        self.assertEqual(result['alerts'], ['checkpoint_header_conflict'])

    def test_missing_receipts_never_continue(self):
        _, new, _, _ = inputs()
        for item in new['providers']:
            item['reads'] = item['reads'][:3]
            item['reads'][2]['result'] = None
        result = self.compare(current=new)
        self.assertFalse(result['accepted'])
        self.assertIn('provider_1:receipt_missing', result['alerts'])
        self.assertIn('current:provider_2:finalized_anchor_missing', result['alerts'])

    def test_cli_pin_failure_before_current_file_open(self):
        paths = []
        reader = q.w.load_workspace_json
        def load(path):
            paths.append(str(path))
            return reader(path)
        with patch.object(q.w, 'load_workspace_json', side_effect=load), redirect_stdout(io.StringIO()):
            code = q.main(['--current', 'does-not-exist.json', '--baseline',
                          str(FOLDER.parent/'provider-agreement'/'paired-evidence.json'),
                          '--policy', str(FOLDER.parent/'paired-freshness'/'observed-policy.json'),
                          '--baseline-sha256', 'f'*64, '--as-of', '1792012453',
                          '--max-head-age', '120', '--max-finalized-age', '1200'])
        self.assertEqual(code, 2)
        self.assertNotIn('does-not-exist.json', paths)

    def test_demo_and_missing_arguments(self):
        output = io.StringIO()
        with redirect_stdout(output): self.assertEqual(q.main(['--demo']), 0)
        self.assertTrue(json.loads(output.getvalue())['accepted'])
        for args in (['--live'], ['--demo','--as-of','1'], ['--current','missing.json']):
            with self.subTest(args=args), redirect_stdout(io.StringIO()): self.assertEqual(q.main(args), 2)

    def test_no_environment_lookup_and_output_bound(self):
        with patch.object(q.s.urllib.request, 'getproxies', side_effect=AssertionError('environment')):
            q.s.RPC(q.s.RPC_URL)
            self.assertTrue(self.compare()['accepted'])
        with self.assertRaises(q.w.Error), redirect_stdout(io.StringIO()): q.p.emit({'x':'x'*100000})


if __name__ == '__main__':
    unittest.main()
