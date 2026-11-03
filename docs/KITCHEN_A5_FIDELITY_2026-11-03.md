# A5 기준 재료 사진·수납·창가 구도 수정

사용자는 이전 결과와 시안의 차이를 설명한 뒤 실제 수정을 요청했다. 이번 변경은 원본 [재료 흐름 시안](../designs/kitchen-ux-storyboards/01-ingredients.png)의 우유 등록 후 A5를 음식 배치의 기준으로 사용하고, A1은 창가·문 선반·프레임을 참고한다. UI 프레임 비중은 원본과 이미 비슷했으므로 일괄 축소하지 않았다.

## 변경한 실제 화면

- 왼쪽 냉장칸을3단, 오른쪽은 높은 위칸과 얕은 아래2단으로 바꿨다. 새 본체/닫힌 앞면은 같은 자산이며 원래 비율을 유지한다. 측정한 실제 선반 위치로 사진 바닥과 유리 앞테두리를 연결한다.
- 음식13종·양념4종을 동일한 시점·조명·용기 표현의 한 사진 세트로 교체했다. 우유와 브로콜리의 과한 크기를 줄이고, 냉동5종은 실제로 넓고 얕은 용기로 새로 생성했다. 사진을 가로로 늘여 용기에 맞추지 않는다. 양념은 기존4개를 문 선반에서 더 잘 보이게 했다.
- 창문을 화면 밖으로 잘라내던 배경을 바꿨다. 왼쪽 창문·늘어진 식물·햇빛과 오른쪽 그릇·허브가 보인다. 조리대와 냉장고의 발은 사진의 실제1066px 바닥선을 함께 사용한다. 기존1045px는 벽과 바닥의 경계였으며 가구의 발과 구분했다.
- 상단의 미입력 대시와 굵은 제목의 무게만 낮췄다. 실제 기록과 목표를 시안의100/35/20 예시로 채우지 않는다. 메뉴·추가/저장·44px 조작 영역은 유지한다.
- 음식의 가로 위치는 저장한 좌표와 실제 드래그를 따른다. 선반과 사진 크기의 계산은 사용자 좌표를 덮어쓰지 않는다. 같은 칸 안에서 옮겨도 그림 크기가 변하지 않으며 새로고침 뒤 같은 위치가 유지된다. 넓어진 냉동 재료를 추가 버튼이 가리지 않도록 버튼을 바깥쪽으로 옮겼다.

기존 v1 저장 세계·재료ID·수량·기한·zone/x/y·식사·계획·지출·보상과 저장 키를 유지한다. 새 초기 재고도 추가하거나 복제하지 않았다. 원본A5와 실제 저장 재고의 개수가 다르므로 기록 수에 따른 빈 칸은 유지한다. 운영 원본 HTML·main/Pages는 변경하지 않았다.

## 자산과 전달물

[본체 경계/압축](kitchen-a5-fidelity/cabinet-geometry-codec.json), [음식17종 경계](kitchen-a5-fidelity/food-sprite-map.json), [음식 압축](kitchen-a5-fidelity/food-codec.json), [배경 압축](kitchen-a5-fidelity/room-codec.json)을 기록했다. 새 원본 PNG는 보존한다. 선택 AVIF는 같은 해상도의 WebP82와 비교해 PSNR·SSIM을 모두 충족한다.

[전달 파일](kitchen-a5-fidelity/generated-files.json)은 앱1,004,646B, 위젯1,004,649B, 모바일 앱1,005,993B, 모바일 위젯1,006,002B로 모두1MiB 이내다. 무손실 전송 포장의 원문 복원과 기존 전송 단위검사12개를 통과했다. 외부 이미지 주소에 의존하지 않는다.

## 검증 범위

기준86e20767의 실제 초기 v1 세계와 기존 저장 v1 세계를 각각 고정해 같은 문 상태·선택·날짜·뷰포트로 전후를 비교한다. 801×782,390×560,320×568,649×600의 앱/위젯을 사용한다. 모바일 래퍼의 임시 세션과 native HTML의 실제 저장/새로고침 검사를 구분한다. 기능 통과는 시안과 동일한 외형 또는 사용자 승인을 뜻하지 않는다.

중간 후보에서 실제 그림이 움직이지 않는데 모델 좌표만 바뀌는 정렬 문제가 발견됐다. 고정 슬롯 정렬을 제거하고 실제 그림의 이동량도 검사하도록 보완했다. 해당 후보의 크기/저장 검사 결과를 최종 이동 통과로 바꿔 부르지 않는다. 최종 고정 후보의 실제 결과는 별도 SHA와 함께 추가한다.

## 최종 고정 후보4 확인

[동일 상태 전후](kitchen-a5-fidelity/same-state-captures.json)16개 모두 세계·좌표·문·선택·기록이 같다. [801px 수정 화면](kitchen-a5-fidelity/after-801.png), [390px](kitchen-a5-fidelity/after-390.png), [320px](kitchen-a5-fidelity/after-320.png), [649px](kitchen-a5-fidelity/after-649.png)과 대응하는 before 파일을 함께 보존한다. 원본A5는 우유 등록 후 상태이나 예시 재고/영양 값이 다르므로 데이터가 같은 전후 화면으로 부르지 않는다.

[실제 포인터 검사](kitchen-a5-fidelity/actual-pointer-cancel.json)는17종×16개 래퍼 상태272/272, 우유 윗부분/뚜껑48/48, 편집 후 취소16/16을 통과했다. [native 저장·이동](kitchen-a5-fidelity/visible-movement-reload.json)16/16은 실제 그림 이동량 최소11.32px, 크기 유지·이동 뒤 새로고침 위치·원문 저장 자료 보존을 확인했다. [가림/조리대 검사](kitchen-a5-fidelity/overlay-and-surfaces.json)에서 냉동 사진14,440개 표본에 추가 버튼·메뉴·헤더 가림이 없고, 닫힌 문/꾸미기의 가구 발과 소품 지지가 연결된다. JavaScript 오류는0개다. [최종 QA 요약](kitchen-a5-fidelity/qa-summary.json)은 모든 결과를 전달 파일 SHA로 묶는다.

시안의 긴 잎채소와 현재 브로콜리의 모양, 원본 예시와 실제 재고 수에 따른 밀도는 차이가 남는다. 이는 픽셀 일치나 사용자 승인으로 보고하지 않는다. 작업 브랜치는 `fix/kitchen-storyboard-fidelity`이며 기존 PR 생성은 GitHub GraphQL403 제한으로 미완료다.

## 최종 공개 실행

구현은 `3afe3d62545a562f15612d71739bf3cfb664379c`, 검증 코드는 `7bb48624ea0ddbbf8a05c4d20e1f2877390fd901`, 공개 결과는 `df4ba497d26127ceba47d0cb74a9a5aea11ac481`이다. [실제 HTTPS 실행](https://github.com/Ohoredingdong/Notion/actions/runs/41640053039)은 앱/위젯 각각320·390·649px 및801×782의8개 상태를 통과했다. 음식/양념17개의 실제 포인터 선택136번이 올바른 상세ID를 열고 세계/기록을 유지했다. 런타임 오류는0개이며 헤더·추가 버튼·알림·계획 보기·꾸미기 취소·기록 후 열린 화면/닫힌 화면도 확인했다. [공개 결과](kitchen-a5-fidelity/public-status.json)는 source/verifier와 각 검사 조건을 기록한다.

[공개801px 실제 PNG](kitchen-a5-fidelity/public-widget-801.png)는 정상 TLS로 HTTP200·image/png·Git 원문 바이트 일치를 확인했다. [공개 파일 확인](kitchen-a5-fidelity/public-fetch.json)에 URL과 SHA를 남긴다. 이는 Chromium 크기별 실행이며 실기기·Safari·실제 Notion 임베드·OCR 검증을 뜻하지 않는다.

[수정본 열기](https://htmlpreview.github.io/?https://raw.githubusercontent.com/Ohoredingdong/Notion/3afe3d62545a562f15612d71739bf3cfb664379c/previews/mobile/widget.html). 작업 브랜치에 push했으며 main/Pages는 변경하지 않았다.
