# 위젯 개발·검증·PR 절차

이 절차는 위젯을 실제로 수정하고 테스트한 뒤 PR로 전달하기 위한 개발 경로다. 이 문서를 추가했다는 사실만으로 원격 브랜치 보호나 운영 배포 정책이 바뀌지는 않는다. [공통 규칙](../AGENTS.md), [재사용 스킬](../.agents/skills/widget-development/SKILL.md), [자동화 점검 기록](development-audit.md)을 함께 읽는다.

## 사용자가 활용하는 방법

개발 체계가 아직 main에 병합되지 않았다면 새 Codex 작업의 저장소 기준을 `codex/development-safety-system` 브랜치로 선택한다. main에서 시작한 새 작업에는 이 브랜치의 AGENTS·스킬·검사 도구가 아직 없을 수 있다. 이 브랜치에서 별도 기능 브랜치를 만들어 변경을 검토하고, 공통 체계를 승인해 main에 반영한 뒤에는 main 기준 작업에서도 같은 규칙을 사용할 수 있다.

매번 도구 명령을 직접 입력할 필요는 없다. 바꾸고 싶은 화면과 유지할 조건을 구체적으로 요청한다.

> 경매노트의 모바일 카드 비율을 조정해 줘. 기존 iOS 스타일과 한 화면 배치는 유지하고, 금액 줄바꿈·버튼 잘림을 확인해. 수정 전후 PC·모바일·노션 크기 iframe을 비교하고 관련 테스트를 실행한 뒤 PR까지 준비해. 배포는 하지 마.

> 투자 레이더에 관심종목 필터를 추가해 줘. 기존 저장 기록과 금융 갱신은 보존하고, 필터·새로고침·요청 실패를 테스트해. 실제 검증 결과와 남은 문제를 보고해 줘.

Codex는 조사 → 기준 화면 저장 → 작은 구현 → 관련 검사 → 브라우저·전후 비교 → 작업 브랜치·PR 준비 순서로 진행한다. 사용자는 전후 이미지, 실제 검사 결과, 사용자 기록·금융 갱신 영향과 남은 제한을 검토한다. 기능·디자인이 승인되기 전에는 운영 반영을 진행하지 않는다.

`구현 완료`, `작업 브랜치에 푸시`, `PR 생성`, `운영 배포 완료`는 서로 다른 상태다. 작업 브랜치에만 있는 수정은 현재 공개 사이트에 자동 반영된 것으로 보지 않는다. 이 환경에서 GitHub API가 차단되면 PR 번호를 만들었다고 보고하지 않고 본문·브랜치를 보관한다. 공개 배포 승인은 검토한 변경과 대상 커밋을 명시한 뒤 별도로 진행한다.

## 운영 구조를 먼저 이해하기

이 저장소는 별도 프런트엔드 빌드 없이 루트 HTML·JS·CSS·저장된 JSON을 제공한다. 투자 레이더의 주요 진입점은 `stock-value-radar.html`이며 `stock-radar-dashboard.html` 등 호환 주소와 로드 자산을 함께 확인해야 한다.

금융 수집·연구·감사 Actions는 main에 직접 데이터를 갱신하고, 일부는 `repos/.../pages/builds`로 Pages 빌드도 요청한다. 일반 코드 PR과 운영 데이터 갱신은 동일한 main을 공유한다. publisher가 수정하는 파일은 JSON이라고 가정하지 말고 실제 스크립트와 허용 목록을 확인한다.

현재 환경에서는 GitHub API 조회가 네트워크 정책으로 거절되었다. 따라서 Pages의 원격 소스 설정, 실제 브랜치 보호 상태, 최근 Actions 실행 결과를 조회한 것으로 보고하지 않는다. 저장소의 워크플로 코드로 확인한 구조와 원격 실행 관측을 구분한다.

## 개발 준비

저장소 루트에서 시작한다. 기존 격리 체크아웃을 사용하고 별도 작업 브랜치를 만든다. 기존 변경이 있으면 먼저 기록·보존한다.

```sh
git status --short
git branch --show-current
git fetch origin main
git switch -c codex/my-widget-change
```

main 최신 상태를 기준으로 시작하거나 기존 작업 브랜치의 base를 명시한다. 이미 작업 중인 파일·커밋을 초기화하지 않는다. 브랜치 이름은 작업마다 겹치지 않게 정한다.

새 로컬 환경에서는 다음 개발 의존성을 설치한다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
npm ci
bash scripts/install_actionlint.sh .dev-artifacts/tools
export PATH="$PWD/.dev-artifacts/tools:$PATH"
.venv/bin/python -m playwright install chromium
```

이후 명령의 `python`은 해당 가상환경의 Python을 사용한다. 클라우드에 이미 준비된 의존성이 있으면 기존 구성을 재사용할 수 있다. 시스템 Chromium을 사용할 때는 브라우저 검사에 `--executable /usr/bin/chromium`을 전달한다. CI의 Playwright 번들 Chromium과 시스템 Chromium의 차이를 결과에 남긴다. 브라우저 설치·네트워크 오류를 TLS 검증 해제로 해결하지 않는다.

## 구현 전 확인

1. 실제 HTML 진입점에서 로드하는 자산·데이터·저장 키를 찾는다.
2. 기존 시안·요구사항과 관련된 테스트·Actions 경로 필터를 읽는다.
3. 관련 기존 검사를 실행해 통과와 기존 실패를 기록한다.
4. 같은 데이터·URL의 데스크톱·모바일·Notion 크기 iframe 화면을 기준 캡처로 남긴다. 작은 글씨, 카드 비율, 잘린 버튼, 패널 넘침도 직접 본다.

실제 개인 기록이나 계정으로 브라우저 상태를 준비하지 않는다. 테스트는 독립 브라우저 컨텍스트의 명시적인 입력을 쓰며 실제 자료를 가짜 성공으로 바꾸지 않는다.

## 변경에 관련된 검사 실행

커밋된 변경과 작업 중인 변경을 함께 검사하려면 저장소 루트에서 실행한다.

```sh
python scripts/check_changed.py --base origin/main --head HEAD --working-tree --browser --artifacts /tmp/widget-checks
```

커밋된 범위만 검사하려면 `--working-tree`를 제외한다. 변경 파일에 따라 기존 검사를 재사용하며 검사 선택과 결과는 실행기의 보고서에서 확인한다. 명령에 브라우저 검증을 요청했더라도 관련 UI 대상이 없어서 실행되지 않았다면 그 사실을 구분한다. 요청한 동작의 핵심 검사가 빠져 있으면 기존 테스트를 확장하거나 회귀 검사를 추가한다.

설치된 시스템 브라우저를 사용하려면 다음처럼 지정한다.

```sh
python scripts/check_changed.py --base origin/main --head HEAD --working-tree --browser --executable /usr/bin/chromium --artifacts /tmp/widget-checks
```

실패한 출력의 종료 코드를 보존한다. 0개 실행·미실행·건너뜀을 통과로 적지 않는다. 환경 오류와 제품 결함을 조사하고, 수정 뒤에는 해당 검사를 다시 실행한다. 체크아웃을 수정하는 publisher나 실제 시장 수집 작업을 로컬 검증 명령으로 대신 실행하지 않는다.

## 투자 레이더 시범 검증

별도 터미널에서 저장소 루트를 제공한다.

```sh
python -m http.server 8766 --bind 127.0.0.1
```

다른 터미널에서 아래 검사를 실행한다. 첫 명령 전에는 수정 전 상태, 두 번째 명령 전에는 수정 후 상태를 준비해 같은 조건으로 비교한다.

```sh
python scripts/test_radar_development_browser.py --base-url http://127.0.0.1:8766/ --artifacts /tmp/radar-before
python scripts/test_radar_development_browser.py --base-url http://127.0.0.1:8766/ --artifacts /tmp/radar-after
```

시스템 브라우저가 필요하면 각 명령에 `--executable /usr/bin/chromium`을 추가한다. 기존 정상 브라우저 테스트도 변경 범위에 해당하면 실행한다. 새로운 검사가 기존 실패를 감추기 위해 오래된 검사를 대체하지 않게 한다.

데스크톱·모바일·iframe 결과와 실제 데이터 표시, 대표 종목 이동, 저장·새로고침, 자료 요청 실패 상태를 확인한다. 수정 전후의 캡처는 동일한 크기·데이터·상태인지 확인하고 수동으로 읽어 본다. iframe 검증과 실제 Notion 임베드 검증, 로컬 응답과 공개 사이트 응답은 각각 구분한다.

## PR 생성과 검토

```sh
git diff --check
git status --short
git diff --stat
```

예상하지 않은 데이터·설정·생성물 변경을 확인한다. 필요한 파일만 커밋하고 작업 브랜치를 푸시한다. PR은 `.github/PULL_REQUEST_TEMPLATE.md`를 바탕으로 작성하며 자동 병합을 켜지 않는다. PR 설명에는 문제와 바뀐 동작, 실제 검사 결과, 전후 화면, 기존 데이터와 금융 갱신 보존, 미검증 항목을 적는다.

```sh
git push -u origin codex/my-widget-change
gh pr create --draft --base main --head codex/my-widget-change --title '위젯의 구체적인 변경' --body-file /tmp/widget-pr.md
```

Git read·브랜치 push·GitHub API 접근은 서로 다른 권한과 경로다. 기존 Git 인증이 동작하는데 토큰 환경변수가 없다는 이유로 새 자격증명을 요구하지 않는다. API나 네트워크 때문에 PR 생성이 막혔다면 브랜치·검증 결과·PR 본문을 보존하고 실제 실패를 보고한다. 만들어지지 않은 PR 링크나 번호를 성공으로 적지 않는다.

## 검증 산출물과 게시 후보

새 `widget-development.yml`은 PR과 개발 브랜치에서만 읽기 전용으로 실행됩니다. 변경 파일을 분류하고 임시 소스 복사본에서 기존 검사와 필요한 브라우저 프로필을 실행합니다. 알려지지 않은 실행 코드·UI의 기능 검사, 요청하지 않은 필수 브라우저 검사, 검사 중 바뀐 소스는 `incomplete`이며 성공으로 처리하지 않습니다. 기존 운영 수집·게시 명령은 호출하지 않습니다.

`widget-release-candidate.yml`은 수동 실행 전용이며 **배포하지 않습니다**. 모든 지원 프로필의 검사 성공 후 `prepare_release.py`가 깨끗하게 커밋된 정확한 소스와 검사 결과를 대조해 검토용 정적 압축 파일을 만듭니다. 실패·취소·누락·다른 커밋·검사 뒤 수정은 후보 생성을 차단합니다. 이 파일은 자동 게시되지 않으며 Pages 설정도 바꾸지 않습니다.

```sh
python scripts/check_changed.py --base origin/main --head HEAD --profile tooling --browser --artifacts /tmp/widget-checks
python scripts/prepare_release.py --report /tmp/widget-checks/report.json --output /tmp/widget-release-candidate.tar.gz
```

시스템 Chromium은 첫 명령에 `--executable /usr/bin/chromium`을 추가합니다. 두 번째 명령은 커밋되지 않은 변경이 있으면 실패하는 것이 정상입니다. 검토용 파일의 JSON manifest에 소스 커밋·파일별 SHA-256·검사 보고서 SHA-256이 들어갑니다. 이는 소스와 결과의 불일치 방지 장치이며 원격 CI의 신뢰 증명이나 배포 승인 자체가 아닙니다.

개발 의존성 갱신은 `requirements-dev.in`을 고친 뒤 `uv pip compile requirements-dev.in --generate-hashes --python-version 3.12 --native-tls --output-file requirements-dev.txt`로 수행하고 다시 설치·검증합니다. Node는 `package.json`을 명시적으로 변경한 뒤 lock을 갱신하고 평소에는 `npm ci`를 사용합니다.

## 배포 보호의 현재 한계와 승인 후 전환안

추가한 PR 검사만으로 **main을 직접 게시하는 Pages가 실패 코드를 절대 배포하지 않는다**고 보장할 수 없다. main 푸시 뒤 실행되는 테스트는 배포가 먼저 일어나는 것을 막지 못할 수 있으며, 브랜치 보호의 필수 검사 설정도 원격에서 별도로 확인해야 한다.

기존 금융 자동화를 유지하기 위해 이번 개발 작업에서는 Pages 소스, 브랜치 보호, 데이터 봇의 main 직접 갱신을 임의로 변경하지 않는다. 다음은 **아직 활성화되지 않은 승인 대상 설계**다.

1. 원격 Pages 소스·필수 검사·데이터 publisher의 인증과 수정 대상을 확인한다.
2. 현재 정상 게시 커밋과 정적 산출물, 최신 데이터 보존·복구 경로를 기록한다.
3. Pages 배포를 명시적인 게이트가 있는 Actions 경로로 전환한다. 검사에 성공한 정확한 커밋의 산출물만 게시하고 실패·취소·누락된 검사는 게시하지 않는다.
4. 데이터 전용 갱신은 별도로 감지하되 필수 데이터 무결성 검사와 공개 배포 연속성을 확인한다. 봇 토큰 푸시가 후속 workflow를 유발하는지도 실제 계정·설정에서 검증한다.
5. 코드 변경의 최초 운영 반영은 사용자 승인 뒤 진행한다. 기존 갱신 작업과 충돌하거나 최신 데이터를 덮어쓰는 문제가 있으면 이전 정상 배포 경로로 복구한다.

이 전환은 문서·로컬 테스트만으로 완료되지 않는다. 사용자 승인, 원격 설정의 실제 적용, 금융 갱신과 실패 차단의 재검증이 모두 필요하다.

## 완료 보고에 남길 증거

- 작업 브랜치·기준/최종 커밋과 실제 변경 파일
- 실제 실행한 검사와 통과·실패·미실행 결과, 진단·재검증 내용
- 수정 전후 데스크톱·모바일·iframe 캡처
- 기존 기능·사용자 기록·금융 갱신에 미치는 영향
- 원격 PR·CI·배포·공개 사이트 확인을 각각 했는지 여부
- 미해결 원인과 필요한 외부 설정 또는 승인

운영 병합·배포는 사용자 승인 범위에서만 수행한다. main push나 Pages 게시를 PR 작업의 마무리 명령으로 실행하지 않는다.
