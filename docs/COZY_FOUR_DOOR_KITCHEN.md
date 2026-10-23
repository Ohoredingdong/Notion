# 코지한 레시피와 흰색 4도어 냉장고

사용자가 2026-10-23에 제공한 따뜻한 미니어처 주방 이미지와 새 구획 요청을 반영한 변경이다. 기준 브랜치는 `docs/project-handoff-20261023`, 구현 브랜치는 `feat/cozy-four-door-kitchen`이다. 기존 공개 URL `use-me-first.html`과 저장 키를 유지하며, 이 변경만으로 main 병합이나 공개 배포를 하지 않는다.

HTML만 전달되는 미리보기에는 CSS·이미지·동작을 포함한 [단일 파일](../previews/use-me-first.html)을 사용한다. 자산 누락 재현과 iframe 검증 결과는 [별도 기록](STANDALONE_KITCHEN_PREVIEW.md)에 있다.

이후 양념 기한 입력과 레퍼런스 기반 선반 디자인을 추가했다. 아래는 4도어 구현 시점의 기록이며, 최신 변경·전후 화면·검증 수치는 [양념 변경 기록](SEASONING_EXPIRY_AND_DESIGN.md)에 있다.

## 화면과 조작

- 흰색 에나멜과 크림색 디스플레이, 우드·타일·미니어처 식재료의 기존 무드를 이어간다.
- 위 왼쪽·오른쪽은 냉장실, 아래 왼쪽·오른쪽은 냉동실이다. 장식이던 아래 영역도 각각 열리고 닫히는 실제 보관 영역으로 연결했다.
- 위 왼쪽 디스플레이는 오늘·내일·3일 이내 재료의 이름·수량을, 위 오른쪽은 보유 재료 기준 추천 메뉴·부족 여부를 표시한다.
- 레시피 카드는 도마 위 미니어처 음식과 실제 레시피 재료를 보여준다. 기존 선택·상세·검색·필터·즐겨찾기·식사 기록 조작을 보존했다. 새로운 사진·가격·영양 정보를 실제 데이터처럼 만들지 않았다.
- 재료·양념 드래그와 겹침·위치 저장을 유지하고, 재료의 앞뒤 순서와 칸 선택 조작도 연결했다. 닫힌 구획은 inert/disabled 상태라 접근·드롭 대상이 되지 않는다.
- 320px 화면의 기본 아이콘 크기를 조정해 다른 재료가 대신 잡히는 문제를 막았다. 정리를 시작하면 냉장고를 화면 가운데로 옮겨 아래 냉동실이 고정 내비게이션에 가리지 않게 한다.

## 기존 데이터 보존

`use-me-first-state-v5`, 기존 위치 키 `use-me-first-kitchen-view-v1`, 양념 위치 `umf-seasoning-layout-v3`를 바꾸거나 삭제하지 않는다. 기존 `top/middle/bottom`은 위 왼쪽 냉장실, `freezer-top/middle/bottom`은 아래 왼쪽 냉동실에서 그대로 읽으며 lot ID·좌표·앞뒤 순서를 재배치하지 않는다. 오른쪽 구획의 zone ID만 추가했다.

기존 v1/v2 화면 설정은 읽기만으로 다시 저장하지 않는다. 네 문 중 하나를 실제로 조작했을 때 기존 v2 레코드에 선택 필드 `panels`를 추가하며, 예전 `doors.fridge/freezer`도 집계 상태로 유지한다. 기존 전체 냉장/냉동 열기 API는 좌우 문을 함께 제어한다. 잘못된 설정이나 알 수 없는 형식은 원본을 덮어쓰지 않고 오류를 표시한다.

화면 초기화 경로의 `refreshLegacyDemoExpiries`는 제거했다. 이전에는 특정 이름·수량 조합을 데모로 추정해 실제로 저장된 소비기한까지 바꿀 수 있었다. 이번에는 해당 조합의 과거 기한도 재로드·문 개폐·정리 중 그대로 보존한다. 이미 다른 실행에서 변경된 과거 기한을 추측해서 복원하지 않는다.

새 동작에 맞는 CSS·화면 상태·레시피·냉장고 JavaScript의 캐시 버전을 함께 갱신했다. 데이터 수집·실제 동기화 서버·다른 위젯은 변경하지 않는다.

## 화면 비교

아래 전후 비교는 같은 여섯 재료·수량·기한과 양념, 같은 1120px 화면으로 촬영했다. 사용자 실제 기록이나 공개 배포 화면이 아니라 격리된 로컬 검토 자료다. 재료가 아직 없는 첫 방문 화면에도 가상의 재고를 추가하지 않는다.

| 화면 | 변경 전 | 변경 후 |
| --- | --- | --- |
| 냉장고 | [1120px](four-door-kitchen/before-home-1120.png) | [1120px](four-door-kitchen/after-home-1120.png) |
| 레시피 | [1120px](four-door-kitchen/before-recipes-1120.png) | [1120px](four-door-kitchen/after-recipes-1120.png) |

모바일 검토: [닫힌 4도어](four-door-kitchen/fridge-390.png), [열린 네 구획](four-door-kitchen/fridge-open-390.png), [레시피 화면](four-door-kitchen/recipes-390.png).

## 검증

최종 결과: Node 138/138 통과·건너뜀 0개, 실제 Chromium 21/21 통과. 320px 터치로 아래 오른쪽 냉동실까지 이동하는 경로도 포함한다.

기존 Node 테스트와 새 회귀를 `node --test tests/*.test.cjs`로 실행한다. 새 테스트는 네 문 독립성, v1/v2 원본 유지, 잠금 중 동시 수정, 잘못된 설정 보존, 오른쪽 냉장·냉동 위치와 재로드, 과거 데모와 같은 식재료의 실제 기한 보존, 미니어처 레시피 조작을 검증한다. 예전 굴소스 customSeason 테스트는 굴소스가 이미 기본 양념이므로 별도의 사용자 정의 양념 ‘유자청’을 사용하게 고쳤으며 추가·삭제 단언을 유지했다.

실제 Chromium 검증 명령은 다음과 같다. 이 클라우드에서는 먼저 `/workspace/.notion-cloud/activate.sh`를 source한다.

```bash
python scripts/test_fridge_four_door_browser.py --root "$PWD" \
  --output /tmp/fridge-four-door-browser --browser-executable /usr/bin/chromium
```

브라우저 검증은 1120/390/320px에서 네 문 개폐, 두 디스플레이, 기존 위치와 재료 보존, 마우스·CDP 터치 입력으로 냉장 및 좌우 냉동실 사이 이동, 양념 이동·재로드, 레시피 선택·즐겨찾기·기록·검색, 가로 넘침·자산 로딩·JavaScript 오류를 확인한다. 매번 새 브라우저 컨텍스트를 사용하고 외부 서비스 쓰기는 차단한다. 재로드 시 테스트 자료를 다시 주입해서 저장 성공으로 오인하지 않게 최초 1회만 초기화한다.

최종 실행 결과는 [브라우저 결과](four-door-kitchen/browser-results.json)와 [Node 실행 로그](four-door-kitchen/node-tests.log)에 보관한다. 실기기 Safari·실제 Notion iframe·개인 Supabase 동기화 쓰기와 공개 배포는 이 로컬 검증으로 완료했다고 주장하지 않는다.
