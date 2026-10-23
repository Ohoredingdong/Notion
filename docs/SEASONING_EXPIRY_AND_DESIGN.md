# 양념 기한 관리와 미니어처 선반

이후 앱과 위젯을 각각 같은 기능·디자인으로 제공했다. 아래는 양념 구현 시점의 기록이며 최신 진입 파일과 검증은 [앱과 위젯 기록](APP_AND_WIDGET.md)을 따른다.

## 문제와 변경

기존 양념은 `season: ['간장', ...]` 형태의 보유 목록이었다. 입력창·저장 필드에 날짜가 없었고 레시피는 체크한 양념을 기한과 무관하게 보유한 것으로 판단했다. 사용자의 기한 설정·레퍼런스 기반 디자인 수정 요청을 `feat/seasoning-expiry-and-miniatures` 브랜치에 반영했다. 비교 기준은 `7f97c3dc`다.

- 양념 병이나 보유 목록의 기한 버튼을 누르면 유통·소비기한을 입력·수정한다. 신규 양념 등록에도 날짜를 입력할 수 있다. 상비 재료 입력은 기존대로 유지한다.
- 이름과 기한 설정·오늘·내일·남은 일수·기한 경과를 선반에 표시한다. 기한 지난 양념은 레시피 보유 판정에서 제외하고 부족 사유를 `expired`로 표시하며, 레시피 상세의 양념 표시에도 경과 상태를 반영한다. 오늘까지인 양념은 포함하며, 기한 미입력은 날짜를 추정하지 않는다.
- 임박 양념은 냉장고의 임박 목록·요약에도 반영한다. 날짜를 지워도 보유 여부는 유지한다. 보유 해제·재체크도 기존 날짜를 임의로 지우지 않는다.
- 참고 이미지의 크림색 도자기·유리병·나무 뚜껑을 바탕으로 새 미니어처 PNG를 생성했다. SVG로 각 용기만 표시하며 한글 이름·상태는 읽을 수 있는 실제 텍스트로 둔다. 따뜻한 타일·우드 선반에 기본 4열로 배치하고 양념 수에 따라 높이를 늘린다. 냉장고와 레시피 화면을 재설계하지 않는다.
- 기존 양념 드래그·저장 좌표·겹침은 유지한다. 이전 좌표를 재배치하거나 초기화하지 않는다. 저장된 적 없는 양념의 기본 위치만 새 선반에 맞춘다.

양념은 기존의 이름별 보유 모델을 유지한다. 같은 이름의 여러 용기에 서로 다른 기한·잔량을 부여하는 lot 관리나 양념 수량 차감까지 구현한 것은 아니다.

## 저장과 호환

기존 `use-me-first-state-v5`와 `version: 5`, `season` 문자열 배열을 유지한다. 날짜를 실제로 저장했을 때만 선택 필드 `seasoningExpiry: { '간장': 'YYYY-MM-DD' }`를 추가한다. 기존 기록은 읽기·취소·일반 조회만으로 다시 저장하거나 날짜를 채우지 않는다. 날짜가 없는 기존 스냅샷 토큰도 그대로 유지한다.

선택 필드가 처음 추가될 때 변경 전 전체 레코드의 원본 문자열을 `use-me-first-before-seasoning-expiry-v1`에 한 번 보관한다. 원본 보관이 실패하면 저장을 중단한다. 잘못된 날짜·손상된 필드·경합·저장 실패는 기존 데이터를 덮어쓰지 않는다. 기한 삭제는 이름별 항목만 지우며, 보유·재료·수량·식사 기록·즐겨찾기·기존 동기화 설정을 초기화하지 않는다.

동기화·백업·복구·동시 쓰기도 선택 필드를 전달한다. 날짜 필드를 모르는 구형 서버 기록을 불러올 때는 알고 있는 로컬 날짜를 유지한다. 지원 클라이언트가 명시적으로 전달한 빈 날짜 맵 `{}`는 삭제로 구분한다. 구형 클라이언트가 새 필드를 보존한다는 보장은 없으므로 여러 기기는 같은 최신 클라이언트로 갱신해야 한다. 서버 함수에는 선택 필드의 날짜 검증도 추가했다. 실제 Supabase 쓰기·함수 배포는 수행하지 않았다.

## 전후 비교

동일한 [합성 자료](seasoning-expiry/fixture.json), 양념 8종·날짜, 2026-10-23 고정 시계와 1040px 높이를 사용했다. 선반을 가운데로 스크롤한 뒤 촬영해 하단 내비게이션이 가리지 않게 했다. 변경 전 코드는 비교 기준 커밋에서 읽어 체크아웃 밖에서 실행했다. 이전 코드에는 날짜 표시 기능이 없어 입력 자료의 날짜가 화면에 보이지 않는다.

| 화면 너비 | 이전 | 변경 후 |
| --- | --- | --- |
| 1120px | [화면](seasoning-expiry/before-1120.png) | [화면](seasoning-expiry/after-1120.png) |
| 390px | [화면](seasoning-expiry/before-390.png) | [화면](seasoning-expiry/after-390.png) |
| 320px | [화면](seasoning-expiry/before-320.png) | [화면](seasoning-expiry/after-320.png) |

[320px 날짜 편집창](seasoning-expiry/editor-320.png). 새 양념 아트 원본은 `assets/seasoning-miniatures-v1.png`이며 생성 결과를 편집하지 않고 사용한다.

## 검증

- [Node 150/150 통과](seasoning-expiry/node-tests.log), 실패·건너뜀 0개. 이전 138개와 새 저장·원본 보관·잘못된 입력·동시 수정·동기화·서버 핸들러·레시피·모달 회귀 12개를 포함한다. 서버 테스트는 실제 함수 코드를 실행하되 DB 전송을 모형으로 대체한다.
- [모듈형 앱 Chromium 30/30](seasoning-expiry/browser-results.json), [단일 HTML 32/32](seasoning-expiry/standalone-browser-results.json) 통과. 각각 1120/390/320px에서 네 문, 실제 마우스·CDP 터치 드래그, 저장·새로고침, 양념 날짜 입력·취소·삭제·경과 제외·최초 원본 보관, 사용자 정의 양념, 상비 재료, 레시피·식사 기록을 확인했다.
- 두 이미지 아틀라스와 주방 배경 디코딩, 가로 넘침, 실행 오류를 확인했다. 단일 파일은 자산 요청이 없으며 `srcdoc` iframe에서도 조작·저장, 저장 불가 환경에서는 안내 표시를 확인했다. 모두 격리된 합성 기록이며 외부 서비스 쓰기는 차단했다.
- 제공하는 `previews/use-me-first.html`이 검사한 단일 파일과 바이트 단위로 같은지 확인했다. 생성 파일의 크기는 3,617,005바이트다.
- 실제 채팅 호스트·Notion·실기기 Safari·개인 동기화·공개 배포는 검증하지 않았다. main 병합·배포는 수행하지 않았다.

제출 상태: [작업 브랜치](https://github.com/Ohoredingdong/Notion/tree/feat/seasoning-expiry-and-miniatures)에 push했다. `feat/cozy-four-door-kitchen`을 base로 draft PR 생성을 시도했으나 GitHub GraphQL API가 HTTP 403 `Forbidden`을 반환해 PR은 생성되지 않았다.

재현은 저장소 루트에서 실행한다. 클라우드에서는 먼저 `/workspace/.notion-cloud/activate.sh`를 source한다.

```bash
node --test tests/*.test.cjs
python scripts/test_fridge_four_door_browser.py --root "$PWD" \
  --output /tmp/seasoning-browser --browser-executable /usr/bin/chromium
python scripts/build_fridge_preview.py --output /tmp/seasoning-preview/use-me-first.html
python scripts/test_fridge_four_door_browser.py --root /tmp/seasoning-preview \
  --output /tmp/seasoning-standalone-browser --standalone --browser-executable /usr/bin/chromium
```
