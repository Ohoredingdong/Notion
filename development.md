# 위젯 개발·검증·배포 안내

이 저장소는 정적 HTML/CSS/JavaScript와 금융 수집·가공 스크립트를 함께 운영합니다. 프런트엔드 프레임워크나 번들러를 추가하지 않았습니다. 개발 규칙은 [AGENTS.md](AGENTS.md), 작업 절차는 [widget-development 스킬](.agents/skills/widget-development/SKILL.md)을 따릅니다.

## 현재 운영 구조와 보호 범위

- 감사 기준은 `17d11d28fdf156f7a6f9ee7eeefe689e761cd83c`입니다. 그 시점 workflow 38개 중 24개가 정기 실행, 27개가 `contents: write`를 사용합니다. 원격 브랜치 174개를 확인했으며 정리·삭제하지 않았습니다.
- 금융 수집기는 `main`에 직접 자료를 쓰고 일부는 `/pages/builds`를 요청합니다. JSON/JSONL뿐 아니라 보고서·일부 자산을 쓰는 작업도 있습니다. 특히 예측 발행기는 HTML에 기존 예측 런타임 태그를 멱등 삽입하므로 무조건 JSON 전용으로 가정하지 않습니다.
- GitHub API는 이 개발 환경의 `api.github.com` 도메인 제한으로 403입니다. 실제 Pages 배포 소스, 브랜치 보호, GitHub 실행 이력은 **미확인**입니다. 소스에서 branch Pages 방식의 흔적을 발견한 것과 실제 설정 확인은 구분합니다.
- **현재 운영 Pages 경로를 CI가 강제로 차단한다고 보장하지 않습니다.** 운영 설정·브랜치 보호·정기 실행·수집기 발행 명령은 변경하지 않았습니다. 기존 경로와 충돌하는 필수 PR 규칙이나 배포 전환을 임의 적용하지 않습니다.
- 추가한 `Change-aware validation`은 PR/개발 브랜치와 완료된 데이터 writer를 읽기 전용으로 검사합니다. `GITHUB_TOKEN`의 push는 일반 push workflow를 다시 실행하지 않으므로 `workflow_run` 관찰을 보완했습니다. 빈번한 데이터 완료 이벤트는 실행 중 검사를 취소하지 않고 최신 대기를 합쳐 검사 진행이 굶지 않도록 합니다. GitHub 체인의 깊이 제한 때문에 이것도 모든 writer의 완전한 배포 차단 장치라고 주장하지 않습니다.
- 선행 수집기 실패로 연쇄 작업을 시작하지 않도록 5개 게시 job과 관련 UI job에 성공·동일 저장소 조건을 추가했습니다. 직접 schedule/manual/push 실행의 복구 경로와 기존 cron·권한·동시성·발행 명령은 보존합니다.

전수 조사 결과와 원본 해시는 [감사 보고서](docs/development-audit-20261105.md), [workflow 목록](docs/development-workflow-inventory.json)에 있습니다. 목록은 감사 시점의 기록이며 새 CI와 수동 release workflow는 그 뒤 추가된 것입니다.

## 환경 설치

Python 3.12와 Node.js 24를 사용합니다. 직접 의존성은 `requirements-dev.txt`, 검증에 사용한 전이 의존성 제약은 `requirements-dev.lock`, Node 잠금 파일은 `package-lock.json`입니다.

```sh
python3 -m venv /workspace/notion-dev/.venv
source /workspace/notion-dev/.venv/bin/activate
python -m pip install -r requirements-dev.txt
npm ci --ignore-scripts --no-audit --no-fund
```

이 클라우드 환경에는 `/usr/bin/chromium`이 있어 브라우저 다운로드 없이 사용할 수 있습니다. 다른 환경에서는 TLS·서명 검증을 유지하며 다음을 실행합니다. Playwright 배포 CDN이 차단되면 관리되는 네트워크 설정에서 필요한 도메인을 추가하거나 제공된 시스템 Chromium을 사용합니다.

```sh
python -m playwright install --with-deps chromium
```

도구 설치 자체가 테스트 통과를 의미하지 않습니다. 환경에 설치한 패키지와 실행 중인 서버는 구분하고, 새 태스크에서는 필요한 서버만 다시 시작합니다. 이 태스크는 이미 격리되어 있으므로 별도 worktree를 만들지 않습니다.

## 변경 파일과 검사 선택

작업 브랜치에서 변경 전 상태와 기준 화면을 보존합니다. 커밋에 포함된 변경 전체를 검사하려면 다음을 실행합니다.

```sh
python scripts/dev_check.py --base origin/main --head HEAD --run \
  --browser-executable /usr/bin/chromium --output /tmp/notion-check/report.json
```

미커밋 변경을 포함하려면 `--working-tree`를 추가합니다. 다른 사용자 작업이 남아 있으면 작업 파일을 정확히 지정합니다. `--files`는 **로컬 집중 검사**이며 PR 전체 검사나 배포 증거로 대체할 수 없습니다.

```sh
python scripts/dev_check.py --base origin/main --working-tree \
  --files assets/stock-radar-clean-bridge.js scripts/test_stock_radar_canonical_browser.py \
  --run --browser-executable /usr/bin/chromium --output /tmp/notion-focused/report.json
```

`--run`(또는 `--check`)을 생략하면 실행 계획만 출력합니다. 보고서에는 실제 base/head, 검사 명령·종료 코드·로그, `passed/failed/unrun/uncovered`가 들어갑니다. 검사 규칙이 없는 코드 변경은 문법 검사만으로 통과시키지 않습니다. 규칙을 추가하고 의미 있는 기존 검사나 회귀 검사를 연결해야 합니다. 삭제와 이름 변경도 기존 경로의 검사를 선택합니다.

모든 검사는 `/tmp`의 격리 사본에서 실행합니다. 원본 체크아웃의 JSON·이력·코드에 테스트 결과를 쓰지 않습니다. 설치된 Node 모듈은 `NODE_PATH`로 참조하되 source/data는 사본을 사용합니다. 생성·수집·발행 entrypoint를 테스트 명령으로 등록하는 것을 막습니다.

일반 HTML/JS/Python/JSON 문법·로컬 자산 검사와 기능 검사는 별도입니다. 자동 검사 규칙의 현재 범위는 `.github/validation-routes.json`에 명시돼 있습니다. [데이터 검사 연결 목록](docs/development-coverage-baseline.json)은 루트 JSON/JSONL95개 중20개 연결·75개 미지원인 계획 기록이며 실행 결과가 아닙니다.  모든 위젯·모든 금융 제공처를 검증했다고 확대 해석하지 않습니다. 외부 제공처 접근·최신성·실제 Notion 계정 화면은 별도 확인입니다.

## 투자 레이더 시범 절차

1. `stock-value-radar.html`과 그 JS·저장 키·소비 JSON·관련 writer를 읽습니다. `stock-radar-dashboard.html`은 query/hash를 보존하는 호환 진입점입니다.
2. 동일한 자료·시각·브라우저 상태로 변경 전 화면을 캡처합니다.
3. 기능을 수정하고 관련 Node·Python 검사 및 canonical 브라우저 검사를 실행합니다.
4. 같은 조건의 변경 후 화면을 비교합니다. localStorage의 기존 즐겨찾기·수기 조건·모의보유·선택을 재로드해 확인합니다.
5. `git diff --check`, 데이터 변경·기존 사용자 작업 보존을 확인하고 정확한 파일만 commit/push합니다.
6. PR 템플릿에 실제 검사·증거와 미검증 범위를 적습니다. merge·운영 deploy는 사용자 승인 후 별도 진행합니다.

```sh
python scripts/test_stock_radar_canonical_browser.py \
  --browser-executable /usr/bin/chromium --output /tmp/radar-current
python scripts/test_stock_radar_publish_protection.py
python scripts/check_workflow_policy.py --output /tmp/workflow-policy/report.json
```

canonical 검사는 실제 저장 자료로 레이아웃·선택·검색·상세·표시 의미·보존·복구를 확인합니다. 실패 응답·잘못된 확률 등은 별도 명시된 테스트에서만 주입합니다. 1629×929/1366×768의 기존 geometry 검사를 유지하고 desktop/mobile/실제 iframe를 포함합니다. 현재 유효한 V6 상세 계약을 포함해 오래된 고정 스크립트 개수와 neutral selector를 대체했습니다. 이전 테스트 파일은 삭제하지 않았으며, 보존용/이전 테마 테스트를 현행 UI의 통과 근거로 사용하지 않습니다.

모의보유의 선택 종목이 submit 후 전역 선택 종목으로 돌아가던 오류는 메모리 form 상태로 수정했습니다. 기존 저장 형식과 자료를 바꾸지 않고 반복 추가·가중평균·다른 보유 보존을 검증합니다.

## 배포 보호: 준비된 경로와 활성 경로 구분

추가한 `reviewed-pages-release.yml`은 `workflow_dispatch`만 허용하고, 기본값이 **dry run**, `.github/release-policy.json`의 운영 활성화가 **false**입니다. 지금 자동으로 실행되거나 현재 Pages 방식을 전환하지 않습니다.

이 경로는 후보 SHA와 실제 검사 SHA를 묶고 다음을 요구합니다.

- 전체 commit diff 검사와 매번 수행하는 투자 레이더 필수 검사 모두 통과.
- 실제 브라우저의 nonempty 결과와 대상 소스 SHA 일치.
- Git에 추적된 명시적 공개 파일만 패키징. `.github`, `.agents`, 테스트·서버 코드·개인 설정·미추적 작업은 제외.
- 자료·보고서·artifact bytes에 대한 해시 재검증. 배포 대상 main이 진행했으면 재검증 요청.
- 실제 운영 시에는 별도 검토된 정책 활성화, `DEPLOY <정확한 SHA>` 확인, 관찰된 Pages `build_type: workflow`가 필요. branch Pages이거나 설정을 읽지 못하면 거부.

**활성화는 별도 승인 작업입니다.** 실제 GitHub Pages 설정과 기존 writer·Pages 요청 경로를 확인한 뒤, 금융 갱신이 배포되는 전체 경로를 설계·승인해야 합니다. 현재의 disabled-policy 회귀 조건도 그 승인 PR에서 명시적으로 검토해야 합니다. 현재 main 직접 writer에 무작정 PR 필수화를 적용하거나 Pages를 전환하면 자동 갱신을 끊을 수 있습니다.

이 수동 경로를 나중에 활성화하더라도 체크 직후 main이 바뀌는 작은 경쟁 구간은 있습니다. 기존 writer를 정지·reset하지 않으므로 future migration에서는 후보 snapshot과 데이터 갱신을 함께 조율해야 합니다. 이런 한계를 숨겨 완전 강제 보호로 보고하지 않습니다.

## 실제 실행 증거와 남은 범위

이번 작업의 최종 실행 결과·파일 목록·산출물 경로·제한은 [개발 검증 결과](docs/development-validation-20261105.md)에 기록합니다. 계획, 로컬 실행, 실제 원격 CI, 실제 운영 배포 결과를 구분합니다. API 도메인 허용 초안 저장은 실제 네트워크 적용이나 PR 생성 성공을 의미하지 않습니다.
