# 미니어처 부엌 배치 수정 · 2026-10-26

사용자의 “수정해” 요청에 따라 [시각 진단](KITCHEN_VISUAL_DIAGNOSIS_2026-10-25.md)의 원인을 수정했다. `design/miniature-kitchen-scene`의 `da220141`에서 분리한 `fix/miniature-kitchen-viewport` 브랜치의 독립 앱·위젯 시안만 대상이다. 기존 서비스·저장 기록·원본 그림은 변경하지 않는다. 이 기록은 사용자가 새 화면을 승인했다는 뜻이 아니다.

## 변경 내용

- 배경·냉장고·식재료·양념·소품을 하나의 `1536×1024` 공간에 배치한다. 화면 폭과 높이로 공통 축척을 계산하고, 탭은 같은 공간의 카메라를 옮긴다. 재료의 최소 44px 조작 크기와 글씨의 가독성은 별도로 보장한다.
- 냉장고의 고정 440px 확대 규칙과 별도 배경 확대를 제거했다. 본체·열린 문·바닥 여백과 문 버튼을 첫 뷰포트에 함께 맞춘다. 넓은 화면의 문 버튼은 한 줄, 좁은 화면은 두 줄이다. 560px에서 필요한 공간을 점진적으로 전환한다.
- 장면의 최소 높이와 종횡비가 서로 밀어내던 규칙을 덮어써 가로 넘침을 없앴다. 버튼은 모든 화면에서 그림 아래에 놓아 좌표계 차이로 인한 겹침을 막는다.
- `fridge-doors`에 `preserve-3d`를 적용하고 열린 문의 각도·원근·양쪽 공간을 함께 조정했다. 실제 원근 설정이 문의 투영을 바꾸는지도 검사한다. 기존 PNG와 CSS 문의 구성은 유지하며 새 3D 모델을 만든 것은 아니다.
- 작은 문 디스플레이는 이름·수량을 같은 줄에 놓고 그 아래에 기한을 표시한다. 두 재료의 기한이 표시창 아래에서 잘리지 않는지 검사한다.
- 조리대 카메라는 찻잔과 꽃병까지 포함하도록 중심을 조정한다. 식재료·양념·소품의 좌표는 계속 같은 방에 속한다.

## 같은 화면에서의 비교

모두 고정 시각 `2026-10-25T03:00:00Z`, Asia/Seoul, 동일한 예시 기록·문 상태·뷰포트로 비교했다. 변경 전은 `da220141`이다. 스크린샷은 전체 페이지가 아닌 **첫 뷰포트**다. 터치 대상의 최소 크기를 유지하기 위해 재료의 가장자리 위치가 제한되는 경우는 있지만 이름·수량·기한·보관 칸은 같다.

| 조건 | 이전 본체 | 수정 본체 | 이전 가로 넘침 → 수정 | 수정 후 처음 보이는 본체 | 수정 후 문 버튼 하단 |
| --- | --- | --- | --- | --- | --- |
| 위젯 649×660 | 440×767px | 220×384px | 0 → 0px | 100% | 612px |
| 앱 760×660 | 440×767px | 232×404px | 0 → 0px | 100% | 636px |
| 앱 761×660 | 285×497px | 232×404px | 107 → 0px | 100% | 636px |
| 앱 800×660 | 285×497px | 232×404px | 68 → 0px | 100% | 636px |
| 앱 1120×900 | 361×630px | 356×621px | 0 → 0px | 100% | 876px |
| 위젯 390×660 | 285×498px | 206×359px | 0 → 0px | 100% | 634px |
| 위젯 320×660 | 243×423px | 189×329px | 0 → 0px | 100% | 601px |

짧은 화면에서 고정 폭을 유지해 아래를 자르는 대신 높이에 맞춰 본체 크기를 정한다. 649×900의 위젯에서는 약 345×601px로 커진다. 재료 담기·요리·꾸미기 버튼이나 설명까지 모든 높이에서 한 화면에 들어간다는 의미는 아니며, 아래 기능은 세로 스크롤로 접근한다.

- 위젯 649×660: [이전](miniature-kitchen/coherent-before-649x660.png), [수정](miniature-kitchen/coherent-after-649x660.png), [네 문 열기](miniature-kitchen/coherent-after-open-649x660.png)
- 경계 양쪽: [760px](miniature-kitchen/coherent-app-760.png), [761px](miniature-kitchen/coherent-app-761.png)
- [넓은 앱](miniature-kitchen/coherent-app-1120.png), [390px 위젯](miniature-kitchen/coherent-widget-390.png), [320px 기한 디스플레이](miniature-kitchen/coherent-widget-320-closed.png)
- [14개 전후 재현의 수치](miniature-kitchen/coherent-layout-comparison.json)

## 검증

[최종 브라우저 검사](miniature-kitchen/coherent-layout-browser-results.json)는 **111개 통과·실패 0**이다. 앱·위젯 18개 폭/높이 조합과 [연속 크기 변경 13단계](miniature-kitchen/coherent-layout-resize-results.json)를 확인했다. 최종 작은 내장형은 앱 939,446바이트, 위젯 939,449바이트다. JavaScript 구문 검사와 `git diff --check`도 통과했다.

기존의 “본체 폭 400px 이상”, “그림 안에만 들어오면 성공” 검사를 실제 뷰포트의 전체 본체·열린 문·문 버튼 노출로 교체했다. 장면·본체·소품의 실제 렌더링 축척을 비교한다. 760/761, 559/560, 960/961 전환에서 냉장고 크기 급변을 막고, 패널 크기를 바꾼 뒤 수정한 수량·기한·보관 칸과 열린 문이 유지되는지 확인한다.

기능 검사는 이미지 응답을 모의로 공급하지 않는다. 문서 외 요청을 차단한 상태에서 내장 그림 5개의 디코딩과 선택 가능한 재료·요리·소품의 실제 픽셀을 확인한다. 네 문 독립 개폐, 닫힌 칸 입력 차단, 마우스/CDP 터치 이동, 키보드 이동, 수량·기한·양념 입력, 소품 순서·제거, 새로고침 후 예시 초기화, 기존 저장 키의 접근·변경 0을 검사한다.

이 결과는 로컬 Chromium 검증이다. 실제 채팅 클라이언트·Notion iframe·Safari의 새 화면 확인, 사용자의 디자인 승인, 사진 인식·영양·식비 기능의 완성을 뜻하지 않는다. 원본 앱 연결 전의 예시 시안이며 앱과 위젯은 기록을 공유하지 않는다.

```bash
source /workspace/.notion-cloud/activate.sh
python scripts/build_miniature_kitchen_preview.py --compact --output-dir /tmp/kitchen-preview
python scripts/test_miniature_kitchen_browser.py --root /tmp/kitchen-preview --output /tmp/kitchen-check
```

## 전달

채팅용 파일은 `/workspace/artifacts/kitchen-layout-fixed/miniature-kitchen-app.html`, `miniature-kitchen-widget.html`이다. 외부 자산 요청 없이 동작하는 작은 내장형 HTML을 사용한다. 기존 네 전달 경로도 같은 최종 파일로 갱신했다. 저장소의 `previews/`는 원본 그림 내장형으로 다시 생성했다.

수정 범위는 공통 시안 HTML/CSS/JS, 생성된 미리보기, 해당 브라우저 검사와 인수인계 문서다. `use-me-first.html` 등 실제 서비스 소스·저장 키·GitHub Pages URL은 변경하지 않았고 main에 병합하거나 배포하지 않았다.

수정 커밋 `ca208ee8`은 원격 `fix/miniature-kitchen-viewport`에 올렸다. 기본 브랜치를 `design/miniature-kitchen-scene`으로 지정한 draft PR 생성을 시도했으나 GitHub GraphQL API가 `Forbidden`으로 차단해 PR은 생성하지 못했다. [브랜치 간 변경 비교](https://github.com/Ohoredingdong/Notion/compare/design/miniature-kitchen-scene...fix/miniature-kitchen-viewport?expand=1)로 검토할 수 있다.

후속 사용자 피드백에서 이 수정의 위치도 배경과 맞지 않는다고 지적받았다. [최신 배경 정합 수정](KITCHEN_BACKGROUND_ALIGNMENT_2026-10-26.md)은 실제 설치 공간과 발의 투명 여백까지 반영한다. 위 기능 검사 통과를 배경 정합이나 디자인 승인으로 해석하지 않는다.
