"""Offline integration and fail-closed ordering tests on real historical ZTO."""
import copy
import io
import json
from contextlib import redirect_stdout
from unittest.mock import patch
import unittest

import checkpoint_review as tool

HERE = 'shared/payment-evidence/'
BASELINE_PIN = 'dd94a4fb3ef241db9cffbf8ccb24b4486e0eea308b1c34a7e0668f6c92f90dd4'
REQUEST_PIN = '8122b8ba057657d449c42e1c0c857be88eda97aebb8c836b07b2cf3589e8316e'


class CheckpointReview(unittest.TestCase):
    def setUp(self):
        self.values = dict(
            baseline=tool.load(HERE + 'checkpoint-baseline.json'),
            current=tool.load(HERE + 'paired-pinned-evidence.json'),
            policy=tool.load(HERE + 'paired-pinned-policy.json'),
            intended=tool.load(HERE + 'paired-pinned-intended.json'),
            client=tool.load(HERE + 'paired-pinned-intended.json'),
            baseline_pin=BASELINE_PIN, request_pin=REQUEST_PIN,
            as_of=1792012453, max_head_age=120, max_finalized_age=1200, future_skew=60)

    def decide(self, **changes):
        return tool.review(**dict(self.values, **changes))

    def test_historical_zto_and_input_immutability(self):
        before = copy.deepcopy(self.values)
        report = self.decide()
        self.assertTrue(report['accepted'])
        self.assertEqual(report['state'], 'checkpoint_and_pinned_request_match')
        self.assertEqual(self.values, before)
        self.assertLess(len(tool.render(report).encode()), 100000)

    def test_one_unit_change_is_explained_exactly(self):
        request = self.values['client']['requests'][0]['request']
        data = json.loads(request['params'][1])
        old = data['message']['minimumRaw']
        data['message']['minimumRaw'] = str(int(old) + 1)
        request['params'][1] = json.dumps(data)
        report = self.decide()
        self.assertFalse(report['accepted'])
        self.assertTrue(report['checkpointAccepted'])
        self.assertEqual(report['requestChanges']['requests'][0]['changes'], [
            {'path': '/message/minimumRaw', 'reason': 'value',
             'before': old, 'after': str(int(old)+1)}])

    def test_account_change_even_with_equal_digest(self):
        self.values['client']['requests'][0]['request']['params'][0] = tool.recheck.w.TOKENS['ZTO']
        report = self.decide()
        self.assertFalse(report['accepted'])
        change = report['requestChanges']['requests'][0]
        self.assertTrue(change['digestMatches'])
        self.assertEqual(change['changes'][0]['reason'], 'public_account')

    def test_stale_current_pair(self):
        report = self.decide(as_of=self.values['as_of'] + 1201)
        self.assertFalse(report['accepted'])
        self.assertFalse(report['checkpointAccepted'])
        self.assertTrue(report['requestChanges']['accepted'])

    def test_unchanged_heads_are_not_progress(self):
        current = self.values['current']
        report = self.decide(baseline=current, baseline_pin=tool.recheck.r.digest(current))
        self.assertFalse(report['accepted'])
        self.assertEqual(report['checkpointState'], 'no_new_heads')
        self.assertTrue(report['currentEvidenceAndRequestAccepted'])

    def test_still_settled_modified_evidence_loses_request_binding(self):
        for provider in self.values['current']['providers']:
            for read in provider['reads']:
                if read['method'] == 'eth_getTransactionReceipt':
                    read['result']['cumulativeGasUsed'] = '0x1653c5d'
        report = self.decide()
        self.assertTrue(report['checkpointAccepted'])
        self.assertFalse(report['intendedBindsExactCurrentEvidenceAndPolicy'])
        self.assertFalse(report['accepted'])

    def test_replaced_baseline_is_invalid(self):
        self.values['baseline']['providers'][0]['reads'][2]['result']['logs'].reverse()
        with self.assertRaises(ValueError):
            self.decide()

    def test_replaced_intended_pin_stops_before_checkpoint(self):
        with patch.object(tool.recheck, 'validate', side_effect=AssertionError('checkpoint opened')):
            report = self.decide(request_pin=BASELINE_PIN)
        self.assertEqual(report['state'], 'request_pin_mismatch')

    def arguments(self):
        return [HERE + 'checkpoint-baseline.json', 'missing-current.json',
                HERE + 'paired-pinned-policy.json', HERE + 'paired-pinned-intended.json',
                'missing-client.json', '--baseline-pin', BASELINE_PIN,
                '--request-pin', REQUEST_PIN, '--as-of', '1792012453',
                '--max-head-age', '120', '--max-finalized-age', '1200']

    def test_cli_wrong_request_pin_before_evidence_files(self):
        args = self.arguments(); args[args.index('--request-pin')+1] = BASELINE_PIN
        output = io.StringIO()
        with patch.object(tool, 'load', wraps=tool.load) as loader, redirect_stdout(output):
            self.assertEqual(tool.main(args), 1)
        self.assertEqual(loader.call_count, 1)
        self.assertEqual(json.loads(output.getvalue())['state'], 'request_pin_mismatch')

    def test_cli_wrong_checkpoint_pin_before_current_and_client(self):
        args = self.arguments(); args[args.index('--baseline-pin')+1] = REQUEST_PIN
        output = io.StringIO()
        with patch.object(tool, 'load', wraps=tool.load) as loader, redirect_stdout(output):
            self.assertEqual(tool.main(args), 2)
        self.assertEqual([c.args[0] for c in loader.call_args_list], [args[3], args[0], args[2]])
        self.assertEqual(json.loads(output.getvalue())['state'], 'input_error')

    def test_cli_missing_current_fails_closed(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tool.main(self.arguments()), 2)

    def test_combined_report_size_is_bounded(self):
        with self.assertRaises(ValueError):
            tool.render({'details': 'x' * 100000})


if __name__ == '__main__':
    unittest.main(verbosity=2)
