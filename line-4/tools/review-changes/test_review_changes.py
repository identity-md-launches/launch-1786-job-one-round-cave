import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from review_changes import display, explain_item, main, render, review
from review_pin import commitment
from typed_digest import TypedDataError

ROOT = Path(__file__).parent
DEMO = json.loads((ROOT / 'zto-set.json').read_text())
PIN = (ROOT / 'zto.pin').read_text().strip()


def alter(value, operation):
    request = value['requests'][0]['request']
    data = json.loads(request['params'][1])
    operation(data)
    request['params'][1] = json.dumps(data)


def request_data(data):
    value = copy.deepcopy(DEMO)
    value['requests'][0]['request']['params'][1] = json.dumps(data)
    return value


def fields_data(fields, message, extra=None):
    return {'types': {'EIP712Domain': [], 'Example': fields, **(extra or {})},
            'primaryType': 'Example', 'domain': {}, 'message': message}


class ChangeTests(unittest.TestCase):
    def setUp(self):
        self.changed = copy.deepcopy(DEMO)

    def changes(self, before, after):
        return review(before, after, commitment(before))['requests'][0]['changes']

    def test_unchanged_historical_zto(self):
        result = review(DEMO, DEMO, PIN)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['requests'][0]['changes'], [])
        self.assertEqual(result['requests'][0]['beforeDigest'],
                         '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774')

    def test_one_raw_unit_no_rounding_and_no_parent_noise(self):
        other = json.loads((ROOT / 'zto-one-unit-change.json').read_text())
        report = review(DEMO, other, PIN)
        self.assertFalse(report['accepted'])
        item = report['requests'][0]
        self.assertEqual(item['changes'], [{'path': '/message/minimumRaw', 'reason': 'value',
            'before': '166357571280020680094504', 'after': '166357571280020680094505'}])
        self.assertEqual(item['propagatedEncodingPaths'], ['/message'])
        self.assertEqual(item['encodingDifferenceCount'], 2)

    def test_account_is_separate_from_digest(self):
        self.changed['requests'][0]['request']['params'][0] = '0xd782bdea4ef02a0bd391eb9089470c8080f0a68e'
        result = review(DEMO, self.changed, PIN)
        self.assertFalse(result['accepted'])
        self.assertTrue(result['requests'][0]['digestMatches'])
        self.assertEqual(result['requests'][0]['changes'][0]['reason'], 'public_account')

    def test_format_case_numeric_equivalence(self):
        req = self.changed['requests'][0]['request']
        req.update(jsonrpc='2.0', id='transport-only')
        req['params'][0] = '0x' + req['params'][0][2:].upper()
        alter(self.changed, lambda d: d['message'].update(minimumRaw=hex(int(d['message']['minimumRaw']))))
        self.assertTrue(review(DEMO, self.changed, PIN)['accepted'])

    def test_domain_chain(self):
        alter(self.changed, lambda d: d['domain'].update(chainId=8453))
        self.assertIn({'path': '/domain/chainId', 'reason': 'value', 'before': '1', 'after': '8453'},
                      self.changes(DEMO, self.changed))

    def test_field_order_change_despite_same_values(self):
        alter(self.changed, lambda d: d['types']['PaymentEvidence'].reverse())
        changes = self.changes(DEMO, self.changed)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['reason'], 'struct_schema')
        self.assertNotEqual(changes[0]['before'], changes[0]['after'])

    def test_primary_type_rename(self):
        def rename(d):
            d['types']['Renamed'] = d['types'].pop(d['primaryType'])
            d['primaryType'] = 'Renamed'
        alter(self.changed, rename)
        self.assertIn('primary_type', [c['reason'] for c in self.changes(DEMO, self.changed)])

    def test_integer_type_change_equal_word(self):
        alter(self.changed, lambda d: d['types']['PaymentEvidence'][4].update(type='uint128'))
        changes = self.changes(DEMO, self.changed)
        self.assertIn({'path': '/message/confirmations', 'reason': 'declared_type',
                       'before': 'uint256', 'after': 'uint128'}, changes)

    def test_array_growth_and_exact_element_paths(self):
        before = request_data(fields_data([{'name': 'items', 'type': 'uint256[]'}], {'items': [7]}))
        after = copy.deepcopy(before)
        alter(after, lambda d: d['message']['items'].append(8))
        changes = self.changes(before, after)
        self.assertIn({'path': '/message/items', 'reason': 'array_length', 'before': 1, 'after': 2}, changes)
        self.assertTrue(any(c['path'] == '/message/items/1' and c['reason'] == 'node_added' for c in changes))

    def test_nested_array_element(self):
        before = request_data(fields_data([{'name': 'items', 'type': 'uint256[][]'}], {'items': [[7]]}))
        after = copy.deepcopy(before)
        alter(after, lambda d: d['message']['items'][0].__setitem__(0, 8))
        changes = self.changes(before, after)
        self.assertEqual(changes, [{'path': '/message/items/0/0', 'reason': 'value', 'before': '7', 'after': '8'}])

    def test_empty_array_dependency_change(self):
        before = request_data(fields_data([{'name': 'items', 'type': 'Child[]'}], {'items': []},
                              {'Child': [{'name': 'amount', 'type': 'uint256'}]}))
        after = copy.deepcopy(before)
        alter(after, lambda d: d['types']['Child'][0].update(type='uint128'))
        changes = self.changes(before, after)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['reason'], 'struct_schema')
        self.assertIn('Child(uint128 amount)', changes[0]['after'])

    def test_unicode_control_characters_escaped_and_exact(self):
        before = request_data(fields_data([{'name': 'body', 'type': 'string'}], {'body': 'cafe\u0301'}))
        after = copy.deepcopy(before)
        alter(after, lambda d: d['message'].update(body='caf\u00e9\x1b[31m\n'))
        report = review(before, after, commitment(before))
        text = render(report)
        self.assertNotIn('\x1b', text)
        self.assertNotIn('\u00e9', text)
        self.assertEqual(report['requests'][0]['changes'][0]['after'], 'caf\u00e9\x1b[31m\n')

    def test_signed_fixed_bytes_dynamic_bytes_and_bool(self):
        data = fields_data([{'name': n, 'type': t} for n,t in
                           [('signed', 'int8'), ('fixed', 'bytes2'), ('dynamic', 'bytes'), ('flag', 'bool')]],
                          {'signed': -1, 'fixed': '0x1234', 'dynamic': '0x00ff', 'flag': False})
        before = request_data(data); after = copy.deepcopy(before)
        alter(after, lambda d: d['message'].update(signed=-128, fixed='0xabcd', dynamic='0xff00', flag=True))
        by_path = {c['path']: c for c in self.changes(before, after)}
        self.assertEqual(by_path['/message/signed']['after'], '-128')
        self.assertEqual(by_path['/message/fixed']['after'], '0xabcd')
        self.assertEqual(by_path['/message/dynamic']['after'], '0xff00')
        self.assertIs(by_path['/message/flag']['after'], True)

    def test_removed_and_added_fields(self):
        def rename(d):
            d['types']['PaymentEvidence'][3]['name'] = 'amount'
            d['message']['amount'] = d['message'].pop('minimumRaw')
        alter(self.changed, rename)
        reasons = {c['reason'] for c in self.changes(DEMO, self.changed)}
        self.assertTrue({'node_removed', 'node_added', 'struct_schema'} <= reasons)

    def test_membership_and_order(self):
        empty = review(DEMO, {'requests': []}, PIN)
        self.assertEqual(empty['missing'], ['zto-receipt-review'])
        self.assertFalse(empty['accepted'])
        extra = copy.deepcopy(DEMO['requests'][0]); extra['reviewId'] = 'second'
        pair = {'requests': [DEMO['requests'][0], extra]}
        flipped = {'requests': list(reversed(pair['requests']))}
        report = review(pair, flipped, commitment(pair))
        self.assertTrue(report['membershipMatches'])
        self.assertFalse(report['orderMatches'])
        self.assertFalse(report['accepted'])
        self.assertEqual(review(DEMO, pair, PIN)['added'], ['second'])

    def test_bad_added_entry_is_input_error(self):
        extra = copy.deepcopy(DEMO['requests'][0]); extra['reviewId'] = 'second'
        extra['request']['method'] = 'unsupported'
        with self.assertRaises(TypedDataError):
            review(DEMO, {'requests': [*DEMO['requests'], extra]}, PIN)

    def test_unused_types_ignored_but_validated(self):
        alter(self.changed, lambda d: d['types'].update(Unused=[]))
        self.assertTrue(review(DEMO, self.changed, PIN)['accepted'])
        alter(self.changed, lambda d: d['types'].update(Unused=[{'name': 'x', 'type': 'uint7'}]))
        with self.assertRaises(TypedDataError):
            review(DEMO, self.changed, PIN)

    def test_pin_mismatch_before_candidate_read(self):
        with patch('review_changes.load_workspace_json', return_value=DEMO) as read:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['prior', 'never-open', '--expect', 'f'*64]), 1)
            read.assert_called_once_with('prior')

    def test_substituting_both_inputs(self):
        alter(self.changed, lambda d: d['domain'].update(chainId=8453))
        result = review(self.changed, self.changed, PIN)
        self.assertFalse(result['pinMatches'])
        self.assertNotIn('requests', result)

    def test_bounds_fail_closed_without_truncation(self):
        with patch('review_changes.MAX_REPORT_BYTES', 10), self.assertRaises(TypedDataError):
            review(DEMO, DEMO, PIN)
        with patch('request_set_check.MAX_REPORT_BYTES', 10), self.assertRaises(TypedDataError):
            review(DEMO, DEMO, PIN)

    def test_encoding_bytes_fallback(self):
        # Simulate a disagreement invisible to local display; it must be retained.
        node = {'type': 'Thing[]', 'kind': 'array', 'preimage': '0x' + 'aa'*32, 'word': '0x01'}
        changed = dict(node, preimage='0x' + 'bb'*32, word='0x02')
        item = {'reviewId': 'x', 'accepted': False, 'digestMatches': False,
                'encodingMatches': False, 'accountMatches': True, 'differenceCount': 1,
                'intended': {'digest': 'a'}, 'client': {'digest': 'b'},
                'differences': [{'path': '/message/items', 'intended': node, 'client': changed}]}
        self.assertEqual(explain_item(item)['changes'][0]['reason'], 'encoding_bytes')

    def test_dynamic_preimage_change_with_simulated_equal_words(self):
        node = {'type': 'string', 'kind': 'dynamic', 'preimage': '0x61', 'word': 'same'}
        self.assertNotEqual(display(node), display(dict(node, preimage='0x62')))

    def test_cli_exits_and_immutable(self):
        original = copy.deepcopy(DEMO)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            args = [str(ROOT/'zto-set.json'), str(ROOT/'zto-set.json'), '--expect', PIN]
            self.assertEqual(main(args), 0)
            args[1] = str(ROOT/'zto-one-unit-change.json')
            self.assertEqual(main(args), 1)
            args[-1] = 'bad'
            self.assertEqual(main(args), 2)
        self.assertEqual(DEMO, original)

    def test_strict_file_errors_and_symlink(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            folder = Path(folder)
            malformed = folder/'bad.json'; malformed.write_text('{"requests":[],"requests":[]}')
            link = folder/'linked.json'; link.symlink_to((ROOT/'zto-set.json').resolve())
            oversized = folder/'large.json'; oversized.write_text(' '*65537)
            for candidate in (str(malformed), str(link), str(oversized), '../outside', '.hidden'):
                with self.subTest(candidate=candidate), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main([str(ROOT/'zto-set.json'), candidate, '--expect', PIN]), 2)


if __name__ == '__main__':
    unittest.main()
