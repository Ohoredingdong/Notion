import unittest
from worker import LiveApp, TossReadOnly, REST_READ_PATHS, make_webapp
from core import quote_from_trade

class SecurityTests(unittest.TestCase):
    def test_only_market_price_path_allowlisted(self):
        self.assertEqual(REST_READ_PATHS,{"/api/v1/prices"})
        self.assertFalse(any("order" in v or "account" in v or "holdings" in v for v in REST_READ_PATHS))
    def test_no_credentials_never_connects(self):
        obj=LiveApp([{"symbol":"005930","market":"KR","name":"가상 테스트","currency":"KRW"}],{})
        self.assertFalse(obj.ready())
        self.assertEqual(obj.source_state,"not_configured")
    def test_readonly_service_has_no_order_routes(self):
        obj=LiveApp([{"symbol":"005930","market":"KR","name":"가상 테스트","currency":"KRW"}],{})
        routes=[r.resource.canonical for r in make_webapp(obj).router.routes()]
        self.assertNotIn("/api/v1/orders",routes)
        self.assertNotIn("/api/v1/accounts",routes)
        self.assertIn("/api/status",routes)
    def test_invalid_market_frame_cannot_notify(self):
        self.assertIsNone(quote_from_trade({"type":"message","topic":"personal:order:42","data":{"price":"123"}}))

if __name__=="__main__":unittest.main()
