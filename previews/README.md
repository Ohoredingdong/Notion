# 한끼의 부엌 앱·위젯 미리보기

최신 선택은 **직접 만지고 꾸미는 입체적인 미니어처 부엌**이다. [앱·위젯 나란히 보기](miniature-kitchen-board.html), [앱 시안](miniature-kitchen-app.html), [위젯 시안](miniature-kitchen-widget.html)에서 확인한다. 이 세 파일은 독립 디자인·조작 시안으로 예시 재료만 사용하며 기존 앱 기록에 접근하지 않는다. 새로고침하면 초기화된다. 아래 기존 미리보기는 사용자가 거절한 생활형 시안의 구현 이력으로 보존한다.

```bash
python scripts/build_miniature_kitchen_preview.py
```

소스는 `designs/miniature-kitchen/`이며 `scene.html`은 생성용 템플릿이다. 단일 HTML 두 개와 비교 페이지를 생성한 뒤 검토한다. 새 디자인의 범위·자료·검증은 [미니어처 부엌 기록](../docs/MINIATURE_KITCHEN_DESIGN.md)을 따른다.

[앱](use-me-first.html)과 [위젯](use-me-first-widget.html)은 같은 냉장고의 CSS·JavaScript·이미지를 포함한 생성 파일이다. 기능·디자인은 공유하고 기본 배치만 다르다. HTML만 전달되는 미리보기 환경에서도 별도 자산 경로가 필요 없다. 직접 수정하지 않고 저장소 루트에서 다시 생성한다.

```bash
python scripts/build_fridge_preview.py --presentation app --output previews/use-me-first.html
python scripts/build_fridge_preview.py --presentation widget --output previews/use-me-first-widget.html
```

배포 진입점과 수정할 원본은 루트의 `use-me-first.html` 및 이 파일이 참조하는 CSS·JavaScript다. 이 미리보기에 사용자 기록·동기화 코드를 넣지 않는다. 기록은 실행한 브라우저의 해당 출처에 저장되며, 다른 출처의 기존 데이터를 자동으로 가져오지 않는다. 저장이 제한된 iframe에서는 기존 앱의 저장 불가 안내가 표시된다.

두 버전의 최신 디자인·생활 기능·미연결 범위·검증은 [생활형 부엌 재디자인](../docs/KITCHEN_LIFE_REDESIGN.md)을 확인한다. 처음 분리한 구조는 [앱과 위젯 기록](../docs/APP_AND_WIDGET.md), 최초 누락 자산 문제는 [검토 기록](../docs/STANDALONE_KITCHEN_PREVIEW.md)에 있다.
