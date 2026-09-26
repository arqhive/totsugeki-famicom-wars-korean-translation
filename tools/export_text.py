"""번역용 텍스트 전량 JSON 내보내기 → work/BW1_텍스트_전량.json

일본판 ISO(work/jp)에서 원문을 판독하고, translation/ko 의 번역을 ko 로 붙인다.
항목: id, file, index, category(메뉴·공통/미션/스토리), scene, speaker(영문 키), speaker_ja, voice,
      ja(일본어 원문, 줄바꿈 \\n), ko(번역), en(일본판 디스크 영어), en_na(북미 최종판 영어, 다를 때만), same_as
빈 항목·일본판에서 쓰지 않는 파일(1.1_*, fmvsubtitles, loading_screen, AttractMode, starjap)은 뺀다.
북미판 영어는 work/na_strings(북미판 Data/Strings)가 있을 때만 붙인다.
사용: python tools/export_text.py [출력 경로]
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_text
import jpdec
import kolib
import paths
import strfile

SPEAKER_JA = {'Betty': 'ベティー准将', 'Austin': 'オースティン大佐', 'Herman': 'ハーマン将軍', 'Vlad': 'ブラッド皇帝',
              'Nova': 'ノバ元帥', 'Ingrid': 'イングリッド', 'Leiqo': 'レイ＝クォ女帝', 'Ubel': 'ウーベル司令官',
              'Nelly': 'ネリー少佐', 'Gorgi': 'ゴルギ大帝'}
STORY_ORDER = ['1_1_NewsDrill', '1_2_StaleMate', '1_3_DealDevil', '1_4_Betrayal', '2_1_EnemyRevealed',
               '2_2_GorgiIsSlain', '3_1_NewFront', '3_2_HistoryLes', '3_3_NewAlly', '4_1_TheDead', '4_2_ShowDown',
               '4_3_TheEnd', '4_3_TheEnd_JP']


def files():
    """(str 파일명, 폰트, 분류, 장면) — 메뉴·공통 → 스토리 → 미션(캠페인 순)"""
    out = [('globjap.str', 'frontend_0', '메뉴·공통', 'glob'),
           ('frontend_0Japanese.str', 'frontend_0', '메뉴·공통', 'frontend_0'),
           ('frontend_1Japanese.str', 'frontend_1', '메뉴·공통', 'frontend_1')]
    for s in STORY_ORDER:
        out.append((f'{s}_Japanese.str', s, '스토리', s))
    missions = []
    for p in glob.glob(str(paths.JP_DATA / 'Strings' / '*Japanese.str')):
        b = os.path.basename(p)
        f = build_text.font_of(b)
        if f and f in build_text.ascii_fonts() and not f.startswith('frontend'):
            missions.append((b, f, '미션', kolib.scene_of(b)))
    missions.sort(key=lambda x: (x[3][1], x[3].lower()))
    return out + missions


def en_name(jp_name):
    return jp_name.replace('Japanese', 'English').replace('globjap', 'globeng')


def _en(e):
    return ''.join(map(chr, e['text'])) if e and e['text'] else ''


def _load_opt(path):
    return strfile.load(path)['ents'] if os.path.exists(path) else None


def export():
    paths.ensure_jp()
    ko = kolib.load_all()
    S = paths.JP_DATA / 'Strings'
    entries, seen = [], {}
    for sname, font, cat, scene in files():
        J = strfile.load(S / sname)['ents']
        E = _load_opt(S / en_name(sname))
        N = _load_opt(paths.NA_STRINGS / en_name(sname))
        for i, e in enumerate(J):
            if not e['text']:
                continue
            ja = jpdec.dec(font, e['text'])
            vd = e['voice_dir'].decode()
            sp = vd.split('/')[-1] if vd else None
            en = _en(E[i]) if E and i < len(E) else ''
            item = {'id': f'{scene}#{i:03d}', 'file': sname, 'index': i, 'category': cat, 'scene': scene,
                    'speaker': sp, 'speaker_ja': SPEAKER_JA.get(sp) if sp else None,
                    'voice': e['voice_id'].decode() or None, 'ja': ja}
            if sname in ko and i in ko[sname]:
                item['ko'] = ko[sname][i]
            item['en'] = en
            if N and i < len(N):
                na = _en(N[i])
                if na and na != en:
                    item['en_na'] = na
            key = (cat, ja)
            if key in seen:
                item['same_as'] = seen[key]
            else:
                seen[key] = item['id']
            entries.append(item)
    return {
        'game': '突撃!! ファミコンウォーズ (GameCube, G8WJ01)',
        'note': ('ja 는 일본판 게임 폰트에서 판독한 원문. 줄바꿈은 \\n(게임 화면 줄바꿈). '
                 'speaker 는 미션 음성 파일 폴더 기준(스토리 자막·메뉴는 없음). '
                 'same_as 가 있는 항목은 같은 분류 안에서 원문이 완전히 같은 항목(번역도 같게). '
                 'en 은 일본판 디스크에 든 영어, en_na 는 북미 최종판 영어가 다를 때만 표기.'),
        'speakers': SPEAKER_JA,
        'count': len(entries),
        'entries': entries,
    }


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else str(paths.WORK / 'BW1_텍스트_전량.json')
    d = export()
    json.dump(d, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    uniq = [x for x in d['entries'] if 'same_as' not in x]
    print('%s: 항목 %d, 고유 %d' % (out, d['count'], len(uniq)))
