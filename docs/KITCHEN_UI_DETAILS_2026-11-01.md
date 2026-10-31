# 한끼의 부엌 · UI 세부 수정

기준: 2026-11-01 Asia/Seoul. 사용자 요청: “디테일 수정해”. 변경 전 `21e664e8`, 작업 브랜치 `fix/kitchen-ui-details`.

선택한 열린 흰색 4도어·중앙 배치·아이보리/린넨/우드 배경과 기존 기록 기능을 유지하면서 실제 앱·위젯 화면의 읽기와 조작을 다듬었다. 새 사진 자산·색상 테마·도메인 모델은 추가하지 않았다.

| 확인한 문제 | 수정 |
| --- | --- |
| 320px에서 재료 이름이 말줄임되고 선택 라벨이 다음 재료를 가림 | 첫 실행의 자동 계란 선택을 제거하고, 라벨의 폭·높이·사진과의 간격을 조정. 작은 라벨에서 양송이버섯은 ‘양송이’로 표시하되 원래 이름·접근성 설명·상세 입력값은 유지. PC 글자는 장면 크기에 맞춰 확대 |
| 작은 화면에서 ‘재료 추가’, ‘요리 찾기’가 두 줄로 갈라짐 | 버튼의 가로 간격·아이콘·글자 크기를 맞추고 한 줄로 표시 |
| 양념 상세가 세로 한 열이며 사진 옆에 빈 공간이 큼 | 이름/사진 → 수량/보관 → 기한 종류/표시 기한/개봉일 순서로 재배치. 사진은 펼쳐 확인하고 하단 저장·닫기 동작을 유지 |
| 영양 기록의 메뉴가 중복되어 본문이 아래로 밀림 | 기능 이동을 하나의 4개 메뉴로 통일하고 현재 위치를 표시. 목표 설정·월간·도감/보상 링크는 해당 내용 아래에 유지 |
| 기한 요약은 읽기만 가능 | 오늘/내일/2~3일/경과 표시를 해당 묶음 목록에 연결. 0수량·소진 재료를 요약과 필터에서 동일하게 제외. 전체 보기로 복귀 가능 |
| 영양 일부만 입력한 식사의 합계가 홈에서는 완전한 값처럼 보일 수 있음 | 탄단지 각각의 ‘N끼 미입력’을 표시. 현재 g(목표 g), 알려진 0과 미입력의 차이, 비례 막대를 유지. 긴 숫자는 목표를 다음 줄로 보내 가로 넘침 방지 |
| 상세 창 열기/저장 후 키보드 초점이 불명확 | 창 제목으로 읽기를 시작하고, 닫거나 저장한 뒤 원래 조작한 버튼/재료로 초점 복귀. 렌더링으로 교체된 같은 재료 버튼도 다시 찾음 |
| 생성기의 전역 치환이 위젯 CSS의 앱 선택자까지 변경 | 실제 body 모드만 치환. PC의 추천 사이드바는 앱에만 적용하고 넓은 위젯은 중앙 냉장고 공간을 온전히 사용 |
| 안내 글자 대비·카드/입력 간격이 들쭉날쭉 | 차콜/웜그레이 대비, 입력 높이, 얇은 경계, 카드 행간과 버튼 반응 통일 |

변경 파일은 `designs/miniature-kitchen/{neutral.css,scene.js,workflows.js}`, 생성기와 생성된 미리보기, 검증 스크립트·문서다. 원래 운영 HTML·URL·localStorage 키·envelope 버전·world/play/workflow 형식은 변경하지 않는다. 필터와 선택은 화면 상태이며 재고를 변경하지 않는다. 사진 자동 인식·자동 영양 데이터·동기화의 미연결 조건도 그대로다.

## 검증 기준

변경 전후를 같은 2026-11-01 날짜·재료·기한·문 상태·브라우저 크기로 비교한다. 앱·위젯 각 320×660, 390×844, 1120×1000의 6개 초기 world/play/workflow가 변경 전과 정확히 같은지 검사한다. 새 기본 선택 제거는 저장 데이터 변경이 아니다.

```bash
source /workspace/.notion-cloud/activate.sh
python scripts/build_miniature_kitchen_preview.py --compact
python scripts/build_kitchen_mobile_preview.py
python scripts/test_kitchen_details_browser.py --root previews --output /tmp/kitchen-details
python scripts/test_open_fridge_neutral_browser.py --root previews --output /tmp/kitchen-regression
node --test tests/*.test.cjs
PYTHONPATH="$PWD:$PWD/scripts" python -m unittest discover -s scripts -p 'test_*.py'
```

새 검사는 기한 표시/목록 일치·영양 미입력/0/긴 숫자·메뉴 재렌더·실제 opaque 프레임의 터치 저장·초점 복귀를 다룬다. 기존 검사는 문 첫 프레임 가림·이동·식사 차감/수정/취소/복구·사진 등록·구매/예산·영양제·월간·저장/가져오기·레거시 기한/좌표 보존을 다룬다. 실제 iPhone/Safari/Notion 실기기 검증과 구분한다.

## 이번 검증 결과

- 세부 브라우저 **13/13**, 기존 연결 흐름 **27/27**, Node **177/177**, Python unittest **262/262** 통과. [요약](kitchen-details-20261101/checks.json), [세부 검사](kitchen-details-20261101/detail-results.json), [기존 흐름 회귀](kitchen-details-20261101/regression-results.json).
- 앱·위젯 320/390/1120px의 6개 world/play/workflow는 이전 화면과 정확히 같다. 같은 날짜·열린 네 문·선택 없음으로 [전후 조건](kitchen-details-20261101/comparison.json)을 맞췄다. 별도로 새 첫 실행에서 자동 선택을 제거한 것도 확인했다.
- 냉동 재료의 기한이 다음 그림에 가려지는 문제는 **문 안쪽의 별도 라벨 표시층**으로 수정했다. 식재료의 저장 좌표·앞뒤 순서는 유지한다. 작은 화면뿐 아니라 스크롤한 PC 화면에서도 각 라벨 하단의 표시 순서를 검사한다. 라벨은 클릭을 가로채지 않고 닫힌 문 뒤에 남는다.
- 영양 [부분 입력 예시](kitchen-details-20261101/partial-nutrition.png)는 검사에서 입력한 값이다. 사용자 기록으로 주입하지 않는다.
- 압축 앱 **957,716B**, 위젯 **957,719B**, 공개 wrapper **1,007,312/1,007,321B**로 모두 1MiB 상한 안이다.

| 같은 상태의 비교 | 이전 | 수정 후 |
| --- | --- | --- |
| 앱 320×660 · 첫 화면 | [열기](kitchen-details-20261101/before-app-320-home.png) | [열기](kitchen-details-20261101/after-app-320-home.png) |
| 앱 390×844 · 양념 상세 | [열기](kitchen-details-20261101/before-app-390-ingredient.png) | [열기](kitchen-details-20261101/after-app-390-ingredient.png) |
| 앱 390×844 · 영양 | [열기](kitchen-details-20261101/before-app-390-nutrition.png) | [열기](kitchen-details-20261101/after-app-390-nutrition.png) |
| 위젯 1120×1000 · 첫 화면 | [열기](kitchen-details-20261101/before-widget-1120-home.png) | [열기](kitchen-details-20261101/after-widget-1120-home.png) |

검토용 브랜치에만 올리고 main·Pages 배포는 유지한다. 공개 미리보기는 원래와 같이 opaque 임시 세션이며, 백업을 통해 보관할 수 있다. 소스 커밋을 고정한 공개 HTTPS 실행 결과는 별도로 기록한다.

## 공개 링크 확인

소스 `38cd042f5429e9e6090097724d7499acb8eadcab`를 고정한 [공개 브라우저 실행](https://github.com/Ohoredingdong/Notion/actions/runs/41222691778)에서 **6/6 통과**했다. 앱·위젯 각각 PC 649×900, 휴대폰 크기 390×844와 320×660에서 실제 HTMLPreview 링크의 HTTP 200·원문 SHA256·실행·문 개폐·양념 기한 저장·하나의 영양 메뉴·사진 등록의 미연결 안내·런타임 오류 없음을 확인했다. 모바일 프로필은 실제 터치 이벤트를 사용했고 실기기 검증을 뜻하지 않는다.

- [앱 열기](https://htmlpreview.github.io/?https://raw.githubusercontent.com/Ohoredingdong/Notion/38cd042f5429e9e6090097724d7499acb8eadcab/previews/mobile/app.html)
- [위젯 열기](https://htmlpreview.github.io/?https://raw.githubusercontent.com/Ohoredingdong/Notion/38cd042f5429e9e6090097724d7499acb8eadcab/previews/mobile/widget.html)
- [실제 결과 JSON](kitchen-details-20261101/public-results.json), [공개 앱 320px](kitchen-details-20261101/public-app-320.png), [공개 위젯 320px](kitchen-details-20261101/public-widget-320.png).

검증 실행은 `delivery/verify-kitchen-details-20261101`, 결과는 `preview/kitchen-details-validation-20261101`의 `9e15bf717125e6fa77380a4c3eacd1d8332be013`에 보관한다. 이 실행은 운영 기록이나 main·Pages 설정을 수정하지 않는다.

PR은 `feat/open-fridge-neutral-ui`를 기준으로 `fix/kitchen-ui-details` 생성 요청을 했으나 GitHub GraphQL API가 `403 Forbidden`을 반환해 생성되지 않았다. 수정·전후 증거·검증 결과는 원격 작업 브랜치에 보관한다.
