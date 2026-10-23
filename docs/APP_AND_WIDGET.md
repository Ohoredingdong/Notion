# 같은 부엌의 앱과 위젯

> 이 문서는 `2a8b8ae` 시점의 첫 분리 작업 기록이다. 사용자가 이후 위젯 크기를 지적하고 두 버전 재디자인을 요청했다. 최신 크기·생활 기능·검증은 [생활형 부엌 재디자인](KITCHEN_LIFE_REDESIGN.md)을 따른다. 아래 ‘작은 배치’ 수치는 이전 비교 증거다.

사용자의 “두 가지를 똑같이, 각각” 요청에 따라 앱과 노션 임베드용 위젯을 별도 진입 파일로 제공한다. 두 프로젝트로 기능·데이터를 복제하지 않고 같은 냉장고·양념·레시피·기록·장보기 코드를 사용한다. 차이는 작은 영역에 맞춘 배치다. 구현 브랜치는 `feat/kitchen-widget-and-app`, 비교 기준은 `0491865d`다.

## 각각의 파일

| 용도 | 배포 소스 | 자산을 포함한 검토 파일 |
| --- | --- | --- |
| 웹앱 | 기존 `use-me-first.html` 유지 | [앱 미리보기](../previews/use-me-first.html) |
| 노션 위젯 | `use-me-first-widget.html` 추가 | [위젯 미리보기](../previews/use-me-first-widget.html) |

기존 앱 URL은 `https://ohoredingdong.github.io/Notion/use-me-first.html`이며 경로를 변경하지 않는다. 새 위젯의 배포 대상 경로는 `https://ohoredingdong.github.io/Notion/use-me-first-widget.html`이다. 이번 작업에서 main 병합·GitHub Pages 배포는 하지 않았으므로 새 위젯 주소가 이미 활성화되었다고 보고하지 않는다. 앱은 브라우저용 웹앱이며 설치형 모바일 앱을 새로 만든 작업이 아니다.

## 공통 기능과 표시 차이

- 같은 흰색 4도어, 위 좌우 냉장·아래 좌우 냉동, 두 디스플레이와 미니어처 아트를 사용한다.
- 두 화면 모두 네 문 개폐, 재료 추가·수정, 드래그·겹침·층 조작·위치 저장, 양념 기한, 레시피 상세·검색·즐겨찾기, 식사 기록, 장보기와 보유 등록을 사용한다. 기존에 구현되지 않은 자동 재고 차감·식비 모델까지 새로 완성했다는 의미는 아니다.
- 앱은 기존 넓은 홈과 안내·통계를 유지한다. 위젯은 냉장고·양념·재고를 작은 메뉴로 전환하고, 네 개의 주요 메뉴를 상단에 둔다. 상세 기능을 제거하지 않는다. 위젯 높이가 부족하면 문서 안에서 세로로 스크롤한다.
- 앱/위젯 보기 버튼과 `?view=app` 또는 `?view=widget`으로 같은 문서 안에서 전환할 수도 있다. 표시 모드는 URL·DOM에만 반영하고 저장 데이터의 키·형식을 변경하지 않는다.
- 같은 출처와 저장 컨텍스트의 두 진입 파일에서 동일한 `use-me-first-state-v5`, `use-me-first-kitchen-view-v1`, `umf-seasoning-layout-v3`를 사용한다. 실제 Notion과 브라우저 간 저장소 공유는 호스트의 권한·분리 정책까지 확인한 것이 아니며, 기기 간 연결은 기존 동기화 기능의 범위다.

작은 선반에서 기존 기본 배치를 그대로 줄이면 네 번째 재료가 앞 재료를 가려 잘못 잡히는 문제를 재현했다. 위젯에서 아직 위치를 저장하지 않은 재료만 4열로 배치하고, 많아지면 높이를 늘린다. 저장된 좌표·순서는 이동시키거나 다시 저장하지 않는다. 층을 바꿀 때도 실제 표시 위치와 저장되는 기본 위치를 일치시켰다. 위젯의 짧은 레시피 목록은 스크롤 영역 안에서 표시해 아래 기록 버튼을 가리지 않게 했다.

## 같은 조건의 전후 화면

합성 재료 4개·양념 6종, 2026-10-23 고정 시계로 촬영했다. 실제 사용자 기록이 아니다. 앱은 1120px, 위젯 비교는 390×640px로 맞췄다. 앱 홈 영역의 전후 PNG는 바이트 단위로 동일하다. 보기 전환 버튼은 홈 영역 밖의 헤더에 추가했다.

| 비교 | 이전 | 변경 후 |
| --- | --- | --- |
| 앱 홈 1120px | [화면](two-views/before-app-1120.png) | [화면](two-views/after-app-1120.png) |
| 작은 영역 390×640px | [앱만 있던 화면](two-views/before-widget-390.png) | [위젯 화면](two-views/after-widget-390.png) |

[320px 위젯 전체](two-views/widget-320.png), [위젯 양념 화면](two-views/seasoning-390.png).

## 생성과 유지보수

원본 마크업은 `use-me-first.html` 하나다. `use-me-first-widget.html`은 원본에서 기본 표시 모드만 바꾼 생성 파일이다. 스크립트·스타일 참조와 기능은 같으며 Node 회귀에서 이를 확인한다. 새 표시 로직은 `use-me-first-presentation.js`, 위젯 전용 배치는 `use-me-first-widget.css`에 있다. 생성 파일 세 개를 따로 수정하지 않는다.

```bash
python scripts/build_fridge_preview.py --presentation widget --modular --output use-me-first-widget.html
python scripts/build_fridge_preview.py --presentation app --output previews/use-me-first.html
python scripts/build_fridge_preview.py --presentation widget --output previews/use-me-first-widget.html
```

## 검증

- [Node 155/155 통과](two-views/node-tests.log), 실패·건너뜀 0개. 기존 회귀 외에 표시 전환 시 원본 보존, 두 진입 파일의 공통 의존성, 화면 메뉴, 많은 재료의 기본 위치·층 저장을 확인한다.
- 앱: [모듈형 30/30](two-views/app-source-results.json), [단일 파일 32/32](two-views/app-standalone-results.json). 기존 네 문·날짜·레시피·기록 흐름과 srcdoc의 저장 허용/차단 처리를 확인했다.
- 위젯: [모듈형 19/19](two-views/widget-source-results.json), [단일 파일 19/19](two-views/widget-standalone-results.json). 320×480·390×640·640×480px에서 실제 터치 이동, 문 개폐, 양념 날짜, 두 진입 URL과 표시 모드 전환·새로고침 후 동일한 원본 유지, 레시피·즐겨찾기·기록·장보기·재고 입력, 320×480px iframe을 확인했다.
- 브라우저 합계 100개 통과. 외부 쓰기는 차단하며 단일 파일은 별도 자산 요청이 없다. 두 미리보기는 검사한 파일과 바이트 단위로 일치하고, 모듈형 위젯도 생성기 결과와 일치한다.
- 스크립트 초기화 확인은 `DOMContentLoaded` 이후 실행한다. 네트워크가 조용한 시점만으로 큰 단일 HTML의 파싱 완료를 가정하지 않는다. 실제 Notion·실기기 Safari·개인 동기화 쓰기·공개 배포는 이 검증으로 완료했다고 보고하지 않는다.

브라우저 검증은 아래 명령으로 재현한다. `--root`에 두 개의 단일 HTML만 있는 디렉터리를 주고 `--standalone`을 추가하면 오프라인 자산 포함 조건을 검사한다. 결과는 체크아웃 밖에 둔다.

```bash
python scripts/test_fridge_presentations_browser.py --root "$PWD" --output /tmp/kitchen-views
python scripts/test_fridge_four_door_browser.py --root "$PWD" --output /tmp/kitchen-app --browser-executable /usr/bin/chromium
```
