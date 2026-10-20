"""Listing filters only. Never change research scores, prices or trade decisions.

US listing source: Nasdaq Trader symbol directory. KR listing uses the provider's
.KS/.KQ codes and exchange metadata. Dow is a separate, overlapping membership
flag, using State Street's dated DIA equity holdings (proxy, not S&P's licensed
constituent feed). Missing/stale source never becomes a negative membership claim.
"""
from __future__ import annotations
import csv,io,json,re,hashlib,zipfile,urllib.request
from pathlib import Path
from datetime import datetime,timedelta,timezone
from xml.etree import ElementTree as ET

NASDAQ='https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'
OTHER='https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'
DIA='https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-dia.xlsx'
NOW=datetime.now(timezone.utc)
N={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
PROVIDER={'KSC':'KOSPI','KOE':'KOSDAQ','KOS':'KOSPI','KOQ':'KOSDAQ','NMS':'NASDAQ','NGM':'NASDAQ','NCM':'NASDAQ','NAS':'NASDAQ','NYQ':'NYSE','NYS':'NYSE','ASE':'NYSE_AMERICAN','PCX':'NYSE_ARCA','BTS':'CBOE'}

def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'PersonalResearchMarketFilter/1.0','Accept':'*/*'})
 with urllib.request.urlopen(req,timeout=25) as r:
  body=r.read(8000000)
 if len(body)>=8000000:raise ValueError('Unexpected source size')
 return body

def directory(body,kind):
 text=body.decode('utf-8-sig');rows=list(csv.DictReader(io.StringIO(text),delimiter='|'))
 if not rows or ('Symbol' if kind=='nasdaq' else 'ACT Symbol') not in rows[0]:raise ValueError('Directory header mismatch')
 stamp=re.search(r'File Creation Time:\s*(\d{8})(?:\d{2}:?\d{2})?',text)
 if not stamp:raise ValueError('Directory creation date unavailable')
 asof=datetime.strptime(stamp.group(1),'%m%d%Y').date()
 if not -1<=(NOW.date()-asof).days<=7:raise ValueError('Directory source date is stale/future: '+str(asof))
 out={}
 for r in rows:
  if r.get('Test Issue')!='N':continue
  venue='NASDAQ' if kind=='nasdaq' else {'N':'NYSE','A':'NYSE_AMERICAN','P':'NYSE_ARCA','Z':'CBOE','V':'IEX'}.get(r.get('Exchange'),'OTHER')
  for key in ('Symbol','ACT Symbol','NASDAQ Symbol','Nasdaq Symbol','CQS Symbol'):
   sym=(r.get(key) or '').strip()
   if sym:out[sym]=venue
 return out,asof.isoformat()

def workbook_rows(body):
 """Read a bounded issuer holdings table using its OOXML cells; no workbook editing."""
 with zipfile.ZipFile(io.BytesIO(body)) as z:
  if sum(x.file_size for x in z.infolist())>30000000:raise ValueError('Unexpected workbook expansion')
  strings=[]
  if 'xl/sharedStrings.xml' in z.namelist():
   strings=[''.join(t.text or '' for t in si.findall('.//m:t',N)) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',N)]
  sheets=[]
  for name in sorted(n for n in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n)):
   rows=[]
   for row in ET.fromstring(z.read(name)).findall('.//m:sheetData/m:row',N):
    cells={}
    for cell in row.findall('m:c',N):
     col=re.sub('[0-9]','',cell.get('r',''));v=cell.find('m:v',N);value=v.text if v is not None else ''
     if cell.get('t')=='s':value=strings[int(value)] if value else ''
     elif cell.get('t')=='inlineStr':value=''.join(t.text or '' for t in cell.findall('.//m:t',N))
     cells[col]=value or ''
    rows.append(cells)
   sheets.append(rows)
 return sheets

def holdings(body):
 for rows in workbook_rows(body):
  intro=' '.join(str(v) for r in rows[:12] for v in r.values())
  if 'dow jones' not in intro.lower():continue
  asof=None
  for i,r in enumerate(rows[:15]):
   joined=' '.join(r.values())
   if not re.search(r'as\s*of|date',joined,re.I):continue
   for text in list(r.values())+(list(rows[i+1].values()) if i+1<len(rows) else []):
    text=re.sub(r'^(?:as\s*of|date)\s*[:：]?\s*','',text.strip(),flags=re.I)
    for form in ('%d-%b-%Y','%d-%b-%y','%b %d %Y','%b %d, %Y','%B %d, %Y','%Y-%m-%d','%m/%d/%Y','%d %b %Y'):
     try:asof=datetime.strptime(text,form).date();break
     except ValueError:pass
    if asof:break
    if re.fullmatch(r'\d{5}(?:\.\d+)?',text):
     asof=(datetime(1899,12,30)+timedelta(days=float(text))).date();break
   if asof:break
  if asof is None:raise ValueError('Holdings as-of date not found')
  if not -1<=(NOW.date()-asof).days<=7:raise ValueError('Holdings source is stale/future: '+str(asof))
  head=None
  for i,r in enumerate(rows):
   names={str(v).strip().lower():k for k,v in r.items()}
   tk=next((names[k] for k in ('ticker','ticker symbol','symbol') if k in names),None)
   nm=next((names[k] for k in ('name','security name','holding name') if k in names),None)
   if tk and nm:head=(i,tk,nm);break
  if head is None:raise ValueError('Holdings ticker/name columns missing')
  i,tk,nm=head;out={}
  for r in rows[i+1:]:
   sym=(r.get(tk) or '').strip();name=(r.get(nm) or '').strip()
   if name and not re.search('cash|currency|dollar',name,re.I) and re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,9}',sym):out[sym]=name
  if len(out)!=30:raise ValueError('Expected 30 distinct DIA equity holdings; found '+str(len(out)))
  return out,asof.isoformat()
 raise ValueError('DIA/Dow fund identity not found')

def classify(r,listing,provider):
 sym=r.get('source_symbol') or r.get('symbol') or '';country=r.get('market');warnings=[]
 if country=='KR':
  suffix='KOSDAQ' if sym.endswith('.KQ') else 'KOSPI' if sym.endswith('.KS') else None
  code=PROVIDER.get(r.get('exchange') or provider.get(sym,{}).get('exchange'))
  if suffix and code and suffix!=code:return 'UNKNOWN','conflict',['한국 거래소 코드와 종목 접미사가 다름']
  return suffix or code or 'UNKNOWN','provider_exchange_suffix',warnings
 if country=='US':
  if sym in listing:return listing[sym],'nasdaq_trader',warnings
  code=PROVIDER.get(r.get('exchange') or provider.get(sym,{}).get('exchange'))
  return code or 'UNKNOWN','provider_exchange' if code else 'unavailable',warnings
 return 'UNKNOWN','unavailable',warnings

def main():
 def read(name):
  try:return json.loads(Path(name).read_text(encoding='utf-8'))
  except (OSError,ValueError):return {}
 deep=read('stock-opportunity-data.json').get('companies',[]);wide=read('stock-opportunity-discovery.json').get('companies',[])
 if not deep:raise ValueError('Research universe unavailable')
 provider={r.get('source_symbol') or r.get('symbol'):r for r in wide};allrows=dict(provider)
 for r in deep:allrows[r.get('source_symbol') or r['symbol']]=r
 listing={};sources=[];errors=[];dow={'status':'unavailable','symbols':[],'source_url':DIA,'as_of':None,'basis':'DIA 공식 일별 주식 보유내역으로 다우 구성종목 확인; 지수 제공사 라이선스 명단과 구분'}
 for url,kind in ((NASDAQ,'nasdaq'),(OTHER,'other')):
  try:
   body=fetch(url);part,day=directory(body,kind);listing.update(part);sources.append({'url':url,'as_of':day,'status':'ok','sha256':hashlib.sha256(body).hexdigest()})
  except Exception as e:errors.append({'source':url,'error':str(e)[:180]})
 try:
  body=fetch(DIA);symbols,day=holdings(body);dow.update(status='current',symbols=sorted(symbols),as_of=day,sha256=hashlib.sha256(body).hexdigest())
 except Exception as e:errors.append({'source':DIA,'error':str(e)[:180]})
 # Source failure is shown, never interpreted as all companies exiting the index.
 members={}
 for sym,r in allrows.items():
  venue,basis,warnings=classify(r,listing,provider);is_dow=(sym in dow['symbols']) if r.get('market')=='US' and dow['status']=='current' else False if r.get('market')=='KR' else None
  members[sym]={'venue':venue,'venue_basis':basis,'country':r.get('market'),'dow_member':is_dow,'warnings':warnings}
 def counts(rows):
  out={k:0 for k in ('KOSPI','KOSDAQ','NASDAQ','DOW','NYSE','OTHER','UNKNOWN')}
  for r in rows:
   x=members[r.get('source_symbol') or r['symbol']];v=x['venue'];out[v if v in out else 'OTHER']+=1
   if x['dow_member'] is True:out['DOW']+=1
  return out
 out={'version':1,'generated_at':NOW.isoformat(),'max_age_hours':36,'dow':dow,'sources':sources,'errors':errors,'members':members,'counts':{'deep':counts(deep),'directory':counts(wide)},'note':'KOSPI/KOSDAQ/NASDAQ/NYSE는 상장시장. DOW는 별도 지수 편입 필터이며 중복 가능. NYSE 전체를 다우로 분류하지 않습니다. 숫자는 현재 위젯 수록 범위입니다.'}
 Path('stock-market-groups.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'counts':out['counts'],'dow_status':dow['status'],'dow_asof':dow['as_of'],'errors':errors},ensure_ascii=False))

if __name__=='__main__':main()
