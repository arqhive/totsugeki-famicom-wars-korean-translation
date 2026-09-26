"""일본어 폰트의 모든 칸을 잘라 work/shapes.pkl 로 저장한다(원문 판독용, 게임 데이터라 커밋하지 않음).

칸: 22x22 격자, 시트당 11x11=121칸, 칸 번호 k = 시트*121 + 행*11 + 열, 글자번호 0xB000 | 시트<<8 | (0x40 + 칸).
칸의 밝기(흰 채움)만 남겨 md5 로 모양을 식별한다. 같은 모양은 여러 폰트에 나타난다.
영문 포함 폰트(미션·메뉴)는 칸 0~95 가 ASCII 0x20+k 이다(칸 95 는 폭 6px 좁은 공백).
loading_screen·AttractMode 는 일본판에서 쓰지 않아 제외한다.
사용: python tools/collect_shapes.py
"""
import glob
import hashlib
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tex
import paths

SKIP = {'loading_screen', 'AttractMode'}


def _sheets(path):
    """btf 의 시트마다 (팔레트 번호 배열, 팔레트별 밝기) — P4·P8 모두"""
    d = open(path, 'rb').read()
    out = []
    for _, c in tex.iter_chunks(d):
        w, h = int.from_bytes(c[0x18:0x1C], 'little'), int.from_bytes(c[0x1C:0x20], 'little')
        pl = c.find(b' LAP', 0x58); pm = c.find(b' PIM', 0x58)
        psz = int.from_bytes(c[pl + 4:pl + 8], 'little')
        pal = tex.rgb5a3(np.frombuffer(c[pl + 8:pl + 8 + psz], '>u2'))
        raw = c[pm + 8:pm + 8 + int.from_bytes(c[pm + 4:pm + 8], 'little')]
        n = len(pal)
        dec = tex.dec_c4 if c[0x28:0x2A] == b'P4' else tex.dec_c8
        idx = dec(raw, w, h, np.arange(n))
        q = [tuple(int(x) for x in v) for v in pal]
        lum = np.array([(r * .3 + g * .59 + b * .11) * a / 255 for r, g, b, a in q] + [0] * (256 - n), np.float32)
        out.append((idx, lum))
    return out


def collect():
    src = paths.ensure_jp()
    shapes, cells, known = {}, {}, {}
    for p in sorted(glob.glob(str(src / 'font' / '*.wdf'))):
        name = os.path.basename(p)[:-4]
        w = open(p, 'rb').read()
        if name in SKIP or not w:
            continue
        sheets = _sheets(p[:-4] + '.btf')
        ascii_font = len(w) > 600
        for k in range(min(len(w), len(sheets) * 121)):
            s, c = divmod(k, 121)
            idx, lum = sheets[s]
            r, col = divmod(c, 11)
            cell = lum[idx[r * 22:r * 22 + 22, col * 22:col * 22 + 22]]
            h = hashlib.md5(cell.tobytes()).hexdigest()
            shapes.setdefault(h, []).append((name, k))
            cells[h] = cell
            if ascii_font and k < 96:
                known[h] = ' ' if k == 95 else chr(0x20 + k)
    paths.WORK.mkdir(exist_ok=True)
    pickle.dump((shapes, cells, known), open(paths.WORK / 'shapes.pkl', 'wb'))
    return shapes, cells, known


if __name__ == '__main__':
    s, c, k = collect()
    print('고유 모양', len(s), 'ASCII 확정', len(k))
