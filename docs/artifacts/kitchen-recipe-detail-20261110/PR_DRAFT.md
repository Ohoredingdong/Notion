# Draft for review; PR not created

Base: `fix/kitchen-readable-controls-20261109`
Head: `fix/kitchen-recipe-cost-detail-20261110`

Title: Improve kitchen recipe cost visibility and detail layout

레시피 카드가 `원가 —`로 표시되고 상세 사진·재료·가격의 위계가 흐려 요리를 비교하기 어려웠습니다. 8카드에 직접 입력·구매 내역·날짜가 표시된 주재료 참고비를 구분하고 월 실제 식비 진입을 추가했습니다. 상세는 넓은 화면의 사진/정보 두 열과 작은 화면의 스크롤·고정 동작으로 정리했습니다.

참고 가격은 2026-10-23 특정 제품 관측치이며 양념·환산 가정을 공개합니다. 6개는 주재료 참고비, 오믈렛은 부분 합계, 닭가슴살 샐러드는 미확인입니다. 비용 입력은 기존 영양·출처·기록을 보존하며 실제 지출에 합산하지 않습니다.

검증: Node 267, 전송 13, 기존 브라우저 25/7,073단언, 전용 브라우저 18/1,638단언, 독립 화면 6개 위젯+2개 앱 통과. 실제 PNG와 같은 날짜·원본 데이터로 전후 비교하고 포커스 가림을 수정·재검증했습니다. 4개 전달물은 검사한 바이트 그대로이며 원본 이미지 11개를 모두 보존했습니다.

증거: docs/KITCHEN_RECIPE_COST_DETAIL_2026-11-10.md, docs/artifacts/kitchen-recipe-detail-20261110/verification.json

원 가격 제공처 직접 확인·공개 HTMLPreview 실행·실제 Notion·Safari는 미검증입니다. 기존 모델·저장 형식·Actions·금융 갱신·운영 사이트는 변경하지 않았습니다. main 병합 및 운영 배포는 승인 후 진행합니다.

이 PR은 선행 UI 브랜치 `fix/kitchen-readable-controls-20261109`를 기준으로 쌓습니다.
