"""Deterministic fixtures. Synthetic test numbers never enter published financial data."""
import copy
import json
import unittest
from pathlib import Path
from stock_official_audit import (num, fact, compare, derive, unique, row_key,
 from_sec_json, from_kind, from_release, SourceError)

REC={'url':'https://www.sec.gov/example','sha256':'unit-test-only','fetched_at':'2026-10-19T00:00:00+00:00'}

def widget(**kw):
 d={'symbol':'TEST','filing_period':'2025-12-31','currency':'USD','statement_basis':'연간 연결','revenue':1000000,'revenue_growth':25.0,'operating_income':200000,'operating_margin':20,'net_income':100000,'eps':2,'capex':50000,'fcf':100000}
 d.update(kw);return d

def source(**kw):
 fs={k:fact(v,k,'percent' if k in ('revenue_growth','operating_margin') else 'USD/shares' if k=='eps' else 'USD','2025-12-31',REC,resolution=.01 if k in ('eps','revenue_growth','operating_margin') else 1) for k,v in widget().items() if k in ('revenue','revenue_growth','operating_income','operating_margin','net_income','eps','capex','fcf')}
 for k,v in kw.items():fs[k].update(v)
 return {'facts':fs}

def byfield(row,src):return {r['field']:r for r in compare(row,src)}

class FinancialAuditTests(unittest.TestCase):
 def test_nonfinite_rejected(self):
  for x in (None,True,False,'NaN','Infinity',float('inf')):self.assertIsNone(num(x))
 def test_zero_is_not_missing(self):self.assertEqual(num(0),0)
 def test_parentheses_negative(self):self.assertEqual(num('(1,250.5)'),-1250.5)
 def test_all_same_matches(self):self.assertTrue(all(x['status']=='match' for x in compare(widget(),source())))
 def test_source_missing_never_match(self):self.assertTrue(all(x['status']=='unverified' for x in compare(widget(),None)))
 def test_missing_widget_not_zero(self):self.assertEqual(byfield(widget(revenue=None),source())['revenue']['status'],'widget_missing')
 def test_period_difference_not_assumed_equivalent(self):self.assertEqual(byfield(widget(filing_period='2025-12-30'),source())['revenue']['status'],'period_mismatch')
 def test_currency_difference_not_automatically_converted(self):self.assertEqual(byfield(widget(currency='KRW'),source())['revenue']['status'],'unit_mismatch')
 def test_separate_vs_consolidated(self):self.assertEqual(byfield(widget(statement_basis='연간 별도'),source())['revenue']['status'],'basis_mismatch')
 def test_material_difference(self):self.assertEqual(byfield(widget(revenue=1100000),source())['revenue']['status'],'mismatch')
 def test_delta_sign_and_percentage(self):
  v=byfield(widget(revenue=1100000),source())['revenue'];self.assertEqual(v['difference'],100000);self.assertEqual(v['difference_pct'],10)
 def test_eps_different_is_account_check(self):self.assertEqual(byfield(widget(eps=3),source())['eps']['status'],'account_check')
 def test_net_income_basis_warning(self):self.assertEqual(byfield(widget(net_income=110000),source())['net_income']['status'],'account_check')
 def test_fcf_definition_warning(self):self.assertEqual(byfield(widget(fcf=110000),source())['fcf']['status'],'definition_check')
 def test_zero_reference_no_divide_by_zero(self):self.assertIsNone(byfield(widget(revenue=100),source(revenue={'value':0}))['revenue']['difference_pct'])
 def test_rounding_tolerance_not_percentage_cover(self):
  self.assertEqual(byfield(widget(eps=2.004),source())['eps']['status'],'match')
  self.assertNotEqual(byfield(widget(eps=2.06),source())['eps']['status'],'match')
 def test_ambiguous_values_no_guess(self):self.assertIsNone(unique([{'value':1},{'value':2}]))
 def test_input_fingerprint_changes_with_eps(self):self.assertNotEqual(row_key(widget()),row_key(widget(eps=3)))
 def test_no_cross_period_fcf(self):
  fs={'operating_cash_flow':fact(100,'CFO','USD','2025-12-31',REC),'ppe':fact(20,'PPE','USD','2024-12-31',REC)};derive(fs);self.assertNotIn('fcf',fs)
 def test_kr_missing_intangible_not_assumed_zero(self):
  fs={'operating_cash_flow':fact(100,'CFO','KRW','2025-12-31',REC),'ppe':fact(20,'PPE','KRW','2025-12-31',REC)};derive(fs);self.assertNotIn('fcf',fs)
 def test_kr_fcf_has_components(self):
  fs={'operating_cash_flow':fact(100,'CFO','KRW','2025-12-31',REC),'ppe':fact(-20,'PPE','KRW','2025-12-31',REC),'intangible':fact(-5,'INT','KRW','2025-12-31',REC)};derive(fs);self.assertEqual(fs['fcf']['value'],75);self.assertEqual(fs['capex']['value'],25)
 def sec(self):
  f=lambda v,s,e,acc='0000123-26-000001':{'val':v,'start':s,'end':e,'accn':acc,'form':'10-K','filed':'2026-02-01','fp':'FY'}
  return {'cik':123,'facts':{'us-gaap':{'Revenues':{'units':{'USD':[f(100,'2025-01-01','2025-12-31'),f(80,'2024-01-01','2024-12-31')]}},'OperatingIncomeLoss':{'units':{'USD':[f(20,'2025-01-01','2025-12-31'),f(5,'2025-10-01','2025-12-31')]}},'EarningsPerShareDiluted':{'units':{'USD/shares':[f(2,'2025-01-01','2025-12-31')]}},'NetIncomeLoss':{'units':{'USD':[f(10,'2024-01-01','2024-12-31')]}}}}}
 def test_sec_issuer(self):
  with self.assertRaises(SourceError):from_sec_json(self.sec(),999,'2025-12-31',REC)
 def test_sec_annual_not_quarter(self):
  x=from_sec_json(self.sec(),123,'2025-12-31',REC);self.assertEqual(x['facts']['operating_income']['value'],20)
 def test_sec_no_prior_year_net_income_mix(self):self.assertNotIn('net_income',from_sec_json(self.sec(),123,'2025-12-31',REC)['facts'])
 def test_sec_growth_from_same_filing(self):self.assertEqual(from_sec_json(self.sec(),123,'2025-12-31',REC)['facts']['revenue_growth']['value'],25)
 def test_kind_scope_and_units(self):
  html='<h1>테스트회사</h1><p>2-2. 연결 손익계산서</p><p>2025.01.01 부터 2025.12.31 까지 (단위 : 백만원)</p><table><tr><th>과목</th><th>당기</th><th>전기</th></tr><tr><td>매출액 (주3)</td><td>100</td><td>80</td></tr><tr><td>영업이익</td><td>20</td><td>10</td></tr></table><p>4. 재무제표</p><table><tr><td>매출액</td><td>999</td></tr></table>'
  x=from_kind(html,'2025-12-31',{'aliases':['테스트회사']},REC);self.assertEqual(x['facts']['revenue']['value'],100000000);self.assertEqual(x['facts']['operating_margin']['value'],20)
 def test_kind_wrong_issuer(self):
  with self.assertRaises(SourceError):from_kind('<h1>Other</h1>','2025-12-31',{'aliases':['회사']},REC)
 def test_kind_unknown_units(self):
  with self.assertRaises(SourceError):from_kind('<h1>회사</h1><p>연결손익계산서 2025.01.01 2025.12.31</p><table><tr><td>매출액</td><td>100</td></tr></table>','2025-12-31',{'aliases':['회사']},REC)
 def test_release_annual_column(self):
  html='<h1>Microsoft</h1><p>Income Statements (in millions)</p><table><tr><td>Three Months / Twelve Months Ended June 30 2026 (in millions)</td></tr><tr><td>Total revenue</td><td>30</td><td>25</td><td>100</td><td>80</td></tr><tr><td>Operating income</td><td>5</td><td>4</td><td>20</td><td>15</td></tr></table>'
  x=from_release(html,'2026-06-30',{'aliases':['Microsoft']},REC,{'index':2,'prior_index':3,'period':'2026-06-30'});self.assertEqual(x['facts']['revenue']['value'],100000000)
 def test_no_forecast_probabilities(self):
  fields=compare(widget(),source());self.assertNotIn('probability',json.dumps(fields))

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(FinancialAuditTests)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 Path('stock-audit-unit-tests.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
