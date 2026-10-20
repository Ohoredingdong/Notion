"""Final consistency gate; may only downgrade, never manufacture a buy opinion."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
p=Path('stock-investment-cases.json');c=json.loads(p.read_text());raw=Path('stock-opportunity-data.json').read_bytes();d=json.loads(raw);rows={r['symbol']:r for r in d['companies']}
assert c['source_sha256']==hashlib.sha256(raw).hexdigest() and c['source_generated_at']==d['generated_at']
changed=[]
for v in c['companies']:
 r=rows[v['symbol']]
 if v['state'] not in ('attractive','conditional','price_wait'):continue
 conditions=[r.get('status')=='current',r.get('period_integrity',{}).get('status')=='ok',r.get('model_integrity',{}).get('status')=='ok',any(x.get('key')=='liquidity' and x.get('ok') is True for x in r.get('assessment',{}).get('checks',[]))]
 if not all(conditions):
  v.update(state='insufficient',label='자료·유동성 조건 확인 전 투자판단 제외',verdict='현재 데이터·기간·업종모형·거래대금 중 필수 조건이 미확인입니다.')
  v['missing'].append('최종 필수 자료 확인 조건 미충족');changed.append(v['symbol']);continue
 if v['state']=='attractive':
  matched={x['field'] for x in v.get('official_comparison',[]) if x['status']=='matched'}
  legacy=set(r.get('official_history',{}).get('matched') or [])
  cash_proof=('fcf' in matched and {'revenue','operating_income'}.issubset(matched)) or {'revenue','eps','fcf'}.issubset(legacy)
  if not cash_proof:
   v.update(state='conditional',label='투자 매력은 있으나 FCF 공식 대조 필요',confidence='현금흐름 일부 대조; FCF 전체 산식 확인 필요')
   v['missing'].append('FCF는 CFO뿐 아니라 CAPEX까지 공식 대조해야 합니다.');changed.append(v['symbol'])
   for x in v['why']:
    if x.get('field')=='fcf':x['type']='제공처 실적 · FCF 공식 대조 전';x['source_url']=r.get('sources',{}).get('cashflow')
   for x in v['criteria']:
    if x['label']=='과거 핵심 실적 공식 대조':x['pass']=False
c['counts']={s:sum(x['state']==s for x in c['companies']) for s in ('attractive','conditional','price_wait','avoid','insufficient')}
c['final_integrity_check']={'checked_at':datetime.now(timezone.utc).isoformat(),'companies_checked':len(c['companies']),'downgraded':changed,'rule':'없거나 오래된 정보는 긍정의 근거가 될 수 없습니다. 인증 성공은 개별기업 검증과 다릅니다.'}
p.write_text(json.dumps(c,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
summary={k:c[k] for k in ('version','generated_at','source_generated_at','source_count','auth','counts','final_integrity_check')}
summary['positive_companies']=[{'symbol':x['symbol'],'name':rows[x['symbol']]['name'],'label':x['label'],'reasons':[a['text'] for a in x['why']],'price_session':rows[x['symbol']].get('price_session')} for x in c['companies'] if x['state']=='attractive']
Path('stock-investment-cases-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print('Final check',len(c['companies']),'companies; downgrades',len(changed))
