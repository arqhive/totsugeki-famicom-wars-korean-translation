"""한글 ISO 빌드: 번역 검사 → 문자열·장면 폰트 → 이미지 → ISO 조립 → 검증.
사용: python tools/build.py [출력 ISO]      (기본 work/TotsugekiFamicomWars_KO.iso)
"""
import os
import re
import shutil
import struct
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_iso
import build_text
import check_ko
import kolib
import paths
import strfile
import tex
import texenc

OUT_DATA = paths.WORK / 'build'           # 바뀐 파일만 모아 두는 곳(ISO 경로와 같은 구조)
# (ISO 안 경로, 텍스처 이름, 한글화 이미지)
IMAGES = [('Data/CompoundFiles/frontend_0_Level.res', b'BWTitleLogoJp', 'BWTitleLogoJp.png'),
          ('Data/Startup/WarningJap.btf', b'warningJap', 'warningJap.png'),
          ('Data/Startup/WarningJap.btf', b'pstartJap', 'pstartJap.png')]


def build_strings():
    kor = {}
    for fname, items in kolib.load_all().items():
        n = len(strfile.load(paths.JP_DATA / 'Strings' / fname)['ents'])
        lst = [None] * n
        for i, ko in items.items():
            lst[i] = ko
        kor[fname] = lst
    return build_text.build(kor, str(OUT_DATA))


def build_images():
    files = {}
    for path, name, png in IMAGES:
        if path not in files:
            src = OUT_DATA / path if (OUT_DATA / path).exists() else paths.JP / path
            files[path] = bytearray(open(src, 'rb').read())
        d = files[path]
        o = next(m.start() for m in re.finditer(rb'TXET', d) if d[m.start() + 8:m.start() + 9 + len(name)] == name + b'\0')
        size = struct.unpack_from('<I', d, o + 4)[0] + 8
        c = d[o:o + size]
        w, h = struct.unpack_from('<II', c, 0x18)
        img = Image.open(paths.ASSETS / png).convert('RGBA')
        assert img.size == (w, h), (png, img.size, (w, h))
        pm = c.find(b' PIM', 0x58)
        psz = struct.unpack_from('<I', c, pm + 4)[0]
        if c[0x28:0x2A] == b'P8':
            pal, pix = texenc.encode_c8(img)
            pl = c.find(b' LAP', 0x58)
            assert len(pal) == struct.unpack_from('<I', c, pl + 4)[0] and len(pix) == psz
            d[o + pl + 8:o + pl + 8 + len(pal)] = pal
        else:
            pix = texenc.encode_cmpr(img)
            assert len(pix) == psz
        d[o + pm + 8:o + pm + 8 + psz] = pix
        _, back = tex.decode_chunk(bytes(d[o:o + size]))  # 다시 풀어 원본 PNG 와 비교
        ref = np.asarray(img, np.float32)
        err = np.abs(back.astype(np.float32) - ref)[ref[..., 3] > 0][:, :3].mean()
        assert err < 6, (png, err)
        print('  %-14s %s 평균 오차 %.2f' % (name.decode(), c[0x28:0x2C].rstrip(b'\0').decode(), err))
    for path, d in files.items():
        (OUT_DATA / path).parent.mkdir(parents=True, exist_ok=True)
        open(OUT_DATA / path, 'wb').write(d)
    build_banner()


BANNER = 'banner.png'   # tools/assets 에 있을 때만 디스크 배너(opening.bnr) 그림을 바꾼다


def build_banner():
    """opening.bnr: 0x20 부터 96x32 RGB5A3 그림(0x1800바이트). 문구는 Shift-JIS 전용이라 그대로 둔다."""
    src = paths.ASSETS / BANNER
    if not src.exists():
        return
    img = Image.open(src).convert('RGBA')
    assert img.size == (96, 32), (BANNER, img.size)
    d = bytearray(open(paths.JP / 'opening.bnr', 'rb').read())
    assert d[:4] == b'BNR1'
    pix = texenc.encode_rgb5a3(img)
    assert len(pix) == 0x1800
    d[0x20:0x20 + 0x1800] = pix
    open(OUT_DATA / 'opening.bnr', 'wb').write(d)
    print('  %-14s RGB5A3 배너 교체' % 'opening.bnr')


def verify(src_iso, out_iso):
    a, b = open(src_iso, 'rb'), open(out_iso, 'rb')
    _, _, _, ea = build_iso.read_fst(a)
    _, _, _, eb = build_iso.read_fst(b)
    bad = rep = 0
    for (_, p, o, s), (_, q, o2, s2) in zip(ea, eb):
        b.seek(o2)
        got = b.read(s2)
        r = OUT_DATA / p
        if r.is_file():
            exp = r.read_bytes(); rep += 1
        else:
            a.seek(o); exp = a.read(s)
        if got != exp or p != q:
            bad += 1
            print('  불일치', p)
    spans = sorted((o, o + s) for _, _, o, s in eb)
    overlap = sum(1 for x, y in zip(spans, spans[1:]) if x[1] > y[0])
    assert bad == 0 and overlap == 0, (bad, overlap)
    print('  파일 %d개 확인(교체 %d), 겹침 없음' % (len(eb), rep))


def main(out_iso):
    paths.ensure_jp()
    print('1) 번역 검사')
    ps = check_ko.check()
    if ps:
        for p in ps[:20]:
            print('  ', *p)
        sys.exit('번역 검사 실패 %d건 (python tools/check_ko.py)' % len(ps))
    shutil.rmtree(OUT_DATA, ignore_errors=True)
    print('2) 문자열·장면 폰트')
    rep = build_strings()
    print('  폰트 %d벌, 최대 %d자 %d장' % (len(rep), *max(rep.values())))
    print('3) 이미지')
    build_images()
    print('4) ISO 조립')
    src = paths.jp_iso()
    subprocess.run([sys.executable, str(paths.TOOLS / 'build_iso.py'), src, str(out_iso), '--repdir', str(OUT_DATA)], check=True)
    print('5) 검증')
    verify(src, out_iso)
    print('완료:', out_iso)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else paths.WORK / 'TotsugekiFamicomWars_KO.iso')
