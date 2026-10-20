"""Explainable investment opinions, NOT assured returns or execution orders.
A separate snapshot is tied to the exact input generation. OpenDART keys never
appear in output, URLs, exception text, or fixtures. Missing facts remain unknown.
"""
from __future__ import annotations
import hashlib,io,json,math,os,re,time,urllib.request,urllib.parse,zipfile
from pathlib import Path
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
from statistics import median
NOW=datetime.now(timezone.utc)
RULES={'min_forecast_analysts':5,'max_eps_spread':.5,'max_target_spread':.8,'revision_floor_pct':-3,'target_room_pct':20,'max_net_debt_ebitda':3,'recent_balance_days':230,'annual_max_days':550,'report_decline_pct':-10,'min_peer_count':3}
def num(x):
 if isinstance(x,bool):return None
 try:
  s=str(x).replace(',','').replace(' ','').replace('−','-')
  if s.startswith('(') and s.endswith(')'):s='-'+s[1:-1]
  n=float(s);return n if math.isfinite(n) else None
 except (ValueError,TypeError):return None
def growth(x,y):return (x/y-1)*100 if x is not None and y is not None and y>0 else None
def age(s,now=NOW):
 try:
  d=datetime.fromisoformat(str(s).replace('Z','+00:00'));d=d.replace(tzinfo=timezone.utc) if not d.tzinfo else d
  return (now-d).total_seconds()/86400
 except (ValueError,TypeError):return None
def read(p,default):
 try:return json.loads(Path(p).read_text())
 except (OSError,ValueError):return default
ACCOUNTS={
 'revenue':(['ifrs-full_Revenue'],['매출액','수익(매출액)','매출','영업수익'],['IS','CIS']),
 'operating_income':(['dart_OperatingIncomeLoss'],['영업이익','영업이익(손실)','영업손익'],['IS','CIS']),
 'net_income':(['ifrs-full_ProfitLossAttributableToOwnersOfParent','ifrs-full_ProfitLoss'],['지배기업의 소유주에게 귀속되는 당기순이익','당기순이익','당기순이익(손실)'],['IS','CIS']),
 'eps':(['ifrs-full_DilutedEarningsLossPerShare'],['희석주당이익','희석주당이익(손실)'],['IS','CIS']),
 'cfo':(['ifrs-full_CashFlowsFromUsedInOperatingActivities'],['영업활동현금흐름','영업활동으로 인한 현금흐름','영업활동으로인한현금흐름'],['CF']),
 'ppe':(['ifrs-full_PurchaseOfPropertyPlantAndEquipment'],['유형자산의 취득','유형자산 취득'],['CF']),
 'intangible':(['ifrs-full_PurchaseOfIntangibleAssets'],['무형자산의 취득','무형자산 취득'],['CF']),
 'cash':(['ifrs-full_CashAndCashEquivalents'],['현금및현금성자산','현금 및 현금성자산'],['BS']),
}
def extract(payload,corp,year,report,basis):
 rows=payload.get('list') or []
 if payload.get('status')!='000' or not rows:raise ValueError('no_statements')
 if any(str(x.get('corp_code'))!=corp or str(x.get('bsns_year'))!=str(year) or x.get('reprt_code')!=report for x in rows):raise ValueError('issuer_or_period_conflict')
 if any(x.get('currency') not in (None,'','KRW') for x in rows):raise ValueError('currency_conflict')
 facts={};prior={};labels={};warnings=[]
 for key,(tags,names,sections) in ACCOUNTS.items():
  subset=[x for x in rows if x.get('sj_div') in sections];found=[]
  for tag in tags:
   found=[x for x in subset if x.get('account_id')==tag]
   if found:break
  if not found:found=[x for x in subset if re.sub(r'\s+','',x.get('account_nm','')) in {re.sub(r'\s+','',v) for v in names}]
  def vals(field):return {num(x.get(field)) for x in found if num(x.get(field)) is not None}
  current='thstrm_add_amount' if report!='11011' and sections==['IS','CIS'] else 'thstrm_amount'
  previous='frmtrm_add_amount' if report!='11011' and sections==['IS','CIS'] else 'frmtrm_amount'
  v=vals(current);p=vals(previous)
  if len(v)==1:facts[key]=v.pop();labels[key]=found[0].get('account_nm')
  elif len(v)>1:warnings.append(key+': multiple conflicting accounts')
  if len(p)==1:prior[key]=p.pop()
 if 'cfo' in facts and 'ppe' in facts and 'intangible' in facts:
  facts['capex']=abs(facts['ppe'])+abs(facts['intangible']);facts['fcf']=facts['cfo']-facts['capex']
 if 'revenue' in facts:
  facts['revenue_growth']=growth(facts['revenue'],prior.get('revenue'))
  facts['operating_margin']=facts.get('operating_income',0)/facts['revenue']*100 if 'operating_income' in facts and facts['revenue']>0 else None
 receipts=sorted({x.get('rcept_no') for x in rows if re.fullmatch(r'\d{14}',str(x.get('rcept_no')))})
 if len(receipts)!=1:raise ValueError('receipt_conflict')
 return {'status':'ok','year':year,'report':report,'basis':basis,'currency':'KRW','facts':facts,'previous':prior,'account_names':labels,'warnings':warnings,'receipt':receipts[0],'source_url':'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+receipts[0],'checked_at':NOW.isoformat(),'scope':'연결 우선, 없을 때만 개별; 중간실적은 동기간 누적. 미래 EPS는 검증하지 않음.'}
class Dart:
 def __init__(self,key):self.key=key;self.calls=0;self.success=0;self.errors=[];self.started=time.monotonic();self.codes={}
 def request(self,endpoint,params):
  if self.calls>=140 or time.monotonic()-self.started>360:raise ValueError('bounded_call_budget')
  self.calls+=1
  url='https://opendart.fss.or.kr/api/'+endpoint+'?'+urllib.parse.urlencode({'crtfc_key':self.key,**params})
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PersonalFinancialResearch/1.0'}),timeout=12) as r:return r.read(18_000_000)
  except Exception as e:raise ValueError('request_failed_'+type(e).__name__) from None
  finally:time.sleep(.10)
 def corpmap(self):
  raw=self.request('corpCode.xml',{})
  if not raw.startswith(b'PK'):
   try:code=ET.fromstring(raw).findtext('status')
   except ET.ParseError:code='invalid_response'
   raise ValueError('DART_'+str(code))
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   doc=ET.fromstring(z.read(next(n for n in z.namelist() if n.lower().endswith('.xml'))))
  self.codes={x.findtext('stock_code').strip():x.findtext('corp_code').strip() for x in doc.findall('list') if x.findtext('stock_code') and x.findtext('stock_code').strip()}
  if len(self.codes)<10:raise ValueError('corpmap_empty')
 def statement(self,symbol,year,report,basis=None):
  corp=self.codes.get(symbol)
  if not corp:raise ValueError('corp_code_not_found')
  choices=[basis] if basis else ['CFS','OFS']
  for fs in choices:
   raw=self.request('fnlttSinglAcntAll.json',{'corp_code':corp,'bsns_year':year,'reprt_code':report,'fs_div':fs})
   try:d=json.loads(raw)
   except ValueError:raise ValueError('invalid_json') from None
   code=d.get('status')
   if code=='013' and fs=='CFS' and not basis:continue
   if code!='000':raise ValueError('DART_'+str(code))
   self.success+=1
   return extract(d,corp,year,report,fs)
  raise ValueError('DART_013')
def compare(row,annual):
 if annual.get('status')!='ok':return []
 h=row.get('history') or {};end=h.get('filing_period')
 if end!=str(annual['year'])+'-12-31':return []
 out=[]
 for k in ('revenue','operating_income','eps','fcf','cfo'):
  x=num(h.get(k));y=num(annual['facts'].get(k))
  if x is None or y is None:continue
  tol=.01 if k=='eps' else max(1,abs(y)*1e-7);diff=x-y
  out.append({'field':k,'widget_value':x,'official_value':y,'difference':diff,'tolerance':tol,'status':'matched' if abs(diff)<=tol else 'difference','source_url':annual['source_url'],'period':end,'basis':annual['basis']})
 return out
def reason(text,source,kind,field=None,value=None):return {'text':text,'source_url':source,'type':kind,'field':field,'value':value}
def evaluate(row,official,peers,now=NOW):
 h=row.get('history') or {};f=row.get('forecasts') or {};t=row.get('targets') or {};b=row.get('balance') or {};src=row.get('sources') or {};old=row.get('assessment') or {}
 annual=official.get('annual') or {};interim=official.get('interim') or {};comparison=compare(row,annual)
 matches={x['field'] for x in comparison if x['status']=='matched'};differences=[x['field'] for x in comparison if x['status']=='difference']
 proof=row.get('official_history') or {};pa=age(proof.get('checked_at'),now)
 existing=set(proof.get('matched') or []) if pa is not None and 0<=pa<=1.5 else set()
 verified=('revenue' in matches and 'operating_income' in matches and bool(matches&{'fcf','cfo'})) or {'revenue','eps','fcf'}.issubset(existing)
 conf='공식 실적 대조 확인' if verified else '공식 대조 일부/미완료'
 positives=[];risks=[];unknown=[];blocked=[]
 official_url=annual.get('source_url') or proof.get('source_url') or src.get('official')
 if row.get('status')!='current':blocked.append('최근 완료 거래일의 시세가 아님')
 if row.get('period_integrity',{}).get('status')!='ok':blocked+=row.get('period_integrity',{}).get('issues') or ['예상 EPS·재무 기준일 불명확']
 if row.get('model_integrity',{}).get('status')=='needs_sector_model':blocked.append('현재 일반기업 평가모형을 적용할 수 없는 업종')
 ha=age(h.get('filing_period'),now)
 if ha is None or not 0<=ha<=RULES['annual_max_days']:blocked.append('과거 연간 실적의 기준일이 오래됐거나 미확인')
 if differences:blocked.append('공식 원문과 다른 숫자: '+', '.join(differences))
 if proof.get('issues'):blocked.append('기존 공식 대조에서 계정·단위 차이 있음')
 if row.get('technical',{}).get('recent_split'):blocked.append('주식분할 전후의 주당수치 기준 확인 필요')
 op=num(h.get('operating_income'));fcf=num(h.get('fcf'));rev=num(h.get('revenue'));margin=num(h.get('operating_margin'));pastgrowth=num(h.get('revenue_growth'));eps=num(h.get('eps'))
 if op is not None and op>0 and fcf is not None and fcf>0:
  positives.append(reason('본업 흑자와 FCF 양수: 영업이익률 '+f'{margin:.1f}%' if margin is not None else '본업 흑자와 FCF 양수',official_url if verified else src.get('cashflow'),'공시 대조' if verified else '제공처 실적','fcf',fcf))
 else:
  if op is None or fcf is None:unknown.append('영업이익·FCF 원자료')
  else:risks.append(reason('영업손실 또는 FCF 비양수: 이익의 질·설비투자 원인 확인',src.get('cashflow'),'관측 위험','fcf',fcf))
 if eps is not None and eps<=0:risks.append(reason('보고 EPS가 0 이하: 흑자전환 예상과 확정 실적을 구분',src.get('official'),'관측 위험','eps',eps))
 fg=num(f.get('eps_growth_next_fy_pct'));er=num(f.get('eps_revision30_pct'));gap=num(t.get('median_gap_pct'));leverage=num(b.get('net_debt_ebitda'));es=num(f.get('spread'));ts=num(t.get('spread'))
 counts=[num(f.get('analysts')),num(t.get('analysts'))]
 for value,label in [(fg,'예상 EPS 성장'),(er,'예상 EPS 30일 변화'),(leverage,'부채 부담'),(gap,'현재 가격과 전망 비교')]:
  if value is None:unknown.append(label)
 if any(x is None or x<5 for x in counts):unknown.append('최소 5명의 전망 표본')
 if f.get('status')!='ok' or t.get('status')!='ok':unknown.append('유효한 EPS·목표가 범위')
 if fg is not None and fg>0 and er is not None and er>=-3:
  positives.append(reason(f'다음 FY 예상 EPS {fg:+.1f}%, 같은 FY 30일 조정 {er:+.1f}%',src.get('estimates'),'애널리스트 전망','eps_growth_next_fy_pct',fg))
 else:
  if fg is not None and fg<=0:risks.append(reason('다음 FY 예상 EPS가 늘지 않음',src.get('estimates'),'전망 위험','eps_growth_next_fy_pct',fg))
  if er is not None and er<-3:risks.append(reason(f'EPS 전망이 30일 동안 {er:.1f}% 하향',src.get('estimates'),'전망 위험','eps_revision30_pct',er))
 if leverage is not None and leverage<=3:positives.append(reason(f'순차입금/EBITDA {leverage:.2f}배'+(' · 순현금 구조' if leverage<0 else ' · 설정한 3배 이내'),src.get('balance'),'제공처 재무','net_debt_ebitda',leverage))
 elif leverage is not None:risks.append(reason(f'순차입금/EBITDA {leverage:.2f}배로 설정한 3배 초과',src.get('balance'),'관측 위험','net_debt_ebitda',leverage))
 if es is None or ts is None:unknown.append('전망 상·하단 편차')
 elif es>.5 or ts>.8:risks.append(reason(f'EPS 편차 {es*100:.0f}% / 목표가 편차 {ts*100:.0f}%: 전망 불확실성이 큼',src.get('estimates'),'전망 위험','eps_spread',es))
 if interim.get('status')=='ok':
  ig=num(interim['facts'].get('revenue_growth'));iop=num(interim['facts'].get('operating_income'));ip=num(interim['previous'].get('operating_income'));og=growth(iop,ip)
  if ig is not None:positives.append(reason(f"{interim['year']}년 누적 공식 매출 전년동기 대비 {ig:+.1f}%",interim['source_url'],'최신 공시','interim_revenue_growth',ig)) if ig>=0 else None
  if ig is not None and ig<=-10 or og is not None and og<=-20:risks.append(reason('최근 공식 누적 매출·영업이익이 큰 폭 감소: 연간 전망만으로 매수 판단하지 않음',interim['source_url'],'최신 공시 위험','interim_revenue_growth',ig))
 elif row.get('market')=='KR':unknown.append('최근 분기·반기 공시 확인')
 pe=num(f.get('next_fy_pe'));pgroup=peers.get((row.get('market'),row.get('sector')),[])
 group=[(s,p) for s,p in pgroup if s!=row['symbol']];peer=None
 if pe is not None and pe>0 and len(group)>=3:
  med=median(p for s,p in group);peer={'median':med,'count':len(group),'symbols':[s for s,p in group],'current':pe,'premium_pct':growth(pe,med),'basis':'같은 수집표의 동일 국가·산업. 사업구성·EPS 조정 차이 미통제. 적정배수 아님.'}
 if gap is not None:positives.append(reason(f'목표가 중앙값과 종가 차이 {gap:+.1f}%'+(' · 20% 여유 기준 통과' if gap>=20 else ' · 20% 여유 기준 미달'),src.get('estimates'),'가격 가정','target_gap',gap))
 liquid=next((x.get('ok') for x in old.get('checks',[]) if x.get('key')=='liquidity'),None)
 if liquid is False:risks.append(reason('평균 거래대금 기준 미달: 체결·변동 위험',src.get('history'),'유동성 위험'))
 if row.get('size_group')=='micro':risks.append(reason('초소형 기업: 변동성과 거래대금 위험',src.get('history'),'규모 위험'))
 if blocked:state,label='insufficient','자료 충돌 · 투자판단 제외'
 elif risks:state,label='avoid','현재는 투자 우선순위 낮음'
 elif unknown:state,label='insufficient','핵심 근거 부족 · 판단 제외'
 elif gap is not None and gap<20:state,label='price_wait','사업은 양호 · 가격을 기다림'
 elif not verified:state,label='conditional','투자 매력은 있으나 공식 대조 필요'
 else:state,label='attractive','현재 가격에서 투자 매력 있음'
 verdict={'attractive':'이익·현금흐름, 이익 전망, 가격 여유, 재무 부담을 함께 충족해 우선 투자 대상으로 판단합니다.','conditional':'가격·실적 조건은 긍정적이지만 공식 실적 대조가 끝나지 않아 확정 후보와 분리합니다.','price_wait':'사업과 이익 전망은 통과했지만 지금 가격에서 요구하는 여유가 부족합니다.','avoid':'주가가 싸 보이는지보다 아래 실제 위험을 먼저 해소해야 합니다.','insufficient':'기업이 나쁘다는 뜻이 아니라, 현재 자료로 투자할 만하다고 말할 근거가 부족합니다.'}[state]
 crit=[{'label':'본업 흑자·FCF 양수','pass':op is not None and op>0 and fcf is not None and fcf>0},{'label':'예상 EPS 성장·최근 전망 유지','pass':fg is not None and fg>0 and er is not None and er>=-3},{'label':'현재 가격 대비 20% 전망 여유','pass':gap is not None and gap>=20},{'label':'과도하지 않은 부채·전망 편차','pass':leverage is not None and leverage<=3 and es is not None and es<=.5 and ts is not None and ts<=.8},{'label':'과거 핵심 실적 공식 대조','pass':verified},{'label':'기준일·유동성·업종모형 정상','pass':not blocked and liquid is True}]
 return {'symbol':row['symbol'],'state':state,'label':label,'verdict':verdict,'horizon':'장기 2~5년 관점 · 개인 자금용도 판단 별도','why':positives,'risks':risks,'missing':list(dict.fromkeys(blocked+unknown)),'criteria':crit,'confidence':conf,'official_comparison':comparison,'official':official,'peer_context':peer,'price_condition':old.get('price_condition'),'price_condition_usable':not blocked,'invalidation':['동일 FY 예상 EPS가 30일 동안 3% 넘게 하향될 때','최근 누적 공시 매출 -10% 또는 영업이익 -20% 이하일 때','목표가·EPS 변화로 가격여유가 사라지거나 부채·현금흐름 악화 시'],'input_price':row.get('price'),'input_price_session':row.get('price_session'),'input_forecast_eps':f.get('next_fy',{}).get('avg'),'method_version':'investment-case-1.0','not_probability':True,'no_guarantee':True}
def main():
 path=Path('stock-opportunity-data.json');raw=path.read_bytes();d=json.loads(raw);rows=d['companies'];key=os.environ.get('DART_API_KEY','').strip();client=Dart(key);auth={'key_configured':bool(key),'status':'pending' if not key else 'not_tested','checked_at':NOW.isoformat(),'success_responses':0,'calls':0};officials={}
 if key:
  try:client.corpmap();auth['status']='corp_lookup_ok'
  except Exception as e:auth['status']='request_failed';auth['error']=str(e);client.codes={}
  for row in rows:
   if row.get('market')!='KR' or not client.codes:continue
   entry={};period=row.get('history',{}).get('filing_period','')
   if not re.fullmatch(r'20\d{2}-12-31',period):continue
   try:entry['annual']=client.statement(row['symbol'],int(period[:4]),'11011')
   except Exception as e:entry['annual']={'status':'unavailable','error':str(e)}
   if entry['annual'].get('status')=='ok':
    report='11014' if NOW.month>=11 else '11012' if NOW.month>=8 else '11013' if NOW.month>=5 else None
    if report:
     try:entry['interim']=client.statement(row['symbol'],NOW.year,report,entry['annual']['basis'])
     except Exception as e:entry['interim']={'status':'unavailable','error':str(e)}
   officials[row['symbol']]=entry
  auth.update(calls=client.calls,success_responses=client.success,status='authenticated' if client.success else auth['status'])
 peers={}
 for r in rows:
  pe=num(r.get('forecasts',{}).get('next_fy_pe'))
  if r.get('status')=='current' and r.get('period_integrity',{}).get('status')=='ok' and pe is not None and pe>0:peers.setdefault((r.get('market'),r.get('sector')),[]).append((r['symbol'],pe))
 cases=[evaluate(r,officials.get(r['symbol'],{}),peers) for r in rows]
 counts={s:sum(c['state']==s for c in cases) for s in ('attractive','conditional','price_wait','avoid','insufficient')}
 out={'version':'investment-case-1.0','generated_at':datetime.now(timezone.utc).isoformat(),'source_generated_at':d['generated_at'],'source_sha256':hashlib.sha256(raw).hexdigest(),'auth':auth,'counts':counts,'rules':RULES,'companies':cases,'source_count':len(rows),'scope':'검증된 사실·제공처 전망·명시된 가격 가정을 분리한 자동 투자 의견. 확실한 수익/상승확률이 아니며 투자전략 성과검증 전.','reference':'https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020'}
 text=json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)
 if key and key in text:raise RuntimeError('Secret leakage blocked')
 Path('stock-investment-cases.json').write_text(text+'\n')
 Path('stock-investment-cases-summary.json').write_text(json.dumps({k:out[k] for k in ('version','generated_at','source_generated_at','source_count','auth','counts')},ensure_ascii=False,indent=2)+'\n')
 print('DART:',auth['status'],'responses',client.success,'cases',counts)
if __name__=='__main__':main()
