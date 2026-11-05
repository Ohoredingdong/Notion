# Nov4 시안과 실제 위젯 크기 재정합

사용자의 “대충 코드 변형” 지적 뒤, Nov4 원본 보드와 같은 너비의 실제 앱을 직접 비교해 수정했다. 원본은 [재료](../designs/kitchen-full-flow-20261104/01-ingredients.png), [식단](../designs/kitchen-full-flow-20261104/02-meals.png), [기록](../designs/kitchen-full-flow-20261104/03-records.png), [성장](../designs/kitchen-full-flow-20261104/04-growth.png)이다. 이전 기능 통과와 공개 링크 성공을 시각적 승인으로 취급하지 않는다.

## 수정한 화면

- A1: 따뜻한 아이보리 본체, 냉장 3단과 냉동 2×2 서랍, 냉장실 약66.5% 비율을 적용했다. 본체는699×828 논리 좌표를 쓰며 원본 사진의 하드웨어와 빈 벽을 나눈 nine-slice 표면으로 구성한다. 냉장실은 중앙 벽 없이 넓은 선반을 공유한다.
- A1: 브랜드20px(320에서는18px), 요약 제목18px, 하단 아이콘26px·라벨14px를 적용했다. 상단 CSS의 더 높은 선택자 우선순위 때문에 브랜드가13px로 남던 문제를 수정했다. 추가 버튼은44px 조작 영역 안의32px 시각적 캡슐이며 메뉴 선택은 원본처럼 산호색 아이콘/글자로 표시한다.
- 기존 재료 좌표는 그대로 읽고 화면에서만 가까운 선반과 빈 공간에 투영한다. 넓은 냉장실을 공유해 구형 배치의 서로 다른 행이 한 자리에 겹치던 문제를 고쳤다. 실제 이름·수량·기한·재고는 추가하거나 바꾸지 않는다. 가장 최근 이동한 재료는 희망 위치를 유지하며 주변 재료를 빈 구간에 배치한다. 수평 이동 때 선반이 바뀌던 경계 계산과 투명한 구획이 재료 클릭을 막던 문제도 고쳤다. 임의로 많은 재고까지 그림의 무겹침을 보장하지 않으며 전체 목록 접근은 유지한다.
- A2/A3/A4/A6: 제목·입력 행·아이콘·저장 버튼 크기를 원본 기준으로 복구했다. 사진 칸과 내용 높이를 맞추고,320에서도 네 핵심 필드와 수정/요리 버튼을 함께 표시한다. CSS 내장 SVG는 빌더가 외부 경로로 오해하지 않게 처리한다.
- B1/B2: 사진 높이와 음식명·시간·가격 크기를 함께 조정했다. 상세는 재료/조리 순서/영양·내 팁 탭으로 전환하고 계획/실제 식사 버튼은 아래에 유지한다. 탭 전환은 저장하지 않는다.
- B4/C1/C3/C4/C5/C6: 계획 배지·토스트·도구 버튼, 월간 카드와 하단 버튼의 겹침을 없앴다. 월간/식비 상세의 숨겨진 메뉴 높이를 제거하고,320 구매 확인 버튼과 시트 뒤로/닫기 헤더를 복구했다.

D1/D5/D6의 넓은 부엌과 같은 조리대 소품 투영, 첫 기록 보상·취소·적용 규칙은 보존했다. 저장 키 `miniature-kitchen-preview-v1`과 version1도 유지한다. 상태/거래 모델·OCR 엔진은 수정하지 않았다.

## 검토 증거

[실제 A1](kitchen-reference-fit-20261104/actual-A1.png), [A2](kitchen-reference-fit-20261104/actual-A2.png), [A4](kitchen-reference-fit-20261104/actual-A4.png), [A6](kitchen-reference-fit-20261104/actual-A6.png), [실제 배치](kitchen-reference-fit-20261104/actual-D5.png)는 생성 시안이 아닌 브라우저 화면이다. 사진 입력 예시는 격리된 검사 자료다. 원본 시안의 예시 재고/영양값을 사용자 데이터에 채우지 않는다.

[전달 파일 크기/해시](kitchen-reference-fit-20261104/generated-files.json)와 [사진 전송 품질](kitchen-reference-fit-20261104/asset-quality.json)을 기록한다. 원본 해상도를 유지한7개 AVIF와12개 모듈·19개 스타일을 HTML에 포함한다. 앱/위젯/모바일4파일 모두1MiB 미만이며 포장을 풀면 생성 원문과 같다. 전송12검사, JS문법, diffcheck를 통과했다.

실제 사진 내용·용기 재질·브라우저 날짜 표기는 원본 보드와 차이가 남는다. 본체 표면 일부는 크기에 따라 사진 경계가 보일 수 있다. 브라우저 실행 및 버튼 검증은 시안의 모든 픽셀 일치나 사용자의 최종 승인을 뜻하지 않는다. 실제Safari/Notion기기 검증도 별도다.

## 최종 실제 확인

[같은 너비의 원본과 실제 화면](kitchen-reference-fit-20261104/original-and-actual.png)을 직접 비교했다.315px 너비에서 본체170.5×202px는 원본 약171×201px이며, 전체 카드 높이는 약0.8% 차이다. 사진 소재·일부 경계 차이는 남긴다.

320/390/801에서 기본17개와 추가 재료가 있는21개 자료를 각각 실제 그림 중심으로 눌러 올바른 A6를 열었다. 기존 v1 저장 원문은 읽기·resize·상세 열기/닫기 전후 바이트가 같다. 실제 drag/방향키·수평 같은 선반·다른 ID/기록 보존·그림 크기·재로드도 확인했다. [선택/원문](kitchen-reference-fit-20261104/selection-and-storage.json), [이동/재로드](kitchen-reference-fit-20261104/native-move-reload.json), [추가 재료 이동](kitchen-reference-fit-20261104/generic-move-reload.json)을 기록한다.

실제 B2 탭 전환의 저장 무변경, 계획→실제 식사→취소·재저장, 지출과 재고 분리, D초안 취소의 원문 보존과 적용 때만 꾸밈권1 차감·동시 재고 보존을 확인했다. 최종 버전의12모듈 중 장면을 제외한11개는 이 거래 확인 버전과 바이트가 같고 모델은 수정 전과 같다. A2/A3/A4/A6 320/390/801 및 B1/B2/C1/C3/C5 320/390의 실제 주요 버튼·가로 넘침도 확인했다.

## 공개 전달

구현은 `9f1ee959aaa3901ac88246bbcb65202deac980f4`에 고정해 작업 브랜치에 업로드했다. main/Pages는 변경하지 않았다.

- [수정한 위젯](https://htmlpreview.github.io/?https://raw.githubusercontent.com/Ohoredingdong/Notion/9f1ee959aaa3901ac88246bbcb65202deac980f4/previews/mobile/widget.html)
- [공개 실제 첫 화면](https://raw.githubusercontent.com/Ohoredingdong/Notion/0fe3f608e4313b088dfdfdbba8674729bb43629b/widget-phone-A1.png)
- [원본·실제 같은 너비 비교](https://raw.githubusercontent.com/Ohoredingdong/Notion/0fe3f608e4313b088dfdfdbba8674729bb43629b/local-reference-comparison.png)
- [공개 Chromium 실행 성공](https://github.com/Ohoredingdong/Notion/actions/runs/41844839718)

공개 HTMLPreview에서320×568·390×844·801×782 모두 실제 A1/A2/A6/B1/B2/C1/D5를 열었고,12모듈·19스타일·7AVIF 원문/바이트·데이터 무변경·저장/적용을 확인했다.21개 실제 화면과 별도 로컬 비교PNG는 정상TLS에서HTTP200·image/png·고정 증거 바이트 일치를 확인했다. [최종 공개 결과](kitchen-reference-fit-20261104/public-status.json)와 [공개 이미지 접근](kitchen-reference-fit-20261104/public-fetch-screenshots.json)을 기록한다.

첫 공개 검사에서는 월간 상세의 숨겨진 하단 메뉴를 누르려던 검사 스크립트가 실패했다. 앱 소스와 단언은 그대로 유지하고 실제 월간 뒤로→영양 기록→하단 메뉴 경로로 검사 동작을 수정해 위 최종 실행을 통과했다. 최초 실패를 최종 통과로 덮지 않았다. 실제 기기 Safari/Notion 검증과 사용자의 디자인 승인은 주장하지 않는다.

Draft PR 생성은 GitHub GraphQL API의403 Forbidden으로 실패했다. Git 작업 브랜치 업로드와 위 공개 실행/이미지 접근은 성공했으며 PR 생성이나 main 병합을 완료했다고 보고하지 않는다.
