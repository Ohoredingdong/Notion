# 공식 공시·기업행위 분석 모듈 (연구판 전용)

## 기존 상태와 이번 범위
기존 `update_stock_event_risks.py`는 최근 14일 뉴스 제목/수동 seed 위험 탐지이며 전체 공시 수집기가 아니다. 기존 추천·가격·데이터를 변경하지 않고 새 독립 모듈을 추가했다.

- `scripts/stock_corporate_actions.py`: OpenDART 전 페이지 목록(정정 포함), SEC 추가 이력 파일 수집, 근거 기반 계약/CB·BW/자사주/M&A 계산.
- `assets/stock-corporate-actions.js`: `StockCorporateActions.render(company)`로 선택한 기업의 수집 범위·분석·미확인·전체 수집목록을 표시하는 순수 렌더러. 자동 네트워크 요청·저장·매매신호 없음.
- 현재 화면/정기 워크플로에는 아직 연결하지 않았다. 이 모듈 단독 추가를 전 종목 분석 완성이나 배포 완료로 표현하면 안 된다.
- 연구판 전용. 공개·판매 시연판에 연구 데이터·이 모듈 자동 수집을 추가하지 않는다. 상업용 데이터 권리는 별도.

## 입력과 실행
입력 JSON: `companies` 배열에는 `symbol`, `market`(KR/US), 검증된 `corp_code` 또는 `cik`가 필요하다. 종목코드에서 고유번호를 추측하지 않는다. 한국은 `start_date`, `end_date`(YYYYMMDD)로 범위를 지정한다. 선택적 `events`는 원문을 읽어 검토한 구조화 사건이며 목록 제목에서 사실을 추측하여 만들지 않는다.

```
python scripts/stock_corporate_actions.py --input corporate-input.json --output stock-corporate-actions.json
python scripts/stock_corporate_actions.py --input corporate-input.json --offline --output corporate-review.json
python scripts/test_stock_corporate_actions.py
node scripts/test_stock_corporate_actions_ui.cjs
```

DART_API_KEY, SEC_USER_AGENT는 실행 환경의 비공개 환경변수로만 제공한다. SEC_USER_AGENT는 운영자가 허용한 연락처를 포함해야 한다. 키 발급/저장을 이 스크립트가 수행하지 않는다. 키·원문 민감정보·예외 URL을 출력하지 않는다. DART 목록은 제한된 페이지 예산을 초과하면 partial이며 SEC 요청은 순차 수행한다. 복수 프로세스를 운영할 때 전체 SEC 요청 제한은 실행자가 함께 관리해야 한다.

`events[]` 공통 필드: `event_id`, `symbol`, `kind`, `filing_status`(current/amended/superseded/withdrawn/unknown), `facts`, `evidence`. 각 `evidence[field]`에는 `url`(허용 공식 호스트), `locator`(원문 절/표 위치), `symbol`(해당 종목)이 있어야 값을 소비한다. 이것은 **추출 입력의 근거 연결 검사**이며 URL 존재/원문 진위·정확성을 자동 검증하는 것이 아니다. 원문·정정 연결을 확인한 수집/검토 계층만 사건을 생산해야 한다. 근거 없는 값은 null/미확인이다.

정정 제목은 표시하되 원본 연결을 제목에서 추측하지 않는다. 공시 ID 중복만 제거하고 정정 접수번호는 보존한다. 수집 중 총건수가 변하면 완전수집으로 인증하지 않는다. 공시 목록 0건은 위험 없음이 아니다.

## 분석 규칙
- 계약: 총계약금액과 선수금 분리, 통화·기업범위 일치 시만 연매출 대비 계산. 기간 연환산은 실제 매출인식 전망이 아니며 단기/대규모만으로 호재·매수 판정하지 않음.
- CB: 미전환 잔액 ÷ 현재가액/하한가액의 잠재 신주. 기존주식 대비와 완전희석 후 비중을 구분. 현재가 날짜·통화 불일치 시 가격 유인 계산 금지. 리픽싱 하한이 낮을수록 잠재희석이 커질 수 있음.
- BW: 채무잔액이 아닌 잔존 신주인수권 행사금액 사용. 사채 상환=권리 소멸로 가정하지 않음.
- 자사주: 취득·소각 모두 실제 완료이고 동일 프로그램일 때만 확인 배지. 계획/결의는 완료가 아님.
- M&A: 공시된 목적·대가·자금조달·승인·일정·주주 영향만 표시. 숨은 의도나 종결 확률을 만들지 않음.
- 모든 분석의 buy_signal=false. 전환/급락확률 미산출. 가격·공시가 최신이라고 예측 성능까지 검증된 것이 아님.

## 검증 상태 (2026-11-17)
30개 Python 단위테스트와 9개 JS 렌더러 assertion을 통과했다. 테스트는 합성 자료이며 실제 종목 데이터가 아니다. 현재 실행환경에 DART_API_KEY/SEC_USER_AGENT가 없어 실제 인증 수집을 실행하지 않았다. 실제 원문 추출기·전종목 회사번호 연결·화면 연결·정기 실행·공개배포 검증은 남아 있다.

## 공식 근거
- https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001
- https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020033
- https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020034
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/about/developer-resources
- https://www.fsc.go.kr/no010101/83400

## 기존 실행 경로 재확인
GitHub Actions의 기존 `stock-investment-cases.yml`와 `stock-reading-depth.yml`는 `secrets.DART_API_KEY`를 사용한다. 2026-11-17 04:46 UTC 결과 요약은 인증 성공·성공 응답 100건을 기록한다. 같은 날 05:03 실행 44021386843은 한국 240개 중 238개 계정을 수집했지만 미국은 실제 SEC 연락처 미설정으로 60개 모두 요청 전 차단했다. 기존 `vars.SEC_USER_AGENT` 주입 경로는 있으며 실제 값은 공백이었다. 따라서 로컬 환경에 키가 없다는 사실을 저장소 미설정으로 확대하면 안 된다. 새 공시 모듈은 검토된 Actions 작업에서 동일 secret을 주입하여 테스트 가능하며 키를 추출/복사할 필요가 없다. 이번에는 기존 워크플로 실행·환경변수·비밀을 변경하지 않았다. SEC 연락처는 사용자가 허용한 실제 연락처여야 하며 메모의 이메일이나 예제/가짜 연락처를 임의 설정하지 않는다.
