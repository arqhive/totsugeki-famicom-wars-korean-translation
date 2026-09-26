"""판독표 검수 시트: tools/data 의 묶음(review.json)과 판독 글자를 그림으로 보여 준다 → work/review/NN.png
시트 NN 의 칸 순서가 tools/data/labels/NN.txt 의 글자 순서와 같다. 틀린 글자는 labels 를 고친다.
한 묶음 안에 모양이 다른 글자가 섞였으면 tools/data/fix_shape.json 에 모양(md5)별로 적는다.
  python tools/review_sheets.py            묶음 대표 모양만
  python tools/review_sheets.py 1093 1269  해당 묶음의 구성 모양 전부와 판독 글자
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jpdec
import paths

R = json.load(open(paths.DATA / 'review.json', encoding='utf-8'))
FONT = ImageFont.truetype('C:/Windows/Fonts/YuGothB.ttc', 20)
SMALL = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 11)


def glyph(h, size):
    return Image.fromarray(np.clip(255 - jpdec.cells[h], 0, 255).astype(np.uint8)).resize((size, size), Image.NEAREST)


def sheets():
    out = paths.WORK / 'review'; out.mkdir(parents=True, exist_ok=True)
    COLS, ROWS, CW, CH = 12, 10, 80, 96
    for n, sh in enumerate(range(0, len(R), COLS * ROWS)):
        im = Image.new('RGB', (COLS * CW, ROWS * CH), 'white'); d = ImageDraw.Draw(im)
        for j, r in enumerate(R[sh:sh + COLS * ROWS]):
            x, y = (j % COLS) * CW, (j // COLS) * CH
            im.paste(glyph(r['rep'], 66), (x + 7, y + 2)); d.rectangle([x + 7, y + 2, x + 73, y + 68], outline=(200, 200, 200))
            d.text((x + 2, y + 70), str(sh + j), fill=(150, 0, 0), font=SMALL)
            d.text((x + 40, y + 68), jpdec.fix.get(r['rep'], '?'), fill=(0, 0, 200), font=FONT)
        im.save(out / f'{n:02d}.png')
    print('%s 에 %d장' % (out, n + 1))


def members(ids):
    out = paths.WORK / 'review'; out.mkdir(parents=True, exist_ok=True)
    rows = [(i, m) for i in ids for m in R[i]['members']]
    im = Image.new('RGB', (420, 32 * len(rows) + 4), 'white'); d = ImageDraw.Draw(im)
    for n, (i, m) in enumerate(rows):
        im.paste(glyph(m, 28), (2, 2 + 32 * n))
        d.text((40, 6 + 32 * n), f'묶음 {i}  {m[:8]}  → {jpdec.fix.get(m, "?")}', fill='black', font=SMALL)
    im.save(out / 'members.png')
    print(out / 'members.png')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        members([int(a) for a in sys.argv[1:]])
    else:
        sheets()
