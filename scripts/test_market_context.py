import unittest
from unittest.mock import patch
from scripts import update_market_context as m
from scripts import run_market_context as runner

class MarketContextTests(unittest.TestCase):
    def test_fed(self):
        html='''<h4>2026</h4><table><tr><th>Date</th><th>Increase</th><th>Decrease</th><th>Level (%)</th></tr><tr><td>September 17</td><td>25</td><td>0</td><td>3.75-4.00</td></tr></table>'''
        x=runner.parse_fed_funds(html)
        self.assertEqual(x['direction'],'인상');self.assertEqual(x['low'],3.75);self.assertEqual(x['date'],'2026-09-17')
    def test_fed_cross_year(self):
        html='''<h4>2026</h4><table><tr><td>September 17</td><td>25</td><td>0</td><td>3.75-4.00</td></tr></table><h4>2025</h4><table><tr><td>December 11</td><td>0</td><td>25</td><td>3.50-3.75</td></tr></table>'''
        x=runner.parse_fed_funds(html)
        self.assertEqual(x['date'],'2026-09-17');self.assertEqual(x['direction'],'인상')
    def test_bok(self):
        html='<div>통화정책방향 (2026.8.27) 금융통화위원회는 기준금리를 2.75%에서 3.00%로 0.25%p 상향 조정 한국은행기준금리 3.00%</div>'
        x=m.parse_bok(html);self.assertEqual(x['value'],3.0);self.assertEqual(x['direction'],'인상')
    def test_fed_latest_meeting_can_be_hold_after_last_rate_change(self):
        rate_html='''<h4>2026</h4><table><tr><th>Date</th><th>Increase</th><th>Decrease</th><th>Level (%)</th></tr><tr><td>September 17</td><td>25</td><td>0</td><td>3.75-4.00</td></tr></table>'''
        calendar_html='''<a href="/newsevents/pressreleases/monetary20260916a.htm">Sep statement</a><a href="/newsevents/pressreleases/monetary20261028a.htm">Oct statement</a>'''
        with patch.object(m,'fetch',side_effect=[rate_html.encode(),calendar_html.encode()]):
            x=m.collect_fed_policy()
        self.assertEqual(x['date'],'2026-10-28')
        self.assertEqual(x['rate_effective_date'],'2026-09-17')
        self.assertEqual(x['direction'],'유지')
        self.assertEqual((x['low'],x['high']),(3.75,4.0))

    def test_bok_latest_meeting_and_last_change_are_separate(self):
        rate_html='''<table><tr><td>2026</td><td>08월 27일</td><td>3.00</td></tr><tr><td>2026</td><td>07월 16일</td><td>2.75</td></tr></table>'''
        meeting_html='''<div>통화정책방향(2026.08.27)</div><div>통화정책방향(2026.10.22)</div>'''
        with patch.object(m,'fetch',side_effect=[rate_html.encode(),meeting_html.encode()]):
            x=m.collect_bok_policy()
        self.assertEqual(x['date'],'2026-10-22')
        self.assertEqual(x['rate_change_date'],'2026-08-27')
        self.assertEqual(x['value'],3.0)
        self.assertEqual(x['direction'],'유지')
        self.assertEqual(x['change_pct_point'],0.0)

    def test_treasury(self):
        xml='''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"><entry><content><m:properties><d:NEW_DATE>2026-10-16T00:00:00</d:NEW_DATE><d:BC_10YEAR>5.09</d:BC_10YEAR></m:properties></content></entry><entry><content><m:properties><d:NEW_DATE>2026-10-19T00:00:00</d:NEW_DATE><d:BC_10YEAR>5.15</d:BC_10YEAR></m:properties></content></entry></feed>'''
        x=m.parse_treasury(xml);self.assertEqual(x['value'],5.15);self.assertAlmostEqual(x['change_1d_pp'],.06)
    def test_fred(self):
        body=b'DATE,CPIAUCSL\n2025-09-01,300\n2026-08-01,309\n2026-09-01,312\n'
        x=m.fred_cpi(body);self.assertAlmostEqual(x['yoy_pct'],4.0)
    def test_interpretation_not_forecast(self):
        i={'fed_policy':{'direction':'인상'},'us_10y':{'value':5.15,'change_20_sessions_pp':.3},'us_cpi':{},'us_unemployment':{},'usdkrw':{'change_20_sessions_pct':2}}
        x=m.interpretation(i);self.assertIn('장기금리',x['label']);self.assertIn('주가 방향을 확정하지',x['not_causality'])

if __name__=='__main__':unittest.main()
