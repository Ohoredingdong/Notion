"""Collect recent material corporate-event headlines for recommendation gating.
RSS headlines are screening evidence, not semantic proof. A medium/high event
requires either a verified seed record or >=2 independent publishers.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
import urllib.request, xml.etree.ElementTree as ET, json, re, time

NOW=datetime.now(timezone.utc)
HIGH=[
 ('accounting_or_fraud',r'감사의견.?거절|회계부정|분식회계|횡령|배임|거래정지|상장폐지|부도|파산|회생절차|accounting fraud|delisting|trading halt|bankrupt'),
]
MEDIUM=[
 ('labor_dispute',r'총파업|파업|쟁의행위|노사갈등|strike|labor dispute'),
 ('capital_raise',r'유상증자|신주발행|rights offering|equity offering|share offering'),
 ('legal_regulatory',r'소송|가처분|과징금|규제|조사 착수|검찰|공정위|FDA 경고|lawsuit|injunction|investigation|regulator'),
 ('operations',r'리콜|생산중단|공장중단|화재|사고|해킹|정보유출|recall|shutdown|cyberattack|data breach'),
 ('customer_contract',r'계약해지|수주 취소|계약 취소|고객 이탈|contract termination|order cancellation')
]
def load(name,default):
 try:return json.loads(Path(name).read_text())
 except (OSError,ValueError):return default
def parse_date(s):
 for fmt in ('%a, %d %b %Y %H:%M:%S %Z','%a, %d %b %Y %H:%M:%S %z','%Y-%m-%d'):
  try:
   d=datetime.strptime(s,fmt)
   return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
  except ValueError:pass
 return None
def rss(name):
 q=quote(f'"{name}" when:14d')
 url=f'https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko'
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 PersonalInvestmentResearch/1.0'})
 with urllib.request.urlopen(req,timeout=12) as r: raw=r.read(2_000_000)
 root=ET.fromstring(raw);out=[]
 for item in root.findall('.//item')[:25]:
  title=(item.findtext('title') or '').strip();link=(item.findtext('link') or '').strip();pub=(item.findtext('pubDate') or '').strip()
  source=item.find('source');publisher=(source.text or '').strip() if source is not None else ''
  d=parse_date(pub)
  if not title or not d or NOW-d>timedelta(days=14):continue
  out.append({'title':title,'url':link,'publisher':publisher,'published_at':d.date().isoformat()})
 return out
def classify(title):
 for cat,pat in HIGH:
  if re.search(pat,title,re.I):return cat,'high'
 for cat,pat in MEDIUM:
  if re.search(pat,title,re.I):return cat,'medium'
 return None,None
def active_seed(seed):
 out=[]
 for e in seed.get('events',[]):
  try:exp=datetime.fromisoformat(e.get('expires_after')+'T23:59:59+00:00')
  except Exception:continue
  if e.get('status')=='active' and exp>=NOW:out.append(e)
 return out
def main():
 raw=load('stock-opportunity-data.json',{})
 seeds=active_seed(load('stock-event-risks-seed.json',{}))
 seed_by={}
 for e in seeds:seed_by.setdefault(e['symbol'],[]).append(e)
 # Scan current, model-compatible names. This is screening, not exhaustive world news.
 targets=[r for r in raw.get('companies',[]) if r.get('status')=='current' and (r.get('model_integrity') or {}).get('status')=='ok']
 results={}
 def work(r):
  try:return r['symbol'],rss(r.get('name') or r['symbol']),None
  except Exception as e:return r['symbol'],[],type(e).__name__
 with ThreadPoolExecutor(max_workers=6) as ex:
  futs=[ex.submit(work,r) for r in targets]
  for f in as_completed(futs):
   sym,items,err=f.result();results[sym]={'items':items,'error':err}
 scans=[]
 for r in targets:
  sym=r['symbol'];articles=results.get(sym,{}).get('items',[]);groups={}
  for a in articles:
   cat,sev=classify(a['title'])
   if not cat:continue
   groups.setdefault((cat,sev),[]).append(a)
  events=list(seed_by.get(sym,[]))
  for (cat,sev),items in groups.items():
   pubs={a['publisher'].strip().lower() for a in items if a['publisher'].strip()}
   # Avoid one-headline auto downgrades. Seed records can pass with one official source.
   if len(pubs)<2:continue
   events.append({'symbol':sym,'category':cat,'severity':sev,'status':'active','event_date':max(a['published_at'] for a in items),'expires_after':(NOW+timedelta(days=21)).date().isoformat(),'title':'최근 중요뉴스 '+len(items).__str__()+'건에서 '+cat+' 위험 키워드 확인','why_it_matters':'서로 다른 매체 2곳 이상에서 최근 중요 이벤트가 탐지됐습니다. 제목 기반 자동탐지이므로 원문 확인 전에는 사건의 영향 방향을 단정하지 않습니다.','sources':items[:5],'auto_detected':True})
  scans.append({'symbol':sym,'name':r.get('name'),'scanned_at':NOW.isoformat(),'status':'ok' if not results.get(sym,{}).get('error') else 'partial','events':events,'headline_count':len(articles),'error':results.get(sym,{}).get('error')})
 out={'version':'event-risk-1.0','generated_at':NOW.isoformat(),'source_generated_at':raw.get('generated_at'),'scope':'최근 14일 뉴스 제목 자동검색 + 검증된 수동 원문. 자동검색은 누락·오탐 가능성이 있어 2개 독립 매체 이상일 때만 추천 경고로 사용.','companies':scans,'seed_event_count':len(seeds),'scanned_companies':len(scans)}
 Path('stock-event-risks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 print('event risk scans',len(scans),'seed',len(seeds),'active',sum(len(x['events']) for x in scans))
if __name__=='__main__':main()
