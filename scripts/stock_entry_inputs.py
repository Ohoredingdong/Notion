"""Actual collector schema, completed-session calendar and transparent timing hypotheses."""
import datetime as dt
import functools
import math
from zoneinfo import ZoneInfo
UTC=dt.timezone.utc

def num(x):
    if isinstance(x,bool): return None
    try:
        v=float(x); return v if math.isfinite(v) else None
    except (ValueError,TypeError): return None

def timestamp(x):
    try:
        t=dt.datetime.fromisoformat(str(x).replace('Z','+00:00'))
        return t.astimezone(UTC) if t.tzinfo else None
    except (ValueError,TypeError): return None

@functools.lru_cache(maxsize=16)
def calendar(market,year):
    import exchange_calendars as xc
    name={'KR':'XKRX','US':'XNYS'}[market]
    return xc.get_calendar(name,start=f'{year-1}-01-01',end=f'{year+1}-12-31')

def clock(market,now):
    try:
        zone=ZoneInfo({'KR':'Asia/Seoul','US':'America/New_York'}[market])
        cal=calendar(market,now.year)
        session=cal.date_to_session(now.astimezone(zone).date().isoformat(),direction='previous')
        # A daily close remains unconfirmed during the collector's 30-minute buffer.
        if cal.session_close(session).to_pydatetime()+dt.timedelta(minutes=30)>now:
            session=cal.previous_session(session)
        next_session=cal.next_session(session)
        return {'date':session.date().isoformat(),'closed_at':cal.session_close(session).isoformat(),
                'next_session':next_session.date().isoformat(),'next_open':cal.session_open(next_session).isoformat(),
                'recheck_at':(cal.session_close(next_session).to_pydatetime()+dt.timedelta(minutes=30)).isoformat(),
                'calendar':cal.name,'buffer_minutes':30,
                'note':'커뮤니티 거래소 달력. 임시휴장 변경은 거래소 원문 확인.'}
    except Exception as exc:
        return {'date':None,'error':type(exc).__name__}

def completed(session,market,collected,now):
    try:
        cal=calendar(market,now.year); label=cal.date_to_session(session,direction='none')
        end=cal.session_close(label).to_pydatetime(); fetched=timestamp(collected)
        return fetched is not None and end+dt.timedelta(minutes=30)<=fetched<=now
    except Exception: return False

def fields(c,raw,now):
    tech=c.get('technical') or {}; forecasts=c.get('forecasts') or {}
    old=(c.get('estimates') or {}).get('next_year') or {}; nxt=forecasts.get('next_fy') or {}
    eps=num(nxt.get('avg',old.get('eps_avg')))
    exact=old.get('fiscal_end') or nxt.get('fiscal_end') or forecasts.get('next_fy_end_provider')
    inferred=forecasts.get('next_fy_end_inferred'); period=exact or inferred
    revision=num(forecasts.get('eps_revision30_pct'))
    if revision is None:
        prior=num(old.get('eps_30d'))
        if prior and eps is not None: revision=(eps/prior-1)*100
    original=c.get('expected_session') or tech.get('expected_session')
    if isinstance(original,dict): original=original.get('date')
    timing=clock(c.get('market'),now)
    integrity=c.get('source_integrity') or {}
    collected=c.get('collected_at') or integrity.get('fetched_at') or (integrity.get('price') or {}).get('fetched_at')
    return {'price':num(c.get('price')),'price_session':c.get('price_session') or tech.get('date') or tech.get('price_session'),
            'source_expected_session':original,'expected_session':timing.get('date'),'session_clock':timing,
            'forecast_eps':eps,'forecast_fiscal_end':period,
            'forecast_period_basis':'confirmed_provider_period' if exact else 'inferred_next_fy_not_exact_close_date' if inferred else 'missing',
            'revision30_pct':revision,'collected_at':collected,'source_generated_at':raw.get('generated_at')}

def technical(c,price,now):
    t=c.get('technical') or {}; blocks=[]
    ma20,ma60,atr,high,support,volume,relative=[num(t.get(k)) for k in ('ma20','ma60','atr14','prior_high20','support10','volume_ratio','relative20_pp')]
    extension=(price/ma20-1)*100 if price and ma20 and ma20>0 else None
    trend=bool(price and ma20 and ma60 and price>=ma20 and price>=ma60)
    breakout=bool(trend and high and price>=high and volume is not None and volume>=1.5 and relative is not None and relative>0)
    pullback=bool(trend and ma20>=ma60 and extension is not None and 0<=extension<=2 and volume is not None and volume>=.8 and relative is not None and relative>=0)
    if not trend: blocks.append('trend_confirmation_wait')
    if extension is None or not 0<=extension<=5: blocks.append('extension20_wait')
    if not (breakout or pullback): blocks.append('setup_confirmation_wait')
    if atr is None or atr<=0 or support is None or not price or not 0<support<price: blocks.append('risk_reference_missing')
    # Calendar values are estimates. Proximity is a caution, never proof of a catalyst.
    dates=(c.get('earnings_calendar') or {}).get('Earnings Date') or []
    if isinstance(dates,str): dates=[dates]
    local=now.astimezone(ZoneInfo('Asia/Seoul' if c.get('market')=='KR' else 'America/New_York')).date()
    upcoming=[]
    for value in dates:
        try:
            date=dt.date.fromisoformat(str(value)[:10])
            if 0<=(date-local).days<=3: upcoming.append(date.isoformat())
        except ValueError: pass
    if upcoming: blocks.append('earnings_event_near')
    watch='breakout_confirmed' if breakout else 'pullback_confirmed' if pullback else 'early_rebound_watch' if price and ma20 and ma60 and price>=ma20 and price<ma60 else 'conditions_wait'
    return {'blocks':blocks,'ma20':ma20,'ma60':ma60,'atr14':atr,'distance_sma20':extension,
            'volume_ratio':volume,'relative20_pp':relative,'support10':support,'prior_high20':high,
            'setup':watch,'technical_only_not_investment_approval':True,'near_earnings_dates':upcoming,
            'watch_conditions':[
                {'id':'breakout','price_reference':high,'volume_ratio_required':1.5,'meaning':'직전 20일 고점 이상 확정 종가 + 거래량 확대 + 시장 대비 강세'},
                {'id':'pullback','price_reference':ma20,'max_extension_pct':2,'meaning':'20일·60일 추세 유지, 20일 평균 근처에서 확정 종가 확인'},
                {'id':'rebound','price_reference':ma60,'meaning':'20일 평균을 회복해도 60일 평균 아래면 초기 반등 관찰로 분리; 매수 승인 아님'}]}
