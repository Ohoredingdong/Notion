# 냉장고 구조·재료 배치 후속 수정

사용자가 “수정해 알면”이라고 요청한 뒤 실제 화면 재검토에서 확인한 다섯 문제를 수정했다. 지난 공개 실행과 크기 측정은 디자인 승인으로 취급하지 않는다.

- 우유를 가로지르던 중간 선반을 제거한 새 냉장고 자산을 연결했다. 냉장/냉동 분할은 약60/40이며, 왼쪽 냉동2서랍·오른쪽3서랍의 실제 가장자리를 음식보다 앞에서 그린다. 본체와 닫힌 앞면은 같은 원본의 두 상태다.
- 음식 모양은 이름별로 고정한다. 같은 칸에서 x/y가 바뀌어도 크기가 변하지 않는다. 다른 칸으로 옮기는 경우 해당 칸의 수납 높이에 맞춘다. 재료 사진·용기·접지 그림자와 따뜻한 조명을 조정했고, 세로 보관통의 브로콜리를 연결했다.
- 저장된 좌표는 그대로 읽는다. 표시할 때 실제 선반/서랍 바닥으로 투영하며 이 계산은 원본 저장 자료를 이전하거나 덮어쓰지 않는다. 기존 생선과 소고기가 같은 서랍으로 모이지 않도록 냉동칸의 두 행을 구분한다. 상세 조회를 위한 선택도 저장을 발생시키지 않는다.
- 배경은 위젯 상단부터 채우면서 냉장고의 발과 같은 바닥선에 맞춘다. 배경 조리대의 높이를 기준으로 소품의 표시 위치도 연결했다.
- 이동 알림은 접근성 안내만 남긴다. 저장·적용·오류 알림은 유지한다. 사진의 윗부분까지 조작 영역에 포함하고, 작은 화면에서 이웃 칸의 투명44px 영역을 눌러도 실제 음식 그림의 상세가 열리도록 연결했다.

이 수정은 새 시안 이미지를 보여주는 작업이 아니라 앱/위젯의 공유 소스와 전송 HTML을 바꾼 작업이다. 식단 계획은 레시피 탭 안에 유지한다. 원래 운영 HTML·main/Pages·저장 키 `miniature-kitchen-preview-v1`과 v1 형식은 바꾸지 않았다.

## 화면·검사 범위

동일한 초기 재료·날짜·열린 문 상태로801×782,390×560,320×568,649×600의 실제 래퍼 화면을 비교한다. 기존 v1 세계는 별도로 복원한다. 예시 영양 수치를 실제 기록으로 넣지 않는다. 변경 전후 자료는 [증거 폴더](kitchen-scene-repair/)에 두며, 브라우저 검사를 시각적 일치나 사용자 승인으로 부르지 않는다. Safari·실기기·실제 Notion 임베드는 이번 검사의 범위가 아니다.

전송 단위검사12개와 관련 상태/워크플로/보상 모델77개가 통과했다. 행동 후보4의 실제 음식 선택52/52, 기존 v1 실제 선택26/26·저장 원문 보존, 이동/새로고침6/6, 우유 뚜껑/중앙 선택12/12가 통과했다. 결과 파일은 후보4 SHA를 기록하며 최종5와 구분한다. 최종5는 음식/저장 로직을 유지하고 양옆 사진 조리대만 추가했다. [최종 닫힌 문·꾸미기 검사](kitchen-scene-repair/final-counter-views.json)는801·390px에서 기존 세계와 편집 초안이 바뀌지 않고 오류가 없음을 확인했다. 최종 전체 공개 실행은 별도 소스 커밋과 함께 기록한다.

## 자산과 전달물

새 자산은 원본1536×1024 냉장고,604×815 브로콜리를 유지한다. [냉장고](kitchen-scene-repair/cabinet-codec.json)·[브로콜리](kitchen-scene-repair/broccoli-codec.json)·[남은 음식 아틀라스](kitchen-scene-repair/pantry-codec.json)의 압축 비교를 보존했다. 사용하지 않는 기존 우유/브로콜리 아틀라스 영역만 전달용 변형에서 비웠으며 원본 PNG와 나머지 음식은 유지한다.

[전달 파일 정보](kitchen-scene-repair/generated-files.json): 앱1,043,031B, 위젯1,043,040B, 모바일 앱1,044,378B, 모바일 위젯1,044,393B. 네 파일 모두1MiB 이내이며 무손실 전송 포장에서 원문 바이트가 복원되는 것을 확인했다. 외부 이미지 요청에 의존하지 않는다.

작업 브랜치는 `fix/kitchen-storyboard-fidelity`다. 이전 PR 생성은 GitHub GraphQL403 Forbidden으로 차단됐으며 이 제한을 디자인 승인이나 배포 완료로 설명하지 않는다.

## 최종 화면

구현 커밋은 `8a98f3c3479894157765db35dae5fed4a7228396`이다. [801px 실제 열린 화면](kitchen-scene-repair/final-user.png), [390px](kitchen-scene-repair/final-phone.png), [320px](kitchen-scene-repair/final-small.png), [짧은649px](kitchen-scene-repair/final-short.png)을 동일 후보5에서 캡처했다. [닫힌 화면](kitchen-scene-repair/closed-801.png)과 [꾸미기](kitchen-scene-repair/decor-390.png)도 실제 HTML 실행이다. [후보별 QA 출처](kitchen-scene-repair/qa-summary.json)는 전체 행동 검사와 조리대 사진만 추가한 후속 화면 검사를 구분한다.649px 왼쪽 조리대에는 작은 사진 이음새가 남아 있다.

## 실제 공개 실행

[최종 HTTPS 실행](https://github.com/Ohoredingdong/Notion/actions/runs/41605085797)은 구현 `8a98f3c3`, 검증 코드 `fadd03e77b02924e836b53e2a8a3a52cf6dcc9d8`, 결과 `2b39eab8e8e8fbc6569502fc9d11896011e98fcd`를 구분한다. 앱/위젯 각각320·390·649px와801×782 총8개가 통과했고 런타임 오류는0개다. 각 화면13개 음식의 실제 클릭104번이 올바른 A6 ID를 열었다. 배경 상단·새 본체/냉장칸 비율·헤더 겹침·조용한 이동/문 알림·추가 버튼·계획 보기·꾸미기 취소·자료 보존을 확인했다. [결과 원문](kitchen-scene-repair/public-status.json)에 각 검사 조건을 기록한다. 이 실행은 시안과 동일하다는 판단이나 사용자 승인을 대신하지 않는다.

[수정된 위젯 열기](https://htmlpreview.github.io/?https://raw.githubusercontent.com/Ohoredingdong/Notion/8a98f3c3479894157765db35dae5fed4a7228396/previews/mobile/widget.html). 작업 브랜치에 push했다. PR 생성은 기존 GitHub GraphQL403 제한으로 미완료이며 main/Pages를 변경하지 않았다.

[실제 공개801px PNG](kitchen-scene-repair/widget-801x782-public.png)는 정상 TLS로 HTTP200·image/png·Git 원문 바이트 일치를 확인했다. [파일 확인](kitchen-scene-repair/public-fetch.json)은 공개 URL과 SHA를 기록한다.
