"""Synthetic fixtures test invariants only; production never imports these prices."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from stock_forecast_model import *
from run_stock_forecasts import freeze, readlines


def fixture(n=900, mode='daily'):
    rng = np.random.default_rng(478)
    cal = calendar('US', 2026)
    sessions = cal.sessions_in_range('2022-01-01', '2026-10-20')[-n if mode == 'daily' else -45:]
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
    return pd.DataFrame(rows)


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

    def test_insufficient_data(self):
        with self.assertRaises(ValueError):
            fit_model(self.bars.tail(100).reset_index(drop=True), 'daily')

    def test_partial_daily_bar_dropped(self):
        last = self.bars.iloc[-1]
        f = pd.DataFrame({'Open': [last.open], 'High': [last.high], 'Low': [last.low], 'Close': [last.close]}, index=[pd.Timestamp(last.session)])
        with self.assertRaises(ValueError):
            normalise_history(f, 'US', 'daily', last.start+pd.Timedelta(minutes=10))
        self.assertEqual(len(normalise_history(f, 'US', 'daily', last.end+pd.Timedelta(minutes=10))), 1)

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
        self.assertEqual(stamp(target['start'])-row.end, pd.Timedelta(minutes=5))
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

if __name__ == '__main__':
    unittest.main()
