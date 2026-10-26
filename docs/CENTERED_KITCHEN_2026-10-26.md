# 냉장고 중앙 구도 복원 · 2026-10-26

사용자가 냉장고가 원래 중앙 정렬이었는데 벽쪽으로 붙었다고 지적하고 수정을 요청했다. 배경에 빈 공간이 있다는 이유로 왼쪽 배치를 확정한 앞선 해석을 바로잡는다. 최신 요구는 **배경과 맞으면서도 화면 중앙에 놓인 냉장고**다.

## 변경

- 따뜻한 타일·아이보리·오크·햇빛의 분위기를 유지하면서 중앙에 넓은 빈 설치 공간, 양옆에 조리대가 있는 배경 `room-centered.png`를 추가했다. 기존 `room.png`와 냉장고 원본은 보존한다.
- 냉장고는 방 좌표 x540.5~995.5, 중심 x768에 놓고 카메라도 이 중심을 따른다. 창 폭이 바뀌어도 냉장고와 사진 영역의 중심 차이를 1px 이내로 검사한다.
- 새 배경의 양쪽 조리대 경계와 y856 바닥선을 기준으로 실제 보이는 발을 맞춘다. 투명한 그림 여백은 제외한다. 카메라 범위를 함께 바꿔 기존에 보이는 본체 크기를 유지한다.
- 냉장고 탭은 냉장고, 양념 탭은 왼쪽 선반, 조리대 탭은 오른쪽 작업대를 보여준다. 양념 전용 작은 선반과 각 구역에 맞는 소품 크기·위치를 조정했다. 냉장고 위를 가리던 설명은 시각적으로 숨기며 접근성 텍스트와 조작 도움말은 유지한다.
- 게임은 사용자의 후속 ‘아이디어’ 요청에 따라 [제안 문서](KITCHEN_GAME_IDEAS.md)로만 정리한다. 영양 게이지·도감·목표·보상·성장 기능은 구현 완료가 아니다.

## 확인

[브라우저 검사](miniature-kitchen/centered-browser-results.json): **111개 통과·실패 0**, 앱·위젯 18개 화면 조건. [연속 크기 변경 13단계](miniature-kitchen/centered-resize-results.json)에서 중앙 정렬·실제 발 위치·입력과 문 상태를 확인했다. 네 문 개폐·마우스/터치 이동·수량/기한·양념·소품·기존 저장소 접근 0 검사를 유지했다.

[전후 기록](miniature-kitchen/centered-comparison.json)은 `57876039`를 기준으로 7개 화면 조건 × 전후 × 기본/닫힘/열림 3상태의 42개 첫 화면을 비교한다. 동일한 예시 기록·문 상태·뷰포트, 시각 `2026-10-25T03:00:00Z`, Asia/Seoul을 사용했다. 본체 폭 차이는 1.5% 미만이며 중앙 정렬·가구 겹침·발 위치를 별도로 검사한다.

- 넓은 앱: [이전](miniature-kitchen/centered-before-app.png), [중앙 배치](miniature-kitchen/centered-after-app.png)
- 위젯: [이전](miniature-kitchen/centered-before-widget.png), [중앙 배치](miniature-kitchen/centered-after-widget.png), [네 문 열기](miniature-kitchen/centered-open-widget.png)

검사는 로컬 Chromium 기준이다. 실제 채팅·Notion·Safari의 새 화면 확인과 사용자 디자인 승인은 별도로 남아 있다. 시안의 예시 데이터는 새로고침하면 초기화되며 기존 앱·기록·배포는 변경하지 않는다.

## 소스·전달

생성 배경 원본은 `/workspace/generated_images/exec-ef809798-c05b-42c1-a68f-39177757af67.png`이며 복사해 사용했다. 앞선 생성 소재도 삭제하지 않았다.

채팅 미리보기는 `/workspace/artifacts/kitchen-centered/miniature-kitchen-app.html`, `miniature-kitchen-widget.html`이다. 외부 이미지 요청이 없는 작은 내장형으로 각각 948,472/948,475바이트다. 원본 그림 내장형 `previews/`도 재생성한다. 소스와 비교 자료는 `design/centered-kitchen` 브랜치에 작성하며 main에 병합·배포하지 않는다. 앞선 PR 생성은 GitHub GraphQL API `Forbidden`으로 차단됐고 현재 PR은 생성되지 않았다.
