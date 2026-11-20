(()=>{'use strict';
const E=v=>String(v??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const N=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
const F=(v,u='')=>N(v)===null?'—':v.toLocaleString('ko-KR',{maximumFractionDigits:2})+u;
const safe=u=>{try{const x=new URL(u);return /^https?:$/.test(x.protocol)?x.href:''}catch{return ''}};
const link=(u,s)=>safe(u)?`<a href="${E(safe(u))}" target="_blank" rel="noopener noreferrer">${E(s)} ↗</a>`:`<span class="rce-muted">${E(s)} 미연결</span>`;
const card=(title,body,tone='mint')=>`<section class="rc-card rce-card"><h3 class="rce-${tone}">${E(title)}</h3>${body}</section>`;
const comparisonCell=Symbol('comparisonCell');
const table=(heads,rows)=>`<div class="rce-scroll"><table class="rc-table"><thead><tr>${heads.map(h=>`<th>${E(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(v=>`<td>${v?.[comparisonCell]??E(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
const text=(s)=>`<p>${E(s||'미확인 · 근거 자료 필요')}</p>`;
const missing=s=>`<p class="rce-empty">${E(s)}</p>`;
function value(c={},ctx={}){
 const v=c.valuation||{},f=c.forecasts||{},h=c.history||{},src=c.sources||{},b=c.business||{};
 const evidence=h.revenue_growth_evidence,p=evidence?.source_rows?.prior,a=evidence?.source_rows?.current;
 const revenueComparable=/연간|annual/i.test(h.basis||'')&&evidence?.status==='verified'&&evidence.source?.identity_verified===true&&a?.period===h.filing_period&&p?.period===h.revenue_previous_period&&a?.value===h.revenue&&p?.value===h.revenue_previous&&N(p?.value)!==null&&!!h.revenue_previous_period&&evidence.source.currency===h.currency;
 const exp=new Set((Array.isArray(h.supplemental_excluded_fields)?h.supplemental_excluded_fields:[]).map(x=>x.field));
 const prior=k=>revenueComparable&&h.supplemental_period_status==='same_period'&&!exp.has(k)&&!exp.has(k+'_previous')?h[k+'_previous']:null;
 const cell=(x,u='',prev=null)=>({[comparisonCell]:E(F(x,u))+(N(x)===null?'':window.RadarCohesive?.compare?.(x,prev,{verified:N(prev)!==null,label:N(prev)===null?'같은 기준의 전기 자료 미확인':`전기 ${h.revenue_previous_period} 대비`})||'')});
 const metrics=[['PER · 제공처 TTM',cell(v.trailing_pe,'배'),'—','—'],['PER · 다음 FY 추정',cell(f.next_fy_pe,'배'),'—','—'],['PBR',cell(v.price_to_book,'배'),'—','—'],['ROE · 제공처',cell(v.return_on_equity_pct,'%'),'—','—'],['EPS · 연간 실적',cell(h.eps,'',prior('eps')),'—','—'],['BPS',cell(v.book_value_per_share),'—','—'],['DPS','—','—','—']];
 const val=card('가격은 적정한가?',table(['지표','현재','업종 중앙값','과거 범위'],metrics)+text(v.basis)+`<small>저장 종가: ${E(c.price_session||'미확인')} · 통화 ${E(c.currency||'미확인')} · 비교자료 미확보로 적정가 판정 보류</small>`);
 const priorMargin=N(prior('operating_income'))!==null&&h.revenue_previous>0?prior('operating_income')/h.revenue_previous*100:null;
 const margin=N(h.operating_income)!==null&&h.revenue>0?h.operating_income/h.revenue*100:h.operating_margin;
 const outlook=card('실적과 전망을 구분해서 보기',table(['항목','연간 실적 A','이번 FY 추정 E','다음 FY 추정 E'],[['기간',h.filing_period||'—',f.current_fy_end_provider||'—',f.next_fy_end_inferred||'—'],['매출',cell(h.revenue,'',revenueComparable?p.value:null),'—','—'],['영업이익',cell(h.operating_income,'',prior('operating_income')),'—','—'],['영업이익률',cell(margin,'%',priorMargin),'—','—'],['EPS',cell(h.eps,'',prior('eps')),cell(f.current_fy?.avg),cell(f.next_fy?.avg)]])+text(f.basis)+text(f.period_note)+`<small>재무통화 ${E(h.currency||'미확인')} · 추정통화 ${E(f.currency||'미확인')} · 추정 참여 ${F(f.analysts)}명 · 수집 ${E(c.collected_at||ctx.data?.raw?.generated_at||'미확인')}</small><p>${link(src.estimates,'추정 출처')} · ${link(h.revenue_growth_evidence?.source?.url,'재무 원자료')}</p>`);
 const drivers=[['성장동력',`매출 변화 ${F(h.revenue_growth,'%')} · EPS 추정 수정(30일) ${F(f.eps_revision30_pct,'%')}`,'mint'],['산업상황',c.sector||b.industry||'미확인','yellow'],['핵심사업',b.summary||'사업 설명 자료 미확보','lilac'],['협력업체·고객','고객 집중도·협력 안정성: 근거 미확보','rose']].map(([t,s,tone])=>card(t,t==='핵심사업'?`<details><summary>제공처 기업 프로필 펼치기</summary>${text(s)}${link(src.profile,'프로필 출처')}</details>`:text(s),tone)).join('');
 const scenarios=[['낙관 시나리오','수요 회복·수익성 개선','수주·고객 회복과 원가·가격·효율 개선을 원문으로 확인','회복 미흡 또는 개선 지연','mint'],['기준 시나리오','완만한 수요·비용 안정','매출 성장 지속과 원가·판관비 안정 확인','성장 둔화 또는 비용 상승','yellow'],['비관 시나리오','수요 둔화·경쟁/원가 부담','주문 둔화·경쟁 심화·원가 부담 확대 확인','매출 둔화 및 수익성 악화','rose']].map(([t,a,b,r,tone])=>card(t,text('일반 점검 가정 · 기업별 확정 예측 아님')+`<strong>${E(a)}</strong>${text(b)}${text('위험: '+r)}`,tone)).join('');
 return `<div class="rce-value"><div class="rce-value-top">${val}${outlook}</div><div class="rce-four">${drivers}</div><div class="rce-three">${scenarios}</div><p class="rce-status">현재 판단: 비교·미래사업 근거 추가 확인 필요. 목표가격/상승확률을 임의 생성하지 않습니다. 저장 자료이며 실시간 아님.</p></div>`;
}
function captured(c,ctx){
 const records=[];const add=(x)=>{if(!x||typeof x!=='object')return;records.push({title:x.title||x.report_nm||x.name||'제목 미확인',type:x.type||x.category||'유형 미확인',date:x.date||x.rcept_dt||x.filed_at||'',url:x.url||x.source_url||'',note:x.note||x.summary||'세부 내용은 원문에서 확인',corrected:x.corrected||x.is_correction||false})};
 for(const a of [c.filings,c.disclosures])if(Array.isArray(a))a.forEach(add);
 // Only explicitly company-bound filing collections are accepted; news is not a filing.
 const pool=ctx.data?.filings;if(Array.isArray(pool))pool.filter(x=>String(x.symbol)===String(c.symbol)).forEach(add);
 else if(Array.isArray(pool?.companies)){const r=pool.companies.find(x=>String(x.symbol)===String(c.symbol));(r?.filings||[]).forEach(add)}
 const meta=c.history?.revenue_growth_evidence?.source_rows?.metadata||{};
 if(meta.rcept_no&&/^\d+$/.test(String(meta.rcept_no)))add({title:'사업보고서 · 재무 수치 연결 원문',type:'정기',date:String(meta.rcept_no).slice(0,8),url:'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+meta.rcept_no,note:'현재 재무 데이터에 연결된 접수번호. 전체 공시 수집을 뜻하지 않습니다.'});
 if(c.official_history?.source_url)add({title:'공식 재무 대조 원문',type:'정기',date:c.official_history.period,url:c.official_history.source_url,note:c.official_history.note});
 // Walk only exact-ticker-bound records, never the whole global dataset.
 const exact=x=>x&&String(x.symbol)===String(c.symbol);
 const sources=[];
 for(const key of ['cases','events','eventOutlook']){
  const data=ctx.data?.[key];
  if(Array.isArray(data?.companies))sources.push(...data.companies.filter(exact));
  if(Array.isArray(data?.events))sources.push(...data.events.filter(exact));
 }
 const fin=ctx.data?.financial?.records;
 if(fin&&typeof fin==='object')for(const r of Object.values(fin))if(exact(r)&&r.identity_verified===true)sources.push(r);
 function walk(x,depth=0){
  if(!x||typeof x!=='object'||depth>12)return;
  if(Array.isArray(x)){x.forEach(r=>walk(r,depth+1));return}
  if(x.symbol&&!exact(x))return;
  const u=x.source_url||x.url||'';let id='',date='',kind='정기',title='공식 공시 원문';
  try{const a=new URL(u);if(a.hostname==='dart.fss.or.kr'&&/^\d{14}$/.test(a.searchParams.get('rcpNo')||'')){id=a.searchParams.get('rcpNo');date=id.slice(0,4)+'-'+id.slice(4,6)+'-'+id.slice(6,8);title=({'11011':'사업보고서','11012':'반기보고서','11013':'1분기보고서','11014':'3분기보고서'})[x.report_code||x.report]||'DART 공시 원문';}
   else if(/(^|\.)sec\.gov$/.test(a.hostname)&&/^\/Archives\/edgar\/data\/\d+\/\d{18}\//.test(a.pathname)){id=a.pathname;title=x.form||x.title||'SEC 공시 원문';date=x.filed||x.filing_date||'';}
  }catch{}
  if(id)add({title,type:kind,date,url:u,note:[x.scope,x.period_end_label,x.basis,x.checked_at?'확인 '+x.checked_at:''].filter(v=>typeof v==='string').join(' · ')||'정확한 발행사 연결 원문 · 수집 범위는 일부'});
  Object.values(x).forEach(v=>{if(v&&typeof v==='object')walk(v,depth+1)});
 }
 // Prefer descriptive official report records before generic repeated evidence links.
 sources.forEach(r=>{if(r.official)walk(r.official);walk(r)});
 const seen=new Map();for(const r of records){let key=r.url;try{const u=new URL(r.url);key=u.hostname==='dart.fss.or.kr'?'DART:'+u.searchParams.get('rcpNo'):u.origin+u.pathname;}catch{key=r.title+'|'+r.date}
 const prior=seen.get(key);if(!prior||(/공시 원문|재무 수치 연결/.test(prior.title)&&/사업보고서|반기보고서|분기보고서/.test(r.title)))seen.set(key,r);}
 return [...seen.values()].sort((a,b)=>String(b.date).replaceAll('-','').localeCompare(String(a.date).replaceAll('-','')));

}
function filings(c={},ctx={}){
 const rows=captured(c,ctx);const guide=card('공시 읽는 법',`<strong>1 원문에서 찾기</strong>${text('계약금액·직전 매출·기간·이행 조건')}<strong>2 비중 계산</strong>${text('계약금액 ÷ 같은 통화의 직전 연매출 × 100')}<strong>3 조건까지 확인</strong>${text('규모·기간만으로 호재 단정 금지. 이익·현금 유입·해지 조건 확인.')}<small>계약금액 ≠ 이익·확정 매출</small>`);
 const ec=c.earnings_calendar||{};const dates=Object.entries(ec).filter(([k,v])=>/Date/.test(k)&&v!=null).map(([k,v])=>[({'Earnings Date':'실적 발표','Dividend Date':'배당 지급','Ex-Dividend Date':'배당락'})[k]||k,Array.isArray(v)?v.join(' / '):String(v)]);
 for(const e of ctx.data?.eventOutlook?.events||[]){if(String(e.symbol)===String(c.symbol)&&safe(e.source_url)&&e.event_date)dates.push([e.title||'기업 공식 일정',e.event_date]);}
 const today=new Date().toISOString().slice(0,10);for(const row of dates){const date=String(row[1]).slice(0,10);if(/^\d{4}-\d{2}-\d{2}$/.test(date))row[1]+=(date<today?' · 지난 일정':' · 예정 / 재확인');}
 const calendar=card('기업 일정 · 예정/지난 날짜 구분',(dates.length?table(['일정','제공처 날짜'],dates):missing('확보된 기업 일정 없음'))+text('전환청구·납입·소각·계약 종료일: 미확인. 제공처 일정은 변경 가능하며 원문 확인 필요.'),'lilac');
 const focus=[['공급계약','계약금액 / 매출 비중 / 기간 / 현금 유입','mint'],['CB·BW','발행 이력·잔존 물량·리픽싱 하한·청구기간·희석','yellow'],['정정 공시','변경 전후 금액·기간·해지 조건을 비교','rose'],['M&A·분할 / 자사주','공식 목적과 추정 구분·진행 단계·취득/소각 완료','lilac']].map(([t,s,tone])=>`<div class="rce-focus rce-${tone}"><strong>${E(t)}</strong>${text(s)}<small>구조화된 근거 미확보 · 원문 확인 전 판단 보류</small></div>`).join('');
 const list=rows.map(r=>`<details class="rce-filing" data-rce-record data-type="${E(r.type)}" data-date="${E(r.date)}"><summary><span>${E(r.title)}</span><small>${E(r.date||'공시일 미확인')} · ${E(r.type)}</small></summary>${text(r.note)}${text(r.corrected?'정정 표시 있음 · 이전 원문 비교 필요':'정정 이력 확인 전')}${link(r.url,'원문 열기')}</details>`).join('');
 const types=[...new Set(rows.map(r=>r.type))];
 const all=card('전체 공시 · 현재 확보분',`<p class="rce-muted">${rows.length}건 연결 · 의무·자율·정정의 전체 수집 여부 미검증</p><div class="rce-filters"><label>유형<select data-rce-filter><option value="">전체</option>${types.map(t=>`<option>${E(t)}</option>`).join('')}</select></label><label>공시일 이후<input type="date" data-rce-date aria-label="공시일 시작 날짜"></label></div><label class="rce-search">공시 검색<input type="search" data-rce-search placeholder="제목·유형 검색"></label><div class="rce-filing-list">${list||missing('연결된 공시 원문이 없습니다. 공시가 없다는 뜻은 아닙니다.')}</div><p data-rce-count>현재 확보분 ${rows.length}건</p><p>${link(c.sources?.official,'공식 공시 검색')}</p><small>자료 수집 ${E(c.collected_at||ctx.data?.raw?.generated_at||'미확인')} · 뉴스 자동탐지를 공시로 표시하지 않습니다.</small>`);
 return `<div class="rce-filings"><aside>${guide}${calendar}</aside>${card('꼭 볼 공시',focus)}${all}</div>`;
}
function filter(target){const root=target.closest('.rce-filings');if(!root)return;const q=(root.querySelector('[data-rce-search]')?.value||'').toLowerCase();const type=root.querySelector('[data-rce-filter]')?.value||'';const date=(root.querySelector('[data-rce-date]')?.value||'').replaceAll('-','');let count=0;root.querySelectorAll('[data-rce-record]').forEach(el=>{const d=el.dataset.date.replaceAll('-','').slice(0,8);el.hidden=!!((type&&el.dataset.type!==type)||(q&&!el.textContent.toLowerCase().includes(q))||(date&&(!d||d<date)));if(!el.hidden)count++});const out=root.querySelector('[data-rce-count]');if(out)out.textContent=`필터 결과 ${count}건 · 현재 확보 자료 내 검색`;}
function handle(e){if(e.target?.matches?.('[data-rce-filter],[data-rce-date],[data-rce-search]'))filter(e.target)}
document.addEventListener('change',handle);document.addEventListener('input',handle);
window.RadarCohesiveEvidence={value,filings,handle,captured};
})();
