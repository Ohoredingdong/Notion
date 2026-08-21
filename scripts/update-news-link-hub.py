from __future__ import annotations
import html, json, re, time, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

OUT=Path('news-link-data.json'); KST=ZoneInfo('Asia/Seoul')
UA={'User-Agent':'Mozilla/5.0 AppleWebKit/537.36 Chrome/124 Safari/537.36'}
QUERIES=[
 ('news','kr','한국 경제 증시 금리 환율 반도체 when:1d'),
 ('news','us','미국 경제 연준 금리 인플레이션 증시 when:1d'),
 ('article','kr','경제 분석 증시 전망 투자 전략 when:2d'),
 ('article','global','글로벌 경제 시장 분석 금리 인플레이션 when:2d'),
 ('realtime','kr','경제 속보 증시 속보 환율 속보 when:1d'),
 ('realtime','us','Fed inflation stocks markets when:1d'),
 ('opinion','kr','경제 오피니언 칼럼 사설 증시 when:7d'),
 ('opinion','global','economy opinion markets column when:7d'),
]

def feed_url(q):
    return 'https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':'ko','gl':'KR','ceid':'KR:ko'})

def clean(s):
    if not s:return ''
    s=re.sub(r'<[^>]+>',' ',html.unescape(s)); s=re.sub(r'\s+',' ',s).strip(); return s

def topic_for(title):
    t=title.lower()
    if any(k in t for k in ['연준','fed','fomc','금리']):return ('미 연준','')
    if any(k in t for k in ['코스피','코스닥','나스닥','증시','주가']):return ('마켓\n인사이트','market')
    if any(k in t for k in ['환율','달러','채권','국채']):return ('데일리\n이코','daily')
    if any(k in t for k in ['반도체','실적','기업','투자']):return ('투자\n프리뷰','invest')
    return ('데일리\n이코','daily')

def parse_feed(tab,region,q):
    r=requests.get(feed_url(q),headers=UA,timeout=25); r.raise_for_status(); root=ET.fromstring(r.text)
    out=[]
    for item in root.findall('.//item')[:12]:
        title=clean(item.findtext('title')); link=clean(item.findtext('link')); desc=clean(item.findtext('description')); pub=item.findtext('pubDate')
        src=item.find('source'); source=clean(src.text if src is not None else '')
        if source and title.endswith(' - '+source):title=title[:-(len(source)+3)]
        try: dt=parsedate_to_datetime(pub).astimezone(KST)
        except Exception: dt=datetime.now(KST)
        topic,cls=topic_for(title)
        if len(desc)>115:desc=desc[:112].rstrip()+'…'
        out.append({'tab':tab,'region':region,'topic':topic,'topic_class':cls,'title':title,'snippet':desc or source,'url':link,'published_at':dt.isoformat(),'source':source})
    return out

def main():
    now=datetime.now(KST); all_items=[]; error=None
    try:
        for tab,region,q in QUERIES:
            try: all_items.extend(parse_feed(tab,region,q)); time.sleep(.25)
            except Exception as e: error=str(e)
        seen=set(); items=[]
        for x in sorted(all_items,key=lambda x:x['published_at'],reverse=True):
            key=re.sub(r'\W+','',x['title'].lower())[:80]
            if not key or key in seen:continue
            seen.add(key);items.append(x)
        if not items: raise RuntimeError(error or 'no RSS items')
        data={'source':'Google News RSS','generated_at':now.isoformat(),'stale':False,'items':items[:80]}
        OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception as exc:
        if OUT.exists():
            old=json.loads(OUT.read_text(encoding='utf-8')); old['stale']=True; old['last_error']=str(exc); old['last_attempt_at']=now.isoformat(); OUT.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
        else: raise
if __name__=='__main__':main()
