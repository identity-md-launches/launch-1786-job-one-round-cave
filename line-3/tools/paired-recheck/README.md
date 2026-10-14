# Paired settlement recheck

Recheck an accepted two-provider Ethereum payment against a later, timely pair
without silently changing the payment policy or the retained checkpoint. ZTO is
the default demonstrated token; the inherited payment verifier also supports IMD.
Python 3.9+ with the standard library and POSIX safe file opens is sufficient.

Run from the repository root, offline:

```sh
python3 -B line-3/tools/paired-recheck/recheck_pair.py --demo
```

The command returned `paired_continued_within_time_budget`, exit 0. It compares
actual saved Publicnode/dRPC observations of ZTO transaction
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`.
Both sampled heads advance from **26192482** to **26193361**. The inclusion,
successful execution and complete selected-token Transfer events remain equal,
including **166357571280020680094504** raw ZTO received by
`0x2d30e495a15f2657d57c3e2caa08b06415c26cbf`.

The later pair is evaluated at historical Unix time **1792012453**, with head
age at most 120 seconds, finalized-head age at most 1200 seconds, and future
skew at most 60 seconds. This is historical replay, not current freshness.
The recipient and minimum were observed in a receipt, not supplied by an
independent invoice. The demo pin is illustrative, computed from the inherited
checkpoint; it is not evidence of independent approval.

## What is checked

1. Validate the separately supplied expected policy and explicit clock/budgets.
2. Match the baseline to a separately retained lowercase SHA-256 digest before
   replaying it or opening current evidence. Recompute both baseline payments;
   both must pass and agree. A saved `accepted` flag is never trusted.
3. Recompute both current observations using paired-freshness. Both must pass
   payment, finality and time checks and agree with each other.
4. Compare each provider with its own baseline. Each head must advance; finality
   cannot regress; receipt inclusion, execution and all selected-token events
   must stay unchanged. Unchanged net amount alone is insufficient.
5. Reject conflicting block hashes at any height shared across all four
   transcripts, including an old latest head that becomes a new finalized head.
   Compare timestamps wherever present on both observations at a shared height.

Older accepted checkpoints without timestamps are supported. They establish
prior settlement facts, **not prior wall-clock freshness**. Current observations
must contain timestamps. Different heights are allowed and no parent-chain
walk is performed. Equal current heads are not progress, even while still fresh.

## Your own checkpoint

Review the expected payment policy independently. Retain a checkpoint digest
when you accept the original evidence, separately from later submitted evidence.
The digest is SHA-256 over parsed JSON encoded with Python's
`json.dumps(sample, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
allow_nan=False).encode()`, as implemented by `payment-recheck.r.digest`.
It is a canonical JSON digest, **not the hash of the formatted file bytes**.
Whitespace and object-key order do not matter; array order and values do.
Replacing both the evidence and its retained digest can still pass.

This fully specified command reproduces the historical demonstration with
explicit inputs:

```sh
python3 -B line-3/tools/paired-recheck/recheck_pair.py --baseline line-3/tools/provider-agreement/paired-evidence.json --baseline-sha256 dd94a4fb3ef241db9cffbf8ccb24b4486e0eea308b1c34a7e0668f6c92f90dd4 --current line-3/tools/paired-freshness/paired-evidence.json --policy line-3/tools/paired-freshness/observed-policy.json --as-of 1792012453 --max-head-age 120 --max-finalized-age 1200 --future-skew 60
```

For a new live recheck, replace `--current PATH` with `--live`, supply your actual
trusted decision time, and review all policy and age limits. Both documented
public endpoints are mandatory: https://ethereum-rpc.publicnode.com and
https://eth.drpc.org. Collection is sequential and read-only, with an explicit
User-Agent, no redirects and no proxy/environment discovery. A slow collection
may fail its time budget; there is no polling or single-provider fallback.
The library accepts an explicit `rpc_factory` for a caller's approved routing.

CLI reads visible, workspace-relative regular JSON files, at most 90 KB each.
The inherited reader refuses symlinks, parent/hidden paths, duplicate keys and
nonfinite JSON. Exact envelope keys, request types and complete transcript
consumption are required. JSON output is limited to 100 KB. CLI writes no files.
Exit **0** means acceptance, **1** means review required (including no new heads),
and **2** means invalid input or unavailable provider.

## Checks and reuse

```sh
python3 -B -m unittest discover -s line-3/tools/paired-recheck -p 'test_*.py' -v
```

All **21 new tests** passed, plus **120 inherited tests**. Rejections cover a
replaced baseline, invalid pin before reads, malformed requests, changed sender
despite agreement on the new amount, stale observations, one unchanged provider,
missing receipts, regressed finality, cross-snapshot anchor conflicts and failed
second provider. Capture/replay produces the same decision. Mutated observations
exist only inside tests and are never published as chain evidence. One inherited
test that opens another loopback server was excluded under the assignment's
local-endpoint restriction. Results are in `../../check-results-29.json`.

This folder reuses unchanged sibling modules in `paired-freshness`,
`settlement-freshness`, `payment-recheck`, `provider-agreement`, `payment-witness`
and `settlement-check`. Copy those folders too, including the two real paired
transcripts used by the demo. No packages, installation or network are needed
for replay. `trial.json` records the demonstration digest and explicit historical
clock; `demo-result.json` is the actual result, not an input to the decision.

Provider evidence and caller time remain trusted inputs. Two URL labels do not
prove separate operators; forged consistent transcripts can pass. Hash matching
does not authenticate sources, establish consensus, prove receipt inclusion or
prevent later reorganizations. This tool does not establish recipient ownership,
invoice provenance, current balances, deduplication or a payment ledger. Nothing
is signed, sent, paid, posted or deployed; no keys or wallet are accessed.
