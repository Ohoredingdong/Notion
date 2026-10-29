# 한끼의 부엌 앱·위젯 미리보기

현재 화면은 사용자가 선택한 [이미지 시안 01의 세로형 유리 표시창·밝은 크림/오크 배경](../docs/APPROVED_KITCHEN_CONCEPT_2026-10-29.md)을 반영한다. 휴대폰에서는 상단 **표시창 크게 보기**로 상세 구성을 읽는다. [앱·위젯 나란히 보기](miniature-kitchen-board.html), [앱 시안](miniature-kitchen-app.html), [위젯 시안](miniature-kitchen-widget.html)에서 확인한다. 이 세 파일은 독립 디자인·조작 시안으로 예시 재료만 사용하며 기존 앱 기록에 접근하지 않는다. 저장 가능한 출처에서는 전용 시안 키로 기록을 보관하며 공개 미리보기 프레임은 임시 저장·JSON 백업을 사용한다. 아래 기존 미리보기는 사용자가 거절한 생활형 시안의 구현 이력으로 보존한다.

```bash
python scripts/build_miniature_kitchen_preview.py
```

소스는 `designs/miniature-kitchen/`이며 `scene.html`은 생성용 템플릿이다. 단일 HTML 두 개와 비교 페이지를 생성한 뒤 검토한다. 새 디자인의 범위·자료·검증은 [미니어처 부엌 기록](../docs/MINIATURE_KITCHEN_DESIGN.md)을 따른다.

HTML 파일 링크가 채팅의 소스 보기로 열리는 문제가 보고되었다. 일반 브라우저에서의 실행 성공을 채팅 내 실행 성공으로 보고하지 않는다. 화면 이미지나 ZIP 전달도 사용자가 요청한 조작 가능한 미리보기의 완료 기준이 아니다.

채팅에는 이미지까지 모두 포함한 단일 HTML을 `sandbox:` 파일 링크로 전달한다. 외부 이미지 URL을 사용했던 경량판은 사용자 화면에서 그림이 깨졌다. 원본 이미지를 내장한 9.35MB 파일도 사용자가 표시되지 않는다고 보고했으므로 완료로 취급하지 않는다. 구체적인 클라이언트 용량 제한은 확인되지 않았다.

```bash
python scripts/build_miniature_kitchen_preview.py --compact \
  --output-dir /workspace/artifacts/kitchen-size-fixed
```

`--compact`는 ImageMagick의 `magick`이 필요하다. 원본 파일을 보존하고, 미리보기 그림을 WebP 품질 82·알파 품질 100으로 인코딩한다. 해상도와 현재 선택 가능한 재료·양념·요리·소품을 유지하며 사용하지 않는 아틀라스 칸만 제외한다. 최신 앱·위젯은 각각 약 938KB이며, 1MiB를 넘으면 생성에 실패하도록 자체 전달 예산을 정했다. 이것은 확인된 클라이언트 제한값을 뜻하지 않는다. 기본 명령은 원본 이미지를 포함한 파일을 생성한다.

2026-10-25 사용자 스크린샷에서 UI·그림 표시를 확인한 뒤 냉장고 크기와 위치 피드백을 반영했다. 작은 화면에서 냉장고를 폭에 맞춰 확대하고 바닥에 배치하며 문 버튼은 그림 아래에 둔다. 커진 화면은 세로로 스크롤한다. 외부 자산 요청을 차단한 브라우저의 52개 점검과 편집 상태를 유지한 화면 크기 변경을 확인했다. 새 배치의 최종 디자인 승인은 아직 아니다. 자세한 증거는 [미니어처 부엌 기록](../docs/MINIATURE_KITCHEN_DESIGN.md)을 따른다.

[앱](use-me-first.html)과 [위젯](use-me-first-widget.html)은 같은 냉장고의 CSS·JavaScript·이미지를 포함한 생성 파일이다. 기능·디자인은 공유하고 기본 배치만 다르다. HTML만 전달되는 미리보기 환경에서도 별도 자산 경로가 필요 없다. 직접 수정하지 않고 저장소 루트에서 다시 생성한다.

```bash
python scripts/build_fridge_preview.py --presentation app --output previews/use-me-first.html
python scripts/build_fridge_preview.py --presentation widget --output previews/use-me-first-widget.html
```

배포 진입점과 수정할 원본은 루트의 `use-me-first.html` 및 이 파일이 참조하는 CSS·JavaScript다. 이 미리보기에 사용자 기록·동기화 코드를 넣지 않는다. 기록은 실행한 브라우저의 해당 출처에 저장되며, 다른 출처의 기존 데이터를 자동으로 가져오지 않는다. 저장이 제한된 iframe에서는 기존 앱의 저장 불가 안내가 표시된다.

두 버전의 최신 디자인·생활 기능·미연결 범위·검증은 [생활형 부엌 재디자인](../docs/KITCHEN_LIFE_REDESIGN.md)을 확인한다. 처음 분리한 구조는 [앱과 위젯 기록](../docs/APP_AND_WIDGET.md), 최초 누락 자산 문제는 [검토 기록](../docs/STANDALONE_KITCHEN_PREVIEW.md)에 있다.
