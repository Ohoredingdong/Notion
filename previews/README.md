# 한끼의 부엌 앱·위젯 미리보기

[앱](use-me-first.html)과 [위젯](use-me-first-widget.html)은 같은 냉장고의 CSS·JavaScript·이미지를 포함한 생성 파일이다. 기능·디자인은 공유하고 기본 배치만 다르다. HTML만 전달되는 미리보기 환경에서도 별도 자산 경로가 필요 없다. 직접 수정하지 않고 저장소 루트에서 다시 생성한다.

```bash
python scripts/build_fridge_preview.py --presentation app --output previews/use-me-first.html
python scripts/build_fridge_preview.py --presentation widget --output previews/use-me-first-widget.html
```

배포 진입점과 수정할 원본은 루트의 `use-me-first.html` 및 이 파일이 참조하는 CSS·JavaScript다. 이 미리보기에 사용자 기록·동기화 코드를 넣지 않는다. 기록은 실행한 브라우저의 해당 출처에 저장되며, 다른 출처의 기존 데이터를 자동으로 가져오지 않는다. 저장이 제한된 iframe에서는 기존 앱의 저장 불가 안내가 표시된다.

두 버전의 구성·검증은 [앱과 위젯 기록](../docs/APP_AND_WIDGET.md)을 확인한다. 최초 누락 자산 문제는 [검토 기록](../docs/STANDALONE_KITCHEN_PREVIEW.md)에 있다.
