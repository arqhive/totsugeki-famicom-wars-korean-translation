"""한국어 문장 → .str + 장면별 폰트(.btf/.wdf) 생성.

kor: {str파일명: [항목별 문장 또는 None(원문 유지)]}
장면 폰트 규칙(일본판과 동일):
  - 영문 포함 폰트(미션·메뉴): 칸 0~95 = 원본 ASCII 그대로, 96~ = 공통(globjap) 글자, 그 뒤 = 장면 글자
  - 스토리 폰트(1_1_* 등): 칸 0~ = 장면 글자만(공백도 글자 칸으로 넣는다)
  - 글자번호: 상위 바이트 0xB0+시트(칸//121), 하위 바이트 0x40+칸%121
  - 영문 포함 폰트에서 ASCII(0x20~0x7E)는 원래 코드 그대로 쓴다(게임이 상위바이트 0 을 ASCII 칸으로 처리)
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import btfw
import korglyph
import paths
import strfile

SRC = str(paths.JP_DATA)
ESC = glob.escape(SRC)  # 폴더 이름의 [GC] 같은 대괄호를 glob 패턴으로 보지 않게
UNUSED = {'loading_screen', 'fmvsubtitles', 'AttractMode'}  # 일본판에서 쓰지 않는 폰트
GLOB = 'globjap.str'


def _fonts_by_lower():
    return {os.path.basename(p)[:-4].lower(): os.path.basename(p)[:-4]
            for p in glob.glob(f'{ESC}/font/*.wdf') if os.path.getsize(p)}


def _strs_by_lower():
    return {os.path.basename(p).lower(): os.path.basename(p) for p in glob.glob(f'{ESC}/Strings/*.str')}


def font_of(strname):
    """문자열 파일 → 폰트 이름(대소문자 무시, 실제 파일명 반환)"""
    b = strname.replace('_Japanese.str', '').replace('Japanese.str', '')
    f = _fonts_by_lower().get(b.lower())
    return None if f in UNUSED else f


def str_of(font):
    """폰트 이름 → 일본어 문자열 파일(실제 파일명) 또는 None"""
    m = _strs_by_lower()
    return m.get(f'{font}_japanese.str'.lower()) or m.get(f'{font}japanese.str'.lower())


def ascii_fonts():
    out = []
    for p in glob.glob(f'{ESC}/font/*.wdf'):
        n = os.path.basename(p)[:-4]
        if n not in ('loading_screen', 'fmvsubtitles') and os.path.getsize(p) > 600:
            out.append(n)
    return sorted(out)


def code_of(k):
    return 0xB000 | ((k // 121) << 8) | (0x40 + k % 121)


def encode(text, table, ascii_ok):
    out = []
    for ch in text:
        if ch == '\n':
            out.append(10)
        elif ascii_ok and 0x20 <= ord(ch) < 0x7F:
            out.append(ord(ch))
        else:
            out.append(code_of(table[ch]))
    return out


def chars_needed(texts, ascii_ok):
    seen = []
    for t in texts:
        for ch in t:
            if ch == '\n' or (ascii_ok and 0x20 <= ord(ch) < 0x7F):
                continue
            if ch not in seen:
                seen.append(ch)
    return seen


def make_font(name, glyph_chars, out_dir, ascii_ok):
    """glyph_chars: 칸 96(또는 0)부터 채울 글자 목록 → .btf/.wdf 저장, {글자: 칸} 반환"""
    orig = btfw.load(f'{SRC}/font/{name}.btf')
    ow = open(f'{SRC}/font/{name}.wdf', 'rb').read()
    start = 96 if ascii_ok else 0
    total = start + len(glyph_chars)
    nsheets = (total + 120) // 121
    tmpl = orig['texs'][0]
    korglyph.set_palette(tmpl['pal'])
    base = tmpl['name'][:-1]
    texs = []
    for s in range(nsheets):
        texs.append(dict(head=tmpl['head'], name=f'{base}{s}', pal=tmpl['pal'], idx=np.zeros((256, 256), np.uint8)))
    widths = bytearray()
    table = {}
    for k in range(total):
        s, c = divmod(k, 121); r, col = divmod(c, 11)
        dst = texs[s]['idx'][r * 22:r * 22 + 22, col * 22:col * 22 + 22]
        if k < start:  # 원본 ASCII 칸 복사
            dst[:] = orig['texs'][0]['idx'][r * 22:r * 22 + 22, col * 22:col * 22 + 22]
            widths.append(ow[k])
        else:
            ch = glyph_chars[k - start]
            if ch == ' ' or ch == '　':
                widths.append(8 if ch == ' ' else 18)
            else:
                g, w = korglyph.render(ch)
                dst[:] = g
                if not (0xAC00 <= ord(ch) <= 0xD7A3) and ch not in '…—':
                    xs = np.where((g > 0).any(0))[0]  # 기호·영숫자는 실제 잉크 폭 + 1 을 글자 간격으로
                    w = min(18, max(6, int(xs.max()) + 2)) if len(xs) else 8
                widths.append(w)
            table[ch] = k
    os.makedirs(out_dir, exist_ok=True)
    btfw.save(dict(hdr=orig['hdr'], texs=texs), f'{out_dir}/{name}.btf')
    open(f'{out_dir}/{name}.wdf', 'wb').write(bytes(widths))
    return table, nsheets


def build(kor, out_root):
    """out_root/Data/Strings, out_root/Data/font 에 결과 저장. 장면별 (글자 수, 시트 수) 반환"""
    def texts_of(sname):
        return [t for t in kor.get(sname, []) if t]

    glob_chars = chars_needed(texts_of(GLOB), True)
    report = {}
    tables = {}
    for name in ascii_fonts():
        sname = str_of(name)
        extra = [c for c in chars_needed(texts_of(sname), True) if c not in glob_chars] if sname else []
        tables[name], ns = make_font(name, glob_chars + extra, f'{out_root}/Data/font', True)
        report[name] = (96 + len(glob_chars) + len(extra), ns)
        if sname:
            write_str(sname, kor[sname], tables[name], True, out_root)
    # 공통 문자열: 모든 영문 포함 폰트에서 같은 칸이므로 아무 표나 사용
    any_tab = tables[ascii_fonts()[0]]
    write_str(GLOB, kor[GLOB], any_tab, True, out_root)
    # 스토리
    for p in sorted(glob.glob(f'{ESC}/Strings/*_Japanese.str')):
        sname = os.path.basename(p)
        name = font_of(sname)
        if not name or name in tables or sname not in kor:
            continue
        chars = chars_needed(texts_of(sname), False)
        tab, ns = make_font(name, chars, f'{out_root}/Data/font', False)
        report[name] = (len(chars), ns)
        write_str(sname, kor[sname], tab, False, out_root)
    return report


def write_str(sname, texts, table, ascii_ok, out_root):
    s = strfile.load(f'{SRC}/Strings/{sname}')
    for e, t in zip(s['ents'], texts):
        if t is not None:
            e['text'] = encode(t, table, ascii_ok)
    os.makedirs(f'{out_root}/Data/Strings', exist_ok=True)
    open(f'{out_root}/Data/Strings/{sname}', 'wb').write(strfile.build(s))
