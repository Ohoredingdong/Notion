"""Idempotent fixes for forecast periods and supplemental filing detail."""
from pathlib import Path
p=Path('assets/stock-radar-v8.js');s=p.read_text(encoding='utf-8')
if 'function priorityValue(r)' not in s:
    s=s.replace("function rows(){return data?.companies||[]}","function rows(){return data?.companies||[]}\nfunction priorityValue(r){return r.period_integrity?.status==='needs_review'?null:r.priority?.score;}")
    s=s.replace("if(paused()||r.status!=='current')", "if(paused()||r.status!=='current'||r.period_integrity?.status==='needs_review')")
    s=s.replace("fmt(r.priority?.score,0)","fmt(priorityValue(r),0)")
    s=s.replace("(b.priority?.score??-1)-(a.priority?.score??-1)","(priorityValue(b)??-1)-(priorityValue(a)??-1)")
    s=s.replace("const expectedAudit=audit?.companies?.find(x=>x.symbol===selected);", "const expectedAudit=r.extension_audit?.status==='compared'?{...r.extension_audit,fields:r.extension_audit.fields.map(x=>({...x,widget_period:r.extension_audit.period}))}:audit?.companies?.find(x=>x.symbol===selected);")
    s=s.replace("'match':'일치','minor_difference'", "'match':'일치','rounding_match':'반올림 허용범위 일치','minor_difference'")
    s=s.replace("const ceilingNote=!finite(pc.move_pct)?", "const ceilingNote=a.price_condition_usable===false?'기준기간 불일치: 아래 가격을 매수 행동 기준으로 사용하지 마세요.':!finite(pc.move_pct)?")
    s=s.replace("b.basis||'연결 범위·만기표 별도 확인'", "'기준일 '+(b.asof||'미상')+' · '+(b.basis||'연결 범위·만기표 별도 확인')")
    s=s.replace("fmt(f.analysts,0)+'명 추정 · 공식 확정 실적 아님'", "fmt(f.analysts,0)+'명 · 제공처 0y 결산일 '+(f.current_fy_end_provider||'미상')+' · 확정 실적 아님'")
    p.write_text(s,encoding='utf-8')
print('Displayed explicit period labels and filing proof; invalid score hidden')
