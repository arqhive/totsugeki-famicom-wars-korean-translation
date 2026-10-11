"""번쩍임(45~장) 모형 맞추기.
logo(RGBA, 화면 위치) → 색을 크림색 C 로 a 만큼 섞고, 층 전체를 sigma 로 흐리게, 빛 번짐 g*blur(alpha, sg)*C 를 더한다."""
import json
import math

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.optimize import minimize

import parts

ORG = (34, 72)
BG = 16.0


def logo_layer(path=parts.JP, seeds='jp'):
    img = parts.load(path)
    # ™ 빼기: 조각 셋 합치기
    ps = parts.split(img, parts.SEEDS[seeds])
    a = np.max([p[..., 3] for p in ps], axis=0)
    L = np.zeros((480, 640, 4), np.float32)
    h, w = a.shape
    L[ORG[1]:ORG[1] + h, ORG[0]:ORG[0] + w, :3] = img[..., :3]
    L[ORG[1]:ORG[1] + h, ORG[0]:ORG[0] + w, 3] = a
    return L


def render(L, p):
    a, sig, g, sg, cr, cg, cb = p
    C = np.array([cr, cg, cb], np.float32)
    al = L[..., 3:] / 255
    rgb = L[..., :3] * (1 - a) + C * a
    if sig > 0.05:
        pre = gaussian_filter(rgb * al, (sig, sig, 0))
        al2 = gaussian_filter(al, (sig, sig, 0))
    else:
        pre, al2 = rgb * al, al
    out = pre + BG * (1 - al2)
    glow = gaussian_filter(al[..., 0], max(sg, 0.3))[..., None] * C * g
    return np.clip(out + glow, 0, 255)


if __name__ == '__main__':
    L = logo_layer()[::2, ::2]  # 반 해상도로 맞춤(시그마도 반 해상도 단위)
    res = {}
    p = [0.0, 0.0, 0.0, 3.0, 240.0, 220.0, 150.0]
    sl = (slice(20, 140), slice(0, 320))
    for t in range(44, 97):
        f = np.asarray(Image.open(parts.JP_FRAMES / f'video_rgb_{t}.ppm')).astype(np.float32)[::2, ::2]

        def cost(v):
            q = list(v)
            q[0] = min(max(q[0], 0), 1); q[1] = max(q[1], 0); q[2] = max(q[2], 0)
            return float(((render(L, q)[sl] - f[sl]) ** 2).mean())
        o = minimize(cost, p, method='Powell', options=dict(maxiter=4000, xtol=0.01, ftol=0.1))
        p = list(o.x)
        p[0] = min(max(p[0], 0), 1); p[1] = max(p[1], 0); p[2] = max(p[2], 0)
        res[t] = p
        print(t, ' '.join('%.3f' % v for v in p), '오차 %.1f' % o.fun, flush=True)
    json.dump(res, open('flash.json', 'w'))
