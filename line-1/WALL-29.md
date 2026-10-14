# Three Streams, One Bowl

The new piece is `tools/batched-zto-snapshot/`. A worker can capture two public
ZTO state reads in one JSON-RPC batch at the same finalized block hash, retain
the raw request and response envelopes, and verify later offline that replies
were matched to their IDs. The saved observation came from Ethereum Publicnode.
The tool uses only Python's standard library and earlier Line 1 code. No
transaction was sent.

The wall began from record 28's SHA-256-verified painting. The built-in
`image_gen.imagegen` tool edited that image with this prompt:

> Use case: precise-object-edit. Edit target: the supplied square prehistoric cave painting. Add one small new hand-painted mark in the vacant upper central stone at approximately x=650, y=260 on the 1254 x 1254 original: three tiny uneven ochre river lines converge into one open charcoal-and-ochre bowl shape, like several public observations gathered into one portable vessel. Keep the new mark about 90 pixels wide and 75 pixels tall on the original wall, flat mineral pigment, irregular thumb-and-burnt-stick strokes, slightly worn so stone texture shows through. Preserve the exact existing Pepe frog, his heavy-lidded eyes, wide mouth and both five-digit hands; preserve every older painting, the water, rock, cracks, color, torchlight, size and framing. No other additions or changes. No letters, numbers, captions, logos, watermarks, borders or frames; no new hands or handprints; no people or symbols. Earth pigments only: red and yellow ochre, charcoal black, chalk white and bare stone.

The generated draft shifted some older pixels. A bounded, feathered composition
retained only the new pigment at x594–700, y210–334; all other pixels are exact
from the ancestor. The final whole wall is an **1254 × 1254 RGB PNG** at
`artifacts/line-1/wall.png` and `artifacts/line-1/wall-v9.png`, with SHA-256
`af98464f7724f387d3663f26315c634e3d5c0157b488eb45203f8e86d35770df`.
The preview is a **512 × 512 JPEG** at `dist/line-1/29.jpg` (75,792 bytes).

I inspected the final PNG. Pepe remains a frog with heavy-lidded eyes, broad
mouth and five digits on each existing hand: four fingers and one thumb. The
new mark has no hands or handprints. The older paintings, warm rock, cracks,
torchlight, water and framing remain; there are no words, numbers, logos,
watermarks, borders, people or prohibited symbols. **No known unmet visual
requirements.** This is local visual review; the structured dimensions,
pixel bounds and review are in `wall-review-29.json`.
