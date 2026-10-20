"""Three annual periods for reading, not a new buy signal. Secrets stay in Actions.
Same period, entity, currency and shareholder scope are required for ratios.
"""
from __future__ import annotations
import json, math, os, time, hashlib
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from build_stock_investment_cases import Dart
NOW=datetime.now(timezone.utc)
FIELDS={
 'revenue':('IS CIS',['ifrs-full_Revenue'],['매출액','수익(매출액)','영업수익']),
 'operating_income':('IS CIS',['dart_OperatingIncomeLoss'],['영업이익','영업이익(손실)']),
 'net_income':('IS CIS',['ifrs-full_ProfitLoss'],['당기순이익','당기순이익(손실)']),
 'owner_income':('IS CIS',['ifrs-full_ProfitLossAttributableToOwnersOfParent'],['지배기업의 소유주에게 귀속되는 당기순이익']),
 'owner_equity':('BS',['ifrs-full_EquityAttributableToOwnersOfParent'],['지배기업의 소유주에게 귀속되는 자본']),
 'total_equity':('BS',['ifrs-full_Equity'],['자본총계']),
 'cfo':('CF',['ifrs-full_CashFlowsFromUsedInOperatingActivities'],['영업활동현금흐름','영업활동으로 인한 현금흐름']),
 'ppe':('CF',['ifrs-full_PurchaseOfPropertyPlantAndEquipment'],['유형자산의 취득','유형자산 취득']),
 'intangibles':('CF',['ifrs-full_PurchaseOfIntangibleAssets'],['무형자산의 취득','무형자산 취득']),
 'receivables':('BS',['ifrs-full_TradeAndOtherCurrentReceivables'],['매출채권 및 기타유동채권','매출채권및기타채권']),
 'inventory':('BS',['ifrs-full_Inventories'],['재고자산']),
 'cash':('BS',['ifrs-full_CashAndCashEquivalents'],['현금및현금성자산','현금 및 현금성자산']),
 'eps':('IS CIS',['ifrs-full_DilutedEarningsLossPerShare'],['희석주당이익','희석주당이익(손실)'])}
def num(x):
 if x is None or isinstance(x,bool):return None
 try:
  s=str(x).replace(',','').replace(' ','');s='-'+s[1:-1] if s.startswith('(') and s.endswith(')') else s
  y=float(s);return y if math.isfinite(y) else None
 except (TypeError,ValueError):return None
def growth(x,y):return (x/y-1)*100 if x is not None and y is not None and y>0 else None
def ratios(series):
 series=sorted(series,key=lambda r:r['period'],reverse=True)
 for i,r in enumerate(series):
  prior=series[i+1] if i+1<len(series) else None
  eq,ni=r.get('owner_equity'),r.get('owner_income');old=prior.get('owner_equity') if prior else None
  r['roe_average']=ni/((eq+old)/2)*100 if ni is not None and eq is not None and old is not None and eq>0 and old>0 else None
  r['roe_basis']='같은 주주범위 순이익 ÷ 기초·기말 평균 자기자본 × 100'
  r['roe_driver']='자료 부족: 같은 주주범위의 전기·당기 자본과 이익 필요'
  if prior:
   for k in ('revenue','net_income','owner_income','owner_equity','cfo','capex','receivables','inventory'):r[k+'_growth']=growth(r.get(k),prior.get(k))
   if eq is not None and old is not None and old>0 and ni is not None and prior.get('owner_income') is not None:
    if eq<old and ni<=prior['owner_income']:r['roe_driver']='이익은 늘지 않았는데 자본이 줄었어요. ROE 상승을 본업 성장으로 단정하면 안 돼요.'
    elif ni>prior['owner_income'] and eq>=old:r['roe_driver']='이익은 늘고 자본도 유지됐어요. 일회성 이익인지와 다음 해에도 이어질지를 확인해요.'
    else:r['roe_driver']='이익 변화와 자본 변화가 함께 작용해요. 아래 두 증가율을 따로 비교해요.'
  r['cfo_to_profit']=r['cfo']/r['net_income'] if r.get('cfo') is not None and r.get('net_income') is not None and r['net_income']>0 else None
 return series
def parse_dart(d,corp,year,basis):
 rows=d.get('list') or []
 if d.get('status')!='000' or not rows:raise ValueError('no_statements')
 if any(str(x.get('corp_code'))!=str(corp) or str(x.get('bsns_year'))!=str(year) or x.get('reprt_code')!='11011' for x in rows):raise ValueError('issuer_period_conflict')
 if any(x.get('currency') not in ('KRW','',None) for x in rows):raise ValueError('currency_conflict')
 receipts={x.get('rcept_no') for x in rows if x.get('rcept_no')}
 if len(receipts)!=1:raise ValueError('multiple_receipts')
 url='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+next(iter(receipts));result=[]
 for offset,col in enumerate(('thstrm_amount','frmtrm_amount','bfefrmtrm_amount')):
  rec={'period':str(year-offset)+'-12-31','basis':basis,'source_url':url,'currency':'KRW','source_type':'DART 사업보고서','account_scope':{}}
  for key,(sections,tags,names) in FIELDS.items():
   subset=[x for x in rows if x.get('sj_div') in sections.split()];matches=[]
   for tag in tags:
    matches=[x for x in subset if x.get('account_id')==tag]
    if matches:break
   if not matches:matches=[x for x in subset if (x.get('account_nm') or '').replace(' ','') in [v.replace(' ','') for v in names]]
   vs={num(x.get(col)) for x in matches if num(x.get(col)) is not None}
   rec[key]=vs.pop() if len(vs)==1 else None
   if matches:rec['account_scope'][key]=matches[0].get('account_nm')
  if basis=='OFS':rec['owner_income']=rec['net_income'];rec['owner_equity']=rec['total_equity']
  rec['capex']=abs(rec['ppe'])+abs(rec['intangibles']) if rec['ppe'] is not None and rec['intangibles'] is not None else None
  rec['fcf']=rec['cfo']-rec['capex'] if rec['cfo'] is not None and rec['capex'] is not None else None
  if rec['revenue'] is not None:result.append(rec)
 return ratios(result)
def fetch_kr(client,row):
 symbol=row['symbol'];corp=client.codes.get(symbol);period=row.get('history',{}).get('filing_period')
 if not corp or not period or not period.endswith('-12-31'):raise ValueError('corp_or_year_end_unresolved')
 year=int(period[:4])
 for basis in ('CFS','OFS'):
  payload=json.loads(client.request('fnlttSinglAcntAll.json',{'corp_code':corp,'bsns_year':year,'reprt_code':'11011','fs_div':basis}))
  if payload.get('status')=='013' and basis=='CFS':continue
  if payload.get('status')!='000':raise ValueError('DART_'+str(payload.get('status')))
  client.success+=1;return parse_dart(payload,corp,year,basis)
 raise ValueError('no_statements')
def fetch_us(row):
 import yfinance as yf
 t=yf.Ticker(row.get('source_symbol',row['symbol']));inc=t.get_income_stmt(freq='yearly');cf=t.get_cashflow(freq='yearly');bs=t.get_balance_sheet(freq='yearly')
 if inc is None or inc.empty:return []
 names={'revenue':['TotalRevenue'],'operating_income':['OperatingIncome'],'net_income':['NetIncomeIncludingNoncontrollingInterests','NetIncome'],'owner_income':['NetIncomeCommonStockholders'],'owner_equity':['CommonStockEquity'],'cfo':['OperatingCashFlow'],'capex':['CapitalExpenditure'],'receivables':['AccountsReceivable'],'inventory':['Inventory'],'cash':['CashAndCashEquivalents'],'eps':['DilutedEPS']}
 result=[]
 for date in sorted(inc.columns,reverse=True)[:4]:
  r={'period':str(date)[:10],'basis':'제공처 연결 집계 · 공시 원문 대조 전','currency':row['currency'],'source_url':'https://finance.yahoo.com/quote/'+row['source_symbol']+'/financials/','source_type':'Yahoo Finance 연간 재무','account_scope':{}}
  for field,aliases in names.items():
   frame=cf if field in ('cfo','capex') else bs if field in ('owner_equity','receivables','inventory','cash') else inc;r[field]=None
   if frame is not None and not frame.empty and date in frame.columns:
    for name in aliases:
     if name in frame.index:r[field]=num(frame.loc[name,date]);r['account_scope'][field]=name;break
  r['capex']=abs(r['capex']) if r['capex'] is not None else None;r['fcf']=r['cfo']-r['capex'] if r['cfo'] is not None and r['capex'] is not None else None
  if r['revenue'] is not None:result.append(r)
 return ratios(result)[:3]
def main():
 raw=Path('stock-opportunity-data.json').read_bytes();d=json.loads(raw);key=os.getenv('DART_API_KEY','').strip();client=Dart(key);results={};errors=[]
 if key:
  try:client.corpmap()
  except Exception as e:errors.append({'source':'DART','error':str(e)});client.codes={}
 us=[r for r in d['companies'] if r.get('market')=='US'];kr=[r for r in d['companies'] if r.get('market')=='KR']
 with ThreadPoolExecutor(max_workers=2) as ex:
  futures={ex.submit(fetch_us,r):r for r in us}
  for r in kr:
   try:
    if not client.codes:raise ValueError('DART_auth_unavailable')
    series=fetch_kr(client,r);results[r['symbol']]={'symbol':r['symbol'],'status':'ok' if len(series)>=3 else 'partial','series':series,'checked_at':datetime.now(timezone.utc).isoformat()}
   except Exception as e:results[r['symbol']]={'symbol':r['symbol'],'status':'unavailable','series':[],'error':str(e)[:180]}
  for f in as_completed(futures):
   r=futures[f]
   try:
    series=f.result();results[r['symbol']]={'symbol':r['symbol'],'status':'ok' if len(series)>=3 else 'partial','series':series,'checked_at':datetime.now(timezone.utc).isoformat()}
   except Exception as e:results[r['symbol']]={'symbol':r['symbol'],'status':'unavailable','series':[],'error':type(e).__name__}
 out={'version':'reading-depth-1','generated_at':datetime.now(timezone.utc).isoformat(),'source_generated_at':d['generated_at'],'source_sha256':hashlib.sha256(raw).hexdigest(),'companies':list(results.values()),'counts':{'tracked':len(results),'three_years':sum(len(x['series'])>=3 for x in results.values()),'official':sum(bool(x['series']) and x['series'][0].get('source_type')=='DART 사업보고서' for x in results.values())},'errors':errors,'scope':'과거 재무 읽기 보조자료. 기존 매수판정이나 가격을 변경하지 않음. 없는 금액을 0으로 채우지 않음.'}
 text=json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)
 if key and key in text:raise RuntimeError('Secret blocked')
 Path('stock-reading-depth.json').write_text(text+'\n');Path('stock-reading-depth-summary.json').write_text(json.dumps({k:out[k] for k in ('generated_at','source_generated_at','counts','errors','scope')},ensure_ascii=False,indent=2)+'\n');print(out['counts'])
if __name__=='__main__':main()
