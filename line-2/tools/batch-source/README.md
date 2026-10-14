# Batch JSON source locator

Check up to 256 JSON handoffs against one explicit offline contract and locate
every supported violation in both the original document and the contract.
Each input is read through the inherited bounded, no-follow reader exactly
once. The batch keeps exact UTF-8 byte offsets, source line and column, and a
SHA-256 for each captured file. The contract is prepared once and documents run
in the order given.

From the repository root, this one command checks two actual inherited records:

```sh
python3 -B line-2/tools/batch-source/locate.py line-2/tools/ordered-deliverables/record.strict.contract.json dist/line-2/27.json dist/line-2/28.json
```

Tried locally: exit 0, two passed, zero failed or unreadable. Each document
hash and the shared contract hash matched the original bytes. The mixed-input
tests also found `/extra` at the `additionalProperties` rule and `/name` at the
string type rule, with byte ranges slicing the exact source tokens. A malformed
first document was reported as unreadable while the later valid document still
passed. An invalid contract and a symlinked input failed closed.

Run the local regression suite with:

```sh
python3 -B line-2/tools/batch-source/test_locate.py
```

The tool reuses the unchanged `source-locator/`, `rule-locator/`,
`bounded-contract/` and `json-contract/` sources; keep those folders beside it.
Python 3.10+ and the standard library are sufficient on POSIX systems with
no-follow file and directory opens. It reads only explicitly named relative
workspace paths, rejects symlinks, caps each source at 1 MB, and never writes,
uses a network, or reads the environment. Exit 0 means every document is
structurally valid; 1 means one or more contain violations; 2 means an input
could not be read or parsed, a contract is invalid, or the batch exceeds its
limit.

This checks the line's supported contract language, not full JSON Schema. It
does not infer repairs, prove that values are true, or authenticate a file from
its hash. Existing regex and uniqueness work can consume substantial CPU, and
the number of emitted violations depends on the inputs; the document-count and
per-file byte limits are not a full CPU or memory sandbox. No coin, price,
payment, balance or pool is required.
