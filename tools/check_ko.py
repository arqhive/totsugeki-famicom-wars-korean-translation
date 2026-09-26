"""번역 검사: 줄 폭, 줄 수, 한자·가나 혼입, 문장부호 규칙.

줄 폭 한계(게임 폰트 폭 기준, 한글 18px, 영문 포함 폰트의 영숫자·공백은 원본 폭, 스토리 폰트의 공백 8px):
  무전 대사(미션·공통의 화자 있는 항목) 346px, 3줄 — 일본어 무전 2,356줄이 340~346px에 몰리고 그 이상이 없다.
  미션의 화자 없는 항목(목표 등) 410px, 스토리 자막 574px, 메뉴 557px(유닛 설명 패널) — 일본어 원문 최대 폭.
문장부호: 물결표 금지, 말줄임표 뒤 마침표 금지(「….」가 「... .」로 떨어져 보임).
사용: python tools/check_ko.py      (문제가 있으면 목록을 출력하고 종료 코드 1)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_text
import kolib
import paths
import strfile

RADIO, MISSION, STORY, MENU = 346, 410, 574, 557
_W = {}


def wdf(font):
    if font not in _W:
        _W[font] = open(paths.JP_DATA / 'font' / f'{font}.wdf', 'rb').read()
    return _W[font]


def line_widths(font, text, ascii_ok):
    w = wdf(font)
    out = []
    for line in text.split('\n'):
        t = 0
        for ch in line:
            if ascii_ok and 0x20 <= ord(ch) < 0x7F:  # 영문 포함 폰트는 공백도 원본 ASCII 칸
                t += w[ord(ch) - 0x20]
            elif ch == ' ':
                t += 8
            else:
                t += 18
        out.append(t)
    return out


def check():
    paths.ensure_jp()
    ascii_fonts = set(build_text.ascii_fonts())
    problems = []
    for fname, items in kolib.load_all().items():
        font = build_text.font_of(fname) or 'frontend_0'
        ents = strfile.load(paths.JP_DATA / 'Strings' / fname)['ents']
        scene = kolib.scene_of(fname)
        story = font not in ascii_fonts
        for i, ko in items.items():
            e = ents[i]
            where = f'{scene}#{i:03d}'
            speaker = bool(e['voice_dir'])
            if story:
                lim, maxl = STORY, None
            elif speaker:
                lim, maxl = RADIO, 3
            elif scene.startswith(('frontend', 'glob')):
                lim, maxl = MENU, None
            else:
                lim, maxl = MISSION, None
            ws = line_widths(font, ko, font in ascii_fonts)
            if max(ws) > lim:
                problems.append((where, f'줄 폭 {max(ws)}px > {lim}px', ko))
            if maxl and ko.rstrip('\n').count('\n') + 1 > maxl:
                problems.append((where, f'줄 수 {ko.rstrip(chr(10)).count(chr(10)) + 1} > {maxl}', ko))
            if not ko.strip():
                problems.append((where, '빈 번역', ko))
            if re.search(r'[぀-ヿ一-鿿]', ko):
                problems.append((where, '한자·가나 혼입', ko))
            if re.search(r'[~〜～]', ko):
                problems.append((where, '물결표', ko))
            if re.search(r'…\.', ko):
                problems.append((where, '말줄임표 뒤 마침표', ko))
            if not e['text']:
                problems.append((where, '원본에서 빈 항목에 번역이 들어감', ko))
    return problems


if __name__ == '__main__':
    ps = check()
    for where, what, ko in ps:
        print(f'{where}\t{what}\t{ko[:60]!r}')
    print('문제 %d건' % len(ps))
    sys.exit(1 if ps else 0)
