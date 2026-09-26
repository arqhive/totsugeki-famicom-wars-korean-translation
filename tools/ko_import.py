"""번역 전량 JSON(export_text.py 형식에 ko 를 채운 것)을 translation/ko/ 로 가져온다.
사용: python tools/ko_import.py <번역 전량.json>
same_as 가 있는 항목은 대표 항목과 번역이 다르면 멈춘다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kolib

if __name__ == '__main__':
    d = json.load(open(sys.argv[1], encoding='utf-8'))
    E = d['entries'] if isinstance(d, dict) else d
    by = {x['id']: x for x in E}
    bad = [x['id'] for x in E if x.get('same_as') and x['ko'] != by[x['same_as']]['ko']]
    if bad:
        sys.exit('same_as 번역 불일치: %s' % ', '.join(bad[:10]))
    empty = [x['id'] for x in E if not x.get('ko')]
    if empty:
        sys.exit('ko 가 빈 항목: %s' % ', '.join(empty[:10]))
    n = kolib.save_from_entries(E)
    print('translation/ko 파일 %d개, 항목 %d개' % (n, len(E)))
