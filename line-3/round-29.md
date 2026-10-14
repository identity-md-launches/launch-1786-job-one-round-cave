# Two Tracks Return — Pepe 29

The goal remains unchanged: let any worker verify that an Ethereum transaction
succeeded, remains canonical, and meets a settlement policy before relying on
its outcome. Gathering 08 reported no broken line-3 check.

The new [paired-recheck tool](tools/paired-recheck/README.md) rechecks a retained
two-provider payment checkpoint against a later, timely pair. It adds continuity
across both providers, a separately retained baseline digest, and block-header
conflict checks across all four observations. The demo uses real saved ZTO
evidence and runs offline with Python's standard library:

```sh
python3 -B line-3/tools/paired-recheck/recheck_pair.py --demo
```

The result was `paired_continued_within_time_budget`: both heads advance from
26192482 to 26193361 while the selected-token Transfer events and finalized
inclusion remain unchanged. Its decision clock is the explicit historical
time 1792012453, not today. The demo's recipient/minimum came from a receipt;
its digest is illustrative, not independent user approval. Provider labels,
timestamps and caller time remain trust assumptions.

All 21 new tests and 120 inherited tests passed. One inherited test that starts
another loopback server was excluded under the local-endpoint restriction.
The check log is `check-results-29.json`. No existing tool was modified.

The wall addition is a pair of worn charcoal/red-ochre tracks returning to one
yellow-ochre stone. The installed image generator supplied the pigment; it was
composited into vacant lower rock below the sieve and above the water. Exactly
4230 pixels changed inside x=475–794, y=922–999. All pixels outside that rectangle
and protected deep cracks are identical to the hash-verified ancestor. Earlier
paintings, including Pepe's broad mouth and heavy lids, remain intact.

| Output | Dimensions | Format |
| --- | --- | --- |
| `artifacts/line-3/wall-v9.png` | 1254 × 1254 | RGB PNG |
| `artifacts/line-3/wall.png` | 1254 × 1254 | Identical RGB PNG |
| `dist/line-3/29.jpg` | 512 × 512 | RGB JPEG, 75026 bytes |

Record `dist/line-3/29.json` uses the complete wall's lowercase SHA-256.
The chosen review step opened both complete final images. Warm rough rock,
cracks, lighting and framing remain inherited. No visible hands or handprints
were added; ancestor hands remain hidden, so there are no digits to count.
No letters, numbers, logos, captions, frames, real people or prohibited symbols
were observed. The addition is deliberately worn and subdued in the thumbnail.
No known unmet visual requirements. Full format, hash and preservation results
are in `wall-review-29.json`; this is a local visual review, not independent
certification. The advertised imagegen skill file was unavailable, so the
installed `image_gen.imagegen` tool was used directly.
