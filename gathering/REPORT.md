# Water gathering 09 — Two Remembered Branches

I inspected the tools before running their offline checks, examples and newest
regression suites. All 87 final runner commands pass, with **592 test cases passed and one
explicitly skipped** (593 enumerated), including every line's
current piece and the shared integrations. Separate expected-rejection and
portable-copy trials are in `round-checks-09.json`; detailed per-line output is
in `check-09-*.json`. These are local observations, not independent certification.
The extra loopback redirect test is explicitly skipped: this assignment permits
only its supplied local RPC address. The other memory-backed boundary checks run.
No line folder or line record was changed.

## Line 1 — portable Ethereum observations

**Tried:** bounded snapshots; anchored and hash-pinned ZTO replay; safe file
checks; comparison, report and revisit commands; the new two-call batch replay;
and a fresh real ZTO batch capture followed by offline verification.

**Works:** the batch correlates replies by integer request ID and retains the
requests, raw successful responses, checksums and rechecked finalized anchor.
The fresh read observed block **26193694**, hash
`0xaff1586e4e34239be25d580492d8355c4d8faadaf4a8168636cf8653b71570f8`,
supply **1000000000000000000000000000** raw ZTO and **18** decimals.
`live-batch-09.json` is a 55,741-byte portable transcript; its public source is
https://ethereum-rpc.publicnode.com. `live-batch-trial-09.json` records the result.

**Broken:** no exercised command failed. Limits remain: a batch is not an atomic
read or state proof, provider responses are trusted, and consistent resealing
can pass. An archive provider can refuse old state. This observation does not
establish present balances, price, consensus or future canonicality.

**Goal fit:** useful to unfamiliar workers, not cave-specific and distinct from
Line 3's settlement decision. The bounded portable-capture goal already works.
Keep the remaining scope to small reproducible public-read bundles; a general
Ethereum proof service would exceed 21 contributions.

## Line 2 — structural JSON contracts

**Tried:** base, ordered, batch and bounded validators; repair review; rule and
source locators; contract-change review; and the newest batch-source command
and five tests. The new command checks actual records 27 and 28 in order.
A separate proposed ZTO policy requiring 13 confirmations correctly rejects the
saved policy with 12, exiting 1 as expected.

**Works:** batch-source prepares one explicit contract, captures each document
once and locates supported violations in exact original UTF-8 document and rule
bytes. Its tests cover exact source ranges and hashes, mixed malformed/valid
inputs, invalid rules and symlink refusal. Later files still receive diagnostics
when an earlier document is unreadable.

**Broken:** no exercised check failed. The supported language is a deliberate
subset, not full JSON Schema. File/document limits do not fully bound regex CPU,
uniqueness work, memory or report size. Structural acceptance authenticates no
source and proves no business policy or truth.

**Goal fit:** useful for general JSON handoffs, distinct from Line 4's typed-data
encoding checks. Already useful within 21 contributions. Keep explicit rules and
exact diagnostics; do not broaden into inferred repairs or a complete schema
implementation without a separately bounded goal.

## Line 3 — settlement across providers and time

**Tried:** settlement/payment replay, read boundary, discovery diagnostic,
provider agreement, recheck, freshness, paired freshness, and the newest paired
checkpoint recheck demo and its 21 tests. The demo uses real historical ZTO
transaction `0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`.

**Works:** both sampled heads advance **26192482 → 26193361**, with unchanged
inclusion, successful execution and complete selected-token Transfer events.
The pair still reports **166357571280020680094504** raw ZTO for the observed
recipient. The caller supplies one policy, retained checkpoint digest, explicit
historical time **1792012453**, and age budgets. Replaced baselines, changed
events, stale evidence, one-provider failures, finality regression and shared
height conflicts fail closed. Unchanged heads require review rather than being
called progress.

**Broken:** no exercised check failed. The extra real-loopback boundary test was
not run, as explained above. Historical replay is not a current chain check.
Caller clock and provider timestamps remain trusted. Two URL labels do not
establish independent operators; different-height ancestry is not proved.
Receipt-derived recipient/amount are not an independent invoice. There is no
ownership check, deduplication system, accounting ledger or receipt proof.

**Goal fit:** useful beyond this cave and distinct from capture and request
encoding. The bounded settlement-policy goal works. A payment processor is too
large for 21 contributions; retain the narrower observation/recheck scope.

## Line 4 — offline EIP-712 commitments and changes

**Tried:** digest/trace examples, domain/request checks, ordered collections,
retained review pins, and the new change reviewer with 24 tests. Its matching
ZTO collection exits 0. The documented one-unit change exits **1**, correctly
reporting `/message/minimumRaw` as
**166357571280020680094504 → 166357571280020680094505**. Parent hash propagation
is separated from the changed value. Tests that create neighboring fixtures run
from byte-for-byte scratch copies, leaving the line untouched.

**Works:** exact decimal strings preserve large integers; reports explain
account, domain, schema, order, membership and value changes. Invalid prior pins
stop before candidate file access. Matching digest alone cannot hide a changed
public account. No request is dispatched.

**Broken:** no exercised check failed. Pins are unkeyed commitments; replacing
both reviewed content and its independently retained pin can pass. Labels and
capture provenance remain caller assertions. Encoding equality proves no
ownership, consent, safety, payment or contract support. The inherited encoder
has not been independently audited here.

**Goal fit:** general worker utility, not cave-only and not a repeat of Line 2.
The offline digest goal already works. Keep future scope to review and comparison,
without signing, client automation or invented approval decisions.

## Shared deliverable

`shared/payment-evidence/checkpoint_review.py` joins Line 3's new paired recheck
with Line 4's new value-level explanation and the existing exact evidence/request
binding. Both new sources are vendored byte-for-byte with hashes in
`provenance.json`. The older real paired baseline is copied as an ordinary file.

A caller must retain two different commitments independently: the baseline's
canonical JSON SHA-256 and the intended request's encoding review pin. The tool
checks both before opening current evidence/candidate files; rechecks both
providers' progress, payment continuity, time policy and shared-height conflicts across snapshots;
requires the intended request to bind the exact current pair and payment policy;
then compares and explains the captured candidate. It updates no pin or policy.
The complete combined report is limited to 100 KB.

The historical demo exits 0 with `checkpoint_and_pinned_request_match`.
All **12 new integration tests** pass, including stale observations, unchanged
heads, exact one-unit/account differences, still-settled evidence losing its
binding, substituted baseline, file-opening order, missing input and report
bounds. The entire shared folder runs detached with no line folders, packages,
network or environment access. Commands and limitations are in its README.
The demonstration self-compares intended/client data and its saved pins are
illustrative, not independent approval, a genuine client capture or an invoice.

## Coins, records and wall

`COINS.md` says **none**: these goals and the bridge do not require another coin
or hook. ZTO supplies the actual chain examples, with IMD supported second.
There is no contract to nominate for Sepolia. Nothing was signed, sent, paid,
posted or deployed, and no keys or wallets were accessed.

This is gathering **09**, so first-gathering placeholder creation does not apply.
All future slots remain; only gathering slot 09 becomes painted. Four unchanged
goals populate `dist/goals.json`. The self-contained styled gallery has **45
paintings and 92 placeholders**, grouped by wall with newest painted marks first.

The ancestor is the SHA-256-verified gathering-08 image. The built-in imagegen
tool generated worn charcoal/ochre pigment: a recognizable heavy-lidded,
wide-mouthed Pepe above a forked twig and two pairs of pebbles. It was composited
only onto vacant stone left of the existing crack. All pixels outside x **65–204**,
y **380–579**, plus protected dark-crack pixels inside, remain identical.
**15,858** pixels gained pigment; **1,556,658** remain unchanged. No ancestor
painting was erased, moved or redrawn.

Output: `artifacts/gathering/wall-v9.png` and whole-wall alias `wall.png`,
**1254 × 1254 RGB PNG**, SHA-256
`2daa514aae24125f90df19455e61febb0880af5b01007fd14c8030a83f2a6b1e`.
`dist/gathering/09.jpg` is **512 × 512 JPEG**, **75,884 bytes**; `09.json` has
the requested shape and content-addressed URL. Only the finished wall and its
JPEG are retained as this round's images. Prompt, dimensions, formats, hashes,
preservation and review are recorded in `wall-review-09.json`.

I visually inspected the full PNG and decoded JPEG. Rough warm rock, cracks,
lighting, framing and all older marks remain visible. Pepe has the required wide
mouth and heavy lids. There are no hands or handprints, so no digits require
counting. No letters, numbers, captions, signatures, logos, watermarks, borders,
real people or prohibited symbols were observed. **No known unmet visual
requirements.** Structural verification checks bytes and metadata; it cannot
certify artistic quality or the truth of RPC observations.
