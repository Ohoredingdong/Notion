"""Pure parsing & failure tests. Synthetic strings exist ONLY in the test, never a published result."""
from __future__ import annotations
import json
import unittest
from scripts import build_stock_universe_catalog as m


class UniverseCatalogTests(unittest.TestCase):
    def test_nasdaq_filters_etfs_test_issues_and_warrants(self):
        raw = ("Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n"
               "AAPL|Apple Inc.|Q|N|N|100|N|N\n"
               "AAAA|Test Company|Q|Y|N|100|N|N\n"
               "QQQ|Invesco Nasdaq 100 ETF|Q|N|N|100|Y|N\n"
               "TESTW|New Company Warrants|Q|N|N|100|N|N\n"
               "MSFT|Microsoft Corporation|Q|N|N|100|N|N\n").encode()
        rows = m.nasdaq_rows(raw)
        self.assertEqual([x["symbol"] for x in rows], ["AAPL", "MSFT"])
        self.assertTrue(all(x["exchange"] == "NASDAQ" for x in rows))

    def test_other_exchange_exchange_filter(self):
        raw = ("ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n"
               "FN|Fabrinet|N|FN|N|100|N|FN\n"
               "VTI|ETF Fund|P|VTI|Y|100|N|VTI\n"
               "ZZZ|Test|?|ZZZ|N|100|N|ZZZ\n").encode()
        records = m.nasdaq_rows(raw, other=True)
        self.assertEqual([x["symbol"] for x in records], ["FN"])

    def test_kind_encoding_and_market(self):
        html = ('<html><table><tr><th>회사명</th><th>종목코드</th></tr>'
                '<tr><td>삼성전자</td><td>5930</td></tr>'
                '<tr><td>카카오</td><td>035720</td></tr></table></html>').encode("euc-kr")
        got = m.kind_rows(html, "KOSPI")
        self.assertEqual(got[0]["symbol"], "005930")
        self.assertEqual(got[0]["name"], "삼성전자")
        self.assertEqual(len(got), 2)

    def test_bad_source_does_not_create_faux_listings(self):
        with self.assertRaisesRegex(RuntimeError, "too_few_verified_listings"):
            m.build(fetcher=lambda url: b"429 Too Many Requests")

    def test_real_alphanumeric_identifiers_do_not_collide_with_numeric_issuers(self):
        # Codes independently checked against DART and the issuer listing notice.
        html = ('<table><tr><th>회사명</th><th>종목코드</th></tr>'
                '<tr><td>덕양에너젠</td><td>0001A0</td></tr>'
                '<tr><td>에임드바이오</td><td>0009K0</td></tr>'
                '<tr><td>별개 숫자코드 기업</td><td>000010</td></tr></table>').encode()
        rows = m.deduplicate(m.kind_rows(html, "KOSDAQ"))
        self.assertEqual({x["symbol"] for x in rows}, {"0001A0", "0009K0", "000010"})
        self.assertEqual(next(x["symbol"] for x in rows if x["name"] == "덕양에너젠"), "0001A0")
        self.assertTrue(all(x["source_symbol"] == x["symbol"] for x in rows))

    def test_malformed_identifiers_are_rejected_not_repaired_into_another_stock(self):
        for value in ("", "A005930", "00-5930", "0001A00", "005930 주", "１２３４５６"):
            self.assertIsNone(m.korean_symbol(value), value)
        self.assertEqual(m.korean_symbol("5930"), "005930")
        self.assertEqual(m.korean_symbol(" 0001a0 "), "0001A0")

    def test_different_companies_cannot_silently_share_a_catalogue_identifier(self):
        a = {"country": "KR", "symbol": "000010", "name": "A", "exchange": "KOSDAQ"}
        with self.assertRaisesRegex(ValueError, "conflicting_listing_identity"):
            m.deduplicate([a, {**a, "name": "B"}])

    def test_sec_fallback_schema_and_source(self):
        data = json.dumps({"fields":["cik","name","ticker","exchange"],
            "data":[[10,"Real US Corporation","RUS","Nasdaq"],[11,"Not a listing","ZZZ","OTC"]]}).encode()
        items = m.sec_rows(data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "SEC EDGAR")
        self.assertEqual(items[0]["symbol"], "RUS")

    def test_duplicates_and_provenance(self):
        item={"symbol":"AAPL","name":"Apple","exchange":"NASDAQ","country":"US",
              "source":"Nasdaq Trader","source_url":m.NASDAQ}
        self.assertEqual(len(m.deduplicate([item,item])),1)

if __name__=="__main__":
    unittest.main()
