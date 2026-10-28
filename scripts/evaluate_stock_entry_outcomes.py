"""Observe preregistered candidates, not imaginary executions or strategy returns."""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from build_stock_entry_plan import number,stamp,UTC

HORIZONS=(1,5,20)

def observe(record, row, bars, benchmark, now):
    outputs=[]; decided=stamp(record.get('recorded_at')); price=number(row.get('price'))
    if not decided or not price or row.get('state')=='data_wait': return []
    settings={'KR':('Asia/Seoul',9,0,15,30),'US':('America/New_York',9,30,16,0)}
    if row.get('market') not in settings: return []
    tz,oh,om,ch,cm=settings[row['market']]; zone=ZoneInfo(tz)
    available=[]
    for b in bars:
        try: d=dt.date.fromisoformat(b['date'])
        except (ValueError,KeyError): continue
        opened=dt.datetime.combine(d,dt.time(oh,om),zone).astimezone(UTC)
        closed=dt.datetime.combine(d,dt.time(ch,cm),zone).astimezone(UTC)
        if opened>decided and closed<=now and number(b.get('close')) is not None: available.append(b)
    available.sort(key=lambda b:b['date']); bm={b['date']:b for b in benchmark}
    ref=next((b for b in bars if b['date']==row.get('price_session')),None)
    baseline=bm.get(row.get('price_session'),{}).get('close')
    if not ref or not number(ref.get('close')) or abs(ref['close']/price-1)>0.0001: return []
    for h in HORIZONS:
        item={'record_id':record['id'],'symbol':row['symbol'],'horizon_sessions':h,'state_at_record':row['state'],
              'status':'pending','recorded_at':record['recorded_at'],'reference_session':row['price_session'],
              'observation_return_not_trade_return':True}
        if len(available)>=h:
            path=available[:h]; last=path[-1]; b_end=bm.get(last['date'],{}).get('close')
            if any(number(b.get('split')) not in (None,0) for b in bars if row['price_session']<b['date']<=last['date']):
                item['status']='corporate_action_review'
            elif not number(baseline) or not number(b_end): item['status']='benchmark_missing'
            else:
                ret=(last['close']/price-1)*100; bret=(b_end/baseline-1)*100
                item.update(status='observed',exit_session=last['date'],price_return_pct=ret,
                            benchmark_price_return_pct=bret,excess_price_return_pp=ret-bret,
                            return_after_assumed_30bp_cost_pct=ret-0.30,
                            cost_is_assumption_not_actual=True,
                            worst_observed_daily_close_change_pct=min((b['close']/price-1)*100 for b in path),
                            dividends_not_included=True,loss_is_not_capped=True)
        outputs.append(item)
    return outputs

def main(root=Path('.'),now=None):
    now=now or dt.datetime.now(UTC); path=root/'stock-entry-ledger.jsonl'
    records=[json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []
    cache={}; errors=[]; results=[]
    def history(symbol):
        if symbol in cache: return cache[symbol]
        try:
            import yfinance as yf
            start=min(r['recorded_at'][:10] for r in records)
            start=(dt.date.fromisoformat(start)-dt.timedelta(days=10)).isoformat()
            frame=yf.Ticker(symbol).history(start=start,auto_adjust=False,actions=True,timeout=15)
            data=[{'date':idx.date().isoformat(),'close':number(row.get('Close')),'split':number(row.get('Stock Splits'))} for idx,row in frame.iterrows()]
            cache[symbol]=data
        except Exception as exc:
            errors.append({'symbol':symbol,'type':type(exc).__name__});cache[symbol]=[]
        return cache[symbol]
    pending=0
    for record in records:
        # Do not fetch prices to manufacture results before the first following session.
        if not stamp(record.get('recorded_at')) or (now-stamp(record['recorded_at'])).total_seconds()<20*3600:
            pending+=len(record.get('companies',[])); continue
        for row in record.get('companies',[]):
            symbol=row.get('provider_symbol')
            if not symbol or row.get('state')=='data_wait': continue
            benchmark='^KQ11' if symbol.endswith('.KQ') else '^KS11' if row.get('market')=='KR' else '^GSPC'
            results.extend(observe(record,row,history(symbol),history(benchmark),now))
    payload={'version':'entry-observations-1.0','generated_at':now.isoformat(),
             'status':'observations_only','live_strategy_validated':False,
             'records':len(records),'not_yet_due_candidates':pending,
             'observed_outcomes':sum(r['status']=='observed' for r in results),
             'scope':'시점 고정 후보의 가격 변화. 미체결·누락·거래비용·배당을 포함한 실거래 성과가 아님.',
             'price_provider':'Yahoo, unofficial single source','results':results,'errors':errors}
    (root/'stock-entry-outcomes.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in payload.items() if k not in ('results','errors')},ensure_ascii=False))

if __name__=='__main__': main()
