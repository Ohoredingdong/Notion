"""Independent extension proof; never embed source monetary values.

Re-fetch a known annual filing for a new research candidate. Reject issuer,
period, basis and units not explicitly identified. Small provider rounding
residuals are shown, not silently removed. Forecast accuracy is NOT audited.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,urllib.request
from bs4 import BeautifulSoup
import update_stock_opportunities as m

SOURCE='https://kind.krx.co.kr/external/2026/03/18/000195/20260318000896/11011.htm'

def compact(s):return re.sub(r'\s+','',s)

def number(s):
 t=compact(s).replace(',','').replace('−','-')
 if t in ('','-','—','–'):return 0.0 if t else None
 if t.startswith('(') and t.endswith(')'):t='-'+t[1:-1]
 return float(t) if re.fullmatch(r'[-+]?\d+(?:\.\d+)?',t) else None

def parse_leeno(body,period):
 if period!='2025-12-31':raise ValueError('등록 원문 기간과 새 입력기간 다름; 원문 URL 갱신 필요')
 soup=BeautifulSoup(body,'html.parser');plain=compact(soup.get_text(' ',strip=True))
 if '리노공업' not in plain[:60000]:raise ValueError('회사명 식별 실패')
 if '연결재무제표작성대상에해당하지않습니다' not in plain:raise ValueError('연결대상이 없는 회사의 개별 재무제표인지 확인 불가')
 state=None;buffer='';annual=False;unit=False;found={}
 aliases={'매출액':'revenue','영업이익':'operating_income','당기순이익':'net_income','희석주당이익(단위:원)':'eps','희석주당이익':'eps','영업활동현금흐름':'cfo','유형자산의취득':'ppe','무형자산의취득':'intang'}
 for node in soup.find_all(['p','table','h1','h2','h3']):
  if node.find_parent('table') is not None:continue
  text=node.get_text(' ',strip=True);s=compact(text[:260])
  if re.match(r'4[-.]2[.]?포괄손익계산서',s):state='income';buffer='';annual=False;unit=False
  elif re.match(r'4[-.]4[.]?현금흐름표',s):state='cash';buffer='';annual=False;unit=False
  elif re.match(r'(?:4[-.][135]|5[.]).*',s):state=None
  if state is None:continue
  buffer=(buffer+' '+text[:900])[-2200:];context=compact(buffer)
  if '2025.01.01' in context and '2025.12.31' in context:annual=True
  if '단위:원' in context:unit=True
  if node.name!='table' or not annual or not unit:continue
  for tr in node.find_all('tr'):
   cells=tr.find_all(['td','th'],recursive=False)
   if len(cells)<4:continue
   label=compact(cells[0].get_text(' ',strip=True));key=aliases.get(label)
   if key is None:continue
   if (key in ('cfo','ppe','intang'))!=(state=='cash'):continue
   vals=[number(td.get_text(' ',strip=True)) for td in cells[1:]]
   if len(vals)!=3 or any(v is None for v in vals):continue
   old=found.get(key)
   if old is not None and old!=vals[0]:raise ValueError('동일 계정의 값이 복수로 달라 비교 중지')
   found[key]=vals[0]
   if key=='revenue':found['revenue_previous']=vals[1]
 required={'revenue','revenue_previous','operating_income','net_income','eps','cfo','ppe','intang'}
 if not required.issubset(found):raise ValueError('원문 추출 누락: '+', '.join(sorted(required-set(found))))
 found['capex']=abs(found['ppe'])+abs(found['intang']);found['fcf']=found['cfo']-found['capex'];found['revenue_growth']=(found['revenue']/found['revenue_previous']-1)*100;found['operating_margin']=found['operating_income']/found['revenue']*100
 return found

def reconcile(hist,ref):
 result=[]
 for field in m.FIELDS:
  x=m.N(hist.get(field));y=m.N(ref.get(field))
  if x is None or y is None:result.append({'field':field,'status':'unverified','reason':'위젯 또는 원문 값 없음'});continue
  tolerance=.02 if field in ('revenue_growth','operating_margin') else .005 if field=='eps' else max(1,abs(y)*1e-8)
  diff=x-y;ok=abs(diff)<=tolerance
  result.append({'field':field,'widget_value':x,'official_value':y,'difference':diff,'allowed_absolute_difference':tolerance,'accepted':ok,'status':'match' if diff==0 else 'rounding_match' if ok else 'mismatch','reason':'비율 0.02%p / EPS 0.005원 / 금액 원문 대비 0.000001% 이내의 제공처 반올림 허용. 차이를 그대로 표시.'})
 return result

def main():
 d=json.loads(Path('stock-opportunity-data.json').read_text());record={'checked_at':datetime.now(timezone.utc).isoformat(),'source_url':SOURCE,'scope':'리노공업 2025년 개별 재무제표; 연결 대상 없음 명시','fields':[]}
 r=next((r for r in d['companies'] if r['symbol']=='058470'),None)
 if r:
  try:
   request=urllib.request.Request(SOURCE,headers={'User-Agent':'StockResearchAudit/1.0','Accept':'text/html'})
   with urllib.request.urlopen(request,timeout=25) as response:body=response.read(8_000_000);charset=response.headers.get_content_charset()
   try:text=body.decode(charset or 'utf-8')
   except (UnicodeDecodeError,LookupError):text=body.decode('euc-kr')
   refs=parse_leeno(text,r.get('history',{}).get('filing_period'));record['sha256']=hashlib.sha256(body).hexdigest();record['fields']=reconcile(r['history'],refs);record['status']='compared';record['period']='2025-12-31';record['raw_derived']=refs
   r['extension_audit']=record;r['sources']['official']=SOURCE
   matched=[x['field'] for x in record['fields'] if x.get('accepted')];issues=[x['field'] for x in record['fields'] if x['status']=='mismatch']
   r['official_history']={'status':'current','matched':matched,'issues':issues,'checked_at':record['checked_at'],'source_url':SOURCE,'period':'2025-12-31','basis':'개별 재무제표 · 연결대상 없음','note':'동일기간 숫자 대조, 미세 제공처 절사 차이는 허용범위와 함께 공개. 미래 추정치 검증이 아님.'}
  except Exception as e:record['status']='unavailable';record['error']=type(e).__name__+': '+str(e);r['extension_audit']=record;r.setdefault('errors',[]).append({'field':'extension_audit','error':record['error']})
 for row in d['companies']:
  row['assessment']=m.assessment(row)
  eps=m.N(row.get('history',{}).get('eps'))
  if eps is not None and eps<=0:
   row['assessment']['risks'].append('과거 보고 EPS가 0 이하: 회계상 적자와 조정 EPS 회복 전망을 구분해야 함')
   if row['assessment']['state'] not in ('data',):row['assessment']['state']='risk';row['assessment']['label']='회계상 손실·회복 가설 확인';row['assessment']['next_action']='예상 이익이 흑자여도 과거 손실의 원인과 회복 근거를 공식 실적에서 확인하세요. 과거 GAAP EPS와 조정 예상 EPS를 직접 비교하지 않습니다.'
 for k in ('ready','verify','price','risk','data'):d['counts'][k]=sum(r['assessment']['state']==k for r in d['companies'])
 d['extension_verified_at']=record['checked_at'];d['extension_audit_policy']='신규 후보 중 공식 원문을 확보한 리노공업만 항목별 재조회·대조. 다른 후보는 자동으로 검증 완료로 확장하지 않음.'
 Path('stock-opportunity-extension-audit.json').write_text(json.dumps(m.core.clean(record),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 Path('stock-opportunity-data.json').write_text(json.dumps(m.core.clean(d),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 Path('stock-opportunity-summary.json').write_text(json.dumps({'generated_at':d['generated_at'],'counts':d['counts'],'extension_audit':record['status'],'states':[{'symbol':r['symbol'],'size':r.get('size_group'),'state':r['assessment']['state'],'score':r['priority']['score']} for r in d['companies']]},ensure_ascii=False,indent=2)+'\n')
 print('extension',record['status'],d['counts'])

if __name__=='__main__':main()
