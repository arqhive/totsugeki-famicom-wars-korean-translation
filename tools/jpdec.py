"""일본어 글자번호 → 글자 변환(판독표 사용).

판독표(tools/data, 커밋됨):
  review.json      같은 글자 모양 묶음 1,646개. 묶음마다 대표 모양과 구성 모양(md5)이 들어 있다.
  labels/NN.txt    묶음 순서대로 판독한 글자(시트당 120자, 줄바꿈 무시).
  fix_shape.json   한 묶음에 비슷한 글자가 섞인 경우의 개별 모양 교정(묶음 판독보다 우선).
모양 md5 는 work/shapes.pkl(collect_shapes.py 가 ISO 에서 만듦)로 폰트 칸과 이어진다.
"""
import glob
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths


def _load():
    pk = paths.WORK / 'shapes.pkl'
    if not pk.exists():
        import collect_shapes
        collect_shapes.collect()
    shapes, cells, known = pickle.load(open(pk, 'rb'))
    R = json.load(open(paths.DATA / 'review.json', encoding='utf-8'))
    fix = dict(known)
    for p in sorted(glob.glob(str(paths.DATA / 'labels' / '*.txt'))):
        n = int(os.path.basename(p)[:2])
        chars = [c for c in open(p, encoding='utf-8').read() if c not in '\r\n']
        assert len(chars) == min(120, len(R) - n * 120), p
        for j, ch in enumerate(chars):
            for m in R[n * 120 + j]['members']:
                fix[m] = ch
    fix.update(json.load(open(paths.DATA / 'fix_shape.json', encoding='utf-8')))
    rev = {(f, k): h for h, lst in shapes.items() for f, k in lst}
    return shapes, cells, fix, rev


shapes, cells, fix, rev = _load()


def glyph(font, code):
    k = ((code >> 8) - 0xB0) * 121 + (code & 0xFF) - 0x40
    h = rev.get((font, k))
    return fix.get(h, '□') if h else '□'


def _dec_raw(font, text):
    return ''.join(glyph(font, c) if 0xB000 <= c < 0xC000 else chr(c) for c in text)


# 모양이 같은 가타카나 ↔ 한자·히라가나 쌍: 앞뒤가 가타카나면 가타카나로 본다.
# 장음 ー(묶음 302)와 한자 一(묶음 303)는 모양이 달라 판독표에서 바로 구분된다.
KATA = {'ニ': '二', 'ロ': '口', 'エ': '工', 'カ': '力', 'タ': '夕', 'ハ': '八', 'ヘ': 'へ', 'ベ': 'べ', 'ペ': 'ぺ',
        'リ': 'り', 'ト': '卜', 'オ': '才'}
OTHER = {v: k for k, v in KATA.items()}
AMB = set(KATA) | set(OTHER)


def _is_kata(ch):
    return 'ァ' <= ch <= 'ヺ' or ch == 'ー'


def fix_context(s):
    out = list(s)
    n = len(out)
    for _ in range(4):  # 쌍 글자끼리 붙은 경우(才ースティン, 八ーマン)를 위해 반복
        for i, ch in enumerate(out):
            if ch not in AMB:
                continue
            kata = ch if ch in KATA else OTHER[ch]
            l = out[i - 1] if i else ''
            r = out[i + 1] if i + 1 < n else ''
            # 조사 へ 는 가타카나 뒤에도 오므로 ヘ 는 뒤가 가타카나일 때만(ヘリ)
            k = _is_kata(r) if kata == 'ヘ' else (_is_kata(l) or _is_kata(r))
            out[i] = kata if k else KATA[kata]
    return ''.join(out)


def dec(font, text):
    return fix_context(_dec_raw(font, text))
