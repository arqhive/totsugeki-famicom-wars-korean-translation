"""Kuju 폰트 BTF(FTBX) 읽기/쓰기 — 256x256 C4(P4) 시트 전용.

파일: 'FTBX' + 8바이트(u16 ?, u16 ?, u32 시트 수) + TXET 청크 x N (빈틈 없음)
TXET 청크(크기 필드 = 전체-8): 0x00 'TXET', 0x04 크기, 0x08 이름[16], 0x18 폭, 0x1C 높이,
  ... 0x5C ' LAP' + 크기 0x20 + RGB5A3 팔레트 16색(BE), 0x84 ' PIM' + 크기 0x8000 + C4 픽셀(8x8 타일, 앞 니블 먼저)
"""
import struct

import numpy as np

W = H = 256


def _untile4(raw):
    a = np.frombuffer(raw, np.uint8)
    hi, lo = a >> 4, a & 15
    px = np.stack([hi, lo], 1).reshape(H // 8, W // 8, 8, 8)  # 타일y, 타일x, y, x
    return px.transpose(0, 2, 1, 3).reshape(H, W)


def _tile4(idx):
    t = idx.reshape(H // 8, 8, W // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 2)
    return ((t[:, 0] << 4) | t[:, 1]).astype(np.uint8).tobytes()


def load(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'FTBX'
    n = struct.unpack_from('<I', d, 8)[0]
    o = 12
    texs = []
    for _ in range(n):
        assert d[o:o + 4] == b'TXET'
        size = struct.unpack_from('<I', d, o + 4)[0] + 8
        c = d[o:o + size]
        assert c[0x28:0x2A] == b'P4' and c[0x5C:0x60] == b' LAP' and c[0x84:0x88] == b' PIM', path
        texs.append(dict(head=c[:0x8C], name=c[8:0x18].split(b'\0')[0].decode(),
                         idx=_untile4(c[0x8C:0x8C + 0x8000]), pal=c[0x64:0x84]))
        o += size
    assert o == len(d)
    return dict(hdr=d[4:8], texs=texs)


def save(f, path):
    out = bytearray(b'FTBX' + f['hdr'] + struct.pack('<I', len(f['texs'])))
    for t in f['texs']:
        head = bytearray(t['head'])
        head[8:0x18] = t['name'].encode().ljust(16, b'\0')
        head[0x64:0x84] = t['pal']
        out += head + _tile4(t['idx'])
    open(path, 'wb').write(out)


if __name__ == '__main__':
    import glob
    import sys
    import tempfile, os
    ok = 0
    for p in sorted(glob.glob(sys.argv[1] + '/*.btf')):
        try:
            f = load(p)
        except AssertionError:
            continue
        tmp = os.path.join(tempfile.gettempdir(), 'btfw_test.btf')
        save(f, tmp)
        same = open(tmp, 'rb').read() == open(p, 'rb').read()
        ok += same
        if not same:
            print('다름', p)
    print('재저장 동일', ok)
