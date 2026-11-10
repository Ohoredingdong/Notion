# 만들 인분·개인 식사·영양 비교

사용자는 만들 인분 선택, 레시피 영양 정보와 식재료의 역할, 오늘 남은 탄수화물·단백질·지방 및 당류·나트륨 관리를 요청했다. 기존 `회분` 입력을 명확히 하고 레시피와 오늘 기록을 연결한다. [기존 비용·수량 표시](KITCHEN_RECIPE_COST_DETAIL_2026-11-10.md)와 [11월 9일 프레임](KITCHEN_REFRESH_APPLIED_2026-11-09.md)은 이어간다. 작업 브랜치는 `fix/kitchen-servings-nutrition-20261110`이다.

## 만드는 양과 먹은 양

- 상세의 **만들 양 n인분**은 필요한 재료·장보기 제안·총비용에 반영한다. 영양 표와 오늘의 비교는 **개인 1인분**이며, n인분 전체를 개인 섭취량으로 합산하지 않는다.
- 신규 계획은 선택한 만들 양을 `servingBasis:'cooking'`과 함께 저장한다. 계획은 재고나 영양 기록을 변경하지 않는다. 표시가 없는 기존 계획은 기존 분량의 의미를 보존한다.
- 새 요리에서 실제 식사 기록을 열면 개인 섭취량은 기본1인분이다. 저장 전에 **내가 먹은 인분**을 조정한다. 기존 식사 수정·이전 계획은 저장된 분량을 유지한다.
- 재고 차감 제안은 개인 섭취량 기준이다. 다른 사람의 인분까지 조리했다면 **재고 확인 → 실제 사용량**에서 전체 사용량을 함께 조정한다. 저장 전에는 차감하지 않는다.

## 레시피의 영양값과 출처

열량·탄수화물·단백질·지방·식이섬유·수분·칼슘·나트륨·총당류를 구분한다. 기존 직접 입력한 1인분 영양값이 최우선이며 **입력한0도 유효한 값**이다. 참고값은 성분별로 모든 재료가 확인됐을 때 전체 추정으로 표시하고, 빠진 재료가 있으면 전체값은 `null`, 확인된 합계와 누락 재료를 별도로 보여 준다.

[선별 참고 자료](artifacts/kitchen-nutrition-20261110/reference-provenance.json)는 [고정한 SR28 게시본](https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb) 중 실행 코드가 사용하는14개 식품의 사실만 담는다. 원문 성분번호·단위·행·중량·파일 해시를 보존하며 전체 데이터베이스나 다른 앱 코드는 복사하지 않는다.

| 날짜·단위 | 의미 |
| --- | --- |
| 2015년9월 | USDA SR28 자료판. 2026년 현재 제품 분석값이 아님 |
| 식품별 관측일 | 확인하지 못했으므로 발행일을 관측일로 표시하지 않음 |
| 2026-11-10 | 자료 확인·앱 편입 가능일 `availableFrom`. 이전 날짜에 새 참고값을 사용하지 않음 |
| 원문 기준량 | 명시된 생것·익힌 상태의 가식부100g |

원 USDA 제공처 직접 대조와 이용 조건 확인은 하지 못했다. 제3자 게시본과 그 안의 원형 SR28 설명서를 확인한 범위다. 가격 참고 자료의2026-10-23 조사일과 영양 자료의2015년 자료판을 혼동하지 않는다.

계란 크기·양파200g·밥210g·요거트15g 등 선택 중량과 조리 전후 상태를 계산 가정에 표시한다. 두부는 **16427 일반 칼슘응고 두부**이며 원문 `Tofu, raw, regular, prepared with calcium sulfate`를 유지한다. 다른 두부·응고제·제품과 특히 칼슘이 달라질 수 있다. 단립종 익힌 밥20453의 식이섬유·총당류는 원자료에 없어 `null`로 남긴다.

생애호박·된장의 검증된 같은 식품 자료는 없어 다른 호박·miso로 치환하지 않는다. `소금 조금`처럼 중량이 없는 양념을 임의 계량하지 않는다. 원자료 수분은 **g**이며 기존 **mL** 수분 기록으로 자동 변환하지 않는다. 식재료와 영양소의 역할 설명은 일반적인 정보이며 치료 효과나 개인의 의학적 안전 판정이 아니다.

## 오늘 남은 목표와 관리 기준

오늘 기록된 식사와 기존 개인 목표를 성분별로 비교한다. 탄단지 등은 목표량, **총당류·나트륨은 직접 정한 관리 기준**으로 표현한다. 총당류에는 과일·우유의 당도 들어가며 유리당·첨가당 기준과 같지 않다. 새로운 보편 상한이나 질환별 기준을 임의로 설정하지 않는다.

오늘 기록이 없거나 목표가 없으면 설정·기록을 안내한다. 한 끼라도 해당 영양값이 빠져 있으면 정확한 잔여량과 식사 추가 후 예측을 표시하지 않는다. 다만 확인된 당류·나트륨 소계만으로 이미 기준을 넘으면 **최소 초과량**임을 표시한다. 기록하지 않은 식사는 계산에 포함하지 않는다. 이 비교를 “더 먹어도 안전”이나 “이제 먹지 말아야 함”으로 단정하지 않는다.

## 실제 식사에 참고값 반영

기록 창의 **참고 영양값 불러오기**를 사용자가 눌러야 확인된 참고 성분을 가져온다. 이미 입력한 값·명시한0은 덮어쓰지 않으며 부분 합계·미확인 성분은 빈칸으로 유지한다. 분량을 바꾸면 선택한 참고 성분과 수동 입력의1인분 기준을 각각 유지해 다시 계산한다.

참고값을 선택해 저장한 거래에는 선택 필드 `nutritionSource`를 붙인다. `kind:'reference-confirmed'`, `referenceId`, `fields`, `baseValues`, `values`로 어떤 성분·1인분 기준·저장량을 썼는지 구분한다. 수동으로 고친 성분은 참고 태그에서 제외한다. 기존 수동 기록에 이 태그를 소급해서 붙이지 않으며 편집·취소·복구에서도 저장된 출처와 값을 보존한다.

기존 저장 키·버전과 자료를 보존하고 신규 계획·거래에 선택 메타데이터만 허용한다. 비용·실제 지출·영양은 별도다. 참고 영양 표시나 계획 저장을 실제 구매 지출로 계산하지 않는다.

## 구현과 검증

실행 경로는 [영양 참고값](../designs/miniature-kitchen/nutrition-reference.js), [레시피 추정](../designs/miniature-kitchen/recipe-nutrition.js), [오늘의 비교](../designs/miniature-kitchen/nutrition-insight.js), [영양 화면](../designs/miniature-kitchen/recipe-nutrition-view.js), [기록 연결](../designs/miniature-kitchen/workflows.js)이다. 실제 생성 HTML의320·390·720px, 낮은 위젯과 앱을 같은 데이터·날짜로 비교한다.

`--before`에는 변경 전 커밋 `e4a782e99db4a5bb8fc48334879c16fa2bd7b9ed`의 `previews/miniature-kitchen-{app,widget}.html`과 `previews/mobile/{app,widget}.html`을 그대로 복사한 폴더를 지정한다. 원본 네 파일과 최종 네 파일은 검사 중 수정하지 않는다.

```bash
python scripts/build_miniature_kitchen_preview.py --compact --output-dir /tmp/kitchen-nutrition
python scripts/build_kitchen_mobile_preview.py --output-dir /tmp/kitchen-nutrition/mobile
node --test tests/*.test.cjs
python scripts/test_kitchen_nutrition_browser.py --root /tmp/kitchen-nutrition \
  --before /tmp/kitchen-nutrition-before \
  --output /tmp/kitchen-nutrition-service-check --browser-executable /usr/bin/chromium
python scripts/test_kitchen_refresh_browser.py --root /tmp/kitchen-nutrition \
  --output /tmp/kitchen-nutrition-regression --browser-executable /usr/bin/chromium
```

| 검사 | 현재 확인한 범위 |
| --- | --- |
| Node | 316개 통과, 실패0·건너뜀0. 새 영양 모델·저장 메타43개 포함 |
| 컴포넌트 | 초기 소스15개·120개 단언 통과. 최종4개 HTML의 전체 회귀를 대신하지 않음 |
| 새 서비스 | 최종 `after-v6`14/14·751개 단언 통과, 전후 캡처16개 완전성 확인 |
| 기존 회귀 | 최종25/25·7,073개 단언, 상세18/18·1,648개 단언, 분수8/8·976개 단언 통과 |
| HTML 전송·자산 | 전송13개 통과. 최종4개 모두1MiB 미만, 기존11개 이미지 바이트 보존 |
| 시각·자료 보존 | 실제8프로필·200개 검사와 내비게이션40개 검사 통과, PNG12장 직접 검토. 초기 원문·프레임8쌍 동일 |
| 전달물 | 검사한4개 HTML을 정확히 복사하고59개 런타임 소스 해시를 동결함 |

[최종 검증·전달물 해시](artifacts/kitchen-nutrition-20261110/verification.json), [실제 시각 검토](artifacts/kitchen-nutrition-20261110/MANUAL_REVIEW.md), [발견·수정·재검증 이력](artifacts/kitchen-nutrition-20261110/findings-and-rechecks.json)을 보존한다. 첫 전체 검사에는 모의 시계 초기화 경합으로 기본 기한17개가 달라져 엄격한 원문 비교가 실패했다. 이 실패와 별도 재현은 보존했으며, 최종 전체 검사는 모든 기본 기한·원문이 이전 값과 정확히 일치해야 통과한다. 공개 HTMLPreview 실행 검증으로 대체하지 않는다.

[수정 전 720px](artifacts/kitchen-nutrition-20261110/before-nutrition-720.png) → [수정 후 720px](artifacts/kitchen-nutrition-20261110/after-nutrition-720.png), [320px](artifacts/kitchen-nutrition-20261110/after-nutrition-320.png), [개인 식사량](artifacts/kitchen-nutrition-20261110/personal-meal-720.png), [관리 기준 설정](artifacts/kitchen-nutrition-20261110/targets-320.png)을 확인한다. [부분 기록 안내 예시](artifacts/kitchen-nutrition-20261110/qa-example-partial-guidance.png)는 검증용 목표·식사 자료이며 사용자 기록이 아니다.

검토 증거 경로는 `docs/artifacts/kitchen-nutrition-20261110/`이다. 실제 Notion·Safari·실물 기기·공개 HTMLPreview 실행은 미검증이다. main 병합·운영 배포와 기존 Actions·금융 자동 갱신은 변경하지 않는다.

공개4개 HTML·선별 화면 PNG는 모두HTTP200 응답과 검사한 바이트 일치를 확인했다([공개 파일 검증](artifacts/kitchen-nutrition-20261110/public-access.json)). GitHub API는 환경 정책으로 차단되어 PR 생성은 완료하지 못했으며, [base·head와 검토 설명 초안](artifacts/kitchen-nutrition-20261110/PR_DRAFT.md)을 보존했다. 작업 브랜치만 게시했고 운영 배포·main 병합은 수행하지 않았다.
