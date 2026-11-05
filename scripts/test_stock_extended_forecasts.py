"""Offline tests of rotating coverage, target guards and no fabricated predictions."""
import tempfile
import unittest
from pathlib import Path
import json
from scripts import run_stock_extended_forecasts as x


def verified_catalogue(items):
    records=[{**item,"source_symbol":item["symbol"]} for item in items]
    return {"identifier_policy":x.SOURCE_IDENTITY_POLICY,"status":"complete",
            "counts":{"total":len(records),"KR":sum(r["country"]=="KR" for r in records),
                      "US":sum(r["country"]=="US" for r in records)},"items":records}


def apple_catalogue(root):
    (root/"stock-universe-catalog.json").write_text(json.dumps(verified_catalogue([
        {"symbol":"AAPL","country":"US","exchange":"NASDAQ","name":"Apple"}])))


class RotationTests(unittest.TestCase):
    def test_round_robin_with_distinct_priority(self):
        tracked=[("AAPL","Apple","US"),("MSFT","Microsoft","US"),
                 ("NVDA","NVIDIA","US"),("TSLA","Tesla","US")]
        directory=tracked+[("FN","Fabrinet","US"),("ON","onsemi","US"),
                 ("DOCS","Doximity","US"),("META","Meta","US")]
        selected, cursor = x.choose_batch(tracked,directory,{},6)
        self.assertEqual(len(set(v[0] for v in selected)),6)
        self.assertEqual(cursor["tracked"],3)
        self.assertEqual(cursor["directory"],3)
        next_selected, next_cursor=x.choose_batch(tracked,directory,{"cursor":cursor},6)
        self.assertEqual(next_selected[0][0],"TSLA")
        self.assertNotEqual(cursor,next_cursor)

    def test_kr_requires_verified_market(self):
        self.assertIsNone(x.ticker("KR","UNKNOWN","005930"))
        self.assertEqual(x.ticker("KR","KOSPI","005930"),"005930.KS")
        self.assertEqual(x.ticker("KR","KOSDAQ","403870"),"403870.KQ")
        self.assertEqual(x.ticker("KR","KOSDAQ","0001A0"),"0001A0.KQ")
        self.assertEqual(x.ticker("KR","KOSDAQ","0009K0"),"0009K0.KQ")
        self.assertIsNone(x.ticker("US","NASDAQ","ABCDE-R"))

    def test_real_summary_and_directory_are_not_mixed_with_fake_fundamentals(self):
        summary={"states":[{"symbol":"AAPL","name":"Apple"},{"symbol":"005930","name":"삼성전자"}]}
        directory=verified_catalogue([{"symbol":"005930","name":"삼성전자","country":"KR","exchange":"KOSPI"},
                             {"symbol":"AAPL","name":"Apple","country":"US","exchange":"NASDAQ"},
                             {"symbol":"FN","name":"Fabrinet","country":"US","exchange":"NYSE"}])
        tracked,broad=x.compile_targets(summary,directory)
        self.assertEqual({v[0] for v in tracked},{"AAPL","005930.KS"})
        self.assertEqual(len(broad),3)

    def test_only_published_target_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"stock-opportunity-summary.json").write_text(json.dumps(
                {"states":[{"symbol":"AAPL","name":"Apple"}]}))
            apple_catalogue(root)
            invoked=[]
            def processor(spec, collector):
                invoked.append(spec[0])
                return {"symbol":spec[0],"mode":"daily","market":"US",
                        "status":"no_call","reason":"test_no_provider_data",
                        "probabilities":None,"target":None}
            output=x.run(root,batch_size=2,collector=lambda s:None,predictor=processor)
            self.assertEqual(output["run"]["research_prediction"],0)
            self.assertEqual(output["run"]["no_call"],1)
            self.assertEqual(output["records"][0]["status"],"no_call")
            self.assertTrue(output["records"][0]["identity_verified"])
            self.assertEqual(output["source_identity_policy"],x.SOURCE_IDENTITY_POLICY)
            self.assertEqual(invoked,["AAPL"])
            second=x.run(root,batch_size=2,collector=lambda s:None,predictor=processor)
            self.assertEqual(len(second["records"]),1)
            self.assertEqual(second["universe"]["attempted_total"],1)

    def test_no_call_keeps_only_unexpired_genuine_forecast(self):
        from datetime import datetime, timedelta, timezone
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"stock-opportunity-summary.json").write_text(json.dumps(
                {"states":[{"symbol":"AAPL","name":"Apple"}]}))
            apple_catalogue(root)
            prior={"version":x.VERSION,"source_identity_policy":x.SOURCE_IDENTITY_POLICY,"cursor":{},
                   "records":[{"symbol":"AAPL","mode":"daily","status":"research_prediction",
                               "market":"US","catalog_symbol":"AAPL","catalog_name":"Apple","catalog_exchange":"NASDAQ",
                               "name":"Apple","identity_verified":True,"source_identity_policy":x.SOURCE_IDENTITY_POLICY,
                               "issued_at":(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),
                               "target":{"start":(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),
                                         "end":(datetime.now(timezone.utc)+timedelta(hours=5)).isoformat()},
                               "probabilities":{"up":.3,"flat":.4,"down":.3},"direction":"flat"}]}
            (root/x.OUTPUT).write_text(json.dumps(prior))
            def unavailable(spec,collector):
                return {"symbol":spec[0],"market":spec[2],"status":"no_call","probabilities":None,
                        "reason":"temporary_source_timeout"}
            current=x.run(root,batch_size=2,collector=lambda _:None,predictor=unavailable)
            self.assertEqual(current["records"][0]["status"],"research_prediction")
            self.assertEqual(current["records"][0]["latest_attempt"]["status"],"no_call")
            self.assertEqual(current["run"]["research_prediction"],0)
            self.assertEqual(current["run"]["no_call"],1)
            self.assertEqual(current["run"]["retained_unexpired_after_no_call"],1)
            previous=current
            previous["records"][0]["target"]["end"]=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
            (root/x.OUTPUT).write_text(json.dumps(previous))
            after=x.run(root,batch_size=2,collector=lambda _:None,predictor=unavailable)
            self.assertEqual(after["records"][0]["status"],"no_call")

    def test_generator_failure_does_not_replace_persisted_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            previous=b'{"user":"prior_research"}'
            (root/x.OUTPUT).write_bytes(previous)
            (root/"stock-opportunity-summary.json").write_text('{"states":[{"symbol":"AAPL","name":"Apple"}]}')
            with self.assertRaises(ValueError):
                x.run(root,batch_size=0,collector=lambda s:None)
            self.assertEqual((root/x.OUTPUT).read_bytes(),previous)

    def test_alphanumeric_korean_summary_uses_current_official_market_and_name(self):
        directory=verified_catalogue([{"symbol":"0001A0","name":"덕양에너젠","country":"KR","exchange":"KOSDAQ"}])
        tracked,broad=x.compile_targets({"states":[{"symbol":"0001A0","name":"stale summary name"}]},directory)
        self.assertEqual(tracked,[("0001A0.KQ","덕양에너젠","KR")])
        self.assertEqual(broad,tracked)

    def test_summary_without_official_directory_match_is_not_a_verified_us_target(self):
        directory=verified_catalogue([{"symbol":"MSFT","name":"Microsoft","country":"US","exchange":"NASDAQ"}])
        tracked,_=x.compile_targets({"states":[{"symbol":"AAPL","name":"Apple"}]},directory)
        self.assertEqual(tracked,[])

    def test_old_catalogue_is_refused_without_rewriting_cached_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            old=b'{"records":[{"symbol":"000010.KQ","name":"wrong prior identity"}]}'
            (root/x.OUTPUT).write_bytes(old)
            (root/"stock-universe-catalog.json").write_text('{"items":[]}')
            with self.assertRaisesRegex(RuntimeError,"verified_catalogue_identifiers"):
                x.run(root,collector=lambda _:None)
            self.assertEqual((root/x.OUTPUT).read_bytes(),old)

    def test_old_wrong_ticker_prediction_is_quarantined_not_relabelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"stock-universe-catalog.json").write_text(json.dumps(verified_catalogue([
                {"symbol":"0001A0","name":"덕양에너젠","country":"KR","exchange":"KOSDAQ"}])))
            old={"symbol":"000010.KQ","name":"덕양에너젠","status":"research_prediction",
                 "probabilities":{"up":0.95,"flat":0.03,"down":0.02}}
            (root/x.OUTPUT).write_text(json.dumps({"records":[old]}))
            called=[]
            def no_data(spec,collector):
                called.append(spec[0])
                return {"symbol":spec[0],"market":spec[2],"status":"no_call","probabilities":None,"target":None}
            result=x.run(root,collector=lambda _:None,predictor=no_data,batch_size=1)
            self.assertEqual(called,["0001A0.KQ"])
            self.assertEqual(result["records"][0]["status"],"no_call")
            self.assertIsNone(result["records"][0]["probabilities"])
            self.assertEqual(result["quarantined_records"],1)
            archive=json.loads((root/x.QUARANTINE_OUTPUT).read_text())
            self.assertEqual(archive["records"][0]["record"],old)

    def test_prior_policy_alone_cannot_keep_a_changed_company_identity(self):
        identities={"AAPL":{"symbol":"AAPL","market":"US","catalog_symbol":"AAPL",
                            "catalog_name":"Apple Inc.","catalog_exchange":"NASDAQ"}}
        old={"symbol":"AAPL","market":"US","catalog_symbol":"AAPL","catalog_name":"Other company",
             "catalog_exchange":"NASDAQ","name":"Other company","status":"no_call",
             "probabilities":None,"target":None,"source_identity_policy":x.SOURCE_IDENTITY_POLICY,
             "identity_verified":True}
        retained,quarantine=x.retain_verified_cache({"source_identity_policy":x.SOURCE_IDENTITY_POLICY,
                                                   "records":[old]},identities,"2026-11-05")
        self.assertEqual(retained,{})
        self.assertEqual(len(quarantine),1)


if __name__=="__main__":
    unittest.main()
