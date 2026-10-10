"""GPT 가 다시 그린 그림을 게임용 크기로 맞춰 tools/assets 에 넣고 비교 시트를 만든다.

  work/GPT/결과/<저장할 이름>.png  →  tools/assets/<asset>.png  (바꾸기 전 파일은 work/GPT/이전_assets/ 에 보관)
  비교 시트: work/GPT/비교/<저장할 이름>.png (원본 | 현재 | GPT 반영, 게임 텍스처로 변환했다 푼 모양)

맞추는 방식(결과가 이미 게임 크기와 같으면 그대로 쓴다)
  fit=ink   로고·배너: GPT 그림의 잉크(불투명) 덩어리를 원본 잉크 상자 안에 비율 유지로 넣고 가운데 정렬.
  fit=frame 경고 화면·버튼 안내: 그림 전체를 원본 크기로 줄인다(검정 바탕, 불투명).
사용: python tools/gpt_import.py            결과 폴더에 있는 것 전부
      python tools/gpt_import.py 01 04      이름이 01·04 로 시작하는 것만
"""
import os
import re
import shutil
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import tex
import texenc

GPT = paths.WORK / 'GPT'
# 저장할 이름, asset 파일, (게임 파일, 텍스처 이름 또는 None=배너), 맞추는 방식
JOBS = [
    ('01_타이틀로고', 'BWTitleLogoJp.png', ('Data/CompoundFiles/frontend_0_Level.res', b'BWTitleLogoJp'), 'ink'),
    ('02_건강안전경고', 'warningJap.png', ('Data/Startup/WarningJap.btf', b'warningJap'), 'frame'),
    ('03_버튼안내', 'pstartJap.png', ('Data/Startup/WarningJap.btf', b'pstartJap'), 'frame'),
    ('04_디스크배너', 'banner.png', ('opening.bnr', None), 'ink'),
]


def _chunk(path, name):
    d = open(paths.JP / path, 'rb').read()
    o = next(m.start() for m in re.finditer(rb'TXET', d) if d[m.start() + 8:m.start() + 9 + len(name)] == name + b'\0')
    return d[o:o + struct.unpack_from('<I', d, o + 4)[0] + 8]


def original(src):
    """→ (원본 RGBA 배열, 게임 왕복 함수)"""
    path, name = src
    if name is None:
        b = open(paths.JP / path, 'rb').read()
        v = np.frombuffer(b[0x20:0x20 + 0x1800], '>u2')
        orig = tex.rgb5a3(v).reshape(8, 24, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(32, 96, 4)

        def game(img):
            v2 = np.frombuffer(texenc.encode_rgb5a3(img), '>u2')
            return tex.rgb5a3(v2).reshape(8, 24, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(32, 96, 4)
        return orig, game
    c = _chunk(path, name)
    _, orig = tex.decode_chunk(c)

    def game(img):
        cc = bytearray(c)
        pm = cc.find(b' PIM', 0x58); psz = struct.unpack_from('<I', cc, pm + 4)[0]
        if cc[0x28:0x2A] == b'P8':
            pal, pix = texenc.encode_c8(img); pl = cc.find(b' LAP', 0x58); cc[pl + 8:pl + 8 + len(pal)] = pal
        else:
            pix = texenc.encode_cmpr(img)
        cc[pm + 8:pm + 8 + psz] = pix
        return tex.decode_chunk(bytes(cc))[1]
    return orig, game


def _premul_resize(im, size):
    a = np.asarray(im.convert('RGBA'), np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    ch = [Image.fromarray(a[..., i], 'F').resize(size, Image.LANCZOS) for i in range(4)]
    r = np.stack([np.asarray(c, np.float32) for c in ch], -1).clip(0, 1)
    r[..., :3] = np.where(r[..., 3:4] > 1e-4, r[..., :3] / np.maximum(r[..., 3:4], 1e-4), 0)
    return Image.fromarray((r * 255 + .5).clip(0, 255).astype(np.uint8), 'RGBA')


def _bbox(alpha, thr):
    ys, xs = np.where(alpha > thr)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def fit(gpt, orig, mode):
    h, w = orig.shape[:2]
    if gpt.size == (w, h):  # 이미 게임 크기로 맞춘 그림은 배치를 건드리지 않고 그대로 쓴다
        if mode == 'frame':
            bg = Image.new('RGBA', gpt.size, (0, 0, 0, 255))
            bg.alpha_composite(gpt.convert('RGBA'))
            return bg
        return gpt.convert('RGBA')
    if mode == 'frame':
        bg = Image.new('RGBA', gpt.size, (0, 0, 0, 255))
        bg.alpha_composite(gpt.convert('RGBA'))
        return bg.resize((w, h), Image.LANCZOS)
    g = np.asarray(gpt.convert('RGBA'))
    gx0, gy0, gx1, gy1 = _bbox(g[..., 3], 16)
    ink = gpt.convert('RGBA').crop((gx0, gy0, gx1, gy1))
    ox0, oy0, ox1, oy1 = _bbox(orig[..., 3], 16)
    bw, bh = ox1 - ox0, oy1 - oy0
    s = min(bw / ink.width, bh / ink.height)
    nw, nh = max(1, round(ink.width * s)), max(1, round(ink.height * s))
    small = _premul_resize(ink, (nw, nh))
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(small, (ox0 + (bw - nw) // 2, oy0 + (bh - nh) // 2))
    return out


def sheet(name, orig, cur, new, scale):
    font = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 16)
    h, w = orig.shape[:2]
    W, H = w * scale, h * scale
    out = Image.new('RGBA', (W * 3 + 40, H + 40), (60, 90, 60, 255))
    d = ImageDraw.Draw(out)
    for i, (lab, a) in enumerate((('원본', orig), ('현재', cur), ('GPT 반영', new))):
        x = 10 + i * (W + 10)
        d.text((x, 8), lab, fill=(255, 255, 210), font=font)
        out.alpha_composite(Image.fromarray(a, 'RGBA').resize((W, H), Image.NEAREST), (x, 32))
    (GPT / '비교').mkdir(parents=True, exist_ok=True)
    out.convert('RGB').save(GPT / '비교' / f'{name}.png')


def main(prefixes):
    done = 0
    for name, asset, src, mode in JOBS:
        if prefixes and not any(name.startswith(p) for p in prefixes):
            continue
        res = GPT / '결과' / f'{name}.png'
        if not res.exists():
            print('  없음  %s' % res.name)
            continue
        orig, game = original(src)
        gpt = Image.open(res)
        rh, rw = orig.shape[:2]
        ratio_o, ratio_g = rw / rh, gpt.width / gpt.height
        if abs(ratio_g / ratio_o - 1) > 0.03:
            print('  주의  %s 비율 %.2f (원본 %.2f)' % (res.name, ratio_g, ratio_o))
        new = fit(gpt, orig, mode)
        cur_path = paths.ASSETS / asset
        cur = game(Image.open(cur_path).convert('RGBA')) if cur_path.exists() else orig
        if cur_path.exists():
            (GPT / '이전_assets').mkdir(parents=True, exist_ok=True)
            shutil.copy2(cur_path, GPT / '이전_assets' / asset)
        new.save(cur_path)
        sheet(name, orig, cur, game(new), 4 if rw <= 128 else 1)
        print('  반영  %s → tools/assets/%s (%dx%d)' % (res.name, asset, rw, rh))
        done += 1
    print('반영 %d장. 비교 시트: %s' % (done, GPT / '비교'))


if __name__ == '__main__':
    main(sys.argv[1:])
