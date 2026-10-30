"""Synthetic-only, preregistered tests of fixed decision-band evidence.
No market quotes, forecasts, orders, tuning or retrospective score edits.
"""
import math
import unittest
from audit_stock_forecast_independent import validate

class FrozenBandAuditTests(unittest.TestCase):
    def record(self, mode='daily', vol20=0.004):
        return {
            'id': 'SYNTHETIC-ONLY-band',
            'symbol': 'TEST', 'market':'US', 'mode':mode,
            'status':'research_prediction', 'version':'direction-forecast-1.0',
            'policy_revision':'provider-latency-30m-v1',
            'observed_until':'2026-10-29T13:35:00Z',
            'received_at':'2026-10-29T13:35:10Z',
            'issued_at':'2026-10-29T13:36:00Z',
            'target':{'start':'2026-10-29T14:00:00Z',
                      'end':'2026-10-29T14:30:00Z'},
            'probabilities':{'down':0.2,'flat':0.6,'up':0.2},
            'direction':'flat',
            'neutral_band_pct':max(0.30 if mode=='daily' else 0.15,
                                   vol20 * (1 if mode=='daily' else math.sqrt(6)) * 0.35 * 100),
            'feature_values':{'vol20':vol20},
        }

    def test_daily_floor_record_is_accepted(self):
        validate(self.record())

    def test_daily_volatility_record_is_accepted(self):
        validate(self.record(vol20=0.018))

    def test_intraday_volatility_record_is_accepted(self):
        validate(self.record(mode='intraday',vol20=0.012))

    def test_unknown_historical_policy_is_not_retroactively_interpreted(self):
        r=self.record()
        r['policy_revision']='legacy'
        r['neutral_band_pct']=0.9
        validate(r)

    def test_changed_band_cannot_relabel_a_frozen_policy_record(self):
        r=self.record(vol20=0.018)
        r['neutral_band_pct'] += 0.2  # Synthetic adversarial alteration.
        with self.assertRaisesRegex(ValueError,'neutral_band_policy_mismatch'):
            validate(r)

    def test_missing_feature_cannot_bypass_known_policy(self):
        r=self.record()
        r.pop('feature_values')
        with self.assertRaisesRegex(ValueError,'missing_frozen_band_feature'):
            validate(r)

if __name__=='__main__':
    unittest.main()
