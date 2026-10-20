"""Fail-closed due-diligence gate, NOT a forecast of investment returns.
The original screen opinion is retained separately. Unknown is never a pass.
Thresholds are a conservative research policy, not accounting standards.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import hashlib,json,math
VERSION='strict-green-1.0'
IDS=['inputs','official','cash_quality','working_capital','earnings_quality','debt','business','valuation','macro','governance','forecast','liquidity']
TERMS={
'inputs':('기준일·단위·대상 확인','같은 회사의 같은 기준 숫자인지'),
'official':('핵심 실적 공식 대조','매출·이익·투자 후 현금을 원문과 비교'),
'cash_quality':('3년 이익의 현금화','장부상 이익이 실제 현금으로 들어왔는지'),
'working_capital':('매출채권·재고 점검','외상대금과 안 팔린 재고가 쌓이는지'),
'earnings_quality':('이익 지속성·일회성 손익','일시적인 이익인지 본업이 좋아진 것인지'),
'debt':('차입금 만기·상환 여력','곧 갚을 빚과 쓸 돈을 감당할 수 있는지'),
'business':('성장 원인·고객·경쟁력','왜 앞으로도 벌 수 있는지 회사 자료로 확인'),
'valuation':('독립 가치평가·하락 시나리오','목표가 외의 계산으로 가격과 손실 위험 비교'),
'macro':('금리·환율 노출','이 회사의 매출·비용·빚에 어떤 영향인지'),
'governance':('감사의견·우발채무·최근 공시','숫자 밖의 중요한 위험이 있는지'),
'forecast':('예상 EPS 기준·수정 추세','누가 어떤 기준으로 예상했는지'),
'liquidity':('거래대금·기업행사','실제로 거래할 수 있는지, 분할 기준이 맞는지')}
TOPICS={
'earnings_quality':['one_off_items','normalised_earnings'],
'debt':['maturities_12m','interest_and_leases','restricted_cash','covenants','committed_capex'],
'business':['products_customers','growth_drivers','competition','customer_concentration','capex_returns'],
'valuation':['eps_basis','fcfe_basis','assumptions','peer_history','downside'],
'macro':['sales_cost_currencies','fx_hedges','fixed_floating_debt','rate_sensitivity'],
'governance':['audit_opinion','going_concern','contingent_liabilities','dilution','latest_disclosures'],
'forecast':['period_and_gaap','estimate_dates','independent_crosscheck'],
'working_capital':['receivables','inventory','growth_reconciliation'],
'cash_quality':['three_year_cash_reconciliation']}
POLICY={'max_snapshot_hours':18,'max_review_days':30,'max_annual_days':460,'cash_conversion_floor':.8,'working_capital_excess_pp':10,'income_decline_flag_pct':-15,'cfo_decline_flag_pct':-15,'fcf_decline_flag_pct':-20,'valuation_discount':.20,'stress_loss_review_pct':-30,'max_revision_decline_pct':-3}
def n(x):
 if x is None or isinstance(x,bool):return None
 try:v=float(x);return v if math.isfinite(v) else None
 except (ValueError,TypeError):return None
def stamp(x):
 try:
  d=datetime.fromisoformat(str(x).replace('Z','+00:00'));return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
 except (ValueError,TypeError):return None
def fresh(x,days,now):
 d=stamp(x);return d is not None and -300<=(now-d).total_seconds()<=days*86400
def change(a,b):
 a,b=n(a),n(b);return (a/b-1)*100 if a is not None and b is not None and b>0 else None
def same(a,b,relative=1e-7,absolute=.01):
 a,b=n(a),n(b);return a is not None and b is not None and abs(a-b)<=max(absolute,abs(b)*relative)
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def fingerprint(row):
 h=row.get('history') or {};f=row.get('forecasts') or {}
 return digest({'symbol':row.get('symbol'),'currency':row.get('currency'),'history':{k:h.get(k) for k in ('filing_period','revenue','operating_income','eps','cfo','capex','fcf')},'next_eps':(f.get('next_fy') or {}).get('avg'),'forecast_end':f.get('current_fy_end_provider'),'split':(row.get('technical') or {}).get('recent_split'),'source_receipts':row.get('strict_source_receipts')})
def safe_url(s):
 try:
  u=urlparse(str(s));q=parse_qs(u.query)
  return u.scheme=='https' and bool(u.hostname) and not u.username and not any(k.lower() in ('crtfc_key','api_key','token','access_token') for k in q)
 except ValueError:return False
def official_url(s):return safe_url(s) and urlparse(s).hostname in ('dart.fss.or.kr','kind.krx.co.kr','www.sec.gov','sec.gov','data.sec.gov')
def document_review(row,records,area,now):
 """Validate a maintainer's source-backed record, NOT semantic truth by URL.
 No invented approval records ship with this release. Mere links cannot pass.
 """
 record=records.get(row['symbol']) or {};r=(record.get('sections') or {}).get(area) or {}
 if record.get('fundamental_fingerprint')!=fingerprint(row):return None
 if not r.get('reviewer') or not fresh(r.get('reviewed_at'),1 if area=='governance' else POLICY['max_review_days'],now):return None
 if r.get('decision') not in ('resolved','unresolved'):return None
 findings=r.get('findings') or {}
 if not all(isinstance(findings.get(k),str) and len(findings[k].strip())>=20 for k in TOPICS[area]):return None
 sources=r.get('sources') or []
 if not sources:return None
 for s in sources:
  if not safe_url(s.get('url')) or not s.get('locator') or not s.get('publisher'):return None
  if not fresh(s.get('published_at'),POLICY['max_annual_days'],now) or stamp(s['published_at'])>stamp(r['reviewed_at']):return None
  h=s.get('document_sha256','')
  if len(h)!=64 or any(c not in '0123456789abcdef' for c in h):return None
  if len(str(s.get('evidence_excerpt','')).strip())<30:return None
 if area=='forecast' and len({s['publisher'].strip().lower() for s in sources})<2:return None
 if area in ('business','debt','governance','earnings_quality') and not any(official_url(s['url']) for s in sources):return None
 return r
def valuation_models(r,currency):
 """Common-equity per-share models. FCFE includes debt cash flows, not EBITDA.
 Inputs are reviewed assumptions. Stress is a scenario, never a loss bound.
 Neither valuation uses analyst target prices.
 """
 m=r.get('models') or {}
 if m.get('currency')!=currency or m.get('share_basis')!='diluted_common':raise ValueError('currency_or_share_basis')
 a=m.get('normalised_eps_pe') or {};b=m.get('fcfe_dcf') or {}
 if b.get('cashflow_definition')!='after_debt_cashflows_to_common_equity':raise ValueError('fcfe_definition')
 shares=n(b.get('diluted_shares'))
 if shares is None or shares<=0:raise ValueError('shares')
 outputs={}
 for scenario in ('conservative','base','stress'):
  x=a.get(scenario) or {};eps=n(x.get('eps'));pe=n(x.get('pe'))
  if eps is None or eps<=0 or pe is None or not 1<=pe<=80:raise ValueError('eps_multiple')
  y=b.get(scenario) or {};cash=y.get('annual_fcfe');ke=n(y.get('cost_of_equity'));g=n(y.get('terminal_growth'))
  if not isinstance(cash,list) or not 3<=len(cash)<=10 or any(n(v) is None for v in cash):raise ValueError('fcfe_path')
  if ke is None or not .04<=ke<=.4 or g is None or not -.02<=g<=.04 or ke-g<.02:raise ValueError('discount_terminal')
  values=[n(v) for v in cash]
  if values[-1]<=0:raise ValueError('terminal_cashflow')
  pv=sum(v/(1+ke)**(i+1) for i,v in enumerate(values));pv+=values[-1]*(1+g)/(ke-g)/(1+ke)**len(values);dcf=pv/shares
  if not math.isfinite(dcf) or dcf<=0:raise ValueError('dcf_result')
  outputs[scenario]={'earnings_model':eps*pe,'fcfe_model':dcf,'lower_value':min(eps*pe,dcf)}
 for method in ('earnings_model','fcfe_model'):
  if not outputs['stress'][method]<=outputs['conservative'][method]<=outputs['base'][method]:raise ValueError('scenario_order')
 return outputs
def evaluate(row,case,raw,depth,macro,records,now=None):
 now=now or datetime.now(timezone.utc)
 row={**row,'strict_source_receipts':{k:(case.get('official',{}).get(k) or {}).get('receipt') for k in ('annual','interim')}}
 h=row.get('history') or {};f=row.get('forecasts') or {};src=row.get('sources') or {};checks=[]
 def add(key,status,why,values=None,urls=None):
  term,meaning=TERMS[key];checks.append({'id':key,'term':term,'meaning':meaning,'status':status,'explanation':why,'values':values or {},'source_urls':[u for u in (urls or [src.get('official')]) if safe_url(u)]})
 source_ok=fresh(raw.get('generated_at'),.75,now)
 aligned=case.get('input_price')==row.get('price') and case.get('input_price_session')==row.get('price_session') and case.get('input_forecast_eps')==(f.get('next_fy') or {}).get('avg')
 inputs=source_ok and aligned and row.get('status')=='current' and row.get('price_session')==(row.get('expected_session') or {}).get('date') and n(row.get('price')) is not None and row['price']>0 and (row.get('period_integrity') or {}).get('status')=='ok' and (row.get('model_integrity') or {}).get('status')=='ok' and fresh(h.get('filing_period'),460,now)
 add('inputs','pass' if inputs else 'blocked','원자료 기준일·가격·예상 EPS·회계기간·업종을 함께 대조했어요.' if inputs else '오래되거나 서로 다른 기준의 자료는 초록색에 쓰지 않아요.',{'price_session':row.get('price_session'),'financial_period':h.get('filing_period')})
 annual=(case.get('official') or {}).get('annual') or {};facts=annual.get('facts') or {};required=('revenue','operating_income','eps','cfo','capex','fcf')
 comparison={k:{'input':h.get(k),'official':facts.get(k),'match':same(h.get(k),facts.get(k),absolute=.01 if k=='eps' else 1)} for k in required}
 official=annual.get('status')=='ok' and str(annual.get('year'))+'-12-31'==h.get('filing_period') and annual.get('basis') in ('CFS','OFS') and annual.get('currency')==row.get('currency') and official_url(annual.get('source_url')) and fresh(annual.get('checked_at'),1.5,now) and all(x['match'] for x in comparison.values()) and all(n(facts.get(k)) is not None for k in ('cfo','capex','fcf')) and same(facts.get('fcf'),facts['cfo']-facts['capex'],absolute=1)
 add('official','pass' if official else 'missing','핵심 여섯 숫자와 FCF 산식을 같은 공식 재무표에서 대조했어요.' if official else '매출·영업이익·희석 EPS·CFO·CAPEX·FCF 전체가 같은 기준으로 확인되어야 해요.',comparison,[annual.get('source_url'),src.get('official')])
 dep=next((v for v in depth.get('companies',[]) if v.get('symbol')==row['symbol']),{});series=sorted(dep.get('series') or [],key=lambda v:v.get('period',''),reverse=True)[:3]
 series_ok=depth.get('source_generated_at')==raw.get('generated_at') and fresh(depth.get('generated_at'),.75,now) and len(series)==3 and series[0].get('period')==h.get('filing_period')
 if series_ok:series_ok=len({(s.get('basis'),s.get('currency'),s.get('source_type')) for s in series})==1 and all(s.get('currency')==row.get('currency') and official_url(s.get('source_url')) and all(n(s.get(k)) is not None for k in ('net_income','cfo','capex','fcf','revenue','operating_income')) for s in series)
 if series_ok:
  dates=[stamp(s['period']) for s in series];series_ok=all(dates) and all(330<=(dates[i]-dates[i+1]).days<=400 for i in (0,1))
 cash_flags=[];cash_values={}
 if series_ok:
  profits=sum(n(s['net_income']) for s in series);cfo=sum(n(s['cfo']) for s in series);ratio=cfo/profits if profits>0 else None
  cash_values={'three_year_cfo':cfo,'three_year_total_profit':profits,'cash_conversion':ratio}
  if ratio is None or ratio<.8:cash_flags.append('3년 합계 영업현금흐름이 합계 순이익의 80%에 못 미치거나 비교할 수 없어요.')
  if any(n(s['cfo'])<=0 for s in series):cash_flags.append('최근 3년 중 영업현금흐름이 양수가 아닌 해가 있어요.')
  names={'net_income':'당기순이익','operating_income':'영업이익','cfo':'영업현금흐름(CFO)','fcf':'FCF'}
  for k,threshold in [('net_income',-15),('operating_income',-15),('cfo',-15),('fcf',-20)]:
   v=change(series[0][k],series[1][k]);cash_values[k+'_yoy_pct']=v
   if v is not None and v<threshold:cash_flags.append(f'{names[k]}이 전년 대비 {v:.1f}%예요. 줄어든 원인을 확인해야 해요.')
  if n(series[0]['fcf'])<=0:cash_flags.append('최근 연간 FCF가 양수가 아니에요. 투자 목적과 자금조달을 확인해야 해요.')
 review=document_review(row,records,'cash_quality',now);cash_status='missing' if not series_ok else 'review' if cash_flags else 'pass'
 if cash_status=='review' and review and review['decision']=='resolved':cash_status='pass'
 add('cash_quality',cash_status,' / '.join(cash_flags) if cash_flags else '같은 연결범위의 3년 이익과 현금을 비교했어요.' if series_ok else '공식 출처의 같은 회계범위 3년 현금흐름이 더 필요해요.',cash_values,[s.get('source_url') for s in series])
 wc=[];wc_values={};wc_missing=False
 if series_ok:
  rg=change(series[0]['revenue'],series[1]['revenue']);wc_values['revenue_growth_pct']=rg
  for k in ('receivables','inventory'):
   x,y=n(series[0].get(k)),n(series[1].get(k));growth=change(x,y);wc_values[k+'_growth_pct']=growth
   if x==0 and y==0:continue
   if growth is None or rg is None:wc_missing=True
   elif growth-rg>10:wc.append(f"{ {'receivables':'매출채권','inventory':'재고자산'}[k]} 증가율이 매출 증가율보다 {growth-rg:.1f}%p 높아요.")
 else:wc_missing=True
 wr=document_review(row,records,'working_capital',now);ws='review' if wc else 'missing' if wc_missing else 'pass'
 if ws in ('review','missing') and wr and wr['decision']=='resolved':ws='pass'
 add('working_capital',ws,' / '.join(wc) or ('없는 금액을 0원으로 간주하지 않아요. 외상대금·재고 주석을 확인해야 해요.' if wc_missing else '외상대금·재고가 매출보다 과도하게 늘었는지 비교했어요.'),wc_values,[src.get('balance'),src.get('official')])
 for key in ('earnings_quality','debt','business','macro','governance'):
  reviewed=document_review(row,records,key,now);status='missing';detail='공식 자료를 읽은 근거·위치·날짜와 결론이 아직 등록되지 않았어요.';values={};urls=[src.get('official')]
  if reviewed:
   status='pass' if reviewed['decision']=='resolved' else 'review';detail='문서의 해당 위치와 반대 근거까지 검토한 기록이 있어요.' if status=='pass' else '문서를 확인했지만 해결되지 않은 위험이 남아 있어요.';values={'reviewed_at':reviewed['reviewed_at'],'findings':reviewed['findings']};urls=[s['url'] for s in reviewed['sources']]
  if key=='debt' and status=='pass':
   v=reviewed.get('amounts') or {};cash=n(v.get('unrestricted_cash'));inflow=n(v.get('stressed_operating_inflow_12m'));uses=n(v.get('all_committed_cash_uses_12m'))
   if v.get('currency')!=row.get('currency') or any(x is None or x<0 for x in (cash,inflow,uses)) or not fresh(v.get('as_of'),180,now):status='missing';detail='현금의 사용제한과 1년 내 상환·이자·리스·투자 약정을 같은 통화로 확인해야 해요.'
   elif cash+inflow<uses:status='review';detail='스트레스 가정의 1년 현금유입·보유현금보다 현금지출 약정이 커요.'
   values['amounts']=v
  if key=='macro' and (not fresh(macro.get('generated_at'),.75,now) or not (macro.get('indicators') or {}).get('fed_policy')):status='missing';detail='회사별 금리·환율 노출과 현재 거시자료를 함께 확인해야 해요.'
  add(key,status,detail,values,urls)
 value_review=document_review(row,records,'valuation',now);val={};vs='missing';explain='애널리스트 목표가만으로는 통과하지 못해요. 이익가치와 주주 현금흐름의 별도 계산·하락 시나리오가 필요해요.'
 if value_review:
  try:
   val=valuation_models(value_review,row.get('currency'));price=n(row.get('price'));conservative=val['conservative']['lower_value'];reference=conservative*(1-POLICY['valuation_discount']);stress_change=change(val['stress']['lower_value'],price)
   val.update(reference_price=reference,price=price,stress_change_pct=stress_change,formula='두 평가의 보수적 값 중 낮은 값 × 0.80',is_loss_bound=False)
   vs='pass' if value_review['decision']=='resolved' and price is not None and 0<price<=reference and stress_change is not None and stress_change>=-30 else 'review'
   explain='목표가와 별개로 두 평가의 계산과 하락 가정을 확인했어요.' if vs=='pass' else '보수적 평가 대비 가격 여유가 부족하거나 하락 시나리오의 손실 부담이 커요.'
  except (ValueError,TypeError,KeyError,OverflowError):explain='가치평가의 단위·주식수·현금흐름 정의·가정 순서가 맞지 않아 가격 확인을 멈췄어요.'
 add('valuation',vs,explain,val,[s['url'] for s in value_review['sources']] if value_review else [src.get('estimates'),src.get('official')])
 fr=document_review(row,records,'forecast',now);es=n(f.get('spread'));rev=n(f.get('eps_revision30_pct'));growth=n(f.get('eps_growth_next_fy_pct'));count=n(f.get('analysts'))
 fs='pass' if fr and fr['decision']=='resolved' and f.get('status')=='ok' and all(v is not None for v in (es,rev,growth,count)) and count>=5 and es<=.5 and rev>=-3 and growth>0 else 'missing'
 if rev is not None and rev<-3 or growth is not None and growth<=0 or es is not None and es>.5:fs='review'
 add('forecast',fs,'회사 자료와 독립된 전망을 같은 회계연도·조정 기준으로 비교해야 해요. 예상 자체가 사실로 바뀌는 것은 아니에요.',{'analysts':count,'eps_revision30_pct':rev,'eps_growth_pct':growth,'spread':es},[src.get('estimates')])
 tv=n((row.get('liquidity') or {}).get('avg_turnover20'));minimum=1e9 if row.get('market')=='KR' else 5e6
 liquidity=tv is not None and tv>=minimum and not (row.get('technical') or {}).get('recent_split') and row.get('size_group') not in ('micro','unknown',None)
 add('liquidity','pass' if liquidity else 'review' if tv is not None else 'missing','20일 거래대금과 분할·병합 표시를 확인했어요. 실제 호가·체결과는 달라요.',{'average_turnover20':tv,'required':minimum},[src.get('history')])
 checks.sort(key=lambda x:IDS.index(x['id']));green=len(checks)==len(IDS) and all(c['status']=='pass' for c in checks);needs=[c for c in checks if c['status']!='pass']
 return {'version':VERSION,'reviewed_at':now.isoformat(),'source_generated_at':raw.get('generated_at'),'input_price':row.get('price'),'input_price_session':row.get('price_session'),'input_forecast_eps':(f.get('next_fy') or {}).get('avg'),'fundamental_fingerprint':fingerprint(row),'green_eligible':green,'checks':checks,'passed':len(checks)-len(needs),'required':len(IDS),'next_checks':[{'term':c['term'],'meaning':c['meaning'],'reason':c['explanation'],'sources':c['source_urls']} for c in needs],'valuation':val,'valid_until':min(now+timedelta(hours=18),(stamp(raw.get('generated_at')) or now)+timedelta(hours=18)).isoformat(),'not_probability':True,'return_guarantee':False,'strategy_performance':'not_validated','scope':'명시한 실사 기준의 통과 여부. 미래 수익·손실한도·개인에게 맞는 투자임을 보장하지 않음.','record_limit':'문서 검토 기록의 출처·날짜·대상·필수항목을 검사합니다. 링크나 해시만으로 문장 내용의 진실까지 자동 증명하지 않습니다.'}
def apply_bundle(raw,cases,depth,macro,records,now=None):
 now=now or datetime.now(timezone.utc)
 if cases.get('source_generated_at')!=raw.get('generated_at'):raise ValueError('snapshot_generation_mismatch')
 rows={r['symbol']:r for r in raw.get('companies',[])}
 if len(rows)!=len(raw.get('companies',[])) or len({c['symbol'] for c in cases.get('companies',[])})!=len(cases.get('companies',[])) or set(rows)!={c['symbol'] for c in cases.get('companies',[])}:raise ValueError('issuer_set_mismatch')
 before=Counter(c['state'] for c in cases['companies']);reports=[]
 for case in cases['companies']:
  row=rows[case['symbol']]
  if 'screening_opinion' not in case:case['screening_opinion']={k:case.get(k) for k in ('state','label','verdict','confidence')}
  original=case['screening_opinion'];report=evaluate(row,case,raw,depth,macro,records,now);case['green_review']=report
  if report['green_eligible']:case.update(state='attractive',label='핵심 검증 통과 · 조건부 투자 후보',verdict='공식 실적·3년 현금·주요 위험·독립 가격평가의 명시 조건을 통과했어요. 그래도 주가는 떨어질 수 있어요.',confidence='명시된 12개 실사 조건 통과 · 수익 보장 아님')
  elif any(c['status']=='blocked' for c in report['checks']):case.update(state='insufficient',label='기준자료 확인 전 · 투자판단 제외',verdict='자료 기준이 맞지 않아 가격만 보고 투자 판단을 하지 않아요.',confidence='현재 자료 기준 미확인')
  elif any(c['status']=='review' for c in report['checks']):case.update(state='avoid',label='확인된 위험 원인부터 살펴봐요',verdict='이익·현금·재고·부채 등에서 검토가 필요한 신호가 있어요. 주가가 반드시 내린다는 뜻은 아니에요.',confidence='추가 실사 필요 · 위험 해소 미확인')
  else:
   keep=original['state'] if original['state'] in ('price_wait','avoid','insufficient') else 'conditional'
   case.update(state=keep,label='좋아 보이는 점은 있지만 핵심 검증이 남았어요',verdict='누락된 검증을 양호하다고 간주하지 않아요. 아래 남은 근거를 확인해야 해요.',confidence='검증 일부 완료 · 초록 기준 미충족')
  case['strict_invalidation']=['새 공시·정정공시로 사용한 숫자가 바뀔 때','같은 회사·기간·단위로 대조되지 않거나 자료가 만료될 때','현금·부채·고객·경쟁·감사의견 위험이 새로 생길 때','독립 가격평가의 가정이나 EPS 전망이 바뀔 때']
  reports.append({'symbol':row['symbol'],'name':row.get('name'),'previous_state':original['state'],'state':case['state'],**report})
 cases['counts']={s:sum(c['state']==s for c in cases['companies']) for s in ('attractive','conditional','price_wait','avoid','insufficient')}
 cases['green_policy']={'version':VERSION,'checked_at':now.isoformat(),'rules':POLICY,'required_ids':IDS,'all_checks_required':True,'no_guarantee':True}
 report={'version':VERSION,'generated_at':now.isoformat(),'source_generated_at':raw['generated_at'],'counts':cases['counts'],'previous_counts':dict(before),'companies':reports,'missing_counts':dict(Counter(c['term'] for r in reports for c in r['checks'] if c['status']=='missing')),'rules':POLICY,'scope':'자료·가정 검증 통과 여부. 예측 성공률은 산출하지 않음.'}
 return cases,report
def main():
 root=Path('.');read=lambda name:json.loads((root/name).read_text());rawbytes=(root/'stock-opportunity-data.json').read_bytes();raw=json.loads(rawbytes);cases=read('stock-investment-cases.json')
 if cases.get('source_sha256')!=hashlib.sha256(rawbytes).hexdigest():raise ValueError('source_content_mismatch')
 optional=lambda name:read(name) if (root/name).exists() else {};records=optional('stock-research-review-records.json').get('companies') or {}
 cases,report=apply_bundle(raw,cases,optional('stock-reading-depth.json'),optional('stock-market-context.json'),records)
 def write(name,d):(root/name).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 write('stock-investment-cases.json',cases)
 summary={k:cases[k] for k in ('version','generated_at','source_generated_at','source_count','auth','counts','final_integrity_check') if k in cases}
 summary['green_policy']=cases['green_policy'];summary['positive_companies']=[{'symbol':r['symbol'],'name':r['name'],'label':'핵심 검증 통과 · 조건부 후보'} for r in report['companies'] if r['green_eligible']]
 write('stock-investment-cases-summary.json',summary);write('stock-green-review.json',report);write('stock-green-review-summary.json',{k:v for k,v in report.items() if k!='companies'})
 print('Strict green:',len(report['companies']),'reviewed;',cases['counts'],'; source numbers unchanged')
if __name__=='__main__':main()
