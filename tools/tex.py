"""Kuju TXET 텍스처(GC 형식) → RGBA numpy.
헤더(청크 시작 기준): 0x18 폭, 0x1C 높이, 0x28 형식('DXT1'=CMPR, 'P8'=C8, 'P4'=C4, 'A8R8'=RGBA8),
0x5C 부터 하위 청크: ' LAP'(팔레트, RGB5A3 BE) / ' PIM'(픽셀). 첫 밉맵만 읽는다."""
import re
import struct

import numpy as np


def rgb5a3(v):
    v = v.astype(np.uint32)
    op = (v & 0x8000) != 0
    r = np.where(op, (v >> 10 & 31) * 255 // 31, (v >> 8 & 15) * 17)
    g = np.where(op, (v >> 5 & 31) * 255 // 31, (v >> 4 & 15) * 17)
    b = np.where(op, (v & 31) * 255 // 31, (v & 15) * 17)
    a = np.where(op, 255, (v >> 12 & 7) * 255 // 7)
    return np.stack([r, g, b, a], -1).astype(np.uint8)


def _tiles(w, h, tw, th):
    return (w + tw - 1) // tw, (h + th - 1) // th


def dec_c4(raw, w, h, pal):
    tx, ty = _tiles(w, h, 8, 8)
    a = np.frombuffer(raw[:tx * ty * 32], np.uint8)
    px = np.stack([a >> 4, a & 15], 1).reshape(ty, tx, 8, 8).transpose(0, 2, 1, 3).reshape(ty * 8, tx * 8)
    return pal[px][:h, :w]


def dec_c8(raw, w, h, pal):
    tx, ty = _tiles(w, h, 8, 4)
    a = np.frombuffer(raw[:tx * ty * 32], np.uint8).reshape(ty, tx, 4, 8).transpose(0, 2, 1, 3).reshape(ty * 4, tx * 8)
    return pal[a][:h, :w]


def dec_rgba8(raw, w, h):
    tx, ty = _tiles(w, h, 4, 4)
    a = np.frombuffer(raw[:tx * ty * 64], np.uint8).reshape(ty, tx, 2, 16, 2)
    ar, gb = a[:, :, 0], a[:, :, 1]
    img = np.stack([ar[..., 1], gb[..., 0], gb[..., 1], ar[..., 0]], -1)  # R G B A
    return img.reshape(ty, tx, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(ty * 4, tx * 4, 4)[:h, :w]


def _565(c):
    return np.array([(c >> 11 & 31) * 255 // 31, (c >> 5 & 63) * 255 // 63, (c & 31) * 255 // 31], np.int32)


def dec_cmpr(raw, w, h):
    tx, ty = _tiles(w, h, 8, 8)
    img = np.zeros((ty * 8, tx * 8, 4), np.uint8)
    p = 0
    for by in range(ty):
        for bx in range(tx):
            for sy in (0, 4):
                for sx in (0, 4):
                    c0, c1, bits = struct.unpack_from('>HHI', raw, p); p += 8
                    a, b = _565(c0), _565(c1)
                    if c0 > c1:
                        pal = [(*a, 255), (*b, 255), (*((2 * a + b) // 3), 255), (*((a + 2 * b) // 3), 255)]
                    else:
                        pal = [(*a, 255), (*b, 255), (*((a + b) // 2), 255), (0, 0, 0, 0)]
                    pal = np.array(pal, np.uint8)
                    idx = np.array([(bits >> (30 - 2 * i)) & 3 for i in range(16)]).reshape(4, 4)
                    img[by * 8 + sy:by * 8 + sy + 4, bx * 8 + sx:bx * 8 + sx + 4] = pal[idx]
    return img[:h, :w]


def decode_chunk(c):
    """c: TXET 청크 바이트 → (이름, RGBA)"""
    name = c[8:0x18].split(b'\0')[0].decode('latin1')
    w, h = struct.unpack_from('<II', c, 0x18)
    fmt = c[0x28:0x2C].rstrip(b'\0')
    pal = None
    pl = c.find(b' LAP', 0x58)
    pm = c.find(b' PIM', 0x58)
    if pl >= 0 and (pm < 0 or pl < pm):
        psz = struct.unpack_from('<I', c, pl + 4)[0]
        pal = rgb5a3(np.frombuffer(c[pl + 8:pl + 8 + psz], '>u2'))
    psz = struct.unpack_from('<I', c, pm + 4)[0]
    raw = c[pm + 8:pm + 8 + psz]
    if fmt == b'DXT1':
        img = dec_cmpr(raw, w, h)
    elif fmt == b'P8':
        img = dec_c8(raw, w, h, pal)
    elif fmt == b'P4':
        img = dec_c4(raw, w, h, pal)
    elif fmt == b'A8R8':
        img = dec_rgba8(raw, w, h)
    else:
        raise ValueError(fmt)
    return name, img


def iter_chunks(d):
    for m in re.finditer(rb'TXET', d):
        o = m.start()
        if o + 0x60 > len(d):
            continue
        sz = struct.unpack_from('<I', d, o + 4)[0] + 8
        w, h = struct.unpack_from('<II', d, o + 0x18)
        if not (0 < w <= 4096 and 0 < h <= 4096) or o + sz > len(d):
            continue
        yield o, d[o:o + sz]
