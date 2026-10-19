"""한글 엔딩 로고 무비(Data/Video/4_3_TheEnd_JP.h4m) 만들기.
원본 마지막 컷씬 끝에 일본어 로고가 나오는 구간(2171~2307장)만 한글 로고로 바꾼다.
1) 원본 무비를 HVQM4 디코더로 work/movie/end_jp/output 에 푼다(처음 한 번).
2) 로고 구간이 든 묶음(GOP) 73~77번(2163~2312장, 30장씩)을 I 프레임으로 새로 만들고,
   나머지 묶음은 원본 바이트를 그대로 둔다.
   - 2171~2294장: 나타나기(배율 1.22→1, 밝기 0→1) — 원본 장면에서 잰 값(data/ending_track.json)
   - 2295~2307장: 노란 면 흰색화 → 흰 실루엣 섞기 → 가로 흐림·빛 번짐(값은 눈으로 맞춤)
   - 2308장~: 흰 띠(글자 없음) — 원본 장면 그대로
3) work/movie/out/Data/Video/4_3_TheEnd_JP.h4m 에 쓴다.
사용: python tools/movie/make_ending.py
"""
import json
import os
import struct
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import h4m  # noqa: E402
import parts  # noqa: E402
import paths  # noqa: E402

NAME = '4_3_TheEnd_JP.h4m'
OUT = parts.MOVIE / 'out' / 'Data' / 'Video' / NAME
FRAMES_DIR = parts.MOVIE / 'end_jp' / 'output'
DECODER = paths.WORK / 'bin' / 'h4m_dec.exe'
TOTAL = 2452
FIRST_BLK, LAST_BLK = 73, 77            # 다시 만드는 묶음(2163~2312장)
BG = 16.0                               # 원본 검은 바탕 밝기
# 정지 장면(2260장)에 맞춘 텍스처 배치: 배율·로고 중심(텍스처 ™ 뺀 bbox 를 화면 bbox (67,163)-(574,306) 에 맞춤)
SCALE, CX, CY = 0.85927, 322.2185, 234.9296
C0 = (320.5, 234.5)                     # 나타나기 확대 기준점(화면 bbox 가운데)
# 2295~2307장 흰색 전환: 노란 면 흰색화 W, 흰 실루엣 M, 가로·세로 흐림 SG·SV, 빛 번짐 B
W = [.2, .4, .6, .8, 1, 1, 1, 1, 1, 1, 1, 1, 1]
M = [0, 0, 0, 0, .1, .15, .2, .3, .35, .4, .45, .5, .55]
SG = [0, 0, 0, 0, 1, 1.5, 2.5, 4, 6, 8, 12, 16, 22]
SV = [0, 0, 0, 0, 0, 0, 0, 1, 1, 1.5, 2, 2.5, 3]
B = [0, 0, 0, 0, 0, 0, 0, .03, .05, .08, .12, .18, .25]


def decode_original():
    if (FRAMES_DIR / f'video_rgb_{TOTAL - 1}.ppm').exists():
        return
    if not DECODER.exists():
        sys.exit('HVQM4 디코더가 없습니다: %s (Tilka/hvqm4 를 -DNATIVE=1 로 컴파일)' % DECODER)
    os.makedirs(FRAMES_DIR, exist_ok=True)
    src = paths.ensure_jp() / 'Video' / NAME
    subprocess.run([str(DECODER), str(src), os.devnull], cwd=str(FRAMES_DIR.parent), check=True,
                   stdout=subprocess.DEVNULL)


def original(i):
    return np.asarray(Image.open(FRAMES_DIR / f'video_rgb_{i}.ppm')).astype(np.float32)


def ko_logo():
    """한글 타이틀 로고(™ 뺌)를 화면 자리에 놓은 것: (바탕 위 장면, 알파)."""
    img = parts.load(parts.KO).copy()
    m = img[..., 3] > 8
    lab, n = nd.label(m)
    sz = nd.sum(m, lab, range(1, n + 1))
    keep = np.isin(lab, [k + 1 for k, s in enumerate(sz) if s > sz.max() * 0.02])
    img[..., 3] = np.where(keep, img[..., 3], 0)
    h, w = img.shape[:2]
    x0, y0 = CX - w * SCALE / 2, CY - h * SCALE / 2
    t = Image.fromarray(img).transform((640, 480), Image.AFFINE,
                                       (1 / SCALE, 0, -x0 / SCALE, 0, 1 / SCALE, -y0 / SCALE), resample=Image.BICUBIC)
    a = np.asarray(t).astype(np.float32)
    al = a[..., 3:4] / 255
    return BG * (1 - al) + a[..., :3] * al, al


def warp(img, k, dx, dy):
    """C0 기준 배율 k, 이동 (dx, dy)."""
    cx, cy = C0[0] + dx, C0[1] + dy
    out = []
    for c in range(3):
        im = Image.fromarray(img[..., c].astype(np.float32), 'F')
        out.append(np.asarray(im.transform((640, 480), Image.AFFINE,
                                           (1 / k, 0, C0[0] - cx / k, 0, 1 / k, C0[1] - cy / k), resample=Image.BILINEAR)))
    return np.stack(out, -1)


def whiten(img, w):
    yel = np.clip(((img[..., 0] + img[..., 1]) / 2 - img[..., 2] - 60) / 120, 0, 1)[..., None]
    return img + w * yel * (255 - img)


def frame(i, logo, al, track):
    if i >= 2308:
        return original(i)
    if 2295 <= i <= 2307:
        k = i - 2295
        sil = al * (240 - BG)
        x = (1 - M[k]) * (whiten(logo, W[k]) - BG) + M[k] * sil
        if SG[k] or SV[k]:
            x = nd.gaussian_filter(x, (SV[k], SG[k], 0))
        if B[k]:
            x = x + B[k] * nd.gaussian_filter(sil, (12, 40, 0))
        return (BG + x).clip(0, 255)
    p = track.get(str(i))
    if p is None:
        return np.full((480, 640, 3), BG, np.float32)
    k, dx, dy, g = p
    return (BG + g * warp(logo - BG, k, dx, dy)).clip(0, 255)


def to_yuv(rgb):
    """JPEG 전범위 YCbCr, 색은 2x2 평균(gen.to_yuv 와 같음)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    u = -0.168736 * r - 0.331264 * g + 0.5 * b + 128
    v = 0.5 * r - 0.418688 * g - 0.081312 * b + 128
    u = u.reshape(240, 2, 320, 2).mean((1, 3))
    v = v.reshape(240, 2, 320, 2).mean((1, 3))
    c = lambda x: np.clip(np.round(x), 0, 255).astype(np.uint8)
    return c(y), c(u), c(v)


def blocks(data):
    """원본 .h4m 을 (머리, [(영상 장수, 묶음 바이트(머리 20바이트 포함))]) 로 나눈다."""
    pos, out = 0x44, []
    while pos < len(data):
        _, sz, nv, _, _ = struct.unpack_from('>5I', data, pos)
        out.append((nv, data[pos:pos + 20 + sz]))
        pos += 20 + sz
    return data[:0x44], out


def main():
    decode_original()
    src = open(paths.ensure_jp() / 'Video' / NAME, 'rb').read()
    head, blks = blocks(src)
    assert len(blks) == 83 and sum(n for n, _ in blks) == TOTAL
    start = sum(n for n, _ in blks[:FIRST_BLK])
    logo, al = ko_logo()
    track = json.load(open(os.path.join(HERE, 'data', 'ending_track.json')))
    max_sz = struct.unpack_from('>I', head, 0x28)[0]
    new = []
    i = start
    for b in range(FIRST_BLK, LAST_BLK + 1):
        n = blks[b][0]
        body = b''
        for k in range(n):
            y, u, v = to_yuv(frame(i, logo, al, track).astype(np.uint8).astype(np.float32))
            data = struct.pack('>I', k) + h4m.encode_ipic(y, u, v)
            body += struct.pack('>HHI', 1, h4m.I_FRAME, len(data)) + data
            max_sz = max(max_sz, len(data))
            i += 1
            print(i - 1, end=' ', flush=True)
        flags = struct.unpack_from('>I', blks[b][1], 16)[0]
        new.append((n, struct.pack('>5I', 0, len(body), n, 0, flags) + body))
    blks[FIRST_BLK:LAST_BLK + 1] = new
    # 묶음 머리의 첫 값 = 앞 묶음 크기(머리 포함)
    out, prev = b'', 0
    for n, blk in blks:
        blk = struct.pack('>I', prev) + blk[4:]
        prev = len(blk)
        out += blk
    head = bytearray(head)
    struct.pack_into('>I', head, 0x14, len(out))
    struct.pack_into('>I', head, 0x28, max_sz)
    os.makedirs(OUT.parent, exist_ok=True)
    open(OUT, 'wb').write(bytes(head) + out)
    print('\n%s %d바이트(원본 %d, 가장 큰 장 %d)' % (OUT, len(head) + len(out), len(src), max_sz))


if __name__ == '__main__':
    main()
