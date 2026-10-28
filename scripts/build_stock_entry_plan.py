"""Point-in-time, fail-closed next-session research plans. Never places orders."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlparse, unquote
from zoneinfo import ZoneInfo

VERSION = 'entry-plan-1.0'
IDS = ('inputs','official','cash_quality','working_capital','earnings_quality','debt','business','valuation','macro','governance','forecast','liquidity')
UTC = dt.timezone.utc
RULES = {'max_source_hours':18, 'max_review_days':30, 'max_extension20_pct':5,
         'max_next_session_gap_pct':2, 'rsi_min':40, 'rsi_max':70,
         'min_revision30_pct':-3, 'execution_mode':'paper_only',
         'thresholds_are_policy_not_probabilities':True}

def number(x):
    if isinstance(x, bool): return None
    try:
        y=float(x)
        return y if math.isfinite(y) else None
    except (TypeError,ValueError): return None

def stamp(x):
    try:
        d=dt.datetime.fromisoformat(str(x).replace('Z','+00:00'))
        return d.astimezone(UTC) if d.tzinfo else None
    except (TypeError,ValueError): return None

def fresh(x, hours, now):
    t=stamp(x)
    return t is not None and 0 <= (now-t).total_seconds() <= hours*3600

def mapping(items):
    return {str(v['symbol']):v for v in items if isinstance(v,dict) and v.get('symbol') is not None}

def fields(c, raw):
    t=c.get('technical') or {}; f=c.get('forecasts') or {}; es=c.get('estimates') or {}
    ny=es.get('next_year') or {}; nf=f.get('next_fy') or {}
    session=c.get('price_session') or t.get('price_session')
    expected=c.get('expected_session') or t.get('expected_session') or (raw.get('market_sessions') or {}).get(c.get('market'))
    if isinstance(expected,dict): expected=expected.get('date')
    eps=number(ny.get('eps_avg',nf.get('avg')))
    fy=ny.get('fiscal_end') or nf.get('fiscal_end') or f.get('next_fy_end_provider')
    revision=number(f.get('eps_revision30_pct'))
    if revision is None:
        old=number(ny.get('eps_30d'))
        if eps is not None and old is not None and old>0: revision=(eps/old-1)*100
    integrity=c.get('source_integrity') or {}
    collected=integrity.get('fetched_at') or (integrity.get('price') or {}).get('fetched_at')
    return {'price':number(c.get('price')), 'price_session':session, 'expected_session':expected,
            'forecast_eps':eps, 'forecast_fiscal_end':fy, 'revision30_pct':revision,
            'collected_at':collected, 'source_generated_at':raw.get('generated_at')}

def completed_bar(session, market, collected_at, now):
    """Conservative regular-session close; never infers the next holiday/session."""
    settings={'KR':('Asia/Seoul',15,30),'US':('America/New_York',16,0)}
    if market not in settings or not session: return False
    try:
        tz,h,m=settings[market]
        d=dt.date.fromisoformat(session)
        close=dt.datetime.combine(d,dt.time(h,m),ZoneInfo(tz)).astimezone(UTC)
        collected=stamp(collected_at)
        return collected is not None and close <= collected <= now and close <= now
    except (ValueError,TypeError): return False

def strict_errors(c, case, review, raw, now, revalidated):
    f=fields(c,raw); errors=[]
    embedded=case.get('green_review') or {}
    if review.get('green_eligible') is not True or embedded.get('green_eligible') is not True:
        errors.append('strict_not_approved')
    if (review.get('version') or review.get('policy'))!='strict-green-1.0': errors.append('strict_version')
    checks=review.get('checks') or []
    if len(checks)!=12 or len({v.get('id') for v in checks})!=12 or {v.get('id') for v in checks}!=set(IDS) or any(v.get('status')!='pass' for v in checks):
        errors.append('strict_checks_incomplete')
    fp=review.get('fingerprint') or {}
    if review.get('source_generated_at')!=raw.get('generated_at'): errors.append('review_snapshot_mismatch')
    reviewed=review.get('reviewed_at') or review.get('checked_at')
    expiry=stamp(review.get('valid_until'))
    if not fresh(reviewed,30*24,now) or expiry is None or now>=expiry: errors.append('review_expired')
    for key,expected in [('input_price',f['price']),('input_price_session',f['price_session']),('input_forecast_eps',f['forecast_eps'])]:
        fallback={'input_price':'price','input_price_session':'price_session','input_forecast_eps':'forecast_eps'}[key]
        actual=review.get(key,fp.get(fallback))
        if expected is None or actual!=expected: errors.append(key+'_mismatch')
    if not revalidated: errors.append('source_documents_or_fingerprint_unverified')
    return errors

def evaluate(c, case, review, raw, now=None, revalidated=False):
    now=now or dt.datetime.now(UTC); f=fields(c,raw); t=c.get('technical') or {}
    data=[]
    if not fresh(raw.get('generated_at'),18,now): data.append('source_expired_or_future')
    if f['price'] is None or f['price']<=0: data.append('price_missing')
    if not f['expected_session'] or f['price_session']!=f['expected_session']: data.append('price_session_mismatch')
    if not fresh(f['collected_at'],18,now): data.append('actual_collection_unverified_or_stale')
    if not completed_bar(f['price_session'],c.get('market'),f['collected_at'],now): data.append('unconfirmed_session_close')
    if f['forecast_eps'] is None or f['forecast_eps']<=0 or not f['forecast_fiscal_end']: data.append('forecast_basis_missing')
    if t.get('latest_bar_matches_session') is False or c.get('status')=='stale': data.append('stale_price')
    strict=strict_errors(c,case,review,raw,now,revalidated)
    timing=[]
    distance=number(t.get('distance_sma20')); rsi=number(t.get('rsi14'))
    turnover=number(t.get('avg_turnover20',(c.get('liquidity') or {}).get('avg_turnover20')))
    if t.get('above_sma20') is not True or t.get('above_sma50') is not True: timing.append('trend_confirmation_wait')
    if distance is None or not 0<=distance<=5: timing.append('extension20_wait')
    if rsi is None or not 40<=rsi<=70: timing.append('rsi_wait')
    if turnover is None or turnover < (1e9 if c.get('market')=='KR' else 5e6): timing.append('liquidity_wait')
    if f['revision30_pct'] is None or f['revision30_pct'] < -3: timing.append('eps_revision_wait')
    if t.get('split_events') or t.get('recent_split'): timing.append('corporate_action_review')
    valuation=review.get('valuation') or embedded_valuation(case)
    cap=number(valuation.get('reference_price'))
    if cap is None or cap<=0: strict.append('independent_value_missing')
    price=f['price']; sma20=price/(1+distance/100) if price and distance is not None and distance>-100 else None
    ceiling=min(price*1.02,sma20*1.05,cap) if not data and not strict and sma20 and cap else None
    if ceiling is not None and ceiling<price: timing.append('price_above_entry_ceiling')
    eligible=not data and not strict and not timing
    state='data_wait' if data else 'diligence_wait' if strict else 'timing_wait' if timing else 'paper_candidate'
    return {'symbol':str(c['symbol']), 'name':c.get('name',c['symbol']), 'market':c.get('market'),
            'currency':c.get('currency'), 'provider_symbol':provider_symbol(c), 'state':state, **f,
            'data_blocks':sorted(set(data)), 'diligence_blocks':sorted(set(strict)),
            'timing_blocks':sorted(set(timing)), 'entry_conditions_met':eligible,
            'live_recommendation':False, 'execution_mode':'paper_only',
            'strict_passed':not strict, 'document_revalidated':revalidated,
            'plan':{'valid_until':min(now+dt.timedelta(hours=18),(stamp(raw.get('generated_at')) or now)+dt.timedelta(hours=18)).isoformat(),
                    'horizon':'다음 실제 정규 거래일의 재확인용; 장중 매수 신호 아님',
                    'entry_ceiling':ceiling, 'trend_invalidation_close':sma20 if eligible else None,
                    'next_session_max_gap_pct':2,
                    'execution_conditions':['장 시작 후 새 호가·공시·EPS·검토 유효기간을 재확인','기준가 대비 2% 초과 갭 또는 진입 상한 초과 시 추격하지 않음','새 공시·정정·전망 변경 또는 만료 시 계획 취소'],
                    'not_an_order':True, 'invalidation_is_not_guaranteed_loss_limit':True},
            'tech':{'rsi14':rsi,'distance_sma20':distance,'turnover20':turnover},
            'sources':c.get('source') or c.get('sources') or {}}

def provider_symbol(c):
    source=c.get('source') or c.get('sources') or {}
    for url in source.values():
        if not isinstance(url,str): continue
        u=urlparse(url)
        if u.hostname=='finance.yahoo.com' and '/quote/' in u.path:
            symbol=unquote(u.path.split('/quote/')[1].split('/')[0])
            if symbol and not symbol.startswith('^'): return symbol
    return str(c['symbol']) if c.get('market')=='US' else None

def embedded_valuation(case): return (case.get('green_review') or {}).get('valuation') or {}

def market_scenarios(macro,now):
    output=[]
    for key in ('kospi','kosdaq','sp500','nasdaq'):
        v=(macro.get('indicators') or {}).get(key) or {}; price=number(v.get('value'))
        output.append({'index':key,'reference_session':v.get('date'),'reference_value':price,
                       'observed_change_pct':v.get('change_1d_pct'), 'source_url':v.get('source_url'),
                       'is_prediction':False,'probability':None,
                       'scenarios':[
                           {'id':'continuation','condition':'다음 확정 종가가 기준 종가를 웃돌고 상승 종목 비중·거래대금이 함께 개선되는지 확인','available_now':False},
                           {'id':'rebound_failure','condition':'반등 뒤 기준 종가 이탈과 시장 폭 악화가 확인되면 신규 진입 보류','available_now':False},
                           {'id':'range','condition':'방향·시장 폭이 엇갈리면 방향을 단정하지 않고 개별 진입 조건을 기다림','available_now':False}],
                       'missing_evidence':['상승·하락 종목 수의 시점별 자료','지수 기여 업종과 투자자별 실제 수급'],
                       'scope':'다음 관측용 조건부 분기. 오늘 상승을 미리 맞혔다는 기록이 아님'})
    return {'written_at':now.isoformat(),'macro_generated_at':macro.get('generated_at'),'indices':output}

def read(root,name,default=None):
    path=root/name
    return json.loads(path.read_text()) if path.exists() else (default if default is not None else {})

def build(root=Path('.'),now=None):
    now=now or dt.datetime.now(UTC)
    blob=(root/'stock-opportunity-data.json').read_bytes(); raw=json.loads(blob)
    cases=read(root,'stock-investment-cases.json'); reports=read(root,'stock-green-review.json')
    depth=read(root,'stock-reading-depth.json'); macro=read(root,'stock-market-context.json')
    records=read(root,'stock-research-review-records.json').get('companies') or {}
    cm=mapping(cases.get('companies',[])); rm=mapping(reports.get('companies',[]))
    research=read(root,'stock-recommendations.json'); rank=mapping(research.get('companies',[]))
    sha=hashlib.sha256(blob).hexdigest()
    synced=(cases.get('source_generated_at')==raw.get('generated_at')==reports.get('source_generated_at')==depth.get('source_generated_at')
            and cases.get('source_sha256')==sha and depth.get('source_sha256')==sha)
    rows=[]; reevaluation_errors=[]
    for c in raw.get('companies',[]):
        symbol=str(c['symbol']); case=cm.get(symbol,{})
        r=rm.get(symbol,{}) or case.get('green_review') or {}
        verified=False
        if synced and r.get('green_eligible') is True:
            try:
                from stock_strict_green import evaluate as strict_evaluate
                actual=strict_evaluate(c,case,raw,depth,macro,records,now)
                verified=(actual.get('green_eligible') is True and actual.get('fundamental_fingerprint')==r.get('fundamental_fingerprint')
                          and bool(actual.get('fundamental_fingerprint')))
            except Exception as exc:
                reevaluation_errors.append({'symbol':symbol,'type':type(exc).__name__})
        result=evaluate(c,case,r,raw,now,verified)
        if not synced:
            result['state']='data_wait'; result['data_blocks'].append('derived_snapshot_mismatch')
            result['entry_conditions_met']=False; result['plan']['entry_ceiling']=None
        result['research_score']=rank.get(symbol,{}).get('score')
        rows.append(result)
    rows.sort(key=lambda v:(v['entry_conditions_met'],v['strict_passed'],number(v['research_score']) or -1),reverse=True)
    payload={'version':VERSION,'generated_at':now.isoformat(),'source_generated_at':raw.get('generated_at'),
             'source_sha256':sha,'rules':RULES,'snapshot_aligned':synced,
             'counts':{s:sum(v['state']==s for v in rows) for s in ('data_wait','diligence_wait','timing_wait','paper_candidate')},
             'live_recommendations':0,'companies':rows,'top':rows[:8],
             'market':market_scenarios(macro,now),'errors':reevaluation_errors,
             'validation':{'status':'forward_observation_only','live_trading_validated':False,
                           'note':'새 기록부터 사후 비교. 점수·문턱은 수익확률이 아니며 과거 신호를 소급 생성하지 않음'}}
    for name,data in [('stock-entry-plan.json',payload),('stock-entry-plan-summary.json',{k:v for k,v in payload.items() if k!='companies'})]:
        (root/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    ledger=root/'stock-entry-ledger.jsonl'
    old=[json.loads(line) for line in ledger.read_text().splitlines() if line.strip()] if ledger.exists() else []
    decision_hash=hashlib.sha256(json.dumps([(v['symbol'],v['state'],v['document_revalidated'],v['data_blocks'],v['diligence_blocks'],v['timing_blocks']) for v in rows],sort_keys=True).encode()).hexdigest()
    key=sha+':'+VERSION+':'+decision_hash
    if not any(v.get('id')==key for v in old):
        item={'id':key,'recorded_at':now.isoformat(),'source_generated_at':raw.get('generated_at'),
              'scope':'후속 관찰; 실제 체결·전략 수익률 아님','policy':RULES,
              'companies':[{k:r[k] for k in ('symbol','provider_symbol','market','price','price_session','state','entry_conditions_met')} for r in rows],
              'market':payload['market']}
        with ledger.open('a') as file: file.write(json.dumps(item,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({'version':VERSION,'snapshot_aligned':synced,'counts':payload['counts'],'live_recommendations':0},ensure_ascii=False))
    return payload

if __name__=='__main__': build()
