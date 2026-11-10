# Review draft; PR not created

Base: `fix/kitchen-readable-quantities-20261110`
Head: `fix/kitchen-servings-nutrition-20261110`

Title: Separate cooking servings from personal nutrition tracking

만들 양을 늘렸을 때 개인 섭취량까지 같은 배수로 기록되던 연결을 분리했습니다. 상세에서는 조리 인분별 재료·총비용과 개인1인분 영양을 구분하고, 식사 확인에서 내가 먹은 인분과 실제 차감할 재료를 확인합니다. 신규 조리 계획은 구분 메타를 쓰며 기존 계획·기록·저장키·버전을 유지합니다.

레시피 영양과 오늘의9개 성분·개인 목표를 연결했습니다. 당류/나트륨은 개인 관리 기준이며 총당류와 유리당을 구분합니다. 확인한14개 SR28 식품의 참고값을 사용하고, 누락·미계량 성분은 전체값으로 채우지 않습니다. 참고 영양은 명시적으로 불러온 뒤 저장하며 수동값/0·부분값·과거 기록·출처를 보존합니다.

검증: Node316/전송13/기존25·7073단언/상세18·1648단언/분수8·976단언/새서비스14·751단언 모두 통과. 실제8프로필 시각 검사·내비게이션40검사·두 독립 수동 검토 완료. 최종4개 HTML은 검사한 바이트와 동일하며59개 소스를 동결하고11개 원본 이미지 자산을 보존했습니다.

증거: docs/KITCHEN_SERVINGS_NUTRITION_2026-11-10.md 및 docs/artifacts/kitchen-nutrition-20261110/verification.json. 중간 실패와 테스트 시계 초기화 경합 진단은 별도 보존했습니다.

자료는2015년 USDA SR28의 고정된 공개 게시본으로 원 제공처 직접 검증·live 갱신은 미완료입니다. 실제 Notion/Safari/실기기·공개 HTMLPreview 실행은 미검증입니다. 금융 Actions·데이터·운영 사이트·main은 변경하지 않았습니다. 실제 배포와 병합은 승인 후 진행합니다.

GitHub API가 환경 정책으로 차단되어 PR 생성은 완료하지 못했습니다. 이 초안과 작업 브랜치가 검토 대상입니다.
