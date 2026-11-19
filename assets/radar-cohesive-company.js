/* Read-only company views. Never infer missing disclosures or approve investment. */
(()=>{'use strict';
const N=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
const rawEsc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function helpers(){const {esc=rawEsc}=window.RadarCohesive||{};return {esc};}
function safeURL(v){try{const u=new URL(v);return ['https:','http:'].includes(u.protocol)?u.href:null;}catch{return null;}}
function source(url,label='원문'){const {esc}=helpers();const u=safeURL(url);return u?`<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:`<span class="rc-muted">${esc(label)} 미연결</span>`;}
function badge(label,tone='neutral'){return `<span class="rcc-badge rcc-${tone}">${helpers().esc(label)}</span>`;}
function card(title,body,cls=''){return `<section class="rc-card rcc-card ${cls}"><h3>${helpers().esc(title)}</h3>${body}</section>`;}
function para(t){return `<p>${helpers().esc(t)}</p>`;}
function missing(t){return `<p class="rc-muted">${helpers().esc(t||'자료 미연결 · 판단 보류')}</p>`;}
function list(items){return `<ul class="rcc-list">${items.map(t=>`<li>${helpers().esc(t)}</li>`).join('')}</ul>`;}
function num(v,d=1){return N(v)===null?'—':v.toLocaleString('ko-KR',{maximumFractionDigits:d});}
function money(v,currency){if(N(v)===null)return '—';if(!currency)return num(v,0)+' (통화 미확인)';return num(v/1e8,2)+'억 '+currency;}
function stamp(c){const {esc}=helpers();return `<div class="rcc-provenance">저장 수집시각: ${esc(c?.collected_at||'미확인')} · 실시간 정보 아님 · 공식 원문 재확인 필요</div>`;}
function quality(c,ctx={}){
 if(!c)return card('기업을 선택해 주세요',missing('시장·산업에서 기업을 고르면 선택 기업이 모든 분석 탭에 유지됩니다.'));
 const {esc}=helpers(),b=c.business||{},sources=c.sources||{},industry=c.industry_metadata||{};
 const summary=b.summary||c.business_summary||c.business_description||c.profile?.business;
 const textSummary=typeof summary==='string'?summary:null;
 const chain=[['원재료·협력사','원재료 구성·공급처·협력관계의 공식 자료 미연결'],['핵심사업',b.industry||industry.industry||c.sector||'업종 미확인'],['주요 고객','주요 고객·매출 집중도 자료 미연결'],['성장사업','핵심 성장사업별 매출·수익 기여 자료 미연결']];
 const chainHTML=chain.map(([t,v])=>`<div class="rcc-chain-item"><h4>${esc(t)}</h4>${para(v)}</div>`).join('');
 const profile=textSummary?`<details class="rcc-profile" open><summary>사업모델 · 제공처 기업 소개</summary>${para(textSummary)}</details>`:missing('사업 소개 미연결. 회사가 판매하는 제품·서비스와 매출 구조를 공식 사업보고서에서 확인해야 합니다.');
 const sector=b.sector||industry.sector||c.sector;
 return `<div class="rcc-company">${stamp(c)}${card('사업 가치사슬',`<div class="rc-grid rcc-chain" style="--cols:4">${chainHTML}</div><small>자료 없는 고객·협력업체·성장사업을 임의로 채우지 않습니다.</small>`)}
 <div class="rc-grid" style="--cols:2">${card('내부 역량',`<div class="rcc-quality-row"><h4>어떤 회사인가요?</h4><div>${profile}${source(sources.profile||industry.source_url,'기업 프로필')}${b.website?' · '+source(b.website,'기업 웹사이트'):''}</div></div><div class="rcc-quality-row"><h4>무엇이 성장하나요?</h4>${missing('사업별 실적·투자·신규 제품의 근거가 아직 연결되지 않았습니다. 전사 매출 증가를 특정 사업의 성장으로 간주하지 않습니다.')}</div><div class="rcc-quality-row"><h4>누가 이끄나요?</h4>${missing('경영진 실행 능력·지배구조·노사 관계·인력 구성 확인 전')}</div>`)}
 ${card('외부 환경',`<div class="rcc-quality-row"><h4>산업·체감경기</h4><div>${para('업종: '+(sector||'미확인')+' / 세부 산업: '+(b.industry||industry.industry||'미확인'))}${missing('기업별 수요·경쟁·체감경기의 인과관계 분석은 미연결')}</div></div><div class="rcc-quality-row"><h4>정책·정치·대외환경</h4>${missing('지원정책·수출규제·지정학적 사건의 해당 기업 적용 여부와 기준일 확인 전')}</div><div class="rcc-quality-row"><h4>고객·협력업체</h4>${missing('고객 집중·공급 연속성·계약 조건 원문 확인 전')}</div>`)}</div>
 <div class="rc-grid" style="--cols:2">${card('왜 주목하나요?',missing('공식 사업구조·사업별 성장성과 경쟁우위 근거가 연결되기 전에는 질적 투자판단을 보류합니다.'),'rcc-mint')}${card('주의할 점',list(['프로필은 제공처 설명이며 최신 공식 공시와 다를 수 있습니다.','정책 수혜·경쟁우위·협력관계는 업종 이름만으로 추정하지 않습니다.','정량 실적이 양호해도 질적 분석의 미확인 항목은 통과 처리하지 않습니다.']),'rcc-rose')}</div>
 <div class="rcc-provenance">프로필 확인일: ${esc(industry.checked_at||'미확인')} · ${source(sources.official,'공식 공시 검색')} · 검색 페이지는 개별 공시 검증 완료를 의미하지 않습니다.</div></div>`;
}
function finance(c,ctx={}){
 if(!c)return card('기업을 선택해 주세요',missing());
 const {esc}=helpers(),h=c.history||{},b=c.balance||{},v=c.valuation||{},s=c.sources||{};
 const currency=h.currency,period=h.filing_period,priorPeriod=h.revenue_previous_period;
 const annual=/연간|annual/i.test(h.basis||'');
 const compare=!!(annual&&period&&priorPeriod&&h.supplemental_period_status==='same_period');
 const revEvidence=h.revenue_growth_evidence;
 const revCompare=!!(revEvidence?.status==='verified'&&revEvidence?.source?.identity_verified===true&&revEvidence.source_rows?.current?.value===h.revenue&&revEvidence.source_rows?.prior?.value===h.revenue_previous&&revEvidence.source_rows?.current?.period===period&&revEvidence.source_rows?.prior?.period===priorPeriod&&revEvidence.source?.currency===currency);
 const value=(n,unit='money')=>unit==='money'?money(n,currency):N(n)===null?'—':num(n,2)+(unit==='pct'?'%':unit==='ratio'?'배':unit==='share'?' '+(currency||'통화 미확인'):'');
 const delta=(a,z,unit)=>{if(N(a)===null||N(z)===null)return '—';if(unit==='pct')return num(a-z,2)+'%p';return z>0?num((a/z-1)*100,1)+'%':'비교 불가';};
 function metric(title,definition,rows,note,url,extra=''){
  const table=`<div class="rcc-table-scroll"><table class="rc-table"><thead><tr><th>항목</th><th>전기</th><th>당기 / 저장값</th><th>증감</th></tr></thead><tbody>${rows.map(r=>`<tr><th>${esc(r.label)}</th><td>${esc(value(r.prior,r.unit))}</td><td>${esc(value(r.current,r.unit))}</td><td>${esc(delta(r.current,r.prior,r.unit))}</td></tr>`).join('')}</tbody></table></div>`;
  // Definitions work on mouse hover, keyboard focus and touch, without invented interactions.
  return `<section class="rc-card rcc-metric"><h3><span class="rcc-definition" tabindex="0">${esc(title)}<span class="rcc-tooltip" role="tooltip">${esc(definition)}</span></span></h3>${table}<div class="rcc-assessment">${badge('검토 필요')}${para(note)}</div>${source(url,'자료 원문')}${extra}</section>`;
 }
 const margin=N(h.revenue)!==null&&h.revenue>0&&N(h.operating_income)!==null?h.operating_income/h.revenue*100:null;
 const priorMargin=compare&&revCompare&&h.revenue_previous>0&&N(h.operating_income_previous)!==null?h.operating_income_previous/h.revenue_previous*100:null;
 const row=(label,current,prior=null,unit='money')=>({label,current,prior,unit});
 const currentNote=period?'보고기간 '+period:'회계기간 미확인';
 const financeURL=revEvidence?.source?.url;
 const revenue=metric('매출','제품·서비스 판매로 벌어들인 금액입니다. 같은 회계기간·통화·연결 범위로 비교합니다.',[row('매출',h.revenue,revCompare?h.revenue_previous:null)],revCompare?'같은 연간 관측치의 증감입니다. 증가 자체가 수익성·현금 개선이나 매수 승인을 뜻하지 않습니다.':'전기와 당기의 비교 근거가 충분하지 않아 성장 판단을 보류합니다.',financeURL);
 const op=metric('영업이익','본업의 매출에서 영업비용을 뺀 이익입니다. 일회성 요인과 흑자 지속성을 확인합니다.',[row('영업이익',h.operating_income,compare?h.operating_income_previous:null)],'전기 대비 비교와 일회성 항목·사업별 기여를 함께 확인해야 합니다.',financeURL);
 const marg=metric('영업이익률','영업이익 ÷ 같은 기간 매출 × 100. 증감은 %가 아니라 %p로 표시합니다.',[row('이익률',margin,priorMargin,'pct')],N(margin)!==null?'같은 보고기간 매출·영업이익으로 계산했습니다. 업종 비교와 지속성은 확인 전입니다.':'매출 또는 영업이익이 없어 계산하지 않았습니다.',financeURL);
 const cfo=metric('영업현금흐름','영업활동에서 실제로 유입·유출된 현금입니다. 순이익·매출채권·재고와 대조합니다.',[row('영업현금흐름',h.cfo,compare?h.cfo_previous:null)],'영업현금이 양수여도 설비투자·차입금 상환·일시적 운전자본 변화를 확인해야 합니다.',s.cashflow,`<details><summary>FCF · 설비투자 보기</summary>${para('FCF '+money(h.fcf,currency)+' / 설비투자 '+money(h.capex,currency))}${para('제공처 저장값. FCF 정의·설비투자 범위는 원문 대조가 필요합니다.')}</details>`);
 const inventory=metric('매출채권/재고','매출채권은 아직 받지 못한 판매대금, 재고는 판매·생산을 위해 보유한 자산입니다. 매출보다 빠른 증가의 원인을 확인합니다.',[row('매출채권',h.accounts_receivable,compare?h.accounts_receivable_previous:null),row('재고',h.inventory,compare?h.inventory_previous:null)],'증가를 자동 호재나 악재로 판단하지 않습니다. 회수기간·재고 회전·평가손실을 함께 확인합니다.',s.balance);
 const debt=metric('부채/현금','차입금은 이자를 부담하는 빚이며 총부채와 다릅니다. 현금은 기준일·통화를 맞춰 비교합니다.',[row('차입금(재무제표)',h.total_debt_statement,compare?h.total_debt_statement_previous:null),row('현금(별도 집계)',b.currency===currency?b.cash:null)],'차입금은 총부채가 아닙니다. 현금 기준일 '+(b.asof||'미확인')+' / 통화 '+(b.currency||'미확인')+'. 기간이 다르면 순차입금으로 결합하지 않습니다.',s.balance,`<details><summary>차입금 만기 · 총부채</summary>${missing('만기별 상환표·총부채·금융약정 자료 미연결')}</details>`);
 const val=metric('PER/PBR/ROE','PER·PBR은 이익·장부가치 대비 가격 배수, ROE는 자기자본 대비 수익성입니다. 계산기간·평균자본 기준과 업종을 확인합니다.',[row('PER(TTM)',v.trailing_pe,null,'ratio'),row('PBR',v.price_to_book,null,'ratio'),row('ROE(제공처)',v.return_on_equity_pct,null,'pct')],'제공처 스냅샷이며 위 연간 재무와 동일 기간이 아닐 수 있습니다. ROE 평균자본·기간은 독립 검증 전입니다.',s.estimates,`<details><summary>산식·업종 비교</summary>${para(v.basis||'기간·산식 미확인')}${missing('동일 업종·동일 기준의 가치 비교 미연결')}</details>`);
 return `<div class="rcc-company">${stamp(c)}<div class="rc-card rcc-fin-context"><strong>${esc(currentNote)}</strong> · ${esc(h.basis||'연간/분기 기준 미확인')} · 통화 ${esc(currency||'미확인')} · 연결/별도: ${esc(h.statement_scope||'제공처 범위 확인 필요')}<p>전기 ${esc(priorPeriod||'미확인')} → 당기 ${esc(period||'미확인')} · 금액: 억 단위 / 이익률·ROE: % / PER·PBR: 배</p><small>지원되지 않는 분기·연결/별도 선택기는 표시하지 않습니다. 저장 근거만 표시하며 결측치를 0으로 채우지 않습니다.</small></div><div class="rc-grid rcc-fin-top" style="--cols:4">${revenue}${op}${marg}${cfo}</div><div class="rc-grid rcc-fin-bottom" style="--cols:3">${inventory}${debt}${val}</div>
 ${card('6가지 투자 질문',`<div class="rc-grid rcc-six" style="--cols:6">${['성장','수익성','현금 여력','부채 안정','적정 가격','미래 성장'].map(t=>`<div><strong>${t}</strong>${badge('판단 보류')}</div>`).join('')}</div>${missing('일부 수치가 양호해도 공식 대조·기간·업종·미래 사업의 근거가 충분하지 않으면 매수 후보로 승인하지 않습니다.')}`)}
 ${card('추가 지표 · 재무제표 출처',`<div class="rc-grid" style="--cols:4">${[['EPS(연간)',value(h.eps,'share')],['BPS(제공처)',value(v.book_value_per_share,'share')],['DPS','— · 미연결'],['부채비율','— · 총부채/자본 검증 전']].map(([a,z])=>`<div><strong>${a}</strong><p>${esc(z)}</p></div>`).join('')}</div><div class="rcc-source-row">${source(financeURL,'손익계산서')} · ${source(s.balance,'재무상태표')} · ${source(s.cashflow,'현금흐름표')} · ${source(c.official_history?.source_url,'공식 원문')}</div>${para('공식 비교 확인시각: '+(c.official_history?.checked_at||'미확인')+' · 일부 항목 대조와 전체 재무 검증은 다릅니다.')}`)}</div>`;
}
window.RadarCohesiveCompany={quality,finance};
})();
