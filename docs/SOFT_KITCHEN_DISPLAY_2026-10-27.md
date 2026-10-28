# 얇은 내장형 디스플레이 시안 · 2026-10-27

> 사용자 전체 화면 피드백으로 이 시안도 미채택이다. [크기·위치·비례 수정](FITTED_KITCHEN_DISPLAYS_2026-10-28.md)에서 이어 검토하며, 아래 기록을 확정된 디자인으로 해석하지 않는다.

사용자가 전날의 디스플레이에도 “안이뻐”라고 피드백했다. [이전 금속 테두리·카드형 화면](DISPLAY_REDESIGN_2026-10-26.md)은 채택된 디자인이 아니다. 이번에는 `feat/kitchen-play-and-sharp-displays`에서 표시창 CSS만 수정했다.

## 변경

- 금색 이중 테두리와 돌출 그림자를 없애고 얇은 테두리와 안쪽 그림자로 문에 들어간 화면을 표현했다.
- 배경은 밝은 세이지색이다. 재료 카드 상자와 메뉴 그림의 사각 틀을 없애고 얇은 줄·여백으로 정보를 구분한다.
- 제목과 이름의 굵기를 낮추고, 기한은 배지 대신 작은 점과 글씨의 색으로 표시한다. 기한이 지났다는 문구와 색의 의미는 유지한다.
- 장식용 상태등과 중복되는 `외 n종` 표시는 숨긴다. 하단의 전체 임박 종류 수는 유지한다.
- 냉장고 본체·양쪽 화면의 위치와 크기, 문 개폐·재료 편집·드래그·식사·도감·꾸미기·저장 로직은 바꾸지 않는다. JavaScript·HTML 원본 템플릿·저장 키·자산 원본도 변경하지 않는다.

[이전 화면](miniature-kitchen/soft-display-before.png) · [수정 화면](miniature-kitchen/soft-display-after.png) · [전체 구도](miniature-kitchen/soft-display-fridge.png) · [320px](miniature-kitchen/soft-display-320.png)

## 비교·검증

기준 커밋은 `6e470a2e`다. 앱·위젯 각각 1120×900, 649×660, 649×900, 390×660, 320×660, 760×660, 761×660에서 같은 재료·닫힌 문·시각 `2026-10-27T03:00:00Z`(Asia/Seoul)로 전후 캡처했다. 14쌍 모두 본체와 양쪽 표시창의 위치·크기가 이전과 같다. 기본 수량과 8개 요리명, 기한 경과/빈 상태, 터치 개폐도 별도로 확인했다.

장면 회귀 111개·식사/도감/저장 회귀 13개·표시창 집중 검사 8개 묶음과 13단계 크기 변경이 통과했다. 원본 그림 내장형과 작은 내장형의 UI 코드도 일치한다. 결과는 [검증 기록](miniature-kitchen/soft-display-validation.json)에 보관한다. 로컬 Chromium 검사이며 실제 Notion·Safari·사용자 클라이언트의 확인이나 최종 디자인 승인을 뜻하지 않는다.

```bash
source /workspace/.notion-cloud/activate.sh
python scripts/build_miniature_kitchen_preview.py --compact --output-dir /tmp/kitchen-soft-display
python scripts/test_miniature_kitchen_browser.py --root /tmp/kitchen-soft-display --output /tmp/kitchen-soft-core
python scripts/test_kitchen_journal_browser.py --root /tmp/kitchen-soft-display --output /tmp/kitchen-soft-journal
git diff --check
```

## 전달 범위

이미지·CSS·JavaScript를 넣은 작은 내장형은 `/workspace/artifacts/kitchen-soft-display/`에 있다. 앱 922,830바이트, 위젯 922,833바이트다. 추적 `previews/`의 원본 그림 내장형도 재생성했다. 기존에 전달한 9개 폴더의 HTML 미리보기도 같은 버전으로 갱신했다.

기존 배포 앱과 사용자 데이터는 수정하지 않았다. main·GitHub Pages에는 반영하지 않으며, 기존 작업 브랜치를 이어 사용한다. PR 생성은 앞선 작업에서 GitHub API의 `Forbidden` 응답으로 차단되어 있다.
