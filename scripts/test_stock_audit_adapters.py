"""Synthetic parser regression fixtures; never a financial reference data source."""
import json
import unittest
from pathlib import Path
import stock_audit_adapters as b
import stock_official_audit as a
from test_stock_official_audit import REC, widget, source

class TableAdapterTests(unittest.TestCase):
 def test_split_parentheses(self):self.assertEqual(b.numeric_cells(['$','(10',')','','20','']),[-10,20])
 def test_negative_zero_positive_and_krw(self):self.assertEqual(b.numeric_cells(['(8,000)','—','60,378원']),[-8000,0,60378])
 def test_blank_does_not_shift_to_zero(self):self.assertEqual(b.numeric_cells(['','','2','']),[2])
 def test_micro_difference_not_urgent_alarm(self):
  x=b.compare(widget(revenue=1000000.006),source());self.assertEqual(x[0]['status'],'match')
 def test_trivial_large_scale_delta_preserved(self):
  r=widget(revenue=2208138388970);s=source(revenue={'value':2208138388720,'resolution':1})
  x=b.compare(r,s)[0];self.assertEqual(x['status'],'minor_difference');self.assertEqual(x['difference'],250)
 def test_material_difference_still_alarm(self):self.assertEqual(b.compare(widget(revenue=2000000),source())[0]['status'],'mismatch')
 def kind(self):
  return '<h1>회사</h1><p>연결포괄손익계산서</p><table><tr><td>제78기 2025년 01월 01일부터 2025년 12월 31일까지</td></tr><tr><td>(단위: 백만원)</td></tr></table><table><tr><td>과목</td><td>주석</td><td>당기</td><td>전기</td></tr><tr><td>매출액</td><td>4,24,31</td><td>100</td><td>80</td></tr><tr><td>영업이익</td><td>7</td><td>20</td><td>10</td></tr><tr><td>당기순이익의 귀속</td><td></td></tr><tr><td>지배기업의 소유주지분</td><td></td><td>10</td><td>8</td></tr><tr><td>총포괄이익의 귀속</td><td></td></tr><tr><td>지배기업의 소유주지분</td><td></td><td>12</td><td>9</td></tr><tr><td>희석주당순이익</td><td></td><td>2원</td><td>1원</td></tr></table>'
 def test_note_number_not_revenue(self):
  x=b.from_kind(self.kind(),'2025-12-31',{'aliases':['회사']},REC);self.assertEqual(x['facts']['revenue']['value'],100000000)
 def test_comprehensive_not_net_income(self):
  x=b.from_kind(self.kind(),'2025-12-31',{'aliases':['회사']},REC);self.assertEqual(x['facts']['net_income']['value'],10000000)
 def test_eps_unit_krw_not_millions(self):
  x=b.from_kind(self.kind(),'2025-12-31',{'aliases':['회사']},REC);self.assertEqual(x['facts']['eps']['value'],2)
 def test_bad_issuer(self):
  with self.assertRaises(a.SourceError):b.from_kind(self.kind(),'2025-12-31',{'aliases':['다른회사']},REC)
 def test_bad_year(self):
  with self.assertRaises(a.SourceError):b.from_kind(self.kind(),'2026-12-31',{'aliases':['회사']},REC)
 def release(self,extra=''):
  return '<h1>Microsoft</h1><table><tr><td>Income Statements in millions; Three Months and Twelve Months Ended June 30 2026</td></tr><tr><td>Total revenue</td><td>30</td><td>25</td><td>100</td><td>80</td></tr><tr><td>Total cost of revenue</td><td>5</td><td>4</td><td>20</td><td>15</td></tr><tr><td>Operating income</td><td>4</td><td>3</td><td>10</td><td>8</td></tr></table>'+extra
 def test_full_annual(self):
  x=b.from_release(self.release(),'2026-06-30',{'aliases':['Microsoft']},REC,{'index':2,'prior_index':3,'period':'2026-06-30'});self.assertEqual(x['facts']['revenue']['value'],100000000)
 def test_segment_excluded(self):
  extra='<table><tr><td>Segment Results in millions; Twelve Months Ended June 30 2026</td></tr><tr><td>Revenue</td><td>10</td><td>8</td><td>30</td><td>20</td></tr><tr><td>Operating income</td><td>1</td><td>1</td><td>3</td><td>2</td></tr></table>'
  x=b.from_release(self.release(extra),'2026-06-30',{'aliases':['Microsoft']},REC,{'index':2,'prior_index':3,'period':'2026-06-30'});self.assertEqual(x['facts']['revenue']['value'],100000000)
 def test_non_gaap_not_substituted(self):
  with self.assertRaises(a.SourceError):b.from_release(self.release().replace('Income Statements','Non-GAAP As Adjusted Income Statements'),'2026-06-30',{'aliases':['Microsoft']},REC,{'index':2,'prior_index':3,'period':'2026-06-30'})
 def test_ambiguous_duplicate_not_used(self):
  html=self.release()+self.release().replace('<td>100</td>','<td>200</td>')
  x=b.from_release(html,'2026-06-30',{'aliases':['Microsoft']},REC,{'index':2,'prior_index':3,'period':'2026-06-30'});self.assertNotIn('revenue',x['facts'])

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TableAdapterTests))
 Path('stock-audit-adapter-tests.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
