"""GC 텍스처 인코더: C8(256색, RGB5A3 팔레트) / CMPR(DXT1). 결과는 tex.py 로 다시 풀어 검증한다."""
import numpy as np
from PIL import Image


def _to_rgb5a3(rgba):
    r, g, b, a = [rgba[:, i].astype(np.int32) for i in range(4)]
    op = a >= 0xE0
    v_op = 0x8000 | ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3)
    v_tr = ((a >> 5) << 12) | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)
    return np.where(op, v_op, v_tr).astype('>u2')


def encode_c8(img):
    """RGBA PIL 이미지 → (팔레트 512바이트, 픽셀 바이트)"""
    w, h = img.size
    q = img.convert('RGBA').quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette(rawmode='RGBA')[:256 * 4], np.uint8).reshape(-1, 4)
    pal = np.vstack([pal, np.zeros((256 - len(pal), 4), np.uint8)])
    idx = np.array(q, np.uint8)
    tx, ty = (w + 7) // 8, (h + 3) // 4
    padded = np.zeros((ty * 4, tx * 8), np.uint8); padded[:h, :w] = idx
    tiles = padded.reshape(ty, 4, tx, 8).transpose(0, 2, 1, 3)
    return _to_rgb5a3(pal).tobytes(), tiles.tobytes()


def _565(c):
    c = np.clip(c, 0, 255).astype(np.int32)
    return ((c[..., 0] >> 3) << 11) | ((c[..., 1] >> 2) << 5) | (c[..., 2] >> 3)


def _from565(v):
    return np.stack([(v >> 11 & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31], -1)


def encode_cmpr(img):
    """불투명 RGB 이미지 → CMPR 바이트(8x8 타일 안에 4x4 블록 4개, 빅엔디언)"""
    w, h = img.size
    a = np.asarray(img.convert('RGB'), np.float32)
    tx, ty = (w + 7) // 8, (h + 7) // 8
    pad = np.zeros((ty * 8, tx * 8, 3), np.float32); pad[:h, :w] = a
    # 블록 순서: 타일(y,x) → 서브블록(0,0)(0,4)(4,0)(4,4)
    blk = pad.reshape(ty, 2, 4, tx, 2, 4, 3).transpose(0, 3, 1, 4, 2, 5, 6).reshape(-1, 16, 3)
    mean = blk.mean(1, keepdims=True)
    cen = blk - mean
    cov = np.einsum('nki,nkj->nij', cen, cen)
    axis = np.ones((len(blk), 3), np.float32)
    for _ in range(8):  # 거듭제곱법으로 주성분 축
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.maximum(np.linalg.norm(axis, axis=1, keepdims=True), 1e-6)
    proj = np.einsum('nki,ni->nk', cen, axis)
    lo = mean[:, 0] + axis * proj.min(1, keepdims=True)
    hi = mean[:, 0] + axis * proj.max(1, keepdims=True)
    c0, c1 = _565(hi), _565(lo)
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    e0, e1 = _from565(c0).astype(np.float32), _from565(c1).astype(np.float32)
    pal = np.stack([e0, e1, (2 * e0 + e1) / 3, (e0 + 2 * e1) / 3], 1)  # 4색 모드(c0>c1)
    d = ((blk[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)
    idx = d.argmin(2)
    same = c0 == c1  # 단색 블록: 3색 모드여도 0번만 쓰면 같다
    idx[same] = 0
    bits = np.zeros(len(blk), np.uint64)
    for i in range(16):
        bits |= idx[:, i].astype(np.uint64) << np.uint64(30 - 2 * i)
    out = np.zeros((len(blk), 8), np.uint8)
    out[:, 0] = c0 >> 8; out[:, 1] = c0 & 255; out[:, 2] = c1 >> 8; out[:, 3] = c1 & 255
    for k in range(4):
        out[:, 4 + k] = (bits >> np.uint64(24 - 8 * k)) & np.uint64(255)
    return out.tobytes()
