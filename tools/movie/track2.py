"""색 비교(SSD)로 조각 움직임을 거꾸로 추적. 화면 = s*(u-c)+c+ORG+(dx,dy) (+ 회전 r)."""
import json
import os
import math

import numpy as np
from PIL import Image
from scipy.optimize import minimize

import parts

ORG = (34, 72)
BG = 16
DS = 2
SETTLE = [20, 34, 45]   # 조각별 제자리 시작 장
START = [5, 15, 28]     # 이 장 전에는 안 보임(추적 끝)


def frame(i):
    return np.asarray(Image.open(parts.JP_FRAMES / f'video_rgb_{i}.ppm')).astype(np.float32)


PS = parts.split(parts.load(parts.JP), parts.SEEDS['jp'])
CEN = []
for p in PS:
    ys, xs = np.where(p[..., 3] > 128)
    CEN.append(((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2))
PIMG = [Image.fromarray(p) for p in PS]


def place(k, s, dx, dy, r=0.0, W=640, H=480, ds=1, img=None, cen=None, org=ORG):
    """조각 k 를 화면에 놓은 RGBA(float) 반환."""
    img = img or PIMG[k]
    c = cen or CEN[k]
    # 화면 (X,Y) → 텍스처 u: u = R^-1((X - c - org - d)/s) + c
    cr, sr = math.cos(r), math.sin(r)
    tx = c[0] + org[0] + dx
    ty = c[1] + org[1] + dy
    # 축소 화면 좌표 x' = X/ds
    a = ds * cr / s
    b = ds * sr / s
    d = -ds * sr / s
    e = ds * cr / s
    cx = -(tx * cr + ty * sr) / s + c[0]
    cy = -(-tx * sr + ty * cr) / s + c[1]
    out = img.transform((W // ds, H // ds), Image.AFFINE, (a, b, cx, d, e, cy), resample=Image.BILINEAR)
    return np.asarray(out).astype(np.float32)


def comp(layers, W=640, H=480, ds=1):
    out = np.full((H // ds, W // ds, 3), BG, np.float32)
    for L in layers:
        al = L[..., 3:] / 255
        out = L[..., :3] * al + out * (1 - al)
    return out


def static_layers(t, ds):
    return [place(k, 1, 0, 0, ds=ds) for k in range(3) if t >= SETTLE[k]]


def fit_part(t, k, init, fr, res):
    tgt = fr[::DS, ::DS]
    later = [place(j, 1, 0, 0, ds=DS) for j in range(3) if j != k and t >= SETTLE[j]]
    later += [place(j, *res[t][j], ds=DS) for j in res.get(t, {}) if j != k]

    def cost(v):
        ls, dx, dy, r = v
        L = place(k, math.exp(ls), dx, dy, r, ds=DS)
        return float(((comp(later + [L], ds=DS) - tgt) ** 2).mean())
    best = None
    s0, dx0, dy0, r0 = init
    for ks in (1.0, 1.25, 0.8, 1.6, 2.2):
        x0 = [math.log(s0 * ks), dx0, dy0, r0]
        o = minimize(cost, x0, method='Nelder-Mead',
                     options=dict(xatol=0.05, fatol=0.5, maxiter=300, initial_simplex=[
                         x0, [x0[0] + 0.1, x0[1], x0[2], x0[3]], [x0[0], x0[1] + 15 * s0, x0[2], x0[3]],
                         [x0[0], x0[1], x0[2] + 15 * s0, x0[3]], [x0[0], x0[1], x0[2], x0[3] + 0.05]]))
        if best is None or o.fun < best.fun:
            best = o
    ls, dx, dy, r = best.x
    return (math.exp(ls), dx, dy, r), best.fun


if __name__ == '__main__':
    res = {}
    for k in (2, 1, 0):
        cur = (1.0, 0.0, 0.0, 0.0)
        for t in range(SETTLE[k] - 1, START[k], -1):
            fr = frame(t)
            cur, e = fit_part(t, k, cur, fr, res)
            res.setdefault(t, {})[k] = cur
            print(k, t, 's=%.3f d=(%.1f,%.1f) r=%.3f  오차 %.0f' % (*cur, e), flush=True)
    json.dump(res, open(os.path.join(parts.DATA, 'track2.json'), 'w'))
