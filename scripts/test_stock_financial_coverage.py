"""Offline finance-provenance and no-fabrication tests for both markets."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import build_stock_financial_coverage as f


def sec_facts():
    return json.dumps({"facts":{"us-gaap":{
        "RevenueFromContractWithCustomerExcludingAssessedTax":{"units":{"USD":[
            {"form":"10-Q","start":"2026-07-01","end":"2026-09-30","filed":"2026-10-28","val":200},
            {"form":"10-K","start":"2025-01-01","end":"2025-12-31","filed":"2026-02-10","val":900}]}},
        "OperatingIncomeLoss":{"units":{"USD":[{"form":"10-Q","start":"2026-07-01",
            "end":"2026-09-30","filed":"2026-10-28","val":40}]}},
        "NetIncomeLoss":{"units":{"USD":[{"form":"10-Q","start":"2026-07-01",
            "end":"2026-09-30","filed":"2026-10-28","val":30}]}},
        "NetCashProvidedByUsedInOperatingActivities":{"units":{"USD":[
            {"form":"10-Q","start":"2026-01-01","end":"2026-09-30",
             "filed":"2026-10-28","val":120}]}},
        "PaymentsToAcquirePropertyPlantAndEquipment":{"units":{"USD":[
            {"form":"10-Q","start":"2026-07-01","end":"2026-09-30",
             "filed":"2026-10-28","val":20}]}},
        "EarningsPerShareDiluted":{"units":{"USD/shares":[
            {"form":"10-Q","start":"2026-07-01","end":"2026-09-30",
             "filed":"2026-10-28","val":1.23}]}},
        "Assets":{"units":{"USD":[
            {"form":"10-Q","end":"2026-09-30","filed":"2026-10-28","val":300}]}},
        "Liabilities":{"units":{"USD":[
            {"form":"10-Q","end":"2026-09-30","filed":"2026-10-28","val":110}]}},
        "StockholdersEquity":{"units":{"USD":[
            {"form":"10-Q","end":"2026-09-30","filed":"2026-10-28","val":190}]}}
    }}}).encode()


def corp_zip():
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        z.writestr("CORPCODE.xml",'<result><list><corp_code>00126380</corp_code>'
            '<stock_code>005930</stock_code></list></result>')
    return buffer.getvalue()


class FinanceTests(unittest.TestCase):
    def test_companyfacts_one_same_interval(self):
        d=f.parse_sec_companyfacts(sec_facts(),symbol="AAPL",cik=320193,checked_at="2026-11-05T00:00:00Z")
        self.assertEqual(d["status"],"available")
        self.assertEqual(d["period_end"],"2026-09-30")
        self.assertEqual(d["metrics"]["revenue"],200.0)
        self.assertEqual(d["metrics"]["net_income"],30.0)
        self.assertEqual(d["metrics"]["reported_eps"],1.23)
        self.assertEqual(d["metrics"]["assets"],300.0)
        self.assertEqual(d["metrics"]["liabilities"],110.0)
        self.assertEqual(d["metrics"]["equity"],190.0)
        self.assertIsNone(d["metrics"]["cash_from_operations"])
        self.assertIsNone(d["metrics"]["free_cash_flow"])  # no mixed cashflow periods
        self.assertFalse(d["estimated"])
        self.assertEqual(d["source"],"SEC EDGAR XBRL")

    def test_no_facts_yields_no_fake_statements(self):
        x=f.parse_sec_companyfacts(b'{"facts":{}}',symbol="UNKNOWN",cik=100,checked_at="X")
        self.assertEqual(x["status"],"no_comparable_facts")
        self.assertNotIn("metrics",x)

    def test_corpcodes_zip_mapping(self):
        self.assertEqual(f.dart_corp_map(corp_zip())["005930"],"00126380")
        with self.assertRaises(ValueError):
            f.dart_corp_map(b"invalid key")

    def test_dart_prefers_consolidated_and_does_not_fill_fcf(self):
        rows={"status":"000","list":[
           {"corp_code":"00126380","fs_div":"OFS","account_nm":"매출액","thstrm_amount":"9999"},
           {"corp_code":"00126380","fs_div":"CFS","account_nm":"매출액","thstrm_amount":"1,234"},
           {"corp_code":"00126380","fs_div":"CFS","account_nm":"영업이익","thstrm_amount":"-50"},
           {"corp_code":"00126380","fs_div":"CFS","account_nm":"당기순이익","thstrm_amount":"20"},
           {"corp_code":"00126380","fs_div":"CFS","account_nm":"자산총계","thstrm_amount":"7000"},
           {"corp_code":"00126380","fs_div":"CFS","account_nm":"부채총계","thstrm_amount":"3000"},
           {"corp_code":"00126380","fs_div":"CFS","account_nm":"자본총계","thstrm_amount":"4000"}
        ]}
        r=f.parse_dart_multi(json.dumps(rows).encode(),corp_map={"005930":"00126380"},
                             checked_at="2026-11-05",report_year=2026,report_code="11012")
        d=r["005930"]
        self.assertEqual(d["metrics"]["revenue"],1234)
        self.assertEqual(d["metrics"]["operating_income"],-50)
        self.assertEqual(d["metrics"]["assets"],7000)
        self.assertEqual(d["metrics"]["equity"],4000)
        self.assertEqual(d["consolidation"],"CFS")
        self.assertIsNone(d["metrics"]["free_cash_flow"])
        self.assertFalse(d["annualized"])

    def test_keep_previous_on_transient_error(self):
        existing={"symbol":"AAPL","status":"available","period_end":"2026-09-30",
                  "metrics":{"revenue":100}}
        broken={"symbol":"AAPL","status":"source_unavailable","reason":"429",
                "checked_at":"today"}
        self.assertEqual(f.merge_record(existing,broken)["metrics"]["revenue"],100)
        self.assertEqual(f.merge_record(existing,broken)["last_refresh_error"]["reason"],"429")

    def test_reject_stale_backwards_period(self):
        existing={"status":"available","period_end":"2026-09-30"}
        older={"status":"available","period_end":"2026-06-30"}
        self.assertEqual(f.merge_record(existing,older),existing)

    def test_bounded_cursors(self):
        data=[{"country":"US","symbol":x} for x in ("A","B","C")]+[
            {"country":"KR","symbol":"005930"}]
        a,next_cursor=f.choose(data,2,"US",2)
        self.assertEqual([z["symbol"] for z in a],["C","A"])
        self.assertEqual(next_cursor,1)
        self.assertEqual(f.choose(data,0,"KR",1)[0][0]["symbol"],"005930")
        self.assertEqual(f.choose(data,0,"US",0)[0],[])

    def test_missing_dart_key_is_explicit_not_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"stock-universe-catalog.json").write_text(json.dumps({
                "generated_at":"2026-11-05","counts":{"total":1,"KR":1,"US":0},
                "items":[{"country":"KR","symbol":"005930","name":"삼성전자","exchange":"KOSPI"}]}))
            data=f.build(p,us_batch=0,kr_batch=1,dart_key="",agent="Test GitHub contact https://github.com/Ohoredingdong/Notion")
            r=data["records"]["KR:005930"]
            self.assertEqual(r["status"],"source_not_configured")
            self.assertNotIn("metrics",r)
            self.assertEqual(data["universe"]["total"],1)

    def test_source_mapping(self):
        d=f.official_cik_map(json.dumps({"fields":["cik","name","ticker","exchange"],
            "data":[[320193,"Apple","AAPL","Nasdaq"]]}).encode())
        self.assertEqual(d["AAPL"],320193)


if __name__=="__main__":
    unittest.main()
