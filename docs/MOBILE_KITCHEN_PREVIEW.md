# 휴대폰용 부엌 미리보기 전달

2026-10-28 사용자가 채팅 내부 파일 링크로는 휴대폰에서 확인하지 못했다고 지적했다. `sandbox:/workspace/...`를 휴대폰 웹 주소로 간주하지 않는다. 이 문서는 표시창 디자인이 아닌 **전달 경로**의 수정이다.

## 파일과 빌드

`previews/mobile/app.html`, `widget.html`은 각각 946,033바이트, 946,042바이트다. 현재 앱·위젯 원본과 그림을 모두 넣어 외부 CSS·JavaScript·이미지 없이 렌더링한다. 기존 원본 그림 내장형 약 11MB보다 작다.

```bash
source /workspace/.notion-cloud/activate.sh
python scripts/build_kitchen_mobile_preview.py
```

공개 파일 렌더러는 여러 사용자의 저장소가 같은 출처를 공유한다. 이 진입점은 `sandbox="allow-scripts"`의 독립 프레임으로 장면을 열고, 기존 저장 어댑터의 **임시 시안 저장**을 사용한다. 기존 앱 기록을 읽거나 수정하지 않는다. 직접 입력한 시안은 백업 화면에서 복사해 보관할 수 있으며, 페이지를 다시 열 때의 영구 저장·앱/위젯 간 공유는 이 공개 확인용 진입점의 범위가 아니다. 기존 HTML·저장 키·저장 형식을 바꾸지 않는다.

프레임은 휴대폰 화면의 실제 폭과 동적 높이를 사용한다. 전체 앱을 줄인 데스크톱 화면으로 표시하지 않는다.

## 확인 범위

[모바일 크기·터치 검사](miniature-kitchen/mobile-delivery-results.json)는 로컬 Chromium에서 iPhone 13 크기, Pixel 7 크기, 320×568의 앱·위젯 6개 조건으로 실행했다. 실제 iPhone/Safari 실기기 검증은 아니다. 두 제목, 가로 넘침, 프레임 폭, 네 문 터치 개폐, 재료 창, 백업 창, 임시 저장 상태, 외부 자원 요청 없음과 JavaScript 예외 없음을 확인했다.

휴대폰에서 열려면 공개 HTML 렌더러의 일반 HTTPS 주소를 제공해야 한다. Raw GitHub·jsDelivr의 HTML 파일은 `text/plain` 응답이라 코드가 표시되므로 실행 링크로 안내하지 않는다. GitHack은 HTML 렌더러로 사용할 수 있으나 이 클라우드에서는 해당 호스트와 GitHub Pages·HTMLPreview로의 연결이 `Tunnel connection failed: 403 Forbidden`으로 차단된다. 공개 파일 다운로드와 외부 렌더러 접속을 구별하고, 렌더러나 실기기 확인을 완료했다고 보고하지 않는다.

휴대폰 링크는 파일이 포함된 전체 커밋 해시를 고정해 다음 형태로 제공한다.

```text
https://raw.githack.com/Ohoredingdong/Notion/<commit>/previews/mobile/app.html
https://raw.githack.com/Ohoredingdong/Notion/<commit>/previews/mobile/widget.html
```

main·기존 GitHub Pages 배포는 변경하지 않는다. 공개 미리보기 파일과 빌드 코드를 기존 작업 브랜치에서 검토한다. 외부 주소의 확인 상태와 고정 링크는 공개 업로드 후 이 문서에 기록한다.

## 공개 업로드 결과

파일이 포함된 커밋은 `3ff0c81701c711d00fa04e4799d51378ecbb826d`다. 인증 없는 Raw GitHub 요청으로 앱·위젯 원본과 [휴대폰 화면 이미지](https://raw.githubusercontent.com/Ohoredingdong/Notion/3ff0c81701c711d00fa04e4799d51378ecbb826d/docs/miniature-kitchen/mobile-app.png)의 HTTP 200 및 로컬 파일과의 바이트 일치를 확인했다. 이미지는 `image/png`로 응답한다. [공개 접근 확인 기록](miniature-kitchen/mobile-public-results.json)을 따른다.

- [휴대폰용 앱 실행 주소](https://raw.githack.com/Ohoredingdong/Notion/3ff0c81701c711d00fa04e4799d51378ecbb826d/previews/mobile/app.html)
- [휴대폰용 위젯 실행 주소](https://raw.githack.com/Ohoredingdong/Notion/3ff0c81701c711d00fa04e4799d51378ecbb826d/previews/mobile/widget.html)

이 두 HTML 렌더러 주소는 현재 클라우드의 연결 차단으로 **응답·실행 미확인**이다. 공개 원본의 HTTP 200과 로컬 모바일 검사만으로 해당 주소가 실제 휴대폰에서 열렸다고 보고하지 않는다. 화면 이미지는 확인용 보조 자료이며 대화형 앱 실행을 대체하지 않는다.
