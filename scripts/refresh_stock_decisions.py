"""Collect decision inputs, then attach official publication metadata.

An official publication proves the event exists, not its effect on price.
No company announcement is automatically labelled bullish/bearish.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from email.utils import parsedate_to_datetime
import json,os,urllib.request,urllib.parse,xml.etree.ElementTree as ET,io,zipfile
import update_stock_decisions as core

FEEDS={'AAPL':'https://www.apple.com/newsroom/rss-feed.rss','MSFT':'https://news.microsoft.com/feed/','NVDA':'https://nvidianews.nvidia.com/releases.xml','005930':'https://news.samsung.com/global/feed','000660':'https://news.skhynix.com/feed/'}
HEADERS={'User-Agent':'Personal Investment Research (github.com/Ohoredingdong/Notion)','Accept':'application/rss+xml, application/xml, application/json, text/xml, */*'}

def fetch(url,params=None):
 request=urllib.request.Request(url+('?' + urllib.parse.urlencode(params) if params else ''),headers=HEADERS)
 try:
  with urllib.request.urlopen(request,timeout=15) as response:return response.read(2000000)
 except Exception as error:
  # Never expose request query parameters: OpenDART keys are credentials.
  raise RuntimeError(type(error).__name__+': upstream unavailable') from None

def feeds(url):
 root=ET.fromstring(fetch(url));rows=[];now=datetime.now(timezone.utc)
 for item in list(root.findall('.//item'))+list(root.findall('{http://www.w3.org/2005/Atom}entry')):
  def text(k):return item.findtext(k) or item.findtext('{http://www.w3.org/2005/Atom}'+k) or ''
  title=text('title');link=text('link')
  if not link:
   el=item.find('{http://www.w3.org/2005/Atom}link');link=el.get('href','') if el is not None else ''
  date=text('pubDate') or text('published') or text('updated')
  try:
   try:dt=parsedate_to_datetime(date)
   except Exception:dt=datetime.fromisoformat(date.replace('Z','+00:00'))
   if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
   if dt>now+timedelta(minutes=5) or dt<now-timedelta(days=14):continue
  except Exception:continue
  if not link.startswith('https://') or not title:continue
  rows.append({'title':title[:200],'url':link,'published':dt.isoformat(),'source':'회사 공식 뉴스룸','status':'official_publication_not_verified_price_catalyst'})
 return sorted(rows,key=lambda r:r['published'],reverse=True)[:2]

def filings(key,companies):
 data=fetch('https://opendart.fss.or.kr/api/corpCode.xml',{'crtfc_key':key})
 z=zipfile.ZipFile(io.BytesIO(data));root=ET.fromstring(z.read('CORPCODE.xml'));codes={}
 for entry in root.findall('list'):
  symbol=(entry.findtext('stock_code') or '').strip()
  if symbol in companies:codes[symbol]=entry.findtext('corp_code')
 now=datetime.now(timezone.utc);out={}
 for symbol,corp in codes.items():
  args={'crtfc_key':key,'corp_code':corp,'bgn_de':(now-timedelta(days=14)).strftime('%Y%m%d'),'end_de':now.strftime('%Y%m%d'),'page_count':'5','sort':'date','sort_mth':'desc'}
  payload=json.loads(fetch('https://opendart.fss.or.kr/api/list.json',args))
  if payload.get('status') not in ('000','013'):out[symbol]={'error':'OpenDART status '+str(payload.get('status'))};continue
  out[symbol]=[{'title':x['report_nm'],'published':x['rcept_dt'],'url':'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+x['rcept_no'],'source':'금융감독원 DART 공시목록','status':'official_filing_metadata_not_directional_catalyst'} for x in payload.get('list',[])[:3]]
 return out

def main():
 core.main()
 p=Path('stock-decision-data.json');d=json.loads(p.read_text());by={r['symbol']:r for r in d['companies']}
 for symbol,url in FEEDS.items():
  if symbol not in by:continue
  row=by[symbol]
  try:
   row['official_events']=feeds(url);row['event_source']={'url':url,'checked_at':datetime.now(timezone.utc).isoformat(),'status':'ok'}
  except Exception as e:row['official_events']=[];row['event_source']={'url':url,'checked_at':datetime.now(timezone.utc).isoformat(),'status':'unavailable','error':str(e)}
 key=os.getenv('DART_API_KEY','').strip()
 if key:
  try:
   kr=[r['symbol'] for r in d['companies'] if r['market']=='KR']
   for symbol,items in filings(key,kr).items():
    if isinstance(items,list):by[symbol]['official_events']=items+by[symbol].get('official_events',[])
    else:by[symbol]['dart_events_error']=items['error']
  except Exception as e:d['dart_event_error']=str(e)
 d['counts']['official_event_links']=sum(len(r.get('official_events',[])) for r in d['companies'])
 d['events_checked_at']=datetime.now(timezone.utc).isoformat()
 p.write_text(json.dumps(core.clean(d),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 print('Official event links',d['counts']['official_event_links'])

if __name__=='__main__':main()
