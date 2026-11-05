# 개발 체계 적용·검증 결과 — 2026-11-05

작업 브랜치: `codex/development-guardrails-20261105`. 기준 main: `17d11d28fdf156f7a6f9ee7eeefe689e761cd83c`. 운영 병합·배포와 원격 보호 설정 변경은 실행하지 않았습니다.

## 실제 변경

- `AGENTS.md`, 재사용 widget-development 스킬과 PR 템플릿에 승인된 디자인 우선, 절제된 iOS 기본 UI, 자료·기록 보존, 데스크톱/모바일/iframe, 전후 화면, 원인 재검증과 상태 구분을 명시했습니다.
- Python 3.12/Node 24, Python 전이 의존성 제약과 npm lockfile을 도입했습니다. 새 프런트엔드 빌드 단계는 없습니다. 설치 스크립트를 실제 실행하고 다시 실행하여 pip dependency check와 Chromium 준비를 확인했습니다.
- 변경 파일과 import/소비 관계에 연결된 검사를 고르는 `dev_check.py`를 구현했습니다. commit-diff는 정확한 head의 검사 설정을 쓰며, 테스트는 임시 사본에서 실행합니다. 실패·시간 초과·0개 검사·기능 검사 누락은 성공으로 바꾸지 않습니다.
- 읽기 전용 공통 CI, 기존 현재 레이더 검사 갱신, 5개 후속 writer와 관련 UI job의 선행 성공 조건을 추가했습니다. 기존 writer의 일정·권한·동시성·발행 명령은 정책 검사로 보존합니다.
- 선택한 모의매수 종목이 제출 후 다른 종목으로 돌아가던 실제 오류를 수정했습니다. AAPL을 한 번 선택해 두 번 매수하면 AAPL 수량 5, 평균 원가 112가 되고 기존 삼성 보유·전역 선택은 그대로임을 확인했습니다.
- 냉장고의 오래된 양념 fixture/선반 selector 세 건을 실제 UI에 맞췄습니다. 안내문과 핸들러는 있으나 접근할 수 없던 앞뒤 순서 버튼을 선택·정리 모드 안에만 복구했습니다. 기존 수량·기한·재고·동기화 원문은 보존합니다.
- 투자 연습 임베드 검사의 과거 고정 해시를 실제 checkout으로 바꿨습니다. PR/main은 후보 소스 검사를, 명시적 수동 `check_public=true`만 공개 파일·헤더·해시 검사를 수행합니다. 공개 사이트 검사를 실행했다고 보고하지 않습니다.
- 수동 검토용 release 경로를 구현했습니다. 기본 dry run/정책 비활성 상태이며 실제 Pages 설정과 exact SHA·검사·artifact를 확인하지 못하면 거부합니다. 현재 운영 Pages 경로의 강제 보호로 전환하지 않았습니다.

## 실행 증거

| 검사 | 실제 결과 | 증거 |
| --- | --- | --- |
| 변경 파일 묶음 격리 실행 | 최초 39개 작업 파일에 대해 50개 검사 통과, 실패/미실행/미지원 0 | `/tmp/notion-development-working/report.json` |
| 최종 커밋 전체 diff | 커밋에 포함된 새 임베드 검사까지 재실행하는 최종 기록은 아래 JSON이 기준 | `/tmp/notion-development-final/report.json` |
| canonical Chromium | 312개 검사 통과, 6개 화면 크기, 실패 0, PNG 25개 | `/tmp/notion-radar-current-20261105-verified/report.json` |
| 수정 전/후 원래 홈 비교 | desktop1440×900/mobile390×844/iframe320×640 PNG 바이트 동일 | `/tmp/notion-radar-portfolio-fix-design-comparison/comparison.json` |
| 실제 모의매수 오류 전 상태 | 삼성으로 선택이 복귀하는 동작 재현·기록 | `/tmp/notion-radar-portfolio-fix-before/reproduction.json` |
| 냉장고 단위·DOM | 130/130 통과, skip 0 | `/tmp/notion-fridge-layer-review/unit-tests.log` |
| 냉장고 실제 Chromium | 48/48 통과, 키보드/모바일 tap/iframe·원문 보존 | `/tmp/notion-fridge-layer-review/report.json` |
| 자동 검사 runner | 41개 자체 테스트 통과: 실제 실패 exit, 0개 검사, 격리, 정확한 commit 설정, 선택하지 않은 미추적 파일 제외 | 최종 관련 검사 로그 `validation-runner.log` |
| workflow 정책 | 305개 구조 조건 및 14개 회귀 테스트 통과 | `workflow-policy.log`, `workflow-policy-tests.log` |
| release gate | 23개 회귀 통과: stale SHA/실패·누락·변조된 증거/수정 artifact/정책 비활성/legacy Pages 거부 | `release-gate-tests.log` |
| 게시 보호 | 기존 legacy assertions + 실제 forecast HTML 삽입 블록 6개 격리 검사 통과 | `radar-publish-protection.log` |
| 기존 금융 회귀 | 시장 복구7, 금리·맥락8, 일정 outlook6, 동시 게시/공식표 보존7, 예측26, 학습35, 방향24 모두 통과 | 같은 이름의 최종 관련 검사 로그 |
| 현재 감사 보고 정합성 | `audit_stock_radar_accuracy.py --check` 통과, 독립 평가132건 | 금융 모델의 `performance_approved=false`, `live_trading_proven=false`는 그대로이며 성능 승인으로 해석하지 않음 |
| 투자 임베드 | 회귀11개·실제9개 파일과5개JS 문법 검사 통과 | 최종 `investment-embed-tests.log`, `investment-embed-source.log` |
| GitHub Actions 실제 실행 | 미확인 | API 도메인 차단으로 실행 이력 조회 불가 |
| 실제 Notion 계정/물리 휴대전화 | 미실행 | Chromium iframe/모바일 viewport와 구분 |
| 원격 금융 제공처·실제 데이터 최신성 | 미실행 | 저장 자료 소비·실패 처리만 확인; 운영 수집기 실행 안 함 |
| 실제 운영 배포·병합·자동 병합 | 미실행 | 사용자 승인 전 진행하지 않음 |

위 로그 이름은 최종 보고서 디렉터리 아래에 있습니다. 실행 계획을 성공 기록으로 사용하지 않습니다. 최종 커밋·설정 SHA와 실제 명령·exit code는 JSON 보고서에 기록합니다.

## 실패와 원인 확인

- 초기 체크아웃은 main보다121커밋 뒤여서 최신 원본을 다시 읽었습니다. 기존 README 변경은 정확한 stash와 외부 보관 파일로 보존한 뒤 충돌 없이 복원했습니다.
- 초기에 옛 Python 환경에서 PyYAML 미설치로 정책 검사가 실패했습니다. 새 고정 환경에서 재실행해 통과했습니다.
- 레이더 테스트에 남은 구형 문구·selector 기대값은 현행 UI 의미를 확인한 뒤 갱신했습니다. 실제 모의매수 오류는 재선택으로 검사를 우회하지 않고 앱을 고쳤습니다.
- 냉장고 검사5건 중3건은 오래된 fixture/selector,2건은 실제 조작 경로 누락이었습니다. 테스트를 삭제하거나 skip하지 않고 수정·재실행했습니다.
- 냉장고 후속 검사에서 문을 다시 열면 이전 재료가 자동 선택될 것으로 잘못 기대해1건 실패했습니다. 기존 의도된 선택 해제를 확인하고, 사용자가 명시적으로 재선택하는 흐름으로 재검증했습니다.
- 냉장고 외부 Google Fonts 요청은 변경 전부터 환경에서 실패했습니다. 전후 비교에는 동일 fallback을 명시적으로 적용했고 typography의 외부 가용성은 미검증으로 남겼습니다. 모바일 차이는 DOM bounds 이동 없이 외곽 anti-alias124픽셀(0.0107%, 채널 최대3/255)이었으며 원값과 기준을 보고서에 기록했습니다. desktop/iframe은 바이트 동일했습니다.

## 자료 보존과 남은 검사 범위

- 기존 미추적 작업16개와 README의 사용자 추가8줄을 보존했습니다. 이번 PR에는 포함하지 않습니다. 원본 보관: `/workspace/notion-work-preservation-20261105/`.
- 운영 JSON/JSONL 내용 변경 없음. 일정·writer 권한·동시성·발행 명령을 유지했습니다. 로컬 검사는 collector/publisher entrypoint를 실행하지 않습니다.
- [데이터 검사 연결 목록](development-coverage-baseline.json)은 **계획 inventory**입니다. 루트 JSON/JSONL95개 중20개가 실제 소비자/감사 검사에 연결되고75개가 미지원입니다. 이를 전체 데이터 검증 완료라고 보고하지 않습니다. 영·중·불 단어 목록, 원자재/환율/채권/암호화폐 등 여러 위젯의 자료 계약·동작 검사를 후속 보강해야 합니다. 미지원 파일 수정은 공통 CI에서 기능 검사를 추가하기 전까지 실패합니다.
- 새 위젯 전체 E2E나 모든 legacy 화면을 일괄 실행한 것은 아닙니다. 이전 flow/neutral/advanced 테스트 원본을 삭제하지 않았으며 현행 main 검사에서는 보존·확장한 canonical suite를 사용합니다.
- GitHub API 도메인 `api.github.com` 허용을 기존 `api.openai.com`과 함께 개발 환경 초안에 저장했습니다. 실행한 개발 설치 스크립트와 시작 지침도 초안에 저장했으나 **실행 환경 반영·게시를 완료했다고 주장하지 않습니다**.
- 원격 Pages/branch protection을 확인하고 기존 금융 writer와의 배포 전환을 승인하기 전에는 실제 강제 배포 보호를 완료했다고 보고할 수 없습니다. PR 생성과 원격 CI 확인도 API 접근 후 마무리해야 합니다.
