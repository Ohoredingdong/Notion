"""Pair each financial term with its everyday meaning on the existing view.
Display-only, idempotent, and fail-closed on changed anchors. No learning tab,
new scoring, source-data edits, probabilities, or additional API collection.
Definition references: https://www.investor.gov/introduction-investing/investing-basics/glossary/earnings-share
FCF uses this widget's existing operating-cash-flow minus CAPEX definition.
"""
from pathlib import Path
import subprocess
p=Path('assets/stock-investment-cases.js')
s=p.read_text(encoding='utf-8');original=s
helpers=r'''// TERMS_WITH_PLAIN_MEANING_V1 — presentation only, never changes a decision.
function reasonTerm(x,r){const v=x.value,h=r?.history||{};
 if(x.field==='fcf')return n(v)&&v>0&&n(h.operating_income)&&h.operating_income>0?'본업 흑자·FCF 양수':'FCF(잉여현금흐름)';
 if(x.field==='eps_growth_next_fy_pct')return '예상 EPS 성장률';
 if(x.field==='net_debt_ebitda')return n(v)&&v<0?'순현금·순차입금/EBITDA':'순차입금/EBITDA';
 if(x.field==='interim_revenue_growth')return '누적 매출 성장률';
 if(x.field==='target_gap')return '목표가 대비 가격 차이';
 if(x.field==='eps_revision30_pct')return '예상 EPS 조정률';
 if(x.field==='eps_spread')return '컨센서스 편차';
 if(x.field==='eps')return 'EPS(주당순이익)';
 return {operating_income:'영업이익',operating_margin:'영업이익률',cfo:'영업활동현금흐름(CFO)',revenue:'매출액',capex:'자본적지출(CAPEX)'}[x.field]||'';
}
function termPair(term,meaning){return '<span class="finance-term">'+E(term)+'</span><span class="finance-meaning">→ '+E(meaning)+'</span>'}
function termMetricLabels(){const pairs={
 '다음 회계연도 예상 EPS':['예상 EPS(주당순이익)','앞으로 주식 1주당 얼마를 벌지에 대한 예상이에요.'],
 '예상 EPS의 30일 변화':['예상 EPS 조정률','한 달 전과 비교해 전문가들이 이익 예상을 얼마나 바꿨는지예요.'],
 '다음 회계연도 예상 PER':['예상 PER(주가수익비율)','주가가 앞으로의 1주당 예상 이익의 몇 배인지예요. 낮다고 무조건 좋은 건 아니에요.'],
 '목표가 중앙값':['목표가 중앙값','전문가들의 목표가격을 순서대로 놓은 가운데 값이에요. 실제로 도달한다는 보장은 없어요.'],
 '다음 FY 예상 EPS 성장':['예상 EPS 성장률','다음 회계연도의 1주당 이익이 이번 회계연도 예상보다 얼마나 늘거나 줄지예요.'],
 '순차입금 / EBITDA':['순차입금/EBITDA','차입금에서 현금을 뺀 금액이 EBITDA(이자·세금·감가상각 전 이익)의 몇 배인지예요. 현금 잔액이나 갚는 데 걸리는 기간은 아니에요.']
};document.querySelectorAll('#detailBody .data-cell>span').forEach(el=>{const pair=pairs[el.textContent];if(pair)el.innerHTML=termPair(...pair)})}
'''
if 'TERMS_WITH_PLAIN_MEANING_V1' not in s:
 def change(a,b):
  global s
  if a not in s:raise RuntimeError('UI anchor missing: '+a[:90])
  s=s.replace(a,b)
 change('function plainReason(x,r){',helpers+'\nfunction plainReason(x,r){')
 change('return {title,body,source_url:x.source_url,type:sourceKind(x),original:x.text};','return {term:reasonTerm(x,r),title,body,source_url:x.source_url,type:sourceKind(x),original:x.text};')
 change("E(p.type)+'</span><b>'+E(p.title)+'</b>'","E(p.type)+'</span>'+termPair(p.term||'투자 근거',p.title)")
 change("readableReasons(c,r,2).map(x=>'<p>'+E(x.title)+'</p>')","readableReasons(c,r,2).map(x=>'<p>'+termPair(x.term||'투자 근거',x.title)+'</p>')")
 change("readableReasons(c,r,2).map(x=>x.title).join(' ')","readableReasons(c,r,2).map(x=>(x.term?x.term+' → ':'')+x.title).join(' ')")
 change("plainReason(c.risks[0],r).title", "[reasonTerm(c.risks[0],r),plainReason(c.risks[0],r).title].filter(Boolean).join(' → ')")
 change("row('','지금 비교한 주가',", "row('',termPair('종가','지금 비교한 주가'),")
 change("row('forecast','전문가들이 예상한 가격',", "row('forecast',termPair('목표가 중앙값','전문가들이 예상한 가격'),")
 change("row('buy','살 때 참고할 가격',", "row('buy',termPair('매수 참고 상한가','살 때 참고할 가격'),")
 change("(x.pass?'✓':'○')+'</strong>'+E({'본업 흑자·FCF 양수'", "(x.pass?'✓':'○')+'</strong><span class=\"finance-term\">'+E(x.label)+'</span><span class=\"finance-meaning\">→ '+E({'본업 흑자·FCF 양수'")
 change("}[x.label]||x.label)+'</div>'", "}[x.label]||x.label)+'</span></div>'")
 change("'revenue':'매출','operating_income':'본업에서 남긴 이익','eps':'주식 1주당 이익','fcf':'투자비를 뺀 현금','cfo':'영업으로 들어온 현금'", "'revenue':'매출액 → 물건·서비스를 팔아 올린 금액','operating_income':'영업이익 → 본업 비용을 빼고 남긴 이익','eps':'EPS → 주식 1주당 순이익','fcf':'FCF → 영업현금에서 투자비를 뺀 돈','cfo':'CFO → 영업으로 들어오고 나간 순현금'")
 change(" groupDetails();\n}", " groupDetails();termMetricLabels();\n}")
 change("최근 연간 영업 현금에서 설비·장비 투자비를 뺀 돈: ", "FCF(잉여현금흐름), 영업현금에서 집계된 투자비를 뺀 돈: ")
 change("plainAmount(v,r.currency)+'.'+(n(h.operating_margin)?", "plainAmount(v,r.currency)+'. 통장에 남은 현금 잔액과는 달라요.'+(n(h.operating_margin)?")
 change("' 100원어치를 팔아 본업 비용을 빼면 약 '", "' 영업이익률을 풀어보면, 100원어치를 팔아 본업 비용을 빼면 약 '")
 css='''.finance-term{display:block;font-weight:700;font-size:12px;line-height:1.8;color:var(--blue);overflow-wrap:anywhere}.finance-meaning{display:block;font-size:13px;font-weight:500;line-height:1.85;color:var(--ink);margin-top:3px;overflow-wrap:anywhere}.case-evidence>.finance-term{font-size:14px;margin-top:5px}.case-evidence>.finance-meaning{font-size:14px}.case-mini .finance-term{font-size:12px}.case-mini .finance-meaning{font-size:12px}.plain-price-item .finance-meaning{font-size:12px}.check .finance-term{font-size:11px}.check .finance-meaning{font-size:11px}.data-cell .finance-term{font-size:12px}.data-cell .finance-meaning{font-size:11px;font-weight:400;color:var(--muted)}@media(max-width:640px){.case-evidence>.finance-term,.case-evidence>.finance-meaning{font-size:13px}}'''
 change('/* PLAIN_LANGUAGE_V1 */','/* PLAIN_LANGUAGE_V1 */\n'+css)
 for name in ('fresh','get','tag','choicePool','load'):
  def fn(src):
   start=src.index('function '+name+'(');end=src.find('\nfunction ',start+1)
   if end<0:end=src.index('\nwindow.StockInvestmentCase',start)
   return src[start:end]
  if fn(original)!=fn(s):raise RuntimeError('Non-display function changed: '+name)
 subprocess.run(['node','--check','-'],input=s,text=True,check=True)
 p.write_text(s,encoding='utf-8')
subprocess.run(['node','--check',str(p)],check=True)
print('Term + everyday meaning installed. Timing, verdicts, sorting and data fetching unchanged.')
