"""Create an explicit next-step brief AFTER all existing risk and date gates.

This never changes assessment.state to create buy signals. The shortlist is a
relative research preference within the actual covered sample, not a return claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import json


def candidates(rows,states,limit=3):
 pool=[r for r in rows if r.get('status')=='current' and r.get('period_integrity',{}).get('status')=='ok' and r.get('assessment',{}).get('state') in states]
 pool.sort(key=lambda r:(r['assessment']['state']!='ready',-(r.get('priority',{}).get('display_score') or 0),r['symbol']))
 chosen=[];sectors=set()
 for r in pool:
  if r.get('sector') in sectors:continue
  chosen.append(r);sectors.add(r.get('sector'))
  if len(chosen)==limit:return chosen
 for r in pool:
  if r not in chosen:chosen.append(r)
  if len(chosen)==limit:break
 return chosen


def describe(r):
 a=r.get('assessment',{});f=r.get('forecasts',{});t=r.get('targets',{});h=r.get('history',{});score=r.get('priority',{}).get('display_score');proof=r.get('official_history',{})
 def signed(n):return f'{n:+.1f}%' if isinstance(n,(int,float)) else '자료 없음'
 reasons=[f"다음 FY 예상 EPS 성장 {signed(f.get('eps_growth_next_fy_pct'))}",f"같은 FY EPS 30일 변화 {signed(f.get('eps_revision30_pct'))}",f"목표가 중앙값과 종가 차이 {signed(t.get('median_gap_pct'))} (기대수익률 아님)"]
 return {'symbol':r['symbol'],'name':r['name'],'market':r['market'],'sector':r.get('sector'),'currency':r.get('currency'),'state':a.get('state'),'score':score,'price':r.get('price'),'price_session':r.get('price_session'),'price_condition':a.get('price_condition'),'why':reasons,'first_action':a.get('next_action'),'verified_count':len(proof.get('matched',[])),'missing':a.get('missing',[]),'risks':a.get('risks',[]),'price_condition_usable':a.get('price_condition_usable',False),'source':r.get('sources',{}).get('estimates'),'disclaimer':'과거 공식수치 확인 여부와 미래 애널리스트 추정 신뢰도는 별개입니다.'}


def main():
 p=Path('stock-opportunity-data.json');d=json.loads(p.read_text());rows=d['companies'];now=candidates(rows,{'ready','verify'});wait=candidates(rows,{'price'},2);ready=sum(r.get('assessment',{}).get('state')=='ready' for r in rows)
 d['decision_brief']={'built_at':datetime.now(timezone.utc).isoformat(),'ready_count':ready,'title':'지금 우선 비교할 기업 3개','now':[describe(r) for r in now],'wait':[describe(r) for r in wait],'summary':('현재 명시 조건을 충족한 후보부터 아래 순서로 비교합니다.' if ready else '아래 기업은 가격·실적 측면의 우선 후보입니다. 지금 매수 확정은 아니며 공식 수치 대조가 남아 있습니다.') if now else '현재 자료로 가격·실적 조건을 동시에 통과한 후보가 없습니다. 아래 가격 대기 후보의 조건가격을 확인하세요.','method':'기존 risk/date gate 통과 후보만. ready 우선, 고정 조사점수 순, 가능할 때 업종 분산. 어떤 문턱도 낮추지 않습니다.','not_trade_instruction':True}
 scan_path=Path('stock-opportunity-discovery.json')
 if scan_path.exists():
  scan=json.loads(scan_path.read_text());d['discovery_counts']=scan['counts'];d['discovery_status']=scan['status']
  scan.pop('specs',None);scan_path.write_text(json.dumps(scan,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 summary=json.loads(Path('stock-opportunity-summary.json').read_text());summary['decision_brief']=d['decision_brief'];summary['discovery_counts']=d.get('discovery_counts');summary['discovery_status']=d.get('discovery_status')
 Path('stock-opportunity-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 print('Named first choices:',[(r['name'],r['state']) for r in d['decision_brief']['now']])

if __name__=='__main__':main()
