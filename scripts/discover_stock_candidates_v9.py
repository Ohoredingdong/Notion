"""Bounded live discovery. A listing/screen result is NOT an investment recommendation.

Download up to 1,000 records per market, validate exchange/currency/type locally,
and select up to 40 new issuers per market for the existing deep-research engine.
Existing 24 user research candidates are retained. Provider failures remain visible.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import json,math,re,time

MAX_PER_MARKET=1000
NEW_PER_MARKET=40
EXCHANGES={'US':{'NMS','NYQ','NGM','NCM','ASE'},'KR':{'KSC','KOE'}}
SECTORS={'Technology':'기술','Healthcare':'헬스케어','Industrials':'산업재','Consumer Cyclical':'경기소비재','Consumer Defensive':'필수소비재','Communication Services':'통신·플랫폼','Energy':'에너지','Basic Materials':'소재','Utilities':'유틸리티','Financial Services':'금융','Real Estate':'부동산'}

def n(x):
 if x is None or isinstance(x,bool):return None
 try:v=float(x);return v if math.isfinite(v) else None
 except (ValueError,TypeError):return None

def normalize(q,market):
 symbol=str(q.get('symbol',''));exchange=q.get('exchange');ccy=q.get('currency')
 if q.get('quoteType')!='EQUITY' or exchange not in EXCHANGES[market]:return None
 if ccy!=('KRW' if market=='KR' else 'USD'):return None
 if market=='KR' and not re.fullmatch(r'\d{6}\.(KS|KQ)',symbol):return None
 if market=='US' and not re.fullmatch(r'[A-Z][A-Z0-9]{0,5}(?:-[A-Z])?',symbol):return None
 name=q.get('longName') or q.get('shortName') or symbol
 if re.search(r'\b(?:warrant|preferred|units|acquisition corp)\b',name,re.I):return None
 if market=='KR' and symbol[:6][-1]!='0':return None
 cap=n(q.get('marketCap'));price=n(q.get('regularMarketPrice'));vol=n(q.get('averageDailyVolume3Month') or q.get('averageDailyVolume10Day'))
 if cap is None or price is None or price<=0:return None
 minimum=200e9 if market=='KR' else 300e6
 if cap<minimum:return None
 sector=q.get('sector') or q.get('sectorDisp') or '미분류';pe=n(q.get('trailingPE'));fpe=n(q.get('forwardPE'));eps=n(q.get('epsTrailingTwelveMonths'))
 smid=cap<(10e12 if market=='KR' else 10e9)
 return {'symbol':symbol.split('.')[0] if market=='KR' else symbol,'source_symbol':symbol,'name':name,'market':market,'sector':SECTORS.get(sector,sector),'sector_provider':sector,'currency':ccy,'exchange':exchange,'market_cap':cap,'price_snapshot':price,'price_time_epoch':n(q.get('regularMarketTime')),'average_volume':vol,'approx_turnover':price*vol if vol is not None else None,'trailing_pe':pe,'forward_pe':fpe,'ttm_eps':eps,'mid_small':smid,'source_url':'https://finance.yahoo.com/quote/'+symbol+'/','stage':'listing_screen_only','financials_verified':False}

def pick_additions(records,existing,limit=NEW_PER_MARKET):
 eligible=[]
 for r in records:
  if r['symbol'] in existing:continue
  # Financials/REITs need a different debt and cash-flow model, so retain in
  # directory but do not feed the generic industrial-company score.
  if r['sector_provider'] in ('Financial Services','Real Estate'):continue
  floor=1e9 if r['market']=='KR' else 5e6
  if r['approx_turnover'] is None or r['approx_turnover']<floor:continue
  if r['ttm_eps'] is None or r['ttm_eps']<=0:continue
  eligible.append(r)
 def key(r):
  # Sampling priority only; it is not used as the deep investment score.
  positive_forward=r['forward_pe'] is not None and 0<r['forward_pe']<60
  return (not r['mid_small'],not positive_forward,-math.log10(max(1,r['approx_turnover'])))
 eligible.sort(key=key);selected=[];counts=Counter()
 for r in eligible:
  sector=r['sector_provider']
  if counts[sector]>=8:continue
  selected.append(r);counts[sector]+=1
  if len(selected)>=limit:return selected
 # A small market may not supply eight per sector. Fill remaining positions
 # without claiming that unavailable diversification was achieved.
 chosen={r['symbol'] for r in selected}
 for r in eligible:
  if r['symbol'] not in chosen:selected.append(r);chosen.add(r['symbol'])
  if len(selected)>=limit:break
 return selected

def discover():
 import yfinance as yf
 from yfinance import EquityQuery as Q
 now=datetime.now(timezone.utc).isoformat();fixed=json.loads(Path('stock-opportunity-universe.json').read_text())['companies'];existing={x[0] for x in fixed}
 records=[];batches=[];errors=[];seen=set()
 for market,region in [('US','us'),('KR','kr')]:
  query=Q('and',[Q('eq',['region',region]),Q('is-in',['exchange',*sorted(EXCHANGES[market])]),Q('gt',['avgdailyvol3m',20000])])
  for offset in range(0,MAX_PER_MARKET,250):
   try:
    response=yf.screen(query,offset=offset,size=250,sortField='intradaymarketcap',sortAsc=False)
    quotes=response.get('quotes') or [];new=0
    for q in quotes:
     rawkey=(market,str(q.get('symbol')))
     if rawkey in seen:continue
     seen.add(rawkey);new+=1;r=normalize(q,market)
     if r:records.append(r)
    batches.append({'market':market,'offset':offset,'received':len(quotes),'new_symbols':new,'provider_total':response.get('total'),'query':query.to_dict()})
    print('screen',market,offset,len(quotes),'eligible',len(records),flush=True)
    if not quotes or new==0 or len(quotes)<250:break
    time.sleep(.5)
   except Exception as e:
    errors.append({'market':market,'offset':offset,'error':type(e).__name__+': '+str(e)[:180]});break
 selected=[]
 for market in ('US','KR'):selected+=pick_additions([r for r in records if r['market']==market],existing)
 specs=fixed+[[r['symbol'],r['name'],r['market'],r['sector'],r['source_symbol'],'자동탐색',''] for r in selected]
 d={'version':'discovery-v9','generated_at':now,'status':'ok' if not errors else 'partial' if records else 'unavailable','counts':{'downloaded_unique':len(seen),'eligible_directory':len(records),'new_deep_candidates':len(selected),'deep_candidates':len(specs)},'limits':{'max_per_market':MAX_PER_MARKET,'new_deep_per_market':NEW_PER_MARKET},'batches':batches,'errors':errors,'companies':records,'deep_selected_symbols':[x[0] for x in specs],'scope':'지역·거래소·평균거래량 쿼리로 시장별 최대 1,000개를 조회한 부분 탐색. 모든 상장기업을 검사했다는 뜻이 아닙니다.','selection_method':'정규주·통화·규모 검증 후 흑자·거래대금 기준. 중소형 우선 및 업종별 분산으로 추가 후보 선정. 선정 자체는 매수 추천이 아닙니다.','source':'Yahoo Finance screener via yfinance; independent verification pending','specs':specs}
 Path('stock-opportunity-discovery.json').write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 return d

if __name__=='__main__':discover()
