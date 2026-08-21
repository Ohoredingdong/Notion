from __future__ import annotations
import json, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

OUT = Path('market-events-data.json')
KST = ZoneInfo('Asia/Seoul')
URL = 'https://economic-calendar.tradingview.com/events'
COUNTRIES = ['US','KR','JP','GB','DE','FR','CN']

HEADERS = {
    'Origin': 'https://www.tradingview.com',
    'Referer': 'https://www.tradingview.com/economic-calendar/',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
    'Accept': 'application/json,text/plain,*/*',
}

KEYWORDS = [
    ('rate', ['interest rate decision','fomc','fed interest rate','boe interest rate','ecb interest rate','boj interest rate','bank of korea','base rate']),
    ('inflation', ['cpi','consumer price','ppi','producer price','inflation','pce price','core pce']),
    ('jobs', ['non farm payroll','nonfarm payroll','unemployment','jobless','employment','jolts','average hourly earnings','claimant count']),
    ('growth', ['gdp','pmi','retail sales','industrial production','consumer confidence','consumer sentiment','business confidence','ifo business climate','ism']),
]

TRANSLATIONS = [
    (r'Fed Interest Rate Decision', '연준 금리 결정'),
    (r'Interest Rate Decision', '금리 결정'),
    (r'Ifo Business Climate', 'Ifo 기업환경지수'),
    (r'Core PCE Price Index', '근원 PCE 물가지수'),
    (r'Personal Spending', '개인소비지출'),
    (r'Personal Income', '개인소득'),
    (r'Durable Goods Orders', '내구재 주문'),
    (r'GDP Growth Rate', 'GDP 성장률'),
    (r'S&P Global Manufacturing PMI', 'S&P 글로벌 제조업 PMI'),
    (r'S&P Global Services PMI', 'S&P 글로벌 서비스업 PMI'),
    (r'NBS Manufacturing PMI', 'NBS 제조업 PMI'),
    (r'RatingDog Manufacturing PMI', 'RatingDog 제조업 PMI'),
    (r'ISM Manufacturing PMI', 'ISM 제조업 PMI'),
    (r'Consumer Price Index', '소비자물가지수'),
    (r'Producer Price Index', '생산자물가지수'),
    (r'Inflation Rate', '물가상승률'),
    (r'Non Farm Payrolls|Nonfarm Payrolls', '비농업 고용'),
    (r'Unemployment Rate', '실업률'),
    (r'Initial Jobless Claims', '신규 실업수당 청구건수'),
    (r'Continuing Jobless Claims', '계속 실업수당 청구건수'),
    (r'JOLTS Job Openings', 'JOLTs 구인건수'),
    (r'Gross Domestic Product', 'GDP'),
    (r'Retail Sales', '소매판매'),
    (r'GfK Consumer Confidence', 'GfK 소비자신뢰지수'),
    (r'Consumer Confidence', '소비자신뢰지수'),
    (r'Consumer Sentiment', '소비자심리지수'),
    (r'Industrial Production', '산업생산'),
    (r'Fed Chair .* Speech', '연준 의장 연설'),
    (r'Fed .* Speech', '연준 인사 연설'),
    (r'Crude Oil Stocks Change', '원유 재고'),
    (r'\bMoM\b', '전월 대비'),
    (r'\bQoQ\b', '전분기 대비'),
    (r'\bYoY\b', '전년 대비'),
    (r'\bPrel\b', '잠정치'),
    (r'\bFlash\b', '잠정치'),
    (r'\b2nd Est\b', '2차 추정치'),
]

OFFICIAL_TIME_RULES = [
    {'country':'DE','pattern':r'ifo business climate','hour':10,'minute':30,'tz':'Europe/Berlin','source':'ifo Institute','url':'https://www.ifo.de/en/survey/ifo-business-climate-index-germany'},
    {'country':'US','pattern':r'(gdp growth rate|personal spending|personal income|core pce price index)','hour':8,'minute':30,'tz':'America/New_York','source':'U.S. Bureau of Economic Analysis','url':'https://www.bea.gov/news/schedule'},
    {'country':'GB','pattern':r'retail sales','hour':7,'minute':0,'tz':'Europe/London','source':'Office for National Statistics','url':'https://www.ons.gov.uk/releasecalendar'},
    {'country':'FR','pattern':r'inflation rate.*prel','hour':8,'minute':45,'tz':'Europe/Paris','source':'INSEE','url':'https://www.insee.fr/en/information/2107817'},
]

HIGH_PATTERNS = [r'interest rate decision', r'\bfomc\b', r'core pce price index', r'non.?farm payroll', r'\bunemployment rate\b', r'\bcpi\b', r'consumer price index']
MEDIUM_PATTERNS = [r'gdp', r'ppi', r'producer price', r'pmi', r'retail sales', r'jolts', r'durable goods', r'consumer confidence', r'consumer sentiment', r'ifo business climate', r'industrial production', r'ism ', r'jobless claims', r'personal spending', r'personal income', r'fed .*speech', r'inflation rate']

DESCRIPTION_RULES = [
    (r'ifo business climate', '독일 기업들의 현재 경기 판단과 향후 6개월 전망을 보여주는 대표적인 기업심리지표입니다.'),
    (r'core pce price index', '미 연준이 중시하는 근원 PCE 물가의 변화를 보여주는 핵심 인플레이션 지표입니다.'),
    (r'personal spending', '미국 가계의 소비지출 변화를 보여주는 지표로 소비 경기와 GDP 흐름을 판단하는 데 활용됩니다.'),
    (r'personal income', '미국 가계가 벌어들인 소득 변화를 보여주며 소비 여력과 향후 지출 흐름을 판단하는 데 활용됩니다.'),
    (r'durable goods orders', '3년 이상 사용하는 내구재 신규 주문을 집계해 제조업 수요와 기업투자 흐름을 보여주는 지표입니다.'),
    (r'gdp growth rate', '국내총생산의 성장 속도를 보여주는 대표적인 경기지표로 경제 확장·둔화 여부를 판단하는 데 쓰입니다.'),
    (r'manufacturing pmi', '제조업 구매관리자 설문을 바탕으로 경기 확장·위축을 보여주는 선행지표입니다. 50을 기준으로 확장과 위축을 구분합니다.'),
    (r'services pmi', '서비스업 구매관리자 설문을 바탕으로 경기 확장·위축을 보여주는 선행지표입니다. 50을 기준으로 확장과 위축을 구분합니다.'),
    (r'retail sales', '소매 판매액 또는 판매량 변화를 통해 소비 경기의 강도를 확인하는 주요 소비지표입니다.'),
    (r'consumer confidence|consumer sentiment', '가계의 현재 경기 인식과 향후 전망을 조사해 소비 심리의 방향을 보여주는 지표입니다.'),
    (r'inflation rate|consumer price|\bcpi\b', '소비자 물가의 변화를 보여주는 대표적인 인플레이션 지표로 금리 전망과 채권·주식시장에 큰 영향을 줄 수 있습니다.'),
    (r'producer price|\bppi\b', '생산 단계의 가격 변화를 보여주는 지표로 향후 소비자물가 압력을 가늠하는 데 활용됩니다.'),
    (r'non.?farm payroll', '미국 비농업 부문의 고용 증감을 보여주는 핵심 고용지표로 달러·채권·주식시장 변동성을 크게 키울 수 있습니다.'),
    (r'unemployment rate', '경제활동인구 중 실업자의 비율을 보여주는 대표적인 고용시장 지표입니다.'),
    (r'jolts', '미국의 구인 건수를 보여줘 노동수요의 강도를 판단하는 고용시장 지표입니다.'),
    (r'jobless claims', '미국의 신규 실업수당 청구 건수를 통해 고용시장 약화 여부를 빠르게 확인하는 주간 지표입니다.'),
    (r'interest rate decision|\bfomc\b', '중앙은행의 기준금리 결정과 통화정책 방향을 확인하는 핵심 이벤트로 금융시장 전반에 큰 영향을 줄 수 있습니다.'),
]

def category(title: str) -> str:
    t = title.lower()
    for cat, words in KEYWORDS:
        if any(w in t for w in words):
            return cat
    return 'other'

def title_ko(title: str) -> str:
    out = title
    for pat, rep in TRANSLATIONS:
        out = re.sub(pat, rep, out, flags=re.I)
    return re.sub(r'\s+', ' ', out).strip()

def impact_level(title: str, country: str, source_importance: int) -> tuple[int, str]:
    t = title.lower()
    if any(re.search(p, t, re.I) for p in HIGH_PATTERNS): return 3, 'rule:high-impact-series'
    if any(re.search(p, t, re.I) for p in MEDIUM_PATTERNS): return 2, 'rule:medium-impact-series'
    if source_importance >= 3: return 3, 'source:tradingview'
    if source_importance == 2: return 2, 'source:tradingview'
    return 1, 'rule:standard'

def explain(title: str, cat: str) -> str:
    t = title.lower()
    for pat, desc in DESCRIPTION_RULES:
        if re.search(pat, t, re.I): return desc
    return {'rate':'중앙은행의 금리와 통화정책 방향을 확인하는 주요 정책 이벤트입니다.','inflation':'물가 압력과 향후 금리 경로를 판단하는 인플레이션 관련 지표입니다.','jobs':'고용시장 수요와 노동시장 강도를 확인하는 고용 관련 지표입니다.','growth':'실물경기와 기업·소비 활동의 확장 또는 둔화 흐름을 확인하는 경기지표입니다.','other':'금융시장에 영향을 줄 수 있는 주요 경제 일정입니다.'}.get(cat,'주요 경제 일정입니다.')

def parse_dt(value: str) -> datetime:
    if not value: raise ValueError('missing date')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)

def official_time_override(dt_kst: datetime, title: str, country: str) -> tuple[datetime, dict | None]:
    t = title.lower()
    for rule in OFFICIAL_TIME_RULES:
        if country == rule['country'] and re.search(rule['pattern'], t, re.I):
            local_tz = ZoneInfo(rule['tz'])
            local = dt_kst.astimezone(local_tz)
            corrected_local = local.replace(hour=rule['hour'], minute=rule['minute'], second=0, microsecond=0)
            corrected = corrected_local.astimezone(KST)
            return corrected, {'verified':True,'agency':rule['source'],'url':rule['url'],'original_datetime_kst':dt_kst.isoformat()}
    return dt_kst, None

def bucket_for(dt: datetime, now: datetime) -> str:
    if dt.date() == now.date(): return 'today'
    week_end = now.date() + timedelta(days=(6 - now.weekday()))
    return 'week' if dt.date() <= week_end else 'later'

def normalize(row: dict, now: datetime) -> dict | None:
    try: raw_dt = parse_dt(row.get('date'))
    except Exception: return None
    if raw_dt < now - timedelta(hours=6) or raw_dt > now + timedelta(days=14): return None
    source_imp = int(row.get('importance') or 0)
    title = str(row.get('title') or '').strip()
    if not title: return None
    dt, verification = official_time_override(raw_dt, title, row.get('country') or '')
    cat = category(title)
    impact, impact_reason = impact_level(title, row.get('country') or '', source_imp)
    return {'id':str(row.get('id') or ''),'title':title,'title_ko':title_ko(title),'country':row.get('country') or '','currency':row.get('currency') or '','source_importance':source_imp,'importance':impact,'impact_level':impact,'impact_reason':impact_reason,'category':cat,'datetime_kst':dt.isoformat(),'date_kst':f"{dt.month}월 {dt.day}일 ({'월화수목금토일'[dt.weekday()]})",'time_kst':dt.strftime('%H:%M'),'bucket':bucket_for(dt,now),'actual':row.get('actual'),'forecast':row.get('forecast'),'previous':row.get('previous'),'comment':(row.get('comment') or '')[:220],'comment_ko':explain(title,cat),'time_verification':verification}

def fetch_rows() -> list[dict]:
    now_utc = datetime.now(timezone.utc)
    params = {'from':(now_utc - timedelta(hours=12)).isoformat(timespec='milliseconds').replace('+00:00','Z'),'to':(now_utc + timedelta(days=14)).isoformat(timespec='milliseconds').replace('+00:00','Z'),'countries':','.join(COUNTRIES)}
    last = None
    for attempt in range(3):
        try:
            r = requests.get(URL, headers=HEADERS, params=params, timeout=25); r.raise_for_status(); rows = r.json().get('result')
            if not isinstance(rows,list): raise RuntimeError('unexpected TradingView payload')
            return rows
        except Exception as e:
            last = e; time.sleep(2 ** attempt)
    raise RuntimeError(f'TradingView calendar fetch failed: {last}')

def main():
    now = datetime.now(KST)
    try:
        events = [e for e in (normalize(r,now) for r in fetch_rows()) if e]
        events.sort(key=lambda e:(e['datetime_kst'],-e['impact_level']))
        higher = [e for e in events if e['impact_level'] >= 2]
        if len(higher) >= 9:
            keep_ids = {e['id'] for e in higher[:24]}
            events = [e for e in events if e['id'] in keep_ids or e['bucket'] == 'today']
        events = events[:36]
        upcoming = [e for e in events if datetime.fromisoformat(e['datetime_kst']) >= now - timedelta(minutes=30)]
        highlight = sorted(upcoming or events, key=lambda e:(-e['impact_level'],e['datetime_kst']))[0] if events else None
        verified_count = sum(1 for e in events if e.get('time_verification'))
        out = {'source':'TradingView Economic Calendar + official schedule overrides','source_url':'https://www.tradingview.com/economic-calendar/','generated_at':now.isoformat(),'updated_label':now.strftime('%m.%d %H:%M'),'stale':False,'countries':COUNTRIES,'accuracy':{'impact_method':'rule-based normalized impact_level (1-3); source_importance preserved separately','official_time_overrides':verified_count,'official_agencies':['ifo Institute','U.S. Bureau of Economic Analysis','Office for National Statistics','INSEE']},'highlight':highlight,'events':events}
        OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception as exc:
        if OUT.exists():
            old = json.loads(OUT.read_text(encoding='utf-8')); old['stale']=True; old['last_error']=str(exc); old['last_attempt_at']=now.isoformat(); OUT.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8'); print(exc,file=sys.stderr); return
        raise

if __name__ == '__main__': main()
