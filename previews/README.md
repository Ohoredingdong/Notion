# 한끼의 부엌 앱·위젯 미리보기

현재 기준은 [11월 4일 전체 동선 실제 적용](../docs/KITCHEN_FULL_FLOW_APPLIED_2026-11-04.md)이다. 메인 메뉴는 **냉장고·레시피·기록·내 부엌**이며, 재료 사진2장 검수·계획/실제 식사·영양/영양제/월간/식비·소품 선택/적용을 연결한다.

- [실제 구현 화면 24장 갤러리](kitchen-full-flow-actual-20261104/index.html): 격리 예시 데이터로 캡처한 실제 화면, 버튼→다음 화면 표시.
- [휴대폰 위젯](mobile/widget.html), [휴대폰 앱](mobile/app.html): 공유 출처와 저장을 격리하는 임시 세션.
- [Standalone 앱](miniature-kitchen-app.html), [Standalone 위젯](miniature-kitchen-widget.html), [나란히 보기](miniature-kitchen-board.html): 저장 가능한 출처에서는 기존 `miniature-kitchen-preview-v1` version1과 JSON 백업/복원을 유지한다.
- [설계 시안 5장](kitchen-full-flow-20261104.html): 실제 구현 갤러리와 구분한 화면·화살표 설계 원본.

소스는 `designs/miniature-kitchen/`이며 `scene.html`은 생성용 템플릿이다. 운영 진입점과 main/Pages는 별도 검토 전까지 바꾸지 않는다. 실제 사용자의 예전 재고/기록을 예시로 간주하거나 초기화하지 않는다.

```bash
python scripts/build_miniature_kitchen_preview.py --compact --output-dir /tmp/kitchen-preview
python scripts/build_kitchen_mobile_preview.py --output-dir /tmp/kitchen-mobile
```

compact 생성에는 저장소 밖의 ImageMagick, Terser, clean-css가 필요하다. 원본 파일을 보존하고 기존 전달 해상도·비율·품질을 유지하며 선택한 AVIF 및 미사용 아틀라스 영역 제거, 텍스트 무손실 포장을 사용한다. 네 전달 파일은 각각 1MiB 이하이며 포장을 풀면 원문 바이트와 같다. 정확한 최종 파일 해시와 환경/시각/기능/공개 실행 증거는 적용 기록에 있다.

이전 생활형 미리보기 [앱](use-me-first.html)·[위젯](use-me-first-widget.html), [이전 재디자인 기록](../docs/KITCHEN_LIFE_REDESIGN.md), [최초 미니어처 설계](../docs/MINIATURE_KITCHEN_DESIGN.md)는 이력과 호환 경로로 보존한다. 이 이전 시안의 외형을 최신 선택으로 취급하지 않는다.
