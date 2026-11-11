# 추천 카드에서 1인분 영양 비교

사용자는 요리 상세를 열기 전에도 8개 추천 카드를 보고 영양을 비교하도록 요청했다. 사진·이름·가격을 유지하고 같은 위치의 네 열에 `kcal / 탄(g) / 단(g) / 지(g)`를 표시한다. [인분·영양 서비스](KITCHEN_SERVINGS_NUTRITION_2026-11-10.md)의 값과 출처를 그대로 재사용한다.

- 모든 카드 영양은 **1인분** 기준이다. 조리 인분·개인 식사 기록·목표·재고·지출을 변경하지 않는다.
- 직접 입력한 값이 우선이며 0도 유효하다. 참고 추정 자격은 공통 설명과 성분별 설명에 표시한다.
- 확인된 일부 재료만 있으면 `≥`와 소계로 구분한다. 하한은 올림하지 않는다. 미확인은 `—`이며 완전한 숫자0으로 채우지 않는다.
- 가장 낮은 화면은 영양 4개와 제목·가격을 우선한다. 시간·재료 수는 상세와 카드의 접근성 설명에 유지한다. 8개 카드와 기존 위젯 프레임은 유지한다.
- 영양 계산·원자료·저장 모델은 변경하지 않는다. 추천 목록에 읽기 전용 보고서만 연결한다.

## 구현과 확인

[목록 데이터 연결](../designs/miniature-kitchen/home.js), [카드 렌더러](../designs/miniature-kitchen/home-recipe-view.js), [카드 스타일](../designs/miniature-kitchen/recipe-card-nutrition.css)을 수정한다. 별도 작업 브랜치는 `fix/kitchen-nutrition-cards-20261111`이다. 운영 사이트·main·금융 Actions·데이터는 변경하지 않는다.

실제 생성된 네 HTML에서 320×360·390×480·720×800·800×600과 앱 두 크기를 검사한다. 전후 비교는 같은11월11일·초기 기록·조작으로 한다. 카드의32개 값과 상세1인분 값의 일치, 수동0/미확인 구분, 11px 이상 실문자·가로 넘침·가림·44px 선택 영역, 원문 보존을 확인한다.

```bash
python scripts/build_miniature_kitchen_preview.py --compact --output-dir /tmp/kitchen-nutrition-cards
python scripts/build_kitchen_mobile_preview.py --output-dir /tmp/kitchen-nutrition-cards/mobile
node --test tests/*.test.cjs
python scripts/test_kitchen_recipe_card_nutrition_browser.py \
  --before /tmp/kitchen-nutrition-cards-before --root /tmp/kitchen-nutrition-cards \
  --output /tmp/kitchen-nutrition-card-check --browser-executable /usr/bin/chromium
```

변경 전 폴더는 기준 커밋 `25d0dcb909dbaee69ee36461985d588054bc584d`의 `previews/miniature-kitchen-{app,widget}.html`, `previews/mobile/{app,widget}.html` 네 파일을 그대로 복사해 준비한다. 생성·검사 도구 환경은 [공통 규칙](../AGENTS.md)을 따른다.

초기 후보에서 낮은 화면의 시간·재료 행 숨김 규칙이 기존 스타일 우선순위에 밀려 암묵적인 세 번째 행을 만든 문제를 발견했다. 실제 CSS 계산값을 확인해 숨김 우선순위와 두 행의 크기를 고쳤고, 좁은 설명에도 추정 자격을 표시했다. 초기 실패는 최종 결과와 구분해 보존한다.

최종 `after-v2`에서 Node316개·전송13개, 새 카드12조건/2,426개 단언, 기존25조건/7,073개 단언이 모두 통과했다. 두 독립 시각 검토도 통과했고 60개 런타임 소스·검사한4개 HTML의 해시가 동일하다. 11개 원본 이미지 자산은 바이트 그대로 유지했다.

[검증·해시](artifacts/kitchen-nutrition-cards-20261111/verification.json), [시각 검토](artifacts/kitchen-nutrition-cards-20261111/MANUAL_REVIEW.md), [720px 수정 전](artifacts/kitchen-nutrition-cards-20261111/before-cards-720.png) → [수정 후](artifacts/kitchen-nutrition-cards-20261111/after-cards-720.png), [320px](artifacts/kitchen-nutrition-cards-20261111/after-cards-320.png), [390px](artifacts/kitchen-nutrition-cards-20261111/after-cards-390.png), [낮고 넓은 화면](artifacts/kitchen-nutrition-cards-20261111/after-short-wide.png)을 보존한다. 첫 공통 검사는 기존 모의 시계 초기화 경합 때문에 기본 기한의 엄격한 비교가 실패했으며, 원본을 보존하고 최종 실행에서10쌍의 원문·기한이 모두 정확히 일치하는 것을 확인했다.

실제 Notion·Safari·실물 기기·공개 HTMLPreview 실행은 별도 미검증이며 운영 배포·병합은 수행하지 않는다.
