import unittest
from scripts import build_stock_decision_guide as g

class GuideTests(unittest.TestCase):
    def row(self):
        return {'name':'테스트','symbol':'T','market':'KR','sector':'반도체 장비','currency':'KRW','history':{'revenue':100,'revenue_growth':20,'operating_income':20,'operating_margin':20,'net_income':10,'cfo':15,'capex':5,'fcf':10,'accounts_receivable':10,'accounts_receivable_growth':35,'inventory':8,'inventory_growth':5,'equity':50,'equity_growth':-5,'roe':20,'quality_flags':[]},'balance':{'net_debt_ebitda':-1,'basis':'test'},'valuation':{'trailing_pe':12,'forward_pe':10,'price_to_book':2,'return_on_equity_pct':20},'forecasts':{'eps_growth_next_fy_pct':15,'eps_revision30_pct':1,'next_fy':{'avg':4}},'targets':{'median':100,'median_gap_pct':25},'business':{'industry':'Semiconductor Equipment & Materials'},'sources':{'profile':'https://example.com/profile','cashflow':'https://example.com/cf','balance':'https://example.com/bs','official':'https://example.com/o','estimates':'https://example.com/e'},'price_session':'2026-10-19'}
    def test_business_sentence(self):
        x=g.business_profile(self.row());self.assertIn('반도체',x['sentence']);self.assertIn('매출은',x['sentence'])
    def test_cash_flags(self):
        x=g.cash_reading(self.row());self.assertTrue(any(i['term'].startswith('FCF') for i in x['items']))
    def test_valuation_pair(self):
        x=g.valuation_reading(self.row(),{'peer_context':{'median':15,'count':5}});self.assertEqual(x['items'][0]['term'],'PER(주가수익비율)');self.assertIn('ROE',x['items'][3]['term'])
    def test_basis_terms(self):
        x=g.basis_checks(self.row(),{'official_comparison':[{'basis':'CFS'}]});self.assertEqual(x[0]['term'],'연결·별도');self.assertIn('실적·예상',[i['term'] for i in x])
    def test_macro_not_deterministic(self):
        macro={'interpretation':{'label':'장기금리 부담','not_causality':'주가 방향 확정 금지'},'indicators':{'us_10y':{'value':5.1},'usdkrw':{'change_20_sessions_pct':2},'fed_policy':{}}}
        x=g.macro_exposure(self.row(),macro);self.assertIn('주가 방향 확정',x['not_causality'])

if __name__=='__main__':unittest.main()
