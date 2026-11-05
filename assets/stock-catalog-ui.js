/* A source-attributed search UI. List entries do not imply priced/AI-reviewed stocks. */
(()=>{"use strict";
 const state={query:"",country:"ALL",preview:null};
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const n=v=>typeof v==="number"&&Number.isFinite(v)?v.toLocaleString("ko-KR"):"—";
 const normalized=v=>String(v??"").toUpperCase().replace(/\.(KS|KQ)$/,"");
 function data(ctx){const c=ctx.data?.catalog;return c?.identifier_policy==="kr-six-character-alphanumeric-v2"&&Array.isArray(c?.items)?c.items:[];}
 function tracked(ctx){return new Map((ctx.data?.raw?.companies||[]).map(c=>[(c.market==="KR"?"KR:":"US:")+normalized(c.symbol),c]));}
 function statement(x,ctx){
  const feed=ctx.data?.financial,f=feed?.records?.[x.country+":"+x.symbol];
  if(feed?.identity_policy!=="official-issuer-identity-v2"||!f)return null;
  if(!feed.catalog_generated_at||feed.catalog_generated_at!==ctx.data?.catalog?.generated_at)return null;
  if(f.identity_verified!==true||f.country!==x.country||f.symbol!==x.symbol)return null;
  if(f.catalog_name!==x.name)return null;
  if(x.country==="KR"&&!/^\d{8}$/.test(String(f.corp_code||"")))return null;
  if(x.country==="US"&&!/^\d{1,10}$/.test(String(f.cik||"")))return null;
  return f;
 }
 function verifiedCount(ctx){return data(ctx).reduce((sum,x)=>{const f=statement(x,ctx);return sum+(f&&["available","partial","stale"].includes(f.status)?1:0)},0);}
 function financeAmount(v,currency){
  if(typeof v!=="number"||!Number.isFinite(v))return "미수집·미확인";
  const sign=v<0?"−":"";const a=Math.abs(v);
  if(currency==="KRW")return sign+(a>=1e12?n(a/1e12)+"조 원":a>=1e8?n(a/1e8)+"억 원":n(a)+"원");
  return sign+(a>=1e9?n(a/1e9)+"B USD":a>=1e6?n(a/1e6)+"M USD":n(a)+" USD");
 }
 function statementPanel(x,ctx){
  const f=statement(x,ctx);
  if(!f||!["available","partial","stale"].includes(f.status))
   return `<div class="fx-catalog-preview-info"><b>공식 재무제표: 아직 미확인</b>
     <p>${esc(ctx.data?.financial?.refresh_status==="blocked"?"최근 공식 자료 수집이 중단됐습니다.":x.country==="US"&&ctx.data?.financial?.financial_available?.US===0?"미국 공식 재무자료는 아직 수집되지 않았습니다.":"해당 종목과 공식 공시 법인의 연결·회계 자료를 확인하는 중입니다.")} 연결이 검증되지 않은 값과 임의 EPS는 표시하지 않습니다.</p></div>`;
  const m=f.metrics||{},key=[["매출액","revenue"],["영업이익","operating_income"],["순이익","net_income"],["자산","assets"],["부채","liabilities"],["자본","equity"],["영업현금흐름","cash_from_operations"],["FCF","free_cash_flow"],["공시 EPS","reported_eps"]];
  const cells=key.map(([name,field])=>`<div class="fx-catalog-finance-cell">
    <small>${name}</small><strong>${field==="reported_eps"&&typeof m[field]==="number"?esc(n(m[field])+" "+f.currency+"/주"):esc(financeAmount(m[field],f.currency))}</strong></div>`).join("");
  const date=f.period_end||f.period_end_label||"보고기간 미확인";
  const src=String(f.source_url||"");const link=/^https:\/\//.test(src)?
    `<a href="${esc(src)}" target="_blank" rel="noopener noreferrer">공식 재무 원문 확인</a>`:"";
  return `<div class="fx-catalog-preview-info fx-catalog-finance">
    <b>공시 재무 요약 ${f.status==="stale"?"· 오래된 보고서":""}</b>
    <small>기간 ${esc(date)} · ${esc(f.source)} · ${esc(f.consolidation||"공시 회계기준")} · 법인 연결 확인</small>
    <div class="fx-catalog-finance-grid">${cells}</div>
    <p>${f.last_refresh_error?"최근 재수집 실패 · 이전에 확인한 자료입니다. ":""}확인 시각 ${esc(f.checked_at?new Date(f.checked_at).toLocaleString("ko-KR",{timeZone:"Asia/Seoul"}):"미확인")} · 공시된 과거 실적의 일부 항목입니다. 미수집 항목은 공시가 없다는 뜻이 아닙니다. 다른 기간의 숫자를 합산하지 않습니다.</p>
    ${link}
  </div>`;
 }
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
    const filing=statement(x,ctx),verified=filing&&["available","partial","stale"].includes(filing.status);
    const text=(s?.active&&s?.value!==null?"AI "+esc(s.label)+" "+n(s.value*100)+"% 연구용":c?"심층분석 · AI "+(s?.stale?"기간 종료":"확인 중"):"AI 미발행")+
      (verified?" · 공식 재무 "+(filing.status==="stale"?"과거":"확인"):" · 재무 대기");
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
  const catalog=ctx.data?.catalog||{},total=data(ctx).length,kr=total?catalog.counts?.KR:0,us=total?catalog.counts?.US:0,financeTotal=verifiedCount(ctx),refresh=ctx.data?.financial?.refresh_status;
  return `<section class="fx-panel fx-catalog" aria-label="국내외 전체 상장종목 검색">
   <div class="fx-catalog-head"><div><h3>전체 상장종목 찾기</h3>
     <small>한국 ${n(kr)}개 · 미국 ${n(us)}개 · 명부 ${n(total)}개 · 법인 대조 재무 ${n(financeTotal)}개${refresh==="blocked"?" · 최근 수집 중단":refresh==="partial"?" · 일부 수집 실패":""}</small></div>
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
      <p>전체 상장종목 중 현재가·FCF·기업 가치평가가 아직 확인되지 않은 항목은 미확인으로 표시합니다. AI 상승 확률은 실제 모델이 해당 기간에 발행한 경우에만 보여줍니다.</p>
      <small>출처: ${esc(x.source)} · 자료일 ${esc(cat.generated_at||"미확인")}</small></div>
    ${statementPanel(x,ctx)}
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
 window.StockCatalogUI={panel,focus,rows,count,statement,statementPanel,verifiedCount,getState:()=>({...state})};
})();
