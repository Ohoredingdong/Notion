# 개발·검증·검토 절차

정적 HTML/CSS/JavaScript 위젯과 Python 금융 데이터 자동화가 함께 있는 저장소다. 운영 수집 작업과 개발 검사를 구분한다. 공통 규칙은 [AGENTS.md](../AGENTS.md), 조사 근거와 남은 범위는 [환경 감사](DEVELOPMENT_AUDIT_2026-11-05.md)에 있다.

## 설치와 시작

Python 3.12와 Node.js 20 이상을 사용한다. 개발 CI는 Node 24를 지정한다. 설치는 추적 파일과 운영 자료를 수정하지 않으며, 잠긴 Python 패키지의 해시와 npm lock을 검증한다.

```bash
bash scripts/setup_dev.sh --state /tmp/notion-dev --install-browser
source /tmp/notion-dev/activate.sh
```

이미 Chromium이 있는 환경에서는 다운로드 대신 다음 명령을 쓴다.

```bash
bash scripts/setup_dev.sh --state /tmp/notion-dev --browser-executable /usr/bin/chromium
source /tmp/notion-dev/activate.sh
```

`requirements-dev.in`이 직접 의존성, `requirements-dev.txt`가 Python 3.12/Linux 기준 해시 잠금 파일이다. `package-lock.json`은 개발용 Linkedom·Playwright 도구를 잠근다. 설치 위치·npm/pip 캐시·브라우저·Python bytecode는 지정한 외부 디렉터리에 둔다. Actionlint 1.7.7은 공식 릴리스와 체크섬으로 검증한다. 기존 수집 Actions의 의존성을 이 개발 잠금 파일로 일괄 교체하지 않는다.

필요할 때만 로컬 서버를 시작한다. 기존 서버를 무작정 종료하지 않는다.

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory .
```

HTTP 응답과 실제 파일 내용으로 준비 상태를 확인한다. 위젯 개발에는 DB·운영 API 키가 필수가 아니다. 로컬 주소는 내부 확인용이며 휴대폰 공개 미리보기로 전달하지 않는다. 서버 프로세스는 새 작업에서 다시 시작해야 한다.

## 변경 파일에 따른 검사

```bash
git fetch origin main
python scripts/dev_check.py --base origin/main --plan
python scripts/dev_check.py --base origin/main --output /tmp/notion-related-check
```

기준과 HEAD의 merge-base부터 비교하고, 미커밋·새 파일도 포함한다. rename은 이전/새 경로를 모두 검사하고 삭제도 원래 기능의 검사를 선택한다. `--plan`은 stdlib만으로 실행되며 검사를 실행한 것처럼 보고하지 않는다.

| 변경 | 자동 검사 |
| --- | --- |
| 공통 규칙·CI·개발 도구·잠금 파일 | 모든 설정된 검사, 워크플로 표현식, 단위/서비스/브라우저 |
| 투자 레이더 HTML·JS·모델·생성/게시 코드 | 관련 Python 단위, 실제 JS 판정 회귀, canonical·시나리오·진입·심층 분석 브라우저, 소스/자료 검사 |
| 시장 수집·공통 게시 코드 | 자료 보존·병렬 게시·시장 문맥 단위, 소스/자료 검사 |
| 냉장고 | 실제 DOM/도메인/저장 회귀, 소스/자료 검사. UI 변경의 실제 전후 촬영은 추가로 수행 |
| 경매 공부 | 기존 계산 모델 회귀, 소스/자료 검사. 기존 별도 브라우저 흐름은 별도 실행·보고 |
| Toss 읽기 전용 어댑터 | 기존 서비스 단위 검사, 소스/자료 검사. 실제 계좌 연결은 별도 범위 |
| JSON/JSONL 자료만 | JSON 구문·유한 숫자·기본 식별/가격 형식과 기존 자동화 계약. 새 시세 수집을 실행하지 않음 |
| 문서 | 자동화 계약과 소스/자료 무결성 |

미분류 제품 코드는 전체 검사로 확장하고 **관련 검증 범위가 없다는 실패**를 기록한다. 새 기능은 경로 분류와 실제 회귀 검사를 함께 추가한다. 임의로 분류를 문서/자료로 바꿔 검사를 우회하지 않는다.

```bash
python scripts/dev_check.py --suite radar --output /tmp/notion-radar-check
python scripts/dev_check.py --all --output /tmp/notion-full-check
```

`--all`은 **설정된 전체 검사**다. 저장소의 모든 역사 버전·모든 실기기·모든 외부 서비스를 검증했다는 뜻이 아니다. 현재 필수 범위는 `repository-policy`, `workflow-lint`, `python-unit`, `service-unit`, `node-unit`, `radar-js-unit`, `radar-browser`, `radar-flow-browser`, `radar-entry-browser`, `radar-advanced-browser`, `syntax`, `data-integrity`다. 계획은 소스에서 재계산한다.

기존 Python 단위 클래스를 AST로 찾은 뒤 unittest 모듈로 실행한다. 일부 `test_*.py`는 import만 해도 브라우저를 띄우므로 전체 `unittest discover -s scripts`를 무작정 실행하지 않는다. 직접 실행할 때 추적 JSON을 쓰는 테스트도 있다. 기존 bare-assert JS 판정 시험과 홈페이지 게시 보호도 재사용한다. 현재 시나리오/조건/모의 보유 흐름과 별도 advanced·진입 브라우저도 표준 CLI로 재사용한다. 이 legacy advanced의 공개 HTML 관측은 로컬 합격과 별도이며 접근 차단을 기록한다. 0개 테스트·필수 테스트 skip·실패·오래된 브라우저 결과를 성공으로 받지 않는다.

로그·`report.json`·실제 캡처는 외부 출력 폴더에 둔다. 보고서에는 입력 SHA, 계획, 개별 종료 코드·실제 테스트 수·시작/종료 시각, 추적 및 새 파일 해시, Git 상태를 남긴다. 실행 중 HEAD/소스/자료가 달라지면 실패다. 전송 실패나 미실행은 통과로 바꾸지 않는다.

## 투자 레이더 브라우저

```bash
python scripts/test_stock_radar_canonical_browser.py \
  --root "$PWD" --output /tmp/radar-browser \
  --browser-executable /usr/bin/chromium
```

기존 desktop1629/1366 검사를 보존하고, 모바일390/320, 실제 교차 출처 HTTP iframe390/320, opaque sandbox 저장 불가의 7개 환경을 확인한다. 실제 저장 JSON과 기업·가격을 사용하며 검색/시장 선택/기업 상세/복귀/재오픈·기존 저장 원문·명시적503 복구를 검사한다. 가격 텍스트와 차트 잉크의 겹침·차트 숨김도 검사한다.

외부·쓰기 요청은 차단하고 실제 체크인 자료를 결정적인 시각으로 재생한다. 장애 주입과 저장 fixture는 격리한 테스트 문맥이며 실제 새 시세가 아니다. opaque 환경은 테스트 서버의 CORS 응답을 사용해 저장 불가 상태를 분리한다. 실제 Notion CORS·Safari·휴대폰 확인이나 금융 자료의 공식성·최신성은 별도 범위다.

같은 자료·시각으로 이전 소스와 비교하려면 기존 체크아웃을 바꾸지 않고 외부 디렉터리에 `git archive`로 기준본을 풀고 `--baseline-root /외부/기준본`을 추가한다. 원본에서 재현된 결함은 `baseline_failed_cases`로 남기며 합격으로 바꾸지 않는다. 최종 합격은 수정본의 실제 결과로 판단한다.

## PR 생성

1. 별도 브랜치의 변경·데이터 보존·전후 화면을 검토한다. 의도한 파일만 커밋한다.
2. clean HEAD에서 `--all`을 실행한다. 이후 파일이나 HEAD가 바뀌면 해당 영수증은 더 이상 PR/후보 생성에 사용할 수 없다.
3. **작업 브랜치만** 명시해 push한다. main push·자동 병합은 하지 않는다.
4. 검토자가 읽을 문제/변경/검증/미검증 범위를 외부 Markdown 파일로 준비하고 다음 명령을 실행한다.

```bash
python scripts/open_development_pr.py \
  --report /tmp/notion-full-check/report.json \
  --title "변경의 구체적인 결과" \
  --body-file /tmp/notion-pr.md \
  --output /tmp/notion-pr-result.json
```

기본 저장소는 `Ohoredingdong/Notion`, base는 `main`이다. CLI는 같은 소스의 전체 성공·clean HEAD·origin·원격 브랜치 SHA부터 확인한다. 같은 저장소/브랜치/base/SHA의 기존 PR만 재사용하고, 없을 때 draft PR을 생성해 다시 읽어 확인한다. GitHub API 오류를 ‘기존 PR 없음’으로 판단하지 않는다. 종료0은 생성/재사용 검증,1은 로컬 조건 거부,2는 원격/API 미확인이다. 로그인·토큰 추출·API 우회·push·병합·배포 기능은 없다.

Git read/push 성공은 API 권한 성공과 다르다. API가 차단되면 결과 JSON·본문·브랜치를 보존하고 막힌 작업을 명확히 보고한다.

## 실패 코드를 후보로 만들지 않는 보호

```bash
python scripts/prepare_release.py \
  --sha "$(git rev-parse HEAD)" \
  --report /tmp/notion-full-check/report.json \
  --output /tmp/notion-reviewed-candidate
```

정확한40자리 SHA·현재 전체 계획·모든 성공/실행 시각·clean Git·추적 파일 전체 해시를 다시 검사한다. 실패/누락/skip/다른 커밋/오래된 파일/심볼릭 링크를 거부한다. 추적된 기존 HTML·자료·자산을 유지한 ZIP과 해시 manifest만 만든다. 누락된 로컬 자산과 변조도 거부한다. 임의 영구 배포·기록 초기화는 없다.

루트 설치용 HTML 템플릿1개와 역사 원본5개는 [명시적 문맥](../config/site-sources.json)으로 검증하고 원문을 보존한다. 이 파일들의 단독 URL 동작을 검증했다고 하지 않는다. 실제 페이지가 archive를 runtime으로 불러오면 실패한다. 외부 CDN·동적 JS 의존성의 완전한 해석은 정적 closure 검사의 범위 밖이다.

`Prepare Site Candidate for Review`는 동일 절차의 **수동·읽기 전용** Actions다. 전체 검사 실패 시 ZIP 생성 단계가 실행되지 않는다. Pages/content-write/id-token 권한이 없고 배포할 수 없다. 워크플로는 기본 브랜치에 승인·병합되기 전에는 수동 실행 메뉴에 나타나지 않을 수 있다.

`Development checks`도 공통 도구 변경 등으로 전체 계획이 선택된 경우 성공한 동일 커밋의 `inspection-candidate` artifact를 만든다. 관련 검사만 실행한 결과로 후보를 만들지 않는다. 이 ZIP은 검토용이며 운영 사이트로 자동 배포되지 않는다.

## 운영 배포 활성화는 별도 승인

현재 저장소에는 main 직접 자료 게시와 Pages build 요청이 있다. 새 PR CI·후보 생성은 기존 Pages를 소급해 차단하지 않는다. 실제 Pages source와 branch/environment 규칙을 API로 확인하기 전 서버 측 배포 보호가 활성화됐다고 보고하지 않는다.

관리자 승인 후 진행할 순서는 다음과 같다.

1. 현재 Pages source와 규칙을 읽고, 금융 writer26개 및3개 Pages build 호출과의 호환을 확인한다.
2. 코드 배포는 승인된 정확한 SHA/검증 run/artifact digest와 보호된 배포 환경을 묶는다. ‘최근 성공’이나 움직이는 branch만 승인 대상으로 쓰지 않는다.
3. 자료 갱신은 기존 일정/CAS/원장 보존을 유지한다. Actions 배포로 전환한다면 마지막 승인 코드와 새 검증 자료를 조합하는 자료 경로를 먼저 준비한다. Pages 모드만 먼저 바꿔 금융 갱신을 끊지 않는다.
4. 실제 배포·복구를 승인된 환경에서 확인한다. rollback은 코드와 최신 자료의 관계를 확인하고, 과거 시세/원장을 임의 되돌리지 않는다.

GITHUB_TOKEN으로 생긴 push는 보통 다른 push 워크플로를 재귀 실행하지 않는다. 새 CI가 모든 봇 자료 게시마다 실행된다고 가정하지 않는다. 기존 producer 검사와 `workflow_run`·독립 감사는 그대로 유지한다.
