"""Official financial reconciliation. No model-generated financial reference values.

Source adapters: SEC CompanyFacts / inline XBRL; OpenDART full annual CFS;
period-limited KIND annual tables and company GAAP earnings releases.
Never bypass a denied request or treat an old successful fetch as a new check.
Run from repository root: python scripts/stock_official_audit.py
"""
from __future__ import annotations
import hashlib
import io
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

ROOT = Path('.')
REPORT = ROOT / 'stock-official-audit.json'
CONFIG = ROOT / 'stock-verification-sources.json'
SOURCE = ROOT / 'stock-value-radar-data.json'
VERSION = 'official-audit-v1'
FIELDS = ('revenue', 'revenue_growth', 'operating_income', 'operating_margin', 'net_income', 'eps', 'capex', 'fcf')
LABELS = dict(zip(FIELDS, ('매출액', '매출 성장률', '영업이익', '영업이익률', '순이익', 'EPS', 'CAPEX', 'FCF')))
TAGS = {
 'revenue': ['RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax','Revenues','SalesRevenueNet'],
 'operating_income': ['OperatingIncomeLoss'],
 'net_income': ['NetIncomeLossAvailableToCommonStockholdersBasic','NetIncomeLoss'],
 'net_income_total': ['ProfitLoss'],
 'eps': ['EarningsPerShareDiluted'],
 'eps_basic': ['EarningsPerShareBasic'],
 'operating_cash_flow': ['NetCashProvidedByUsedInOperatingActivities'],
 'ppe': ['PaymentsToAcquirePropertyPlantAndEquipment'],
}
ALLOWED = {'www.sec.gov','data.sec.gov','opendart.fss.or.kr','kind.krx.co.kr','www.microsoft.com','nvidianews.nvidia.com','investor.nvidia.com','ir.aboutamazon.com','www.apple.com','ir.tesla.com'}

def now():
 return datetime.now(timezone.utc).isoformat()

def load(p, default):
 try: return json.loads(Path(p).read_text(encoding='utf-8'))
 except (OSError, ValueError): return default

def save(p, data):
 p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
 temp = p.with_suffix(p.suffix + '.tmp')
 temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
 temp.replace(p)

def num(v):
 if v is None or isinstance(v, bool): return None
 try:
  if isinstance(v, str):
   v = v.strip().replace(',', '').replace('−', '-')
   if v in ('', '-', '—', '–', 'N/A'): return None
   if v.startswith('(') and v.endswith(')'): v = '-' + v[1:-1]
  n = Decimal(str(v))
  return float(n) if n.is_finite() else None
 except (ValueError, TypeError, InvalidOperation): return None

def compact(s):
 return re.sub(r'\s+', '', str(s)).lower()

def label(s):
 s = re.sub(r'\(주[^)]*\)', '', str(s))
 s = re.sub(r'^[\sⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ\d.ㆍ]+', '', s)
 return re.sub(r'[\s():：·ㆍ,]', '', s).lower()

def digest(obj):
 return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def row_key(row):
 return digest({k: row.get(k) for k in ('symbol','filing_period','currency','statement_basis') + FIELDS})

class SourceError(Exception):
 def __init__(self, code, message):
  super().__init__(message); self.code = code

class Client:
 def __init__(self): self.last = 0.0; self.memo = {}
 def fetch(self, url, params=None):
  if urllib.parse.urlsplit(url).hostname not in ALLOWED:
   raise SourceError('host_not_allowed', '허용된 공식 출처가 아닙니다.')
  key = url + ('?' + urllib.parse.urlencode(params) if params else '')
  if key in self.memo: return self.memo[key]
  time.sleep(max(0.0, 0.55 - (time.monotonic()-self.last)))
  ua = os.environ.get('SEC_USER_AGENT') or 'StockValueRadar/1.0 (+https://github.com/Ohoredingdong/Notion; personal research)'
  req = urllib.request.Request(key, headers={'User-Agent':ua,'Accept':'application/json,text/html;q=0.9,*/*;q=0.5'})
  self.last = time.monotonic()
  try:
   with urllib.request.urlopen(req, timeout=22) as response:
    if urllib.parse.urlsplit(response.url).hostname not in ALLOWED:
     raise SourceError('redirect_not_allowed', '공식 출처 외 리다이렉트')
    body = response.read(24000001)
    if len(body)>24000000: raise SourceError('size_limit', '원문이 안전한 처리 크기를 초과했습니다.')
    charset = response.headers.get_content_charset() or 'utf-8'
   record = {'url':url,'sha256':hashlib.sha256(body).hexdigest(),'fetched_at':now(),'bytes':len(body)}
   self.memo[key] = (body, charset, record)
   return self.memo[key]
  except urllib.error.HTTPError as e:
   raise SourceError('http_'+str(e.code), '공식 서버 HTTP '+str(e.code)+'; 우회하지 않고 검증 보류') from None
  except (urllib.error.URLError, TimeoutError, OSError):
   raise SourceError('network_error', '공식 서버 연결 실패 또는 시간 초과') from None
 def json(self, url, params=None):
  b, _, record = self.fetch(url, params)
  try: return json.loads(b), record
  except ValueError: raise SourceError('invalid_json', '공식 응답이 JSON이 아닙니다.') from None

def fact(value, tag, unit, end, record, start=None, resolution=1, basis='consolidated'):
 return {'value':num(value),'account':tag,'unit':unit,'period':end,'start':start,'basis':basis,'resolution':resolution,'source_url':record['url'],'document_sha256':record['sha256'],'fetched_at':record['fetched_at']}

def unique(items):
 vals = {x['value'] for x in items if x.get('value') is not None}
 if len(vals)>1: return None
 return items[0] if items and vals else None

def derive(fs):
 def calc(key, deps, fn, desc, unit, resolution):
  if not all(k in fs and fs[k].get('value') is not None for k in deps): return
  xs = [fs[k] for k in deps]
  if len({(x['period'], x['source_url']) for x in xs})!=1: return
  try: value=fn(*[x['value'] for x in xs])
  except (ZeroDivisionError, ValueError): return
  if not math.isfinite(value): return
  base=dict(xs[0]);base.update(value=value,account=desc,unit=unit,resolution=resolution,components={k:fs[k]['value'] for k in deps})
  fs[key]=base
 calc('operating_margin',['operating_income','revenue'],lambda op,r:op/r*100,'영업이익 / 매출액 ×100','percent',0.01)
 if fs.get('revenue_previous',{}).get('value',0)>0:
  # Previous-year value is preserved with its own period; explicitly derived over the year pair.
  a=fs.get('revenue');b=fs.get('revenue_previous')
  if a and b and a['source_url']==b['source_url']:
   x=dict(a);x.update(value=(a['value']/b['value']-1)*100,account='전년 동기 대비 매출 성장률',unit='percent',resolution=0.01,prior_period=b['period'],components={'current':a['value'],'prior':b['value']});fs['revenue_growth']=x
 if 'ppe' in fs:
  pp=fs['ppe'];parts=['ppe']
  if pp['unit']=='KRW' and 'intangible' not in fs: return
  if 'intangible' in fs: parts.append('intangible')
  calc('capex',parts,lambda *a:sum(abs(x) for x in a),'현금 지급 유형자산 취득'+(' + 무형자산 취득' if len(parts)>1 else ''),pp['unit'],sum(fs[k]['resolution'] for k in parts))
  if 'capex' in fs:
   fs['capex']['definition']='ppe_plus_intangibles' if len(parts)>1 else 'ppe_cash'
   calc('fcf',['operating_cash_flow','capex'],lambda c,k:c-k,'영업활동현금흐름 − CAPEX',pp['unit'],fs['capex']['resolution']+fs.get('operating_cash_flow',{}).get('resolution',0))
   if 'fcf' in fs: fs['fcf']['definition']=fs['capex']['definition']

def from_sec_json(raw, cik, target, record):
 if int(raw.get('cik',0))!=int(cik): raise SourceError('issuer_mismatch','SEC 발행회사 CIK가 다릅니다.')
 facts=raw.get('facts',{}).get('us-gaap',{})
 # Bind all facts to ONE annual filing and exact annual duration; never mix years/tags silently.
 anchors=[]
 for tag in TAGS['revenue']:
  for x in facts.get(tag,{}).get('units',{}).get('USD',[]):
   try: length=(date.fromisoformat(x['end'])-date.fromisoformat(x['start'])).days
   except (KeyError,ValueError): continue
   if x.get('form') in ('10-K','10-K/A') and 330<=length<=380 and abs((date.fromisoformat(x['end'])-date.fromisoformat(target)).days)<=7:
    anchors.append(x)
 if not anchors: raise SourceError('period_not_found','요청 연간기간의 SEC 10-K 재무자료가 없습니다.')
 anchor=max(anchors,key=lambda x:(x.get('filed',''),x.get('end','')))
 acc=anchor['accn'];end=anchor['end'];start=anchor['start'];fs={}
 source=dict(record); source['url']='https://www.sec.gov/Archives/edgar/data/'+str(int(cik))+'/'+acc.replace('-','')+'/'+acc+'-index.html'
 for key,tags in TAGS.items():
  unit='USD/shares' if key.startswith('eps') else 'USD'
  for tag in tags:
   xs=[]
   for x in facts.get(tag,{}).get('units',{}).get(unit,[]):
    if x.get('accn')==acc and x.get('start')==start and x.get('end')==end:
     xs.append(fact(x['val'],tag,unit,end,source,start,resolution=0.01 if key.startswith('eps') else 1))
   selected=unique(xs)
   if selected: fs[key]=selected;break
 for tag in TAGS['revenue']:
  ys=[]
  for x in facts.get(tag,{}).get('units',{}).get('USD',[]):
   try: length=(date.fromisoformat(x['end'])-date.fromisoformat(x['start'])).days; gap=(date.fromisoformat(end)-date.fromisoformat(x['end'])).days
   except (KeyError,ValueError): continue
   if x.get('accn')==acc and 330<=length<=380 and 330<=gap<=380:
    ys.append(fact(x['val'],tag,'USD',x['end'],source,x['start']))
  y=unique(ys)
  if y:fs['revenue_previous']=y;break
 derive(fs)
 return {'period':end,'start':start,'kind':'SEC 10-K XBRL','receipt':acc,'facts':fs,'document':source,'api_document':record}

def from_ixbrl(body, target, cfg, record):
 soup=BeautifulSoup(body,'html.parser');contexts={}
 for el in soup.find_all(lambda t:t.name and t.name.lower().split(':')[-1]=='context'):
  if el.find(lambda t:t.name and t.name.lower().split(':')[-1] in ('explicitmember','typedmember')):continue
  get=lambda k:el.find(lambda t:t.name and t.name.lower().split(':')[-1]==k)
  ident=get('identifier');st=get('startdate');en=get('enddate')
  if not ident or int(ident.get_text().strip())!=int(cfg['cik']) or not st or not en: continue
  contexts[el.get('id')]=(st.get_text().strip(),en.get_text().strip())
 pairs=[]
 for st,en in contexts.values():
  try:
   if 330<=(date.fromisoformat(en)-date.fromisoformat(st)).days<=380 and abs((date.fromisoformat(en)-date.fromisoformat(target)).days)<=7:pairs.append((st,en))
  except ValueError:pass
 if not pairs:raise SourceError('period_not_found','원문의 연간 연결 XBRL 컨텍스트를 확인하지 못했습니다.')
 st,en=max(pairs,key=lambda p:p[1]);fs={}
 for key,tags in TAGS.items():
  for tag in tags:
   found=[]
   for el in soup.find_all(lambda t:t.name and t.name.lower().split(':')[-1]=='nonfraction'):
    if el.get('name','').split(':')[-1]!=tag or contexts.get(el.get('contextref'))!=(st,en):continue
    if str(el.get('unitref','')).lower() not in ('usd','usd/shares','usdshares','usdper-share','usd-per-share','usdsharesunit'):continue
    v=num(el.get_text(' ',strip=True))
    if v is None:continue
    v*=10**int(el.get('scale',0));v=-abs(v) if el.get('sign')=='-' else v
    decimals=el.get('decimals','0');resolution=0 if decimals.upper()=='INF' else 10**(-int(decimals))
    found.append(fact(v,tag,'USD/shares' if key.startswith('eps') else 'USD',en,record,st,resolution))
   val=unique(found)
   if val:fs[key]=val;break
 # Previous year uses identical concept/entity and no dimensional contexts.
 for tag in TAGS['revenue']:
  found=[]
  for el in soup.find_all(lambda t:t.name and t.name.lower().split(':')[-1]=='nonfraction'):
   p=contexts.get(el.get('contextref'))
   if not p or el.get('name','').split(':')[-1]!=tag:continue
   try: length=(date.fromisoformat(p[1])-date.fromisoformat(p[0])).days;gap=(date.fromisoformat(en)-date.fromisoformat(p[1])).days
   except ValueError:continue
   if 330<=length<=380 and 330<=gap<=380:
    v=num(el.get_text(' ',strip=True))
    if v is not None:found.append(fact(v*10**int(el.get('scale',0)),tag,'USD',p[1],record,p[0],1e6))
  val=unique(found)
  if val:fs['revenue_previous']=val;break
 if not fs:raise SourceError('parse_error','표준 XBRL 계정 추출 실패')
 derive(fs)
 return {'period':en,'start':st,'kind':'SEC 10-K inline XBRL','facts':fs,'document':record}

KR_NAMES={
 'revenue':['매출액','수익매출액','영업수익','매출'],
 'operating_income':['영업이익','영업이익손실'],
 'net_income':['지배기업의소유주에게귀속되는당기순이익손실','지배기업의소유주에게귀속되는당기순이익','지배기업소유주지분','지배기업의소유주','지배기업소유주','지배기업의소유주에게귀속되는지분'],
 'net_income_total':['당기순이익','당기순이익손실','연결당기순이익','연결총당기순이익'],
 'eps':['희석주당이익','희석주당순이익','희석주당이익보통주','희석주당순이익단위원','보통주희석주당이익','희석주당이익손실'],
 'eps_basic':['기본주당이익','기본주당순이익','기본주당이익보통주'],
 'operating_cash_flow':['영업활동현금흐름','영업활동으로인한현금흐름','영업활동으로부터의현금흐름'],
 'ppe':['유형자산의취득','유형자산취득'],
 'intangible':['무형자산의취득','무형자산취득']
}

def table_rows(table):
 for tr in table.find_all('tr'):
  if tr.find_parent('table') is not table:continue
  cells=tr.find_all(['td','th'],recursive=False)
  if not cells:continue
  texts=[x.get_text(' ',strip=True) for x in cells]
  lead=next((i for i,x in enumerate(texts) if x.strip()),None)
  if lead is None:continue
  yield texts[lead],texts[lead+1:]

def values_from_cells(cells):
 out=[]
 for c in cells:
  t=re.sub(r'\s+','',c).replace('$','').replace('₩','')
  if re.fullmatch(r'\(?[-+−]?\d[\d,]*(?:\.\d+)?\)?',t):out.append(num(t))
  elif t in ('-','—','–'):out.append(0.0)
 return out

def from_kind(body,target,cfg,record,kind='kind_html'):
 soup=BeautifulSoup(body,'html.parser');plain=compact(soup.get_text(' ',strip=True))
 if not any(compact(a) in plain[:60000] for a in cfg.get('aliases',[])):
  raise SourceError('issuer_mismatch','문서에서 대상 회사명을 확인하지 못했습니다.')
 # Only the consolidated statement sections, never subsidiaries in note tables or separate financials.
 state=None;scope='';buffer='';fs={};collect={};current_year=int(target[:4]);context={}
 for node in soup.find_all(['p','table','h1','h2','h3']):
  if node.find_parent('table') is not None:continue
  text=node.get_text(' ',strip=True);norm=compact(text)
  if node.name!='table':
   buffer=(buffer+' '+text)[-2600:]
   n=compact(buffer)
   for word,k in [('연결손익계산서','income'),('연결포괄손익계산서','income'),('연결현금흐름표','cash'),('연결재무상태표','balance')]:
    if word in compact(text):state=k;scope='consolidated';context={};break
   if ('별도재무제표' in norm or re.match(r'4[.．]재무제표',norm) or '연결재무제표주석' in norm):state=None
   continue
  n=compact(buffer+' '+text[:650])
  for word,k in [('연결손익계산서','income'),('연결포괄손익계산서','income'),('연결현금흐름표','cash'),('연결재무상태표','balance')]:
   if word in compact(text[:200]):state=k;scope='consolidated';context={}
  if not state or state=='balance':continue
  if re.search(r'단위[:：]?백만원',n):context['scale']=1000000
  elif re.search(r'단위[:：]?천원',n):context['scale']=1000
  elif re.search(r'단위[:：]?원',n):context['scale']=1
  if str(current_year)+'.01.01' in n or str(current_year)+'년1월1일' in n:context['annual']=True
  if str(current_year)+'.12.31' in n or str(current_year)+'년12월31일' in n:context['end']=True
  if not (context.get('annual') and context.get('end') and context.get('scale')):continue
  for raw,cells in table_rows(node):
   lab=label(raw);vals=values_from_cells(cells)
   if not vals:continue
   for key,names in KR_NAMES.items():
    if lab not in names:continue
    if (state=='cash')!=(key in ('operating_cash_flow','ppe','intangible')):continue
    scale=1 if key.startswith('eps') else context['scale']
    x=fact(vals[0]*scale,raw,'KRW/shares' if key.startswith('eps') else 'KRW',target,record,str(current_year)+'-01-01',scale)
    collect.setdefault(key,[]).append(x)
    if key=='revenue' and len(vals)>1:
     collect.setdefault('revenue_previous',[]).append(fact(vals[1]*scale,raw,'KRW',str(current_year-1)+'-12-31',record,str(current_year-1)+'-01-01',scale))
  # Do not extend buffer with full note tables.
 for key,xs in collect.items():
  x=unique(xs)
  if x:fs[key]=x
 if not fs:raise SourceError('parse_error','연결 연간 표·단위·계정을 확실하게 식별하지 못했습니다.')
 derive(fs)
 return {'period':target,'start':str(current_year)+'-01-01','kind':'KIND 주총 참고서류 수록 재무표 (최종 감사보고서 아님)' if kind=='kind_proxy' else 'KIND 사업보고서 연결재무제표','facts':fs,'document':record}

US_NAMES={
 'revenue':['totalrevenue','totalrevenues','totalnetsales','netsales','revenue'],
 'operating_income':['operatingincome','incomefromoperations'],
 'net_income':['netincome','netincomeattributabletocommonstockholders','netincomeattributabletocommonshareholders'],
 'eps':['diluted','dilutedearningspershare','dilutednetincomepershare'],
 'operating_cash_flow':['netcashprovidedbyoperatingactivities','netcashprovidedbyusedinoperatingactivities'],
 'ppe':['additionstopropertyandequipment','purchasesofpropertyandequipment','paymentstoacquirepropertyplantandequipment','purchasesofpropertyandequipmentexcludingfinanceleases','purchasesofpropertyandequipmentincludingfinanceleases']
}

def from_release(body,target,cfg,record,spec):
 soup=BeautifulSoup(body,'html.parser');plain=compact(soup.get_text(' ',strip=True))
 if not any(compact(a) in plain[:60000] for a in cfg.get('aliases',[])):
  raise SourceError('issuer_mismatch','기업 공식 발표의 회사 식별 실패')
 index=spec['index'];prior=spec['prior_index'];fs={};candidates={}
 for table in soup.find_all('table'):
  txt=compact(table.get_text(' ',strip=True));header=txt[:1600]
  # A full GAAP statement must contain an annual column, not a reconciliation or isolated quarter.
  if not any(k in header for k in ('twelvemonthsended','yearended','yearsend','fiscalyearended')):continue
  if 'non-gaap' in header[:300] or 'asadjusted' in header[:300]:continue
  rows=list(table_rows(table));alllabels={label(r[0]) for r in rows}
  income=any(x in alllabels for x in US_NAMES['revenue']) and any(x in alllabels for x in US_NAMES['operating_income'])
  cf=any('netcashprovidedby' in x for x in alllabels)
  if not (income or cf):continue
  if str(target[:4]) not in header:continue
  if 'million' not in compact(table.find_previous().get_text(' ',strip=True) if table.find_previous() else '') and 'million' not in header:
   # Company statement units are explicitly named in the release.
   before=compact(' '.join(table.find_all_previous(string=True,limit=30)))
   if 'million' not in before:continue
  eps_seen=False
  for raw,cells in rows:
   lab=label(raw)
   if 'earningspershare' in lab or 'netincomepershare' in lab:eps_seen=True
   if 'weightedaverage' in lab or 'sharesused' in lab:eps_seen=False
   vals=values_from_cells(cells)
   if len(vals)<=max(index,prior):continue
   for key,names in US_NAMES.items():
    if lab not in names:continue
    if key=='eps' and lab=='diluted' and not eps_seen:continue
    if key in ('ppe','operating_cash_flow') and not cf:continue
    if key not in ('ppe','operating_cash_flow') and not income:continue
    scale=1 if key=='eps' else 1000000
    x=fact(vals[index]*scale,raw,'USD/shares' if key=='eps' else 'USD',spec['period'],record,resolution=.01 if key=='eps' else scale)
    candidates.setdefault(key,[]).append(x)
    if key=='revenue':candidates.setdefault('revenue_previous',[]).append(fact(vals[prior]*scale,raw,'USD',str(int(spec['period'][:4])-1)+spec['period'][4:],record,resolution=scale))
 for k,xs in candidates.items():
  x=unique(xs)
  if x:fs[k]=x
 if not fs:raise SourceError('parse_error','공식 발표에서 같은 회계연도의 GAAP 연간 열을 확정하지 못했습니다.')
 derive(fs)
 return {'period':spec['period'],'kind':'기업 공식 실적발표 GAAP (SEC 최종공시와 별개)','facts':fs,'document':record}

DART_IDS={'revenue':['ifrs-full_Revenue'], 'operating_income':['dart_OperatingIncomeLoss'], 'net_income':['ifrs-full_ProfitLossAttributableToOwnersOfParent'], 'net_income_total':['ifrs-full_ProfitLoss'], 'eps':['ifrs-full_DilutedEarningsLossPerShare'], 'eps_basic':['ifrs-full_BasicEarningsLossPerShare'], 'operating_cash_flow':['ifrs-full_CashFlowsFromUsedInOperatingActivities'], 'ppe':['ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities'], 'intangible':['ifrs-full_PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities']}

def from_dart(raw,target,corp,record):
 if raw.get('status')!='000':raise SourceError('dart_'+str(raw.get('status')),'OpenDART 상태 '+str(raw.get('status'))+'; 키·접근권한·공시유무 확인')
 rows=raw.get('list',[]);year=target[:4];fs={};receipt=None
 for key,ids in DART_IDS.items():
  matches=[]
  for x in rows:
   if str(x.get('corp_code'))!=corp or str(x.get('bsns_year'))!=year or x.get('reprt_code')!='11011':continue
   sj=x.get('sj_div');is_cf=key in ('operating_cash_flow','ppe','intangible')
   if (is_cf and sj!='CF') or (not is_cf and sj not in ('IS','CIS')):continue
   if x.get('account_id') not in ids and label(x.get('account_nm')) not in KR_NAMES.get(key,[]):continue
   if x.get('currency') not in (None,'','KRW'):continue
   value=num(x.get('thstrm_amount'))
   if value is None:continue
   receipt=x.get('rcept_no');source=dict(record)
   if receipt:source['url']='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+str(receipt)
   matches.append(fact(value,x.get('account_id')+' / '+x.get('account_nm'),'KRW/shares' if key.startswith('eps') else 'KRW',target,source,year+'-01-01',1))
   if key=='revenue' and num(x.get('frmtrm_amount')) is not None:
    fs['revenue_previous']=fact(num(x['frmtrm_amount']),x.get('account_nm'),'KRW',str(int(year)-1)+'-12-31',source,str(int(year)-1)+'-01-01',1)
  val=unique(matches)
  if val:fs[key]=val
 if not fs:raise SourceError('parse_error','같은 회사·연도의 연결 주요계정을 확인하지 못했습니다.')
 derive(fs)
 return {'period':target,'kind':'OpenDART 사업보고서 연결 XBRL','receipt':receipt,'facts':fs,'document':record}

def collect(row,cfg,client,corps):
 target=row.get('filing_period');attempts=[]
 if not target:raise SourceError('missing_period','위젯 대상기간이 없습니다.')
 sources=[]
 if cfg.get('cik'):
  url='https://data.sec.gov/api/xbrl/companyfacts/CIK'+str(cfg['cik']).zfill(10)+'.json'
  try:
   raw,record=client.json(url);s=from_sec_json(raw,cfg['cik'],target,record);sources.append(s)
  except SourceError as e:attempts.append({'url':url,'code':e.code,'message':str(e)})
 else:
  key=os.getenv('DART_API_KEY','').strip()
  if key and row['symbol'] in corps:
   url='https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json'
   try:
    raw,record=client.json(url,{'crtfc_key':key,'corp_code':corps[row['symbol']],'bsns_year':target[:4],'reprt_code':'11011','fs_div':'CFS'})
    sources.append(from_dart(raw,target,corps[row['symbol']],record))
   except SourceError as e:attempts.append({'url':url,'code':e.code,'message':str(e)})
  else:attempts.append({'url':'https://opendart.fss.or.kr/','code':'credential_required','message':'DART_API_KEY 미설정 또는 회사 고유번호 조회 실패; 한국 공시 API 자동탐색 보류'})
 if sources:return sources[0],attempts
 for spec in cfg.get('fallbacks',[]):
  try:
   delta=abs((date.fromisoformat(spec['period'])-date.fromisoformat(target)).days)
   if delta>7:continue
   body,charset,record=client.fetch(spec['url'])
   try:text=body.decode(charset)
   except (UnicodeDecodeError,LookupError):text=body.decode('utf-8',errors='replace')
   if spec['type']=='ixbrl':parsed=from_ixbrl(text,target,cfg,record)
   elif spec['type'].startswith('kind_'):parsed=from_kind(text,spec['period'],cfg,record,spec['type'])
   else:parsed=from_release(text,target,cfg,record,spec)
   sources.append(parsed)
  except SourceError as e:attempts.append({'url':spec['url'],'code':e.code,'message':str(e)})
  except (ValueError,KeyError,TypeError,OverflowError):attempts.append({'url':spec['url'],'code':'parse_error','message':'문서구조·단위·계정 처리 실패; 검증 보류'})
 if sources:return max(sources,key=lambda s:len(s['facts'])),attempts
 return None,attempts

def compare(row,source):
 output=[]
 for key in FIELDS:
  actual=num(row.get(key));ref=(source or {}).get('facts',{}).get(key)
  item={'field':key,'label':LABELS[key],'widget_value':actual,'widget_period':row.get('filing_period'),'widget_currency':row.get('currency'),'official_value':ref.get('value') if ref else None,'status':'unverified','reason':'공식 원문 수집 또는 해당 계정 추출이 필요합니다.'}
  if not ref:output.append(item);continue
  item.update(official_period=ref['period'],official_unit=ref['unit'],official_account=ref['account'],source_url=ref['source_url'],document_sha256=ref['document_sha256'],fetched_at=ref['fetched_at'],official_basis=ref.get('basis'),formula=ref.get('components'))
  if actual is None:item.update(status='widget_missing',reason='공식 숫자는 있으나 위젯 수치가 없습니다.')
  elif row.get('filing_period')!=ref['period']:item.update(status='period_mismatch',reason='결산일이 다릅니다. 52/53주 회계연도와 제공처의 달력말일 표기 차이를 확인해야 합니다.')
  elif ref['unit'] not in ('percent',row.get('currency'),str(row.get('currency'))+'/shares'):item.update(status='unit_mismatch',reason='통화 또는 단위가 다릅니다. 환산해 일치로 처리하지 않습니다.')
  elif '별도' in str(row.get('statement_basis','')) or 'OFS' in str(row.get('statement_basis','')):item.update(status='basis_mismatch',reason='위젯 별도재무제표와 원문 연결재무제표가 다릅니다.')
  else:
   delta=actual-ref['value'];resolution=max(float(ref.get('resolution',0))*.5, .005 if key=='eps' else .005 if key in ('revenue_growth','operating_margin') else .5)
   tolerance=resolution+abs(ref['value'])*1e-10
   if key in ('revenue_growth','operating_margin'):tolerance=max(tolerance,.015)
   item.update(difference=delta,difference_pct=(delta/abs(ref['value'])*100 if ref['value'] else None),tolerance=tolerance)
   if abs(delta)<=tolerance:item.update(status='match',reason='같은 기간·통화의 원문 수치와 표시 반올림 허용범위에서 일치합니다.')
   elif key in ('fcf','capex'):item.update(status='definition_check',reason='금액이 다릅니다. 유형·무형자산, 처분대금, 금융리스 등 CAPEX 범위와 FCF 정의를 먼저 확인하세요.')
   elif key in ('net_income','eps'):item.update(status='account_check',reason='금액이 다릅니다. 지배주주/전체 순이익, 기본/희석 EPS 및 주식분할·중단영업 기준을 확인하세요.')
   else:item.update(status='mismatch',reason='같은 기간·단위의 수치가 반올림 허용범위 밖에서 다릅니다. 정정공시·표준화 조정·데이터 오류를 확인하세요.')
  output.append(item)
 return output

def corp_map(client):
 key=os.getenv('DART_API_KEY','').strip()
 if not key:return {}
 try:
  raw,_,_=client.fetch('https://opendart.fss.or.kr/api/corpCode.xml',{'crtfc_key':key})
  z=zipfile.ZipFile(io.BytesIO(raw));root=ET.fromstring(z.read('CORPCODE.xml'))
  return {str(x.findtext('stock_code','')).strip():str(x.findtext('corp_code','')).strip() for x in root.findall('list')}
 except Exception:return {}

def main():
 started=now();raw=load(SOURCE,{})
 config=load(CONFIG,{})
 if not raw.get('rows'):raise RuntimeError('검증할 위젯 스냅샷이 없습니다.')
 previous=load(REPORT,{});old={r['symbol']:r for r in previous.get('companies',[])}
 client=Client();corps=corp_map(client);companies=[]
 for row in raw['rows']:
  symbol=row['symbol'];cfg=config.get('companies',{}).get(symbol)
  source=None;attempts=[]
  if cfg:
   try:source,attempts=collect(row,cfg,client,corps)
   except Exception as e:attempts=[{'code':e.code if isinstance(e,SourceError) else 'internal_error','message':str(e) if isinstance(e,SourceError) else '수집 처리 실패; 수치를 생성하지 않음'}]
  else:attempts=[{'code':'source_not_configured','message':'회사 공식 출처 설정 없음'}]
  fields=compare(row,source)
  counts=Counter(x['status'] for x in fields)
  rowstatus='differences' if any(x['status'] in ('mismatch','account_check','definition_check','unit_mismatch','basis_mismatch','period_mismatch') for x in fields) else 'partial' if counts['match'] else 'unavailable'
  if counts['match']==len(FIELDS):rowstatus='matched'
  entry={'symbol':symbol,'name':row.get('name'),'market':row.get('market'),'input_key':row_key(row),'input_period':row.get('filing_period'),'checked_at':now(),'status':rowstatus,'counts':dict(counts),'source':source,'attempts':attempts,'fields':fields,'last_successful_fetch_at':source['document']['fetched_at'] if source else old.get(symbol,{}).get('last_successful_fetch_at')}
  if not source and old.get(symbol,{}).get('source'):
   entry['previous_success']={'checked_at':old[symbol].get('checked_at'),'period':old[symbol]['source'].get('period'),'url':old[symbol]['source']['document'].get('url'),'notice':'이전 성공 기록이며 이번 검증 결과로 재사용하지 않았습니다.'}
  companies.append(entry)
 summary=Counter(x['status'] for r in companies for x in r['fields'])
 report={'version':VERSION,'generated_at':now(),'started_at':started,'input_generated_at':raw.get('generated_at'),'input_sha256':digest(raw),'scope':'고정 관심종목의 연간 재무 수치 대조. 주가·미래 전망·확률·신용위험 검증은 별도입니다.','counts':{'companies':len(companies),'source_fetched':sum(bool(x['source']) for x in companies),'fields':len(companies)*len(FIELDS),**dict(summary)},'companies':companies,'limitations':['KIND 주총 참고서류와 기업 실적발표는 최종 감사보고서가 아닙니다. 문서 유형을 확인하세요.','기간이 달라지면 과거 HTML 주소를 새 기간의 검증자료로 재사용하지 않습니다.','DART 인증키가 없거나 SEC 접근이 차단되면 해당 경로의 최신 공시 자동탐색이 제한됩니다.','기존 원시 수치를 자동으로 수정하거나 투자 주문을 실행하지 않습니다.']}
 save(REPORT,report)
 # Append bounded audit history: observations have time, source hashes and per-field status.
 hist=load('stock-official-audit-history.json',{'entries':[]})
 entries=hist.get('entries',[])
 entries.append({'checked_at':report['generated_at'],'input_sha256':report['input_sha256'],'counts':report['counts'],'companies':[{'symbol':r['symbol'],'period':r['input_period'],'status':r['status'],'source_sha256':r['source']['document']['sha256'] if r['source'] else None,'fields':{x['field']:x['status'] for x in r['fields']}} for r in companies]})
 save('stock-official-audit-history.json',{'entries':entries[-120:]})
 # A concise, machine-readable deployment result, never a success-only green flag.
 print(json.dumps(report['counts'],ensure_ascii=False))
 return report

if __name__=='__main__':main()
