/* A source-attributed search UI. List entries do not imply priced/AI-reviewed stocks. */
(()=>{"use strict";
 const state={query:"",country:"ALL"};
 const empty=[];
 let modelCache=null;
 const searchCache=new WeakMap();
 const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const n=v=>typeof v==="number"&&Number.isFinite(v)?v.toLocaleString("ko-KR"):"—";
 const upper=v=>String(v??"").trim().toUpperCase();
 const normalized=(v,country)=>country==="KR"?upper(v).replace(/\.(KS|KQ)$/,""):upper(v);
 const countryOf=c=>upper(c?.country||c?.market);
 const keyOf=(country,symbol)=>country+":"+normalized(symbol,country);
 const currencies=new Set(Intl.supportedValuesOf?.("currency")||["KRW","USD","CNY","JPY","GBP","EUR","HKD"]);
 const financialCurrency=v=>currencies.has(v)?v:null;
 function data(ctx){const c=ctx?.data?.catalog;return c?.identifier_policy==="kr-six-character-alphanumeric-v2"&&Array.isArray(c?.items)?c.items:empty;}
 function selectionId(c){return c?.selection_id|| (c?.catalog_only?String(c.universe_key||keyOf(countryOf(c),c.symbol)):String(c?.symbol||""));}
 function symbolAliases(c){
  const item=c?.catalog_entry,country=countryOf(c),out=new Set();
  for(const value of [c?.symbol,c?.source_symbol,c?.provider_symbol,item?.symbol,item?.source_symbol]){
   const code=upper(value);if(!code)continue;out.add(code);
   if(country==="KR")out.add(normalized(code,country));
   // Share-class aliases aid selection only; they never create quotes or model outputs.
   if(country==="US"&&/^[A-Z]{1,5}[.-][A-Z]$/.test(code)){out.add(code.replace(".","-"));out.add(code.replace("-","."));}
  }
  const exchange=item?.exchange||c?.exchange;
  if(country==="KR"){
   const suffix=({KOSPI:".KS",KSC:".KS",KOSDAQ:".KQ",KOE:".KQ"})[exchange];
   if(suffix)for(const code of [...out])if(/^[A-Z0-9]{6}$/.test(code))out.add(code+suffix);
  }
  return [...out];
 }
 function addAlias(index,alias,value,identity){
  const id=upper(alias);if(!id)return;
  if(!index.has(id))index.set(id,value);
  else if(index.get(id)!==null&&identity(index.get(id))!==identity(value))index.set(id,null);
 }
 function model(ctx){
  const raw=ctx?.data?.raw||null,catalog=ctx?.data?.catalog||null;
  const rawRows=Array.isArray(raw?.companies)?raw.companies:empty,items=data(ctx);
  if(modelCache?.raw===raw&&modelCache?.catalog===catalog&&modelCache?.rawRows===rawRows&&modelCache?.items===items&&modelCache.rawLength===rawRows.length&&modelCache.itemLength===items.length)return modelCache;
  const catalogue=new Map(),catalogueAliases=new Map(),byKey=new Map(),aliases=new Map(),list=[];
  for(const item of items){
   if(!item||!["KR","US"].includes(item.country)||!item.symbol)continue;
   const key=keyOf(item.country,item.symbol);catalogue.set(key,item);
   for(const alias of symbolAliases(item))addAlias(catalogueAliases,keyOf(item.country,alias),item,x=>keyOf(x.country,x.symbol));
  }
  for(const row of rawRows){
   if(!row||typeof row!=="object"||!row.symbol)continue;
   const country=countryOf(row),rawKey=keyOf(country,row.symbol);
   let item=catalogue.get(rawKey)||null;
   if(!item){
    const found=new Set(symbolAliases(row).map(alias=>catalogueAliases.get(keyOf(country,alias))).filter(Boolean));
    if(found.size===1)item=[...found][0];
   }
   const universeKey=item?keyOf(item.country,item.symbol):rawKey;
   const c={...row,country,catalog_entry:item,catalog_only:false,universe_key:universeKey};
   list.push(c);if(!byKey.has(universeKey))byKey.set(universeKey,c);
  }
  for(const [key,item] of catalogue){
   if(byKey.has(key))continue;
   const c={symbol:item.symbol,name:item.name,country:item.country,market:item.country,exchange:item.exchange,
    source_symbol:item.source_symbol||item.symbol,catalog_entry:item,catalog_only:true,universe_key:key,
    price:null,price_session:null,currency:null,status:"catalog_only"};
   list.push(c);byKey.set(key,c);
  }
  for(const c of list){
   for(const alias of [selectionId(c),...symbolAliases(c)]){
    addAlias(aliases,alias,c,x=>x.universe_key);
    if(!alias.includes(":"))addAlias(aliases,c.country+":"+alias,c,x=>x.universe_key);
   }
  }
  // Existing raw IDs stay unchanged unless that bare/provider ID is ambiguous.
  // Every row still has a selectable, round-trippable qualified identity.
  for(const c of list)c.selection_id=c.catalog_only||aliases.get(upper(c.symbol))===null?c.universe_key:String(c.symbol);
  modelCache={raw,catalog,rawRows,items,rawLength:rawRows.length,itemLength:items.length,list,byKey,aliases,info:{official:items.length,total:list.length,
   tracked:list.filter(c=>!c.catalog_only).length,extra:list.filter(c=>!c.catalog_entry).length}};
  return modelCache;
 }
 function universe(ctx){return model(ctx).list;}
 function resolve(id,ctx){
  const key=upper(id);if(!key)return null;
  const index=model(ctx);
  if(index.byKey.has(key))return index.byKey.get(key);
  // Ambiguous bare/provider aliases remain unselectable; qualified keys retain identity.
  return index.aliases.get(key)||null;
 }
 function catalogItem(c,ctx){
  const id=typeof c==="string"?c:c?.universe_key||keyOf(countryOf(c),c?.symbol);
  return resolve(id,ctx)?.catalog_entry||null;
 }
 function searchText(c){
  if(!c||typeof c!=="object")return "";
  if(searchCache.has(c))return searchCache.get(c);
  const text=[c.name,c.catalog_entry?.name,c.universe_key,selectionId(c),...symbolAliases(c)].filter(Boolean).join(" ").toLocaleLowerCase();
  searchCache.set(c,text);return text;
 }
 function count(ctx){return data(ctx).length;}
 function info(ctx){return {...model(ctx).info};}
 function statement(x,ctx){
  if(!x)return null;
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
  if(!financialCurrency(currency))return "통화 미확인";
  const sign=v<0?"−":"";const a=Math.abs(v);
  if(currency==="KRW")return sign+(a>=1e12?n(a/1e12)+"조 원":a>=1e8?n(a/1e8)+"억 원":n(a)+"원");
  return sign+(a>=1e9?n(a/1e9)+"B":a>=1e6?n(a/1e6)+"M":n(a))+" "+currency;
 }
 function statementPanel(x,ctx){
  const f=statement(x,ctx);
  if(!f||!["available","partial","stale"].includes(f.status))
   return `<div class="fx-catalog-preview-info"><b>공식 재무제표: 아직 미확인</b>
     <p>${esc(ctx.data?.financial?.refresh_status==="blocked"?"최근 공식 자료 수집이 중단됐습니다.":x?.country==="US"&&ctx.data?.financial?.financial_available?.US===0?"미국 공식 재무자료는 아직 수집되지 않았습니다.":"해당 종목과 공식 공시 법인의 연결·회계 자료를 확인하는 중입니다.")} 연결이 검증되지 않은 값과 임의 EPS는 표시하지 않습니다.</p></div>`;
  const m=f.metrics||{},currency=financialCurrency(f.currency),key=[["매출액","revenue"],["영업이익","operating_income"],["순이익","net_income"],["자산","assets"],["부채","liabilities"],["자본","equity"],["영업현금흐름","cash_from_operations"],["FCF","free_cash_flow"],["공시 EPS","reported_eps"]];
  const cells=key.map(([name,field])=>`<div class="fx-catalog-finance-cell">
    <small>${name}</small><strong>${field==="reported_eps"&&typeof m[field]==="number"?esc(currency?n(m[field])+" "+currency+"/주":"통화 미확인"):esc(financeAmount(m[field],f.currency))}</strong></div>`).join("");
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
  const candidates=universe(ctx);
  const found=candidates.filter(x=>(state.country==="ALL"||state.country===x.country)&&
   (!q||searchText(x).includes(q)));
  return {found,total:candidates.length};
 }
 function sig(c,ctx){
  return window.StockRadarFlowV2?.signal?.(c,ctx)||null;
 }
 function rows(ctx){
  const {found,total}=matching(ctx);
  if(!total)return '<p class="fx-catalog-empty">공식 종목 목록을 확인하는 중입니다. 기존 심층분석은 계속 이용할 수 있습니다.</p>';
  if(!found.length)return '<p class="fx-catalog-empty">검색 결과가 없습니다. 회사명이나 종목코드를 확인해 주세요.</p>';
  return found.slice(0,35).map(c=>{
    const x=catalogItem(c,ctx),s=sig(c,ctx);
    const filing=statement(x,ctx),verified=filing&&["available","partial","stale"].includes(filing.status);
    const text=(s?.active&&typeof s.value==="number"?"AI "+esc(s.label)+" "+n(s.value*100)+"% 연구용":!c.catalog_only?"심층분석 · AI "+(s?.stale?"기간 종료":"확인 중"):"AI 미발행")+
      (verified?" · 공식 재무 "+(filing.status==="stale"?"과거":"확인"):" · 재무 대기");
    return `<button type="button" class="fx-catalog-row" data-nr-select="${esc(selectionId(c))}">
      <span class="fx-catalog-company"><strong>${esc(c.name)}</strong><small>${esc(c.symbol)} · ${esc(x?.exchange||c.exchange||c.market)}${x?"":" · 명부 미포함 기존 분석"}</small></span>
      <span class="fx-catalog-signal ${s?.active?"is-active":""}">${text}</span>
      <span aria-hidden="true">›</span>
    </button>`;
  }).join("");
 }
 function countText(ctx){
  const {found,total}=matching(ctx),catalog=ctx.data?.catalog||{},meta=info(ctx);
  return `검색 ${n(found.length)}건 / 선택 목록 ${n(total)}건 · 공식 명부 ${n(meta.official)}건${meta.extra?" + 명부 미포함 기존 분석 "+n(meta.extra)+"건":""} · ${catalog.status==="partial"?"일부 거래소 자료 누락 · ":""}가격·재무제표와는 별개`;
 }
 function panel(ctx){
  const catalog=ctx.data?.catalog||{},total=data(ctx).length,kr=total?catalog.counts?.KR:0,us=total?catalog.counts?.US:0,financeTotal=verifiedCount(ctx),refresh=ctx.data?.financial?.refresh_status;
  return `<section class="fx-panel fx-catalog" aria-label="국내외 전체 상장종목 검색">
   <div class="fx-catalog-head"><div><h3>전체 상장종목 찾기</h3>
     <small>한국 ${n(kr)}개 · 미국 ${n(us)}개 · 명부 ${n(total)}개 · 법인 대조 재무 ${n(financeTotal)}개${refresh==="blocked"?" · 최근 수집 중단":refresh==="partial"?(ctx.data?.financial?.current_run_failed===true?" · 일부 수집 실패":" · 일부 미확인"):""}</small></div>
     <small>${esc(catalog.generated_at?"출처 확인 "+new Date(catalog.generated_at).toLocaleDateString("ko-KR",{timeZone:"Asia/Seoul"}):"출처 수집 전")}</small></div>
   <div class="fx-catalog-toolbar"><input id="fx-catalog-search" type="search" value="${esc(state.query)}"
      aria-label="전체 상장종목 이름이나 종목코드 검색" placeholder="회사명·종목코드로 8천여 종목 검색"/>
    <div class="fx-catalog-countries">${[["ALL","전체"],["KR","한국"],["US","미국"]].map(([key,label])=>
      `<button type="button" data-catalog-country="${key}" class="${state.country===key?"active":""}">${label}</button>`).join("")}</div></div>
   <div id="fx-catalog-results" class="fx-catalog-results">${rows(ctx)}</div>
   <small id="fx-catalog-count" class="fx-catalog-count">${esc(countText(ctx))}</small>
  </section>`;
 }
 function safeSource(value){try{const u=new URL(String(value||""));return u.protocol==="https:"&&!u.username&&!u.password?u.href:""}catch{return""}}
 function profile(c,ctx){
  c=resolve(typeof c==="string"?c:c?.universe_key,ctx);
  if(!c?.catalog_only)return null;
  const x=catalogItem(c,ctx);if(!x)return null;
  const s=sig(c,ctx),cat=ctx.data.catalog,id=selectionId(c),source=safeSource(x.source_url);
  const has=!!s?.active&&!s.stale&&!s.unknown&&typeof s.value==="number"&&Number.isFinite(s.value)&&s.value>=0&&s.value<=1;
  const headline=has?s.label+" "+n(s.value*100)+"%":s?.stale?"기간 종료 · 과거 예측":s?.r?.status==="no_call"?"미발행 · 자료 대기":"미발행 · 검증 대기";
  const description=s?.status||"아직 유효한 AI 연구 신호가 없습니다.";
  const saved=(ctx.favorites||[]).some(value=>resolve(value,ctx)?.universe_key===c.universe_key);
  return `<section class="fx-panel fx-catalog-preview" aria-label="선택 기업 종합 분석">
    <div class="fx-panel-heading"><div><h3>${esc(x.name)}</h3><small>${esc(x.symbol)} · ${esc(x.exchange)}</small></div>
      <button type="button" data-catalog-back data-nr-screen="stocks" class="fx-link">종목 목록으로</button></div>
    <div class="fx-catalog-preview-info fx-catalog-quote"><b>저장 종가 미확인 · 차트 미수집</b>
      <p>가격·컨센서스 및 심층 판단 자료는 아직 확보되지 않았습니다. 아래에는 확인된 공시 재무와 출처를 표시합니다.</p></div>
    <div class="fx-catalog-preview-core"><small>AI 방향 연구</small>
     <strong>${esc(headline)}</strong><p>${esc(description)}</p>
     ${s?.r?.status==="research_prediction"?`<small>예측 발행 ${esc(s.r.issued_at||"미확인")} · 대상 ${esc(s.r.target?.start||"미확인")} ~ ${esc(s.r.target?.end||"미확인")}</small>`:""}
     <small>연구용 · 매수 성공 확률이나 투자 승인이 아닙니다.</small></div>
    <div class="fx-catalog-preview-info"><b>공식 상장종목 목록에 확인된 기업</b>
      <p>현재가·FCF·기업 가치평가가 아직 확인되지 않은 항목은 미확인으로 표시합니다. AI 방향 확률은 실제 모델이 해당 기간에 발행한 경우에만 보여줍니다.</p>
      <small>출처: ${esc(x.source)} · 자료일 ${esc(cat.generated_at||"미확인")}</small>
      ${source?`<a href="${esc(source)}" target="_blank" rel="noopener noreferrer">상장명부 원문 확인</a>`:""}</div>
    ${statementPanel(x,ctx)}
    <div class="fx-catalog-actions"><button type="button" data-nr-detail="${esc(id)}">재무·공시 상세</button>
      <button type="button" data-nr-star="${esc(id)}" aria-pressed="${saved}">${saved?"★ 관심 해제":"☆ 관심 등록"}</button></div>
  </section>`;
 }
 function focus(ctx){return profile(resolve(ctx?.selected,ctx),ctx);}
 function update(){
  const ctx=window.StockRadarV2Bridge?.snapshot?.();if(!ctx)return;
  const out=document.getElementById("fx-catalog-results"),counter=document.getElementById("fx-catalog-count");
  if(out)out.innerHTML=rows(ctx);if(counter)counter.textContent=countText(ctx);
 }
 document.addEventListener("input",e=>{
  if(e.target?.id==="fx-catalog-search"){state.query=e.target.value;update()}
 });
 document.addEventListener("click",e=>{
  const b=e.target.closest?.("button");if(!b)return;
  if("catalogPreview" in b.dataset){const bridge=window.StockRadarV2Bridge,ctx=bridge?.snapshot?.(),c=ctx&&resolve(b.dataset.catalogPreview,ctx);if(c)bridge.select?.(selectionId(c));e.stopPropagation();return}
  if("catalogCountry" in b.dataset){state.country=b.dataset.catalogCountry;window.StockRadarV2Bridge?.render?.();e.stopPropagation();return}
  // data-catalog-back carries the common screen action; preserve the selected issuer.
 },true);
 window.StockCatalogUI={universe,selectionId,resolve,searchText,catalogItem,profile,panel,focus,rows,count,info,
  statement,statementPanel,verifiedCount,getState:()=>({...state,preview:null})};
})();
