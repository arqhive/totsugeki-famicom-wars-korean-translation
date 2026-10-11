"""한글 오프닝 로고 무비(Data/Video/BW_Title_JP.h4m) 만들기.
1) 원본 무비를 HVQM4 디코더(work/bin/h4m_dec.exe, Tilka/hvqm4)로 work/movie/jp/output 에 푼다(처음 한 번).
2) gen.py 로 한글 장면 97장을 그린다(work/movie/ko).
3) h4m.py 로 묶어 work/movie/out/Data/Video/BW_Title_JP.h4m 에 쓴다.
사용: python tools/movie/make_title.py
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import h4m  # noqa: E402
import parts  # noqa: E402
import paths  # noqa: E402

NAME = 'BW_Title_JP.h4m'
FRAMES = 97
OUT = parts.MOVIE / 'out' / 'Data' / 'Video' / NAME
DECODER = paths.WORK / 'bin' / 'h4m_dec.exe'


def decode_original():
    if (parts.JP_FRAMES / f'video_rgb_{FRAMES - 1}.ppm').exists():
        return
    if not DECODER.exists():
        sys.exit('HVQM4 디코더가 없습니다: %s (Tilka/hvqm4 를 -DNATIVE=1 로 컴파일)' % DECODER)
    os.makedirs(parts.JP_FRAMES, exist_ok=True)
    src = paths.ensure_jp() / 'Video' / NAME
    subprocess.run([str(DECODER), str(src), os.devnull], cwd=str(parts.JP_FRAMES.parent), check=True,
                   stdout=subprocess.DEVNULL)


def main():
    decode_original()
    import gen  # 원본 장면이 있어야 불러올 수 있다
    frames = []
    for t in range(FRAMES):
        rgb = gen.frame(t)
        frames.append(gen.to_yuv(rgb.astype(np.uint8).astype(np.float32)))
        print(t, end=' ', flush=True)
    os.makedirs(OUT.parent, exist_ok=True)
    size, mx = h4m.write_h4m(str(OUT), frames)
    print('\n%s %d바이트(가장 큰 장 %d)' % (OUT, size, mx))


if __name__ == '__main__':
    main()
