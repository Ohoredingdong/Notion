# 화이트 냉장고 표시창 소재·위계 수정 · 2026-10-28

후속 요청의 현재 화면은 [iOS 느낌의 표시창](IOS_KITCHEN_DISPLAYS_2026-10-29.md)이다. 아래 이미지와 고정 주소는 이전 시안의 기록이다.

사용자는 아이보리 정보형 시안에서 표시창 디자인을 더 고급스럽게 다듬어 달라고 요청했다. 기준은 `a8781a40`이며, 흰 냉장고에 어울리는 밝은 화면과 풍부한 정보 구성이라는 직전 결정은 유지한다.

샴페인빛 실버 가장자리와 펄 화이트 화면을 사용하고, 제목 아래에 가는 구분선을 둔다. 왼쪽의 세 개 색상 카드는 한 줄 기한 요약으로 바꾸고, 재료 그림·이름·수량·기한의 위계를 정리했다. 오른쪽 음식 그림에는 옅은 크림색 바탕을 두고, 조리 정보는 짧은 한 줄로 묶으며 재료 기록률·미등록 재료를 하나의 하단 영역에 배치했다. 메뉴·재료 이름의 굵기도 낮췄다.

변경 소스는 `scene.css`와 `scene.js`의 표시용 묶음 요소 하나다. 데이터 계산·저장 형식·원본 그림·냉장고 좌표와 크기·문 개폐는 변경하지 않는다. 왼쪽 `유통기한 임박`, 오른쪽 `오늘의 추천메뉴`와 이름 기준 재료 기록률의 의미도 그대로다. 작은 화면에서는 기존 compact/summary 구성에 맞춰 간격을 줄이며, 요리명이나 수량을 작게 축소해 맞추지 않는다.

[변경 전](miniature-kitchen/pearl-before.png) · [표시창 상세](miniature-kitchen/pearl-detail.png) · [전체 냉장고](miniature-kitchen/pearl-fridge.png) · [휴대폰 크기](miniature-kitchen/pearl-phone.png)

## 확인 범위

- 같은 기본 재료·닫힌 문·고정 시각 `2026-10-28T03:00:00Z`, Asia/Seoul에서 앱·위젯을 각각 비교했다. 649×900, 390×660, 320×660, 320×568의 8쌍 모두 냉장고와 표시창의 위치·크기가 동일하다.
- 장면 회귀 111개와 13단계 크기 변경 검사를 통과했다. 네 문, 재료·양념 편집과 드래그, 꾸미기, 재로드 저장 및 기존 데이터 키 보존을 포함한다.
- 집중 검사 12개 묶음에서 앱·위젯 각각 11개 화면 조건, 8종 요리명, 수량, 빈 상태·기한 경과·기록률을 확인했다. 첫 수정에서 짧은 화면의 긴 요리명이 영역을 넘는 것을 발견해 summary 여백을 줄였고, 기존 단언을 유지한 채 최종 소스로 다시 통과했다.
- 3개 화면 구성의 기본/기한 경과 상태에서 계산한 글자 대비는 최소 약 4.59:1이다. 실제 글자색과 가까운 불투명 바탕색을 사용하고, 화면 그라데이션에는 더 어두운 `#f1eadc`를 보수적 기준으로 사용했다. 모든 접근성 항목을 전수 검증했다는 의미는 아니다.
- 공개 확인용 프레임의 로컬 Chromium 휴대폰 크기·터치 검사 6개 조건은 마지막 단독 실행에서 통과했다. 앞선 두 실행에서는 문을 누른 뒤 닫힌 상태가 유지되거나 `main.shell`이 터치를 가로챈다는 자동화 오류가 있었다. 별도 좌표·이벤트 진단과 변경 전 파일의 6개 조건은 통과했지만, 간헐 실패의 원인은 아직 확정하지 못했다. 이를 수정 완료나 실기기 안정성 검증으로 보고하지 않는다.
- 원본/작은 내장형 UI 코드 일치, JavaScript 구문과 `git diff --check`를 확인했다. 식사·도감 모델과 저장 코드는 이번 변경 대상이 아니며 해당 전체 회귀를 새로 실행한 것으로 보고하지 않는다.

상세 결과는 [검증 기록](miniature-kitchen/pearl-display-validation.json)을 따른다. 실제 iPhone/Safari·Notion 실행과 사용자 디자인 승인은 미확인이다. 공개 프레임의 임시 저장 및 외부 렌더러의 `Open the page` 안내는 [모바일 전달 문서](MOBILE_KITCHEN_PREVIEW.md)와 같다. 기존 앱·main·GitHub Pages는 변경하지 않는다.

```bash
source /workspace/.notion-cloud/activate.sh
python scripts/build_miniature_kitchen_preview.py
python scripts/build_kitchen_mobile_preview.py
```

작은 내장형은 앱 931,765바이트·위젯 931,768바이트, 공개 확인용은 954,978바이트·954,987바이트다. 외부 그림 요청은 없다.

## 공개 확인 주소와 검토 상태

화면 파일이 포함된 커밋은 `3b9f6a81322851a1a86f7ad2267c76fc8c8a3a17`이다. 아래 PNG 세 개와 앱·위젯 HTML 원본의 HTTP 200 및 로컬 바이트 일치를 확인했다. [공개 파일 검사](miniature-kitchen/pearl-public-results.json)는 HTML 원본 접근과 렌더러 실행을 구분한다. 외부 HTML 렌더러는 이 환경에서 연결 403으로 실행 미확인이다.

- [표시창 상세](https://raw.githubusercontent.com/Ohoredingdong/Notion/3b9f6a81322851a1a86f7ad2267c76fc8c8a3a17/docs/miniature-kitchen/pearl-detail.png) · [전체 모습](https://raw.githubusercontent.com/Ohoredingdong/Notion/3b9f6a81322851a1a86f7ad2267c76fc8c8a3a17/docs/miniature-kitchen/pearl-fridge.png) · [휴대폰 크기](https://raw.githubusercontent.com/Ohoredingdong/Notion/3b9f6a81322851a1a86f7ad2267c76fc8c8a3a17/docs/miniature-kitchen/pearl-phone.png)
- [앱 미리보기](https://raw.githack.com/Ohoredingdong/Notion/3b9f6a81322851a1a86f7ad2267c76fc8c8a3a17/previews/mobile/app.html) · [위젯 미리보기](https://raw.githack.com/Ohoredingdong/Notion/3b9f6a81322851a1a86f7ad2267c76fc8c8a3a17/previews/mobile/widget.html)

GitHack 안내가 나타나면 `Open the page`를 누른다. 이는 외부 렌더러의 문서 확인 단계이며 앱 오류로 해석하지 않는다.

작업 브랜치 `feat/kitchen-play-and-sharp-displays`에 push했다. `design/centered-kitchen`을 기준으로 PR 생성을 시도했지만 `Post "https://api.github.com/graphql": Forbidden`으로 차단되어 PR은 생성하지 못했다. [브랜치 비교](https://github.com/Ohoredingdong/Notion/compare/design/centered-kitchen...feat/kitchen-play-and-sharp-displays?expand=1)에서 검토할 수 있다. main 반영·병합·Pages 배포는 하지 않았다.
