import datetime as dt
import unittest
from core import normalize_universe, subscription_rows, quote_from_trade, quote_from_rest, WatchEngine

NOW=dt.datetime(2026,10,29,0,0,tzinfo=dt.timezone.utc)
def row(code="005930",market="KR"):
    return dict(symbol=code,market=market,name="실험 종목",currency="KRW" if market=="KR" else "USD",
                prior_high20=110,price_session="2026-10-28",technical_date="2026-10-28",reference_price=99)
def q(price=100, seconds=0, sym="005930"):
    return dict(symbol=sym,price=price,currency="KRW",timestamp=NOW+dt.timedelta(seconds=seconds),source="REST")

class Tests(unittest.TestCase):
    def test_leading_zeros_preserved(self):
        rows=normalize_universe({"companies":[{"market":"KR","symbol":"005930"},{"market":"US","symbol":"AAPL"}]})
        self.assertEqual([r["symbol"] for r in rows],["005930","AAPL"])
    def test_invalid_and_duplicate_symbols(self):
        rows=normalize_universe({"companies":[{"market":"KR","symbol":"005930"},{"market":"KR","symbol":"005930"},{"market":"KR","symbol":"a&b"},{"market":"US","symbol":"1234"}]})
        self.assertEqual(len(rows),1)
    def test_one_websocket_and_rest_fallback(self):
        rows=[row(str(i).zfill(6)) for i in range(104)]
        declared,rest=subscription_rows(rows)
        self.assertEqual(sum(len(v["codes"]) for v in declared),100)
        self.assertEqual(len(rest),4)
        self.assertRaises(ValueError,subscription_rows,rows,101)
    def test_full_replace_spec(self):
        declared,_=subscription_rows([row(),row("AAPL","US")])
        self.assertEqual(declared,[{"type":"trade:kr","codes":["005930"]},{"type":"trade:us","codes":["AAPL"]}])
    def test_toss_rest_schema(self):
        self.assertEqual(quote_from_rest({"symbol":"005930","lastPrice":"72000","timestamp":NOW.isoformat(),"currency":"KRW"})["price"],72000)
    def test_toss_trade_schema(self):
        frame={"type":"message","topic":"trade:kr:005930","data":{"price":"71000","timestamp":NOW.isoformat(),"currency":"KRW","volume":"8"}}
        self.assertEqual(quote_from_trade(frame)["symbol"],"005930")
        self.assertIsNone(quote_from_trade({"type":"message","topic":"personal:order:3","data":frame["data"]}))
    def test_start_is_never_alert(self):
        engine=WatchEngine([row()],now_fn=lambda:NOW)
        self.assertIsNone(engine.ingest(q(100)))
        self.assertEqual(len(engine.alerts),0)
    def test_positive_and_negative_observation_never_buy(self):
        engine=WatchEngine([row()],now_fn=lambda:NOW)
        engine.ingest(q(100,seconds=-1))
        msg=engine.ingest(q(103))
        self.assertEqual(msg["type"],"research_watch_only")
        self.assertFalse(msg["order_authorized"])
        self.assertFalse(msg["strict_green_eligible"])
        self.assertIsNone(engine.ingest(q(104,seconds=1)))
        self.assertEqual(engine.ingest(q(96,seconds=2))["type"],"research_watch_only")
    def test_stale_future_currency_and_out_of_order_fail_closed(self):
        engine=WatchEngine([row()],now_fn=lambda:NOW)
        self.assertIsNone(engine.ingest(q(100,-100)))
        self.assertIsNone(engine.ingest(q(100,10)))
        self.assertIsNone(engine.ingest({**q(100),"currency":"USD"}))
        engine.ingest(q(100,-1))
        self.assertIsNone(engine.ingest(q(103,-2)))
        self.assertEqual(engine.accepted,1)
        self.assertEqual(engine.dropped,4)
    def test_breakout_requires_dated_reference(self):
        engine=WatchEngine([row()],now_fn=lambda:NOW)
        engine.ingest(q(109,-1))
        event=engine.ingest(q(111))
        self.assertIn("고점",str(event["reasons"]))
        stale={**row(),"technical_date":"2026-10-20"}
        engine=WatchEngine([stale],now_fn=lambda:NOW)
        engine.ingest(q(109,-1))
        self.assertIsNone(engine.ingest(q(110,0)))
    def test_status_does_not_report_stale_quotes(self):
        engine=WatchEngine([row()],now_fn=lambda:NOW)
        engine.ingest(q(100,-1))
        self.assertEqual(engine.status(True,"live",1,0)["active_fresh_quotes"],1)
        self.assertEqual(engine.status(True,"live",1,0)["live_buy_recommendations"],0)
    def test_unknown_symbol_rejected(self):
        engine=WatchEngine([row()],now_fn=lambda:NOW)
        self.assertIsNone(engine.ingest(q(100,sym="AAPL")))
    def test_bool_price_rejected(self):
        self.assertIsNone(quote_from_rest({"symbol":"005930","lastPrice":True,"timestamp":NOW.isoformat()}))

if __name__=="__main__": unittest.main()
