"""Offline boundary tests for the public project demo (not a legal certification)."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'radar-public'

class EditionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT / 'stock-radar-editions.json').read_text())
        self.html = (PUBLIC / 'index.html').read_text()
        self.js = (PUBLIC / 'app.js').read_text()

    def test_exact_public_inventory(self):
        self.assertEqual(set(self.contract['public']['deployment_allowlist']), {p.name for p in PUBLIC.iterdir() if p.is_file()})
        self.assertFalse(any(p.is_dir() for p in PUBLIC.iterdir()))

    def test_two_stable_urls_and_real_status(self):
        c=self.contract
        self.assertTrue(c['research']['url'].endswith('/stock-radar-research.html'))
        self.assertTrue(c['public']['url'].endswith('/radar-public/'))
        self.assertFalse(c['research']['private_access_configured'])
        for key in ['commercial_ready','real_market_data_enabled','research_data_included','prediction_service_enabled','payments_enabled','external_requests_enabled']:
            self.assertIs(c['public'][key],False)

    def test_no_research_source_import(self):
        material='\n'.join(p.read_text() for p in PUBLIC.iterdir() if p.is_file()).lower()
        for forbidden in ['stock-value-radar','stock-opportunity-data','stock-forecast','stock-direction-forecast','stock-radar-chart-data','stock-radar-research','yfinance','finance.yahoo','tradingview','tossinvest','nvda']:
            self.assertNotIn(forbidden,material)

    def test_no_data_network_clients(self):
        for forbidden in [r'\bfetch\s*\(',r'\bXMLHttpRequest\b',r'\bWebSocket\b',r'\bEventSource\b',r'\bnavigator\.sendBeacon\b',r'\bimport\s*\(']:
            self.assertIsNone(re.search(forbidden,self.js))
        self.assertIn("connect-src 'none'",self.html)
        self.assertIn("frame-src 'none'",self.html)
        self.assertNotIn('<iframe',self.html)

    def test_external_resources_are_click_only_sources(self):
        self.assertEqual(re.findall(r'<script[^>]+src="([^"]+)',self.html),['app.js?v=editions-1'])
        self.assertEqual(re.findall(r'<link[^>]+href="([^"]+)',self.html),['styles.css?v=editions-1'])
        self.assertEqual(re.findall(r'href="(https:[^"]+)',self.html),['https://dart.fss.or.kr/','https://www.sec.gov/edgar/search/'])
        self.assertIn('rel="noopener noreferrer"',self.html)

    def test_samples_cannot_be_mistaken_for_live(self):
        for label in ['가상 예시','실제 시세·예측 제공 안 함','판매 미개시','비활성화 상태','현재는 시연판']:
            self.assertIn(label,self.html)
        for label in ['DEMO-A','DEMO-B','DEMO-C','시세 미연결']:
            self.assertIn(label,self.js)

    def test_journal_is_separate_and_not_remote(self):
        self.assertIn("const KEY = 'radar-public-demo:journal:v1'",self.js)
        self.assertIn('다른 탭의 기록이 변경',self.js)
        self.assertIn('저장하지 못했습니다',self.js)
        self.assertIn('암호화 저장이 아닙니다',self.html)
        self.assertIn('unsaved_draft',self.js)

    def test_research_wrapper_is_not_fake_auth(self):
        research=(ROOT/'stock-radar-research.html').read_text()
        self.assertIn('웹 접근제어 없음',research)
        self.assertIn('src="./stock-value-radar.html"',research)
        self.assertIn('href="./radar-public/"',research)
        self.assertNotIn('password',research)

if __name__=='__main__':
    unittest.main(verbosity=2)
