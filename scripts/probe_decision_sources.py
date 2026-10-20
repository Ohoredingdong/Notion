"""Bounded provider availability test. No user accounts, orders, or credential output."""
from pathlib import Path
from datetime import datetime, timezone
import json, time, traceback
import yfinance as yf

out={"at":datetime.now(timezone.utc).isoformat(),"yfinance":yf.__version__,"tickers":{}}
keys=['currency','financialCurrency','regularMarketTime','regularMarketPrice','marketCap','trailingEps','forwardEps','forwardPE','targetLowPrice','targetMeanPrice','targetMedianPrice','targetHighPrice','numberOfAnalystOpinions','totalCash','totalDebt','ebitda','lastFiscalYearEnd','nextFiscalYearEnd','mostRecentQuarter']
for symbol in ['MSFT','000660.KS']:
 t=yf.Ticker(symbol); row={}
 for name,fn in [('info',lambda:{k:v for k,v in t.get_info().items() if k in keys}),('estimates',t.get_earnings_estimate),('eps_trend',t.get_eps_trend),('targets',t.get_analyst_price_targets),('revisions',t.get_eps_revisions),('revenue_estimates',t.get_revenue_estimate),('history',lambda:t.history(period='6mo',auto_adjust=False,actions=True,raise_errors=True)),('calendar',lambda:t.calendar),('news',lambda:t.get_news(count=3))]:
  try:
   value=fn()
   if hasattr(value,'to_json'):value=json.loads(value.tail(5).to_json(orient='split',date_format='iso'))
   row[name]=value
  except Exception as e:row[name]={'error':str(e)[:200]}
  time.sleep(.6)
 out['tickers'][symbol]=row
Path('decision-source-probe.json').write_text(json.dumps(out,ensure_ascii=False,default=str,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,default=str,indent=2))
