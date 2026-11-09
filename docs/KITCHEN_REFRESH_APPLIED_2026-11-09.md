# 11월 8일 디자인의 실제 위젯 적용

사용자가 11월 9일 “해봐 이대로 위젯 수정”으로 [홈·네 탭 시안](../designs/kitchen-refresh-20261108/README.md)의 적용을 요청했다. 이 문서는 이미지 제안과 실제 실행물을 구분한다. 작업 브랜치는 `feat/kitchen-refresh-20261109`, 기준은 `9a910076adc437f80ac8c54283d75321b5527913`다. main 병합·운영 배포는 하지 않는다.

## 구현

- 아이보리·오크·코랄과 부드러운 일러스트 질감을 공통 적용했다. 배경·빈 본체·네 문·음식은 별도 자산이다. 재고를 지우면 음식도 사라진다. 시안의 영양·복용·식비 숫자를 제품 초기값으로 넣지 않았다.
- 720px 기준 약 763px 프레임이다. 상단 194px, 장면 1254:893, 하단 56px을 기준으로 가용 화면에 균일하게 맞춘다. 휴대폰 외곽이나 세로 앱 높이를 추가하지 않는다. 작은 폭은 최소 44px 주요 버튼을 유지한다.
- 냉장고 바로 위 영양제는 큰 빈 판 대신 짧은 행이다. 넓은 화면에서는 좌우 95px을 같게 두어 제품 열을 중앙에 맞춘다. 내용 폭 560px 미만에서는 실제 버튼을 브랜드 행 중앙으로 옮긴다. 영양 미입력·목표 미설정·일부 식사만 입력된 상태를 구분한다.
- 레시피는 사진·이름·시간·입력 열량/원가·재료 충족을 보여 주는 2열×4행이다. 320/390px은 사진과 문자를 별도로 배치한다. 시간·예산·재료 조건은 기존 필터와 연결한다.
- 기록 첫 화면은 음식 달력, 선택일 식사, 실제 월 식비/예산과 장보기다. 5주·6주 달력을 구분하고 미래 계획을 실제 식사처럼 그리지 않는다. 영양·영양제·식비 상세도 유지한다.
- 내 부엌은 같은 냉장고 모델과 방을 사용하는 편집 화면이다. 보유/무료/꾸밈권 사용 소품을 구분한다. 배치 미리보기와 취소·적용, 도감·건강상식·설정은 기존 거래 규칙을 사용한다.

## 저장·기능 보존

저장 키·형식·모델·계획/실제 식사·차감/취소·지출/입고 거래는 유지한다. `workflows.js` 변경은 영양 부분 입력의 표시뿐이다. 기존 `zone=seasoning` 자료는 문 선반에 **표시만** 투영한다. 수량·기한·원래 zone/x/y/z는 화면을 열거나 탭을 바꾸는 것만으로 다시 저장하지 않는다. 사용자가 실제로 이동·수정하면 기존 저장 동작을 사용한다.

사진 2장 등록과 검수·저장, 재료 상세, 계획 저장과 실제 식사, 영양·재고 갱신/취소, 실제 지출과 별도 재료 입고, 첫 요리 보상과 소품 비용을 유지한다. OCR 공급자·공식 영양/가격·개인 권장량·실제 동기화는 이번 디자인 작업으로 검증됐다고 주장하지 않는다.

공개 미리보기는 opaque iframe의 임시 저장을 사용한다. `임시 · 백업`을 표시하며 내보내기 동작을 유지한다. 일반 원본 HTML의 localStorage 보존과 같은 조건으로 보고하지 않는다. 운영 금융 데이터·Actions·원래 사이트 진입 파일은 변경하지 않는다.

## 재현

기존 생성 환경의 Terser 5.44.1, clean-css-cli 5.6.3과 이미지 도구를 저장소 밖에 준비한다. 브라우저 증거는 체크아웃 밖에 둔다.

```bash
python scripts/build_miniature_kitchen_preview.py --compact --output-dir /tmp/kitchen-refresh
python scripts/build_kitchen_mobile_preview.py --output-dir /tmp/kitchen-refresh/mobile
python scripts/test_kitchen_refresh_browser.py \
  --root /tmp/kitchen-refresh --output /tmp/kitchen-refresh-check \
  --scene-contract designs/miniature-kitchen/assets/refresh-20261109/acceptance-geometry.json \
  --browser-executable /usr/bin/chromium
python -m unittest discover -s scripts -p test_kitchen_mobile_transport.py
node --test tests/*.test.cjs
```

기준 화면을 동결해 두었다면 `--observe-only`로 전후 공통 상태를 기록하고 최종 실행에 `--baseline-evidence <이전 증거 폴더>`를 더한다. 신규 검사는 기존 생활·위젯·문·드래그 검사 함수를 재사용한다. 공유 파일 네 개를 직접 열어 모드·바이트/해시·실제 그림·클릭·저장과 빈 재고를 확인한다. 원본 PNG 검사만으로 압축 공유본을 통과 처리하지 않는다.

## 검증 상태

최종 `after-v6`를 검증한 뒤 **같은 바이트 그대로** `previews/miniature-kitchen-{app,widget}.html`, `previews/mobile/{app,widget}.html`에 복사했다. [검증 결과·해시·보존 목록](artifacts/kitchen-refresh-20261109/verification.json)에 실제 실행 범위를 남긴다.

| 검사 | 결과 |
| --- | --- |
| 최종 HTML 실제 브라우저 | 25/25 시나리오, 7,003개 단언 통과 |
| 네 전송물의 실제 body 모드 | app/widget/native/opaque 기대 모드 모두 통과 |
| 화면 | 320×360, 390×480, 720×800, 800×600 및 앱 390×844·720×900 |
| 같은 자료 전후 | 10/10 raw/envelope·선택 날짜 동일 |
| 파일/검사 코드 | 전송물4개·재사용 검사 코드5개 실행 전후 해시 동일 |
| 기존 Node 회귀 | 233 통과, 실패0 |
| HTML 전송·모드 회귀 | 13 통과, 실패0 |
| 운영 보호 | 금융/Actions/도메인·기존 테스트 등139개 보호 파일 바이트 동일. 금융 갱신을 점검 명목으로 실행하지 않음 |
| 전송 예산 | 네 파일 각각1MiB 미만, 기능·이미지 해상도를 삭제해 예산을 맞추지 않음 |

브라우저 시나리오는 영양제 날짜/등록/복용, 사진2장 등록/검수/저장, 실제 식사·차감/취소/재저장, 계획과 실제 지출 분리, 편집 적용/취소, 문별 실클릭·재료 드래그·빈 재고·기존 v1을 포함한다. 같은 데이터의 720px [수정 전 홈](artifacts/kitchen-refresh-20261109/before-720-fridge.png)·[수정 후 홈](artifacts/kitchen-refresh-20261109/after-720-fridge.png), [레시피](artifacts/kitchen-refresh-20261109/after-720-meals.png), [기록](artifacts/kitchen-refresh-20261109/after-720-records.png), [꾸미기](artifacts/kitchen-refresh-20261109/after-720-kitchen.png)를 직접 비교했다. 숫자가 있는 전후 화면은 명시적인 일회용 QA 자료다. 사용자 기본 기록으로 저장하지 않는다. [빈 재고](artifacts/kitchen-refresh-20261109/after-720-no-food.png)에서도 음식 그림이 남지 않는 것을 별도로 확인했다.

실제 Notion, Safari, 실물 휴대폰과 HTMLPreview의 공개 실행은 미검증이다. 이 환경에서 GitHub API와 HTMLPreview 호스트는 네트워크 정책상 접근할 수 없다. 브라우저 기능 통과는 사용자 최종 외형 승인을 뜻하지 않는다. main 병합·자동 배포는 하지 않았다.

중간 후보 `after-v2`는 실패했다. body 속성 순서가 달라지자 생성기의 단순 문자열 교체가 widget을 app 모드로 남겼다. 추가 배너·임시 백업·달력/식비 경계·필터 진입도 실제 생성물에서 확인했다. 생성기를 속성 순서와 무관하게 바꾸고 잘못된 원본에는 실패시키며 회귀 테스트를 추가했다. 실패 후보의 로그·화면은 별도로 보존하고 최종 배포 후보로 사용하지 않는다.

`after-v5`도 24/25만 통과했다. 공개390px의 식사 완료 창이 실제 위젯보다7px 크게 열린 원인은 dialog가 shell의 새 프레임 변수를 상속하지 못한 것이었다. 형제 dialog와 shell에 같은 값을 전달하고 상세창 경계를 맞춘 뒤, 동일한25개 전체를 재실행해 통과했다. 기본 화면102개는 v5와v6가 PNG 바이트까지 같았다.

11월 6일 문서는 이전 배치 이력으로 남긴다. 정사각 장면, 영양제 680px 전환, 앱 확대 계수처럼 이번 승인 디자인이 대체한 외형 가정을 새 후보에 그대로 적용하지 않는다. 데이터·거래·기존 자료 보존 단언은 유지한다.
