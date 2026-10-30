"""Collect a small, auditable macro snapshot for the investment radar.

The script separates official policy decisions, market yields and provider prices.
It never turns one indicator into a deterministic stock-market forecast.
"""
from __future__ import annotations
import csv, io, json, math, re, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

NOW=datetime.now(timezone.utc)
OUT=Path('stock-market-context.json')
UA='PersonalInvestmentResearch/1.0 contact=private'

FED_URL='https://www.federalreserve.gov/FOMC/fundsrate.htm'
FED_CALENDAR_URL='https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'
BOK_URL='https://www.bok.or.kr/portal/singl/baseRate/list.do?menuNo=200643'
BOK_DECISIONS_URL='https://www.bok.or.kr/portal/main/contents.do?menuNo=200755'
TREASURY_URL='https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}'
FRED_CPI='https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL'
FRED_UNRATE='https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE'


def fetch(url,limit=8_000_000):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xml,text/csv,*/*'})
    with urllib.request.urlopen(req,timeout=25) as r:return r.read(limit)

def num(x):
    try:
        n=float(str(x).replace(',','').strip())
        return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None

def pct_change(new,old):return (new/old-1)*100 if new is not None and old not in (None,0) else None

def parse_fed_funds(html,year=None):
    year=year or NOW.year;soup=BeautifulSoup(html,'html.parser');rows=[]
    for tr in soup.find_all('tr'):
        cells=[re.sub(r'\s+',' ',x.get_text(' ',strip=True)) for x in tr.find_all(['th','td'])]
        if len(cells)<4:continue
        level=next((x for x in reversed(cells) if re.fullmatch(r'\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?',x)),None)
        if not level:continue
        date=next((x for x in cells if re.search(r'[A-Za-z]+\s+\d{1,2}',x)),None)
        if not date:continue
        lo,hi=[float(x) for x in re.split(r'[-–]',level)]
        numeric=[num(x) for x in cells[1:-1] if num(x) is not None]
        increase=numeric[0] if numeric else 0
        decrease=numeric[1] if len(numeric)>1 else 0
        try:day=datetime.strptime(f'{date} {year}','%B %d %Y').date().isoformat()
        except ValueError:continue
        rows.append({'date':day,'low':lo,'high':hi,'increase_bp':increase or 0,'decrease_bp':decrease or 0})
    if not rows:raise ValueError('fed_rate_table_not_found')
    rows.sort(key=lambda x:x['date'],reverse=True);latest=rows[0]
    latest['direction']='인상' if latest['increase_bp'] else '인하' if latest['decrease_bp'] else '유지'
    latest['source_url']=FED_URL;latest['basis']='FOMC 목표금리 범위와 해당 회의의 인상·인하 폭'
    return latest

def parse_fed_latest_statement(html):
    soup=BeautifulSoup(html,'html.parser');dates=[]
    for a in soup.find_all('a',href=True):
        match=re.search(r'monetary(20\d{6})a(?:1)?[.]htm',a['href'])
        if not match:continue
        try:day=datetime.strptime(match.group(1),'%Y%m%d').date()
        except ValueError:continue
        if day<=NOW.date():dates.append(day)
    if not dates:raise ValueError('fomc_statement_date_not_found')
    return max(dates).isoformat()

def collect_fed_policy():
    rate=parse_fed_funds(fetch(FED_URL))
    meeting=parse_fed_latest_statement(fetch(FED_CALENDAR_URL))
    effective=rate.get('date')
    out=dict(rate);out['rate_effective_date']=effective;out['date']=meeting
    try:
        meeting_day=datetime.fromisoformat(meeting).date()
        effective_day=datetime.fromisoformat(effective).date()
        changed_here=abs((effective_day-meeting_day).days)<=1
    except Exception:changed_here=False
    if not changed_here:
        out['increase_bp']=0;out['decrease_bp']=0;out['direction']='유지'
    out['basis']='최신 FOMC statement 일자와 현재 목표금리 범위의 마지막 변경일을 분리'
    out['source_url']=FED_CALENDAR_URL
    return out

def parse_bok(html):
    text=re.sub(r'\s+',' ',BeautifulSoup(html,'html.parser').get_text(' ',strip=True))
    current=re.search(r'한국은행\s*기준금리\s*([0-9.]+)%',text)
    decision=re.search(r'통화정책방향\s*\((20\d{2}[.]\d{1,2}[.]\d{1,2})\).*?기준금리를\s*([0-9.]+)%에서\s*([0-9.]+)%로\s*([0-9.]+)%p\s*(상향|하향)',text)
    if not current and not decision:raise ValueError('bok_rate_not_found')
    value=float(current.group(1) if current else decision.group(3));out={'value':value,'source_url':BOK_URL,'basis':'한국은행 홈페이지의 기준금리·통화정책방향'}
    if decision:
        out.update(date=decision.group(1).replace('.','-'),previous=float(decision.group(2)),change_pct_point=float(decision.group(4))*(1 if decision.group(5)=='상향' else -1),direction='인상' if decision.group(5)=='상향' else '인하')
    else:out.update(date=None,previous=None,change_pct_point=None,direction='최근 결정문 확인 필요')
    return out

def parse_bok_rate_history(html):
    text=re.sub(r'\s+',' ',BeautifulSoup(html,'html.parser').get_text(' ',strip=True));rows=[]
    for y,m,d,v in re.findall(r'(20\d{2})\s+(\d{1,2})월\s*(\d{1,2})일\s+([0-9]+(?:[.][0-9]+)?)',text):
        try:day=datetime(int(y),int(m),int(d)).date().isoformat();value=float(v)
        except (ValueError,TypeError):continue
        rows.append({'date':day,'value':value})
    rows=sorted({(r['date'],r['value']) for r in rows},reverse=True)
    if not rows:raise ValueError('bok_rate_history_not_found')
    return [{'date':d,'value':v} for d,v in rows]

def parse_bok_latest_decision(html):
    text=re.sub(r'\s+',' ',BeautifulSoup(html,'html.parser').get_text(' ',strip=True));dates=[]
    for y,m,d in re.findall(r'통화정책방향\s*[(](20\d{2})[.](\d{1,2})[.](\d{1,2})[)]',text):
        try:day=datetime(int(y),int(m),int(d)).date()
        except ValueError:continue
        if day<=NOW.date():dates.append(day)
    if not dates:raise ValueError('bok_decision_date_not_found')
    return max(dates).isoformat()

def collect_bok_policy():
    history=parse_bok_rate_history(fetch(BOK_URL));meeting=parse_bok_latest_decision(fetch(BOK_DECISIONS_URL))
    current=history[0];previous=history[1] if len(history)>1 else None
    current_value=current['value'];change_date=current['date'];direction='최근 결정문 확인 필요';change=None
    if meeting>change_date:
        direction='유지';change=0.0;previous_value=current_value
    elif meeting==change_date and previous:
        previous_value=previous['value'];change=current_value-previous_value
        direction='인상' if change>0 else '인하' if change<0 else '유지'
    else:
        previous_value=previous['value'] if previous else None
    return {'date':meeting,'value':current_value,'previous':previous_value,'change_pct_point':change,
            'direction':direction,'rate_change_date':change_date,'source_url':BOK_DECISIONS_URL,
            'basis':'최신 통화정책방향 결정일과 기준금리 실제 변경일을 분리; 금리 수준은 한국은행 기준금리 추이'}

def parse_treasury(xml):
    root=ET.fromstring(xml);ns={'a':'http://www.w3.org/2005/Atom','m':'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata','d':'http://schemas.microsoft.com/ado/2007/08/dataservices'};rows=[]
    for entry in root.findall('a:entry',ns):
        p=entry.find('.//m:properties',ns)
        if p is None:continue
        date=p.findtext('d:NEW_DATE',default='',namespaces=ns)[:10];value=num(p.findtext('d:BC_10YEAR',default='',namespaces=ns))
        if date and value is not None:rows.append({'date':date,'value':value})
    if not rows:raise ValueError('treasury_10y_not_found')
    rows.sort(key=lambda x:x['date']);latest=rows[-1];prior=rows[-2] if len(rows)>1 else None;old=rows[-21] if len(rows)>=21 else rows[0]
    return {'date':latest['date'],'value':latest['value'],'change_1d_pp':latest['value']-(prior['value'] if prior else latest['value']),'change_20_sessions_pp':latest['value']-old['value'],'source_url':TREASURY_URL.format(year=latest['date'][:4]),'basis':'미국 재무부 일별 국채 수익률의 10년 만기'}

def parse_fred_csv(body):
    rows=[]
    for row in csv.DictReader(io.StringIO(body.decode('utf-8-sig'))):
        date=row.get('DATE') or row.get('observation_date');value=next((v for k,v in row.items() if k not in ('DATE','observation_date')),None)
        n=num(value)
        if date and n is not None:rows.append((date,n))
    if not rows:raise ValueError('fred_series_empty')
    rows.sort();return rows

def fred_cpi(body):
    rows=parse_fred_csv(body);date,value=rows[-1];lookup={d:v for d,v in rows};year=int(date[:4])-1;old=lookup.get(f'{year}{date[4:]}')
    if old is None:
        target=datetime.fromisoformat(date).replace(year=year);old=min(rows,key=lambda x:abs((datetime.fromisoformat(x[0])-target).days))[1]
    yoy=pct_change(value,old);previous=None
    if len(rows)>=2:
        pd,pv=rows[-2];py=int(pd[:4])-1;pold=lookup.get(f'{py}{pd[4:]}');previous=pct_change(pv,pold) if pold else None
    return {'date':date,'value_index':value,'yoy_pct':yoy,'previous_yoy_pct':previous,'source_url':'https://fred.stlouisfed.org/series/CPIAUCSL','basis':'미국 CPI 계절조정지수의 전년동월 대비'}

def fred_unrate(body):
    rows=parse_fred_csv(body);date,value=rows[-1];old=rows[-4][1] if len(rows)>=4 else rows[0][1]
    return {'date':date,'value_pct':value,'change_3m_pp':value-old,'source_url':'https://fred.stlouisfed.org/series/UNRATE','basis':'미국 실업률, 계절조정'}

def market_series(symbol,label):
    import yfinance as yf
    frame=yf.Ticker(symbol).history(period='3mo',interval='1d',auto_adjust=False,actions=False,raise_errors=True)
    if frame is None or frame.empty:raise ValueError(label+'_empty')
    values=[(str(i.date()),num(v)) for i,v in frame['Close'].items() if num(v) is not None]
    if not values:raise ValueError(label+'_no_close')
    latest=values[-1];prior=values[-2] if len(values)>1 else latest;old=values[-21] if len(values)>=21 else values[0]
    return {'date':latest[0],'value':latest[1],'change_1d_pct':pct_change(latest[1],prior[1]),'change_20_sessions_pct':pct_change(latest[1],old[1]),'source_url':'https://finance.yahoo.com/quote/'+symbol,'basis':'시장 데이터 제공처의 마지막 일봉 종가; 실시간 아님'}

def interpretation(i):
    fed=i.get('fed_policy',{});ten=i.get('us_10y',{});cpi=i.get('us_cpi',{});un=i.get('us_unemployment',{});fx=i.get('usdkrw',{})
    notes=[];label='혼합된 금리 환경'
    if fed.get('direction')=='인상':notes.append('미국 기준금리가 최근 회의에서 올랐어요. 물가·경기·금융안정 중 무엇을 우선한 결정인지 회의문을 확인해야 해요.')
    elif fed.get('direction')=='인하':
        if cpi.get('previous_yoy_pct') is not None and cpi.get('yoy_pct') is not None and cpi['yoy_pct']<cpi['previous_yoy_pct'] and (un.get('change_3m_pp') or 0)<.3:notes.append('물가가 둔화하고 실업률 급등은 아직 뚜렷하지 않아 물가 안정형 인하 가능성을 먼저 확인해요.')
        elif (un.get('change_3m_pp') or 0)>=.3:notes.append('실업률이 올라 경기 악화 대응형 인하 가능성도 확인해야 해요.')
        else:notes.append('금리를 내렸지만 물가 안정 때문인지 경기 악화 때문인지 추가 지표가 필요해요.')
    level=ten.get('value');move=ten.get('change_20_sessions_pp')
    if level is not None and (level>=4.5 or (move is not None and move>=.25)):
        label='장기금리 부담이 큰 환경';notes.append('미국 10년물 국채금리가 높거나 최근 올랐어요. 먼 미래 이익의 현재가치가 낮아져 고PER 성장주의 평가 부담이 커질 수 있어요.')
    elif level is not None and level<3.5 and (move or 0)<=0:label='장기금리 부담이 낮아지는 환경'
    if fx.get('change_20_sessions_pct') is not None:
        notes.append('원/달러 환율은 최근 20거래일 '+('올랐어요. 원화 약세는 수출매출 환산에 유리할 수 있지만 수입 원가에는 불리할 수 있어요.' if fx['change_20_sessions_pct']>0 else '내렸어요. 원화 강세는 수입 원가에는 유리할 수 있지만 수출매출 환산에는 불리할 수 있어요.'))
    return {'label':label,'summary':' '.join(notes),'not_causality':'금리·국채금리·환율 하나만으로 주가 방향을 확정하지 않아요. 변화의 원인과 기업별 노출을 같이 확인합니다.','questions':[{'term':'기준금리','meaning':'중앙은행이 정하는 돈의 기본 가격','question':'왜 올리거나 내렸나요?','check':'물가 안정, 경기 둔화, 금융안정 중 무엇이 결정의 핵심이었는지 공식 회의문에서 확인'},{'term':'국채금리','meaning':'정부가 장기로 돈을 빌릴 때 시장이 요구하는 금리','question':'왜 시장금리가 움직였나요?','check':'기준금리 기대, 물가 기대, 장기채 위험보상 중 무엇이 변했는지 확인'},{'term':'환율','meaning':'1달러를 사는 데 필요한 원화','question':'이 기업에 유리한가요?','check':'매출 통화, 비용 통화, 해외자산·환헤지 여부를 구분'}]}

def main():
    errors=[];ind={}
    for key,fn in [('fed_policy',collect_fed_policy),('bok_policy',collect_bok_policy),('us_10y',lambda:parse_treasury(fetch(TREASURY_URL.format(year=NOW.year)))),('us_cpi',lambda:fred_cpi(fetch(FRED_CPI))),('us_unemployment',lambda:fred_unrate(fetch(FRED_UNRATE))),('usdkrw',lambda:market_series('KRW=X','usdkrw')),('sp500',lambda:market_series('^GSPC','sp500')),('nasdaq',lambda:market_series('^IXIC','nasdaq')),('kospi',lambda:market_series('^KS11','kospi')),('kosdaq',lambda:market_series('^KQ11','kosdaq'))]:
        try:ind[key]=fn()
        except Exception as e:errors.append({'field':key,'error':type(e).__name__+': '+str(e)[:160]})
    out={'version':'market-context-1.0','generated_at':NOW.isoformat(),'status':'ok' if not errors else 'partial','max_age_hours':18,'indicators':ind,'interpretation':interpretation(ind),'errors':errors,'source_note':'정책금리는 중앙은행 공식자료, 미국 10년물은 미국 재무부, CPI·실업률은 FRED, 환율·주가지수는 시장 데이터 제공처의 일봉 종가를 사용합니다.','terms':[{'term':'기준금리','meaning':'중앙은행이 정하는 돈의 기본 가격'},{'term':'국채금리','meaning':'정부가 돈을 빌릴 때 시장이 요구하는 금리'},{'term':'환율','meaning':'1달러를 사는 데 필요한 원화'}]}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(out['status'],len(ind),'indicators',len(errors),'errors')
    if len(ind)<5:raise SystemExit('핵심 거시지표 수집률 부족')

if __name__=='__main__':main()
