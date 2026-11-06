"""Synthetic fixtures test invariants only; production never imports these prices."""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from stock_forecast_model import *
from run_stock_forecasts import freeze, readlines


def fixture(n=900, mode='daily', market='US', end='2026-10-20'):
    rng = np.random.default_rng(478)
    cal = calendar(market, 2026)
    sessions = cal.sessions_in_range('2021-01-01', end)[-n if mode == 'daily' else -45:]
    rows = []
    price = 100.0
    for session in sessions:
        start, close = cal.session_open(session), cal.session_close(session)
        times = [(start, close)] if mode == 'daily' else [(s, s+pd.Timedelta(minutes=5)) for s in pd.date_range(start, close-pd.Timedelta(minutes=5), freq='5min')]
        for s, e in times:
            opened = price*(1+rng.normal(0, .001))
            price = opened*np.exp(rng.normal(0.0001, .012 if mode == 'daily' else .002))
            rows.append({'start': s, 'end': e, 'session': session.date().isoformat(),
                         'open': opened, 'high': max(opened, price)*1.002,
                         'low': min(opened, price)*.998, 'close': price})
    result = pd.DataFrame(rows)
    result.attrs.update(market=market, mode=mode)
    return result


class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bars = fixture()
        cls.fitted = fit_model(cls.bars, 'daily')
        cls.now = cls.bars.iloc[-1]['end']+pd.Timedelta(minutes=60)
        cls.record = make_prediction(cls.bars, cls.fitted, 'TEST', 'US', 'daily', cls.now, cls.now)

    def test_probability_sum(self):
        self.assertAlmostEqual(sum(self.record['probabilities'].values()), 1)
        self.assertEqual(set(self.record['probabilities']), set(CLASSES))

    def test_no_order_or_green_override(self):
        self.assertFalse(self.record['recommendation'])
        self.assertFalse(self.record['strict_green_override'])
        self.assertFalse(self.record['validation']['live_validated'])

    def test_truly_future_target(self):
        self.assertLess(stamp(self.record['issued_at']), stamp(self.record['target']['start']))
        self.assertLess(stamp(self.record['target']['start']), stamp(self.record['target']['end']))

    def test_no_future_feature_leakage(self):
        old, _ = features(self.bars, 'daily')
        changed = self.bars.copy()
        changed.loc[850:, 'close'] *= 4
        new, _ = features(changed, 'daily')
        pd.testing.assert_frame_equal(old.iloc[:850], new.iloc[:850])

    def test_train_cal_test_purge(self):
        data, _, _ = samples(self.bars, 'daily')
        train, cal, test = chronological_split(data)
        self.assertLess(train.target_end.max(), cal.origin.min())
        self.assertLess(cal.target_end.max(), test.origin.min())
        self.assertFalse(set(train.session) & set(test.session))

    def test_calibration_disjoint_from_test(self):
        self.assertLess(stamp(self.record['calibrated_through']), stamp(self.record['validation']['test_start']))

    def test_no_retroactive_forecast(self):
        late = stamp(self.record['target']['start'])+pd.Timedelta(minutes=1)
        r = make_prediction(self.bars, self.fitted, 'TEST', 'US', 'daily', self.now, late)
        self.assertEqual(r['status'], 'no_call')
        self.assertIsNone(r['probabilities'])

    def test_future_received_rejected(self):
        r = make_prediction(self.bars, self.fitted, 'TEST', 'US', 'daily', self.now+pd.Timedelta(hours=1), self.now)
        self.assertEqual(r['reason'], 'future_input_timestamp')
        self.assertIsNone(r['target'])

    def test_observation_after_receipt_rejected(self):
        received = self.bars.iloc[-1].end-pd.Timedelta(seconds=1)
        r = make_prediction(self.bars, self.fitted, 'TEST', 'US', 'daily', received, self.now)
        self.assertEqual(r['reason'], 'future_input_timestamp')
        self.assertIsNone(r['target'])

    def test_default_issue_uses_actual_call_clock_not_receipt(self):
        issued = self.now+pd.Timedelta(minutes=2)
        with patch('stock_forecast_model.datetime') as clock:
            clock.now.return_value = issued
            r = make_prediction(self.bars, self.fitted, 'TEST', 'US', 'daily', self.now)
        self.assertEqual(stamp(r['issued_at']), issued)
        self.assertEqual(stamp(r['received_at']), self.now)
        self.assertEqual(r['status'], 'research_prediction')

    def test_explicit_issue_ahead_of_actual_clock_rejected(self):
        with patch('stock_forecast_model.datetime') as clock:
            clock.now.return_value = self.now
            r = make_prediction(self.bars, self.fitted, 'TEST', 'US', 'daily', self.now,
                                self.now+pd.Timedelta(minutes=1))
        self.assertEqual(r['reason'], 'future_issue_timestamp')
        self.assertIsNone(r['probabilities'])
        self.assertIsNone(r['target'])

    def test_model_policy_and_market_provenance(self):
        self.assertEqual(VERSION, 'direction-forecast-1.1')
        self.assertEqual(self.fitted['version'], VERSION)
        self.assertEqual(self.fitted['policy_sha256'], digest(POLICY))
        self.assertEqual(self.record['policy_sha256'], digest(POLICY))
        self.assertEqual(self.record['policy_revision'], 'session-complete-targets-v2')
        old = {**self.fitted, 'version': 'direction-forecast-1.0'}
        r = make_prediction(self.bars, old, 'TEST', 'US', 'daily', self.now, self.now)
        self.assertEqual(r['reason'], 'model_policy_mismatch')
        self.assertIsNone(r['target'])
        wrong = {**self.fitted, 'market': 'KR'}
        r = make_prediction(self.bars, wrong, 'TEST', 'US', 'daily', self.now, self.now)
        self.assertEqual(r['reason'], 'model_input_market_or_mode_mismatch')
        self.assertIsNone(r['target'])

    def test_insufficient_data(self):
        with self.assertRaises(ValueError):
            fit_model(self.bars.tail(100).reset_index(drop=True), 'daily')

    def test_daily_500_sample_floor_is_unchanged(self):
        below = fixture(520)
        enough = fixture(521)
        self.assertEqual(len(samples(below, 'daily')[0]), 499)
        self.assertEqual(len(samples(enough, 'daily')[0]), 500)
        with self.assertRaisesRegex(ValueError, 'fewer_than_500_daily_training_samples'):
            fit_model(below, 'daily')
        fitted = fit_model(enough, 'daily')
        self.assertGreaterEqual(fitted['metrics']['test_samples'], 40)
        self.assertGreaterEqual(fitted['metrics']['test_sessions'], POLICY['minimum_test_sessions'])

    def test_missing_daily_trading_session_is_not_a_next_session_label(self):
        for market in ('KR', 'US'):
            with self.subTest(market=market):
                bars = fixture(8, market=market)
                missing = bars.drop(index=3).reset_index(drop=True)
                labels = target_rows(missing, 'daily')
                self.assertFalse(labels.iloc[2]['valid'])
                self.assertTrue(labels.iloc[1]['valid'])
                self.assertTrue(labels.iloc[3]['valid'])

    def test_daily_holiday_weekend_and_early_close_follow_exchange_calendar(self):
        us = fixture(2, market='US', end='2026-07-06')
        self.assertEqual(us.session.tolist(), ['2026-07-02', '2026-07-06'])
        self.assertTrue(target_rows(us, 'daily').iloc[0]['valid'])
        kr = fixture(2, market='KR', end='2026-07-03')
        self.assertEqual(kr.session.tolist(), ['2026-07-02', '2026-07-03'])
        self.assertTrue(target_rows(kr, 'daily').iloc[0]['valid'])
        short = fixture(2, market='US', end='2026-11-27')
        self.assertEqual(short.iloc[-1].end, pd.Timestamp('2026-11-27T18:00:00Z'))
        self.assertTrue(target_rows(short, 'daily').iloc[0]['valid'])

    def test_daily_dst_shift_preserves_next_session_label(self):
        bars = fixture(2, market='US', end='2026-11-02')
        self.assertEqual(bars.iloc[0].start, pd.Timestamp('2026-10-30T13:30:00Z'))
        self.assertEqual(bars.iloc[1].start, pd.Timestamp('2026-11-02T14:30:00Z'))
        self.assertTrue(target_rows(bars, 'daily').iloc[0]['valid'])

    def test_daily_market_must_be_bound_or_explicit(self):
        bars = self.bars.copy()
        with self.assertRaisesRegex(ValueError, 'history_market_mismatch'):
            target_rows(bars, 'daily', market='KR')
        bars.attrs.clear()
        with self.assertRaisesRegex(ValueError, 'history_market_required'):
            target_rows(bars, 'daily')
        self.assertTrue(target_rows(bars, 'daily', market='US').iloc[-2]['valid'])
        self.assertFalse(target_rows(bars, 'daily', market='KR')['valid'].any())

    def test_daily_wrong_boundary_or_naive_times_cannot_be_labels(self):
        bars = fixture(5)
        bars.loc[2, 'end'] -= pd.Timedelta(minutes=1)
        labels = target_rows(bars, 'daily')
        self.assertFalse(labels.iloc[1]['valid'])
        self.assertFalse(labels.iloc[2]['valid'])
        bars['start'] = bars['start'].dt.tz_localize(None)
        with self.assertRaisesRegex(ValueError, 'daily_session_timezone_missing'):
            target_rows(bars, 'daily')

    def test_partial_daily_bar_dropped(self):
        last = self.bars.iloc[-1]
        f = pd.DataFrame({'Open': [last.open], 'High': [last.high], 'Low': [last.low], 'Close': [last.close]}, index=[pd.Timestamp(last.session)])
        with self.assertRaises(ValueError):
            normalise_history(f, 'US', 'daily', last.start+pd.Timedelta(minutes=10))
        normalized = normalise_history(f, 'US', 'daily', last.end+pd.Timedelta(minutes=10))
        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized.attrs['market'], 'US')
        self.assertEqual(normalized.attrs['received_at'], (last.end+pd.Timedelta(minutes=10)).isoformat())

    def test_naive_intraday_rejected(self):
        f = pd.DataFrame({'Open': [100], 'High': [101], 'Low': [99], 'Close': [100]}, index=[pd.Timestamp('2026-10-20T10:00:00')])
        with self.assertRaises(ValueError):
            normalise_history(f, 'US', 'intraday', self.now)

    def test_nonoverlap_eval(self):
        bars = fixture(mode='intraday')
        d, _, _ = samples(bars, 'intraday')
        _, _, t = chronological_split(d)
        independent = t.iloc[nonoverlapping_positions(t)]
        self.assertTrue(all(independent.target_start.iloc[1:].to_numpy() >= independent.target_end.iloc[:-1].to_numpy()))

    def test_intraday_does_not_cross_session(self):
        bars = fixture(mode='intraday')
        tar = target_rows(bars, 'intraday')
        for idx in bars.groupby('session').tail(7).index:
            self.assertFalse(tar.loc[idx, 'valid'])

    def test_missing_bar_invalidates_target(self):
        bars = fixture(mode='intraday').iloc[:80].copy()
        bars = bars.drop(index=32).reset_index(drop=True)
        tar = target_rows(bars, 'intraday')
        self.assertFalse(tar.loc[29, 'valid'])

    def test_model_not_retrained_on_test(self):
        self.assertLess(stamp(self.record['trained_through']), stamp(self.record['calibrated_through']))
        self.assertGreater(self.record['validation']['test_samples'], 40)

    def test_temperature_keeps_normalized(self):
        p = temperature_scale(np.array([[.01, .04, .95]]), 3)
        self.assertAlmostEqual(float(p.sum()), 1)
        self.assertLess(p[0, 2], .95)

    def test_ledger_no_retimestamp_or_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'ledger.jsonl'
            freeze(p, [self.record])
            changed = {**self.record, 'issued_at': (self.now+pd.Timedelta(minutes=1)).isoformat()}
            freeze(p, [changed])
            stored = readlines(p)
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]['issued_at'], self.record['issued_at'])

    def test_no_call_not_added_to_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'ledger.jsonl'
            freeze(p, [{'status': 'no_call'}])
            self.assertEqual(readlines(p), [])

    def test_future_outcomes_pending(self):
        result = score_prediction(self.record, self.bars, self.now)
        self.assertEqual(result['status'], 'pending')

    def test_scoring_without_target_is_missing(self):
        result = score_prediction(self.record, self.bars, stamp(self.record['target']['end'])+pd.Timedelta(minutes=1))
        self.assertEqual(result['status'], 'target_prices_missing')

    def test_invalid_issue_date_not_success(self):
        late = {**self.record, 'issued_at': self.record['target']['end']}
        result = score_prediction(late, self.bars, stamp(self.record['target']['end'])+pd.Timedelta(minutes=1))
        self.assertEqual(result['status'], 'invalid_time_contract')

    def test_intraday_exact_future_window(self):
        bars = fixture(mode='intraday')
        row = bars.iloc[-30]
        target, reason = future_target(row, 'US', 'intraday', row.end+pd.Timedelta(seconds=20))
        self.assertIsNone(reason)
        self.assertEqual(stamp(target['start'])-row.end, pd.Timedelta(minutes=POLICY['intraday_gap_minutes']))
        self.assertEqual(stamp(target['end'])-stamp(target['start']), pd.Timedelta(minutes=30))

    def test_last_minutes_no_forecast(self):
        bars = fixture(mode='intraday')
        target, reason = future_target(bars.iloc[-1], 'US', 'intraday', bars.iloc[-1].end)
        self.assertIsNone(target)
        self.assertEqual(reason, 'insufficient_regular_session_time')

    def test_bad_quote_unit_spike_blocks(self):
        bars = self.bars.copy()
        bars.loc[bars.index[-1], 'close'] *= 100
        r = make_prediction(bars, self.fitted, 'TEST', 'US', 'daily', self.now, self.now)
        self.assertEqual(r['reason'], 'unresolved_price_discontinuity')
        self.assertIsNone(r['target'])
        from run_stock_extended_forecasts import valid_research_result
        self.assertTrue(valid_research_result(r))

    def test_missing_latest_features_is_a_compatible_no_call(self):
        fitted = {**self.fitted, 'features': self.fitted['features'].copy()}
        fitted['features'].iloc[-1, 0] = np.nan
        r = make_prediction(self.bars, fitted, 'TEST', 'US', 'daily', self.now, self.now)
        self.assertEqual(r['reason'], 'latest_features_missing')
        self.assertIsNone(r['target'])
        self.assertIsNone(r['probabilities'])
        from run_stock_extended_forecasts import valid_research_result
        self.assertTrue(valid_research_result(r))

    def test_provider_delay_keeps_target_in_future(self):
        bars = fixture(mode='intraday')
        row = bars.iloc[-30]
        target, reason = future_target(row, 'US', 'intraday', row.end+pd.Timedelta(minutes=16))
        self.assertIsNone(reason)
        self.assertGreater(stamp(target['start']), row.end+pd.Timedelta(minutes=16))

    def test_fixed_lead_is_also_used_in_training_labels(self):
        bars = fixture(mode='intraday')
        targets = target_rows(bars, 'intraday')
        self.assertEqual(targets.iloc[25]['target_start']-bars.iloc[25]['end'], pd.Timedelta(minutes=POLICY['intraday_gap_minutes']))
        self.assertEqual(targets.iloc[25]['target_end']-targets.iloc[25]['target_start'], pd.Timedelta(minutes=30))

def benchmark_synthetic():
    """Local/CI CPU timing only; these made-up candles are never market evidence."""
    for market in ('KR', 'US'):
        bars = fixture(1200, market=market)
        frame = pd.DataFrame({name.capitalize(): bars[name].to_numpy()
                              for name in ('open', 'high', 'low', 'close')},
                             index=pd.DatetimeIndex(bars.session))
        received = bars.iloc[-1].end+pd.Timedelta(minutes=10)
        wall, cpu = time.perf_counter(), time.process_time()
        normalized = normalise_history(frame, market, 'daily', received)
        normalise = {'wall_seconds': time.perf_counter()-wall, 'cpu_seconds': time.process_time()-cpu}
        wall, cpu = time.perf_counter(), time.process_time()
        fitted = fit_model(normalized, 'daily', market=market)
        fit = {'wall_seconds': time.perf_counter()-wall, 'cpu_seconds': time.process_time()-cpu}
        print('SYNTHETIC_MODEL_CPU_BENCHMARK', json.dumps({
            'fixture_type': 'synthetic_test_only', 'market': market, 'bars': len(normalized),
            'market_fetch_included': False, 'calendar_warmed': True,
            'normalise': normalise, 'fit': fit, 'model_version': fitted['version'],
            'test_samples': fitted['metrics']['test_samples']}, sort_keys=True))


if __name__ == '__main__':
    if sys.argv[1:] == ['--benchmark']:
        benchmark_synthetic()
    else:
        unittest.main()
