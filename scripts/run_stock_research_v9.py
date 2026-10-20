"""Market discovery followed by bounded deep collection using the existing engine."""
from datetime import datetime,timezone
from pathlib import Path
import json,time,os
import update_stock_opportunities as engine
from discover_stock_candidates_v9 import discover


def main():
 import yfinance as yf
 now=datetime.now(timezone.utc);started=time.monotonic()
 discovery=discover();specs=discovery['specs']
 base=engine.core.read('stock-value-radar-data.json',{});audit=engine.core.read('stock-official-audit.json',{});bases={r['symbol']:r for r in base.get('rows',[])}
 benchmarks={}
 for key,symbol,market in [('US','SPY','US'),('KR','^KS11','KR'),('KQ','^KQ11','KR')]:
  try:benchmarks[key]=engine.core.bars_from(yf.Ticker(symbol).history(period='1y',auto_adjust=False,actions=True,raise_errors=True),engine.core.latest_session(market,now))
  except Exception:benchmarks[key]=[]
 rows=[]
 for spec in specs:
  try:
   if time.monotonic()-started>13*60:raise TimeoutError('수집 실행의 13분 한도. 다음 회차에 새로 시도합니다.')
   bench='KQ' if spec[4].endswith('.KQ') else spec[2]
   row=engine.collect(spec,bases.get(spec[0],{}),audit,benchmarks.get(bench,[]),now)
   row['technical']['benchmark_symbol']={'US':'SPY','KR':'^KS11','KQ':'^KQ11'}[bench]
  except Exception as e:
   row={'symbol':spec[0],'name':spec[1],'market':spec[2],'sector':spec[3],'cohort':spec[5],'source_symbol':spec[4],'status':'failed','collected_at':datetime.now(timezone.utc).isoformat(),'errors':[{'field':'collector','error':type(e).__name__+': '+str(e)[:180]}]}
   row['priority']=engine.priority_score(row);row['assessment']=engine.assessment(row)
  rows.append(row)
  print('deep',len(rows),'/',len(specs),spec[0],row['status'],row['assessment']['state'],flush=True)
 counts={'tracked':len(rows),'current':sum(r['status']=='current' for r in rows),'expanded':sum(r.get('cohort')!='기존' for r in rows),'mid_small':sum(r.get('size_group') in ('mid','small') for r in rows),'discovered':discovery['counts']['eligible_directory'],'screen_downloaded':discovery['counts']['downloaded_unique']}
 for state in ('ready','verify','price','risk','data'):counts[state]=sum(r['assessment']['state']==state for r in rows)
 out={'version':'opportunity-v9','generated_at':datetime.now(timezone.utc).isoformat(),'max_age_hours':18,'counts':counts,'companies':rows,'rules':engine.RULES,'scope':discovery['scope']+' 기존 24개를 유지하고 자동탐색 결과에서 시장별 최대 40개를 추가 정밀 분석합니다.','discovery_status':discovery['status'],'size_policy':'자체 기준: US mega≥$200B, large≥$10B, mid≥$2B, small≥$300M. KR mega≥100조, large≥10조, mid≥1조, small≥0.2조. 거래소 지수 분류와 다릅니다.','data_notice':'Yahoo 단일 제공처의 참고자료. 미래 추정·목표가·리포트 날짜는 독립 검증 전. 공개 재배포·상품화 이용권한 별도 확인.','score_notice':'고정 가중치를 적용한 조사 순서. 확률·내재가치·매수 적합성을 보장하지 않음.','pending_setup':{'DART_API_KEY':'configured' if os.getenv('DART_API_KEY') else 'pending','investor_flow':'not_connected'},'training_widget_unchanged':True}
 Path('stock-opportunity-data.json').write_text(json.dumps(engine.core.clean(out),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 Path('stock-opportunity-summary.json').write_text(json.dumps({'generated_at':out['generated_at'],'counts':counts,'discovery_status':discovery['status']},ensure_ascii=False,indent=2)+'\n')
 if not counts['current']:raise SystemExit('최신 완료시세를 확보하지 못했습니다.')

if __name__=='__main__':main()
