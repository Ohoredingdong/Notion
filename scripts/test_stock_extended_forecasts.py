"""Offline tests of rotating coverage, target guards and no fabricated predictions."""
import tempfile
import unittest
from pathlib import Path
import json
from scripts import run_stock_extended_forecasts as x


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
        self.assertIsNone(x.ticker("US","NASDAQ","ABCDE-R"))

    def test_real_summary_and_directory_are_not_mixed_with_fake_fundamentals(self):
        summary={"states":[{"symbol":"AAPL","name":"Apple"},{"symbol":"005930","name":"삼성전자"}]}
        directory={"items":[{"symbol":"005930","name":"삼성전자","country":"KR","exchange":"KOSPI"},
                             {"symbol":"AAPL","name":"Apple","country":"US","exchange":"NASDAQ"},
                             {"symbol":"FN","name":"Fabrinet","country":"US","exchange":"NYSE"}]}
        tracked,broad=x.compile_targets(summary,directory)
        self.assertEqual({v[0] for v in tracked},{"AAPL","005930.KS"})
        self.assertEqual(len(broad),3)

    def test_only_published_target_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"stock-opportunity-summary.json").write_text(json.dumps(
                {"states":[{"symbol":"AAPL","name":"Apple"}]}))
            (root/"stock-universe-catalog.json").write_text(json.dumps(
                {"items":[{"symbol":"AAPL","country":"US","exchange":"NASDAQ","name":"Apple"}]}))
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
            self.assertEqual(invoked,["AAPL"])
            second=x.run(root,batch_size=2,collector=lambda s:None,predictor=processor)
            self.assertEqual(len(second["records"]),1)
            self.assertEqual(second["universe"]["attempted_total"],1)

    def test_generator_failure_does_not_replace_persisted_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            previous=b'{"user":"prior_research"}'
            (root/x.OUTPUT).write_bytes(previous)
            (root/"stock-opportunity-summary.json").write_text('{"states":[{"symbol":"AAPL","name":"Apple"}]}')
            with self.assertRaises(ValueError):
                x.run(root,batch_size=0,collector=lambda s:None)
            self.assertEqual((root/x.OUTPUT).read_bytes(),previous)


if __name__=="__main__":
    unittest.main()
