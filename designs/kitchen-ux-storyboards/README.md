# 한끼의 부엌 · 동작 설계 시안

2026-11-02 Asia/Seoul. 00전체동선과01~04상세 흐름의 이미지다. 수치/날짜/요리/보상은 설계 예시이며 기존 앱에 구현한 결과를 뜻하지 않는다. 원본PNG를 바이트 그대로 보관하고 화면별 동작은 [DESIGN_SPEC.md](DESIGN_SPEC.md)에 기록한다.

사용자가 채팅의 회색 이미지 미리보기를 보고 표시 문제를 전달했다. 다섯 원본은 정상PNG1448×1086임을 확인했으나 채팅 표시 실패의 원인은 확인하지 못했다. 표시 복구용 뷰어는 한 번에 한 이미지만 요청하고, 원본 열기/확대/재시도를 제공한다. 원본 검사는 [manifest.json](manifest.json)의 바이트/해시를 기준으로 한다.

기존 앱·위젯·운영 URL·저장 키·Pages 설정은 변경하지 않는다.

## 보기

- [00~04 한 장씩 보기](https://htmlpreview.github.io/?https://raw.githubusercontent.com/Ohoredingdong/Notion/b5f13a245a7e4003f0207c8cfc5fe802707b9854/previews/kitchen-ux-storyboards.html)
- 탭 선택 → 크게 보기 또는 원본 열기로 글씨를 확대한다.

원본 PNG:

- [00 전체 동선](https://raw.githubusercontent.com/Ohoredingdong/Notion/f18a75c851dfbc3fb69612063dd18fe8cede1d28/designs/kitchen-ux-storyboards/00-overview.png)
- [01 재료 등록](https://raw.githubusercontent.com/Ohoredingdong/Notion/f18a75c851dfbc3fb69612063dd18fe8cede1d28/designs/kitchen-ux-storyboards/01-ingredients.png)
- [02 식단·식사](https://raw.githubusercontent.com/Ohoredingdong/Notion/f18a75c851dfbc3fb69612063dd18fe8cede1d28/designs/kitchen-ux-storyboards/02-meals.png)
- [03 영양·식비](https://raw.githubusercontent.com/Ohoredingdong/Notion/f18a75c851dfbc3fb69612063dd18fe8cede1d28/designs/kitchen-ux-storyboards/03-records.png)
- [04 도감·꾸미기](https://raw.githubusercontent.com/Ohoredingdong/Notion/f18a75c851dfbc3fb69612063dd18fe8cede1d28/designs/kitchen-ux-storyboards/04-growth.png)

## 표시 검증

이미지 pin은f18a75c8, 뷰어 pin은b5f13a24다. [실제 공개 결과](display-public-results.json)는390×844/1120×1000/320×568의3개 프로필에서5장씩15회 HTTP200·원본SHA/바이트 일치·1448×1086디코딩·JS오류0을 확인했다. 최초PNG요청1개, 단일이미지 교체, 44px탭·원본링크·확대1448px내부스크롤도 확인했다. [실행](https://github.com/Ohoredingdong/Notion/actions/runs/41439401049).

[로컬 검사](display-local-results.json)는 일시 로드실패→안내/원본열기/재시도 복구와 키보드 이동도 확인했다. 실제 공개 폰크기/확대 스크린샷에서 시안이 그려지는 것을 별도로 확인했다. 이는 ChatGPT 클라이언트의 회색 첨부 칸 원인이나 복구 성공을 증명하는 것은 아니며 실제 휴대폰/Safari/Notion 검증과 구분한다.

별도design/kitchen-ux-storyboards브랜치에 보관했다. basefix/kitchen-purpose-navigation로 draft PR 생성 시도는 GitHub GraphQL API403 Forbidden으로 실패했다. [비교/PR 작성](https://github.com/Ohoredingdong/Notion/compare/fix/kitchen-purpose-navigation...design/kitchen-ux-storyboards?expand=1). 검증용CI는delivery/verify-kitchen-storyboards-20261102, 결과는preview/kitchen-storyboards-display-20261102에만 게시했다.
