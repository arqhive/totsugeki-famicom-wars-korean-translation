"""translation/ko/*.json 읽기·쓰기.

파일 하나 = 게임 문자열 파일 하나(Data/Strings/<file>).
  {"file": "c1_OnPatrolJapanese.str", "scene": "c1_OnPatrol",
   "entries": [{"index": 12, "speaker": "Betty", "ko": "..."}, ...]}
index 는 .str 항목 번호, speaker 는 미션 음성 폴더 기준 화자(없으면 생략). 원문은 넣지 않는다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths


def scene_of(fname):
    if fname == 'globjap.str':
        return 'glob'
    return fname.replace('_Japanese.str', '').replace('Japanese.str', '')


def load_all():
    """→ {str 파일명: {index: ko}}"""
    out = {}
    for p in sorted(paths.KO.glob('*.json')):
        d = json.load(open(p, encoding='utf-8'))
        out[d['file']] = {e['index']: e['ko'] for e in d['entries']}
    return out


def save_from_entries(entries):
    """번역 전량 JSON 의 entries(id, file, index, speaker, ko) → translation/ko/<scene>.json"""
    paths.KO.mkdir(parents=True, exist_ok=True)
    by = {}
    for x in entries:
        by.setdefault(x['file'], []).append(x)
    for f, xs in by.items():
        ents = []
        for x in sorted(xs, key=lambda x: x['index']):
            e = {'index': x['index']}
            if x.get('speaker'):
                e['speaker'] = x['speaker']
            e['ko'] = x['ko']
            ents.append(e)
        d = {'file': f, 'scene': scene_of(f), 'entries': ents}
        with open(paths.KO / (scene_of(f) + '.json'), 'w', encoding='utf-8', newline='\n') as fp:
            json.dump(d, fp, ensure_ascii=False, indent=1)
            fp.write('\n')
    return len(by)
