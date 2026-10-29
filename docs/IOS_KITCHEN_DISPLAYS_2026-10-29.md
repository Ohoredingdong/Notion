# iOS 느낌의 냉장고 표시창 · 2026-10-29

사용자가 표시창을 아이폰처럼 바꿔 달라고 명시적으로 요청했다. 기준은 `3475b22f`다. 앞선 펄·샴페인 실버 시안을 채택된 디자인으로 취급하지 않는다.

화면을 iOS의 밝은 회색 바탕(`#f2f2f7`), 둥근 흰 카드, 검정 제목, 파란 배지·기록 막대로 구성했다. 기한별 숫자는 옅은 주황·파랑·초록으로 구분하며 경과 항목은 빨강을 사용한다. 금속 이중 가장자리와 장식 그라데이션을 없애고 얇은 회색 가장자리만 둔다. 왼쪽은 기한 숫자와 재료 목록, 오른쪽은 음식 그림·메뉴명·조리 정보·재료 이름 기록률을 구분한다.

변경 소스는 `scene.css`의 LCD 영역뿐이다. 원본 그림, 본체·표시창 좌표와 크기, 문 조작, JavaScript와 데이터·저장 형식은 변경하지 않는다. 앱·위젯 생성 파일에도 같은 CSS를 넣는다. 표시창 위에서 누르면 문이 열리고 열린 문을 다시 눌러 닫는다. 두 제목은 `유통기한 임박`·`오늘의 추천메뉴`를 유지한다. 기록률은 재료 이름 기준이며 수량 검증·조리 가능 판정이 아니다.

좁은 화면에서는 메뉴명을 먼저 배치하고 작은 음식 그림과 조리시간을 같은 줄에 둔다. 짧은 summary 구성에서는 기존처럼 그림을 생략한다. 제목과 수량을 작은 글자로 줄여 맞추지 않는다.

[수정 전](miniature-kitchen/ios-before.png) · [수정 후 상세](miniature-kitchen/ios-detail.png) · [전체 모습](miniature-kitchen/ios-fridge.png) · [휴대폰 크기](miniature-kitchen/ios-phone.png)

## 검증

같은 예시 데이터·닫힌 문·고정 시각 `2026-10-28T03:00:00Z`와 Asia/Seoul 조건으로 전후를 비교했다. 앱·위젯의 649×900, 390×660, 320×660, 320×568 총 8쌍에서 본체와 표시창의 위치·크기가 같다. 날짜를 고정한 예시이며 실제 사용자 재료의 현황이 아니다.

집중 검사 12개 묶음은 앱·위젯 각각 11개 화면 조건, 기존 8개 요리명과 카드 내부 배치, 수량·기한·빈 상태·양념 경과·재료 기록률 및 직접 문 조작을 통과했다. 처음에는 320px의 흰 재료 카드 여백 때문에 `500ml`가 잘렸고, compact 여백을 줄인 뒤 기존 수량 단언을 유지해 통과했다. 원본·작은 내장형의 UI 코드도 일치한다.

공개 확인용 프레임의 로컬 Chromium 휴대폰 크기·터치 검사 6개 조건은 이번 첫 실행에서 통과했다. 네 문, 대화창과 백업, 가로 넘침·제목·임시 저장 범위 및 외부 요청 부재를 확인했다. 앞선 [펄 시안의 간헐 터치 실패](PEARL_KITCHEN_DISPLAYS_2026-10-28.md)를 이번 CSS 수정으로 해결했다고 보고하지 않는다. 실제 iPhone/Safari·Notion은 미확인이다.

기본·경과 상태와 세 화면 구성의 실제 글자색/불투명 바탕색으로 계산한 대비는 최소 약 5.36:1이다. [검증 기록](miniature-kitchen/ios-display-validation.json)에 범위를 보관한다. JavaScript·저장 모델이 바뀌지 않았으므로 전체 장면·식사 회귀를 새로 실행한 것으로 보고하지 않는다.

작은 내장형은 앱 931,491바이트·위젯 931,494바이트, 공개 확인용은 954,718바이트·954,727바이트다. 공개 프레임의 임시 저장과 `Open the page` 안내는 [모바일 전달 문서](MOBILE_KITCHEN_PREVIEW.md)를 따른다. 기존 앱·main·GitHub Pages에는 반영하지 않는다.

## 공개 검토

화면이 포함된 커밋은 `fdca2d982bf44bb99e206b473b8f4b79756ceecb`다. 아래 PNG 세 개와 HTML 원본 두 개의 공개 HTTP 200·로컬 바이트 일치를 [공개 파일 기록](miniature-kitchen/ios-public-results.json)으로 확인했다. 외부 HTML 렌더러는 이 환경의 연결 403으로 실제 실행 미확인이다.

- [표시창 상세](https://raw.githubusercontent.com/Ohoredingdong/Notion/fdca2d982bf44bb99e206b473b8f4b79756ceecb/docs/miniature-kitchen/ios-detail.png) · [전체 모습](https://raw.githubusercontent.com/Ohoredingdong/Notion/fdca2d982bf44bb99e206b473b8f4b79756ceecb/docs/miniature-kitchen/ios-fridge.png) · [휴대폰 크기](https://raw.githubusercontent.com/Ohoredingdong/Notion/fdca2d982bf44bb99e206b473b8f4b79756ceecb/docs/miniature-kitchen/ios-phone.png)
- [앱 미리보기](https://raw.githack.com/Ohoredingdong/Notion/fdca2d982bf44bb99e206b473b8f4b79756ceecb/previews/mobile/app.html) · [위젯 미리보기](https://raw.githack.com/Ohoredingdong/Notion/fdca2d982bf44bb99e206b473b8f4b79756ceecb/previews/mobile/widget.html)

GitHack 안내가 나타나면 `Open the page`를 누른다. 사용자에게 실제 휴대폰에서 확인됐다고 보고하지 않는다.

`feat/kitchen-play-and-sharp-displays`에 push했다. `design/centered-kitchen`을 기준으로 PR 생성을 시도했지만 `Post "https://api.github.com/graphql": Forbidden`으로 차단됐다. PR·병합·Pages 배포는 완료하지 못했으며 [브랜치 비교](https://github.com/Ohoredingdong/Notion/compare/design/centered-kitchen...feat/kitchen-play-and-sharp-displays?expand=1)에서 검토할 수 있다.
