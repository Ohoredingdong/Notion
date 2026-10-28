# 검정 베젤·다크 유리 디스플레이 · 2026-10-28

> 사용자는 검정색이 아닌 흰 냉장고와 어울리는 배경과 더 풍부한 내부 구성을 원한다고 정정했다. 이 시안은 미채택이며 [아이보리 정보형 표시창](IVORY_KITCHEN_DASHBOARD_2026-10-28.md)으로 이어 검토한다.

사용자가 검정 매립형 터치 디스플레이가 있는 실제 냉장고 사진을 제공하며 고급스러운 느낌으로 수정해 달라고 요청했다. `5c00c786`의 밝은 표시창을 기준으로 기존 작업 브랜치에서 **표시창 CSS만** 바꿨다. 참고 사진의 검정 냉장고 전체를 재현하는 작업은 아니다.

## 적용

- 모서리가 작은 검정 베젤, 얇은 금속 가장자리, 안쪽 차콜색 화면과 약한 유리 반사를 사용한다. 큰 그림자나 화면 전체 흐림 필터를 사용하지 않는다.
- `유통기한 임박`·`오늘의 추천메뉴` 제목과 기존 목록·메뉴 구조는 유지한다. 밝은 이름·수량, 얇은 구분선, 작은 음식 그림으로 위계를 구분한다.
- 오늘은 앰버색, 내일은 옅은 금색, 가까운 기한은 연녹색, 지난 기한은 밝은 붉은색으로 표시한다. 색 외에 날짜 문구도 유지한다.
- 작은 표시창의 베젤은 1px 안쪽 여백으로 줄여 제목·수량 공간을 확보한다. 짧은 화면의 요약 배치도 유지한다.
- 냉장고 본체와 배경 원본, 중앙 배치, 표시창 위치·크기, 네 문 개폐와 데이터·저장 코드는 바꾸지 않았다. 앱·위젯이 같은 CSS를 사용한다.

[이전](miniature-kitchen/glass-before.png) · [수정 전체 구도](miniature-kitchen/glass-fridge.png) · [표시창 확대](miniature-kitchen/glass-detail.png) · [휴대폰 크기](miniature-kitchen/glass-phone.png)

## 검증

같은 재료·닫힌 문·고정 시각 `2026-10-28T03:00:00Z`, Asia/Seoul로 앱·위젯의 649×900, 390×660, 320×660, 320×568을 전후 비교했다. 본체와 표시창의 위치·크기가 같은지, 전체 구도와 작은 화면을 함께 확인한다. 결과는 [검증 기록](miniature-kitchen/glass-display-validation.json)에 보관한다.

표시창 집중 검사 **10개 묶음**, 휴대폰 크기·터치 검사 **6개 조건**이 통과했다. 전후 캡처 8쌍 모두 본체와 표시창의 위치·크기가 같다. 기본 표시 텍스트의 대비 검사와 원본/작은 내장형 UI 코드 일치, `git diff --check`도 통과했다. 검사를 통과한 뒤 추가로 전체 회귀 검사를 반복하지 않았으며, 이전 111개/13개 결과를 이번 실행 결과로 세지 않는다.

- 기존 집중 검사로 제목, 이름·수량의 잘림, 원본 표시창 홈 덮임, 손잡이·냉장 글씨와의 간격, 8종 메뉴, 기한/빈 상태, 문 조작을 확인한다.
- 기본 화면의 실제 글자색을 밝은 쪽 화면 배경의 보수적 기준 `#333b46`과 비교해 4.5:1 이상인지 확인한다. 전체 사이트의 접근성 인증을 뜻하지 않는다.
- 공개 확인용 진입점도 로컬 Chromium의 휴대폰 크기·터치 프로필에서 앱·위젯으로 검사한다. 실기기 Safari 검증으로 보고하지 않는다.

```bash
source /workspace/.notion-cloud/activate.sh
python scripts/build_miniature_kitchen_preview.py
python scripts/build_kitchen_mobile_preview.py
```

기존 전체 회귀의 과거 결과와 이번 CSS 집중 검사를 구분한다. 추천 계산·재고 차감·영양 계산 등 기능을 추가했다고 보고하지 않는다. 사용자 디자인 승인은 별도다.

## 전달

작은 내장형은 앱 924,526바이트·위젯 924,529바이트, 공개 휴대폰 확인용은 각각 946,542바이트·946,551바이트다. 휴대폰 확인에는 채팅 내부 파일만 안내하지 않고 공개 HTTPS 이미지와 앱·위젯 주소를 제공한다.

GitHack은 일반 브라우저에서 첫 확인 안내를 띄울 수 있다. 안내가 나오면 빨간 `Open the page` 버튼으로 진행한다. 같은 저장소의 확인은 24시간 유지된다는 [서비스 설명](https://github.com/neoascetic/rawgithack/blob/master/web/index.html#L204)을 확인했다. 외부 렌더러는 이 작업 환경의 접속 차단 때문에 실제 실행을 검증할 수 없으며, 공개 파일의 HTTP 200과 모바일 프로필 검사를 구분한다.

main·기존 GitHub Pages는 수정하지 않는다. 기존 작업 브랜치를 이어 사용하며 PR API 접근 차단 상태도 유지된다.

## 고정된 공개 확인 주소

디자인 파일이 포함된 커밋은 `56a7f5d0d5d5dcf7b8f683bc3e705ebcab0658c9`다. [전체 냉장고 이미지](https://raw.githubusercontent.com/Ohoredingdong/Notion/56a7f5d0d5d5dcf7b8f683bc3e705ebcab0658c9/docs/miniature-kitchen/glass-fridge.png)·[표시창 확대](https://raw.githubusercontent.com/Ohoredingdong/Notion/56a7f5d0d5d5dcf7b8f683bc3e705ebcab0658c9/docs/miniature-kitchen/glass-detail.png)·[휴대폰 화면](https://raw.githubusercontent.com/Ohoredingdong/Notion/56a7f5d0d5d5dcf7b8f683bc3e705ebcab0658c9/docs/miniature-kitchen/glass-phone.png)과 공개 HTML 원본의 HTTP 200 및 로컬 바이트 일치를 확인했다. [공개 접근 기록](miniature-kitchen/glass-public-results.json)을 따른다.

- [앱 미리보기](https://raw.githack.com/Ohoredingdong/Notion/56a7f5d0d5d5dcf7b8f683bc3e705ebcab0658c9/previews/mobile/app.html)
- [위젯 미리보기](https://raw.githack.com/Ohoredingdong/Notion/56a7f5d0d5d5dcf7b8f683bc3e705ebcab0658c9/previews/mobile/widget.html)

미리보기의 GitHack 확인 안내와 이 환경에서 외부 렌더러 실행을 검증하지 못하는 제한은 위 전달 항목과 같다. 원본 파일이 공개돼 있다는 확인과 실제 휴대폰 브라우저에서 실행됐다는 확인은 구별한다.
