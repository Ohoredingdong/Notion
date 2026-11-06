# 전체 상장 명부 일간 AI 연구 생성 — 2026-11-06

상태: **첫 실제 실행의 초기 shard에서 개별 OHLC 필터 차이를 발견하여 보완, 전체 재실행 최종 결과 미확정**.

최초 실행 소스: [`8e01c65a72e3af1215a516fcfb94d29525918329`](https://github.com/Ohoredingdong/Notion/commit/8e01c65a72e3af1215a516fcfb94d29525918329).
작업 브랜치: `feat/radar-all-ai-20261106`.
첫 실행: [Actions run 42179275477](https://github.com/Ohoredingdong/Notion/actions/runs/42179275477), `2026-11-06 07:12 UTC` 대기열 진입 확인. 초기 shard의 실제 오류와 보완은 8절에 기록하며 전체 완료 결과는 아직 기록하지 않는다.

이 문서는 전체 명부를 처리하는 설계, 고정한 모델·출처 조건, 검증 범위와 운영 한계를 기록한다. 작성 시점에는 실제 32개 shard의 최종 생성 수, 실패 수, 미처리 수, 게시 성공을 확인하지 않았다. 아래 명부 수와 테스트 통과 수를 실제 예측 생성 실적으로 해석하면 안 된다. 실제 실행 결과는 마지막 절에 별도로 추가한다.

## 1. 문제와 변경 범위

기존 `run_stock_extended_forecasts.py`의 순환 배치는 한 번에 최대 16개를 허용했고, 운영 workflow는 12개를 선택했다. 일반적으로 추적 종목 6개와 전체 명부 쪽 6개를 뽑고 각 cursor를 다음 위치로 옮겼다. 이미 생성된 결과를 합쳐 보관하는 작은 순환 처리여서, 검색 목록을 전체 명부로 넓힌 것만으로 전체 회사의 새로운 일간 AI 분석이 생기지는 않았다. 이 배치 구조는 [기존 선택 함수](../../scripts/run_stock_extended_forecasts.py)의 `choose_batch()`에서 확인할 수 있다.

이번 변경은 검증된 공식 명부의 모든 식별자를 하나의 manifest에 고정하고, 32개 shard가 각자 실제 일봉 수집·학습을 수행한 뒤 한 번에 합치는 방식이다. 기존 확장 feed인 `stock-extended-direction-forecast.json`의 v1 계약을 유지하면서 전체 실행의 식별자와 분모를 추가한다. 같은 feed를 예전 순환 workflow와 새 workflow가 번갈아 덮어쓰지 않도록 기존 `stock-extended-coverage.yml`을 전체 생성 pipeline으로 교체했다.

이 작업은 가격 기반 일간 연구 결과의 범위를 넓힌다. 모든 회사에 재무·뉴스·실시간 호가·심층 실사가 새로 수집됐다는 의미는 아니다. 기존 동결 예측·결과·전달 원장과 자동 주문 동작은 변경하지 않는다. 새 runner는 이 원장에 기록하지 않으며 `automatic_orders=false`, `recommendation=false`, `live_validated=false`를 유지한다.

## 2. 고정 입력과 전체 분모

최초 실행 준비 시 대조한 입력은 다음과 같다.

| 입력 | 시각 / 내용 | SHA256 |
| --- | --- | --- |
| `stock-universe-catalog.json` | 생성 `2026-11-06T03:24:32.254842+00:00`, 전체 8,587개 | `14c89892ffa8eee1b1f19f7bdb0aba4c2e5abc5649e4b82085a87ea2eb1cd525` |
| `stock-opportunity-data.json` | 생성 `2026-11-06T02:20:53.660935+00:00`, 기존 상세 자료 104개 | `e3cb038df8151f61c0c6dc9db8b4b35fbfcab34d4dd64af8407151f98281cc7d` |

공식 명부의 국가별 분모는 **한국 2,658개 + 미국 5,929개 = 8,587개**다. 명부는 `status=complete`와 `identifier_policy=kr-six-character-alphanumeric-v2`를 충족해야 한다. 국가·종목코드·이름·거래소와 한국 원문 코드가 유효하지 않거나 식별자가 중복되면 수집을 시작하지 않는다.

기존 상세 자료 104개는 모두 이 명부에 대응한다. 단순 문자열 비교에서 달랐던 항목은 기존 자료의 `US:MOG-A`와 공식 명부의 `US:MOG.A` 한 개이며, 같은 클래스에 대한 Yahoo 표기 차이다. 이를 별도 회사로 더하지 않는다. 따라서 이번 실행 분모는 8,587개이고, `8,587 + 104`가 아니다.

식별자 규칙은 다음과 같다.

| 범위 | 공식 식별자 | 제공자 요청 식별자 | 검증 |
| --- | --- | --- | --- |
| 한국 KOSPI | 6자리 영숫자 원문 유지 | 원문 + `.KS` | 원문 코드 및 거래소 일치 |
| 한국 KOSDAQ | 예: `0001A0` | `0001A0.KQ` | 알파벳을 삭제하거나 숫자로 바꾸지 않음 |
| 미국 일반 주식 | 예: `AAPL` | `AAPL` | 원문 코드 유지 |
| 미국 클래스 주식 | 예: `BRK.B`, `MOG.A` | `BRK-B`, `MOG-A` | 명시적 클래스 별칭, 원문은 `catalog_symbol`에 보존 |

현재 명부의 클래스 점 표기 23개는 이 규칙으로 지원되며, 8,587개 전부에 요청 식별자가 생기고 제공자 식별자 충돌은 0건이었다. 이것은 **요청 경로를 결정할 수 있다는 검증**이다. Yahoo에 유효한 가격 이력이 있거나 500개 학습 표본을 충족한다는 보장은 아니다. 향후 두 명부 항목이 같은 제공자 식별자로 변환되면 두 항목 모두 `provider_collision`으로 보류한다.

## 3. 실행 구조와 자원 제한

[전체 runner](../../scripts/run_stock_universe_forecasts.py)는 세 단계로 나뉜다.

1. `manifest`: 명부 원본 해시, 정확한 소스 commit, run ID와 attempt, 구현 파일 해시, 모든 회사의 식별자 및 shard 배정을 고정한다.
2. `shard`: 각 배정 종목을 직렬로 처리한다. 유효한 실제 가격으로만 기존 모델을 학습하고, 성공·보류·미처리 중 하나의 최종 상태를 남긴다.
3. `aggregate`: 명부와 코드가 manifest에 묶인 상태인지 확인하고, 모든 shard의 식별자·시각·카운터·모델 계약을 재검산한 뒤 한 개 feed를 만든다. 누락된 빈 shard도 거부한다.

[운영 workflow](../../.github/workflows/stock-extended-coverage.yml)의 고정값은 다음과 같다.

| 항목 | 값 |
| --- | --- |
| shard 수 | 32 |
| 동시 실행 상한 | 4개 shard |
| shard 내부 요청 | 종목별 직렬 처리 |
| 요청 간 최소 대기 | 앞선 요청 완료 후 0.75초 |
| shard 수집 예산 | 1,800초 |
| shard job 제한 | 35분 |
| 정상 예정 시각 | 매주 월–금 06:55 UTC, 한국 시각 15:55 |
| 예측 대상 | 다음 실제 거래 세션의 시가 → 종가 |
| 가격 원본 artifact | 2일 보관 |
| manifest·shard·게시 검증 artifact | 7일 보관 |

Yahoo/yfinance `0.2.66`, exchange-calendars `4.13.1`, scikit-learn `1.8.0`, NumPy `2.3.5`, pandas `2.2.3`, SciPy `1.17.0`을 고정하고 설치된 패키지 목록도 실행 증거로 남긴다. CPU 라이브러리 내부 스레드 수는 1로 제한한다.

본 수집 전에 [7개 종목의 실제 출처 검사](../../scripts/check_stock_universe_source.py)를 수행한다. 삼성전자, Apple, SK하이닉스, Berkshire B, Coca-Cola, 한국 알파벳 코드 종목과 첫 실행에서 오류가 확인된 동화약품(`000020.KS`)을 포함한다. 사전 검사도 실제 shard와 같은 `process_target()` 경로를 사용한다. 한국과 미국 각각 실제 완료 일봉 500개를 넘는 응답이 하나 이상 있어야 하고, 동화약품의 `price_available`도 실제로 확인돼야 다음 단계로 진행한다. 사전 검사에서 429 또는 제공자 회로 중단이 발생하면 전체 sweep을 시작하지 않는다. 개별 신생 회사의 표본 부족을 전체 제공자 장애로 단정하지 않는다.

같은 브랜치의 새 실행 요청은 `cancel-in-progress=true`로 이전 sweep을 대체한다. 이미 저장을 마친 유효 OHLC 캐시는 새 실행에서 재사용한다. 중단 당시 아직 저장되지 않은 결과가 모두 보존된다고 가정하지 않으며, 새 manifest를 만들고 전체 명부를 다시 처리한다. 서로 다른 코드 해시의 shard를 혼합하지 않는다.

32개 shard에 4개 동시 실행이므로 최대 8회 실행 묶음이 필요하다. 각 shard의 30분 예산을 모두 쓰면 수집만 약 4시간이 될 수 있고, 대기열·설치·집계·게시 시간은 별도다. 실제 소요 시간은 첫 실행에서 측정해야 하며 완료 시각을 보장하지 않는다. UI의 다음 평일 06:55 UTC + 3시간 여유는 지연을 알리는 기준이며 수집 완료 보증이 아니다. 거래소 휴일과 세션 시각은 모델의 거래소 달력으로 별도 판단한다.

## 4. 출처, 시각, 모델 보호 조건

### 실제 가격과 응답 식별자

수집은 Yahoo Finance의 실제 5년 일봉을 사용한다. 가격을 만들거나 빈 이력을 대체하지 않는다. `auto_adjust=false`, `actions=true`를 사용하며, 제공자 응답의 `symbol`, `exchangeName`, `exchangeTimezoneName`, `instrumentType=EQUITY`를 공식 명부의 요청 대상과 대조한다. 값이 없거나 다른 회사·클래스·거래소·상품이면 `source_identity_unverified`로 남긴다.

명부 대조를 뜻하는 `identity_verified`와 실제 응답 대조를 뜻하는 `source_identity_verified`를 분리한다. Yahoo는 거래소 공식 인증 원문이 아니므로 `provider_is_official_exchange=false`다. 이 식별자 검사는 종목 대응 오류를 막는 조건이며 가격의 거래소 원본 인증이나 모든 법인 사건의 독립 확인을 뜻하지 않는다.

고정된 yfinance 버전에서 공개 metadata 접근자는 추가 5일·1시간봉 요청을 일으킬 수 있어, 이미 받은 일봉 응답의 내부 metadata만 읽는다. 과도한 추가 요청으로 식별자 검사를 수행하지 않는다.

### 시각과 대상 세션

`fetched_at`은 실제 응답을 받은 뒤, `issued_at`은 학습을 마친 뒤 기록한다. 완료된 거래 세션의 봉만 모델에 넣고 다음 계약을 확인한다.

```text
observed_until <= received_at <= issued_at < target.start < target.end
```

모델은 정확히 다음 거래 세션의 개장·폐장 시각을 사용한다. 전체 수집이 오래 걸렸다고 이미 시작한 목표를 더 먼 날로 임의 이동하지 않는다. 발행 시 대상 세션이 이미 시작했거나 전달 여유가 부족하면 `no_call`이다. shard 완료 때나 aggregate 시점에 이미 끝난 목표를 가진 예측은 게시용 집계에서 거부한다. 개별 목표 만료는 문서 전체의 일간 갱신 시각과 별도로 처리해야 한다.

현재 실행의 shard 시작보다 오래된 `issued_at`도 거부한다. 이전 예측을 복사해 이번에 새로 생성한 수로 집계하지 않는다.

### 기존 모델 조건

가격 기반 모델의 최소 일간 학습 표본 **500개**, 시간순 학습·보정·검증 분리, 기존 평가 조건을 유지한다. 모델은 `direction-forecast-1.1` / `session-complete-targets-v2` 계약으로 정확한 거래 세션 경계를 검산한다. 최소 표본을 낮추거나 실패한 종목에 균등·고정 확률을 넣지 않는다.

집계에서는 소스에 고정된 모델 버전과 정책 해시, 모델·입력 지문, 보존된 feature 값, 예측 ID, 학습·보정·검증 종료 시각과 표본 수를 확인한다. [기존 독립 감사](../../scripts/audit_stock_forecast_independent.py)도 재사용해 확률 합계, 최대 확률과 방향의 일치, 중립 구간 정책을 검사한다. `strict_green_override=false`, 실거래 미검증, 연구 전용 표시를 유지한다.

최신 완료 세션에 주식 분할이 있으면 기존 정책처럼 `latest_session_split_review_required`로 보류한다. 새로 받은 이력과 현재 세션 캐시 양쪽에서 같은 조건을 적용한다. 과거에 분할이 있었다는 이유만으로 모든 이후 예측을 금지하지는 않는다.

## 5. 캐시와 제공자 제한

캐시는 회사의 국가·공식 코드·이름·거래소·제공자 식별자에 묶인 실제 OHLC다. 예측 캐시가 아니다. 가격 행과 응답 metadata의 해시를 재검산하고, 미래 수집 시각이나 변조된 내용은 재사용하지 않는다.

- 최신 완료 세션까지 유효한 캐시가 있으면 네트워크를 다시 호출하지 않고 기존의 실제 `fetched_at`을 유지한다. 이 가격으로 모델은 새로 학습하고 새 발행 시각을 기록한다.
- 오래된 캐시는 마지막 완료 세션의 14일 전부터 겹치는 구간을 요청해 병합한다. 겹치는 가격이나 분할 값이 바뀌었거나 새로운 분할이 있으면 5년 전체를 다시 받아 서로 다른 수정 상태의 가격을 섞지 않는다.
- 미완성 현재 봉은 캐시에 완료 봉으로 보관하지 않는다. 가격 원본은 cache와 짧은 보관 기간의 artifact에만 둔다. 공개 feed는 가격 원본 수천 개를 복제하지 않고 출처·입력 지문을 남긴 compact JSON이다.

OHLC가 비수치·비유한·0 이하이거나 고가/저가 관계를 충족하지 않는 봉은 기존 모델처럼 그 봉만 제외한다. 가격 수정·보간·앞 값 채우기를 하지 않는다. `row_quality`의 `original_rows`, `valid_rows`, `discarded_rows`, `discarded_reasons`를 cache와 출처 정보에 기록하고 source hash로 묶는다. 새 응답의 `basis=latest_provider_response`는 마지막 실제 응답의 분모를 뜻하므로 증분 응답의 행 수와 전체 보관 이력 길이는 다를 수 있다. 기존 유효 캐시는 `basis=legacy_verified_cache_rows`와 보관 행 수·제외 0을 사용하며, 과거 HTTP 응답의 원본 행 수를 알고 있다고 주장하지 않는다. 새 응답에서 잘못된 것으로 제외한 겹치는 날짜를 과거 캐시가 되살리지 않도록 해당 날짜도 제거한다.

429는 제한된 지수형 대기 후 최대 2회 재시도한다. 재시도 예산이 끝나면 해당 shard의 제공자 회로를 열어 남은 조회를 중단한다. 연속된 전송 장애 3건도 추가 요청을 중단한다. 중단 후 남은 회사는 `circuit_skipped`, 제한시간 뒤 남은 회사는 `deadline_skipped`다. 앞서 완료한 결과는 유지한다. 우회 주소·다중 계정·프록시 회전으로 제공자 제한을 피하는 동작은 없다.

이 회로는 shard별로 동작하므로 전체 pipeline에는 최대 4개의 직렬 요청 흐름이 존재한다. 제공자의 수용량, 지원 종목, 가격 누락, 정지·상장 변경 때문에 일부 또는 많은 회사가 실패할 수 있다. 유효한 가격이 와도 표본·모델·목표 시점 조건 때문에 예측은 보류될 수 있다.

## 6. 분모와 상태 산식

최종 `records`에는 공식 명부의 모든 식별자가 정확히 한 번 있어야 한다. `coverage`의 산식은 다음과 같다.

```text
total = prediction + failed + not_attempted
attempted = prediction + failed
no_call = failed + not_attempted
```

| 필드 | 의미 |
| --- | --- |
| `total` | manifest에 고정된 전체 회사 수 |
| `prediction` | 이번 실행에서 실제 가격으로 학습·검증하여 새로 발행한 연구 예측 수 |
| `failed` | 처리했으나 예측을 만들지 못한 수: 출처 실패, 식별자 불일치, 표본 부족, 모델 보류, 미지원·충돌 포함 |
| `not_attempted` | 제공자 회로 또는 시간 제한으로 처리하지 못한 수 |
| `attempted` | 성공 또는 최종 실패 상태까지 처리한 회사 수. 실제 외부 요청 수와 다름 |
| `source_collection_attempted` | 실제 제공자 조회를 한 번 이상 시도한 회사 수 |
| `source_fetch_attempts` | collector 호출 수. 재시도·전체 재수집 포함. 라이브러리 내부의 쿠키·HTTP 요청 수와 같다고 주장하지 않음 |
| `cache_current` | 현재 완료 세션 캐시를 사용한 회사 수. 외부 요청은 없지만 새 학습 결과가 생길 수 있음 |
| `price_available` | 신원이 대조된 실제 가격 이력을 확보한 회사 수. 예측 성공 수와 다름 |
| `unsupported` | 변환 미지원 또는 요청 식별자 충돌로 처리 실패한 회사 수. 외부 조회 시도에는 포함하지 않음 |

예전 run 계약과의 호환을 위해 **`run.no_call`은 `failed`만 포함**하고, `coverage.no_call`은 `failed + not_attempted`를 포함한다. 따라서 `run.attempted = run.research_prediction + run.no_call`이다. UI는 집계 위치를 혼용하면 안 된다.

`manifest_complete=true`는 모든 shard와 식별자가 모였음을 뜻한다. `coverage_complete=true`는 `not_attempted=0`을 뜻한다. 이 둘은 모든 회사에서 예측을 생성했다는 뜻이 아니다. 모든 `no_call`은 `probabilities=null`, `direction=null`, `target=null`이며 구체적인 이유가 있어야 한다.

최상위에는 `generation_mode=full_universe`, `run_id`, `source_commit`, `source_catalog_sha256`, `implementation_sha256`, `manifest_sha256`을 남긴다. `run`에는 각 shard의 원본 해시, 시작·완료 시각, 건수와 제한 사유가 포함된다.

## 7. 최초 검증과 게시 경계

최초 로컬 gate는 **총 92개 테스트 통과**, 그중 [새 runner 전용 회귀](../../scripts/test_stock_universe_forecasts.py)는 **28개 통과**다. 28개에는 다음 검증이 포함된다.

- 전체 식별자 분할, 한국 영숫자와 클래스 별칭, 충돌 차단, 명부·manifest 변조 거부.
- 실제 수집 완료·학습 완료 이후 시각, 캐시 수집 시각 보존, 증분 병합·과거 수정 시 전체 재수집.
- 429의 제한된 재시도와 이후 미처리 산식, 연속 전송 장애, 제한시간 후 부분 결과 보존.
- 제공자 종목·거래소·상품 불일치, 최신 분할 세션의 새 수집·캐시 양쪽 보류.
- 누락·중복·다른 run의 shard, 잘못된 분모, 현재 명부 변경, 만료·미래·재사용 발행과 모델 증거 변조 거부.
- 기존 실제 모델 라이브러리에 **테스트 전용 합성 900봉**을 넣은 `shard → aggregate` 연결 성공. 이 데이터는 임시 디렉터리에서만 사용하며 운영 feed나 원장에 기록하지 않는다.
- `python -S`로 aggregate CLI가 실행되는 표준 라이브러리 전용 경로.

92개 통합 gate는 `2026-11-06 07:11 UTC` 직전 로컬에서 3.067초에 통과했다. 고정 의존성을 설치한 환경에서 재현할 명령은 다음과 같다. 로컬 검증은 임시 디렉터리에 설치한 동일 모델 의존성을 Python 검색 경로에 추가해 실행했으며, 아래 명령은 의존성이 설치된 CI 환경의 경로를 쓴다.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=scripts \
  python -m unittest \
  scripts.test_stock_forecasts \
  scripts.test_stock_universe_forecasts \
  scripts.test_stock_extended_forecasts \
  scripts.test_stock_timing_band_audit \
  scripts.test_stock_universe_public -q
```

로컬 gate는 코드 계약 검증이며 실제 Yahoo 가용성이나 예측 수를 증명하지 않는다. 실제 사전 출처 검사, 32개 shard, 현재 데이터에 대한 UI·브라우저 검사, 게시·공개 페이지 대조는 별도의 실행 근거가 필요하다.

[게시기](../../scripts/publish_stock_universe_forecasts.py)는 실행 당시 명부·모델·수집기·독립 감사·workflow를 최신 브랜치와 비교한다. 중요한 입력이 바뀌면 과거 결과를 나중 소스 위에 게시하지 않는다. 무관한 동시 변경은 최신 브랜치에 보존하면서 **확장 feed 한 파일만** 갱신한다. 더 새로운 결과를 오래된 결과로 덮어쓰지 않는다.

처음에는 기능 브랜치에 게시하며, 기능 브랜치 수집만으로 공개 main 배포가 완료됐다고 판단하지 않는다. main에서 게시 성공한 경우 Pages 빌드를 요청하고 [공개 결과 검사](../../scripts/verify_stock_universe_public.py)로 실제 게시 commit과 문서를 확인한다. 업로드·commit·Pages 요청·공개 결과 확인은 각각 다른 단계다.

## 8. 첫 실행에서 확인한 오류와 제한된 수정

[첫 실행](https://github.com/Ohoredingdong/Notion/actions/runs/42179275477)의 shard 0–3 artifact를 대조한 중간 표본은 1,076개였다. 이는 전체 실행 완료 집계가 아니다. 이 중 한국 334개의 `source_error` 213건을 확인했고, 212건의 이유는 `ValueError: invalid_provider_ohlc_order`였다. 동화약품 `000020.KS`도 여기에 포함됐다. 첫 manifest SHA256은 `44eb107e474ed8736ed43412f76125119afed63ec1a3f2c9a7935c319b7aeb5b`이며 실행 소스는 최초 commit `8e01c65a72e3af1215a516fcfb94d29525918329`다.

원인은 기존 `normalise_history()`와 새 `frame_rows()`의 차이였다. 기존 경로는 잘못된 OHLC 봉을 제외하고 남은 실제 봉을 검증했지만, 최초 전체 runner는 한 봉의 고가/저가 관계 오류만 있어도 회사의 전체 이력을 거절했다. 오류 종목의 실제 잘못된 가격 값은 실패 이전에 보관되지 않았으므로, 어떤 가격이 얼마나 어긋났는지까지 이 중간 결과로 단정하지 않는다.

보완은 다음 범위로 제한했다.

- 잘못된 개별 봉만 제외하고 원본·유효·제외 수와 이유를 저장한다. 날짜 파싱·중복 날짜·회사 및 제공자 신원 검사는 계속 엄격하게 거부한다.
- 빠진 거래일을 채우지 않는다. 다음 거래 세션이 아닌 행을 정답으로 연결하지 않는 기존 `target_rows()` 조건과 최소 500개 유효 학습 표본을 유지한다.
- 최신 봉이 제외돼 과거 목표 시점만 남았다면 보류한다. 목표를 미래 날짜로 바꿔 성공 처리하지 않는다.
- 기존의 유효 cache는 유지하고, 새 source hash로 manifest를 다시 만들어 전체 명부를 재실행한다.
- preflight를 동일한 production 경로로 바꾸고 실제 오류 종목 `000020.KS`의 가격 확보를 필수 조건으로 추가한다.

회귀 검증에는 테스트 전용 900봉 중 고가 관계 오류·NaN·음수 봉 3개를 제거한 897봉으로 실제 모델 학습·집계가 통과하는 양성 사례를 추가했다. 남은 유효 학습 표본이 500개 이상인지 확인하고, 각 결측 직전 세션의 라벨이 무효인 것도 검산했다. 모든 봉이 잘못된 경우의 `no_call`, 최신 봉 오류로 목표가 이미 지난 경우의 `no_call`, 날짜·중복 거부, 기존 cache 재사용, 증분 응답의 잘못된 날짜가 과거 cache에서 복원되지 않는 경우도 검증한다. 이 보완의 runner 전용 회귀는 **35개 통과**, 최초 gate와 같은 통합 구성은 **99개가 3.658초에 모두 통과**했다. 별도 검토에서도 동일 runner 35개가 통과했으며, 실제 제공자 재검증은 이후 실행의 별도 조건이다.

첫 실행의 성공 경로를 독립 재현한 세 종목 `004490.KS`, `ABNB`, `HEI-A`에서는 저장된 실제 가격 입력으로 모델·입력·예측 ID·목표가 일치했고 확률의 최대 차이는 0이었다. 이는 해당 세 결과의 재현 확인이며 오류 212건의 해결 또는 전체 명부의 성공 비율을 대신 증명하지 않는다. 수정 후 실제 출처 확인과 최종 전체 결과는 다음 절에 기록한다.

## 9. 전체 재실행 결과 — 검증 후 추가

**아직 미확정. 아래 칸은 실제 실행 artifact와 공개 결과를 대조한 뒤 채운다. 명부 수를 생성 수에 복사하거나 테스트 fixture 결과를 사용하지 않는다.**

| 확인 항목 | 실제 근거 / 결과 |
| --- | --- |
| Actions run URL, run ID / attempt | 확인 후 추가 |
| 실행 source commit / manifest SHA256 / 명부 SHA256 | 확인 후 추가 |
| 실제 출처 preflight 결과 | 확인 후 추가 |
| 32개 shard 완료 여부, 실행 시작·끝, 전체 소요 시간 | 확인 후 추가 |
| `total / prediction / failed / not_attempted` | 확인 후 추가 |
| `source_collection_attempted / source_fetch_attempts / cache_current / price_available` | 확인 후 추가 |
| 국가별 실제 새 예측 수와 주요 보류·오류 사유 | 확인 후 추가 |
| 429·전송 장애·제한시간 회로와 남은 종목 수 | 확인 후 추가 |
| aggregate·UI·브라우저 gate 결과 | 확인 후 추가 |
| 기능 브랜치 게시 commit, 이후 main 반영 여부 | 확인 후 추가 |
| 공개 Pages 결과·commit·확인 시각 | 확인 후 추가 |

