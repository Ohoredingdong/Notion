"""Offline finance-provenance and no-fabrication tests for both markets."""
import io
import json
from datetime import date
from pathlib import Path
import tempfile
import unittest
import zipfile
from urllib.parse import urlparse, parse_qs

from scripts import build_stock_financial_coverage as f
from scripts.validate_stock_financial_coverage import validate


def sec_facts():
    return json.dumps({"cik":320193,"entityName":"Apple Inc.","facts":{"us-gaap":{
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


def corp_zip(symbol="005930", corp="00126380", name="삼성전자", extra=""):
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        z.writestr("CORPCODE.xml",f'<result><list><corp_code>{corp}</corp_code>'
            f'<corp_name>{name}</corp_name><stock_code>{symbol}</stock_code></list>{extra}</result>')
    return buffer.getvalue()


def official_rows(symbol="005930", corp="00126380", *, year=2026, report="11012"):
    period_end={"11013":"03.31","11012":"06.30","11014":"09.30","11011":"12.31"}[report]
    result=[]
    for account, amount, statement in (("매출액",1234,"IS"),("영업이익",-50,"IS"),
                                       ("당기순이익",20,"IS"),("자산총계",7000,"BS"),
                                       ("부채총계",3000,"BS"),("자본총계",4000,"BS")):
        result.append({"corp_code":corp,"stock_code":symbol,"bsns_year":str(year),
            "reprt_code":report,"rcept_no":"20261030000501","fs_div":"CFS",
            "account_nm":account,"sj_div":statement,"thstrm_amount":str(amount),
            "thstrm_dt":f"{year}.01.01 ~ {year}.{period_end}" if statement=="IS" else
                        f"{year}.{period_end} 현재","currency":"KRW"})
    return {"status":"000","list":result}


def catalog(root, *, symbol="005930", name="삼성전자", country="KR"):
    item={"country":country,"symbol":symbol,"name":name,"exchange":"KOSPI" if country=="KR" else "NASDAQ",
          "source_symbol":symbol}
    (root/"stock-universe-catalog.json").write_text(json.dumps({
        "identifier_policy":f.CATALOG_POLICY,"status":"complete","generated_at":"2026-11-05",
        "counts":{"total":1,"KR":int(country=="KR"),"US":int(country=="US")},"items":[item]}))
    return item


def verified_record(*, symbol="005930", name="삼성전자", corp="00126380", period="2026-06-30"):
    return {"symbol":symbol,"country":"KR","status":"available","catalog_name":name,
        "corp_code":corp,"identity_policy":f.IDENTITY_POLICY,"identity_verified":True,
        "identity":{"official_symbol":symbol,"corp_code":corp},
        "checked_at":"2026-11-04T00:00:00Z","period_end":period,"metrics":{"revenue":100}}


def dart_getter(symbol="005930", name="삼성전자", corp="00126380", calls=None):
    def get(url, **kwargs):
        if calls is not None:
            calls.append((url,kwargs))
        if url.startswith(f.DART_MAP):
            return corp_zip(symbol,corp,name)
        query=parse_qs(urlparse(url).query)
        if url.startswith(f.DART_MULTI):
            if query["reprt_code"] != ["11012"]:
                return b'{"status":"013","message":"No report published"}'
            return json.dumps(official_rows(symbol,corp)).encode()
        raise AssertionError("unexpected request")
    return get


def many_issuers(root, count, *, matching_names=True):
    items=[{"country":"KR","symbol":f"{i:06}","source_symbol":f"{i:06}",
            "name":f"Issuer {i}","exchange":"KOSPI"} for i in range(1,count+1)]
    source={"identifier_policy":f.CATALOG_POLICY,"status":"complete",
            "generated_at":"2026-11-05","counts":{"total":count,"KR":count,"US":0},"items":items}
    (root/"stock-universe-catalog.json").write_text(json.dumps(source))
    rows="".join(f'<list><corp_code>{10000000+i}</corp_code><stock_code>{item["symbol"]}</stock_code>'
                 f'<corp_name>{item["name"] if matching_names else "Different name"}</corp_name></list>'
                 for i,item in enumerate(items,1))
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w") as zf:
        zf.writestr("CORPCODE.xml","<result>"+rows+"</result>")
    return source,buffer.getvalue()


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
        self.assertTrue(d["identity_verified"])
        self.assertEqual(d["cik"],320193)
        self.assertFalse(d["full_financial_statements"])

    def test_no_facts_yields_no_fake_statements(self):
        x=f.parse_sec_companyfacts(b'{"cik":100,"facts":{}}',symbol="UNKNOWN",cik=100,checked_at="X")
        self.assertEqual(x["status"],"no_comparable_facts")
        self.assertNotIn("metrics",x)

    def test_corpcodes_zip_mapping(self):
        self.assertEqual(f.dart_corp_map(corp_zip())["005930"],"00126380")
        with self.assertRaises(ValueError):
            f.dart_corp_map(b"invalid key")

    def test_dart_prefers_consolidated_and_does_not_fill_fcf(self):
        rows=official_rows()
        rows["list"].insert(0,{**rows["list"][0],"fs_div":"OFS","thstrm_amount":"9999"})
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
        self.assertEqual(d["period_end"],"2026-06-30")
        self.assertEqual(d["rcept_no"],"20261030000501")
        self.assertFalse(d["full_financial_statements"])

    def test_keep_previous_on_transient_error(self):
        existing=verified_record()
        broken={"symbol":"005930","status":"source_unavailable","reason":"429",
                "checked_at":"today"}
        self.assertEqual(f.merge_record(existing,broken)["metrics"]["revenue"],100)
        self.assertEqual(f.merge_record(existing,broken)["last_refresh_error"]["reason"],"429")

    def test_reject_stale_backwards_period(self):
        existing=verified_record(period="2026-09-30")
        older=verified_record(period="2026-06-30")
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
            catalog(p)
            data=f.build(p,us_batch=0,kr_batch=1,dart_key="",agent="Test GitHub contact https://github.com/Ohoredingdong/Notion")
            r=data["records"]["KR:005930"]
            self.assertEqual(r["status"],"source_not_configured")
            self.assertNotIn("metrics",r)
            self.assertEqual(data["universe"]["total"],1)
            self.assertEqual(data["refresh_status"],"blocked")
            self.assertTrue(data["current_run_failed"])

    def test_source_mapping(self):
        d=f.official_cik_map(json.dumps({"fields":["cik","name","ticker","exchange"],
            "data":[[320193,"Apple","AAPL","Nasdaq"]]}).encode())
        self.assertEqual(d["AAPL"],320193)

    def test_real_alphanumeric_dart_corporation_map_is_preserved(self):
        mapping=f.dart_corp_map(corp_zip("0001A0","01516933","덕양에너젠"))
        self.assertEqual(mapping,{"0001A0":"01516933"})
        self.assertNotIn("000010",mapping)

    def test_historical_code_reuse_is_not_silently_resolved(self):
        extra='<list><corp_code>00999999</corp_code><corp_name>Another issuer</corp_name><stock_code>005930</stock_code></list>'
        self.assertNotIn("005930",f.dart_corp_map(corp_zip(extra=extra)))
        self.assertEqual(len(f.dart_corp_identities(corp_zip(extra=extra))["005930"]),2)

    def test_new_official_issuer_without_accounts_cannot_reuse_old_issuer_financials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog(root)
            old=verified_record(corp="00126380")
            (root/f.OUTPUT).write_text(json.dumps({"records":{"KR:005930":old}}))
            def get(url,**kwargs):
                if url.startswith(f.DART_MAP):
                    return corp_zip("005930","00999999","삼성전자")
                if url.startswith(f.DART_MULTI):
                    return b'{"status":"013","message":"No accounts for the new issuer"}'
                raise AssertionError("unexpected provider request")
            result=f.build(root,us_batch=0,kr_batch=1,getter=get,dart_key="offline",agent="",throttle=0)
            row=result["records"]["KR:005930"]
            self.assertEqual(row["corp_code"],"00999999")
            self.assertEqual(row["status"],"no_report")
            self.assertNotIn("metrics",row)
            self.assertEqual(result["financial_available"]["KR"],0)
            archived=json.loads((root/f.QUARANTINE_OUTPUT).read_text())["records"]
            self.assertEqual(archived[0]["record"],old)
            self.assertEqual(archived[0]["reason"],"official_issuer_mapping_changed")

    def test_new_issuer_identity_replaces_older_issuer_even_if_its_report_is_earlier(self):
        old=verified_record(corp="00126380",period="2026-09-30")
        new=verified_record(corp="00999999",period="2026-06-30")
        self.assertEqual(f.merge_record(old,new)["corp_code"],"00999999")
        old_us={"country":"US","symbol":"TEST","cik":100,"metrics":{"revenue":777}}
        new_us={"country":"US","symbol":"TEST","cik":200,"issuer_mapping_verified":True,
                "status":"source_unavailable"}
        self.assertNotIn("metrics",f.merge_record(old_us,new_us))

    def test_dart_remains_independent_when_sec_contact_is_unconfigured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog(root)
            calls=[]
            result=f.build(root,us_batch=0,kr_batch=1,getter=dart_getter(calls=calls),
                           agent="",dart_key="offline-test-only",throttle=0,as_of=date(2026,11,5))
            record=result["records"]["KR:005930"]
            self.assertTrue(record["identity_verified"])
            self.assertEqual(record["corp_code"],"00126380")
            self.assertEqual(result["run"]["KR"]["available"],1)
            self.assertEqual(result["refresh_status"],"success")
            self.assertFalse(result["current_run_failed"])
            self.assertTrue(all(kwargs["agent"]==f.PROJECT_AGENT for _,kwargs in calls))
            self.assertTrue(all("sec.gov" not in url for url,_ in calls))
            self.assertEqual(result["provider_readiness"]["US"],"real_contact_required")
            source_catalog=json.loads((root/"stock-universe-catalog.json").read_text())
            self.assertEqual(validate(source_catalog,result),{"KR":1,"US":0})
            result["financial_available"]["KR"]=2579
            with self.assertRaisesRegex(AssertionError,"coverage counter"):
                validate(source_catalog,result)

    def test_corrupted_previous_financials_are_archived_not_rekeyed_or_displayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog(root,symbol="0001A0",name="덕양에너젠")
            bad={"symbol":"000010","country":"KR","status":"available",
                 "metrics":{"net_income":1301581000000}}
            (root/f.OUTPUT).write_text(json.dumps({"records":{"KR:000010":bad}}))
            result=f.build(root,us_batch=0,kr_batch=1,getter=dart_getter("0001A0","덕양에너젠","01516933"),
                           agent="",dart_key="offline-test-only",throttle=0,as_of=date(2026,11,5))
            self.assertNotIn("KR:000010",result["records"])
            good=result["records"]["KR:0001A0"]
            self.assertTrue(good["identity_verified"])
            self.assertEqual(good["metrics"]["net_income"],20)
            quarantine=json.loads((root/f.QUARANTINE_OUTPUT).read_text())
            self.assertEqual(quarantine["records"][0]["record"],bad)
            self.assertEqual(result["quarantined_records"],1)

    def test_unverified_same_symbol_cache_is_not_grandfathered_into_verified_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog(root)
            (root/f.OUTPUT).write_text(json.dumps({"records":{"KR:005930":{
                "symbol":"005930","country":"KR","status":"available","metrics":{"revenue":999}}}}))
            result=f.build(root,us_batch=0,kr_batch=1,dart_key="",agent="",throttle=0)
            self.assertEqual(result["financial_available"]["KR"],0)
            self.assertNotIn("metrics",result["records"]["KR:005930"])
            self.assertEqual(result["quarantined_records"],1)

    def test_catalogue_without_correct_identifier_policy_cannot_drive_financial_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog(root)
            data=json.loads((root/"stock-universe-catalog.json").read_text())
            data.pop("identifier_policy")
            (root/"stock-universe-catalog.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError,"alphanumeric_identifier_rebuild"):
                f.build(root,us_batch=0,kr_batch=1)

    def test_partial_source_catalogue_cannot_erase_a_valid_financial_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog(root)
            before=json.dumps({"records":{"KR:005930":verified_record()}})
            (root/f.OUTPUT).write_text(before)
            source=json.loads((root/"stock-universe-catalog.json").read_text())
            source["status"]="partial"
            (root/"stock-universe-catalog.json").write_text(json.dumps(source))
            with self.assertRaisesRegex(RuntimeError,"source_refresh_incomplete"):
                f.build(root,us_batch=0,kr_batch=1)
            self.assertEqual((root/f.OUTPUT).read_text(),before)

    def test_accounts_from_different_currencies_are_not_combined(self):
        payload=official_rows();payload["list"][1]["currency"]="USD"
        with self.assertRaisesRegex(ValueError,"currency_missing_or_inconsistent"):
            f.parse_dart_multi(json.dumps(payload).encode(),corp_map={"005930":"00126380"},
                               checked_at="2026-11-05",report_year=2026,report_code="11012")

    def test_a_different_official_company_cannot_attach_to_catalogue_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog(root,symbol="000010",name="덕양에너젠")
            def get(url,**kwargs):
                if url.startswith(f.DART_MAP):
                    return corp_zip("000010","00999999","전혀다른회사")
                if url.startswith(f.DART_COMPANY):
                    return json.dumps({"status":"000","stock_code":"000010","corp_cls":"Y",
                                       "corp_name":"전혀다른회사","stock_name":"전혀다른회사"}).encode()
                raise AssertionError("Financials must not be requested for mismatched company")
            result=f.build(root,us_batch=0,kr_batch=1,getter=get,dart_key="offline",agent="",throttle=0)
            self.assertEqual(result["records"]["KR:000010"]["status"],"identity_mismatch")
            self.assertEqual(result["financial_available"]["KR"],0)
            self.assertTrue(result["current_run_failed"])

    def test_response_stock_code_must_match_requested_official_corporation(self):
        raw=json.dumps(official_rows(symbol="000010",corp="01516933")).encode()
        with self.assertRaisesRegex(ValueError,"stock_corporation_mismatch"):
            f.parse_dart_multi(raw,corp_map={"0001A0":"01516933"},checked_at="2026-11-05",
                               report_year=2026,report_code="11012")

    def test_failed_current_refresh_does_not_report_success_from_retained_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog(root)
            (root/f.OUTPUT).write_text(json.dumps({"records":{"KR:005930":verified_record()}}))
            def fail(url,**kwargs):
                raise RuntimeError("provider blocked crtfc_key=do-not-publish&request=x")
            result=f.build(root,us_batch=0,kr_batch=1,getter=fail,dart_key="offline",agent="",throttle=0)
            self.assertEqual(result["financial_available"]["KR"],1)
            self.assertEqual(result["run"]["KR"]["available"],0)
            self.assertEqual(result["refresh_status"],"blocked")
            self.assertTrue(result["current_run_failed"])
            self.assertEqual(result["records"]["KR:005930"]["checked_at"],"2026-11-04T00:00:00Z")
            self.assertNotIn("do-not-publish",json.dumps(result))

    def test_three_dart_transport_failures_stop_remaining_batches_and_preserve_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,archive=many_issuers(root,321)
            old=verified_record(symbol="000321",name="Issuer 321",corp="10000321")
            old.update(full_financial_statements=False,source="DART periodic reports")
            (root/f.OUTPUT).write_text(json.dumps({"records":{"KR:000321":old}}))
            multi_calls=[]
            def get(url,**kwargs):
                if url.startswith(f.DART_MAP):
                    return archive
                if url.startswith(f.DART_MULTI):
                    multi_calls.append(url)
                    if len(multi_calls)==1:
                        return json.dumps(official_rows("000001","10000001",report="11014")).encode()
                    raise TimeoutError("DART transport timed out")
                raise AssertionError("unexpected request")
            result=f.build(root,us_batch=0,kr_batch=321,getter=get,dart_key="offline",agent="",
                           throttle=0,as_of=date(2026,11,5))
            self.assertEqual(len(multi_calls),4)  # one success, exactly three failures
            self.assertEqual(result["run"]["KR"]["provider_requests"],5)  # plus the issuer map
            self.assertEqual(result["run"]["KR"]["available"],1)
            self.assertEqual(result["run"]["KR"]["deferred"],320)
            self.assertEqual(result["run"]["KR"]["provider_errors"],320)
            self.assertTrue(result["current_run_failed"])
            self.assertEqual(result["refresh_status"],"partial")
            self.assertEqual(result["records"]["KR:000001"]["metrics"]["revenue"],1234)
            retained=result["records"]["KR:000321"]
            self.assertEqual(retained["checked_at"],old["checked_at"])
            self.assertEqual(retained["metrics"],old["metrics"])
            self.assertIn("circuit breaker",retained["last_refresh_error"]["reason"])
            self.assertEqual(validate(source,result),{"KR":2,"US":0})
            self.assertEqual(json.loads((root/f.OUTPUT).read_text())["financial_available"]["KR"],2)

    def test_deadline_saves_current_and_prior_verified_accounts_before_next_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,archive=many_issuers(root,81)
            old=verified_record(symbol="000081",name="Issuer 81",corp="10000081")
            old.update(full_financial_statements=False,source="DART periodic reports")
            (root/f.OUTPUT).write_text(json.dumps({"records":{"KR:000081":old}}))
            clock=[0];multi_calls=[]
            def get(url,**kwargs):
                if url.startswith(f.DART_MAP):
                    return archive
                if url.startswith(f.DART_MULTI):
                    multi_calls.append(url)
                    clock[0]=11  # the first successful request consumes the remaining budget
                    return json.dumps(official_rows("000001","10000001",report="11014")).encode()
                raise AssertionError("unexpected request")
            result=f.build(root,us_batch=0,kr_batch=81,getter=get,dart_key="offline",agent="",
                           throttle=0,as_of=date(2026,11,5),max_runtime_seconds=10,monotonic=lambda:clock[0])
            self.assertEqual(len(multi_calls),1)
            self.assertEqual(result["run"]["KR"]["provider_requests"],2)
            self.assertEqual(result["run"]["KR"]["deferred"],80)
            self.assertEqual(result["run"]["KR"]["provider_errors"],80)
            self.assertTrue(result["current_run_failed"])
            self.assertIn("deadline",result["run"]["KR"]["collection_stop_reason"])
            self.assertEqual(result["records"]["KR:000081"]["checked_at"],old["checked_at"])
            self.assertEqual(validate(source,result),{"KR":2,"US":0})
            self.assertTrue((root/f.OUTPUT).is_file())

    def test_dart_identity_lookup_transport_failure_uses_same_three_request_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,archive=many_issuers(root,90,matching_names=False)
            calls=[]
            def get(url,**kwargs):
                if url.startswith(f.DART_MAP):
                    return archive
                calls.append(url)
                if url.startswith(f.DART_COMPANY):
                    raise TimeoutError("DART identity endpoint timed out")
                raise AssertionError("Accounts cannot be requested without issuer verification")
            result=f.build(root,us_batch=0,kr_batch=90,getter=get,dart_key="offline",agent="",throttle=0)
            self.assertEqual(len(calls),3)
            self.assertEqual(result["run"]["KR"]["provider_requests"],4)
            self.assertEqual(result["run"]["KR"]["identity_errors"],0)
            self.assertEqual(result["run"]["KR"]["provider_errors"],90)
            self.assertEqual(result["run"]["KR"]["deferred"],87)
            self.assertEqual(result["refresh_status"],"blocked")
            self.assertTrue(result["current_run_failed"])
            self.assertEqual(validate(source,result),{"KR":0,"US":0})

    def test_failed_optional_alias_endpoint_does_not_block_exact_mapped_issuer_accounts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,_=many_issuers(root,5)
            alias_rows="".join(f'<list><corp_code>{10000000+i}</corp_code><stock_code>{i:06}</stock_code>'
                               '<corp_name>Different legal name</corp_name></list>' for i in range(1,5))
            archive=corp_zip("000005","10000005","Issuer 5",extra=alias_rows)
            identity_calls=[];account_calls=[]
            def get(url,**kwargs):
                if url.startswith(f.DART_MAP):
                    return archive
                if url.startswith(f.DART_COMPANY):
                    identity_calls.append(url)
                    raise TimeoutError("Optional identity lookup unavailable")
                if url.startswith(f.DART_MULTI):
                    account_calls.append(url)
                    return json.dumps(official_rows("000005","10000005",report="11014")).encode()
                raise AssertionError("unexpected request")
            result=f.build(root,us_batch=0,kr_batch=5,getter=get,dart_key="offline",agent="",
                           throttle=0,as_of=date(2026,11,5))
            self.assertEqual(len(identity_calls),3)
            self.assertEqual(len(account_calls),1)
            self.assertEqual(result["run"]["KR"]["provider_requests"],5)
            self.assertEqual(result["run"]["KR"]["available"],1)
            self.assertEqual(result["run"]["KR"]["provider_errors"],4)
            self.assertEqual(result["run"]["KR"]["deferred"],1)
            self.assertEqual(result["records"]["KR:000005"]["metrics"]["revenue"],1234)
            self.assertTrue(result["current_run_failed"])
            self.assertEqual(validate(source,result),{"KR":1,"US":0})

    def test_early_year_checks_last_year_q3_instead_of_future_quarters(self):
        periods=f.reported_period_candidates(date(2027,1,10))
        self.assertEqual(periods[:2],[(2026,"11011"),(2026,"11014")])
        self.assertFalse(any(year==2027 for year,_ in periods))

    def test_h1_replaces_q1_using_dates_not_lexical_period_labels(self):
        previous=verified_record();previous.pop("period_end");previous["period_end_label"]="2026-Q1"
        latest=verified_record();latest.pop("period_end");latest["period_end_label"]="2026-H1"
        self.assertEqual(f.merge_record(previous,latest)["period_end_label"],"2026-H1")
        self.assertEqual(f.merge_record(latest,previous)["period_end_label"],"2026-H1")

    def test_dart_cumulative_income_and_balance_snapshot_are_not_mixed(self):
        payload=official_rows()
        for row in payload["list"]:
            if row["sj_div"]=="IS":
                row["thstrm_add_amount"]=str(int(row["thstrm_amount"])*2)
        result=f.parse_dart_multi(json.dumps(payload).encode(),corp_map={"005930":"00126380"},
                                 checked_at="2026-11-05",report_year=2026,report_code="11012")["005930"]
        self.assertEqual(result["metrics"]["revenue"],2468)
        self.assertEqual(result["metrics"]["assets"],7000)
        self.assertEqual(result["income_amount_basis"],"year_to_date_as_reported")

    def test_sec_issuer_identity_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"issuer_identity_mismatch"):
            f.parse_sec_companyfacts(sec_facts(),symbol="MSFT",cik=789019,checked_at="2026-11-05")

    def test_no_sec_requests_with_missing_real_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog(root,country="US",symbol="AAPL",name="Apple")
            def prohibited(*args,**kwargs):
                raise AssertionError("SEC network must not run without real contact")
            result=f.build(root,us_batch=1,kr_batch=0,getter=prohibited,agent="",dart_key="",throttle=0)
            self.assertEqual(result["records"]["US:AAPL"]["status"],"source_not_configured")
            self.assertTrue(result["current_run_failed"])


if __name__=="__main__":
    unittest.main()
