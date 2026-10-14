# Batched, hash-pinned ZTO snapshot

This Python standard-library piece captures two public Ethereum `eth_call`
responses in **one JSON-RPC batch**. It first reads Ethereum mainnet's finalized
block, pins ZTO `totalSupply()` and `decimals()` to that block hash with
`requireCanonical: true`, then rechecks the block at its height. Batch replies
may arrive in either order: the offline verifier matches each result to its
request ID and refuses missing or duplicate IDs. The JSON file keeps the three
surrounding read responses, both batch replies, the exact batch requests, content type,
source URL, capture time and SHA-256 checksums. It never uses an account, wallet,
key or transaction.

One command from the repository root shows the included real-chain transcript
working **offline**:

```sh
python3 -B line-1/tools/batched-zto-snapshot/batch.py --verify line-1/tools/batched-zto-snapshot/live-batch.json
```

I ran capture against `https://ethereum-rpc.publicnode.com` on 2026-10-14 UTC.
The provider reported finalized block **26193534** with hash
`0x878e40bbef5d78d9822b3b7c45a6fcbcae25e410038148462e6429591452c6df`.
The two batch replies reported ZTO supply
`1000000000000000000000000000` raw units and 18 decimals. The saved transcript
is 73,125 bytes; offline verification exited 0. A local check also accepted
the same replies in reversed order and rejected four resealed changes: duplicate
ID, changed block pin, out-of-range decimals and changed recheck hash.

To capture a fresh public observation into a **new** visible workspace file:

```sh
python3 -B line-1/tools/batched-zto-snapshot/batch.py --capture test/scratch/zto-batch.json
```

Capture needs network access; verification uses only ordinary files in this
repository. The output file is created without replacing any existing file.
The implementation reuses Line 1's strict JSON parser, bounded public-read
transport and safe-file boundary. It sets its own User-Agent, refuses redirects,
disables environment proxy lookup and caps the saved transcript at 100,000 bytes.

This is a record of one provider's answers, not a cryptographic state proof.
The two state calls are sent in one batch but are not guaranteed to execute
atomically. Checksums detect accidental or partial changes, but a forged and
consistently resealed transcript can pass offline verification. The final block
read does not guarantee that a later reorganization cannot happen.
