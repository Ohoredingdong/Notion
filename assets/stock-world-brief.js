/* One-screen, source-dated domestic / international / company risk intelligence.
   Headlines are explicitly *reports*, never facts or trading recommendations. */
(()=>{"use strict";
 const E=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const num=(v,d=1)=>typeof v==="number"&&Number.isFinite(v)?v.toLocaleString("ko-KR",{maximumFractionDigits:d}):"—";
 const ts=v=>{const n=Date.parse(v||"");return Number.isFinite(n)?new Date(n).toLocaleString("ko-KR",
  {timeZone:"Asia/Seoul",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false}):"시간 미확인"};
 const safe=v=>{try{const u=new URL(v);return u.protocol==="https:"?u.href:""}catch{return""}};
 const ago=value=>{const d=Date.parse(value||"");return Number.isFinite(d)?Math.round((Date.now()-d)/60000):null};
 const policyTopic=/선거|중간선거|개표|의회|관세|규제|정부|정책|제재|금리|연준|한은|물가|고용|방산|무역|election|congress|policy|tariff|federal reserve|regulation|sanction/i;
 const companyTopic=/실적|인수|합병|계약|수주|공급|공시|반도체|AI|기술주|기업|삼성|현대|엔비디아|애플|마이크로소프트|메타|테슬라|M&A|earnings|merger|acquisition|agreement|earnings|export|nvidia|apple|microsoft/i;
 function items(ctx,group){
  const d=ctx.data?.newsLink||{},raw=Array.isArray(d.items)?d.items:[];
  return raw.filter(x=>{
   if(!x||x.tab==="opinion"||!["A","B","OFFICIAL"].includes(x.source_tier)||!safe(x.url))return false;
   const time=Date.parse(x.published_at||"");
   if(!Number.isFinite(time)||time>Date.now()+300000||Date.now()-time>72*3600000)return false;
   if(group==="kr")return x.region==="kr"&&(x.topic_class==="policy"||x.topic_class==="market"||policyTopic.test(x.title||""));
   if(group==="world")return (x.region==="us"||x.region==="global")&&(x.topic_class==="policy"||x.topic_class==="market"||policyTopic.test(x.title||""));
   return companyTopic.test(x.title||"")&&(x.region==="kr"||x.region==="us"||x.region==="global");
  }).sort((a,b)=>Date.parse(b.published_at)-Date.parse(a.published_at));
 }
 function article(x){
  const name=E(x.source||"기사 제공처"),date=ts(x.published_at);
  return `<article class="fx-world-article">
   <a href="${E(safe(x.url))}" rel="noopener noreferrer" target="_blank">${E(x.title)}</a>
   <small>${name} · ${date} · 보도 제목 (원문 확인)</small>
  </article>`;
 }
 function panel(title,label,rows){
  return `<section class="fx-panel fx-world-panel"><div class="fx-world-panel-head"><h3>${E(title)}</h3><small>${E(label)}</small></div>
   <div class="fx-world-list">${rows.length?rows.slice(0,9).map(article).join(""):'<p class="fx-world-empty">최근 확인 가능한 기사가 없습니다. 수집 시각 또는 출처를 확인하세요.</p>'}</div></section>`;
 }
 function corporate(ctx){
  const real=(ctx.data?.events?.companies||[]).flatMap(c=>(c.events||[]).map(x=>({...x,company:c.name||c.symbol})));
  const audited=real.filter(x=>x.status==="active"&&x.sources?.some(s=>safe(s.url))&&
    x.event_date&&Date.parse(x.event_date)>Date.now()-60*86400000).sort((a,b)=>String(b.event_date||"").localeCompare(String(a.event_date||""))).slice(0,4);
  const snippets=audited.map(x=>{
    const first=x.sources.find(s=>safe(s.url));
    return `<article class="fx-world-article fx-world-company-flag">
      <a target="_blank" rel="noopener noreferrer" href="${E(safe(first.url))}">${E(x.company)} · ${E(x.title)}</a>
      <small>${E(first.publisher||"출처 미표기")} · ${E(x.event_date)} · 자동 제목 탐지, 공시 확정 아님</small>
     </article>`;
  }).join("");
  const rows=items(ctx,"company").slice(0,6).map(article).join("");
  return `<section class="fx-panel fx-world-panel"><div class="fx-world-panel-head"><h3>기업 · 산업 소식</h3><small>수주·실적·규제·기업간 이슈</small></div>
    <div class="fx-world-list">${snippets+rows||'<p class="fx-world-empty">기업 관련 확인 가능한 소식 없음</p>'}</div></section>`;
 }
 function metric(name,value,unit,date,source){
   const link=safe(source),formatted=E(name);
   return `<div class="fx-world-metric"><small>${formatted} · ${E(date||"기준 미확인")}</small><strong>${E(value)}${E(unit)}</strong>
    ${link?`<a rel="noopener noreferrer" target="_blank" href="${E(link)}">공식·원본 확인</a>`:""}</div>`;
 }
 function render(ctx){
  const macro=ctx.data?.macro?.indicators||{},news=ctx.data?.newsLink||{},date=ago(news.generated_at),
      flag=date===null?"뉴스 수집 전":date>90||news.stale?"뉴스 갱신 지연":"뉴스 저장본";
  const bok=macro.bok_policy||{},fed=macro.fed_policy||{},usd=macro.usdkrw||{},yield10=macro.us_10y||{},
      kospi=macro.kospi||{},nasdaq=macro.nasdaq||{};
  const gauges=[
    metric("코스피",num(kospi.value,2),"",kospi.date,kospi.source_url),
    metric("나스닥",num(nasdaq.value,2),"",nasdaq.date,nasdaq.source_url),
    metric("원/달러",num(usd.value,2),"원",usd.date,usd.source_url),
    metric("한국은행",num(bok.value,2),"%",bok.date,bok.source_url),
    metric("미국 10년물",num(yield10.value,2),"%",yield10.date,yield10.source_url),
    metric("연준 기준금리",typeof fed.low==="number"?num(fed.low,2)+"–"+num(fed.high,2):"—","%",fed.date,fed.source_url)
  ].join("");
  const pending=(ctx.data?.eventOutlook?.events||[]).filter(e=>{
    const t=Date.parse(e.event_at||"");return Number.isFinite(t)&&t>=Date.now()-3600000&&t<Date.now()+7*86400000
     &&safe(e.source_url);
  }).slice(0,4);
  return `<div class="fx-world-page">
   <div class="fx-intro fx-world-intro"><div><h2>국내외 경제 · 정책 · 기업 상황판</h2>
    <p>중요 보도·공식 지표·예정된 이벤트를 분리해서 확인합니다. 방향 전망이나 자동 매수 신호가 아닙니다.</p></div>
    <span class="fx-stamp">${E(flag)} · ${E(ts(news.generated_at))}</span></div>
   <div class="fx-world-metrics">${gauges}</div>
   <div class="fx-world-columns">
    ${panel("국내 정책 · 시장","한국 정책, 금리, 증시",items(ctx,"kr"))}
    ${panel("국제 정치 · 경제","미국 및 글로벌 정책과 시장",items(ctx,"world"))}
    ${corporate(ctx)}
   </div>
   <section class="fx-world-schedule" aria-label="확인할 예정 경제 일정">
    <div><b>다가오는 일정</b><small>기사와 일정은 발표 전후의 상태가 다릅니다.</small></div>
    <div class="fx-world-schedule-items">${pending.length?pending.map(x=>
      `<a href="${E(safe(x.source_url))}" rel="noopener noreferrer" target="_blank">${E(x.title)} · 예정 ${E(ts(x.event_at))}</a>`).join(""):
      '<span>신뢰 가능한 예정 일정 확인 전</span>'}</div>
   </section>
  </div>`;
 }
 window.StockWorldBrief={render};
})();