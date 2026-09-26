# 저장소 안팎 경로 (어느 폴더에서 실행해도 같게 동작)
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / 'tools'
DATA = TOOLS / 'data'                 # 일본어 판독표(글자 모양 묶음·판독 결과)
ASSETS = TOOLS / 'assets'             # 한글화 이미지
TRANS = ROOT / 'translation'
KO = TRANS / 'ko'                     # 번역 JSON
RELEASE = ROOT / 'release'
DOCS = ROOT / 'docs'
WORK = ROOT / 'work'                  # 빌드 결과·원문 등 커밋하지 않는 작업 폴더
JP = WORK / 'jp'                      # 일본판 ISO 추출본
JP_DATA = JP / 'Data'
NA_STRINGS = WORK / 'na_strings'      # (선택) 북미판 Data/Strings, 원문 내보내기 참고용
ISO_NAME = 'Totsugeki!! Famicom Wars (Japan).iso'


def jp_iso():
    p = os.environ.get('BW_JP_ISO')
    if p:
        return str(p)
    for d in (ROOT, ROOT / 'iso', ROOT.parent):
        if (d / ISO_NAME).exists():
            return str(d / ISO_NAME)
    raise FileNotFoundError('%s 를 찾을 수 없습니다 (환경 변수 BW_JP_ISO 로 지정하세요)' % ISO_NAME)


def ensure_jp():
    """work/jp 가 없으면 일본판 ISO 에서 추출한다."""
    if not (JP_DATA / 'Strings').exists():
        import dump
        dump.main(jp_iso(), str(JP))
    return JP_DATA
