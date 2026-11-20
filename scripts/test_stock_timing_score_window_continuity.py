"""Synthetic-only negative controls for direct intraday score window continuity.

No broker, market API, original forecast row, price, order or learning write.
"""
import unittest

import pandas as pd

from stock_forecast_model import score_prediction
from run_stock_forecasts import complete_target


class IntradayScorerContinuityTests(unittest.TestCase):
    def setUp(self):
        start = pd.Timestamp("2026-10-30T14:30:00Z")
        self.end = start + pd.Timedelta(minutes=30)
        self.bars = pd.DataFrame([
            dict(start=start + pd.Timedelta(minutes=5*i),
                 end=start + pd.Timedelta(minutes=5*(i+1)),
                 session="2026-10-30",
                 open=100.0 if i == 0 else 100.0 + .3*i,
                 high=103.0, low=99.0,
                 close=102.0 if i == 5 else 100.0 + .3*(i+1))
            for i in range(6)])
        self.frozen = {
            "id": "synthetic_scoring_continuity_not_a_market_forecast",
            "symbol": "SYNTH_ONLY", "mode": "intraday",
            "status": "research_prediction",
            "issued_at": "2026-10-30T14:00:00+00:00",
            "received_at": "2026-10-30T13:59:00+00:00",
            "observed_until": "2026-10-30T13:55:00+00:00",
            "target": {"start": start.isoformat(), "end": self.end.isoformat()},
            "neutral_band_pct": 1.0,
            "direction": "up",
            "probabilities": {"down": .1, "flat": .1, "up": .8},
        }

    def score(self, bars, record=None):
        return score_prediction(record or self.frozen, bars,
                                self.end + pd.Timedelta(minutes=3))

    def test_complete_six_bar_window_scores_as_original(self):
        self.assertTrue(complete_target(self.frozen, self.bars))
        result = self.score(self.bars)
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["actual"], "up")
        self.assertTrue(result["correct"])
        self.assertAlmostEqual(result["return_pct"], 2.0)
        self.assertFalse(result["public_before_target_verified"])

    def test_missing_middle_bar_cannot_be_scored_from_endpoints_only(self):
        bad = self.bars.drop(index=2).reset_index(drop=True)
        self.assertFalse(complete_target(self.frozen, bad))
        self.assertEqual(self.score(bad)["status"], "target_prices_missing")

    def test_off_grid_middle_bar_cannot_be_scored(self):
        bad = self.bars.copy()
        bad.loc[2, "start"] += pd.Timedelta(minutes=1)
        self.assertFalse(complete_target(self.frozen, bad))
        self.assertEqual(self.score(bad)["status"], "target_prices_missing")

    def test_duplicate_middle_bar_cannot_be_scored(self):
        bad = self.bars.copy()
        bad.loc[2, "start"] = bad.loc[1, "start"]
        self.assertFalse(complete_target(self.frozen, bad))
        self.assertEqual(self.score(bad)["status"], "target_prices_missing")

    def test_session_boundary_must_not_be_crossed(self):
        bad = self.bars.copy()
        bad.loc[2, "session"] = "2026-10-31"
        self.assertFalse(complete_target(self.frozen, bad))
        self.assertEqual(self.score(bad)["status"], "target_prices_missing")

    def test_each_bar_must_cover_exact_five_minutes(self):
        bad = self.bars.copy()
        bad.loc[2, "end"] -= pd.Timedelta(minutes=1)
        self.assertEqual(self.score(bad)["status"], "target_prices_missing")

    def test_daily_single_complete_session_preserves_existing_scoring(self):
        daily = dict(self.frozen, mode="daily", target={
            "start": "2026-11-02T14:30:00+00:00",
            "end": "2026-11-02T21:00:00+00:00",
        })
        daily["issued_at"] = "2026-11-01T15:00:00+00:00"
        daily["received_at"] = "2026-10-30T21:05:00+00:00"
        daily["observed_until"] = "2026-10-30T20:00:00+00:00"
        bars = pd.DataFrame([dict(start=pd.Timestamp(daily["target"]["start"]),
                                 end=pd.Timestamp(daily["target"]["end"]),
                                 session="2026-11-02", open=100.0,
                                 high=103.0, low=99.0, close=102.0)])
        result = score_prediction(daily, bars,
                                  pd.Timestamp("2026-11-02T21:10:00Z"))
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["actual"], "up")


if __name__ == "__main__":
    unittest.main()
