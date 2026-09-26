"""한글 글자 렌더(원본 스타일 재현판).
4배 해상도에서: 글자 채움(흰색) + 둥근 1px 테두리(검정) + 테두리를 아래로 2px 내린 그림자(검정)를 합성하고,
22x22 로 줄인 뒤 원본 팔레트(16색, 반투명 포함)에서 가장 가까운 색으로 바꾼다."""
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SS = 4
FONT = 'C:/Windows/Fonts/malgun.ttf'
SIZE = 17
OUT_R = 1.15      # 테두리 반지름(px)
SHADOW_DY = 2     # 그림자 아래 이동(px)
MAX_FILL_W = 16   # 흰 채움 최대 폭(px) 안전장치: 넘는 글자만 가로로 눌러 글자 간격 18 안에 넣는다
_font = None
_off = None
_pal = None


def set_palette(pal_bytes):
    """btf 팔레트 32바이트(RGB5A3 BE) → 비교용 premultiplied RGBA"""
    global _pal
    out = []
    for i in range(16):
        v = struct.unpack('>H', pal_bytes[i * 2:i * 2 + 2])[0]
        if v & 0x8000:
            r, g, b, a = (v >> 10 & 31) * 255 / 31, (v >> 5 & 31) * 255 / 31, (v & 31) * 255 / 31, 255
        else:
            r, g, b, a = (v >> 8 & 15) * 17, (v >> 4 & 15) * 17, (v & 15) * 17, (v >> 12 & 7) * 255 / 7
        out.append((r * a / 255, g * a / 255, b * a / 255, a))
    _pal = np.array(out, np.float32)


def _font_and_offset():
    global _font, _off
    if _font is None:
        _font = ImageFont.truetype(FONT, SIZE * SS)
        # 기준 글자 '국'의 잉크 위끝을 4행, 왼끝을 1열에 맞춘다(원본 일본어와 같은 위치)
        img = Image.new('L', (40 * SS, 40 * SS), 0)
        ImageDraw.Draw(img).text((8 * SS, 8 * SS), '국', fill=255, font=_font)
        ys, xs = np.where(np.asarray(img) > 50)
        _off = (8 * SS + 1 * SS - xs.min(), 8 * SS + 4 * SS - ys.min())
    return _font, _off


def _disk_dilate(a, r):
    """회색조 원형 팽창(최댓값 필터). 가장자리는 0으로 채워 넘겨 붙지 않게 한다."""
    k = int(np.ceil(r))
    pad = np.pad(a, k)
    h, w = a.shape
    out = a.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            if dx * dx + dy * dy <= r * r:
                out = np.maximum(out, pad[k + dy:k + dy + h, k + dx:k + dx + w])
    return out


def render(ch):
    """→ (22x22 팔레트 번호, 폭)
    채움: 22x22 에서 덮임 ≥0.45 → 흰색(11), 0.25~0.45 → 회색(15)
    테두리·그림자: 4배에서 원형 팽창 후 줄인 덮임 ≥0.5 → 검정(4), 0.25~0.5 → 반투명(3), 0.1~0.25 → 옅은 반투명(1)"""
    font, (ox, oy) = _font_and_offset()
    n = 22 * SS
    img = Image.new('L', (n, n), 0)
    ImageDraw.Draw(img).text((ox, oy), ch, fill=255, font=font)
    hi = np.asarray(img, np.float32) / 255
    # 가로로 넓은 글자(과·화·웨 등)는 흰 채움 폭이 MAX_FILL_W 를 넘지 않게 왼쪽 기준으로 가로만 눌러 준다
    xs = np.where(hi.max(0) > 0.2)[0]
    if len(xs):
        x0, x1 = xs.min(), xs.max() + 1
        lim = MAX_FILL_W * SS
        if x1 - x0 > lim:
            part = Image.fromarray((hi[:, x0:x1] * 255).astype(np.uint8)).resize((lim, n), Image.LANCZOS)
            hi = np.zeros_like(hi)
            hi[:, x0:x0 + lim] = np.asarray(part, np.float32) / 255
    outline_hi = _disk_dilate(hi, OUT_R * SS)
    small = lambda x: np.asarray(Image.fromarray(x.astype(np.float32), 'F').resize((22, 22), Image.BOX), np.float32)
    fill = small(hi)
    out = small(outline_hi)
    sh = np.zeros_like(out); sh[SHADOW_DY:] = out[:-SHADOW_DY]
    black = np.maximum(out, sh)
    idx = np.zeros((22, 22), np.uint8)
    idx[black >= 0.1] = 1
    idx[black >= 0.25] = 3
    idx[black >= 0.5] = 4
    idx[fill >= 0.25] = 15
    idx[fill >= 0.45] = 11
    return idx, 18
