"""Final gate: fetch time is not the financial period. Raw values are preserved."""
from datetime import datetime, timezone
from pathlib import Path
import json
import update_stock_opportunities as model

def parse_date(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
    except (TypeError,ValueError):return None

def validate_row(row,now):
    f=row.get('forecasts') or {};b=row.get('balance') or {};problems=[];details=[]
    for key,label,value,minage,maxage in [
        ('forecast_period','EPS 전망 회계연도',f.get('current_fy_end_provider'),-500,120),
        ('balance_period','현금·부채 기준일',b.get('asof'),0,230),
    ]:
        stamp=parse_date(value);age=(now-stamp).total_seconds()/86400 if stamp else None
        valid=age is not None and minage<=age<=maxage
        details.append({'key':key,'value':value,'age_days':round(age,1) if age is not None else None,'valid':valid,'allowed_age_days':[minage,maxage]})
        if not valid:problems.append(label+' '+str(value or '없음')+' — 현재 판단의 허용기간과 불일치')
    row['period_integrity']={'status':'ok' if not problems else 'needs_review','checked_at':now.isoformat(),'items':details,'issues':problems,'policy':'EPS 기준연도 -500~120일 / 현금·부채 0~230일. 추정치 자체의 공식 검증 또는 공시 적시성을 보장하지 않습니다.'}
    if problems:
        a=row.setdefault('assessment',{});a['state']='data';a['label']='최신 시세·재무 기준일 혼재 — 기간 확인'
        a['missing']=list(dict.fromkeys(a.get('missing',[])+problems))
        a['next_action']='아래 원자료의 기준일 충돌을 해소해야 합니다. 과거 날짜의 재무비율이나 회계연도가 불명확한 추정치를 현재 매수 근거로 쓰지 않습니다.'
        a.setdefault('checks',[]).append({'key':'period_integrity','label':'전망·현금·부채의 기준기간 검증','ok':False,'actual':details})
        a['price_condition_usable']=False
        a['price_condition_note']='표시된 목표가 산식은 참고용입니다. 기간 충돌이 해소되기 전에는 행동 기준으로 사용하지 않습니다.'
        priority=row.get('priority') or {};priority['display_score']=None;priority['blocked_reason']='기준기간 검증 실패';row['priority']=priority
    else:
        row.setdefault('assessment',{})['price_condition_usable']=True
        row.setdefault('priority',{})['display_score']=row.get('priority',{}).get('score')
    return row

def main():
    path=Path('stock-opportunity-data.json');d=json.loads(path.read_text(encoding='utf-8'));now=datetime.now(timezone.utc)
    for row in d.get('companies',[]):validate_row(row,now)
    for state in ('ready','verify','price','risk','data'):d['counts'][state]=sum(r.get('assessment',{}).get('state')==state for r in d['companies'])
    d['counts']['period_conflicts']=sum(r.get('period_integrity',{}).get('status')!='ok' for r in d['companies'])
    d['period_validated_at']=now.isoformat()
    path.write_text(json.dumps(model.core.clean(d),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    summary={'generated_at':d['generated_at'],'counts':d['counts'],'period_validated_at':d['period_validated_at'],'states':[{'symbol':r['symbol'],'size':r.get('size_group'),'state':r['assessment']['state'],'score':r.get('priority',{}).get('display_score'),'period_issues':r['period_integrity']['issues']} for r in d['companies']]}
    Path('stock-opportunity-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Period gate:',d['counts'])
if __name__=='__main__':main()
