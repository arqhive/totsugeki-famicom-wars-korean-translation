# 배포용 xdelta 패치 생성: 한글 ISO 빌드 → xdelta3 패치 → 적용해서 결과 검증
#   python tools/make_patch.py [버전]        (기본 0.1.1)
# xdelta3 실행 파일은 PATH 에 있거나, 환경 변수 XDELTA3 또는 work/xdelta3.exe 로 둡니다.
import hashlib
import os
import shutil
import subprocess
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

VER = sys.argv[1] if len(sys.argv) > 1 else '0.1.1'
ISO = paths.WORK / 'TotsugekiFamicomWars_KO.iso'
PATCH = paths.RELEASE / ('G8WJ_KPatch_v%s.xdelta' % VER)  # 릴리즈 첨부 이름 규칙 [게임 코드]_KPatch_[버전]


def xdelta3():
    p = os.environ.get('XDELTA3') or shutil.which('xdelta3') or shutil.which('xdelta3.exe')
    if not p and (paths.WORK / 'xdelta3.exe').exists():
        p = str(paths.WORK / 'xdelta3.exe')
    if not p:
        sys.exit('xdelta3 을 찾을 수 없습니다. PATH 에 두거나 환경 변수 XDELTA3 로 지정하세요.\n'
                 '  https://github.com/jmacd/xdelta-gpl/releases')
    return p


def digest(path):
    md5, sha1, sha256, crc = hashlib.md5(), hashlib.sha1(), hashlib.sha256(), 0
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            md5.update(b); sha1.update(b); sha256.update(b); crc = zlib.crc32(b, crc)
    return '%08X' % (crc & 0xFFFFFFFF), md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()


def run(*cmd):
    if subprocess.run(cmd).returncode:
        sys.exit('실패: %s' % ' '.join(map(str, cmd)))


if __name__ == '__main__':
    paths.WORK.mkdir(exist_ok=True); paths.RELEASE.mkdir(exist_ok=True)
    run(sys.executable, str(paths.TOOLS / 'build.py'), str(ISO))
    xd, jp = xdelta3(), paths.jp_iso()
    run(xd, '-f', '-e', '-9', '-B', '1073741824', '-s', jp, str(ISO), str(PATCH))
    check = paths.WORK / 'patched_check.iso'
    run(xd, '-f', '-d', '-s', jp, str(PATCH), str(check))
    a, b = digest(ISO), digest(check)
    assert a == b, '패치 적용 결과가 빌드 결과와 다릅니다'
    os.remove(check)
    print('\n패치: %s (%.2f MB)' % (PATCH, PATCH.stat().st_size / 1e6))
    print('원본 ISO  CRC32 %s / MD5 %s / SHA1 %s / SHA256 %s' % digest(jp))
    print('적용 결과 CRC32 %s / MD5 %s / SHA1 %s / SHA256 %s' % a)
