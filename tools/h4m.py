"""HVQM4 1.5(.h4m) 무비 인코더 — I 프레임만 쓰는 단순판.

블록(4x4) 종류는 둘만 쓴다.
  8: 한 값으로 채운 블록(DC)
  6: 원본 16바이트를 그대로 넣는 블록(fixvl)
디코더 기준은 Tilka/hvqm4(h4m_audio_decode.c) 의 HVQM4DecodeIpic.
"""
import heapq
import struct

import numpy as np

I_FRAME = 0x10


class BitWriter:
    """MSB 먼저, 32비트 빅엔디언 단어로 읽히는 비트열."""

    def __init__(self):
        self.bits = []

    def bit(self, b):
        self.bits.append(b & 1)

    def byte(self, v):
        for i in range(7, -1, -1):
            self.bits.append((v >> i) & 1)

    def code(self, c):
        self.bits.extend(c)

    def data(self):
        n = len(self.bits)
        if n == 0:
            return b''
        pad = (-n) % 32
        a = np.array(self.bits + [0] * pad, np.uint8)
        return np.packbits(a).tobytes()


class Huff:
    """바이트 기호 허프만 표. 트리는 앞순회(1=가지, 0=잎+8비트)로 적는다."""

    def __init__(self, freq):
        syms = [s for s in range(256) if freq.get(s, 0)]
        if not syms:
            syms = [0]
        if len(syms) == 1:
            self.tree = ('leaf', syms[0])
        else:
            heap = [(freq[s], i, ('leaf', s)) for i, s in enumerate(syms)]
            heapq.heapify(heap)
            k = len(heap)
            while len(heap) > 1:
                a = heapq.heappop(heap)
                b = heapq.heappop(heap)
                heapq.heappush(heap, (a[0] + b[0], k, ('node', a[2], b[2])))
                k += 1
            self.tree = heap[0][2]
        self.codes = {}
        self._walk(self.tree, [])

    def _walk(self, t, path):
        if t[0] == 'leaf':
            self.codes[t[1]] = path
        else:
            self._walk(t[1], path + [0])
            self._walk(t[2], path + [1])

    def write_tree(self, bw):
        def rec(t):
            if t[0] == 'leaf':
                bw.bit(0)
                bw.byte(t[1])
            else:
                bw.bit(1)
                rec(t[1])
                rec(t[2])
        rec(self.tree)

    def put(self, bw, sym):
        bw.code(self.codes[sym])


def _plane_blocks(p):
    h, w = p.shape
    return p.reshape(h // 4, 4, w // 4, 4).transpose(0, 2, 1, 3)  # (by, bx, 4, 4)


def _dc_deltas(values):
    """IpicDcvDec 의 예측을 따라 블록 DC 값 → 차이값 목록(uint8 순환)."""
    vb, hb = values.shape
    prev = np.full(hb + 1, 0x7F, np.int32)  # 위 줄(+오른쪽 테두리 0x7F)
    out = []
    for y in range(vb):
        value = int(prev[0])
        cur = np.full(hb + 1, 0x7F, np.int32)
        for x in range(hb):
            t = int(values[y, x])
            out.append((t - value) & 0xFF)
            value = t
            cur[x] = t
            value = (value + int(prev[x + 1]) + 1) // 2
        prev = cur
    return out


def _signed(d):
    return d - 256 if d >= 128 else d


def _dc_symbols(delta):
    """한 차이값을 decodeSOvfSym 이 읽는 기호들(int8)로. 127·-128 은 넘침 기호로 이어 적는다."""
    s = _signed(delta)
    if -128 < s < 127:
        return [s]
    return [s, 0]  # 127 / -128: 넘침 기호 뒤에 0 을 붙여 합을 끝낸다


def _with_rle(seq, is_zero):
    """0 다음에 이어지는 0 개수를 적는 run 방식으로 (기호, run 또는 None) 목록을 만든다."""
    out = []
    i = 0
    n = len(seq)
    while i < n:
        if is_zero(seq[i]):
            j = i + 1
            while j < n and is_zero(seq[j]) and j - i - 1 < 255:
                j += 1
            out.append((seq[i], j - i - 1))
            i = j
        else:
            out.append((seq[i], None))
            i += 1
    return out


def encode_ipic(y, u, v, tol=0):
    """평면 3개(uint8) → I 프레임 본문(표시 번호 4바이트 제외)."""
    planes = [y, u, v]
    types, dcs, raws = [], [], []
    for p in planes:
        b = _plane_blocks(p.astype(np.int32))
        mn = b.min(axis=(2, 3))
        mx = b.max(axis=(2, 3))
        mean = (b.sum(axis=(2, 3)) + 8) // 16
        flat = (mx - mn) <= tol * 2
        t = np.where(flat, 8, 6).astype(np.int32)
        # 원본 블록(6)의 DC 는 예측값과 같게 두면 차이 0 이 되지만, 예측이 앞 값에 기대므로 평균을 쓴다
        dc = np.where(flat, mean, mean).astype(np.int32)
        types.append(t)
        dcs.append(dc)
        raw = b.astype(np.uint8)[t == 6]  # (n, 4, 4) 래스터 순서
        raws.append(raw.reshape(-1).tobytes())

    # 블록 종류: 밝기, 색(u | v<<4)
    luma_syms = [int(t) for t in types[0].reshape(-1)]
    chroma_syms = [int(a) | (int(b) << 4) for a, b in zip(types[1].reshape(-1), types[2].reshape(-1))]
    luma_r = _with_rle(luma_syms, lambda s: s == 0)
    chroma_r = _with_rle(chroma_syms, lambda s: s == 0)

    # DC 차이값
    dc_r = []
    for dc in dcs:
        syms = []
        for d in _dc_deltas(dc):
            syms.append(d)
        dc_r.append(_with_rle(syms, lambda s: s == 0))

    # 허프만 빈도
    fb, frun, fdc = {}, {}, {}
    for seq in (luma_r, chroma_r):
        for s, r in seq:
            fb[s] = fb.get(s, 0) + 1
            if r is not None:
                frun[r] = frun.get(r, 0) + 1
    for seq in dc_r:
        for d, r in seq:
            for s in _dc_symbols(d):
                fdc[s & 0xFF] = fdc.get(s & 0xFF, 0) + 1
            if r is not None:
                frun[r] = frun.get(r, 0) + 1
    hb_, hr, hd = Huff(fb), Huff(frun), Huff(fdc)

    # 버퍼들
    bn = [BitWriter(), BitWriter()]
    bnr = [BitWriter(), BitWriter()]
    hb_.write_tree(bn[0])
    hr.write_tree(bnr[0])
    for i, seq in enumerate((luma_r, chroma_r)):
        for s, r in seq:
            hb_.put(bn[i], s)
            if r is not None:
                hr.put(bnr[i], r)
    dcv = [BitWriter() for _ in range(3)]
    dcr = [BitWriter() for _ in range(3)]
    hd.write_tree(dcv[0])
    for i, seq in enumerate(dc_r):
        for d, r in seq:
            for s in _dc_symbols(d):
                hd.put(dcv[i], s & 0xFF)
            if r is not None:
                hr.put(dcr[i], r)

    def chunk(data):
        return struct.pack('>I', len(data)) + data

    bufs = []  # 순서는 HVQM4DecodeIpic 의 setCode 순서
    for i in range(2):
        bufs.append(chunk(bn[i].data()))
        bufs.append(chunk(bnr[i].data()))
    for i in range(3):
        bufs.append(chunk(dcv[i].data()))
        bufs.append(chunk(b''))  # bufTree0(기저 계수) — 안 씀
        bufs.append(chunk(raws[i]))
    for i in range(3):
        bufs.append(chunk(dcr[i].data()))
    offs, pos = [], 0
    for b in bufs:
        offs.append(pos)
        pos += len(b)
    head = struct.pack('>BBHHH', 0, 9, 0, 0, 0) + b''.join(struct.pack('>I', o) for o in offs)
    assert len(head) == 8 + 0x40
    return head + b''.join(bufs)


def write_h4m(path, frames, usec_per_frame=33333, gop=30, w=640, h=480):
    """frames: [(y, u, v)] → I 프레임만으로 된 .h4m. 묶음(GOP)은 원본처럼 gop 장씩."""
    blocks = []
    max_sz = 0
    for s in range(0, len(frames), gop):
        body = b''
        part = frames[s:s + gop]
        for k, (y, u, v) in enumerate(part):
            data = struct.pack('>I', k) + encode_ipic(y, u, v)
            body += struct.pack('>HHI', 1, I_FRAME, len(data)) + data
            max_sz = max(max_sz, len(data))
        blocks.append((len(part), body))
    out = b''
    prev = 0
    for i, (n, body) in enumerate(blocks):
        blk = struct.pack('>5I', prev, len(body), n, 0, 0x01000000) + body
        prev = len(blk)
        out += blk
    hdr = b'HVQM4 1.5'.ljust(16, b'\0')
    hdr += struct.pack('>9I', 0x44, len(out), len(blocks), len(frames), 0, usec_per_frame, max_sz, 0, 0)
    hdr += struct.pack('>HHBBBBBBBBI', w, h, 2, 2, 0, 0, 0, 0, 0, 0, 0)
    open(path, 'wb').write(hdr + out)
    return len(hdr) + len(out), max_sz
