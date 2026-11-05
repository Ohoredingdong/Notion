# 개발 환경 감사 및 개선

기준은 최신 main을 실제 fetch한 `17d11d28fdf156f7a6f9ee7eeefe689e761cd83c`(2026-11-05)이다. 이전 냉장고 기능 브랜치에는 main에 없는 문서·테스트가 많아 이를 운영 기준으로 복사하지 않았다. 기존 체크아웃에서 `chore/codex-development-system-20261105`를 만들었고 운영 main·Pages·원격 보호 설정은 바꾸지 않았다.

후속 읽기 fetch에서 main `03431e1aa8e5beee730b9ae534f029c7c4d1cbf2`는 암호화폐·프리미엄 JSON만 추가 갱신했다. 이 운영 갱신을 되돌리거나 개발 브랜치의 자료로 덮어쓰지 않는다. 승인된 병합/배포 시에는 최종 대상 SHA에서 다시 검사해야 한다.

## 기존 구조

- 루트 package/잠금·AGENTS·공통 스킬이 main에는 없었다. 현재 화면은 `stock-value-radar.html`의 flow-v3/V5 구성과 실제 로드하는 bridge/flow/forecast 모듈이 기준이다. 오래된 v9/advanced와 동일 화면이라고 가정하지 않는다.
- 원래 워크플로38개 중 생산 자료 writer26개, preview branch writer1개, 제한된 복구 writer1개, 읽기 전용10개였다. PR 트리거5개·일정24개·명시적 Pages build 요청3개가 있다. [고정 소스 전수 목록](development-evidence-20261105/workflow-inventory.json)과 [연결 DAG](development-evidence-20261105/workflow-handoffs.json)를 남겼다.
- 일반 자료 게시기는 최신 main에서 명시한 JSON만 게시하고 최신 관측/병렬 충돌을 보호한다. forecast 게시기는 검증 상태·학습 CAS·불변 원장을 보호하며3개 HTML의 forecast script tag도 관리한다. 모든 writer가 JSON만 쓴다고 보고하지 않는다.
- 기존 UI 설치/게시 보호 `test_stock_radar_publish_protection.py`를 재사용한다. 금융 수집·공식 조회·예측·게시 스크립트는 이 작업에서 실제 실행하지 않았다. 테스트의 synthetic reader/model/임시 Git은 운영 갱신과 다르다.
- 저장소 소스에는 전체 Pages 배포 workflow가 없고 기존3개 작업이 Pages build API를 호출한다. 실제 Pages source/branch protection/environment 설정은 GitHub API403으로 미확인이다. 소스만 보고 현재 배포 모드를 확정하지 않는다.

## 중복·실패·누락과 조치

| 발견 | 원인/근거 | 이번 조치 |
| --- | --- | --- |
| PR 검사 경로 누락 | canonical/integration PR paths가 일부 자산·generators/publishers·주 HTML을 빠뜨림 | paths 필터 없는 단일 `Development checks` 추가, 변경 파일이 스위트를 선택 |
| 현재 홈과 오래된 neutral 설치 충돌 | neutral verify가 main의 custom 홈에 옛 installer를 실행한 뒤 원문 불변을 요구 | design branch만 옛 설치, main은 실제 canonical 검사. 예약 display-cache writer는 원문 보존 |
| 중복 명령·역할 겹침 | integration에 같은 node syntax 명령2회, canonical/integration/preview의 검사 일부 겹침 | 같은 node 명령1회만 제거. 정상 후속/역사 검사를 임의 삭제하지 않음. 새 공통 gate를 기준으로 승인 후 통합 가능 |
| 안전하지 않은 Python discovery | 브라우저 프로그램7개가 import 시 실행하거나 추적 위치에 캡처 | TestCase 클래스만 정적으로 분류·모듈 실행, 기존 독립 브라우저는 명시적 CLI로 구분 |
| 고정 포트·라이브 요청·출력 혼재 | 과거 브라우저들이 외부 최신 자료/localhost 고정 포트/루트 PNG에 의존 | canonical CLI에 동적 서버·실제 체크인 JSON·외부 차단·외부 출력·해시 guard 적용 |
| 경량 Python4건 실패 | 로컬 pandas3/calendar4.11과 운영 CI pandas<3/calendar4.13 불일치 | 개발 잠금을 CI 계열로 정합. 관련51건 재실행 통과. 수집 workflow의 설치는 교체하지 않음 |
| 기존 Node5건 실패 | 기본 굴소스를 custom으로 기대, 옛 이동 선택자, 실제 층 순서 UI 진입점 누락 | fixture/실제 선반 조작 정정, 선택 중44px 앞/뒤 버튼 복구. 전체150/150 및 기존 UI39/39 통과 |
| 저장 기한 자동 변경 P0 | 이름·수량6종으로 예시를 추정해 만료 기한/리비전을 재작성 | 자동 재작성 차단. 기존 key/schema/marker를 지우지 않고 일반 boot/날짜 변경/reload 원문 보존 |
| 잘못된 실행 출처 | queued stale 방지로 최신 branch checkout인데 source_commit은 이벤트 GITHUB_SHA | event_commit과 실제 checkout HEAD를 분리, CI 해석 실패는 수집/모델/쓰기 전 중단. 과거 기록은 그대로 |
| 320px 가격·차트 겹침 | 68×33 absolute 차트가 가격 텍스트를 침범 | 375px 이하만 grid 전용 행. 숫자/폰트/차트 유지,390/desktop 이미지 동일 |
| 영어 추가 자료 JSON 오류 | 마지막 배열 닫는 괄호 누락 | 괄호1개 복구,20단어와 값 원문 보존. 전체 실제 JSON 구문 검사에 포함 |
| 다른 SHA·누락·실패를 후보로 만들 위험 | 배포 전 일반적인 정확한 전체 검사 영수증 없음 | 정확한 SHA/계획/실행/clean/해시/의존성·ZIP 변조를 재검증하는 read-only 후보 생성 |

전체 Python 초기 통합은582건 중1건의 출처 검사 실패를 실제로 드러냈다. 단언을 지우지 않고 이벤트/실제 코드의 의미를 분리했으며 [출처 수정](development-evidence-20261105/execution-identity-summary.json)의 독립25건·패키지 없는25건·관련144건을 재검증했다. 기존 값·모델·원장16파일 보존도 [별도 해시](development-evidence-20261105/execution-identity-preservation.json)로 확인했다. 이후 최종 전체 결과는 실행 SHA와 함께 `dev_check` 영수증/Actions artifact에서 확인한다.

새 CI 자체도 Actionlint가 job-level env의 잘못된 runner 문맥을 검출했고 제거 후 기존 포함40개 workflow의 표현식 검사를 통과했다. YAML/Bash와 원격 실제 실행은 구분한다. 실패한 중간 로그는 외부 증거에 보존하고 성공 결과로 바꾸지 않았다.

기존 integrated browser 실패도 실제로 재현했다. Node 진입 화면의 원래 제목 단언은 현재 소스와 맞아 완화하지 않았고, 같은 체크인 JSON으로 응답하도록 정리했다. Flow의 오래된2개 script 가정은 실제6개 bridge/flow/forecast 역할을 정확히 확인하도록 정정하고 시나리오·조건·모의 저장 단언을 유지했다. Advanced의 옛 neutral-home 선택자만 실제 RF 홈의 같은 시장/알림/목록/이동 동작으로 교정했다. [현재 흐름75건](development-evidence-20261105/radar-flow-regression.json), [진입2환경](development-evidence-20261105/radar-entry-regression.json), [심층 분석81건](development-evidence-20261105/radar-advanced-regression.json)을 실행했다. 공개 HTML 관측403은 별도 미확인으로 남겼다.

Canonical/integration의 job 이름과 트리거는 원격 required-status 확인 전 보존한다. 고정 포트 서버 중복을 없애고 직접 CLI·외부 산출물·항상 캡처 업로드로 정합했다. 새 공통 gate와 검사의 일부 겹침은 이 호환 기간에 남으며, 정책을 확인하지 않고 이전 필수 status를 없애 PR을 막지 않는다.

## 데이터와 화면 보존

[기존 자료 보존](development-evidence-20261105/existing-data-preservation.json)에서 영어 구문 복구를 제외한 기존 JSON/JSONL은 기준 소스와 같다. 과거 기한이나 과거 source_commit을 추측해 재작성하지 않았다. 기존 writer27개의 trigger/권한/동시성/본문은 [계약](../config/automation-contract.json)으로 보호하며, neutral은 예약 writer 원문을 유지한 read-only verify 변경만 예외다. 이 계약은 원격 브랜치 정책 설정이 아니다.

[레이더 전후 수치](development-evidence-20261105/radar-card-comparison.json)와 [원본 결함 재현](development-evidence-20261105/radar-before-negative.json)을 구분한다. 원본320 일반/iframe의 겹침은 실제 실패로 남았다. 다른5환경은 이 결함이 없었다. 좁은 화면 수정은 실제 값·18px 글자·68×33 차트를 그대로 두고 겹침만 없앤다.

[레이더320 수정 전](development-evidence-20261105/radar-320-before.png) · [수정 후](development-evidence-20261105/radar-320-after.png)

[냉장고 수정 요약](development-evidence-20261105/fridge-regression-summary.json)과 [전후 위치/원문 검사](development-evidence-20261105/fridge-layout-comparison.json)에는320/390/1366 일반 화면0픽셀 차이, 선택 중 버튼의 실제 조작과 재로드·원문 보존 범위를 기록했다.

[선택 중 수정 전](development-evidence-20261105/fridge-selected-390-before.png) · [수정 후](development-evidence-20261105/fridge-selected-390-after.png)

## 자동화·배포 보호의 실제 범위

새 PR CI와 수동 후보 workflow는 `contents:read`만 쓰고 체크아웃 자격 증명을 남기지 않는다. 실패·skip·0tests·누락된 브라우저 결과·실행 중 자료 변경·미분류 코드는 실패다. main 자료 전용 push 이벤트에서는 설치 없는 가벼운 무결성 검사만 한다. GITHUB_TOKEN의 후속 push 이벤트 억제 때문에 **모든 봇 자료 push를 새 CI가 검사한다고 주장하지 않는다**. 기존 수집 자체 검증과 workflow_run 감사가 계속 담당한다.

후보 workflow는 배포 권한이 없어 실제 사이트를 변경할 수 없다. [후보 가드 회귀](development-evidence-20261105/release-guard-summary.json)는 실패/오래된 영수증/다른 SHA/누락 자산/경로 탈출/변조 등을 검증한다. [PR 가드](development-evidence-20261105/pr-guard-summary.json)는 정확한 remote head와 same-repository PR만 다루고 원격 미확인을 성공으로 보지 않는다. **이 변경은 기존 Pages의 배포 차단을 활성화한 것이 아니다.** 사용자 승인 후 실제 설정·금융 자료 경로 호환을 확인해 활성화해야 한다. 세부 순서는 [개발 절차](DEVELOPMENT.md)에 있다.

## 브랜치와 재사용

운영 main 외에 kitchen feature/design, 연구·검증·evidence 브랜치가 다수 있었다. 별도 읽기 fetch로 같은 목적의 미병합 `codex/dev-safety-pr-workflow-20261105`(f8667e4d)와 `codex/development-safety-system`(0e46462d)도 확인했다. 둘 다 main의 현재 운영 설정으로 가정하지 않는다. 다른 브랜치·PR을 덮어쓰거나 삭제·병합하지 않았다.

두 브랜치는 서로 다른 preflight/check_changed·스킬·CI 이름을 사용하고 AGENTS/prepare_release 등과 충돌할 수 있다. 이 작업과 함께 무작정 모두 병합하면 중복 gate가 생긴다. 공통 규칙·CI 한 세트를 검토해 통합해야 한다. 공식 checksum을 검증하는 Actionlint 설치 helper는 기존 `codex/development-safety-system`의 고정 소스에서 재사용했다. 그 브랜치의 런타임 결과를 이 작업의 통과로 보고하지 않는다.

## 남은 검증과 접근 제한

- API403 때문에 원격 Pages/branch/environment settings·전체 Actions 로그·PR 생성 권한을 확인하지 못했다. native Git read/push와 공개 GitHub Actions HTML 조회는 별도 능력이다. 공개 HTML의 최근 run 목록은 전체 API 감사/설정 조회가 아니다.
- 현재 환경 설정 초안에 api.github.com과 운영 사이트 읽기 호스트를 추가했으나, 저장만으로 현재 런타임에 적용됐다고 하지 않는다. 비밀값을 요청하거나 다른 서비스로 차단 API를 우회하지 않는다.
- canonical 레이더의 로컬 Chromium7환경과 기존 저장 fixture 검사는 실제 Notion/Safari/휴대폰이나 외부 제공처 정확성·실시간 거래·수익성의 검증이 아니다. opaque 상태는 저장 불가 negative control이다.
- `--all`은 설정된12개 검사다. 역사 forecast/preview browser의 모든 동작·다른38위젯 전체 실브라우저·실제 Supabase 개인 쓰기·Toss 계좌·음성 재생은 전부 검증됐다고 하지 않는다. 기존 단위·현재 canonical·명시적 오류 회귀를 우선한다.
- 기존 Pages 자동 경로, publisher 재생성 후 최종 바이트의 일반적인 CI artifact provenance, 외부 CDN·동적 JS 전체 의존성은 승인 후 운영 전환 단계에서 추가 검증할 범위다. 현재 금융 schedules/권한/원장/CAS·기존 데이터 갱신은 유지한다.

## 기준 소스의 전체 Actions 목록

아래는17d11d28의38개이며, 새로운2개는 개발 검증·후보 준비 전용이다. 표는 소스 조사이며 원격 활성/성공 상태를 뜻하지 않는다.

| 워크플로 | 역할 | 트리거 | workflow_run 입력 |
| --- | --- | --- | --- |
| [audit-stock-radar-accuracy.yml](../.github/workflows/audit-stock-radar-accuracy.yml) | production-writer | workflow_dispatch, push, schedule | — |
| [monitor-stock-value-radar.yml](../.github/workflows/monitor-stock-value-radar.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [probe-decision-sources.yml](../.github/workflows/probe-decision-sources.yml) | read-only | workflow_dispatch, push | — |
| [stock-autopilot-recovery.yml](../.github/workflows/stock-autopilot-recovery.yml) | recovery-actions-writer | workflow_run | Stock Prospective Forecasts |
| [stock-entry-plan.yml](../.github/workflows/stock-entry-plan.yml) | production-writer | workflow_dispatch, push, workflow_run, schedule | Strict Green Review → Stock Three-Year Reading → Stock Recommendations |
| [stock-forecast-independent-audit.yml](../.github/workflows/stock-forecast-independent-audit.yml) | read-only | workflow_dispatch, pull_request, workflow_run, push, schedule | Stock Prospective Forecasts |
| [stock-forecasts.yml](../.github/workflows/stock-forecasts.yml) | production-writer | workflow_dispatch, push, schedule, workflow_run | Update News Link Hub |
| [stock-investment-cases.yml](../.github/workflows/stock-investment-cases.yml) | production-writer | workflow_dispatch, workflow_run, schedule, push | Update Stock Opportunities |
| [stock-reading-depth.yml](../.github/workflows/stock-reading-depth.yml) | production-writer | workflow_dispatch, workflow_run, push | Stock Investment Cases |
| [stock-recommendations.yml](../.github/workflows/stock-recommendations.yml) | production-writer | workflow_dispatch, workflow_run, push | Stock Three-Year Reading |
| [stock-strict-green.yml](../.github/workflows/stock-strict-green.yml) | production-writer | workflow_dispatch, workflow_run, push | Stock Investment Cases → Stock Three-Year Reading |
| [test-stock-decisions-ui.yml](../.github/workflows/test-stock-decisions-ui.yml) | read-only | workflow_dispatch, push, workflow_run | Update Stock Decisions |
| [test-stock-neutral-ui.yml](../.github/workflows/test-stock-neutral-ui.yml) | production-writer | workflow_dispatch, push, schedule | — |
| [test-stock-radar-canonical.yml](../.github/workflows/test-stock-radar-canonical.yml) | read-only | pull_request, push, workflow_dispatch | — |
| [test-stock-radar-integration.yml](../.github/workflows/test-stock-radar-integration.yml) | read-only | workflow_dispatch, pull_request, push | — |
| [test-stock-radar-ui-preview.yml](../.github/workflows/test-stock-radar-ui-preview.yml) | preview-branch-writer | workflow_dispatch, push | — |
| [test-toss-live.yml](../.github/workflows/test-toss-live.yml) | read-only | workflow_dispatch, push | — |
| [update-bond-yields.yml](../.github/workflows/update-bond-yields.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [update-commodities.yml](../.github/workflows/update-commodities.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [update-cryptocurrency.yml](../.github/workflows/update-cryptocurrency.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [update-exchange-rates.yml](../.github/workflows/update-exchange-rates.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [update-fear-greed.yml](../.github/workflows/update-fear-greed.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [update-korea-fear-greed.yml](../.github/workflows/update-korea-fear-greed.yml) | production-writer | workflow_dispatch, push, schedule | — |
| [update-market-events.yml](../.github/workflows/update-market-events.yml) | production-writer | workflow_dispatch, pull_request, push, schedule | — |
| [update-mortgage-rates.yml](../.github/workflows/update-mortgage-rates.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [update-news-link-hub.yml](../.github/workflows/update-news-link-hub.yml) | production-writer | workflow_dispatch, push, schedule | — |
| [update-real-estate-pulse.yml](../.github/workflows/update-real-estate-pulse.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [update-stock-decisions.yml](../.github/workflows/update-stock-decisions.yml) | production-writer | workflow_dispatch, schedule, workflow_run, push | Verify Stock Official Filings |
| [update-stock-market-groups.yml](../.github/workflows/update-stock-market-groups.yml) | production-writer | workflow_dispatch, schedule, workflow_run, push | Update Stock Opportunities |
| [update-stock-opportunities.yml](../.github/workflows/update-stock-opportunities.yml) | production-writer | workflow_dispatch, schedule, workflow_run, push | Verify Stock Official Filings |
| [update-stock-value-radar.yml](../.github/workflows/update-stock-value-radar.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [update-stocks-dashboard.yml](../.github/workflows/update-stocks-dashboard.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [update-supply-chain.yml](../.github/workflows/update-supply-chain.yml) | production-writer | workflow_dispatch, schedule, push | — |
| [validate-real-estate-pulse.yml](../.github/workflows/validate-real-estate-pulse.yml) | read-only | pull_request | — |
| [verify-investment-embeds.yml](../.github/workflows/verify-investment-embeds.yml) | read-only | workflow_dispatch, push | — |
| [verify-stock-detail-v6.yml](../.github/workflows/verify-stock-detail-v6.yml) | read-only | workflow_dispatch, push | — |
| [verify-stock-official.yml](../.github/workflows/verify-stock-official.yml) | production-writer | workflow_dispatch, schedule, workflow_run, push | Update Stock Value Radar |
| [verify-stock-value-radar.yml](../.github/workflows/verify-stock-value-radar.yml) | read-only | workflow_dispatch, push | — |

## 설치 재현과 환경 설정

해시 잠금 설치를 반복하고, 유지된 dependency-only toolkit으로 별도 상태 디렉터리에서도 설치했다. [현재 환경 준비 확인](development-evidence-20261105/environment-readiness.json)은 패키지 import·Node DOM 의존성과4개 실제 HTTP 응답/체크아웃 바이트를 확인한다. 환경 설정의 install/start 초안을 저장했으나 현재 런타임의 네트워크 정책은 revision1/명시 추가 호스트 없음으로 재관측됐다. 초안 저장은 적용·환경 publication·다음 작업의 준비 검증과 다르다. 기존 main에 아직 개발 체계 코드가 없으면 fallback은 도구만 준비하고 저장소 파일을 삽입하거나 브랜치를 바꾸지 않는다.

공개 GitHub HTML의 최근 run 목록도 읽었다. [관측 기록](development-evidence-20261105/actions-public-observation.json)에는 main의 기존 neutral/integrated 실패와 다른 개발 브랜치의 run도 보인다. 이는 개별 HTML 아이콘/링크의 관측이며 로그 원인·관리자 설정·이 작업의 실제 CI 통과를 대신하지 않는다.

첨부한 개별 개발 단계 요약의 당시 소스 해시는 보존했다. 최종 필수 계획과 정확한 HEAD의 전체 영수증은 실제 최종 실행 결과를 사용하며, 이전 단계 요약을 최신 배포 증명으로 재사용하지 않는다.
