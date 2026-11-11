# Review draft — PR not created

Base: `fix/kitchen-servings-nutrition-20261110`
Head: `fix/kitchen-nutrition-cards-20261111`
Title: Show per-serving nutrition on recipe cards

추천 목록에 영양이 보이지 않아 요리를 하나씩 열어야 비교할 수 있었습니다. 기존 1인분 영양 보고서를 8개 카드에 읽기 전용으로 연결하고 열량·탄수화물·단백질·지방을 같은 위치의 네 열로 표시합니다. 입력0·참고 추정·일부 재료 소계·미확인을 구분합니다.

좁고 낮은 화면은 제목·가격·영양을 우선하며 시간·재료 정보는 상세와 접근성 설명에 유지합니다. 기존 위젯 프레임·사진·식비·상세·저장 모델은 유지합니다.

검증: Node316, 전송13, 새 카드12/2426단언, 기존25/7073단언 및10쌍 원문 비교 모두 통과. 두 독립 실제 PNG 검토 통과. 4개 HTML은 검사한 바이트 그대로이며 기존11개 이미지·13개 모델/컨트롤러/참고파일은 변경하지 않았습니다. 중간 CSS 실패와 기존 모의 시계 초기화 문제는 findings-and-rechecks.json에 보존했습니다.

docs/KITCHEN_RECIPE_NUTRITION_CARDS_2026-11-11.md 및 docs/artifacts/kitchen-nutrition-cards-20261111/verification.json 참조. 실제Notion/Safari/공개HTMLPreview 실행은 미검증입니다. 금융 Actions·data·main·운영 배포는 변경하지 않았습니다.

GitHub API가 환경 정책으로 차단되어 PR 생성은 완료하지 못했습니다. 작업 브랜치와 이 초안이 검토 대상입니다. 자동 병합·배포는 수행하지 않습니다.
