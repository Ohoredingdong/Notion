"""Offline source-window, row-binding and independent numeric regressions."""
import copy
import hashlib
import json
import unittest
from datetime import datetime, timezone
from statistics import mean

import pandas as pd

import stock_technical_evidence as proof
import update_stock_decisions as producer
from market_data_utils import exchange_calendar
from stock_price_evidence import response_identity

NOW = datetime(2026, 11, 6, 11, tzinfo=timezone.utc)


def source(symbol='AAPL', market='US', end='2026-11-05', kind='EQUITY'):
    currency = 'USD' if market == 'US' else 'KRW'
    exchange = {'^KS11':'KSC', '^KQ11':'KOE', 'SPY':'PCX'}.get(symbol, 'NMS' if market == 'US' else 'KOE' if symbol.endswith('.KQ') else 'KSC')
    meta = {'symbol':symbol, 'currency':currency, 'instrumentType':kind,
            'exchangeName':exchange,
            'exchangeTimezoneName':'America/New_York' if market == 'US' else 'Asia/Seoul'}
    identity = response_identity(meta, symbol, market, currency, kind)
    return {**identity, 'expected_session':end, 'latest_completed_session':end,
            'selected_attempt':1, 'collection_attempts':1, 'stale_retry_attempted':False,
            'attempts':[{'request':{'period':'1y'}, 'received_at':'2026-11-06T10:00:00+00:00',
                         'latest_completed_session':end, 'status':'verified_response'}],
            'basis':'provider_close_auto_adjust_false'}


def inputs(count=100, *, market='US', symbol='AAPL'):
    end = '2026-11-05' if market == 'US' else '2026-11-06'
    dates = [str(day.date()) for day in exchange_calendar(market, 2026).sessions_in_range('2025-01-02', end)][-count:]
    bars = []
    benchmark = []
    for i, day in enumerate(dates):
        close = 100 + i*.1 + (i % 7)*.01
        bars.append({'date':day, 'open':close-.1, 'high':close+2, 'low':close-2,
                     'close':close, 'volume':1000+i*7, 'split':0})
        benchmark.append({'date':day, 'open':100, 'high':200, 'low':90,
                          'close':100+i*.06, 'volume':100000, 'split':0})
    bench = 'SPY' if market == 'US' else '^KQ11' if symbol.endswith('.KQ') else '^KS11'
    return (proof.ObservedBars(bars, source(symbol,market,end)),
            proof.ObservedBars(benchmark,source(bench,market,end,'ETF' if market == 'US' else 'INDEX')))


def row_for(bars, benchmark, market='US'):
    s = bars.source_evidence
    return producer.clean({'symbol':s['provider_symbol'].removesuffix('.KS').removesuffix('.KQ'),
                           'source_symbol':s['provider_symbol'], 'market':market, 'currency':s['currency'],
                           'price':bars[-1]['close'] if bars else None,
                           'price_session':bars[-1]['date'] if bars else None,
                           'expected_session':{'date':s['expected_session']},
                           'price_source':s, 'technical':producer.technical(bars,benchmark,market)})


def mutate_block(block, mutate):
    rows = json.loads(block['rows_json']); mutate(rows)
    block['rows_json'] = json.dumps(rows, separators=(',', ':'), allow_nan=False)
    block['rows_sha256'] = hashlib.sha256(block['rows_json'].encode()).hexdigest()


class TechnicalEvidenceTests(unittest.TestCase):
    def test_full_ohlcv_recalculation_survives_outer_serializer(self):
        row = row_for(*inputs())
        result = proof.validate_technical_evidence(row, NOW)
        self.assertEqual(result['status'], 'verified', result['errors'])
        self.assertEqual(result['coverage']['numeric_fields'], 14)
        self.assertEqual(result['coverage']['benchmark_stored_sessions'], 21)
        self.assertEqual(result['errors'], [])

    def test_all_fourteen_numeric_values_are_independently_checked(self):
        row = row_for(*inputs())
        for field in proof.METRICS:
            changed = copy.deepcopy(row)
            value = changed['technical'][field]
            changed['technical'][field] = 999 if value is None else value+1
            result = proof.validate_technical_evidence(changed,NOW)
            self.assertTrue(any(e.get('field') == field for e in result['errors']), field)

    def test_raw_peak_and_range_change_is_caught_after_a_resealed_hash(self):
        row = row_for(*inputs())
        mutate_block(row['technical']['evidence']['stock'], lambda rows: rows[-2].__setitem__(2,999))
        fields = {e.get('field') for e in proof.validate_technical_evidence(row,NOW)['errors']}
        self.assertIn('atr14', fields)
        self.assertIn('prior_high20', fields)
        self.assertIn('resistance_1y', fields)

    def test_modified_input_bytes_without_new_hash_are_rejected(self):
        row = row_for(*inputs())
        row['technical']['evidence']['stock']['rows_json'] += ' '
        issues = {e['issue'] for e in proof.validate_technical_evidence(row,NOW)['errors']}
        self.assertIn('stock_rows_digest_mismatch',issues)

    def test_changed_benchmark_closes_change_relative_return(self):
        row = row_for(*inputs())
        mutate_block(row['technical']['evidence']['benchmark'],lambda rows: rows[-1].__setitem__(1,999))
        self.assertIn('relative20_pp',{e.get('field') for e in proof.validate_technical_evidence(row,NOW)['errors']})

    def test_missing_benchmark_endpoint_is_withheld(self):
        bars, bench = inputs()
        bench = proof.ObservedBars(bench[:-1],bench.source_evidence)
        row = row_for(bars,bench)
        self.assertIsNone(row['technical']['relative20_pp'])
        self.assertEqual(proof.validate_technical_evidence(row,NOW)['status'],'verified')
        row['technical']['relative20_pp'] = 1
        self.assertTrue(proof.validate_technical_evidence(row,NOW)['errors'])

    def test_benchmark_internal_missing_session_cannot_pass_as_complete(self):
        bars, bench = inputs()
        del bench[-10]
        row = row_for(bars,bench)
        issues = {e['issue'] for e in proof.validate_technical_evidence(row,NOW)['errors']}
        self.assertIn('benchmark_comparison_sessions_missing',issues)

    def test_new_listing_preserves_all_real_bars_and_checks_numeric_withholding(self):
        row = row_for(*inputs(20,market='KR',symbol='950260.KQ'),market='KR')
        result = proof.validate_technical_evidence(row,NOW)
        self.assertEqual(result['status'],'verified_withheld',result['errors'])
        self.assertEqual(result['coverage']['stock_stored_sessions'],20)
        row['technical']['support10'] = 100
        self.assertTrue(proof.validate_technical_evidence(row,NOW)['errors'])

    def test_recent_stock_session_gap_requires_withheld_status(self):
        bars, bench = inputs()
        del bars[-10]
        row = row_for(bars,bench)
        result = proof.validate_technical_evidence(row,NOW)
        self.assertEqual(result['status'],'verified_withheld',result['errors'])
        row['technical']['status'] = 'ok'
        self.assertIn('technical_eligibility_mismatch',{e['issue'] for e in proof.validate_technical_evidence(row,NOW)['errors']})

    def test_other_issuer_market_or_quote_cannot_reuse_evidence(self):
        row = row_for(*inputs())
        for key,value in (('source_symbol','MSFT'),('market','KR'),('currency','KRW'),
                          ('price',1),('price_session','2026-11-04')):
            changed = copy.deepcopy(row); changed[key] = value
            self.assertTrue(proof.validate_technical_evidence(changed,NOW)['errors'],key)

    def test_other_benchmark_identity_is_rejected_even_with_same_prices(self):
        row = row_for(*inputs())
        row['technical']['benchmark_symbol'] = '^KS11'
        self.assertTrue(proof.validate_technical_evidence(row,NOW)['errors'])

    def test_future_source_time_and_uncompleted_cutoff_are_rejected(self):
        row = row_for(*inputs())
        row['technical']['evidence']['stock']['source']['attempts'][0]['received_at'] = '2099-01-01T00:00:00+00:00'
        self.assertTrue(proof.validate_technical_evidence(row,NOW)['errors'])
        row = row_for(*inputs())
        row['expected_session']['date'] = '2026-11-06'
        row['technical']['evidence']['stock']['source']['expected_session'] = '2026-11-06'
        self.assertIn('stock_uncompleted_cutoff',{e['issue'] for e in proof.validate_technical_evidence(row,NOW)['errors']})

    def test_nonpositive_risk_and_reward_remain_null(self):
        for close in (99,100,120):
            bars,bench = inputs()
            for item in bars:
                item.update(open=103,high=110,low=100,close=103)
            bars[-1].update(open=close,high=close+1,low=close-1,close=close)
            row = row_for(bars,bench)
            self.assertIsNone(row['technical']['reward_risk'])
            self.assertEqual(proof.validate_technical_evidence(row,NOW)['status'],'verified')
            row['technical']['reward_risk'] = 0
            self.assertTrue(proof.validate_technical_evidence(row,NOW)['errors'])

    def test_tiny_real_denominator_uses_full_precision_inputs(self):
        bars,bench = inputs()
        for item in bars:
            item.update(open=60,high=82.86000061035156,low=59.45000076293945,close=60)
        bars[-1].update(open=59.470001220703125,close=59.470001220703125)
        row = row_for(bars,bench)
        self.assertEqual(row['technical']['reward_risk'],1169.47320237)
        self.assertEqual(proof.validate_technical_evidence(row,NOW)['status'],'verified')
        self.assertIn('59.470001220703125',row['technical']['evidence']['stock']['rows_json'])

    def test_maximum_window_stays_small_without_changing_extrema(self):
        bars,bench = inputs(300)
        row = row_for(bars,bench)
        e = row['technical']['evidence']
        self.assertEqual(e['stock']['stored_count'],254)
        self.assertEqual(e['stock']['original_count'],300)
        self.assertLess(len(json.dumps(e)),40000)
        self.assertEqual(proof.validate_technical_evidence(row,NOW)['status'],'verified')

    def test_bars_from_preserves_provenance_without_an_extra_request(self):
        bars,bench = inputs()
        frame = pd.DataFrame([{'Open':r['open'],'High':r['high'],'Low':r['low'],'Close':r['close'],
                               'Volume':r['volume'],'Stock Splits':r['split']} for r in bars],
                             index=pd.to_datetime([r['date'] for r in bars]))
        result = producer.bars_from(frame,{'date':'2026-11-05'},source_evidence=bars.source_evidence)
        self.assertIsInstance(result,list)
        self.assertEqual(result,bars)
        self.assertEqual(result.source_evidence,bars.source_evidence)
        self.assertEqual(proof.validate_technical_evidence(row_for(result,bench),NOW)['status'],'verified')

    def test_bad_date_and_duplicate_dates_fail_closed(self):
        for mutate in (lambda rows: rows[-2].__setitem__(0,rows[-1][0]),
                       lambda rows: rows[-2].__setitem__(0,'not-a-date'),
                       lambda rows: rows[-2].__setitem__(0,None)):
            row=row_for(*inputs()); mutate_block(row['technical']['evidence']['stock'],mutate)
            self.assertEqual(proof.validate_technical_evidence(row,NOW)['status'],'failed')

    def test_turnover_uses_actual_prices_and_volumes_when_published(self):
        bars,bench = inputs(); row=row_for(bars,bench)
        row['liquidity']={'avg_turnover20':round(mean(r['close']*r['volume'] for r in bars[-20:]),8)}
        self.assertEqual(proof.validate_technical_evidence(row,NOW)['status'],'verified')
        row['liquidity']['avg_turnover20'] += 1
        self.assertIn('liquidity_value_mismatch',{e['issue'] for e in proof.validate_technical_evidence(row,NOW)['errors']})


if __name__ == '__main__':
    unittest.main()
