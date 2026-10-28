/* entry-plan-1.0: a research score must never bypass the strict investment gate. */
(function (root) {
  'use strict';
  const LABELS={data_wait:'자료 재확인',diligence_wait:'실사 완료 대기',timing_wait:'진입 조건 대기',paper_candidate:'조건 충족 · 성과 검증 전'};
  const WHY={source_expired_or_future:'원자료 만료 또는 시각 오류',price_missing:'가격 미확인',price_session_mismatch:'거래 기준일 불일치',actual_collection_unverified_or_stale:'실제 가격 수집 시각 미확인·만료',unconfirmed_session_close:'확정 종가 미확인',forecast_basis_missing:'예상 EPS 회계연도 미확인',stale_price:'오래된 시세',strict_not_approved:'엄격 실사 미승인',strict_version:'검증 정책 불일치',strict_checks_incomplete:'12개 필수 실사 미완료',review_snapshot_mismatch:'검토와 원자료 시점 불일치',review_expired:'검토 기록 만료',source_documents_or_fingerprint_unverified:'원문 근거·정정·fingerprint 재검증 미완료',independent_value_missing:'독립 가치평가 미완료',derived_snapshot_mismatch:'원자료·기업분석·3년자료 동기화 대기',trend_confirmation_wait:'20일·50일 추세 확인 대기',extension20_wait:'20일 평균 대비 이격 조건 미충족',rsi_wait:'단기 과열·약세 조건 확인',liquidity_wait:'거래대금 확인',eps_revision_wait:'예상 EPS 하향 또는 추세 미확인',corporate_action_review:'분할·기업행사 검토',price_above_entry_ceiling:'진입 검토 상한 초과',input_price_mismatch:'검토 가격 변경',input_price_session_mismatch:'검토 거래일 변경',input_forecast_eps_mismatch:'예상 EPS 변경'};
  function viewState(row,plan,currentSource,now=Date.now()) {
    const generated=Date.parse(plan?.source_generated_at), expiry=Date.parse(row?.plan?.valid_until);
    if(plan?.version!=='entry-plan-1.0' || !currentSource || currentSource!==plan.source_generated_at || !Number.isFinite(generated) || generated>now || now-generated>18*3600000 || !Number.isFinite(expiry) || expiry<=now) return 'data_wait';
    return Object.prototype.hasOwnProperty.call(LABELS,row.state)?row.state:'data_wait';
  }
  if(typeof module==='object' && module.exports) module.exports={viewState,LABELS};
  if(!root.document) return;
  const doc=root.document;
  let cache=null,current=null,loaded=0,busy=false,error='',tab='entry';
  const esc=x=>String(x??'').replace(/[&<>"']/g,v=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[v]));
  const num=x=>typeof x==='number' && Number.isFinite(x)?x.toLocaleString('ko-KR',{maximumFractionDigits:2}):'미확인';
  const time=x=>x && Number.isFinite(Date.parse(x))?new Date(x).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',hour12:false}):'미확인';
  const styles=`.rec-root{margin:14px 0;padding:20px;border:1px solid #d8e0e9;border-radius:20px;background:#f7f9fc;color:#243246}.rec-root *{box-sizing:border-box}.entry-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.entry-head h2{font-size:22px;margin:0 0 8px}.entry-note{font-size:13px;color:#526177;line-height:1.65;margin:8px 0}.entry-badge{background:#e7edf7;color:#314c75;border-radius:20px;padding:6px 10px;white-space:nowrap;font-size:12px}.entry-tabs{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}.entry-tabs button{padding:8px 12px;border:1px solid #d4dce7;border-radius:12px;background:white;cursor:pointer;color:#344963}.entry-tabs button[aria-selected=true]{background:#e4ecf9;border-color:#9daed0}.entry-counts{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0;font-size:12px}.entry-counts span{background:white;border:1px solid #dee5ee;padding:7px 10px;border-radius:10px}.entry-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.entry-card{padding:16px;background:white;border:1px solid #dce3ec;border-radius:15px;min-width:0}.entry-card h3{font-size:16px;margin:0 0 10px}.entry-state{font-size:12px;background:#edf1f7;color:#445874;border-radius:8px;padding:4px 7px;display:inline-block;margin-bottom:10px}.entry-metrics{display:grid;grid-template-columns:1fr 1fr;gap:9px;font-size:13px;margin:10px 0}.entry-metrics small{display:block;color:#66758b;font-size:11px;margin-bottom:4px}.entry-why{font-size:12px;line-height:1.7;color:#7b542c;border-top:1px solid #edf0f4;padding-top:10px}.entry-details{font-size:12px;line-height:1.65;margin-top:8px}.entry-details summary{cursor:pointer}.entry-scenario{padding:14px;background:white;border-radius:13px;margin:10px 0;border:1px solid #dce3ec}.entry-scenario h3{margin:0 0 8px;font-size:15px}.entry-foot a{color:#31598c;text-decoration:underline}.entry-muted{color:#69778b;font-size:12px}@media(max-width:680px){.rec-root{padding:14px}.entry-grid{grid-template-columns:1fr}.entry-head{display:block}.entry-badge{display:inline-block;margin:7px 0}.entry-head h2{font-size:20px}}`;
  function ensureStyles(){if(doc.getElementById('stock-entry-style'))return;const s=doc.createElement('style');s.id='stock-entry-style';s.textContent=styles;doc.head.appendChild(s);}
  async function load(){
    if(busy || Date.now()-loaded<60000)return;
    busy=true;
    try{
      const results=await Promise.all(['stock-entry-plan-summary.json','stock-opportunity-summary.json'].map(async file=>{
        const r=await fetch(file+'?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);return r.json();
      }));
      if(results[0].version!=='entry-plan-1.0')throw new Error('policy_version');
      cache=results[0];current=results[1].generated_at;error='';loaded=Date.now();root.stockEntryPlan=cache;
    }catch(e){error='진입 계획의 최신 자료를 확인하지 못했습니다. 조사 점수를 매수 추천으로 대신 표시하지 않습니다.';loaded=Date.now();cache=null;current=null;}
    finally{busy=false;render();}
  }
  function card(r){
    const state=viewState(r,cache,current), p=r.plan||{};
    const blocks=[...(r.data_blocks||[]),...(r.diligence_blocks||[]),...(r.timing_blocks||[])];
    if(state==='data_wait' && r.state!=='data_wait')blocks.unshift('review_snapshot_mismatch');
    const ceiling=state==='paper_candidate' || state==='timing_wait'?p.entry_ceiling:null;
    return `<article class="entry-card" data-entry-symbol="${esc(r.symbol)}"><h3>${esc(r.name)} <small>${esc(r.symbol)}</small></h3><span class="entry-state">${esc(LABELS[state])}</span><div class="entry-metrics"><div><small>기록된 가격 · ${esc(r.price_session)}</small>${num(r.price)} ${esc(r.currency)}</div><div><small>진입 검토 상한 · 주문가 아님</small>${ceiling==null?'검증 전 미산출':num(ceiling)+' '+esc(r.currency)}</div><div><small>조사 점수 · 확률 아님</small>${num(r.research_score)}</div><div><small>예상 EPS 기준</small>${esc(r.forecast_fiscal_end||'회계연도 미확인')}</div></div><div class="entry-why">${blocks.length?esc([...new Set(blocks)].slice(0,3).map(x=>WHY[x]||x).join(' / ')):'필수 조건 충족. 실거래 검증 전이므로 사후 관찰만 진행합니다.'}</div><details class="entry-details"><summary>기준 시각·취소 조건·남은 검증</summary><p>실제 가격 수집: ${esc(time(r.collected_at))}<br>원자료 생성: ${esc(time(r.source_generated_at))}<br>계획 만료: ${esc(time(p.valid_until))}</p><p>${esc(blocks.map(x=>WHY[x]||x).join(' / ')||'현재 명시 조건 충족')}</p><p>새 공시·정정·EPS 변경 시 취소합니다. 다음 장에서 기준가 대비 2% 초과 갭은 추격하지 않습니다. 추세 이탈 기준은 최대 손실 보장이 아닙니다.</p></details><button class="text-button" type="button" data-entry-open="${esc(r.symbol)}">기업 상세 보기 ›</button></article>`;
  }
  function market(){return `<p class="entry-note">상승·반등 실패·횡보를 미리 구분해 다음 관측과 대조합니다. 확률을 임의로 붙이거나 이미 오른 것을 사전 예측으로 기록하지 않습니다.</p>`+(cache.market?.indices||[]).map(v=>`<div class="entry-scenario"><h3>${esc(v.index.toUpperCase())} · 기준일 ${esc(v.reference_session||'미확인')}</h3><p class="entry-muted">원자료 기록값 ${num(v.reference_value)} · 독립 확인 전</p>${(v.scenarios||[]).map(s=>`<p class="entry-note">${esc(s.condition)}</p>`).join('')}<p class="entry-why">수급·시장 폭 자료 미완성: 이 항목만으로 방향을 확정하지 않습니다.</p></div>`).join('');}
  function record(){return `<div class="entry-scenario"><h3>오늘부터 남기는 사전 기록</h3><p class="entry-note">전체 관찰 종목과 통과·보류 사유, 당시 가격·EPS·자료 시점을 저장합니다. 같은 기록을 수정해 과거의 추천을 만든 것처럼 표시하지 않습니다.</p><p class="entry-note">1·5·20거래일 뒤 가격 변화와 지수 대비 차이를 비교합니다. 미도래·가격 미확인·기업행사 발생은 성공으로 집계하지 않습니다. 관찰 수익률은 실제 체결 수익률이나 검증된 전략 성과가 아닙니다.</p><p class="entry-why">현재 상태: 실거래 유효성 미검증 · 자동 주문 없음 · 수익확률 미산출</p></div>`;}
  function render(){
    const anchor=doc.getElementById('todayBrief');const panel=doc.getElementById('view-discover')||doc.getElementById('panel-snapshot');if(!panel)return;
    ensureStyles();let box=panel.querySelector('.rec-root');if(!box){box=doc.createElement('section');box.className='rec-root';box.id='practicalRecommendations';if(anchor?.parentNode===panel)panel.insertBefore(box,anchor);else panel.prepend(box);}
    const head=`<div class="entry-head"><div><h2>투자 조건과 진입 타이밍</h2><p class="entry-note">기업 실사 → 최신 확정자료 → 가격·추세 조건 → 다음 장 재확인. 조사 점수만으로 추천하지 않습니다.</p></div><span class="entry-badge">다음 거래일 계획 · 진입 신호 검증 단계</span></div>`;
    if(!cache){box.innerHTML=head+`<p class="entry-why">${esc(error||'진입 계획을 확인하고 있습니다. 확인 전 매수 추천은 표시하지 않습니다.')}</p>`;return;}
    const counts=Object.entries(cache.counts||{}).map(([k,v])=>`<span>${esc(LABELS[k]||k)} ${num(v)}개</span>`).join('');
    box.innerHTML=head+`<div class="entry-counts">${counts}<span>검증된 실거래 추천 0개</span></div><div class="entry-tabs" role="tablist">${[['entry','종목 진입 조건'],['market','시장 분기 시나리오'],['record','검증 기록']].map(([id,text])=>`<button role="tab" aria-selected="${tab===id}" data-entry-tab="${id}">${text}</button>`).join('')}</div>`+(tab==='market'?market():tab==='record'?record():`<div class="entry-grid">${(cache.top||[]).slice(0,6).map(card).join('')}</div>`)+`<p class="entry-note entry-foot">원자료 ${esc(time(cache.source_generated_at))} · 계획 작성 ${esc(time(cache.generated_at))}<br>현재 문턱은 초기 운용 정책이며 수익률 최적화 결과가 아닙니다. <a href="stock-entry-plan.json" target="_blank" rel="noopener">전체 검증 근거</a> · <a href="stock-entry-outcomes.json" target="_blank" rel="noopener">사후 관찰</a></p>`;
    box.querySelectorAll('[data-entry-open]').forEach(button=>button.addEventListener('click',()=>{const select=doc.getElementById('companySelect');if(select&&[...select.options].some(o=>o.value===button.dataset.entryOpen)){select.value=button.dataset.entryOpen;select.dispatchEvent(new Event('change',{bubbles:true}));doc.getElementById('tab-detail')?.click();}}));
    box.querySelectorAll('[data-entry-tab]').forEach(button=>button.addEventListener('click',()=>{tab=button.dataset.entryTab;render();}));
  }
  function start(){render();load();}
  if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',start);else start();
  ['stock-v8-ready','stock-opportunities-ready','stock-investment-cases-ready','stock-longterm-unified-ready'].forEach(name=>root.addEventListener(name,start));
  setInterval(()=>{if(!doc.hidden){render();load();}},15000);
})(typeof window!=='undefined'?window:globalThis);
