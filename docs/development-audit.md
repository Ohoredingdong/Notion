# 개발 환경·자동화 감사

기준: 2026-11-05, 작업 시작 시 `main`의 `17d11d28fdf156f7a6f9ee7eeefe689e761cd83c`. 아래 38개 목록과 수치는 **개선 전 소스 기준**입니다. 이 PR에서 추가한 검사는 별도이며, 최신 전체 목록은 아래 명령으로 다시 생성합니다.

```sh
python scripts/audit_workflows.py --check --output /tmp/notion-workflow-inventory.json
python -m unittest discover -s tests -p 'test_workflow_inventory.py' -v
```

`audit_workflows.py`는 YAML·리터럴 실행 파일·unittest 모듈·실행 조건·권한·게시 단계·중복 검사·연결되지 않은 테스트 후보를 JSON으로 기록합니다. 작업을 실행하거나 GitHub 설정을 변경하지 않습니다. `--check`는 잘못된 YAML, 중복 workflow 이름, 존재하지 않는 리터럴 실행 파일·구문 검사 자산을 실패로 반환합니다. 동적으로 조합한 경로와 런타임 셸·네트워크·허용 권한까지 보증하는 검사는 아닙니다. 미연결 테스트 목록도 동적 discovery가 가능한지 검토해야 하는 정적 힌트입니다.

## 확인한 범위와 미확인 범위

- 전체 기존 workflow **38개 / job 39개**, 예약 workflow **24개**, `pull_request` 이벤트 **5개**.
- 최상위 `contents: write` **27개**. 저장소 파일을 쓰는 단계가 있는 workflow도 **27개**이며, 일부는 디자인 브랜치에만 씁니다. 이를 모두 main publisher로 해석하면 안 됩니다.
- 명시적인 Pages build API 호출 **3개**: `stock-forecasts.yml`, `stock-entry-plan.yml`, `test-stock-neutral-ui.yml`.
- 리터럴 Python/Node 스크립트와 unittest 모듈 참조는 모두 존재했습니다. 파싱 실패·누락 파일 0건입니다.
- HTTPS Git 읽기로 원격 기본 브랜치 `main`과 원격 브랜치 **175개**를 확인했습니다. `research/` 63개, `fix/` 33개, `feat/` 18개, `preview/` 17개, `delivery/` 16개, `design/` 9개 등 여러 실험·배달 브랜치가 공존합니다. 브랜치는 삭제하거나 정리하지 않았습니다. 기존 `codex/dev-safety-pr-workflow-20261105`도 있으므로 중복 검토가 필요합니다.
- GitHub API와 공개 Pages 주소는 현재 클라우드 네트워크 정책에서 차단되어 있습니다. **Actions 과거 실행 성공률·현재 Pages source/build type·브랜치 보호·필수 검사·환경 승인자 설정은 미확인**입니다. 소스에 `main` 게시가 있다는 사실과 서버 설정을 확인한 것은 다릅니다.

## 운영 데이터 갱신과 충돌하는 지점

`publish_widget_data.py`는 수집 checkout과 분리된 임시 checkout에서 최신 `origin/main`을 받아 명시한 JSON만 정상 fast-forward push합니다. 전체 JSON bundle의 기준 시각을 비교하고, 더 최신 자료가 있거나 충돌을 판단할 시각이 없으면 원격 내용을 보존합니다. `test_widget_data_repairs.py`에는 실제 임시 Git 저장소의 연속 push 경합·과거 데이터 덮어쓰기 방지·공식 표 검증 테스트가 있습니다.

`publish_stock_forecasts.py`는 상태 CAS와 변경 불가 JSONL 충돌을 별도로 다룹니다. `publish_stock_opportunities.py`는 수집기 소스 fingerprint를 비교합니다. 다만 기회·시장분류·투자사례 publisher에는 구형 UI 자산과 installer를 함께 stage하는 경로도 남아 있습니다. `scripts/test_stock_radar_publish_protection.py`는 사용자 확정 홈페이지가 이 목록에 끼어들지 않는지 검사합니다.

따라서 지금 `main` 전체에 PR 강제·새 required check·새 배포 원본을 바로 켜면 봇 데이터 갱신을 막거나 예상치 못한 오래된 snapshot을 배포할 수 있습니다. **이 PR은 기존 데이터 스케줄·publisher·main 권한·Pages 설정을 자동으로 전환하지 않습니다.** 소스 수정은 작업 브랜치→읽기 전용 검사→PR 리뷰→사용자 승인으로 진행합니다. 운영 배포를 실제로 완전히 막는 정책 활성화에는 현행 Pages source·봇 권한·승인 환경을 확인한 뒤 별도 승인이 필요합니다.

## 발견한 오류·누락과 조치 기준

### 확인된 구형 UI 검사 충돌

개선 전 `test-stock-neutral-ui.yml`의 비예약 `verify` job은 `install_stock_radar_neutral.py`를 실행해 현재 `flow-v3` 홈페이지에 구형 neutral CSS·JS를 추가한 다음, `main`에서 `git diff --exit-code`를 요구했습니다. 필요한 6개 파일을 임시 폴더에 복사해 재현했으며 installer는 종료 0이지만 홈페이지 바이트가 바뀌었습니다. 실제 Actions 이력을 읽은 결과가 아니라 **동일 명령의 로컬 원인 재현**입니다.

같은 workflow의 `display-cache` job은 예약에 따라 실제 종가 표시 cache를 갱신하고 main에 push한 뒤 Pages build를 요청합니다. workflow 전체를 꺼서는 안 됩니다. 수정 시에는 현재 UI의 읽기 전용 검사와 구형 디자인 브랜치 전용 installer를 분리하고, 예약 job은 보존해야 합니다. 이 PR의 workflow diff에서 이 경계를 검토합니다.

### PR 범위와 중복

개선 전 `test-stock-radar-integration.yml`의 PR `paths`는 push 목록보다 좁아 홈페이지와 forecast·recommendation 자산 변경이 해당 PR 검사를 빠뜨릴 수 있었습니다. `node --check assets/stock-radar-flow-v2.js`도 연속 두 번 실행했습니다. 경로 검사는 신규 변경 기반 진입점에서 보완하며, 기존 push와 PR 목록을 맞춥니다. 독립 모델 감사와 UI 브라우저 검사가 같은 파일을 읽는 것은 목적이 달라 삭제 대상 중복으로 간주하지 않습니다.

기존 Actions에서 이름이 연결되지 않은 핵심 검사에는 냉장고 domain/store/kitchen-state/UI, 경매 계산·브라우저, `test_widget_data_repairs.py`, `test_market_repairs.py`가 있었습니다. 변경 기반 검사에서는 해당 기능의 수정을 감지하면 관련 테스트를 실행해야 합니다. 테스트 수가 0이면 성공으로 간주하지 않습니다.

### 직접 확인한 기존 테스트 결과

| 검사 | 이번 감사 실행 결과 | 판단 |
|---|---|---|
| Workflow inventory 단위 검사 | 8개 통과 | YAML `on` 보존, discovery·복수 모듈, 누락 파일·중복 이름·게시 단계 검증 |
| `test_market_repairs.py` | 7개 통과 | HTTP 429 시 마지막 관측값 보존·공식 표 파서 등을 오프라인 확인 |
| `tests/fridge-ui.test.cjs` | **30개 통과 / 5개 실패** | 아래 기존 코드·테스트 불일치, 전체 성공으로 보고하지 않음 |
| `test_widget_data_repairs.py` | 최초 `requests` 누락 후 개발 가상환경에서 **7개 통과** | 실제 임시 Git remote의 6회 경합, 오래된 snapshot 보존, 공식 자료 오류 시 기존 값 보존 확인 |

냉장고 실패 5개는 `굴소스`가 이미 기본 재료인데 `customSeason`에도 들어가야 한다는 기대 1개, 현 화면에 없는 `.kitchen-zone-controls` 및 `layer-front` 버튼을 찾는 기대 4개입니다. 새 환경을 만들었다는 이유로 기존 UI를 임의 재설계하거나 이 테스트를 skip·무력화하지 않습니다. 이번 PR에서는 현재 UI 요구사항과 대조한 뒤 오래된 기대를 좁게 수정하고, 누락된 레이어 이동 컨트롤을 복원하는 별도 변경을 진행합니다. 초기 실패와 수정 후 재검증 결과는 구분해야 하며, 해당 기능의 검사 경로에서 남은 실패가 있으면 그대로 실패로 보고해야 합니다.

### 관찰은 했지만 이번에 자동 변경하지 않은 위험

- 여러 `workflow_run` 후속 job은 상위 실행이 `completed`이면 성공·실패를 구분하지 않고 실행할 수 있습니다: `verify-stock-official`, `update-stock-opportunities`, `update-stock-decisions`, `stock-investment-cases`, `stock-reading-depth`, `test-stock-decisions-ui`. 실패 후 수집·재계산이 의도된 복구인지 먼저 확인해야 하므로 무조건 success guard를 추가하지 않습니다.
- radar→official→opportunities→cases→reading→recommendations→entry처럼 긴 `workflow_run` 사슬은 GitHub의 연쇄 단계 제한을 검토해야 합니다. 중간 예약 실행이 독립 진입점이므로 schedule·workflow_run을 단순 중복으로 지우면 갱신 빈도가 달라집니다. [GitHub workflow_run 계약](https://docs.github.com/actions/using-workflows/events-that-trigger-workflows#workflow_run)
- `continue-on-error`는 mortgage·real-estate 수집 단계 2개에서 발견되었습니다. 두 workflow 모두 마지막 health 상태를 게시한 뒤 `steps.*.outcome == 'failure'`이면 `exit 1`로 실패를 보고합니다. 이를 오류 은폐로 단정하거나 health 게시를 제거하면 안 됩니다.
- `verify-investment-embeds.yml`의 9개 고정 SHA-256은 현재 소스와 일치했습니다. 그러나 기존 파일을 정상 수정하면 승인된 digest를 업데이트해야 합니다. 이는 공개 배포 후 점검이며 새 소스가 배포되기 전의 차단 장치가 아닙니다.
- 일부 수집 job은 timeout을 명시하지 않고 일부 도구 설치는 버전이 고정되지 않았습니다. 우선 신규 개발 검사 의존성을 고정하며, 운영 수집기의 도구·timeout 변경은 실제 API 지연·출력 호환성을 따로 검증한 뒤 적용합니다.

## 기존 workflow 전체 목록

Cron은 GitHub Actions의 **UTC** 표현입니다. 표의 파일 게시는 소스 명령 기준이며 실제 서버 권한·성공 이력을 뜻하지 않습니다. `stock-autopilot-recovery`는 파일 게시 대신 `actions: write`로 허용된 인프라 실패를 한 번 재실행합니다.

| Workflow | 이벤트 | UTC cron | 저장소 파일 게시 경로 |
|---|---|---|---|
| [audit-stock-radar-accuracy.yml](../.github/workflows/audit-stock-radar-accuracy.yml) | workflow_dispatch, push, schedule | `15 0 * * 1-5, 30 8 * * 1-5` | git push |
| [monitor-stock-value-radar.yml](../.github/workflows/monitor-stock-value-radar.yml) | workflow_dispatch, schedule, push | `23 0,4,8,12,16,20 * * *` | git push |
| [probe-decision-sources.yml](../.github/workflows/probe-decision-sources.yml) | workflow_dispatch, push | `—` | 읽기 전용 |
| [stock-autopilot-recovery.yml](../.github/workflows/stock-autopilot-recovery.yml) | workflow_run | `—` | 읽기 전용 |
| [stock-entry-plan.yml](../.github/workflows/stock-entry-plan.yml) | workflow_dispatch, push, workflow_run, schedule | `37 8,23 * * *` | git push + Pages build |
| [stock-forecast-independent-audit.yml](../.github/workflows/stock-forecast-independent-audit.yml) | workflow_dispatch, pull_request, workflow_run, push, schedule | `33 * * * *` | 읽기 전용 |
| [stock-forecasts.yml](../.github/workflows/stock-forecasts.yml) | workflow_dispatch, push, schedule, workflow_run | `7,17,27,37,47,57 0-7,13-22 * * 1-5, 47 23 * * 0-4` | publish_stock_forecasts.py + Pages build |
| [stock-investment-cases.yml](../.github/workflows/stock-investment-cases.yml) | workflow_dispatch, workflow_run, schedule, push | `17 8,23 * * *` | publish_stock_investment_cases.py, publish_widget_data.py |
| [stock-reading-depth.yml](../.github/workflows/stock-reading-depth.yml) | workflow_dispatch, workflow_run, push | `—` | publish_widget_data.py |
| [stock-recommendations.yml](../.github/workflows/stock-recommendations.yml) | workflow_dispatch, workflow_run, push | `—` | publish_widget_data.py |
| [stock-strict-green.yml](../.github/workflows/stock-strict-green.yml) | workflow_dispatch, workflow_run, push | `—` | publish_stock_investment_cases.py, publish_widget_data.py |
| [test-stock-decisions-ui.yml](../.github/workflows/test-stock-decisions-ui.yml) | workflow_dispatch, push, workflow_run | `—` | 읽기 전용 |
| [test-stock-neutral-ui.yml](../.github/workflows/test-stock-neutral-ui.yml) | workflow_dispatch, push, schedule | `41 */2 * * 1-5` | git push + Pages build |
| [test-stock-radar-canonical.yml](../.github/workflows/test-stock-radar-canonical.yml) | pull_request, push, workflow_dispatch | `—` | 읽기 전용 |
| [test-stock-radar-integration.yml](../.github/workflows/test-stock-radar-integration.yml) | workflow_dispatch, pull_request, push | `—` | 읽기 전용 |
| [test-stock-radar-ui-preview.yml](../.github/workflows/test-stock-radar-ui-preview.yml) | workflow_dispatch, push | `—` | 디자인 브랜치만 git push |
| [test-toss-live.yml](../.github/workflows/test-toss-live.yml) | workflow_dispatch, push | `—` | 읽기 전용 |
| [update-bond-yields.yml](../.github/workflows/update-bond-yields.yml) | workflow_dispatch, schedule, push | `13,43 * * * *` | publish_widget_data.py |
| [update-commodities.yml](../.github/workflows/update-commodities.yml) | workflow_dispatch, schedule, push | `17 * * * *` | publish_widget_data.py |
| [update-cryptocurrency.yml](../.github/workflows/update-cryptocurrency.yml) | workflow_dispatch, schedule, push | `11,41 * * * *` | publish_widget_data.py |
| [update-exchange-rates.yml](../.github/workflows/update-exchange-rates.yml) | workflow_dispatch, schedule, push | `37 14,15,16 * * 1-5` | publish_widget_data.py |
| [update-fear-greed.yml](../.github/workflows/update-fear-greed.yml) | workflow_dispatch, schedule, push | `17 * * * *` | publish_widget_data.py |
| [update-korea-fear-greed.yml](../.github/workflows/update-korea-fear-greed.yml) | workflow_dispatch, push, schedule | `55 6 * * 1-5, 25 9 * * 1-5` | git push |
| [update-market-events.yml](../.github/workflows/update-market-events.yml) | workflow_dispatch, pull_request, push, schedule | `17,47 * * * *` | publish_widget_data.py |
| [update-mortgage-rates.yml](../.github/workflows/update-mortgage-rates.yml) | workflow_dispatch, schedule, push | `30 7 * * *` | publish_widget_data.py |
| [update-news-link-hub.yml](../.github/workflows/update-news-link-hub.yml) | workflow_dispatch, push, schedule | `7,22,37,52 * * * *` | publish_widget_data.py |
| [update-real-estate-pulse.yml](../.github/workflows/update-real-estate-pulse.yml) | workflow_dispatch, schedule, push | `20 7 * * *` | publish_widget_data.py |
| [update-stock-decisions.yml](../.github/workflows/update-stock-decisions.yml) | workflow_dispatch, schedule, workflow_run, push | `47 7,22 * * *` | git push |
| [update-stock-market-groups.yml](../.github/workflows/update-stock-market-groups.yml) | workflow_dispatch, schedule, workflow_run, push | `19 8,23 * * *` | publish_stock_market_groups.py |
| [update-stock-opportunities.yml](../.github/workflows/update-stock-opportunities.yml) | workflow_dispatch, schedule, workflow_run, push | `57 7,22 * * *` | publish_stock_opportunities.py |
| [update-stock-value-radar.yml](../.github/workflows/update-stock-value-radar.yml) | workflow_dispatch, schedule, push | `15 3,13 * * *` | git push |
| [update-stocks-dashboard.yml](../.github/workflows/update-stocks-dashboard.yml) | workflow_dispatch, schedule, push | `7,37 * * * *` | publish_widget_data.py |
| [update-supply-chain.yml](../.github/workflows/update-supply-chain.yml) | workflow_dispatch, schedule, push | `17 2 * * *` | publish_widget_data.py |
| [validate-real-estate-pulse.yml](../.github/workflows/validate-real-estate-pulse.yml) | pull_request | `—` | 읽기 전용 |
| [verify-investment-embeds.yml](../.github/workflows/verify-investment-embeds.yml) | workflow_dispatch, push | `—` | 읽기 전용 |
| [verify-stock-detail-v6.yml](../.github/workflows/verify-stock-detail-v6.yml) | workflow_dispatch, push | `—` | 읽기 전용 |
| [verify-stock-official.yml](../.github/workflows/verify-stock-official.yml) | workflow_dispatch, schedule, workflow_run, push | `47 3,13 * * *` | publish_widget_data.py |
| [verify-stock-value-radar.yml](../.github/workflows/verify-stock-value-radar.yml) | workflow_dispatch, push | `—` | 읽기 전용 |

## 승인 전에 충족할 배포 보호 조건

1. 현재 Pages의 실제 배포 원본·이벤트·토큰과 main 작성 주체를 조회합니다. 조회가 막혀 있으면 원인을 해소하고 미확인 상태를 유지합니다.
2. 코드 PR에는 변경 기반 검사와 투자 레이더 브라우저 검사를 적용합니다. 실패·스킵·0개 실행·미검증·기존 실패를 구분합니다.
3. 새 배포 경로는 정확히 검사한 commit/artifact를 대상으로 하며 사용자 승인 환경과 결합합니다. 현행 봇 JSON 게시가 코드 검사나 승인 절차를 우회해 임의 코드를 배포하지 않도록 별도 설계합니다.
4. 활성화 전 publisher별 허용 파일·대기열·Pages 빌드·데이터 동시 갱신을 검증합니다. 롤백은 UI 소스/artifact를 대상으로 하고 사용자 기록과 금융 JSONL 원장을 과거 상태로 reset하지 않습니다.
5. 승인 환경·ruleset·Pages source를 실제로 설정하기 전까지는 **“새 코드의 PR 검사는 구현됨”**과 **“실사용 배포 우회까지 차단됨”**을 구분해 보고합니다. 이번 작업에서는 자동 병합·운영 배포·main 보호 변경을 하지 않습니다.

## 이 작업 브랜치에서 적용한 개선과 재검증

- 신규 읽기 전용 개발 CI와 수동 검토 후보 CI를 추가해 전체 workflow는 40개입니다. 두 CI 모두 운영 배포·main push·예약 수집 권한이 없습니다.
- actionlint 1.7.7 공식 릴리스의 SHA-256을 확인한 뒤 **40개 workflow 의미 검사 통과**를 확인했습니다. ShellCheck는 별도 미실행입니다. 저장한 설치 스크립트는 TLS·공식 체크섬 검증을 유지합니다.
- 기존 예약 workflow 24개의 schedule·permissions·concurrency·예약 job body를 `tests/fixtures/scheduled-finance-jobs.json`의 기준 해시로 보호합니다. neutral의 비예약 verify만 별도이며, 예약 display-cache는 그대로입니다.
- neutral 설치기는 과거 디자인 브랜치에만 실행하고 현재 홈페이지는 읽기 전용 실제 검사로 확인하게 분리했습니다. integration의 PR 경로 누락과 중복 구문 검사 1회를 수정했습니다.
- 변경 검사기는 임시 소스 복사본에서 실행해 예전 결과 파일 생성기가 실제 금융 JSON을 덮지 못하도록 합니다. 알려지지 않은 UI·필수 브라우저 미실행·검사 중 소스 변경은 미검증으로 실패 종료합니다.
- 실제로 상세 버튼을 가리는 레이더 grid 높이 문제는 CSS 4줄로 수정했습니다. 화면 밖으로 하단 안내를 밀어내지 않고 두 조작 영역이 1366×768에 모두 보이며 내부 높이도 넘치지 않습니다.
- 기존 flow 검사는 오래된 선택자·2개 스크립트 가정·고정 날짜·정확히 1개 검색 결과 가정을 현 명세에 맞게 고쳤고 **72개 검사 통과**했습니다. canonical은 **2개 화면 통과**, 새 레이더 검사는 **5개 시나리오·64개 단언 통과**입니다.
- 냉장고 초기 실패 5개 중 오래된 테스트 3개를 수정하고 실제 누락된 앞/뒤 순서 버튼 2개를 기존 정리 배너에 복원했습니다. DOM은 **35개 모두 통과**, 실제 데스크톱·모바일·iframe은 **3개 모두 통과**했습니다. 저장 스키마·ID·수량·좌표·기존 재고 바이트를 보존합니다.
- 금융 판단·예측·시장 문맥 등 관련 기존 단위 검사 **115개**, 데이터 게시 경합·오류 보존 검사 **14개**가 통과했습니다. 운영 수집·게시 명령은 실행하지 않았습니다.

전후 캡처는 [실제 브라우저 증거](development-evidence/README.md)를 확인합니다. 첫 통합 실행에서는 모든 명령이 통과했어도 검증 도중 소스가 바뀌어 전체 결과를 `incomplete`로 남겼습니다. 완료 커밋에 대한 최종 통합 결과·후보 파일은 PR 본문과 현재 실행의 보고서를 기준으로 확인하며, 오래된 성공 JSON을 재사용하지 않습니다.

기존 `codex/dev-safety-pr-workflow-20261105` 브랜치는 6개 파일의 사전 점검·브라우저·규칙 작업이며 main에 반영되지 않은 별도 작업입니다. 읽기 전용으로 비교했고 삭제·덮어쓰기·무단 병합하지 않았습니다. 이번 브랜치는 CI·잠금 의존성·기존 금융 job 보호·실제 버그 재현과 수정까지 추가하므로, 두 브랜치를 함께 병합하려면 AGENTS·개발 문서·검사 진입점을 하나로 정리해야 합니다.

독립 검토에서 발견된 검사 선택 누락(stock build/update 및 단독 entry UI 테스트)과 후보 생성 중 파일 재읽기 경합도 수정했습니다. 소스에 대응하는 기존 unittest를 자동 연결하며 미지원 실행 코드는 `incomplete`로 남습니다. 게시 후보는 검증한 커밋의 불변 Git 객체에서 읽은 같은 바이트로 manifest·tar를 만들고, 생성 완료 전 다시 검증한 뒤 원자적으로 확정합니다. 관련 보호 회귀 검사 29개가 통과했습니다.
