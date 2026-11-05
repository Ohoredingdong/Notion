/* A source-attributed search UI. List entries do not imply priced/AI-reviewed stocks. */
(()=>{"use strict";
 const state={query:"",country:"ALL",preview:null};
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const n=v=>typeof v==="number"&&Number.isFinite(v)?v.toLocaleString("ko-KR"):"—";
 const normalized=v=>String(v??"").toUpperCase().replace(/\.(KS|KQ)$/,"");
 function data(ctx){const c=ctx.data?.catalog;return Array.isArray(c?.items)?c.items:[];}
 function tracked(ctx){return new Map((ctx.data?.raw?.companies||[]).map(c=>[(c.market==="KR"?"KR:":"US:")+normalized(c.symbol),c]));}
 function matching(ctx){
  const q=state.query.trim().toLocaleLowerCase();
  const candidates=data(ctx);
  const found=candidates.filter(x=>(state.country==="ALL"||state.country===x.country)&&
   (!q||String(x.name||"").toLocaleLowerCase().includes(q)||String(x.symbol||"").toLocaleLowerCase().includes(q)));
  return {found,total:candidates.length};
 }
 function symbolFor(x){return x.country==="KR"?x.symbol+(x.exchange==="KOSDAQ"?".KQ":".KS"):x.symbol;}
 function sig(x,ctx){
  return window.StockRadarFlowV2?.signal?.({symbol:symbolFor(x)},ctx)||null;
 }
 function rows(ctx){
  const {found,total}=matching(ctx),investigated=tracked(ctx);
  if(!total)return '<p class="fx-catalog-empty">공식 종목 목록을 확인하는 중입니다. 기존 심층분석은 계속 이용할 수 있습니다.</p>';
  if(!found.length)return '<p class="fx-catalog-empty">검색 결과가 없습니다. 회사명이나 종목코드를 확인해 주세요.</p>';
  return found.slice(0,35).map(x=>{
    const c=investigated.get(x.country+":"+normalized(x.symbol)),s=sig(x,ctx);
    const text=s?.active&&s?.value!==null?"AI "+esc(s.label)+" "+n(s.value*100)+"% (연구용)":c?"심층분석 보유 · AI "+(s?.stale?"기간 종료":"확인 필요"):"상장정보만 · AI 연구 대기";
    const attr=c?`data-nr-select="${esc(c.symbol)}"`:`data-catalog-preview="${esc(x.country+":"+x.symbol)}"`;
    return `<button type="button" class="fx-catalog-row" ${attr}>
      <span class="fx-catalog-company"><strong>${esc(x.name)}</strong><small>${esc(x.symbol)} · ${esc(x.exchange)}</small></span>
      <span class="fx-catalog-signal ${s?.active?"is-active":""}">${text}</span>
      <span aria-hidden="true">›</span>
    </button>`;
  }).join("");
 }
 function count(ctx){
  const {found,total}=matching(ctx),catalog=ctx.data?.catalog||{};
  return `검색 ${n(found.length)}건 / 공식 명부 ${n(total)}건 · ${catalog.status==="partial"?"일부 거래소 자료 누락 · ":""}가격·재무제표와는 별개`;
 }
 function panel(ctx){
  const catalog=ctx.data?.catalog||{},total=data(ctx).length,kr=catalog.counts?.KR,us=catalog.counts?.US;
  return `<section class="fx-panel fx-catalog" aria-label="국내외 전체 상장종목 검색">
   <div class="fx-catalog-head"><div><h3>전체 상장종목 찾기</h3>
     <small>한국 ${n(kr)}개 · 미국 ${n(us)}개 · 명부 전체 ${n(total)}개</small></div>
     <small>${esc(catalog.generated_at?"출처 확인 "+new Date(catalog.generated_at).toLocaleDateString("ko-KR",{timeZone:"Asia/Seoul"}):"출처 수집 전")}</small></div>
   <div class="fx-catalog-toolbar"><input id="fx-catalog-search" type="search" value="${esc(state.query)}"
      aria-label="전체 상장종목 이름이나 종목코드 검색" placeholder="회사명·종목코드로 8천여 종목 검색"/>
    <div class="fx-catalog-countries">${[["ALL","전체"],["KR","한국"],["US","미국"]].map(([key,label])=>
      `<button type="button" data-catalog-country="${key}" class="${state.country===key?"active":""}">${label}</button>`).join("")}</div></div>
   <div id="fx-catalog-results" class="fx-catalog-results">${rows(ctx)}</div>
   <small id="fx-catalog-count" class="fx-catalog-count">${esc(count(ctx))}</small>
  </section>`;
 }
 function focus(ctx){
  if(!state.preview)return null;
  const x=data(ctx).find(x=>x.country+":"+x.symbol===state.preview);
  if(!x)return null;
  const s=sig(x,ctx),cat=ctx.data.catalog;
  const has=s?.active&&s?.value!==null;
  const description=has?s.status:(s?.status||"아직 유효한 AI 연구 신호가 없습니다.");
  return `<section class="fx-panel fx-catalog-preview">
    <div class="fx-panel-heading"><div><h3>${esc(x.name)}</h3><small>${esc(x.symbol)} · ${esc(x.exchange)}</small></div>
      <button type="button" data-catalog-back class="fx-link">심층 분석 종목으로</button></div>
    <div class="fx-catalog-preview-core"><small>AI 방향 연구</small>
     <strong>${has?esc(s.label+" "+n(s.value*100)+"%"):"미발행 · 검증 대기"}</strong>
     <p>${esc(description)}</p></div>
    <div class="fx-catalog-preview-info"><b>공식 상장종목 목록에 확인된 기업</b>
      <p>현재가·재무제표·FCF·기업 가치평가가 연결되지 않았다면 분석 점수나 예상수익률을 표시하지 않습니다.</p>
      <small>출처: ${esc(x.source)} · 자료일 ${esc(cat.generated_at||"미확인")}</small></div>
  </section>`;
 }
 function update(){
  const ctx=window.StockRadarV2Bridge?.snapshot?.();if(!ctx)return;
  const out=document.getElementById("fx-catalog-results"),counter=document.getElementById("fx-catalog-count");
  if(out)out.innerHTML=rows(ctx);if(counter)counter.textContent=count(ctx);
 }
 document.addEventListener("input",e=>{
  if(e.target?.id==="fx-catalog-search"){state.query=e.target.value;update()}
 });
 document.addEventListener("click",e=>{
  const b=e.target.closest?.("button");if(!b)return;
  if("catalogPreview" in b.dataset){state.preview=b.dataset.catalogPreview;window.StockRadarV2Bridge?.render?.();e.stopPropagation();return}
  if("catalogCountry" in b.dataset){state.country=b.dataset.catalogCountry;state.preview=null;window.StockRadarV2Bridge?.render?.();e.stopPropagation();return}
  if("catalogBack" in b.dataset){state.preview=null;window.StockRadarV2Bridge?.render?.();e.stopPropagation();return}
  if("nrSelect" in b.dataset)state.preview=null;
 },true);
 window.StockCatalogUI={panel,focus,rows,count,getState:()=>({...state})};
})();