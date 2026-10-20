import json,unittest
from pathlib import Path
import finalize_stock_opportunities as f

class FilingTests(unittest.TestCase):
 def fixture(self):
  def row(label,*v):return '<tr><td>'+label+'</td>'+''.join('<td>'+str(x)+'</td>' for x in v)+'</tr>'
  period='<p>제30기 2025.01.01 부터 2025.12.31 까지 (단위 : 원)</p>'
  return '<html><body><p>리노공업</p><p>당사는 연결재무제표 작성대상에 해당하지 않습니다.</p><p>4-2. 포괄손익계산서</p>'+period+'<table>'+row('매출액',300,200,100)+row('영업이익',90,60,30)+row('당기순이익',60,50,20)+row('희석주당이익 (단위 : 원)',2,1,1)+'</table><p>4-3. 자본변동표</p><table>'+row('당기순이익',999,999,999)+'</table><p>4-4. 현금흐름표</p>'+period+'<table>'+row('영업활동현금흐름',100,90,80)+row('유형자산의 취득','(20)','(10)','(5)')+row('무형자산의 취득','(5)','(5)','(5)')+'</table><p>5. 재무제표 주석</p></body></html>'
 def test_scope_and_capex(self):
  d=f.parse_leeno(self.fixture(),'2025-12-31');self.assertEqual(d['fcf'],75);self.assertEqual(d['net_income'],60);self.assertEqual(d['eps'],2)
 def test_year(self):
  with self.assertRaises(ValueError):f.parse_leeno(self.fixture(),'2026-12-31')
 def test_issuer(self):
  with self.assertRaises(ValueError):f.parse_leeno(self.fixture().replace('리노공업','타사'),'2025-12-31')
 def test_consolidation(self):
  with self.assertRaises(ValueError):f.parse_leeno(self.fixture().replace('연결재무제표 작성대상에 해당하지 않습니다.','연결재무제표 작성대상입니다.'),'2025-12-31')
 def test_missing_unit(self):
  with self.assertRaises(ValueError):f.parse_leeno(self.fixture().replace('단위 : 원','단위 미상'),'2025-12-31')
 def test_missing_cash(self):
  with self.assertRaises(ValueError):f.parse_leeno(self.fixture().replace('영업활동현금흐름','알 수 없음'),'2025-12-31')
 def test_material_mismatch(self):
  x=next(x for x in f.reconcile({'eps':20},{'eps':2}) if x['field']=='eps');self.assertEqual(x['status'],'mismatch');self.assertFalse(x['accepted'])
 def test_rounding_visible(self):
  x=next(x for x in f.reconcile({'revenue':1e11+10},{'revenue':1e11}) if x['field']=='revenue');self.assertEqual(x['status'],'rounding_match');self.assertEqual(x['difference'],10)
 def test_eps_tolerance(self):
  x=next(x for x in f.reconcile({'eps':2.01},{'eps':2}) if x['field']=='eps');self.assertEqual(x['status'],'mismatch')

if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FilingTests))
 Path('stock-opportunity-filing-tests.json').write_text(json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'passed':r.wasSuccessful()},indent=2)+'\n')
 raise SystemExit(0 if r.wasSuccessful() else 1)
