# 냉장고 위젯 크기와 상세 화면

사용자는 위젯을 요청했으며 앱 형식과 어긋난 디자인 비율을 거부했다. 이전 미리보기의 기능 검사 통과는 외형 승인으로 취급하지 않는다.

기존 720×500 임베드에서 바깥 폭이 약475px로 줄고 하단 메뉴가 약61px로 커졌다. 원인은 높이에서 폭을 역산한 공통 프레임, viewport 기준 큰 화면 규칙과 장면/메뉴 확대율의 혼용이다. 320×360 요리 상세는 재료 본문에12.5px만 남았다.

위젯은 가용 가로폭을 사용하고 상단44px 헤더·44px 텍스트 탭을 둔다. 긴 휴대폰 화면에서도 세로 앱으로 늘리지 않으며 상세 창도 같은 카드 영역 안에 둔다. 장면과 조작의 확대율을 분리하고, 기존 사진과 식재료의 원래 투영을 유지한다. 넓은 위젯은 장면과 영양을 나란히, 좁은 위젯은 장면 위에 간결한 영양 요약을 둔다. 재료 추가는 사진을 가리지 않는 헤더로 옮긴다.

레시피·기록·내 부엌은 위젯 크기를 기준으로 배치하고, 복잡한 상세는 헤더·주요 조작을 고정하고 본문 안에서 탐색한다. 기존 거래 모델·저장 key/version1·재고·계획·식사·실제 지출·보상과 기존 앱의 외형·동작을 보존한다. 금융 자동화·운영 main/Pages는 변경하지 않는다.

`scripts/test_kitchen_widget_browser.py`는 실제 생성된 위젯·opaque wrapper·기존 앱 HTML을 입력으로 삼는다. 320×360·390×480·720×500·800×600·390×844의 native/opaque 임베드에서 가로폭·탭·상세·사진 투영·원문 보존을 검사하고, 이전 생성물을 `--baseline-root`로 지정해 같은 상태의 실제 화면을 비교한다. `--check-app-unchanged`는 기존 앱의8개 화면 픽셀 보존도 확인한다. 단위 fixture와 기본 시안 재료는 실제 새 재고나 개인 자료가 아니다.

실제 계획 저장 후 320×360의 이름/분량/상태가 겹치는 문제도 재현했다. 날짜·끼니44px를 유지하고 카드의 조작을 공통 한 줄로 묶어 모든 수치를 별도 줄로 보존했다. 실제 식사 완료(B6)의 주요 버튼이 아래로 밀리는 실패도 유지한 뒤 고쳤다. 완료 안내·영양·보상·닫기/되돌리기 조작은 카드 안에 두고, 긴 실제 재료 차감 목록만 별도 내부 영역에서 탐색한다.

과거 `test_kitchen_complete_flow_browser.py`와 `test_kitchen_tabs_browser.py`는 수정 전52c 생성물에서도 각각 숨긴 expirySummary/미선택 선반 label을 전제로 실패했다. 실패를 성공으로 바꾸거나 기능 단언을 삭제하지 않는다. 현재 화면의 회귀와 해당 과거 harness 정합 문제를 구분한다. 실제 Notion/Safari/휴대폰 및 외부 사진 인식·영구 동기화는 별도 검증 범위다.

## 최종 검증과 실제 화면

최종 생성4파일은 각각1MiB 이하이며 source/build 해시가 일치한다. [위젯 회귀](widget-sizing-20261105/widget-verification.md)는17사례·941검사, [실제 기능](widget-sizing-20261105/business-verification.md)은8스위트·26프로필을 통과했다. 기존 Node233건·전송12건도 통과했다. 수정 전 실패와 QA helper의 하단 메뉴/시계 주입 가정 수정은 별도 근거로 보존했다. [요약 결과](widget-sizing-20261105/verification.json)와 [기존 자료 보존](widget-sizing-20261105/preservation.json)을 함께 확인한다.

- [720px 수정 전](widget-sizing-20261105/widget-720-before.png) · [수정 후](widget-sizing-20261105/widget-720-after.png)
- [320px 위젯](widget-sizing-20261105/widget-320-after.png) · [요리 상세](widget-sizing-20261105/recipe-detail-320-after.png) · [실제 식사 완료](widget-sizing-20261105/meal-complete-320-after.png)
- [레시피](widget-sizing-20261105/recipes-390-after.png) · [기록](widget-sizing-20261105/records-390-after.png) · [내 부엌](widget-sizing-20261105/kitchen-390-after.png)

공유본은 `previews/mobile/widget.html`이다. `app.html`과 기존 운영 URL을 수정본 위젯 링크로 대신 전달하지 않는다. 원본 앱8개 화면은 전후 픽셀이 같고, opaque 공유 미리보기는 임시 저장 상태다. 실제 Notion/Safari/기기 검증과 main 병합·운영 배포는 완료 범위에 포함하지 않는다.
