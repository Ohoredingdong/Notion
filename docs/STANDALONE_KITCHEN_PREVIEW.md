# 단일 HTML 미리보기의 누락 자산 복구

아래는 최초 복구 시점의 기록이다. 이후 [양념 기한·디자인 변경](SEASONING_EXPIRY_AND_DESIGN.md)으로 미리보기에 세 번째 이미지인 양념 PNG를 포함했으며, 현재 파일은 약 3.62MB다. 최신 단일 파일 검사 32개는 해당 변경 기록에 보관한다.

## 사용자 화면과 재현

사용자가 전달한 화면에는 기본 HTML만 표시되고 냉장고와 스타일이 없었다. 원래 `use-me-first.html`은 같은 디렉터리의 CSS 2개·JavaScript 11개·이미지를 참조한다. HTML만 다른 경로에 표시하고 자산을 제공하지 않는 조건에서 동일한 모양을 재현했다. 초기 자산 요청 14개가 실패하고 `.fridge-door`는 0개, `UMFKitchen`은 미생성이었다. [요청 기록](standalone-kitchen-preview/reproduction.json)에 누락 파일을 남겼다. 사용자 측 시각화 호스트의 콘솔·네트워크 로그 자체를 확인한 것은 아니다.

| 같은 931×900px, 초기 재고 없음 | 화면 |
| --- | --- |
| 변경 전: 원래 HTML만 제공, 상대 자산 없음 | [화면](standalone-kitchen-preview/before.png) |
| 변경 후: 단일 HTML만 제공, 나머지 요청 차단 | [화면](standalone-kitchen-preview/after.png) |

## 변경 범위

`previews/use-me-first.html`은 기존 앱의 스타일·스크립트·두 WebP 이미지를 모두 포함한 약 1.51MB의 미리보기다. 원래 HTML에서 참조 순서를 읽어 스크립트를 본문 뒤에 배치하며, Google Fonts 다운로드 대신 기존 CSS의 대체 글꼴을 사용한다. 생성기는 `scripts/build_fridge_preview.py`다. 기능을 따로 재구현하거나 원본 CSS·앱 로직·배포 진입점을 변경하지 않는다.

사용자의 재고·동기화 코드·인증정보를 포함하지 않는다. 기존 저장 키와 저장 로직을 그대로 사용한다. 다른 도메인·로컬 파일에서 열면 출처가 다르므로 GitHub Pages의 기존 기록을 자동으로 가져오지 않는다. 저장을 허용하지 않는 iframe에서 가짜 저장 성공이나 임시 저장을 영구 저장처럼 표시하지 않고 기존 오류 안내를 유지한다.

원본을 수정하면 아래 명령으로 미리보기를 다시 생성한다. 생성한 HTML을 직접 수정하지 않는다. main 병합·GitHub Pages 배포는 수행하지 않았다.

```bash
python scripts/build_fridge_preview.py --output previews/use-me-first.html
```

## 검증 결과

- Node 회귀: 138개 통과, 실패·건너뜀 0개.
- 단일 파일만 있는 별도 디렉터리에서 Chromium 검증: 1120/390/320px의 기존 주요 흐름 21개 통과. 이미지 디코딩, 외부 자산 요청 0건, JavaScript 실행 오류 0건을 추가로 확인했다.
- `srcdoc` iframe: 냉동실 개폐·재료 추가·iframe 새로고침 후 저장 보존 통과. 저장 권한이 없는 opaque iframe에서도 스타일·냉장고 렌더링 및 저장 불가 안내 통과. 위 21개와 합쳐 [23개 통과](standalone-kitchen-preview/browser-results.json).
- 최종 생성 파일이 이 23개 검사에 사용한 파일과 바이트 단위로 같은지 확인했다.
- 클라우드 Chromium의 `file://` 직접 탐색은 `ERR_BLOCKED_BY_ADMINISTRATOR`로 차단되어 검증하지 못했다. 위 검사는 단일 파일 HTTP 응답과 iframe으로 실행했다. 실제 사용자 채팅 시각화·실기기 브라우저·Notion·공개 배포 화면을 확인했다고 주장하지 않는다.

별도 디렉터리 검증을 재현하려면 저장소 루트에서 다음을 실행한다. 테스트 중 외부 서비스 쓰기는 차단하고 합성 기록만 사용한다.

```bash
python scripts/build_fridge_preview.py --output /tmp/notion-preview/use-me-first.html
python scripts/test_fridge_four_door_browser.py \
  --root /tmp/notion-preview --output /tmp/notion-preview-results \
  --standalone --browser-executable /usr/bin/chromium
```
