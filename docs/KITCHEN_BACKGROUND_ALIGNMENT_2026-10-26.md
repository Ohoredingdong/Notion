# 냉장고와 부엌 배경의 위치 정합 · 2026-10-26

사용자는 앞선 수정본에서도 냉장고 위치가 배경과 맞지 않는다고 지적했다. 화면 안의 크기와 버튼만 검사하고 실제 설치 공간을 제대로 맞추지 못했다. 이 문서가 현재 배치 기준이며, [앞선 뷰포트 수정](KITCHEN_LAYOUT_FIX_2026-10-26.md)은 변경 경과로 보존한다.

## 확인한 원인과 변경

원본 `room.png`의 왼쪽 타일 공간은 x555에서 끝나고 오른쪽 조리대가 시작한다. 앞선 본체는 x130~660이라 조리대 안으로 105px 들어갔다. 옆 수납장 바닥선은 y905인데 냉장고 배치 상자는 y984까지 내려와 있었다. 같은 좌표와 축척을 사용해도 그 좌표 자체가 배경의 공간과 맞지 않았다.

본체를 x95~550의 빈 타일 공간에 넣었다. 실제 그림의 발은 994px 자르기 영역 중 y987까지 보이므로 투명 여백을 제외해 바닥선을 맞춘다. 새 배치 상자의 하단 y911에서 실제 발은 약 y905.4에 놓인다. 문을 연 상태에서 돌출되는 문과 닫힌 본체의 설치 범위는 구분한다.

냉장고를 보는 카메라는 위의 빈 벽과 앞쪽 바닥을 덜 보도록 조정했다. 배경·냉장고·재료는 같은 공간 안에서 확대하며 **화면에 보이는 냉장고 크기를 유지**한다. 방의 실제 재료와 그림은 교체하지 않았다. 작은 재료는 44px 조작 크기를 유지한다.

양념·조리대 탭은 해당 공간을 보여주며, ‘꾸미기’는 넓은 앱에서도 조리대로 이동한다. 화면 밖 지점을 시험용 드래그 대상으로 삼지 않고 실제 탭을 눌러 보이는 공간에서 이동을 검사한다.

## 같은 뷰포트·기록·문 상태의 비교

기준은 `9e302907`, 시각은 `2026-10-25T03:00:00Z`, 시간대는 Asia/Seoul로 고정했다. 7개 화면 조건 × 전후 × 기본/닫힘/열림 3상태의 42개 첫 화면을 비교했다. 기록의 이름·수량·기한·보관 칸과 문 상태는 같다. 재료 가장자리는 조작 크기에 따라 위치가 제한될 수 있다.

| 화면 | 이전 본체 폭 | 수정 본체 폭 |
| --- | ---: | ---: |
| 앱 1120×900 | 356.09px | 355.73px |
| 위젯 649×660 | 220.39px | 220.16px |
| 위젯 649×900 | 344.61px | 344.26px |
| 위젯 390×660 | 206.00px | 205.78px |
| 위젯 320×660 | 188.73px | 189.80px |
| 앱 760/761×660 | 231.88px | 231.64px |

- 문을 닫고 배경과 비교: [이전](miniature-kitchen/background-before-app-closed.png), [수정](miniature-kitchen/background-after-app-closed.png)
- 위젯 기본 화면: [이전](miniature-kitchen/background-before-widget.png), [수정](miniature-kitchen/background-after-widget.png)
- [수정 후 네 문 열림](miniature-kitchen/background-after-open.png), [배경 기준 수치](miniature-kitchen/background-alignment-comparison.json)

## 검증과 전달

[최종 브라우저 결과](miniature-kitchen/background-alignment-browser-results.json): **111개 통과·실패 0**, 앱·위젯 18개 화면 조건. [13단계 크기 변경](miniature-kitchen/background-alignment-resize-results.json)에서도 배경 정합과 입력·문 상태를 확인했다. 전후 14개 배치에서 본체 폭 차이는 1.5% 미만이다. JavaScript 구문 검사·`git diff --check`도 통과했다. 채팅용 HTML은 앱 939,906바이트, 위젯 939,909바이트다.

위치 검사는 원본 배경의 조리대 시작점·벽 모서리·수납장 바닥선과 냉장고 그림의 불투명한 발 위치를 비교한다. 기존의 실제 뷰포트 검사, 네 문 개폐, 마우스/터치 이동, 양념 기한, 소품 배치, 저장소 접근 0 검사도 유지한다. 그림을 보지 않고 검사 통과만으로 사용자 디자인 승인을 보고하지 않는다. 검사는 로컬 Chromium 기준이며 실제 채팅·Notion·Safari의 새 화면 확인은 별도로 남아 있다.

채팅용 파일은 `/workspace/artifacts/kitchen-position-fixed/miniature-kitchen-app.html`, `miniature-kitchen-widget.html`이다. 기존 전달 경로도 같은 최종 파일로 갱신한다. 변경 대상은 독립 시안이며 기존 서비스·데이터·배포를 수정하지 않았다. 원본 그림도 그대로다. 소스·검사·비교 자료는 기존 작업 브랜치 `fix/miniature-kitchen-viewport`에 추가한다. 앞선 draft PR 생성은 GitHub GraphQL API의 `Forbidden`으로 차단됐으며 PR은 생성되지 않았다.
