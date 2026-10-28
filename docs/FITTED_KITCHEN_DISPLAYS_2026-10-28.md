# 냉장고 표시창 크기·위치·비례 수정 · 2026-10-28

사용자가 전체 화면 사진으로 표시창의 어색함을 지적한 뒤 수정을 요청했다. `5cd6e950`의 [세이지색 표시창](SOFT_KITCHEN_DISPLAY_2026-10-27.md)은 미채택 시안이다. 이번 수정은 `feat/kitchen-play-and-sharp-displays`에서 화면의 크기·위치와 정보 배치를 바꾼다.

## 변경

- 공통 표시창 폭은 오른쪽 냉장 문 폭의 82%에서 70%로 줄였다. 바깥쪽 여백은 왼쪽 약 10%, 오른쪽 10%이며 손잡이 주변도 비운다. 냉장고 본체·카메라·배경 위치와 크기는 유지한다.
- 큰 화면의 표시창 높이는 문 높이의 약 46%다. 작은 화면은 읽을 수 있는 글씨를 위해 116px를 기준으로 하되 문 높이의 66%를 넘지 않는다. 아주 짧은 화면은 요약 배치를 사용한다.
- 원본 냉장고 그림의 표시창 홈은 아틀라스 y188~394에 있다. 패널을 줄이자 홈 아래쪽이 노출되는 것을 확인해 실제 홈의 중심에 맞췄다. 짧은 화면에서는 냉장 글씨와의 간격도 확보한다. 그림 원본을 바꾸거나 새로 생성하지 않았다.
- 왼쪽은 넓은 화면에서 재료 3종, 작은 화면에서 2종, 아주 짧은 화면에서 1종과 전체 임박 종류 수를 표시한다. 이름은 일반 배치에서 12~14px, 요약 배치에서 11px다. 수량·기한과 전체 재료는 계속 보관하며 문을 열어 편집할 수 있다.
- 오른쪽은 작은 음식 그림과 메뉴명을 나란히 둔다. 좁은 표시창에서는 작은 그림과 이름을 위아래로 배치하고, 아주 짧은 화면에서는 메뉴명·시간을 우선한다. 조리시간은 기존 레시피 값이며 영양·비용을 추정해 추가하지 않는다.
- 네 문의 직접 개폐, 재료·양념 드래그, 날짜·수량 편집, 식사·영양·도감·보상과 저장 모델은 유지한다. 앱·위젯이 같은 원본을 사용한다.

## 비교와 검증

[이전 전체 구도](miniature-kitchen/fitted-before.png) · [수정 전체 구도](miniature-kitchen/fitted-after.png) · [표시창](miniature-kitchen/fitted-detail.png) · [320px](miniature-kitchen/fitted-320.png)

같은 기본 재료·닫힌 문 상태·시각 `2026-10-28T03:00:00Z`, Asia/Seoul로 앱·위젯 각각 9개 뷰포트를 비교했다. 320/390px의 568px 높이도 포함한다. 본체 정렬, 표시창 홈이 밖으로 노출되는지, 문 가장자리·냉장 글씨와의 여백, 기본 수량·8개 요리명의 잘림을 구분해 확인했다.

649×900 앱 조건의 왼쪽 표시창은 137×213→117×149px로 바뀌어 면적이 약 40.3% 줄었다. 18쌍 모두 본체 x/y/폭/높이는 그대로이며 양쪽 표시창의 폭·높이는 줄었다. 일반 배치의 재료명·메뉴명은 최대 14px로 키웠다.

- 장면 회귀 **111개**, 식사·도감·저장 회귀 **13개**, 표시창 집중 검사 **10개 묶음**, 크기 변경 **13단계**가 통과했다.
- 집중 검사에는 568px 높이의 긴 재료명·500ml 수량·8개 메뉴명·빈 상태와 원본 표시창 홈의 전체 덮임을 포함한다. 짧은 화면에서 냉장 글씨와 겹치던 중간 수정본을 보정한 뒤 통과했다.
- JavaScript 구문, 원본/작은 내장형 UI 일치 및 `git diff --check`도 통과했다.

최종 결과는 [검증 기록](miniature-kitchen/fitted-display-validation.json)에 보관한다. 로컬 Chromium 검사이며 실제 Notion·Safari·사용자 클라이언트 검증이나 사용자의 디자인 승인을 뜻하지 않는다. 기능 검사 통과로 디자인 채택을 대신하지 않는다.

```bash
source /workspace/.notion-cloud/activate.sh
python scripts/build_miniature_kitchen_preview.py --compact --output-dir /tmp/kitchen-fitted
python scripts/test_miniature_kitchen_browser.py --root /tmp/kitchen-fitted --output /tmp/kitchen-fitted-core
python scripts/test_kitchen_journal_browser.py --root /tmp/kitchen-fitted --output /tmp/kitchen-fitted-journal
node --check designs/miniature-kitchen/scene.js
git diff --check
```

## 전달 범위

작은 내장형은 `/workspace/artifacts/kitchen-fitted-displays/`의 앱 924,016바이트·위젯 924,019바이트다. 외부 이미지·CSS·JavaScript 요청이 없으며 원본 그림 내장형 `previews/`도 재생성했다. 앞서 전달한 10개 폴더의 HTML 미리보기도 같은 버전으로 갱신했다. 기존 배포 앱과 사용자 데이터는 수정하지 않았다. 전용 시안 키 `miniature-kitchen-preview-v1`의 형식과 기존 문 상태 복원을 유지한다.

기존 작업 브랜치에 반영하며 main·GitHub Pages는 변경하지 않는다. PR은 앞선 작업에서 GitHub API가 `Forbidden`으로 차단한 상태다.
