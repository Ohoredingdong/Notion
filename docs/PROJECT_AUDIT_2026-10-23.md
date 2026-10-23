# 기존 위젯·웹앱 현황 보고서

분석일: 2026-10-23 KST. 저장소: [Ohoredingdong/Notion](https://github.com/Ohoredingdong/Notion). 기준 커밋: `f1b1f99a347ae871a4397712c4552b2854241fe2`. 분석 시작 시 Git 원격 main의 SHA와 같았다. 작업 브랜치: `docs/project-handoff-20261023`.

소스·데이터·테스트·워크플로·README·배포 화면은 변경하지 않았다. 인수인계 문서와 조사 증거만 추가했다. 과거 ChatGPT 대화나 외부 앱 소스에 접근했다고 가정하지 않는다.

## 조사 범위와 확인 수준

기준 커밋의 추적 파일은 342개다. 루트 HTML 93개는 **현재 실행 페이지 40개와 기존 주소 보존용 리다이렉트 53개**로 나뉜다. 별도로 `assets/stock-radar-v8.html` 조각 HTML이 있어 HTML 전체는 94개다. Python 73개(테스트 파일 17개 포함), JSON 77개(루트 74개·tests 3개), JavaScript 28개, CSS 13개, Node 테스트 4개, GitHub Actions 26개, Supabase 함수 TypeScript 1개가 있다.

README 표의 38종은 모두 실제 현재 파일과 대응한다. README가 별도로 언급한 `home-budget-wide-v4.html`과 목록에 빠진 `company-notebook.html`을 추가해 실행 페이지는 40개다. README의 2026-10-20 점검 문장은 당시 기록이며 이번 확인 결과로 간주하지 않았다. 루트에 `index.html`은 없으므로 저장소 루트 배포 URL 자체를 실제 홈 화면이라고 확정할 수 없다.

검증을 다음처럼 구별한다.

- **소스 확인**: 실제 코드·참조·저장 키·스냅샷 구조 확인. 기능을 전수 실행했다는 뜻은 아니다.
- **초기 화면 확인**: 40개 페이지를 로컬 HTTP에서 1120/390/320px로 렌더링. raw GitHub 데이터 요청은 변경하지 않은 체크아웃 파일로 응답했다. 다른 외부 요청은 차단했다.
- **상호작용 확인**: 별도로 기록한 입력·저장·재로드·드래그 등 제한된 대표 경로. 모든 기능·접근성·터치 실기기의 완료 판정이 아니다.
- **저장된 결과**: JSON의 출처·날짜·인증·검증 상태를 읽은 것이다. 원 제공처의 최신 원자료와 재대조한 결과는 아니다.
- **원격 미확인**: GitHub Pages, 별도 Sites 앱, GitHub API가 이 환경의 네트워크 정책에서 403. 아래 배포 링크는 보존해야 할 경로이며 공개 HTTP 200·최신 배포 일치·실제 Notion iframe 작동을 보증하지 않는다.

브라우저는 Chromium 154, Python 3.12.14, Node 24.19.0을 사용했다. 외부 폰트 차단에 따른 대체 폰트로 화면을 관측했다. 개인 계정·실제 동기화·데이터 수집·게시·알림 전송은 실행하지 않았다. Python 게시 충돌 회귀에서의 Git push는 임시 디렉터리의 로컬 bare 저장소만 사용했다.

## 전체 프로젝트 현황표

이 표의 ‘현재 기능’은 소스 확인과 초기 화면 관찰을 합한 기술이다. 대표 상호작용까지 확인한 항목은 뒤의 검증 표에서 구별한다. S=좁은 파일/로직, M=연관 UI·저장·검증, L=도메인 모델·데이터 파이프라인. P0=데이터 보존, P1=핵심 신뢰성·작은 화면, P2=요구 확장·추가 검증. 수치 완성률은 근거가 없어 부여하지 않았다.

| 프로젝트명 | 실제 소스 파일 | 배포 링크(원격 미확인) | 현재 구현된 기능 | 오류 및 미완성 기능 | 예상 수정 범위 | 우선순위 | 추가 자료가 필요한 사항 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 투자 레이더 | [stock-value-radar.html](../stock-value-radar.html)<br>[stock-radar-v8.js](../assets/stock-radar-v8.js)<br>[stock-radar-v9.js](../assets/stock-radar-v9.js)<br>[build_stock_recommendations.py](../scripts/build_stock_recommendations.py) | [열기](https://ohoredingdong.github.io/Notion/stock-value-radar.html) | 104개 정밀·1,688개 기본 탐색, 시장/중소형 필터, 단기/장기·재무·근거·위험·관심 저장 | A03·A10: 판정/공식 검증 범위 차이, 기존 3흐름 회귀 실패. 최신 원자료 대조 미실행 | M/L: 판정·경고·Python 수집/대조·회귀 | P1 | 공식 기준·추천 표시·데이터 사용 범위 |
| 주식 판단 연습 | [stock-paper-investing.html](../stock-paper-investing.html)<br>[stock.js](../assets/investment-labs-20261016/stock.js)<br>[trainer.js](../assets/investment-labs-20261019/trainer.js) | [열기](https://ohoredingdong.github.io/Notion/stock-paper-investing.html) | 3단계 가상 판단 훈련, 용어 시험·복습, 직접 입력 계좌·손익·백업 코드 | A07: 실제 과거 사례·정보 시점·실제 결과 연결 없음 | L: 사례 데이터와 시간축/검증 | P2 | 역사 사례·당시 원자료·평가 기준 |
| 부동산 판단 연습 | [property-paper-investing.html](../property-paper-investing.html)<br>[property.js](../assets/investment-labs-20261016/property.js)<br>[trainer.js](../assets/investment-labs-20261019/trainer.js) | [열기](https://ohoredingdong.github.io/Notion/property-paper-investing.html) | 가상 판단 훈련·용어·복습, 직접 입력 부동산 금융/현금흐름 도구 | A07: 실제 시장 사건 재생 없음; 전체 금융 산식 실검증 미실행 | L: 실제 사례·금융 시뮬레이션 검증 | P2 | 사례·당시 공시/실거래·금융 기준 |
| 냉장고 & 레시피 | [use-me-first.html](../use-me-first.html)<br>[use-me-first-store.js](../use-me-first-store.js)<br>[use-me-first-kitchen.js](../use-me-first-kitchen.js)<br>[use-me-first-recipe-grid-final.js](../use-me-first-recipe-grid-final.js) | [열기](https://ohoredingdong.github.io/Notion/use-me-first.html) | 재료 수량/기한·추천·기록·장보기, 미니어처·재료/양념 드래그·위치 저장 | A01·A02·A08·A09: 기한 자동 변경, 5회귀 실패, 실제 서랍·차감·원가/예산 차이 | S→M/L: 데이터 보존 우선, 승인된 UI/도메인 | P0 | 최종 참고 이미지·별도 소스·단위/가격/영양 기준 |
| 우리의 식탁 | [our-food-budget.html](../our-food-budget.html) | [열기](https://ohoredingdong.github.io/Notion/our-food-budget.html) | 고정 품목 장보기·7일 식단, 주간/월 환산 예산·체크 저장 | 실제 재고 기반 자동 계획·구매 지출 원장 없음; 냉장고와 미연동 | M/L: 식단·지출·재고 계약 | P2 | 인분·실제 가격·연동 범위 |
| 우리의 돈 | [our-money-savings.html](../our-money-savings.html) | [열기](https://ohoredingdong.github.io/Notion/our-money-savings.html) | 수입·자산·저축·분담 계산, 월 스냅샷, CSV/JSON 백업 코드 | 거래별 실제 지출 원장과 계획/실소비 비교는 부분; 전체 복원 회귀 미실행 | M: 월별 소비·저장/복원·산식 | P1/P2 | 분담·이월·실지출 규칙 |
| Work Today | [work-today-v6.html](../work-today-v6.html) | [열기](https://ohoredingdong.github.io/Notion/work-today-v6.html) | Today/Tomorrow/This Week 할 일·완료·정렬·저장, 코드 동기화 경로 | A05·A12: 모바일 +21px 넘침; 외부 동기화 함수/쓰기 미검증 | S/M: 너비·기존 기록/동기화 검증 | P1 | 함수 소스·안전한 테스트 계정 |
| Routine Tracker | [routine-tracker-widget-v3.html](../routine-tracker-widget-v3.html) | [열기](https://ohoredingdong.github.io/Notion/routine-tracker-widget-v3.html) | 주간 루틴 추가·이름·요일 체크·완료율·로컬 저장 코드 | 초기 오류/넘침 없음; 전주 전환·긴 기록·모든 편집 경로 미검증 | S/M: 대표 조작·보존 회귀 | P2 | 필요 시 주간 이월/완료 규칙 |
| Habit Tracker | [habit-tracker-v2.html](../habit-tracker-v2.html) | [열기](https://ohoredingdong.github.io/Notion/habit-tracker-v2.html) | 주간 습관·체크·이름 편집·추가·달성률·저장 코드 | 초기 오류/넘침 없음; 기본 체크 예시와 실제 기록 구분/장기 보존 추가 점검 | S/M: 초기값·편집/보존 검증 | P2 | 기본 예시 표시·이월 기준 |
| Zero Spend | [zero-spend-v3.html](../zero-spend-v3.html) | [열기](https://ohoredingdong.github.io/Notion/zero-spend-v3.html) | 월 달력·무지출 표시·이동·통계·로컬 저장·동기화 경로 | A12: 개인 실제 동기화·다기기 충돌 미검증 | M: 기록·오류/충돌·월 변경 검증 | P2 | 백엔드 소스·테스트 계정 |
| 무지출 챌린지 | [nospend-dashboard.html](../nospend-dashboard.html) | [열기](https://ohoredingdong.github.io/Notion/nospend-dashboard.html) | 현재 월 날짜별 무지출 토글·연속/최고 기록·월별 키 저장 | A13: README의 달 이동과 달리 현재 월 고정; 전체 재로드 흐름 미검증 | S/M: 설명/월 탐색 정책·보존 | P2 | 과거 월 열람 필요 여부 |
| Minimal Greeting | [minimal-greeting.html](../minimal-greeting.html) | [열기](https://ohoredingdong.github.io/Notion/minimal-greeting.html) | 시간대 인사·날짜·이름 편집·이름 저장 코드 | 초기 오류/넘침 없음; 시간대 경계·이름 저장 입력 경로 추가 검증 | S: 시간/보존 회귀 | P2 | 원하는 인사·시간대 규칙 |
| Dot Web To-Do | [widgetstation-dot-todo.html](../widgetstation-dot-todo.html) | [열기](https://ohoredingdong.github.io/Notion/widgetstation-dot-todo.html) | 날짜별 할 일·완료·관심·삭제·날짜 탐색·저장 코드 | 초기 오류/넘침 없음; 긴 항목·여러 날짜의 보존 미검증 | S/M: 날짜·편집/보존 검증 | P2 | 필요 시 반복/이월 기준 |
| Daily English Word | [english-word-widget-v2.html](../english-word-widget-v2.html) | [열기](https://ohoredingdong.github.io/Notion/english-word-widget-v2.html) | 단어·뜻·예문·선택·앞뒤 이동·음성 호출·화면 설정 | A04·A05: 추가 JSON 파싱 실패 및 568px 넘침; 실제 음성 미검증 | S/M: 데이터·반응형·발음 | P1 | 추가 단어 원본·대상 음성 기기 |
| Daily French Word | [french-word-widget-v2.html](../french-word-widget-v2.html) | [열기](https://ohoredingdong.github.io/Notion/french-word-widget-v2.html) | 프랑스어 단어·뜻·예문·단어 이동·음성 호출·설정 저장 | A05: 570px 가로 넘침; 실제 발음/전수 어휘 미검증 | S/M: 반응형·언어 검증 | P1 | 발음 기준·대상 기기 |
| Daily Chinese Word | [chinese-word-widget-v2.html](../chinese-word-widget-v2.html) | [열기](https://ohoredingdong.github.io/Notion/chinese-word-widget-v2.html) | 중국어·병음·뜻·예문·이동·음성 호출·설정 저장 | A05: 570px 가로 넘침; 실제 음성/전수 어휘 미검증 | S/M: 반응형·언어 검증 | P1 | 중국어 음성/내용 기준 |
| 중국어 성조 퀴즈 | [tone-quiz-widget-v2.html](../tone-quiz-widget-v2.html) | [열기](https://ohoredingdong.github.io/Notion/tone-quiz-widget-v2.html) | 발음 듣기·4성 선택·정답/연속 기록·문항 진행 | 초기 표시 확인; 실제 음성 엔진·정답 판정 전체 경로 미검증 | S/M: 기기 발음·채점/진행 | P2 | 음성 엔진·대상 브라우저 |
| Cycle Notes | [cycle-notes-v3.html](../cycle-notes-v3.html) | [열기](https://ohoredingdong.github.io/Notion/cycle-notes-v3.html) | 월 달력·주기/증상·메모·기록·동기화 경로 | A05·A12: 526px 넘침; 개인 실제 동기화/빠른 전환 전수 미검증 | S/M: 반응형·기록/연결 실패 | P1 | 함수 소스·안전한 테스트 계정 |
| Market Radar | [market-radar.html](../market-radar.html) | [열기](https://ohoredingdong.github.io/Notion/market-radar.html) | 지수·환율·원자재 등 10항목의 값·변동·관측 시각 | 저장 JSON 렌더링 확인; 라이브 제공처·장시간 갱신 미검증 | S/M: 수집/표시·실패 경로 | P2 | 제공처 접근·갱신 주기 |
| 주식 시장 대시보드 | [stocks-dashboard-v2.html](../stocks-dashboard-v2.html) | [열기](https://ohoredingdong.github.io/Notion/stocks-dashboard-v2.html) | 지역·기간·지수/종목 가격·변동·차트·주기 재조회 코드 | 저장 데이터 초기 표시 확인; 모든 기간 데이터/라이브 수집 미검증 | M: 지역/기간·신선도/오류 | P2 | 시세 제공 범위·주기 |
| Market Events | [market-events-v4.html](../market-events-v4.html) | [열기](https://ohoredingdong.github.io/Notion/market-events-v4.html) | 한국/미국 등 경제 일정·실제/예상 값·필터·더 보기 | A05: 모바일 +20px 넘침; 일정의 현재 원자료 재검증 미실행 | S/M: 반응형·시점/일정 검증 | P1 | 공식 발표·시간대 기준 |
| Market Mood | [market-mood-v3.html](../market-mood-v3.html) | [열기](https://ohoredingdong.github.io/Notion/market-mood-v3.html) | 한국/미국/Crypto 심리·이전값·최근 관측·설정 | 저장 데이터 초기 표시 확인; 지수 산식·실시간 API 재검증 미실행 | S/M: 산식/출처·지연/오류 | P2 | 지표 산식·관측 주기 |
| 공포·탐욕 지수 | [fear-greed-dashboard-v3.html](../fear-greed-dashboard-v3.html) | [열기](https://ohoredingdong.github.io/Notion/fear-greed-dashboard-v3.html) | 한국/미국/Crypto 공포·탐욕, 이전값·최근 흐름 | 초기 표시 확인; Market Mood와 유사하나 별도 URL 유지, 라이브 검증 미실행 | S/M: 출처·지연/오류 회귀 | P2 | 지표 산식·관측 주기 |
| Exchange Rates | [exchange-rates-v3.html](../exchange-rates-v3.html) | [열기](https://ohoredingdong.github.io/Notion/exchange-rates-v3.html) | 주요 통화 KRW 환율·변동·USD/KRW 흐름·재조회 | 저장 일별 환율 확인; 실시간 환율/현재 고시 재대조 아님 | S/M: 기준일·단위·갱신 | P2 | 고시/현물 기준·JPY 100단위 |
| Exchange 환산기 | [exchange-dashboard.html](../exchange-dashboard.html) | [열기](https://ohoredingdong.github.io/Notion/exchange-dashboard.html) | KRW 금액 환산·선택 통화/검색·저장, Frankfurter 직접 조회 | 외부 API 차단 상황에서 실패 표시 확인; 성공 응답 환산 미검증 | S/M: 목적지 접근·응답/계산·실패 | P2 | api.frankfurter.dev 접근 |
| Bond Yields | [bond-yields-v3.html](../bond-yields-v3.html) | [열기](https://ohoredingdong.github.io/Notion/bond-yields-v3.html) | 한국/미국 만기별 국채 수익률·bp변동·장단기 스프레드 | 저장 값 표시 확인; 원 제공처 최신 관측/모든 만기 재검증 미실행 | S/M: 출처·만기/단위 검증 | P2 | 수익률 출처·관측 주기 |
| 원자재·원료 시세 | [commodities-dashboard-v3.html](../commodities-dashboard-v3.html) | [열기](https://ohoredingdong.github.io/Notion/commodities-dashboard-v3.html) | 7개 원자재 가격·변동·최근 흐름·관측 시각 | 초기 표시 확인; 계약/단위·원시세 라이브 재검증 미실행 | S/M: 시세·단위/오류 | P2 | 종목/계약·단위 기준 |
| Commodities Matrix | [commodities-matrix.html](../commodities-matrix.html) | [열기](https://ohoredingdong.github.io/Notion/commodities-matrix.html) | 귀금속·에너지·금속 매트릭스, 가격·KRW 환산·흐름 | 기존 이모지 아이콘 존재; 신규 디자인 승인 없이 유지. 라이브 재검증 미실행 | S/M: 단위·오류·기존 UI 유지 | P2 | 아이콘 변경은 별도 시각 승인 |
| Commodities Summary | [commodities-summary-widget.html](../commodities-summary-widget.html) | [열기](https://ohoredingdong.github.io/Notion/commodities-summary-widget.html) | 원자재 핵심 요약·7일 흐름·전체 보기 링크 | 저장 값 확인; 다른 원자재 화면과 목적 중복은 삭제 근거 아님 | S: 출처/오류·링크 검증 | P2 | 요약 대상·원본 단위 |
| 암호화폐 시장 | [cryptocurrency-dashboard-v2.html](../cryptocurrency-dashboard-v2.html) | [열기](https://ohoredingdong.github.io/Notion/cryptocurrency-dashboard-v2.html) | 코인 가격·상승/하락·기간/정렬·최근 흐름 | 저장 JSON 표시 확인; 거래소 실시간 연결·모든 기간 미검증 | M: 시세/기간·오류/지연 | P2 | 거래소·기간 데이터 기준 |
| Bitcoin Korea Premium | [bitcoin-korea-premium-v3.html](../bitcoin-korea-premium-v3.html) | [열기](https://ohoredingdong.github.io/Notion/bitcoin-korea-premium-v3.html) | BTC/ETH 국내-해외 비교·참고 프리미엄·환율 기준 분리 | 저장 status=reference·ECB 일별 환율. 실시간 차익거래 지표로 부르면 안 됨 | S/M: 시각·환율/가격 기준 검증 | P2 | 가격 시각/환율 기준 |
| Supply Chain Pulse | [supply-chain-pulse-v2.html](../supply-chain-pulse-v2.html) | [열기](https://ohoredingdong.github.io/Notion/supply-chain-pulse-v2.html) | GSCPI·ISM·WCI 등 공식/공개 지표·기간·지연 표시 | A11: WCI stale·HTTP429 저장. 최신 원자료 재대조 미실행 | M: 수집 복구·마지막 값 보존 | P1/P2 | Drewry/공식 제공처 접근 |
| News Link Hub | [news-link-hub-v3.html](../news-link-hub-v3.html) | [열기](https://ohoredingdong.github.io/Notion/news-link-hub-v3.html) | 지역·분류·신뢰/시간순 필터·기사 원문 링크 | 저장 기사 목록 확인; 기사 출처·분류·신뢰도 전수 검증 미실행 | S/M: 수집·출처/정렬 검증 | P2 | 분류·신뢰도 평가 기준 |
| Home Budget | [home-budget-v2.html](../home-budget-v2.html) | [열기](https://ohoredingdong.github.io/Notion/home-budget-v2.html) | 현금·대출·주택가로 자기자금/LTV·예산 계산, 입력 저장 코드 | 생활비 가계부가 아닌 주택 구입 계산기; 실제 대출 승인 모델 아님 | S: 산식·보존/범위 검증 | P2 | 주택 예산과 생활비의 구분 유지 |
| Loan Planner | [loan-planner-v3.html](../loan-planner-v3.html) | [열기](https://ohoredingdong.github.io/Notion/loan-planner-v3.html) | 대출 원금·금리·기간의 원리금균등 월납입·상환 구성 | 시뮬레이션. 실제 은행 견적/DSR 승인 아님; 전수 경계값 검증 미실행 | S/M: 0금리·기간/반올림 | P2 | 대출/상환 가정 |
| Buying Costs | [buying-costs-v3.html](../buying-costs-v3.html) | [열기](https://ohoredingdong.github.io/Notion/buying-costs-v3.html) | 주택 수·지역·면적·예외·매매가에 따른 취득 부대비용 계산 | 세율 가정 코드 확인; 현재 법규·개별 예외 원자료 재검증 미실행 | S/M: 법규 기준일·산식 검증 | P2 | 적용 법규·지역/예외 기준 |
| Mortgage Rate Watch | [mortgage-rate-watch-v3.html](../mortgage-rate-watch-v3.html) | [열기](https://ohoredingdong.github.io/Notion/mortgage-rate-watch-v3.html) | BOK 기준금리·COFIX·공식 기준일/이전값·상태 표시 | 은행 개인별 대출금리가 아님을 표시. 원 제공처 현재 값 재대조 미실행 | S/M: 공식 수집·지연/복구 | P2 | BOK/KFB 제공처 접근 |
| Real Estate Pulse | [real-estate-pulse-v3.html](../real-estate-pulse-v3.html) | [열기](https://ohoredingdong.github.io/Notion/real-estate-pulse-v3.html) | 16지역 매매/전세 주간 변동·BOK 기준금리·검증/지연 표시 | A11: health stale, asOf 10/12·발표 10/15. 현재 최신이라고 부를 수 없음 | M: 공식 수집·검증·마지막 값 보존 | P1 | REB 원자료·제공처 접근 |
| Home Budget 넓은 화면 | [home-budget-wide-v4.html](../home-budget-wide-v4.html) | [열기](https://ohoredingdong.github.io/Notion/home-budget-wide-v4.html) | 주택 구입 예산의 넓은 레이아웃·LTV·잔여자금/필요금 계산 | A06: 입력 재로드 시 초기화. home-budget-wide.html의 실제 대상 | S/M: 저장 계약·표준형과 공존 | P1 | 저장 공유/분리 정책 |
| 기업 노트 | [company-notebook.html](../company-notebook.html) | [열기](https://ohoredingdong.github.io/Notion/company-notebook.html) | 6개 기업 고정 재무·PER/PBR/ROE·가정·검토 노트·백업 코드 | README 표 누락. 자료 2026-10-20, 자동 갱신 없음·전체 복원/산식 미검증 | M: 갱신 정책·계산/백업·목록 보완 | P1/P2 | 6기업 자료 기준·갱신/시장 확대 범위 |
| 별도 한끼의 부엌 Sites 앱 | 이 저장소에서 소스 대응 미확인 | [열기](https://hankki-cozy-kitchen.wldms3053.chatgpt.site/) | 사용자 제공 URL만 확인 | 화면 접근 403·기능/코드/배포 대응 미확인 | 소스 확보 후 범위 산정 | 보류 | 별도 소스·배포 대응표·참고 이미지 |

## 재현된 오류와 요구사항 차이

| ID | 구분·우선순위 | 관측과 근거 | 다음 작업 범위 |
| --- | --- | --- | --- |
| A01 | 실제 저장 데이터 변경 · P0 | `use-me-first-kitchen.js`의 `refreshLegacyDemoExpiries`는 이름·수량이 정해진 조합 5개 이상이고 그중 4개 이상 만료되면 기한을 오늘 기준으로 다시 쓴다. 격리 브라우저에서 애호박 1개·우유 900ml·두부 300g·계란 10개·양파 3개·요거트 1개의 기한을 모두 2020-01-01로 저장하고 재로드하자 6개 모두 2026-10월 날짜로 변경됐다. `umf-demo-expiry-balance-v1=done`도 기록됨 | 실제 사용자 기록과 데모를 이름·수량만으로 구분할 수 없음. 자동 변경 중단/명시적 데모 범위, 원본 보존·복구 및 회귀를 별도 PR로 검토. 원본이 없는 과거 날짜를 추정 복원하지 않음 |
| A02 | 기존 Node 회귀 실패 · P1 | 130개 중 5실패. 1개는 기본 양념으로 편입된 굴소스를 customSeason으로 기대. 4개는 현재 없는 `.kitchen-zone-controls` 또는 `[data-action="layer-front"]`를 찾음 | 단순 테스트 삭제 금지. 사용자에게 필요한 이동·층 조작 UI의 의도와 현행 코드를 대조해 기능 복구/테스트 정정 결정 |
| A03 | 기존 레이더 브라우저 회귀 불일치 · P1 | 이 대화의 앞선 온보딩에서 같은 커밋으로 12케이스 통과·3폭 흐름 실패. 과거 `decision_brief.now` 3개와 현행 장기 `StockInvestmentCase.brief`의 판정 필터가 불일치. 실패 이후 흐름은 해당 실행에서 미검증 | 현재 판정의 기대값과 실제 데이터 계약을 검증하도록 조정. 실제 검색·상세·필터는 추가 16개 점검에서 별도로 확인. 기존 실패를 통과로 계산하지 않음 |
| A04 | 활성 JSON 구문 오류 · P1 | `english-words-extra.json`: JSONDecodeError, line 1 column 10120. 실제 영어 페이지가 이 파일을 요청하지만 Promise.allSettled로 실패 항목을 제외해 기본 단어는 표시함 | 구문을 고치고 전체 단어·중복·정렬 보존 검증. 일부 데이터 누락이 조용히 감춰지는 문제도 검토 |
| A05 | 작은 화면 가로 넘침 · P1 | 390/320px에서 Work Today=411/341, 영어=568/568, 프랑스어=570/570, 중국어=570/570, Cycle Notes=526/526, Market Events=410/340px의 document scrollWidth. 나머지 34페이지 초기 화면은 두 모바일 폭에서 가로 넘침 없음 | 공통 CSS·고정 너비·크기 설정을 원인별 점검. overflow만 숨겨 조작을 잘라내지 않고 기능·설정 패널까지 검증 |
| A06 | 넓은 주택 예산 저장 누락 · P1 | `home-budget-wide.html`→v4. 현금 120,000,000→200,000,000으로 입력한 뒤 재로드하면 120,000,000으로 복귀. 소스에 localStorage 저장 없음. 표준형은 `lifeTownHomeBudget.v2` 사용 | 키 공유/분리 정책 정하고 현재 표준형 기록과 URL을 보존. 생활비 앱으로 목적을 바꾸지 않음 |
| A07 | 실제 역사 사례 요구 미구현 · P2 | 두 학습 앱의 curriculum은 6유형의 수치 변형으로 생성한 가상 사례, 기존 12문제도 가상. 화면에 가상이라고 명시되어 있음 | 실제 사건·공개 당시 정보·결과 자료 선정, 시간축과 미래 정보 노출 방지 설계. 기존 가상 문제를 실제 사례로 재명명하지 않음 |
| A08 | 냉장고 외형·구획 요구 차이 · P2 | 현재 코지한 디자인, 두 문, 하단 두 서랍 모양은 존재. 실제 구획은 왼쪽 냉동·오른쪽 냉장, 하단 서랍은 aria-hidden 장식. 임박/추천 화면은 두 문에 각각 배치 | 사용자 참고 이미지와 외부 사이트 소스를 비교한 뒤 프렌치도어·실제 냉동 서랍·오른쪽 디스플레이 구조 확정. 임의 재디자인 금지 |
| A09 | 냉장고 도메인 기능 일부 없음 · P2 | 추천은 보유 재료 종류 중심. 식사 기록·취소·기록 복원은 있지만 수량 차감은 하지 않음. kcal는 고정 매핑이며 재료비·월 예산 연결 없음 | 단위·인분·소모·취소 정책과 가격/영양 출처 필요. 사용자 수량을 추측해 차감하지 않음 |
| A10 | 투자 결과의 적용 범위와 표시 · P1 | 정밀 104개, 기본 탐색 1,688개. 요약 current=52, 기간 충돌=8, 업종 모델 보강=15. strict green/투자 case positive=0인데 추천 요약 우선 추천=1. 별도 공식 감사는 10기업만 대상으로 함 | 서로 다른 규칙을 계산 오류로 단정하지 않고, 추천과 엄격 검증·공식 확인 범위를 혼동하지 않게 표시·기간 검증. 데이터 부족을 ‘검증 완료’로 바꾸지 않음 |
| A11 | 저장된 수집 지연 · P1/P2 | Real Estate health=stale, 마지막 asOf=2026-10-12/published=10-15. 공급망 WCI=stale·HTTP 429·reference_date=10-15. UI에 지연 표시 경로 존재 | 실접근·공식 원자료·주기 확인 후 갱신 복구. 이번에는 데이터/날짜/health를 변경하지 않음 |
| A12 | 외부 앱·함수 소스 및 실제 연결 미확인 | 별도 냉장고 Sites 소스 없음. Work Today·Cycle Notes·Zero Spend의 호출 대상 백엔드 구현을 이 체크아웃에서 모두 확인할 수 없음 | 외부 배포와 소스 대응표·안전한 테스트 계정·동기화 충돌 계약 확인. 소스 부재를 미구현이라고 단정하지 않음 |
| A13 | README와 실제 범위 차이 · P2 | 기업 노트 누락. 넓은 Home Budget은 별도 언급. README가 무지출 챌린지의 달 이동을 기재하지만 `nospend-dashboard.html`은 현재 연월을 고정하고 이전/다음 달 UI가 없음 | 실제 기능 재확인 후 설명 또는 승인된 기능 보완. 이번에는 README를 수정하지 않음 |

## 검증 결과와 한계

| 검증 | 결과 | 증거·범위 |
| --- | --- | --- |
| 현재 40페이지 × 3폭 초기 로드 | 120/120 HTTP 200, load_error=0, 처리되지 않은 JS 예외=0 | [page-audit.json](audit-2026-10-23/page-audit.json). 원격 GitHub 요청은 로컬 JSON으로 응답. 성공은 초기 렌더링만 의미 |
| 작은 화면 폭 | 6페이지의 두 모바일 폭에서 넘침, 나머지 34페이지는 초기 화면 폭 통과 | document/body scrollWidth와 viewport 비교. 모달·키보드·장시간 상태 전수 검증은 아님 |
| 53개 이전 주소 | 53/53 최종 URL·쿼리·해시 유지 | [redirect-checks.json](audit-2026-10-23/redirect-checks.json). `?handoff_audit=1#preserve-fragment`로 Chromium 실제 이동 |
| HTML의 리터럴 로컬 script/link/img 참조 | 누락 0개 | [file-relations.json](audit-2026-10-23/file-relations.json). 동적으로 계산한 URL과 CSS 내부 참조까지 전부 검사했다는 뜻은 아님 |
| 추적 JSON 파싱 | 77개 중 76개 성공, 영어 extra 1실패 | [json-checks.json](audit-2026-10-23/json-checks.json). 루트 74개·tests 3개. 파싱 성공은 내용의 공식 정확성 검증이 아님 |
| Python unittest | 262/262 통과, 0실패/0오류 | [python-tests.log](audit-2026-10-23/python-tests.log). 실패·경합 주입의 경고 출력은 테스트의 의도된 분기 |
| Node 테스트 | 130개 중 125통과·5실패·0 skipped | [node-tests.log](audit-2026-10-23/node-tests.log). 기존 실패를 유지한 상태 |
| 기존 레이더 브라우저 suite | 12케이스 통과·3흐름 실패 | 동일 커밋의 앞선 온보딩 실행 결과 [radar-browser-results.json](audit-2026-10-23/radar-browser-results.json). 이번에 같은 실패를 반복 실행하지 않고 소스 원인과 추가 경로를 조사 |
| 별도 레이더·냉장고 16점검 | 16통과 | [functional-smoke.json](audit-2026-10-23/functional-smoke.json). 앞선 온보딩의 같은 소스에서 검색·상세·시장·페이지 추가·3폭 레이아웃·재료 저장 등 확인 |
| 이번 주요 앱의 대표 입력 | 5페이지의 선택 경로 통과 | [primary-flows.json](audit-2026-10-23/primary-flows.json). 돈: 수입 변경·월 기록·재로드. 식탁: 장보기 체크·재로드·식단/예산 탭. 기업 노트: 메모 자동 저장·재로드. 두 학습 앱: 답 제출·해설·기록 보존·용어 화면. 학습 답안 정확성 전체 검증은 아님 |
| 냉장고 실제 pointer·저장 | 재료 위치 변경·재로드 보존, 간장 선반 이동·재로드 보존 확인 | [verified-gaps.json](audit-2026-10-23/verified-gaps.json). 격리 데스크톱 Chromium의 두 재료·세 양념 표본. 터치 실기기·모든 아이콘·층 조작을 전수 통과한 것은 아님 |
| 확정 결함 재현 | 소비기한 6개 자동 변경, 넓은 주택 예산 값 재로드 소실 | 동일 verified-gaps.json. 오염 없는 새 브라우저 컨텍스트의 합성 데이터만 사용 |
| 공개 배포·별도 Sites·GitHub API | 네트워크 정책 403으로 미확인/차단 | 배포 서버 자체 장애나 GitHub 권한 부재로 단정하지 않음. Git HTTPS 읽기는 별도로 성공 |
| 실제 개인 동기화·알림·Notion·모바일 터치·발음 | 미실행 | 서비스 쓰기·음성 엔진·실제 임베드 검증을 로컬 테스트로 대신 주장하지 않음 |

### 초기 화면 기준선

시각 수정은 하지 않았으므로 ‘수정 후’ 이미지는 없다. 아래는 로컬 소스의 초기 상태이며 최종 디자인 승인 자료나 현재 공개 배포 스크린샷은 아니다. 레시피·예산의 기본 예시값은 코드의 초기값이다.

| 화면 | PC 1120px | 모바일 390px |
| --- | --- | --- |
| 냉장고 | [초기 화면](audit-2026-10-23/fridge-1120.png) | [초기 화면](audit-2026-10-23/fridge-390.png) |
| 투자 레이더 | [초기 화면](audit-2026-10-23/radar-1120.png) | [초기 화면](audit-2026-10-23/radar-390.png) |
| 기업 노트 | [초기 화면](audit-2026-10-23/notebook-1120.png) | [초기 화면](audit-2026-10-23/notebook-390.png) |

## 구조·공유 의존성과 개발 절차

| 위치 | 역할·주의 |
| --- | --- |
| 루트 40개 현재 HTML | 정적 실행 진입점. README의 38종 외 기업 노트·넓은 주택 예산도 포함 |
| 루트 53개 작은 HTML | canonical 링크와 `assets/widget-legacy-redirect.js`를 사용하는 호환 URL. 삭제 금지 |
| JSON 77개(루트 74개·tests 3개) | 시세·수집 상태·학습 단어·투자 파생 결과 및 과거 테스트 결과. 과거 결과 파일을 현재 실행의 통과 증거로 사용하지 않음 |
| `assets/life-town-v2.css`, `life-town-controls-v2.js` | 현재 실행 HTML 23개가 각각 직접 참조. 컨트롤이 다른 공통 CSS를 동적으로 추가하는 경로도 있어 파일명 버전만으로 사용 여부를 판단하면 안 됨 |
| `assets/life-town-detail-batch1.css` | Cycle Notes·Routine Tracker·Zero Spend 3페이지에서 직접 참조 |
| `use-me-first-*`, `widget-control-system.js` | 냉장고의 도메인·영구 저장·동기화·화면·미니어처·구획별 책임. 이름에 final이 있어도 임의 제거/교체 금지 |
| `assets/stock-radar-v8.*` + v9 및 추가 레이어 | 현재 레이더가 v8 기반과 v9 확장, 시장 분류·읽기 안내·판정·추천을 함께 참조. v8이 구버전이라는 이유만으로 삭제하면 안 됨 |
| `assets/investment-labs-20261016/`, `20261019/` | 두 학습 페이지가 기존 계좌/계산과 새 curriculum/trainer를 동시에 사용 |
| `scripts/` 73 Python | 수집·판정·공식 대조·설치·게시와 17테스트. 설치·갱신 함수 중에는 추적 HTML/JSON을 덮어쓰는 작업이 있음 |
| `.github/workflows/` 26 YAML | 시장·부동산 수집과 투자 분석·검증·게시. CI Python 3.12, 일부 Playwright 1.56.0·bs4 4.14.3·yfinance 0.2.66·exchange-calendars 4.11.3 고정 |
| `scripts/publish_widget_data.py` | 최신 main에서 지정 JSON을 게시하고 경합·오래된 스냅샷 덮어쓰기를 처리. 실제 실행은 원격 변경이므로 읽기 점검과 구별 |
| `supabase/functions/use-me-first-sync/index.ts` | 냉장고 서버 함수. SUPABASE_URL·SUPABASE_SERVICE_ROLE_KEY는 서버 설정이며 정적 프런트엔드에 넣으면 안 됨 |
| `tests/` | 4개 CJS 테스트와 과거 점검 JSON. 과거 점검 메타데이터는 이번 실행 결과와 분리 |

루트 package.json·Python requirements/lock·일반 번들 빌드 설정은 없다. 개발은 정적 서버와 Python/Node 검증이 중심이다. 현 클라우드의 의존성은 저장소 밖 `/workspace/.notion-cloud`에 설치되어 있다. 실행 명령과 안전한 unittest 경로는 [AGENTS.md](../AGENTS.md)에 기록했다.

기존 Actions는 main에 데이터를 자동 게시하는 설계를 갖고 있다. 사용자가 요구한 개발 브랜치·PR 규칙과 자동 수집 게시 정책의 관계는 추후 따로 검토한다. 이번 작업에서는 Actions를 실행하거나 게시 정책을 변경하지 않았다.

### 삭제하지 않을 구버전 주소

모든 이전 주소의 현재 canonical 대상은 다음과 같다. 53개 모두 실제 Chromium에서 쿼리·해시 보존을 확인했다. 외부 Notion 임베드 사용량을 열람할 수 없으므로 ‘참조가 없어 보인다’는 이유로 제거하지 않는다.

| 현재 대상 | 보존할 이전 파일 |
| --- | --- |
| `bitcoin-korea-premium-v3.html` | `bitcoin-korea-premium-v2.html`, `bitcoin-korea-premium.html` |
| `bond-yields-v3.html` | `bond-yields-v2.html`, `bond-yields.html` |
| `buying-costs-v3.html` | `buying-costs-v2.html`, `buying-costs.html` |
| `chinese-word-widget-v2.html` | `chinese-word-widget.html` |
| `commodities-dashboard-v3.html` | `commodities-dashboard-v2.html`, `commodities-dashboard.html` |
| `cryptocurrency-dashboard-v2.html` | `cryptocurrency-dashboard.html` |
| `cycle-notes-v3.html` | `cycle-notes-v2.html`, `cycle-notes.html` |
| `english-word-widget-v2.html` | `english-word-widget.html` |
| `exchange-rates-v3.html` | `exchange-rates-v2.html`, `exchange-rates.html` |
| `fear-greed-dashboard-v3.html` | `fear-greed-dashboard-v2.html`, `fear-greed-dashboard.html`, `market-sentiment.html` |
| `french-word-widget-v2.html` | `french-word-widget.html` |
| `habit-tracker-v2.html` | `habit-tracker.html` |
| `home-budget-v2.html` | `home-budget-combined.html` |
| `home-budget-wide-v4.html` | `home-budget-wide-v2.html`, `home-budget-wide-v3.html`, `home-budget-wide.html` |
| `loan-planner-v3.html` | `loan-planner-v2.html`, `loan-planner.html` |
| `market-events-v4.html` | `market-events-v2.html`, `market-events-v3.html`, `market-events.html` |
| `market-mood-v3.html` | `market-mood-v2.html` |
| `mortgage-rate-watch-v3.html` | `mortgage-rate-watch-v2.html`, `mortgage-rate-watch.html` |
| `news-link-hub-v3.html` | `news-link-hub-v2.html`, `news-link-hub.html` |
| `our-money-savings.html` | `our-money-lavender.html`, `our-money-pastel.html`, `our-money-shared.html`, `our-money-v2.html`, `our-money.html` |
| `real-estate-pulse-v3.html` | `real-estate-pulse-v2.html`, `real-estate-pulse.html` |
| `routine-tracker-widget-v3.html` | `routine-tracker-widget-v2.html`, `routine-tracker-widget.html` |
| `stocks-dashboard-v2.html` | `stocks-dashboard.html` |
| `supply-chain-pulse-v2.html` | `supply-chain-pulse.html` |
| `tone-quiz-widget-v2.html` | `tone-quiz-widget.html` |
| `work-today-v6.html` | `work-today-v2.html`, `work-today-v3.html`, `work-today-v4.html`, `work-today-v5.html`, `work-today.html` |
| `zero-spend-v3.html` | `zero-spend-v2.html`, `zero-spend.html` |

`assets/stock-radar-v8.html`은 현재 루트 HTML과 별개의 조각 자산이며 `scripts/install_stock_radar_v8.py`가 읽는다. 일부 예전 설치 경로·텍스트·이미지 자산은 직접 런타임 참조가 없을 수 있지만 빌드/설치 입력이나 외부 사용 가능성까지 이번 조사로 배제하지 않았다. 미사용으로 확정하거나 삭제하지 않았다.

### 저장 계약의 주요 예

| 기능 | 보존해야 할 기존 키·형태 |
| --- | --- |
| 냉장고 | `use-me-first-state-v5`, `use-me-first-v4`, 양념·상비·사용자 정의·수량·식사·즐겨찾기 레거시 키, 동기화 메타·복구 키. 전체 목록은 store.js의 keys 객체 |
| 냉장고 배치·양념 | `use-me-first-kitchen-view-v1`(내용은 version 2), `umf-seasoning-layout-v3`. 키와 내부 버전 번호를 혼동하지 않음 |
| 레이더·기업 노트 | `radar-v8-stars`, `company-notebook-v1` |
| 학습·기존 계좌 | `investment-lab:stock:learning:v2`, `investment-lab:property:learning:v2`, `investment-lab:stock:v1`, `investment-lab:property:v1` |
| 식비·생활비 | `our-food-widget-1`, `ourmoney-dashboard-v1` |
| 주택 예산 | 표준형 `lifeTownHomeBudget.v2`; 넓은 v4는 현재 입력 저장 없음 |
| Work Today | `lifetown_work_today_compact_v3`, `lifetown_work_today_sync_code_v1`, `lifetown_work_today_v5_ui` |
| 루틴·습관 | `routineTracker.v3`, `lifeTownHabitTracker.v2` |
| 주기·무지출 | `cycle-notes-v5`, `cycle-notes-sync-code-v1`, `zeroSpendWidget:v1`, 동적 `notion_nospend_${year}_${month+1}` |
| 단어 | 영어 `english-word-widget-controls-v4`, 프랑스어 `french-word-widget-v2-state`, 중국어 `chinese-word-widget-v2-state` |
| 기타 | `life-town-dot-web-todo-v1`, `lifetown_minimal_greeting_name_v1`, `notion_exchange_dashboard_v1`, 공통 크기/테마/잠금 키 |

이 목록은 주요 고정 키의 예다. 동적 키와 추가 컨트롤 키까지 전부 열거한 것으로 사용하지 않는다. 키·스키마 변경 전 실제 코드·기존 백업과 실패/복구 경로를 더 확인해야 한다.

## 완성도 평가와 먼저 완성할 프로젝트

| 프로젝트 | 현재 준비 수준 | 완성 판정을 막는 핵심 조건 |
| --- | --- | --- |
| 냉장고·레시피 | 주요 입력·배치·저장 기반을 실행 확인 | P0 소비기한 보존, 5개 회귀 실패, 확정 외형과 구획 차이, 차감·원가·예산 미연결 |
| 투자 레이더 | 탐색·상세·필터 및 분석 파이프라인 존재 | 판정 정책 설명·검증 범위·누락/기한, 3흐름 회귀 실패, 실제 제공처 재대조 미실행 |
| 기업 노트 | 6기업 자료·계산·메모 보존 확인 | 고정 자료의 갱신 정책과 확장 범위, 전체 계산·복원 검증 |
| 주식·부동산 훈련 | 가상 학습·용어·직접 입력 도구 기반 | 요구한 실제 역사 사례·정보 시점·결과 비교가 없음 |
| 우리의 돈·식탁 | 대표 입력·월 기록/체크 보존 확인 | 거래 원장/계획 구분, 월별 실제 소비, 냉장고 재고와 연동 정책 |
| 주택 예산·기타 위젯 | 현재 40화면 모두 초기 렌더 가능 | 넓은 화면 저장 누락, 6페이지 모바일 넘침, 영어 데이터 오류, 외부 연결/지연 검증 |

가장 먼저 완성할 세 프로젝트는 **① 냉장고·레시피(데이터 보존) ② 투자 레이더(판단 신뢰성과 경고) ③ 우리의 돈(이미 있는 저장·월 기록 기반의 생활비 완성)**이다. 다른 위젯의 확정된 작은 결함은 별도 좁은 PR로 수정할 수 있다. 각 프로젝트의 수정 순서·예상 범위·수용 기준은 [ROADMAP.md](../ROADMAP.md)에 정리했다. 기업 노트나 학습 앱을 레이더와 임의로 통합하자는 제안이 아니다.

필요한 추가 자료는 최종 냉장고 참고 이미지와 별도 사이트 소스/배포 대응표, 수량·취소·가격·영양 기준, 투자 판단·원자료 정책, 실제 역사 사례, 생활비 분담·실제 지출 규칙이다. 키 값은 공개 문서나 채팅 대신 보안 설정에서 제공한다. 이 자료가 없어도 진행할 수 있는 확인과 문서화는 완료했다.
