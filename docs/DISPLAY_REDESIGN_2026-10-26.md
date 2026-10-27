# 냉장고 양쪽 디스플레이 디자인 수정 · 2026-10-26

> 2026-10-27 사용자가 이 디자인에도 “안이뻐”라고 피드백했다. 이 문서는 미채택 시안의 구현 기록이며, [후속 내장형 표시창 시안](SOFT_KITCHEN_DISPLAY_2026-10-27.md)에서 계속 검토한다.

사용자의 “디스플레이 디자인좀 똑바로해봐” 요청에 따라 `feat/kitchen-play-and-sharp-displays`에서 양쪽 표시창을 수정했다. 비교 기준은 `9acc14ee`다. 기존 서비스가 아닌 독립 미니어처 앱·위젯 시안에 적용한다.

## 화면 변경

- 같은 폭의 두 표시창에 크림색 화면, 얇은 샴페인색 금속 테두리, 같은 제목·구분선·하단 정보 구조를 적용했다. 문 손잡이와 냉장/냉동 글씨를 가리지 않도록 배치했다.
- 왼쪽은 미니어처 식재료·이름·수량·기한을 묶는다. 오늘/내일/2~3일 이내를 색과 글로 구분하며, 기한이 지나면 붉은 `지남` 표시와 `기한 확인` 제목을 사용한다. 3일보다 먼 재료를 임박 목록에 채워 넣지 않는다. 날짜 비교는 현지 달력 날짜를 기준으로 하며, 시차·일광절약시간 때문에 하루가 달라지는 반올림을 피한다.
- 표시창 높이 185px 이상이면 최대 3종, 더 작은 화면이면 최대 2종을 기한순으로 표시한다. 아래에 전체 임박 종류 수를 표시하고, 넓은 화면에는 목록 밖의 종류 수도 보인다. 작은 표시창은 사진을 생략해 이름·수량 공간을 확보한다. 임박 재료가 없을 때는 빈 상태를 표시한다.
- 오른쪽은 음식 그림을 정해진 영역에 담고 메뉴명을 분리했다. 기존 8종 레시피에 있는 조리시간과 난이도만 표시한다. 좁은 화면에서는 난이도를 생략한다. 영양·비용을 새로 추정하거나, 선택한 메뉴를 자동 추천 결과로 표시하지 않는다.
- 글자는 변형·필터가 없는 HTML 레이어와 정수 픽셀 배치를 유지한다. 이름은 11px 이상이다. 320px에서도 기본 수량 `500ml`가 생략되지 않도록 표시창 폭과 안쪽 여백을 조정했다. 사용자가 매우 긴 수량 메모를 입력한 경우에는 생략 표시와 원문 `title`을 사용한다.
- 저장 기록이 없는 첫 실행은 네 문을 닫아 양쪽 화면을 바로 보여 준다. 이미 저장된 문 상태는 그대로 복원한다. 표시창 위를 눌러도 해당 문이 열리고, 열린 문을 다시 누르면 닫힌다.

카메라·배경·냉장고 본체 위치/크기와 문 애니메이션, 재료/양념 드래그, 식사·영양·도감·보상 및 저장 모델은 유지한다. `miniature-kitchen-preview-v1`의 키와 형식도 바꾸지 않는다. 기존 배포 앱과 기존 사용자 키는 수정하지 않는다.

## 비교와 검증

고정 시각 `2026-10-26T03:00:00Z`, Asia/Seoul, 같은 기본 재료와 닫힌 문 상태로 비교했다. 앱·위젯 각각 1120×900, 649×660, 649×900, 390×660, 320×660, 760×660, 761×660의 총 14쌍이다. **모든 쌍에서 냉장고 본체의 x/y/폭/높이가 이전과 같다.**

[이전 표시창](miniature-kitchen/display-before.png) · [수정 표시창](miniature-kitchen/display-after.png) · [수정 전체 화면](miniature-kitchen/display-fridge.png) · [320px 표시창](miniature-kitchen/display-320.png)

- [전후 캡처 수치](miniature-kitchen/display-comparison.json): 28개 캡처의 위치·크기·텍스트·넘침 수치.
- [추가 표시창 점검](miniature-kitchen/display-focused-results.json): 8개 묶음 통과. 앱·위젯의 7개 화면 조건에서 동일한 양쪽 폭, 수량의 실제 텍스트 폭, 영역 밖 잘림, 냉장 글씨와 겹침, 변형 없는 글자를 검사했다. 320px의 8종 요리명·시간·그림, 미래/미입력/경과 기한, 빈 상태와 표시창을 통한 터치 개폐도 확인했다.
- [장면 회귀 검사](miniature-kitchen/display-core-results.json): **111개 통과, 실패0**. 앱·위젯18개 화면 조건의 문·드래그·수량·기한·양념·소품·저장과 기존 데이터 보존. [13단계 크기 변경](miniature-kitchen/display-resize-results.json)도 통과했다.
- [식사·도감·보상·저장 회귀 검사](miniature-kitchen/display-journal-results.json): **13개 통과, 실패0**. 임시/손상/용량 오류 상태의 기존 기록 보존도 유지한다.
- 첫 실행이 닫힌 문으로 바뀌어, 검사도 필요한 칸을 먼저 연 뒤 재료를 측정하도록 수정했다. 기존 단언과 데이터 보존 검사는 유지한다. 이전 실행에서 열린 문을 전제한 검사 실패를 조사했으며 최종 실행 결과와 구별한다. 최종 생성 파일의 기본/작은 내장형 UI 코드 일치, JavaScript 구문과 `git diff --check`도 통과했다.

```bash
source /workspace/.notion-cloud/activate.sh
python scripts/build_miniature_kitchen_preview.py --compact --output-dir /tmp/kitchen-display
python scripts/test_miniature_kitchen_browser.py --root /tmp/kitchen-display --output /tmp/kitchen-display-core
python scripts/test_kitchen_journal_browser.py --root /tmp/kitchen-display --output /tmp/kitchen-display-journal
node --check designs/miniature-kitchen/scene.js
git diff --check
```

로컬 Chromium 검증이며 실제 사용자 클라이언트·Notion·Safari 검증이나 사용자의 최종 디자인 승인을 뜻하지 않는다. 실제 배포 앱에 기존 데이터를 연결하는 작업은 별도다.

## 전달

작은 내장형은 앱 923,194바이트, 위젯 923,197바이트다. `/workspace/artifacts/kitchen-display-redesign/`의 두 HTML에 이미지·CSS·JavaScript를 모두 넣었으며 외부 이미지 요청이 없다. 기존에 전달한 8개 미리보기 폴더도 같은 파일로 갱신했다. 이미 열린 화면은 새로 열어야 수정 내용이 보인다.

추적 `previews/`의 원본 그림 내장형도 재생성했다. main·GitHub Pages는 변경하지 않았다. 기존 작업 브랜치를 이어 사용하며 PR 생성은 앞선 작업에서 GitHub GraphQL API의 `Forbidden` 응답으로 차단된 상태다.
