"""로고를 세 조각(돌격!!·패미컴·워즈★)으로 나눈다. 앞 조각 씨앗 사각형 + 알파 거리 분수령."""
import numpy as np
from PIL import Image
from scipy import ndimage as nd

import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
import tex  # noqa: E402

JP = 'JP'                                                  # 일본판 텍스처(게임에서 바로 푼다)
KO = str(paths.ASSETS / 'BWTitleLogoJp.png')               # 한글 타이틀 로고(게임판)
HI = str(paths.ASSETS / 'movie' / 'BWTitleLogo_hires.png')  # 같은 로고 고해상도판(확대 장면용)
MOVIE = paths.WORK / 'movie'
JP_FRAMES = MOVIE / 'jp' / 'output'                        # 원본 무비를 푼 장면(video_rgb_N.ppm)
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

SEEDS = {
    'jp': [(30, 0, 215, 75), (0, 76, 335, 168), (336, 40, 592, 168)],
    'ko': [(30, 0, 215, 75), (0, 76, 310, 168), (311, 30, 592, 168)],
}


def split(img, seeds, scale=1.0, drop_tm=True):
    """img: RGBA ndarray. 반환: 조각별 RGBA 배열 3개(같은 크기, 나머지는 투명)."""
    a = img[..., 3]
    m = a > 8
    if drop_tm:  # ™ 지우기(오른쪽 아래 작은 덩어리)
        lab, n = nd.label(m)
        sizes = nd.sum(np.ones_like(a), lab, range(1, n + 1))
        keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > sizes.max() * 0.02])
        m &= keep
    rgb = img[..., :3].astype(np.int32) * scale_dummy if False else img[..., :3].astype(np.int32)
    core = m & (rgb[..., 0] > 190) & (rgb[..., 1] > 150) & (rgb[..., 2] < 140)
    clab, cn = nd.label(core)
    coms = nd.center_of_mass(core, clab, range(1, cn + 1))
    sizes = nd.sum(core, clab, range(1, cn + 1))
    part_of = np.zeros(cn + 1, np.int16)
    for i, ((cy, cx), sz) in enumerate(zip(coms, sizes)):
        if sz < 3:
            continue
        cy, cx = cy / scale, cx / scale
        for k, (x0, y0, x1, y1) in enumerate(seeds):
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                part_of[i + 1] = k + 1
                break
    lab0 = part_of[clab]
    _, (iy, ix) = nd.distance_transform_edt(lab0 == 0, return_indices=True)
    lab = lab0[iy, ix]
    out = []
    for k in range(len(seeds)):
        p = img.copy()
        sel = (lab == k + 1) & m
        # 경계가 깨지지 않게 1px 넓혀 알파를 살린다
        sel = nd.binary_dilation(sel, iterations=1) & (a > 0) & (m | (a > 0))
        p[..., 3] = np.where(sel, a, 0)
        out.append(p)
    return out


def jp_logo():
    d = open(paths.JP_DATA / 'CompoundFiles' / 'frontend_0_Level.res', 'rb').read()
    name = b'BWTitleLogoJp'
    o = next(m.start() for m in re.finditer(rb'TXET', d) if d[m.start() + 8:m.start() + 9 + len(name)] == name + b'\0')
    return tex.decode_chunk(d[o:o + struct.unpack_from('<I', d, o + 4)[0] + 8])[1]


def load(path):
    if path == JP:
        return np.asarray(jp_logo()).copy()
    return np.asarray(Image.open(path).convert('RGBA')).copy()


if __name__ == '__main__':
    for name, path in (('jp', JP), ('ko', KO)):
        img = load(path)
        ps = split(img, SEEDS[name])
        cols = [(255, 80, 80), (80, 255, 80), (80, 120, 255)]
        vis = np.zeros(img.shape[:2] + (3,), np.uint8)
        for p, c in zip(ps, cols):
            vis[p[..., 3] > 8] = c
        Image.fromarray(vis).resize((1184, 336), Image.NEAREST).save(f'split_{name}.png')
