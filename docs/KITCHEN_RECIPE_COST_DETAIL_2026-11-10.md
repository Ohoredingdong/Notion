# 요리 비용 비교와 상세 화면 개선

사용자가 “식비 어느 정도인지 확인도 안 되고 요리 상세에 들어가면 너무 별로”라고 지적했다. 카드의 `원가 —`는 직접 입력한 `recipeFacts.cost`만 사용하고 기본값이 비어 있었기 때문이다. 상세는 사진·미입력 영양·비용·입력 동작이 분산돼 있었다.

기준 커밋은 `babceb0983903d9f75ef35e004abd1b21f5b249f`, 작업 브랜치는 `fix/kitchen-recipe-cost-detail-20261110`이다. 독립 예시 프리뷰의 기능·표현을 수정한다. [11월 9일 프레임과 냉장고 구도](KITCHEN_REFRESH_APPLIED_2026-11-09.md), 기존 저장 키·형식·자료와 운영 진입점은 유지하며 main·GitHub Actions·운영 금융 갱신은 변경하지 않는다.

## 비용과 실제 지출

카드와 상세는 다음 근거를 구분한다.

1. 사용자가 입력한 1회분 재료비가 있으면 우선한다. 명시한 0원도 유지한다.
2. 구매 내역의 원래 구매 수량·품목 금액과 같은 단위의 사용량으로 계산한다. 소비 후 남은 재고량을 단가의 분모로 쓰지 않는다.
3. 전체 재료비를 계산하지 못하면 주재료만 살핀다. 사용 가능한 구매 단가를 우선하고, 확인한 날짜의 공개 참고 단가로 보완한다. 양념 제외·단위 환산 가정·가격 미확인을 표시한다.

`estimate()`는 직접 입력·구매 내역만 계산하고, `suggest()`가 별도의 주재료 참고 계산을 제공한다. 전체 금액이 없으면 `total:null`을 유지하고 `knownSubtotal`과 누락 재료를 구분한다. 입력하지 않은 가격을 0원으로 채우거나, 주재료 합계를 한 끼 전체 비용으로 표시하지 않는다. 영수증 품목 합계와 실제 결제액의 차이는 임의로 재료별 배분하지 않는다.

레시피 상단의 월 식비는 기존 지출 원장의 합계다. 누르면 해당 월 식비 관리로 이동한다. 빈 지출은 `지출 기록 없음`, 미설정 예산은 그대로 표시한다. 예상 조리비·계획 금액·참고값을 실제 지출에 더하지 않는다.

## 참고값의 범위와 날짜

[선별 참고 단가](../designs/miniature-kitchen/recipe-price-reference.js)는 [고정한 공개 게시본](https://github.com/novoodi/martmemo-data/tree/da2abfa6c7019c7ed86b078dd0fd4ac20e83dcff)에서 확인한 8개 품목의 사실과 출처 메타데이터다. 특정 제품의 대형마트 관측행 중앙값이며 현재가·전국 평균·사용자 구매가가 아니다. 원 제공처인 한국소비자원과의 직접 대조는 수행하지 못했다. [원행·포장·가격·매장 수·해시 검증 기록](artifacts/kitchen-recipe-detail-20261110/reference-provenance.json)을 함께 보존한다.

| 날짜 | 의미 |
| --- | --- |
| 2026-10-23 | 가격 관측일 `day` |
| 2026-11-06 22:56:17 UTC | 게시본 생성 시각. 한국시간 11월 7일 07:56:17 |
| 2026-11-10 | 앱에서 자료를 확인·편입한 날 `availableFrom`. 공식 발행일이라는 뜻이 아님 |

선택 날짜가 `availableFrom` 이전이거나 그 값이 잘못되면 참고 단가를 사용하지 않는다. 기존 직접 입력·그 날짜 이전의 구매 내역은 계속 유효하다. 11월 5일에는 참고 금액이 미확인이고, 11월 10일부터 아래 계산을 할 수 있는 회귀 검사를 둔다. 실제 사용한 관측일만 `referenceDay` 또는 `referenceDays`로 반환한다.

주재료의 단위를 맞추기 위한 다음 값은 관측한 식품 무게가 아니라 **명시적인 참고 비용 계산 가정**이다. 상세의 계산 근거에서 사용량과 가정을 표시한다.

- 양파 1개를 200g으로 계산
- 플레인 요거트 1큰술을 15g으로 계산
- 밥 1공기를 즉석밥 210g 한 개로 계산

가정이 없으면 개·큰술·공기와 g을 자동 변환하지 않는다. 이 가정은 참고 비용에만 쓰며 기존 구매 견적·재고 차감 단위 규칙은 바꾸지 않는다. 치즈는 레시피에 명시된 `1장 또는 20g` 중 실제 단가와 같은 단위를 선택하고 선택한 사용량을 표시한다.

| 요리 | 1회분 화면 표시 |
| --- | --- |
| 계란 볶음밥 | 주재료 약 2,800원 |
| 두부 된장국 | 주재료 약 1,200원 |
| 애호박 계란전 | 주재료 약 1,000원 |
| 요거트 계란 샐러드 | 주재료 약 1,600원 |
| 두부 스테이크 | 주재료 약 1,000원 |
| 버섯 두부볶음 | 주재료 약 2,500원 |
| 토마토 치즈 오믈렛 | 확인된 부분 약 1,870원 + 토마토 가격 미확인 |
| 닭가슴살 샐러드 | 닭가슴살·토마토 가격 미확인 |

완전한 주재료 참고 표시는 100원 단위로 반올림한다. 부분 합계는 전체 견적이 아니며 미확인 품목을 함께 표시한다. 영양값은 새 기본값을 만들지 않고 기존 직접 입력값을 사용한다.

## 상세와 비용 입력

상세는 사진·요리명·조리 시간·비용과 근거를 먼저 보여 주고 재료, 조리 순서, 영양·내 팁으로 나눈다. 재료에는 필요량·보유량·확인 상태를 표시한다. 분량·장보기·계획 저장·실제 식사 기록을 기존 동작에 연결하고, 하단 주요 동작은 상세 내용과 구분한다. 작은 프레임에서는 내부 스크롤을 사용한다.

비용 수정은 `recipeCost`의 **1회분 재료비 한 필드**다. 기존 영양값·출처·내 팁·실제 지출을 보존하고 `recipeFacts[id].cost`만 사용자의 입력에 따라 갱신한다. 비우면 구매 내역이나 참고 가격 계산을 다시 사용한다. 직접 입력한 금액도 실제 지출에 자동 반영하지 않는다.

구현 진입점은 [비용 모델](../designs/miniature-kitchen/recipe-cost.js), [카드](../designs/miniature-kitchen/home-recipe-view.js), [상세 뷰](../designs/miniature-kitchen/recipe-detail-view.js), [기존 작업 연결](../designs/miniature-kitchen/workflows.js)이다. `scene.html`에서 기존 여정 모델 뒤에 비용 모델·참고값·상세 뷰를 로드한다.

## 실행과 검증 상태

전송물은 기존 생성기로 체크아웃 밖에 만든 뒤 검사한다. 증거는 `docs/artifacts/kitchen-recipe-detail-20261110/`에 최종 선별 보존한다.

```bash
python scripts/build_miniature_kitchen_preview.py --compact --output-dir /tmp/kitchen-recipe-detail
python scripts/build_kitchen_mobile_preview.py --output-dir /tmp/kitchen-recipe-detail/mobile
node --test tests/*.test.cjs
python -m unittest discover -s scripts -p test_kitchen_mobile_transport.py
python scripts/test_kitchen_refresh_browser.py \
  --root /tmp/kitchen-recipe-detail --output /tmp/kitchen-recipe-regression \
  --scene-contract designs/miniature-kitchen/assets/refresh-20261109/acceptance-geometry.json \
  --browser-executable /usr/bin/chromium
python scripts/test_kitchen_recipe_detail_browser.py \
  --root /tmp/kitchen-recipe-detail --output /tmp/kitchen-recipe-detail-check \
  --browser-executable /usr/bin/chromium
```

필요한 Node·Python·이미지 도구 환경은 [공통 개발 규칙](../AGENTS.md)을 따른다. 같은 데이터의 전후 비교에는 새 검사 스크립트의 `--observe-only`와 `--baseline-evidence`를 사용한다. 신규 검사는 실제 4개 HTML, 320·390·720px와 낮은 임베드·앱, 가격 출처·가정·부분값·비용 입력·상세 조작·자료 보존을 확인한다. 화면 검토와 기능 검사는 별도다.

| 검사 | 현재 확인한 결과 |
| --- | --- |
| Node 회귀 | 267 통과, 실패 0. 비용 모델의 34개 검사 포함 |
| HTML 전송 | 13 통과, 실패 0 |
| 기존 브라우저 회귀 | 최종 후보 `after-v3`에서25/25·7,073개 단언 통과. 이전25개 시나리오의 식사·취소·장보기·기록·문·꾸미기 및10쌍 자료 보존 확인 |
| 신규 요리 상세 브라우저 | 최종 후보 `after-v3`에서18/18·1,638개 단언 통과 |
| 독립 브라우저 화면 | 최종 위젯6개·앱2개·198개 단언 통과. 실제 PNG12장 직접 검토; 이전 후보의 가정 접두어 중복·포커스 가림을 수정한 최종 파일에서 재확인 |
| 최종 전송물·공개 파일 | 검사한4개 HTML을 바이트 그대로 복사·해시 일치, 각1MiB 미만. 공개 접근은 게시 후 별도 검증한다 |

[최종 검사·입력 해시](artifacts/kitchen-recipe-detail-20261110/verification.json), [수동 화면 검토](artifacts/kitchen-recipe-detail-20261110/MANUAL_REVIEW.md), [발견·수정 및 검사 보정 이력](artifacts/kitchen-recipe-detail-20261110/harness-corrections.json)을 보존한다. 54개 런타임·생성 소스의 해시를 동결했으며 기존11개 이미지 자산은 바이트 그대로 유지했다. 전송 크기 축소는 기존 생성기의 무손실 압축 방식 선택에 따른다. 원본 이미지의 해상도를 줄이지 않았다.

같은11월10일·같은 데이터·같은720×800 프레임에서 비교했다.

| 화면 | 수정 전 | 수정 후 |
| --- | --- | --- |
| 8카드 | [이전 카드](artifacts/kitchen-recipe-detail-20261110/before-cards-720.png) | [비용 비교 카드](artifacts/kitchen-recipe-detail-20261110/after-cards-720.png) |
| 요리 상세 | [이전 상세](artifacts/kitchen-recipe-detail-20261110/before-detail-720.png) | [새 상세](artifacts/kitchen-recipe-detail-20261110/after-detail-720.png) |

[320px 상세](artifacts/kitchen-recipe-detail-20261110/after-detail-320.png), [부분 합계](artifacts/kitchen-recipe-detail-20261110/after-partial-320.png), [계산 근거](artifacts/kitchen-recipe-detail-20261110/after-cost-basis-720.png), [실제 초점 가림 수정](artifacts/kitchen-recipe-detail-20261110/after-focused-portions-390.png)도 함께 확인한다.

원 공급자 직접 검증, 실시간 가격 갱신, 실제 Notion·Safari·실물 기기, 공개 HTMLPreview 실행은 미검증이다. main 병합·운영 배포는 수행하지 않았다. 중간 후보의 실패·검사 보정 이력과 최종 통과를 구분해 보존한다.
