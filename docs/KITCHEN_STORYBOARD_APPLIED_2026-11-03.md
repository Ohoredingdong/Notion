# 첨부한 네 장의 시안을 실제 화면에 적용

사용자는 앞선 외형 수정 이후에도 실제 위젯이 첨부한 A1~D6 시안과 다르다고 정정했다. 이번 변경은 사진과 입력 행, 카드의 순서, 다음 화면 연결을 기준으로 실제 화면 구성을 다시 적용한다. 지난 기능 검사 통과를 디자인 승인으로 취급하지 않는다.

| 흐름 | 실제 변경 |
| --- | --- |
| A1~A6 재료 | 거의 정사각형인 냉장고 홈, 작은 균형 카드, 큰 보관통 사진, 파란 우유 팩, 떠 있는 추가 버튼. 등록 방법 → 사진 두 장 → 왼쪽 입력 행·오른쪽 검수 안내 → 실제 새 재료 강조. 상세는 배경 위의 행 입력 시트. |
| B1~B6 레시피 | 추천 요리/내 식단, 작동하는 시간·예산·피할 재료 필터, 사진 카드와 보조 두 장. 요리 상세의 재료·순서와 두 행동, 날짜/끼니/분량 계획, 실제 수량 전후, 하루 균형과 완료·실행 취소. |
| C1~C6 기록 | 파스텔 균형 카드와 식사 행, 영양제 제품/일정 시트. 선택한 날짜 주변 2주 달력과 전체 달력 펼치기, 실제 기록의 도넛, 식비 세 열, 장보기 수량 조작, 실제 지출과 선택적 입고. |
| D1~D6 내 부엌 | 목표·꾸밈권·오늘의 균형과 닫힌 부엌. 8개 실제 요리의 3열 도감, 첫 기록 사진·보상, 실제 기본 소품/보상 소품 선택, 배치 도구. 적용 후 닫힌 냉장고와 실제 진행 카드. |

메인 메뉴는 `냉장고 / 레시피 / 기록 / 내 부엌`이다. `내 식단`의 계획 개념과 내부 `meals` 경로는 유지한다. 도감의 미기록 요리도 기본 정보를 볼 수 있다. 기본 소품을 꾸밈권 유료 상품으로 바꾸거나 실제 없는 상품·재료·영양값을 추가하지 않는다.

공통 소스는 `designs/miniature-kitchen/`이며, 화면별 추가 스타일은 `scene-screens.css`, `home-screens.css`, `workflow-screens.css`, `growth-screens.css`다. 앱·위젯과 모바일 전달 화면을 같은 소스로 생성한다. 320px 집중 화면은 전체 높이와 너비를 써서 하단 저장 버튼과 날짜 입력이 잘리지 않게 한다. 홈은 작은 화면에서도 별도로 짧게 유지한다.

## 이미지와 전달

기존 식재료 사진은 보관통 크기로 표시한다. 우유는 새 투명 원본과 원본 픽셀을 유지한 AVIF를 사용한다. 식재료 아틀라스도 원본 1536×1024 AVIF로 전달한다. 두 AVIF는 크림/회색 배경의 합성 PSNR·SSIM이 비교 WebP82보다 높으며, 투명 가장자리의 작은 알파 오차는 실제 합성 화면에서 확인했다. 원본 PNG는 보존한다. 측정은 [이미지 비교 기록](kitchen-storyboard-applied/codec-report.json)에 둔다.

HTML은 기존 무손실 gzip/base85 포장을 사용한다. 네 전달 파일 각각의 1MiB 상한과 원문 바이트 복원을 검사한다. 화질이나 기능을 삭제해서 맞추지 않는다.

## 데이터와 검증 범위

저장 키 `miniature-kitchen-preview-v1`, v1 형식과 기존 재료 ID·수량·기한·좌표·기록·보상은 유지한다. 계획 저장은 재고를 차감하지 않는다. 실제 식사 저장과 취소, 첫 요리 보상 1회, 실제 구매 지출과 재료 입고의 구분을 확인한다. 꾸미기 취소는 편집 초안을 폐기하고, 적용은 배치를 저장한 뒤 닫힌 앞면을 보여 준다. 기존 운영 HTML과 main/Pages는 수정하지 않는다.

확인한 로컬 검사: 모델 49개, 전달 포장 12개, 홈 화면 조작 32개, 워크플로 15개, 도감·소품 10개. 화면 비교는 동일한 명시적 예시 데이터로 진행한다. 사진 검수 화면을 여는 검사에는 브라우저 안의 인식 결과 예시를 사용했으며 실제 OCR 실행 증거가 아니다. Chromium의 모바일 크기 확인은 실제 휴대폰·Safari·Notion 검증을 뜻하지 않는다.

최종 구현은 `5d1c0a8f314294ba31c23be517f477b88ed7de24`다. 전달 크기는 앱 1,028,219B, 위젯 1,028,226B, 모바일 앱 1,029,566B, 모바일 위젯 1,029,579B다. [생성 파일의 SHA와 원문 복원](kitchen-storyboard-applied/generated-files.json)을 기록했다.

## 실제 화면

[수정한 위젯 열기](https://htmlpreview.github.io/?https://raw.githubusercontent.com/Ohoredingdong/Notion/5d1c0a8f314294ba31c23be517f477b88ed7de24/previews/mobile/widget.html)

[네 메뉴의 실제 실행 화면](kitchen-storyboard-applied/widget-updated.png)은 별도 예시 데이터의 최종 전달물(release5)을 캡처한 것이다. 계란 볶음밥 한 끼의 입력값 455kcal/60g/20g/15g과 목표 230g/70g/60g을 사용했으며 실제 사용자 데이터나 전후 비교 자료와 혼동하지 않는다. [소개용 캡처 출처](kitchen-storyboard-applied/showcase-manifest.json)를 별도로 둔다.

| 흐름 | 선택한 실제 화면 |
| --- | --- |
| 재료 | [등록 방법](kitchen-storyboard-applied/A2-add.png), [사진 선택](kitchen-storyboard-applied/A3-selected.png), [검수 행과 안내](kitchen-storyboard-applied/A4-review.png), [담은 재료 강조](kitchen-storyboard-applied/A5-saved.png), [재료 상세](kitchen-storyboard-applied/A6-detail.png) |
| 레시피·식사 | [상세](kitchen-storyboard-applied/B2-detail.png), [계획](kitchen-storyboard-applied/B3-plan.png), [차감 전후](kitchen-storyboard-applied/B4-eaten.png), [끼니별 계획](kitchen-storyboard-applied/B5-plans.png), [기록 완료](kitchen-storyboard-applied/B6-success.png) |
| 기록·지출 | [영양제 상세](kitchen-storyboard-applied/C2-detail.png), [달력·도넛](kitchen-storyboard-applied/C3-month.png), [식비](kitchen-storyboard-applied/C4-budget.png), [장보기](kitchen-storyboard-applied/C5-shopping.png), [실제 구매](kitchen-storyboard-applied/C6-batch.png) |
| 도감·꾸미기 | [도감](kitchen-storyboard-applied/D2-book.png), [첫 기록](kitchen-storyboard-applied/D3-first-record.png), [소품 선택](kitchen-storyboard-applied/D4-rewards.png), [배치](kitchen-storyboard-applied/D5-decor.png), [적용한 홈](kitchen-storyboard-applied/D6-applied.png) |

기본 시각 자료는 동일한 예시 데이터의 기존 화면 19개와 수정 화면 27개(390×560), 작은 화면의 핵심 11개(320×568)를 비교했다. release3 캡처 뒤 바뀐 금색 강조·닫힌 홈은 release4에서 두 크기로 재확인했다. 마지막 release5에서는 기록이 있는 열린 홈의 추가 버튼과 닫힌 홈의 진행 카드를 실제 버튼으로 4개 조건 검사했다. [최종 추가 버튼/닫힌 홈 검사](kitchen-storyboard-applied/open-closed-controls.json), [홈 조작](kitchen-storyboard-applied/home-actions-results.json), [워크플로](kitchen-storyboard-applied/workflow-checked-results.json)에 결과를 구분한다. 과거 캡처를 최신 바이너리에서 다시 실행한 것으로 표시하지 않는다.

공개 실행 결과는 [공개 HTTPS 검사](kitchen-storyboard-applied/public-status.json)에 기록한다. 실제 공개 링크에서 앱/위젯 각각 320·390·649px를 실행하고 원문·모듈·스타일·네 이미지와 실제 터치·문·입력·꾸미기 취소를 확인한다. 마지막 추가 버튼 회귀 검사는 각 임시 브라우저에 식사 한 끼 예시를 명시적으로 기록한 뒤 열린/닫힌 홈을 확인하며 실제 사용자 저장·OCR 검사와 구분한다.

최종 소스 `5d1c0a8f`의 공개 검사 **6/6 통과**, 런타임 오류 0개다. [실제 실행](https://github.com/Ohoredingdong/Notion/actions/runs/41582346737)의 검증 코드 `f31d1f8dc7bdf6d395973751219772cf160100d9`와 결과 커밋 `14b1ccf1d1782cdc6878a8c13dc5b0de43bf514d`를 구분한다. 이전 `e3048f3c` 공개 검사와 별개로 최종 추가 버튼 수정까지 확인했다.

PR 생성은 `gh pr create --draft`의 GitHub GraphQL 요청이 `Forbidden`으로 차단되어 완료하지 못했다. 작업 브랜치와 공개 미리보기는 push했고 main/Pages는 변경하지 않았다. [브랜치 비교](https://github.com/Ohoredingdong/Notion/compare/feat/kitchen-storyboard-widget...fix/kitchen-storyboard-fidelity?expand=1)로 변경을 검토할 수 있다.
