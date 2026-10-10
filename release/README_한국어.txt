돌격!! 패미컴 워즈 한글패치 v0.1.1 (게임큐브 / 일본판 기준)
==============================================================

■ 준비물
  - 일본판 ISO   Totsugeki!! Famicom Wars (Japan).iso
      CRC32 ED987629 / MD5 edd9c78deed24f0807c3ed380a8f61d8
      (RVZ·GCM 등으로 갖고 계시면 Dolphin으로 ISO 변환 후 사용)
  - 패치 파일     G8WJ_KPatch_v0.1.1.xdelta
  - 패치 도구     xdelta3 또는 Delta Patcher 같은 GUI 도구

■ 적용 방법
  1) Delta Patcher (GUI)
     - Original file: 일본판 ISO
     - XDelta patch:  G8WJ_KPatch_v0.1.1.xdelta
     - Apply patch 클릭

  2) xdelta3 (명령줄)
     xdelta3 -d -s "Totsugeki!! Famicom Wars (Japan).iso" G8WJ_KPatch_v0.1.1.xdelta "Totsugeki!! Famicom Wars (Korean).iso"

  ※ 북미판(Battalion Wars)·유럽판에는 적용할 수 없습니다.
  ※ 원본 일본판에 적용하세요. v0.1 한글판 ISO에 덧씌우지 마세요.

■ 결과 파일 확인 (여기와 다르면 원본 ISO가 다른 것입니다)
  CRC32 8AA50C96
  MD5   d02a9e730c04f0c4100ce262de25fa5b
  SHA1  2264a465e281c337db8f12cffd194fddce4d6036
  SHA256 c79acb792c7b30496c3fdbb2c18fe329d0228ba15ae328709f4dcf23d652b82f
  크기  1,459,978,240 바이트

■ 한글화 범위
  - 대사: 미션 24개의 무전 대사·목표, 스토리 무비 자막
  - 메뉴: 메인 메뉴, 설정, 유닛 설명, 메모리카드 메시지
  - 그래픽: 타이틀 로고, 건강·안전 경고 화면, 버튼 안내, 디스크 배너 그림

■ 확인 환경
  - Dolphin 에뮬레이터
  - 실기: Wii U vWii + Nintendont

■ 알려진 문제
  - 승리·패배 연출 글자(VICTORY, DEFEAT)와 배경 속 간판은 원본부터 영문이라 그대로 두었습니다.
  - 무비 영상 안에 그려진 글자는 바꾸지 않았습니다. 자막은 모두 한글로 나옵니다.
  - 게임 목록의 배너 제목·설명과 메모리카드 세이브 이름은 한글을 넣을 수 없는 칸이라 일본어로 남습니다.

■ 기타
  비공식 팬 번역이며 Nintendo와 관련이 없습니다.
  패치를 적용한 게임 파일의 배포를 금지합니다.
