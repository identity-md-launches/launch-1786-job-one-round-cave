# Offline EIP-712 change reviewer

Explain exactly what changed between a previously pinned review and a candidate
collection of captured `eth_signTypedData_v4` requests. Outputs exact normalized
values, public-account changes, field/type changes, array lengths, membership
and order. Containing hashes that changed because a child changed are listed
separately, so a one-unit amount change does not become a page of hash words.
Python standard library only; copy this entire folder to use it offline.

One command from the repository root:

```sh
python3 -B line-4/tools/review-changes/review_changes.py line-4/tools/review-changes/zto-set.json line-4/tools/review-changes/zto-one-unit-change.json --expect c1f7a3ff0b7cf878d16be782f567b2bf89f88e9b962ed64210eeaeb2cf6d7023
```

Tried: exit **1** (the intended rejection), `pinMatches: true`, `accepted: false`.
It reports `/message/minimumRaw` changing from **166357571280020680094504** to
**166357571280020680094505** and lists `/message` as a propagated encoding change.
The first digest is
`0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774`;
the changed digest is
`0x79447ddb9c4bb1eafebf3333948dda1358cbf12db05f411e98f64b2ea1d64621`.
Replace the second filename with `line-4/tools/review-changes/zto-set.json` to
see exit **0**, no changes and `accepted: true`. Saved outputs are
`example-change.json` and `example-match.json`.

The source is the ancestor's historical evidence for real Ethereum ZTO,
`0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`. The second fixture deliberately
changes one raw unit to demonstrate rejection; it is not another chain
observation. The public account is the historical recipient, with no ownership
claim. The demo's saved pin and self-comparison illustrate execution, not
independent approval, a genuine client capture or a current payment.

For real use, independently review the intended collection first and retain its
pin separately using the included ancestor `review_pin.py pin <intended.json>`.
Pass that previously retained value as `--expect`. Do not generate a replacement
pin from incoming data and call it prior review. A pin mismatch stops before
the candidate file is opened. This command never emits a newly approved pin,
modifies an input, dispatches a request, signs, or accesses a wallet, key,
environment variable or network.

Inputs use the ancestor collection format:

```text
{"requests": [{"reviewId": "your-label", "request": {
  "method": "eth_signTypedData_v4",
  "params": [public-account-address, typed-data-as-a-JSON-string]
}}]}
```

`public-account-address` and `typed-data-as-a-JSON-string` above describe required
values, not executable example JSON. Complete JSON-RPC 2.0 envelopes are also
accepted. Labels must be unique ASCII identifiers; 1–16 intended and 0–16
candidate requests are allowed. Labels and order are caller assertions.

Exit **0** means unchanged under the inherited comparison rules. Exit **1**
means the prior pin, membership, order, public account or encoding differs.
Exit **2** means invalid/unsafe input or a bound was exceeded; no partial review
is emitted. `accepted` never means a proposed change is safe or approved.

Each matching review label has a `requests` entry with:

- `changes`: exact before/after values at typed-data JSON Pointer paths, with
  `/params/0` reserved for the separate public account. Integers are decimal
  strings, bytes are hex, addresses are lowercase, and booleans are JSON booleans.
  Dynamic strings preserve their exact Unicode scalar sequence; CLI output
  escapes non-ASCII and control characters for terminals.
- `struct_schema`: the complete EIP-712 type encoding, including reachable
  dependencies. This catches changed types behind empty arrays and field order
  changes even when values are unchanged.
- `propagatedEncodingPaths`: parent nodes whose encoding differences are explained
  by differing descendants. `encodingDifferenceCount` counts the full ancestor
  differences before this reduction, not the number of local change entries.
- Both digests and independent account/encoding match flags. If a differing
  node has no local display change or differing descendant, `encoding_bytes`
  retains its full raw encoding difference. The reduced display never decides
  acceptance; the complete inherited comparator does.

Missing/added review labels are reported at collection level. Their requests are
validated but have no paired value diff. Array positions are compared by index;
inserting at the start can report shifted elements. The tool does not infer a
move, business meaning, token decimals, monetary value or risk severity. Schema
changes may appear on multiple enclosing structs because each signs its type
dependencies. Raw values can be sensitive: reports are for local review.

Whitespace, JSON key order, transport IDs/wrappers, equivalent integer notation
and address case do not differ. Unreachable valid types are not encoded and do
not differ; invalid declarations still fail. Unknown fields fail. An unkeyed pin
is not a signature: replacing the inputs and the retained pin can pass. Matches
prove no ownership, consent, replay protection, settlement or contract support.
The encoder is an unchanged ancestor implementation, not independent crypto.

Files must be regular no-follow files under cwd, at most 65,536 bytes, strict
UTF-8 JSON without duplicate keys, floats or nonfinite numbers. Hidden paths,
parent traversal and symlinks are rejected. POSIX directory descriptors are
required. Inherited bounds include depth 48, 8,192 input nodes, 64 types, 256
fields, eight array dimensions and 1 MiB pin/trace/comparison limits. Final
ASCII JSON output, including its trailing newline, is limited to 1 MiB; excess
fails closed without truncation. These are size limits, not a CPU-time guarantee.

```sh
python3 -B -m unittest discover -s line-4/tools/review-changes -v
```

Tried: **24 tests pass**, covering exact large integers, account-only changes,
domain/type/order changes, empty-array dependencies, nested arrays, added/removed
fields, Unicode/control characters, signed integers, bytes, booleans, retained
pin substitution, unsafe files, report bounds and CLI exits. The inherited
review-pin suite and a detached copy of this folder also pass offline.

`provenance.json` records exact unchanged source-copy hashes. Encoding rules:
[EIP-712 specification](https://eips.ethereum.org/EIPS/eip-712). The wall's forked
twig represents following a changed hash back to the value that caused it.
