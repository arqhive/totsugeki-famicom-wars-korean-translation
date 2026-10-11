"""한글 타이틀 무비 97장 만들기(원본 연출 재현).
조각 0 돌격!!: 원본 추적값(균일 배율 s + 이동 d), 확대 장면은 고해상도 그림.
조각 1 패미컴 / 2 워즈★: 원본 노란 글자 가장자리로 잰 미끄러짐·눌림(가로 배율).
파편 줄·빛 줄기는 원본 장면에서 로고 밖 밝은 픽셀을 옮겨 오고, 번쩍임은 flashfit 모형을 한글 로고에 적용."""
import json
import os
import math
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as nd

import flashfit
import parts
import track2 as T

ORG = (34, 72)
BG = 16.0
W, H = 640, 480
HI_K = 587 / 1763          # 고해상도 → 게임판 배율
HI_OFF = (0.0, 1 - 4 * HI_K)

KO = parts.load(parts.KO)
KPS = parts.split(KO, parts.SEEDS['ko'])
HI = parts.load(parts.HI)
HPS = parts.split(HI, parts.SEEDS['ko'], scale=1 / HI_K)
KIMG = [Image.fromarray(p) for p in KPS]
HIMG = [Image.fromarray(p) for p in HPS]


def bbox(p):
    ys, xs = np.where(p[..., 3] > 128)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


KBOX = [bbox(p) for p in KPS]
JBOX = [bbox(p) for p in T.PS]
KCEN = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in KBOX]

TR = {int(t): {int(k): v for k, v in d.items()} for t, d in json.load(open(os.path.join(parts.DATA, 'track2.json'))).items()}
FL2 = {int(t): v for t, v in json.load(open(os.path.join(parts.DATA, 'flash2.json'))).items()}

# 패미컴: 원본 노란 글자 너비 296, 오른쪽 끝 346 기준. (가로 배율, 가운데 이동 px)
JW1 = 296.0
P1 = {16: (1, -286), 17: (1, -198), 18: (1, -125), 19: (1, -62),
      20: (.88, 14), 21: (.78, 46), 22: (.82, 30), 23: (.95, 19),
      24: (1.02, -2.5), 25: (1.07, -12.5), 26: (1.06, -10), 27: (1.03, -5.5),
      28: (.99, 1), 29: (.95, 6), 30: (.95, 8), 31: (.97, 9.5), 32: (.99, 6.5)}
# 워즈★: 원본 너비 245. 29~32 은 이동, 33~ 은 왼쪽 고정 가로 배율
JW2 = 245.0
P2 = {29: ('t', 251), 30: ('t', 158), 31: ('t', 70), 32: ('t', 11),
      33: ('s', .76), 34: ('s', .85), 35: ('s', .94), 36: ('s', 1.03), 37: ('s', 1.07), 38: ('s', 1.06),
      39: ('s', 1.0), 40: ('s', .97), 41: ('s', .94), 42: ('s', .95), 43: ('s', .98), 44: ('s', 1.0)}


def place(k, A, use_hi=False):
    """A: 게임판 텍스처 좌표 → 화면 좌표 2x3 행렬(numpy). RGBA float 반환."""
    M = np.vstack([A, [0, 0, 1]])
    if use_hi:
        S = np.array([[HI_K, 0, HI_OFF[0]], [0, HI_K, HI_OFF[1]], [0, 0, 1]])
        M = M @ S
        img = HIMG[k]
        # 많이 줄이는 경우 먼저 LANCZOS 로 줄여 계단 현상을 막는다
        sc = math.sqrt(abs(np.linalg.det(M[:2, :2])))
        if sc < 0.9:
            f = sc
            img = img.resize((max(1, round(img.width * f)), max(1, round(img.height * f))), Image.LANCZOS)
            M = M @ np.diag([1 / f, 1 / f, 1])
    else:
        img = KIMG[k]
    Mi = np.linalg.inv(M)
    out = img.transform((W, H), Image.AFFINE, tuple(Mi[:2].reshape(-1)), resample=Image.BILINEAR)
    return np.asarray(out).astype(np.float32)


def affine(sx, sy, ax, ay, dx, dy):
    """(ax,ay) 를 기준점으로 sx,sy 배율 뒤 (dx,dy) 이동, ORG 더함."""
    return np.array([[sx, 0, ax - sx * ax + dx + ORG[0]], [0, sy, ay - sy * ay + dy + ORG[1]]], np.float64)


def part_matrix(k, t):
    """None 이면 안 보임."""
    if k == 0:
        if t < 6:
            return None
        if t >= T.SETTLE[0]:
            return affine(1, 1, 0, 0, 0, 0)
        s, dx, dy, r = TR[t][0]
        c = KCEN[0]
        return affine(s, s, c[0], c[1], dx, dy)
    if k == 1:
        if t < 16:
            return None
        if t not in P1:
            return affine(1, 1, 0, 0, 0, 0)
        sx, d = P1[t]
        wk = KBOX[1][2] - KBOX[1][0]
        c = KCEN[1]
        return affine(sx, 1, c[0], c[1], d * wk / JW1, 0)
    if t < 29:
        return None
    if t not in P2:
        return affine(1, 1, 0, 0, 0, 0)
    kind, v = P2[t]
    wk = KBOX[2][2] - KBOX[2][0]
    if kind == 't':
        return affine(1, 1, 0, 0, v * wk / JW2, 0)
    return affine(v, 1, KBOX[2][0], KCEN[2][1], 0, 0)


def jp_model_alpha(t):
    """원본 장면에서 로고가 차지한 자리(파편만 남기려고 뺄 곳)."""
    f = T.frame(t)
    lum = np.abs(f - BG).sum(2)
    logo = (f[..., 0] > 90) & (f[..., 1] > 80) & (f[..., 2] < 110)  # 노랑·초록 몸통
    logo |= (f[..., 1] > f[..., 2] + 25) & (lum > 60)
    lab, n = nd.label(lum > 40)
    if n:
        sizes = nd.sum(np.ones_like(lum), lab, range(1, n + 1))
        big = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 1500])
        logo |= big
    return nd.binary_dilation(logo, iterations=6)


def debris(t):
    """원본의 로고 밖 밝은 픽셀(파편 줄·별빛). 46장부터는 번쩍임 모형이 맡는다."""
    if t < 6 or t > 45:
        return None
    f = T.frame(t)
    keep = (np.abs(f - BG).sum(2) > 30) & ~jp_model_alpha(t)
    if not keep.any():
        return None
    return np.where(keep[..., None], f, np.nan)


def ko_logo_layer():
    L = np.zeros((H, W, 4), np.float32)
    for k in range(3):
        L = np.maximum(L, place(k, affine(1, 1, 0, 0, 0, 0))) if False else L
    out = np.zeros((H, W, 4), np.float32)
    rgb = np.full((H, W, 3), 0, np.float32)
    al = np.zeros((H, W), np.float32)
    for k in range(3):
        P = place(k, affine(1, 1, 0, 0, 0, 0))
        a = P[..., 3] / 255
        rgb = P[..., :3] * a[..., None] + rgb * (1 - a[..., None])
        al = a + al * (1 - a)
    out[..., :3] = np.where(al[..., None] > 0, rgb / np.maximum(al[..., None], 1e-6), 0)
    out[..., 3] = al * 255
    return out


KL = None


def flash_frame(t):
    """46~ 장: flashfit 모형. 끝(96장) 기준값을 빼서 마지막엔 한글 로고 그대로가 되게 한다."""
    global KL
    if KL is None:
        KL = ko_logo_layer()
    if t not in FL2:
        return KL[..., :3] * (KL[..., 3:] / 255) + BG * (1 - KL[..., 3:] / 255)
    a, sig, g, sg = FL2[t]
    if t >= 56:
        a = max(0.0, (a - 0.15) / 0.85)  # 원본 영상과 텍스처의 기본 색 차이(0.15)를 뺀다
    p = [a, sig * 2, g, sg * 2, 240.0, 222.0, 150.0]
    return flashfit.render(KL, p)


def shine(t, base):
    """74~89 장 빛 줄기: 원본에서 마지막 장보다 밝아진 만큼을 한글 로고 자리에만 더한다."""
    if not 74 <= t <= 95:
        return base
    d = np.clip(T.frame(t) - T.frame(96), 0, None)
    d = nd.gaussian_filter(d, (1, 1, 0))
    return np.clip(base + d * (KL[..., 3:] / 255), 0, 255)


def frame(t):
    if t >= 46:
        return shine(t, flash_frame(t))
    out = np.full((H, W, 3), BG, np.float32)
    for k in range(3):
        A = part_matrix(k, t)
        if A is None:
            continue
        use_hi = k == 0 and t < T.SETTLE[0] and TR[t][0][0] > 1.15
        P = place(k, A, use_hi)
        a = P[..., 3:] / 255
        out = P[..., :3] * a + out * (1 - a)
    d = debris(t)
    if d is not None:
        m = ~np.isnan(d[..., 0])
        out[m] = np.maximum(out[m], d[m])
    return np.clip(out, 0, 255)


def to_yuv(rgb):
    """JPEG 전범위 YCbCr(디코더 dumpRGB 의 역). 색은 2x2 평균."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    u = -0.168736 * r - 0.331264 * g + 0.5 * b + 128
    v = 0.5 * r - 0.418688 * g - 0.081312 * b + 128
    u = u.reshape(H // 2, 2, W // 2, 2).mean((1, 3))
    v = v.reshape(H // 2, 2, W // 2, 2).mean((1, 3))
    c = lambda x: np.clip(np.round(x), 0, 255).astype(np.uint8)
    return c(y), c(u), c(v)


if __name__ == '__main__':
    out = parts.MOVIE / 'ko'
    os.makedirs(out, exist_ok=True)
    ts = [int(x) for x in sys.argv[1:]] or range(97)
    for t in ts:
        Image.fromarray(frame(t).astype(np.uint8)).save(out / f'{t:03d}.png')
        print(t, end=' ', flush=True)
