"""Synthetic unit fixtures only; never represent live issuer facts."""
import copy
from datetime import date
import json
import unittest
from stock_corporate_actions import (analyze, DartIndex, collect_sec, sec_items, number, official_url)

URL='https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261117000001'
def event(kind, **facts):
    return {'event_id':'synthetic-1','symbol':'TEST','kind':kind,'filing_status':'current','facts':facts,
            'evidence':{k:{'url':URL,'locator':'synthetic unit fixture, not actual filing','symbol':'TEST'} for k in facts}}
def contract(**updates):
    facts=dict(contract_amount=1000,prior_annual_revenue=2000,contract_currency='KRW',revenue_currency='KRW',
               contract_entity_basis='same_entity',revenue_entity_basis='same_entity',start_date='2026-01-01',end_date='2026-12-31',
               event_status='signed',profitability_assessment='undisclosed',payment_terms='milestones',termination_conditions='conditional')
    facts.update(updates);return event('contract',**facts)
def cb(**updates):
    facts=dict(instrument_type='CB',outstanding_conversion_principal=10000,current_conversion_price=100,
               adjustment_floor_price=70,initial_price=100,shares_outstanding_ex_treasury=1000,principal_currency='KRW',
               conversion_price_currency='KRW',exercise_start='2026-01-01',exercise_end='2027-01-01',balance_as_of='2026-11-17',
               market_price=150,market_price_currency='KRW',price_as_of='2026-11-17')
    facts.update(updates);return event('convertible',**facts)
def buyback(**updates):
    facts=dict(acquisition_completed_shares=100,cancellation_completed_shares=100,stated_purpose='shareholder return',
               acquisition_status='completed',cancellation_status='completed',same_program_confirmed=True)
    facts.update(updates);return event('buyback',**facts)

class AnalysisTests(unittest.TestCase):
    def test_numeric_missing_and_boolean(self):
        for x in (None,True,'NaN','Infinity','-'):self.assertIsNone(number(x))
        self.assertEqual(number('1,000'),1000)
    def test_url_security(self):
        for x in ('http://dart.fss.or.kr/x','https://dart.fss.or.kr.evil/x','https://dart.fss.or.kr/x?crtfc_key=secret','https://u:p@www.sec.gov/x'):
            self.assertFalse(official_url(x))
    def test_contract_scale_not_buy(self):
        r=analyze(contract());self.assertEqual(r['metrics']['revenue_ratio_pct'],50);self.assertFalse(r['buy_signal']);self.assertIsNone(r['metrics']['deposit_amount'])
    def test_currency_mismatch(self):
        self.assertIsNone(analyze(contract(revenue_currency='USD'))['metrics']['revenue_ratio_pct'])
    def test_basis_mismatch(self):
        self.assertIsNone(analyze(contract(revenue_entity_basis='subsidiary'))['metrics']['revenue_ratio_pct'])
    def test_period_invalid(self):
        r=analyze(contract(end_date='2025-01-01'));self.assertIsNone(r['metrics']['annualized_scale_pct']);self.assertEqual(r['status'],'partial')
    def test_missing_source_not_zero(self):
        e=contract();e['evidence'].pop('contract_amount');r=analyze(e);self.assertIsNone(r['metrics']['contract_amount'])
    def test_issuer_evidence_mismatch(self):
        e=contract();e['evidence']['contract_amount']['symbol']='OTHER';self.assertIsNone(analyze(e)['metrics']['contract_amount'])
    def test_terminated_contract(self):
        self.assertEqual(analyze(contract(event_status='terminated'))['assessment'],'종료/철회')
    def test_cb_dilution_denominators(self):
        r=analyze(cb(),date(2026,11,17));m=r['metrics'];self.assertEqual(m['new_to_existing_pct'],10);self.assertAlmostEqual(m['fully_diluted_new_pct'],100/1100*100);self.assertIsNone(r['conversion_probability']);self.assertIsNone(r['crash_probability'])
    def test_lower_floor_more_dilution(self):
        a=analyze(cb(),date(2026,11,17));b=analyze(cb(adjustment_floor_price=50),date(2026,11,17));self.assertGreater(b['metrics']['potential_new_shares_floor'],a['metrics']['potential_new_shares_floor'])
    def test_expired_period(self):
        self.assertFalse(analyze(cb(exercise_end='2026-10-01'),date(2026,11,17))['metrics']['exercise_window_open'])
    def test_future_balance(self):
        self.assertIsNone(analyze(cb(balance_as_of='2026-11-18'),date(2026,11,17))['metrics']['potential_new_shares_current'])
    def test_stale_quote_no_premium(self):
        self.assertIsNone(analyze(cb(price_as_of='2026-11-16'),date(2026,11,17))['metrics']['price_premium_pct'])
    def test_invalid_floor(self):
        self.assertIsNone(analyze(cb(adjustment_floor_price=101),date(2026,11,17))['metrics']['potential_new_shares_floor'])
    def test_bw_uses_rights_not_debt(self):
        e=cb(instrument_type='BW',outstanding_exercise_amount=5000,current_exercise_price=100,outstanding_conversion_principal=0)
        self.assertEqual(analyze(e,date(2026,11,17))['metrics']['potential_new_shares_current'],50)
    def test_buyback_completion(self):
        self.assertTrue(analyze(buyback())['acquired_and_cancelled_confirmed'])
        for e in (buyback(cancellation_status='planned'),buyback(same_program_confirmed=False),buyback(cancellation_completed_shares=101)):
            self.assertFalse(analyze(e)['acquired_and_cancelled_confirmed'])
    def test_superseded_blocks_badge(self):
        e=buyback();e['filing_status']='superseded';self.assertFalse(analyze(e)['acquired_and_cancelled_confirmed'])
    def test_ma_no_guessed_purpose(self):
        r=analyze(event('reorganization'));self.assertIsNone(r['inferred_hidden_purpose']);self.assertEqual(r['status'],'partial');self.assertFalse(r['purpose_inference'])

class CollectorTests(unittest.TestCase):
    def row(self,n):return {'corp_code':'00000001','rcept_no':f'20261117{n:06d}','report_nm':'정정 보고서' if n==1 else '보고서','rcept_dt':'20261117'}
    def test_dart_pagination_complete_not_semantics(self):
        calls=[]
        def request(url):
            calls.append(url);return {'status':'000','total_count':2,'list':[self.row(len(calls))]}
        r=DartIndex('SECRET',request).collect('00000001','20260101','20261117')
        self.assertTrue(r['coverage']['complete']);self.assertFalse(r['coverage']['semantic_complete']);self.assertEqual(len(calls),2)
        self.assertTrue(r['items'][0]['amendment']);self.assertNotIn('SECRET',json.dumps(r))
    def test_dart_unauthorized_no_zero_claim(self):
        r=DartIndex('').collect('00000001','20260101','20261117');self.assertFalse(r['coverage']['complete']);self.assertEqual(r['status'],'unavailable')
    def test_dart_error_sanitized(self):
        def request(url):raise RuntimeError(url)
        r=DartIndex('SECRET',request).collect('00000001','20260101','20261117');self.assertNotIn('SECRET',json.dumps(r));self.assertFalse(r['coverage']['complete'])
    def test_dart_zero_result_is_index_only(self):
        r=DartIndex('x',lambda u:{'status':'013'}).collect('00000001','20260101','20261117');self.assertTrue(r['coverage']['complete']);self.assertFalse(r['coverage']['semantic_complete'])
    def test_dart_page_limit_partial(self):
        r=DartIndex('x',lambda u:{'status':'000','total_count':2,'list':[self.row(1)]},1).collect('00000001','20260101','20261117');self.assertFalse(r['coverage']['complete'])
    def test_dart_wrong_issuer(self):
        row=self.row(1);row['corp_code']='00000002'
        r=DartIndex('x',lambda u:{'status':'000','total_count':1,'list':[row]}).collect('00000001','20260101','20261117');self.assertEqual(r['items'],[]);self.assertFalse(r['coverage']['complete'])
    def test_dart_mutating_total(self):
        calls=[]
        def request(u):
            calls.append(u);return {'status':'000','total_count':len(calls)+1,'list':[self.row(len(calls))]}
        r=DartIndex('x',request).collect('00000001','20260101','20261117');self.assertEqual(r['error'],'index_changed_during_pagination')
    def test_sec_column_integrity(self):
        with self.assertRaises(ValueError):sec_items({'accessionNumber':['a'],'filingDate':[],'form':[],'primaryDocument':[]})
    def test_sec_complete_history(self):
        cols={'accessionNumber':['0000000001-26-000001'],'filingDate':['2026-11-17'],'form':['8-K/A'],'primaryDocument':['a.htm']}
        r=collect_sec('1','Research fixture@synthetic.test',lambda *a:{'cik':1,'filings':{'recent':cols,'files':[]}})
        self.assertTrue(r['coverage']['complete']);self.assertFalse(r['coverage']['semantic_complete']);self.assertTrue(r['items'][0]['amendment'])
    def test_sec_no_unidentified_client(self):
        for ua in ('bot','Research contact@example.org','x@y.com'):
            with self.assertRaises(ValueError):collect_sec('1',ua)
    def test_sec_issuer_mismatch(self):
        r=collect_sec('1','Research fixture@synthetic.test',lambda *a:{'cik':2});self.assertFalse(r['coverage']['complete'])
if __name__=='__main__':unittest.main()
