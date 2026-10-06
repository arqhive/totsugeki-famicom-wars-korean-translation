# 돌격!! 패미컴 워즈 (GC) 한글 패치

*Totsugeki!! Famicom Wars* (게임큐브, 일본판 `G8WJ01`) 비공식 한국어 팬 패치입니다.
대사는 일본어판 원문을 기준으로 번역했습니다.

**제작: arqhive** · **최신 버전: [v0.1](../../releases/tag/v0.1)**

- 대사 전체를 한글화했습니다(미션 24개의 무전 대사·목표, 스토리 무비 자막 13편).
- 메뉴 전체를 한글화했습니다(메인 메뉴, 설정, 유닛 설명, 메모리카드 메시지).
- 타이틀 로고와 시작할 때 나오는 경고 화면을 한글화했습니다.
- 장면마다 쓰인 한글만 모아 게임 폰트를 새로 만들었습니다. 원본과 같은 흰 글씨·검은 테두리·그림자 모양입니다.
- **원본과 같은 1.4GB 디스크 크기를 유지합니다.**

> 이 저장소에는 **게임 데이터(롬·디스크 이미지, 추출한 원문 대사, 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 만들거나 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

### 준비물

- 일본판 ISO. 북미판(Battalion Wars)·유럽판에는 적용할 수 없습니다. RVZ·GCM으로 갖고 있다면 Dolphin으로 ISO로 바꾼 뒤 적용하세요.
- xdelta 패치 도구. [Delta Patcher](https://github.com/marco-calautti/DeltaPatcher)(GUI)나 [xdelta3](https://github.com/jmacd/xdelta-gpl/releases)(명령줄)를 쓰면 됩니다.

### 적용 방법

1. [배포 페이지](../../releases/latest)에서 `G8WJ_KPatch_v0.1.xdelta`를 받습니다.
2. 일본판 원본 ISO에 패치를 적용합니다. xdelta3에서는 다음처럼 실행합니다.

   ```
   xdelta3 -d -s "Totsugeki!! Famicom Wars (Japan).iso" G8WJ_KPatch_v0.1.xdelta "Totsugeki!! Famicom Wars (Korean).iso"
   ```

3. 결과 파일의 확인값을 아래 표와 비교합니다.

자세한 방법은 [`README_한국어.txt`](release/README_한국어.txt)를 참고하세요.

### 파일 확인값

| 항목 | 원본 일본판 | 패치 적용 결과 (v0.1) |
|---|---|---|
| 크기 | 1,459,978,240 바이트 | 1,459,978,240 바이트 |
| CRC32 | `ED987629` | `37C036E0` |
| MD5 | `edd9c78deed24f0807c3ed380a8f61d8` | `5e33c190200e1b2639900ad1debe4c88` |
| SHA-1 | `2abe94f9e12918d5688f1995beff198a2a096350` | `ff8de22aadcb628bda99cd31a39d3d162886336c` |
| SHA-256 | `15d338ce604215424c975dbbabaae463f009bff9d6b8af83e9a058a6f823055e` | `abe50d27e007fb5f80d0f19c9f551d986e61b259d11573f300bc2093e37fae0f` |

원본 파일명 예: `Totsugeki!! Famicom Wars (Japan).iso`

### 실행 환경

- **확인함**: Dolphin, Wii U vWii + Nintendont.

### 알려진 문제

- 승리·패배 연출 글자(VICTORY, DEFEAT)와 배경 속 간판(FORT GRIDIRON, STOP)은 일본판 원본부터 영문 디자인이라 그대로 두었습니다.
- 스토리 무비와 데모 영상 안에 그려진 글자는 영상의 일부라 바꾸지 않았습니다. 무비 자막은 모두 한글로 나옵니다.
- 게임 안 이미지 1,187종을 전수 확인했습니다. 일본어가 들어간 이미지는 타이틀 로고와 경고 화면 두 장뿐이며 모두 한글화했습니다.

## 개발자용: 직접 빌드

### 요구 사항

- Python 3.11 이상. `pip install -r requirements.txt`로 numpy, Pillow를 설치합니다.
- 일본판 ISO. 저장소 루트나 `iso/`에 두거나 환경 변수 `BW_JP_ISO`로 지정합니다.
- 맑은 고딕(`C:/Windows/Fonts/malgun.ttf`). 한글 글자를 그리는 데 씁니다.
- 원문 판독 도구(`export_text.py`, `review_sheets.py`)는 Yu Gothic Bold(`YuGothB.ttc`)도 씁니다.
- xdelta3. 배포용 패치를 만들 때만 필요하며, PATH에 두거나 환경 변수 `XDELTA3` 또는 `work/xdelta3.exe`로 둡니다.

### 빌드

```bash
# 한글 ISO 만들기 (work/TotsugekiFamicomWars_KO.iso)
python tools/build.py

# 배포용 패치까지: 빌드, xdelta 패치 생성, 적용 결과 해시 검증
python tools/make_patch.py 0.1
```

처음 실행하면 일본판 ISO를 `work/jp`에 추출합니다. 번역을 검사한 뒤 문자열 40개, 장면 폰트 39벌, 이미지 3장을 만들어 바뀐 파일 120개로 ISO를 다시 구성하고, 파일 3,576개를 모두 원본·빌드 결과와 비교해 검증합니다.
같은 입력이면 결과는 바이트 단위로 같습니다. Windows Git Bash에서는 `MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8`을 붙이세요.

### 번역 수정

- 번역: [`translation/ko/*.json`](translation/ko)의 `ko` 값을 고친 뒤 빌드합니다. 파일 하나가 게임 문자열 파일 하나이고, `index`는 항목 번호, `speaker`는 화자입니다.
- 원문 대조: `python tools/export_text.py`를 실행하면 일본어 원문·영어·번역을 나란히 담은 `work/BW1_텍스트_전량.json`이 만들어집니다. 이 파일의 `ko`를 고친 뒤 `python tools/ko_import.py work/BW1_텍스트_전량.json`으로 되돌려 넣을 수 있습니다.
- 검사: `python tools/check_ko.py`(줄 폭, 줄 수, 한자·가나 혼입, 문장부호). 빌드는 검사를 통과해야 진행됩니다. 줄 폭 한계는 무전 대사 346px(3줄), 미션 목표 410px, 메뉴 557px, 무비 자막 574px입니다.
- 표기·말투·문장부호 원칙은 [`translation/GLOSSARY.md`](translation/GLOSSARY.md)를 참고하세요.
- 그림 글씨: [`tools/assets/`](tools/assets)의 PNG를 원본과 같은 크기로 고친 뒤 빌드합니다.

`translation/ko/*.json`에는 **번역문만** 들어 있습니다(항목 번호, 화자, 한국어).
일본어·영어 원문은 게임 데이터라 넣지 않았습니다. 이 게임은 일본어를 글자 그림 번호로 저장하므로, 원문은 [`tools/data`](tools/data)의 판독표로 폰트를 읽어 복원합니다.

### 폴더 구조

```
tools/             빌드·검사·원문 판독 도구 (paths.py가 기준 경로를 잡음)
  data/            일본어 판독표(글자 모양 묶음과 판독 글자)
  assets/          한글화 이미지(타이틀 로고, 경고 화면)
translation/
  ko/              번역 JSON (항목 번호, 화자, 한국어)
  GLOSSARY.md      표기·말투·문장부호 원칙
docs/
  TECHNICAL.md     파일 포맷과 한글화 방식
  releases/        릴리즈 노트 사본
release/           배포용 xdelta 패치와 사용자 설명서
work/              (git 제외) 추출본·빌드 결과·원문
```

### 기술 문서

파일 포맷과 한글화 방식은 [`docs/TECHNICAL.md`](docs/TECHNICAL.md)에 정리했습니다.

## 변경 내역

전체 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 있습니다.

## 크레딧·라이선스

- 이 저장소의 도구 코드, 한국어 번역문, 문서: [MIT License](LICENSE) (© 2026 arqhive).

## 면책

비공식 팬 번역이며 Nintendo와 관련이 없습니다. 「돌격!! 패미컴 워즈」 관련 상표·저작권은 Nintendo와 Kuju Entertainment에 있습니다.
패치를 적용한 게임 파일의 배포를 금지합니다.
