"""Kuju .str 문자열 파일 읽기/쓰기.

구조(리틀 엔디언):
  헤더 16바이트: magic 0x0005A177, 항목 수, 파일 전체 크기, 0
  항목 0x38바이트 x N:
    +00 색(0x007F7F7F)  +04 음성폴더 오프셋  +08 음성ID 오프셋  +0C 예비 오프셋
    +10 ?  +14 float 표시 시간  +18 ?  +1C 본문 오프셋  +20~ 나머지(원본 그대로 보존)
  본문 영역: 항목 순서대로 [음성폴더(ASCII) 음성ID(ASCII) 예비(ASCII) 본문(UTF-16/글자번호)],
            각각 0 종료 후 4바이트 정렬(0으로 채움).
본문은 u16 목록으로 다룬다(일본어는 0xBsCC 글자번호, 그 밖은 UTF-16 코드).
loading_screen_*/star*.str 은 칸마다 여유가 있고(0xCD 채움, 4바이트 정렬 아님) 실행 중 채워 쓸 수 있으므로
원래 칸(slot) 바이트를 보존한다: 새 내용이 칸에 들어가면 칸 크기 유지, 넘치면 4바이트 정렬로 늘린다.
"""
import struct

MAGIC = 0x0005A177
ENT = 0x38


def _cstr(d, o):
    return d[o:d.index(b'\0', o)]


def _wstr(d, o):
    out = []
    while True:
        c = struct.unpack_from('<H', d, o)[0]
        if c == 0:
            return out
        out.append(c); o += 2


def load(path):
    d = open(path, 'rb').read()
    magic, n, size, z = struct.unpack_from('<4I', d, 0)
    assert magic == MAGIC and size == len(d), path
    ents = []
    starts = []
    for i in range(n):
        w = struct.unpack_from('<14I', d, 16 + i * ENT)
        starts += [w[1], w[2], w[3], w[7]]
    order = sorted(starts)
    nxt = {o: (order[k + 1] if k + 1 < len(order) else len(d)) for k, o in enumerate(order)}
    for i in range(n):
        e = d[16 + i * ENT:16 + (i + 1) * ENT]
        w = list(struct.unpack('<14I', e))
        ents.append(dict(
            raw=e,
            voice_dir=_cstr(d, w[1]), voice_id=_cstr(d, w[2]), extra=_cstr(d, w[3]),
            text=_wstr(d, w[7]),
            slots=[d[o:nxt[o]] for o in (w[1], w[2], w[3], w[7])],
        ))
    return dict(z=z, ents=ents)


def _pad4(b):
    return b + b'\0' * (-len(b) % 4)


def _put(data, slot):
    """원래 칸에 들어가면 칸 바이트 위에 덮어쓰고, 아니면 4바이트 정렬로 늘린다."""
    if slot is not None and len(data) <= len(slot):
        return data + slot[len(data):]
    return _pad4(data)


def build(s):
    n = len(s['ents'])
    pos = 16 + n * ENT
    table = bytearray(); body = bytearray()
    for e in s['ents']:
        w = list(struct.unpack('<14I', e['raw']))
        slots = e.get('slots') or [None] * 4
        for j, (k, key) in enumerate(((1, 'voice_dir'), (2, 'voice_id'), (3, 'extra'))):
            w[k] = pos + len(body)
            body += _put(e[key] + b'\0', slots[j])
        w[7] = pos + len(body)
        body += _put(struct.pack(f'<{len(e["text"]) + 1}H', *e['text'], 0), slots[3])
        table += struct.pack('<14I', *w)
    total = 16 + len(table) + len(body)
    return struct.pack('<4I', MAGIC, n, total, s['z']) + bytes(table) + bytes(body)


if __name__ == '__main__':
    import glob
    import sys
    ok = bad = 0
    for p in sorted(glob.glob(sys.argv[1] + '/*.str')):
        if build(load(p)) == open(p, 'rb').read():
            ok += 1
        else:
            bad += 1; print('다름', p)
    print(f'재조립 동일 {ok}개, 다름 {bad}개')
