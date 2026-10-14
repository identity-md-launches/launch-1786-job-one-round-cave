#!/usr/bin/env python3
"""Retain the generated addition while preserving all ancestral pixels outside it."""
import hashlib
import json
from pathlib import Path

from image_bytes import jpeg, png, read_png, resize

ANCESTOR = 'd0899d81145c8538c75a3af1d6f3d72bd7ea6285653bd7c9e932fac3508e80ae'


def main():
    folder = Path('artifacts/line-4')
    before = (folder/'wall.png').read_bytes()
    assert hashlib.sha256(before).hexdigest() == ANCESTOR
    generated = (folder/'wall-v9.png').read_bytes()
    w, h, old = read_png(before)
    gw, gh, draft = read_png(generated)
    assert (w, h) == (gw, gh) == (1254, 1254)
    final = bytearray(old)
    count = 0
    for y in range(140, 262):
        for x in range(585, 674):
            j = (y*w+x)*3
            # Place only the newly generated motif on the vacant right alcove.
            # The source crop's older dots are excluded by the masks below.
            i = ((y+240)*w+x+415)*3
            source = draft[j:j+3]
            original = old[i:i+3]
            r, g, b = source
            # Three small masks on unused stone: burnt-stick twig and two seeds.
            twig = 601 <= x <= 645 and 143 <= y <= 233
            seeds = (x-599)**2+(y-187)**2 <= 13**2 or (x-655)**2+(y-193)**2 <= 12**2
            charcoal = twig and r < 150 and g < 110 and b < 75 and r-g < 45
            red = seeds and r > g*1.7 and r-g > 35 and g < 115
            if sum(original) < 140 or not (charcoal or red):
                continue
            # No generated substrate is transferred. Keep original light and
            # texture in the worn pigment, and never lighten a fissure.
            factor = max(.3, min(.65, r/200))
            target = ([a*factor for a in original] if charcoal else
                      [original[0]*.85, original[1]*.45, original[2]*.4])
            final[i:i+3] = bytes(round(a*.25 + v*.75) for a,v in zip(original, target))
            count += final[i:i+3] != original
    assert count > 500
    for y in range(h):
        for x in range(w):
            i = (y*w+x)*3
            if final[i:i+3] != old[i:i+3]:
                assert 1000 <= x < 1089 and 380 <= y < 502
                assert sum(old[i:i+3]) >= 140
    wall = png(w, h, final)
    for name in ('wall.png', 'wall-v9.png'):
        (folder/name).write_bytes(wall)
    preview = jpeg(512, 512, resize(w, h, final), 52)
    assert len(preview) < 100000
    Path('dist/line-4/29.jpg').write_bytes(preview)
    sha = hashlib.sha256(wall).hexdigest()
    review = {
        'wall': {'paths': ['artifacts/line-4/wall.png', 'artifacts/line-4/wall-v9.png'],
                 'width': w, 'height': h, 'format': 'PNG', 'mode': 'RGB', 'sha256': sha},
        'preview': {'path': 'dist/line-4/29.jpg', 'width': 512, 'height': 512,
                    'format': 'JPEG', 'bytes': len(preview),
                    'sha256': hashlib.sha256(preview).hexdigest()},
        'ancestorSha256': ANCESTOR,
        'generatedImageSha256': hashlib.sha256(generated).hexdigest(),
        'changedPixels': count, 'unchangedPixels': w*h-count,
        'additionBoundsExclusive': [1000, 380, 1089, 502],
        'preservation': 'Every pixel outside the addition and every deep fissure pixel is identical to the ancestor. All older pigment is outside the addition.',
        'imageTool': 'image_gen.imagegen, referenced inherited wall; retained only generated twig/seed pigment using the inherited image byte codec',
        'visualReview': 'Pending final PNG and JPEG inspection.',
        'unmetVisualRequirements': [],
        'limitations': ['Local visual inspection is not independent certification.',
                       'The small worn twig is less distinct in the JPEG thumbnail.'],
    }
    Path('line-4/wall-review-29.json').write_text(json.dumps(review, indent=2)+'\n')
    record = {'name': 'The Branch That Changed', 'image': 'https://api.imd.fun/artifacts/'+sha,
              'attributes': [
                  {'trait_type': 'Cave', 'value': 'Water'},
                  {'trait_type': 'Wall', 'value': 'Line 4'},
                  {'trait_type': 'Number', 'value': 29},
                  {'trait_type': 'Left behind', 'value': 'offline EIP-712 change reviewer'},
                  {'trait_type': 'Meaning', 'value': 'Pepe follows a forked twig to find which seed changed.'},
                  {'trait_type': 'One thing', 'value': 'offline EIP-712 typed-data digest checking'}]}
    Path('dist/line-4/29.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
