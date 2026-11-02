(()=>{'use strict';
function fxEscape(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}

function fxN(v){return typeof v==="number"&&Number.isFinite(v)?v:null;}

function fxNum(v,d=1){return fxN(v)===null?"—":v.toLocaleString("ko-KR",{maximumFractionDigits:d});}

function fxPct(v){return fxN(v)===null?"—":(v>0?"+":"")+fxNum(v,2)+"%";}

function fxMoney(v,c){return fxN(v)===null?"—":fxNum(v,c==="KRW"?0:2)+(c==="KRW"?"원":" "+(c||""));}

function fxContext(){return window.StockRadarV2Bridge?.snapshot?.()||{data:{},selected:"",screen:"home",favorites:[],market:"ALL"};}

function fxHelpers(){return window.StockRadarV2Bridge?.helpers||{};}

function fxRecord(c,ctx){
 const sym=String(c?.symbol||"").toUpperCase().replace(/\.(KS|KQ)$/,"");
 const rs=(ctx.data?.direction?.records||[]).filter(r=>String(r.symbol||"").toUpperCase().replace(/\.(KS|KQ)$/,"")===sym);
 const matched=rs.filter(r=>r.status==="research_prediction"&&r.probabilities).sort((a,b)=>Date.parse(b.issued_at||"")-Date.parse(a.issued_at||""));
 return matched.find(r=>r.mode==="daily")||matched[0]||rs.find(r=>r.mode==="daily")||rs[0]||null;
}

function fxPrediction(c,ctx){
 const r=fxRecord(c,ctx),p=r?.probabilities||{},raw=p[r?.direction],value=fxN(raw);
 const active=r?.status==="research_prediction"&&value!==null;
 const until=Date.parse(r?.target?.end||""),stale=active&&Number.isFinite(until)&&until<Date.now(),unknown=active&&!Number.isFinite(until);
 const label=!active?"미발행":r.direction==="up"?"상승":r.direction==="down"?"하락":"횡보";
 const klass=stale||unknown?"stale":r?.direction==="up"?"up":r?.direction==="down"?"down":"flat";
 return {r,p,label,klass,value:active?value:null,stale,unknown,active,status:!active?"AI 자료 없음":stale?"기간 종료 · 과거 기록":unknown?"시점 미확인":"연구용 방향 예측"};
}

function fxUniverse(ctx){
 const h=fxHelpers(),fav=new Set(ctx.favorites||[]);
 const data=[...(ctx.data?.raw?.companies||[])];
 data.sort((a,b)=>Number(fav.has(b.symbol))-Number(fav.has(a.symbol))+(Number(b.priority?.display_score??b.priority?.score??0)-Number(a.priority?.display_score??a.priority?.score??0))/1000);
 return data.filter(c=>{
  if(ctx.market!=="ALL"){
   if(typeof window.RadarMarkets?.match==="function"){if(!window.RadarMarkets.match(c,ctx.market))return false}
   else if(ctx.market==="KOSPI"&&!(c.market==="KR"&&!String(c.symbol).endsWith(".KQ")))return false;
   else if(ctx.market==="KOSDAQ"&&!(c.market==="KR"&&String(c.symbol).endsWith(".KQ")))return false;
   else if(ctx.market==="NASDAQ"&&c.market!=="US")return false;
   else if(ctx.market==="DOW")return false;
  }
  if(fxLocal.filter==="star"&&!fav.has(c.symbol))return false;
  if(["up","flat","down"].includes(fxLocal.filter)&&(!fxPrediction(c,ctx).active||fxRecord(c,ctx)?.direction!==fxLocal.filter))return false;
  if(fxLocal.filter==="ai"&&!fxPrediction(c,ctx).active)return false;
  return !fxLocal.search||(String(c.name||"")+" "+String(c.symbol)).toLowerCase().includes(fxLocal.search.toLowerCase());
 });
}

function fxChosen(ctx){
 const arr=fxUniverse(ctx);
 return arr.find(c=>String(c.symbol)===String(ctx.selected))||arr[0]||null;
}

function fxSignalChip(c,ctx){
 const x=fxPrediction(c,ctx);
 return `<span class="fx-signal ${x.klass}">${fxEscape(x.label)}${x.value===null?"":" "+fxNum(x.value*100,0)+"%"}</span><small class="fx-signal-note">${x.stale?"기간 종료":x.unknown?"시점 확인":x.active?"연구용":"없음"}</small>`;
}

function fxStockRows(ctx,expanded){
 const h=fxHelpers(),pool=fxUniverse(ctx),cap=expanded?fxLocal.limit:9;
 if(!pool.length)return '<div class="fx-chart-empty">현재 검색·필터에 해당하는 종목이 없습니다.</div>';
 return pool.slice(0,cap).map(c=>{
  const m=window.RadarMarkets?.label?window.RadarMarkets.label(c):c.market;
  const d=h.change?.(c);
  return `<button type="button" data-nr-select="${fxEscape(c.symbol)}" class="fx-row ${String(c.symbol)===String(fxChosen(ctx)?.symbol)?"active":""}" aria-label="${fxEscape(c.name)} 선택">
  <span class="fx-stock-name"><strong>${fxEscape(c.name)}</strong><small>${fxEscape(c.symbol)} · ${fxEscape(m||"분류 확인 전")}</small></span>
  <span class="fx-price">${fxMoney(c.price,c.currency)}<small class="${h.tone?.(d)||""}">${fxPct(d)}</small></span><span class="fx-signal-wrap">${fxSignalChip(c,ctx)}</span></button>`;
 }).join("");
}

function fxStockPanel(ctx,expanded){
 const h=fxHelpers(),pool=fxUniverse(ctx),cap=expanded?fxLocal.limit:9;
 return `<section class="fx-panel fx-list-panel"><div class="fx-panel-head"><div><h3>AI 종목 신호</h3><p>종목을 선택하면 분석이 바뀝니다.</p></div><button class="fx-link" type="button" data-nr-screen="stocks">${expanded?"목록":"전체"} ${h.I?.("arrow")||"›"}</button></div>
 <div class="fx-filters"><div class="fx-chips">${[["ALL","전체"],["KOSPI","코스피"],["KOSDAQ","코스닥"],["NASDAQ","나스닥"],["DOW","다우"]].map(([key,title])=>`<button type="button" data-rf-market="${key}" class="${ctx.market===key?"active":""}" aria-pressed="${ctx.market===key}">${title}</button>`).join("")}</div>
 ${expanded?`<div class="fx-chips direction">${[["all","전체"],["ai","AI 발행"],["up","상승"],["down","하락"],["star","관심"]].map(([key,title])=>`<button type="button" data-fx-filter="${key}" class="${fxLocal.filter===key?"active":""}" aria-pressed="${fxLocal.filter===key}">${title}</button>`).join("")}</div>`:""}
 <label class="fx-search">${h.I?.("search")||"⌕"}<input id="fx-search-input" type="search" aria-label="종목명·코드로 검색" placeholder="종목명 · 코드 검색" value="${fxEscape(fxLocal.search)}"></label></div>
 <div class="fx-columns"><span>기업 / 시장</span><span>저장 종가</span><span>AI 방향</span></div>
 <div class="fx-results" id="fx-results">${fxStockRows(ctx,expanded)}</div>
 <div class="fx-list-footer"><span id="fx-result-count">${Math.min(pool.length,cap)} / ${pool.length}개 · AI 연구용</span>${pool.length>cap?`<button type="button" ${expanded?"data-fx-more":"data-nr-screen=\"stocks\""}>${expanded?"더 보기":"전체 보기"}</button>`:'<button type="button" data-nr-screen="stocks">신호 필터 →</button>'}</div></section>`;
}

function fxChart(c){
 const h=fxHelpers(),p=h.pointData?.([String(c.symbol)],fxLocal.period),series=p?.series?.[0],vs=series?.prices||[];
 if(vs.length<2)return '<div class="fx-chart-empty">비교 가능한 실제 종가가 없습니다.</div>';
 const w=620,H=166,L=9,R=10,T=8,B=18,lo=Math.min(...vs),hi=Math.max(...vs),pad=(hi-lo||Math.abs(hi)*.01||1)*.18;
 const x=i=>L+i*(w-L-R)/(vs.length-1),y=v=>T+(hi+pad-v)*(H-B-T)/(hi-lo+2*pad),pts=vs.map((v,i)=>x(i).toFixed(1)+","+y(v).toFixed(1)).join(" ");
 const rising=vs.at(-1)>=vs[0],color=rising?"#df617a":"#4b83d3";
 return `<svg class="fx-chart-svg" viewBox="0 0 ${w} ${H}" role="img" aria-label="${fxEscape(c.name)} ${fxEscape(p.dates[0])}부터 ${fxEscape(p.dates.at(-1))}까지의 실제 종가 차트">
 ${[.2,.5,.8].map(k=>`<line x1="${L}" x2="${w-R}" y1="${T+k*(H-T-B)}" y2="${T+k*(H-T-B)}" stroke="#e6edf7" stroke-dasharray="4 4"/>`).join("")}
 <polygon points="${L},${H-B} ${pts} ${w-R},${H-B}" fill="${rising?"#fff0f4":"#eaf2ff"}"/>
 <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
 <circle cx="${x(vs.length-1)}" cy="${y(vs.at(-1))}" r="4.8" fill="${color}" stroke="white" stroke-width="2"/></svg>
 <div class="fx-chart-foot"><span>${fxEscape(p.dates[0])}</span><span>확정 일봉</span><span>${fxEscape(p.dates.at(-1))}</span></div>`;
}

function fxBars(c,ctx){
 const sig=fxPrediction(c,ctx),r=sig.r;
 if(sig.value===null)return '<div class="fx-chart-empty">이 종목의 방향 연구 신호는 미발행입니다.</div>';
 return `<div class="fx-ai-heading"><span class="fx-signal ${sig.klass}">${sig.label}</span><strong class="${sig.klass}">${fxNum(sig.value*100,1)}%</strong></div>
 ${[["상승","up"],["횡보","flat"],["하락","down"]].map(([n,k])=>{const v=fxN(r.probabilities?.[k]);return `<div class="fx-prob-row"><span>${n}</span><span class="fx-bar"><i class="${k}" style="width:${v===null?0:Math.max(0,Math.min(100,v*100))}%"></i></span><b>${v===null?"—":fxNum(v*100,1)+"%"}</b></div>`}).join("")}
 <p class="fx-footnote">${fxEscape(sig.status)}<br>${r.target?.end?"목표 종료 "+fxEscape(fxHelpers().T?.(r.target.end)):"목표 시점 미확인"} · 매수·수익률 확률 아님</p>`;
}

function fxFocus(ctx){
 const h=fxHelpers(),c=ctx.screen==="home"||ctx.screen==="stocks"?fxChosen(ctx):ctx.data?.raw?.companies?.find(v=>String(v.symbol)===String(ctx.selected));
 if(!c)return '<section class="fx-panel fx-focus"><div class="fx-chart-empty">기업을 선택해 주세요.</div></section>';
 const delta=h.change?.(c),venue=window.RadarMarkets?.label?window.RadarMarkets.label(c):c.market,why=h.flowReasonLines?.(c)||[];
 return `<section class="fx-panel fx-focus"><div class="fx-focus-head"><div><small>선택 종목 분석 · ${fxEscape(venue||"분류 미확인")}</small><h3>${fxEscape(c.name)} <span>${fxEscape(c.symbol)}</span></h3></div><div class="fx-icon-actions">
 <button type="button" class="${(ctx.favorites||[]).includes(c.symbol)?"saved":""}" data-nr-star="${fxEscape(c.symbol)}" title="관심 등록" aria-label="관심 등록">${h.I?.("star")||"☆"}</button>
 <button type="button" data-nr-detail="${fxEscape(c.symbol)}" title="종목 상세" aria-label="종목 상세">${h.I?.("arrow")||"›"}</button></div></div>
 <div class="fx-price-large"><strong>${fxMoney(c.price,c.currency)}</strong><span class="${h.tone?.(delta)||""}">${fxPct(delta)}</span><small>${fxEscape(c.price_session||"기준일 미확인")} 저장 종가</small></div>
 <div class="fx-focus-content"><div class="fx-chart-card"><div class="fx-mini-head"><b>실제 가격 흐름</b><div class="fx-periods">${[["1W","1주"],["1M","1개월"],["3M","3개월"],["6M","6개월"]].map(([key,title])=>`<button type="button" data-fx-period="${key}" class="${fxLocal.period===key?"active":""}">${title}</button>`).join("")}</div></div>${fxChart(c)}</div>
 <div class="fx-ai-card"><div class="fx-mini-head"><b>AI 방향 분석</b><span class="fx-signal stale">연구용</span></div>${fxBars(c,ctx)}</div></div>
 <div class="fx-evidence"><div><b>우선 확인할 근거</b><p title="${fxEscape(why[0]||"공식 자료 대조 필요")}">${fxEscape(why[0]||"공식 자료 대조 필요")}</p></div><div><b>확인할 위험</b><p title="${fxEscape(why[1]||"가격·공시 재확인")}">${fxEscape(why[1]||"가격·공시 재확인")}</p></div></div>
 <div class="fx-focus-actions"><button class="fx-action-primary" data-nr-detail="${fxEscape(c.symbol)}">${h.I?.("search")||"⌕"} 상세 분석</button><button class="fx-action-secondary" data-nr-screen="scenario">${h.I?.("chart")||"↗"} 시나리오</button></div></section>`;
}

function fxRisk(ctx){
 const h=fxHelpers(),c=ctx.screen==="home"||ctx.screen==="stocks"?fxChosen(ctx):ctx.data?.raw?.companies?.find(v=>String(v.symbol)===String(ctx.selected));
 if(!c)return '<div class="fx-chart-empty">종목을 선택해 주세요.</div>';
 const k=h.caseOf?.(c),why=h.flowReasonLines?.(c)||[],labels={attractive:"엄격 실사 항목 통과",conditional:"추가 검증 필요",avoid:"위험 검토 필요",price_wait:"가격 조건 대기",insufficient:"자료 보강 필요"};
 return `<div class="fx-risk-lines"><div class="fx-risk-item"><span class="fx-risk-icon">!</span><span><b>${fxEscape(k?labels[k.state]||"실사 확인 필요":"동일 시점 실사 미확인")}</b><div>AI 예측과 실사 판정은 별도입니다.</div></span></div>
 ${why.slice(0,2).map(x=>`<div class="fx-risk-item"><span class="fx-risk-icon">·</span><span>${fxEscape(x)}</span></div>`).join("")}</div>
 <p class="fx-subtext">${fxEscape(c.price_session||"기준일 미확인")} 종가 기준 · 매수 승인이 아님</p>`;
}

function fxMiniScore(ctx){
 const o=ctx.data?.learning?.overall||{},accur=fxN(o.accuracy);
 return `<div class="fx-score-grid"><div><small>사후 방향 일치율</small><strong>${accur===null?"—":fxNum(accur*100,1)+"%"}</strong></div><div><small>일치 / 평가</small><strong>${fxNum(o.correct,0)} / ${fxNum(o.samples,0)}</strong></div></div><div class="fx-danger-note">타이밍 유용성·실전 수익성 미입증</div>`;
}

function fxNav(ctx){
 const h=fxHelpers(),pages=[["home","홈","home"],["stocks","AI 종목","search"],["stockdetail","종목 분석","chart"],["scenario","시나리오","chart"],["performance","예측 검증","check"],["portfolio","포트폴리오","star"],["monitor","감시","check"]];
 return `<header class="fx-topbar"><div class="fx-brand"><span class="fx-brand-icon">${h.I?.("chart")||"◉"}</span><h1>투자 레이더</h1><span class="fx-mode-badge">저장 종가 · 연구용</span></div><nav class="fx-nav" aria-label="위젯 메뉴">${pages.map(([s,n,ico])=>`<button type="button" class="${ctx.screen===s?"active":""}" data-nr-screen="${s}" aria-current="${ctx.screen===s?"page":"false"}">${h.I?.(ico)||""}${n}</button>`).join("")}</nav><div class="fx-nav-tools"><button type="button" data-nr-screen="news" title="뉴스" aria-label="뉴스">${h.I?.("news")||"▤"}</button><button type="button" data-fx-refresh title="자료 다시 불러오기" aria-label="자료 새로고침">↻</button><button type="button" data-nr-screen="settings" title="설정" aria-label="설정">${h.I?.("settings")||"⚙"}</button></div></header>`;
}

function fxSteps(ctx){
 const h=fxHelpers(),steps=[["home","시장 확인"],["stocks","종목 선택"],["stockdetail","상세 분석"],["scenario","시나리오 확인"],["performance","예측 검증"],["portfolio","관심·모의투자"]];
 return `<div class="fx-flowbar"><div><strong>투자 분석 흐름</strong><small>선택 기업을 기준으로 연결</small></div><div class="fx-flow-links">${steps.map(([id,t],i)=>`${i?h.I?.("arrow")||"›":""}<button type="button" class="${ctx.screen===id?"active":""}" data-nr-screen="${id}">${t}</button>`).join("")}</div></div>`;
}

function fxHome(ctx){
 const h=fxHelpers(),c=fxChosen(ctx),connected=!!(ctx.data?.toss?.enabled&&ctx.data.toss.api_base);
 return `<section class="fx-intro"><div><h2>시장 현황과 선택 기업을 한눈에</h2><p>AI 종목 신호 → 종목 분석 → 가격 시나리오 → 검증 흐름으로 연결됩니다.</p></div><span class="fx-stamp">자료 ${fxEscape(h.T?.(ctx.data?.raw?.generated_at)||"미확인")} · ${connected?"조회 설정됨 / 응답 미확인":"실시간 시세 미연결"}</span></section>
 <section class="fx-market-row" aria-label="시장 지수"><div class="nr-market-grid">${h.indices?.()||""}</div></section>
 <div class="fx-home-grid">${fxStockPanel(ctx,false)}<div class="fx-focus-slot" id="fx-focus-slot">${fxFocus(ctx)}</div><aside class="fx-aside">
 <section class="fx-panel fx-side-card"><div class="fx-panel-head"><h3 class="fx-card-label">${h.I?.("check")||""} 투자 체크</h3><button class="fx-link" data-nr-detail="${fxEscape(c?.symbol||"")}">자세히 ${h.I?.("arrow")||"›"}</button></div><div id="fx-risk-slot">${fxRisk(ctx)}</div></section>
 <section class="fx-panel fx-side-card"><div class="fx-panel-head"><h3 class="fx-card-label">${h.I?.("news")||""} 주요 뉴스</h3><button class="fx-link" data-nr-screen="news">더보기 ${h.I?.("arrow")||"›"}</button></div><div class="fx-side-news">${h.compactAlerts?.()||"<p>저장된 뉴스 없음</p>"}</div></section>
 <section class="fx-panel fx-side-card"><div class="fx-panel-head"><h3 class="fx-card-label">${h.I?.("chart")||""} 예측 검증 요약</h3><button class="fx-link" data-nr-screen="performance">자세히 ${h.I?.("arrow")||"›"}</button></div>${fxMiniScore(ctx)}</section></aside></div>${fxSteps(ctx)}`;
}

function fxStockPage(ctx){
 const pool=fxUniverse(ctx);
 return `<div class="fx-intro"><div><h2>AI 종목 신호</h2><p>${pool.length}개 검색 결과 · 가격 방향 연구 분포이며 매수 추천이 아닙니다.</p></div><span class="fx-stamp">실시간 호가 아님</span></div><div class="fx-page-grid">${fxStockPanel(ctx,true)}<div class="fx-focus-slot" id="fx-focus-slot">${fxFocus(ctx)}</div></div>${fxSteps(ctx)}`;
}

function fxDetail(ctx){
 const h=fxHelpers(),c=ctx.data?.raw?.companies?.find(r=>String(r.symbol)===String(ctx.selected));
 if(!c)return '<div class="fx-chart-empty">종목을 먼저 선택해 주세요.</div>';
 const forecast=c.forecasts||{},fact=[["다음 FY 예상 PER",fxN(forecast.next_fy_pe)===null?"—":fxNum(forecast.next_fy_pe,1)+"배"],["EPS 30일 수정",fxPct(forecast.eps_revision30_pct)],["20일 평균 거래량 대비",fxN(c.technical?.volume_ratio)===null?"—":fxNum(c.technical.volume_ratio,2)+"배"],["저장 종가 기준일",c.price_session||"확인 필요"]];
 return `<div class="fx-intro"><div><h2>${fxEscape(c.name)} 상세 분석</h2><p>가격·AI·재무·위험 정보를 구분해서 보고, 다음 단계로 넘어갑니다.</p></div><button class="fx-link" data-nr-screen="stocks">종목 다시 선택 ${h.I?.("arrow")||"›"}</button></div><div class="fx-detail-grid"><div class="fx-detail-mode">${fxFocus(ctx)}</div>
 <aside class="fx-detail-right"><section class="fx-panel"><div class="fx-panel-head"><h3>핵심 재무·시장 지표</h3></div><div class="fx-detail-metrics">${fact.map(([a,b])=>`<div><small>${fxEscape(a)}</small><strong>${fxEscape(b)}</strong></div>`).join("")}</div></section>
 <section class="fx-panel fx-side-card"><div class="fx-panel-head"><h3>투자 검증 포인트</h3></div>${fxRisk(ctx)}</section>
 <section class="fx-panel"><div class="fx-panel-head"><h3>더 깊게 확인하기</h3></div><div class="fx-detail-cta"><button class="fx-action-primary" data-fx-deep="${fxEscape(c.symbol)}">기존 심층 분석</button><button class="fx-action-secondary" data-nr-screen="scenario">시나리오 분석</button></div></section></aside></div>${fxSteps(ctx)}`;
}

function fxScenarioPlot(c){
 const t=c.targets||{},vals=[["상단",t.high,"#d65c74"],["중앙",t.median,"#417ed0"],["하단",t.low,"#2a9a70"],["현재",c.price,"#8493a9"]].filter(x=>fxN(x[1])!==null);
 if(vals.length<2)return '<div class="fx-chart-empty">비교 가능한 가격 구간 자료가 없습니다.</div>';
 const n=vals.map(x=>x[1]),lo=Math.min(...n),hi=Math.max(...n),pad=(hi-lo||1)*.16,y=v=>22+(hi+pad-v)/(hi-lo+2*pad)*160;
 return `<div class="fx-target-diagram"><svg viewBox="0 0 640 205" role="img" aria-label="현재 종가와 실제 저장된 애널리스트 목표가의 수준 비교">
 ${vals.map(([title,v,color])=>`<line x1="110" x2="515" y1="${y(v)}" y2="${y(v)}" stroke="${color}" stroke-width="${title==="현재"?2:4}" ${title==="현재"?'stroke-dasharray="8 6"':""}/><circle cx="515" cy="${y(v)}" r="5" fill="${color}"/><text x="20" y="${y(v)+4}" font-size="15" fill="${color}">${title}</text><text x="535" y="${y(v)+4}" font-size="13" fill="${color}">${fxNum(v,0)}</text>`).join("")}</svg></div>`;
}

function fxScenario(ctx){
 const h=fxHelpers(),c=ctx.data?.raw?.companies?.find(r=>String(r.symbol)===String(ctx.selected));
 if(!c)return '<div class="fx-chart-empty">분석할 종목을 선택해 주세요.</div>';
 const t=c.targets||{},vals=[["상단",t.high,"optimistic"],["중앙",t.median,"base"],["하단",t.low,"conservative"]];
 return `<div class="fx-intro"><div><h2>${fxEscape(c.name)} · 가격 시나리오</h2><p>애널리스트 목표가의 상·중·하단을 비교하며, AI 가격방향 연구와는 별도입니다.</p></div><button class="fx-link" data-nr-detail="${fxEscape(c.symbol)}">상세 분석 ${h.I?.("arrow")||"›"}</button></div>
 <div class="fx-scenario-layout"><section class="fx-panel"><h3>목표가 구간 비교</h3><p>저장 종가 ${fxMoney(c.price,c.currency)} · ${fxEscape(c.price_session||"기준일 미확인")}</p>${fxScenarioPlot(c)}
 <div class="fx-target-row">${vals.map(([title,v,cl])=>`<div class="${cl}"><span>${title} 목표가</span><strong>${fxMoney(v,c.currency)}</strong><small>${fxN(v)===null||fxN(c.price)===null||c.price===0?"비교 불가":fxPct((v/c.price-1)*100)}</small></div>`).join("")}</div>
 <p class="fx-page-note">위 차트는 실제 목표가 수준을 비교한 것입니다. 미래 날짜별 가격 경로를 생성한 예측 차트가 아닙니다.</p></section>
 <aside class="fx-panel fx-scenario-aside"><h3>AI 방향 연구 분포</h3><p>발행 시점·기간 종료를 확인하세요.</p><div class="fx-ai-card">${fxBars(c,ctx)}</div>
 <p class="fx-page-note">AI 분류 확률과 애널리스트 목표가를 결합해 수익 확률로 표시하지 않습니다.</p>
 <div class="fx-detail-cta"><button class="fx-action-primary" data-nr-screen="performance">실제 검증 확인</button><button class="fx-action-secondary" data-nr-screen="portfolio">모의투자</button></div></aside></div>${fxSteps(ctx)}`;
}

function fxPerformance(ctx){
 const h=fxHelpers(),o=ctx.data?.learning?.overall||{},rec=o.recall||{};
 const facts=[["사후 방향 일치율",fxN(o.accuracy)===null?"—":fxNum(o.accuracy*100,1)+"%"],["일치 / 평가",fxNum(o.correct,0)+" / "+fxNum(o.samples,0)],["실제 상승 포착률",fxN(rec.up)===null?"—":fxNum(rec.up*100,1)+"%"],["실제 하락 포착률",fxN(rec.down)===null?"—":fxNum(rec.down*100,1)+"%"]];
 const utility=ctx.data?.autopilot?.timing_utility?.status, proven=utility==="proven";
 return `<div class="fx-intro"><div><h2>AI 예측 검증</h2><p>실제 결과와 비교하되, 적중률과 매매 수익률을 구분합니다.</p></div><span class="fx-stamp">자료 ${fxEscape(h.T?.(ctx.data?.learning?.generated_at)||"확인 전")}</span></div>
 <div class="nr-performance-grid">${facts.map(([label,n])=>`<section class="nr-panel"><small>${label}</small><strong>${n}</strong></section>`).join("")}</div>
 <div class="fx-validation-grid">${fxOutcomes(ctx)}<section class="nr-panel fx-validation-aside">${h.qualityHTML?.()||""}<div class="nr-validation-note"><b>검증 판정</b><p>${proven?"검증된 범위 내 유용성 추가 확인 필요":"실전 매매 타이밍의 유용성은 아직 입증되지 않았습니다."}</p><p>확률은 연구 모델 분류값이며 미래 매수 성공률이 아닙니다.</p></div><button data-nr-forecast class="nr-action">전체 예측 성적표</button></section></div>${fxSteps(ctx)}`;
}
function fxOutcomes(ctx){
 const h=fxHelpers(),input=Array.isArray(ctx.data?.outcomes)?ctx.data.outcomes:[],seen=new Set();
 const rows=input.filter(r=>{
  if(r.status!=="observed"||r.public_before_target_verified!==true)return false;
  const key=String(r.id||[r.symbol,r.mode,r.issued_at,r.target?.start].join("|"));
  if(seen.has(key))return false;seen.add(key);return true;
 }).sort((a,b)=>Date.parse(b.evaluated_at||0)-Date.parse(a.evaluated_at||0)).slice(0,8);
 const dir={up:"상승",down:"하락",flat:"횡보"};
 return `<section class="nr-panel fx-audit-table"><div class="nr-head"><h3>최근 실제 관측 검증</h3><span class="nr-sub">발행 시점 검증 표본 · ${rows.length}건 표시</span></div><div class="fx-table-clip"><table class="fx-audit"><thead><tr><th>검증 시각</th><th>종목</th><th>예측</th><th>실제</th><th>결과</th></tr></thead><tbody>${rows.length?rows.map(r=>`<tr><td>${fxEscape(h.T?.(r.evaluated_at)||"시각 미확인")}</td><td>${fxEscape(r.symbol||"—")}</td><td>${fxEscape(dir[r.predicted]||r.predicted||"—")}</td><td>${fxEscape(dir[r.actual]||r.actual||"—")}</td><td><span class="fx-mark ${r.correct===true?'yes':'no'}">${r.correct===true?'일치':'불일치'}</span></td></tr>`).join(""):'<tr><td colspan="5">발행·평가 이력이 확인된 결과가 없습니다.</td></tr>'}</tbody></table></div><p class="fx-table-hint">실제 체결·수익 데이터가 아닌 가격 관측 기반의 사후 평가입니다.</p></section>`;
}
function fxRender(){
 const ctx=fxContext(),h=fxHelpers(),s=ctx.screen||"home";
 const body=s==="home"?fxHome(ctx):s==="stocks"?fxStockPage(ctx):s==="stockdetail"?fxDetail(ctx):s==="scenario"?fxScenario(ctx):s==="performance"?fxPerformance(ctx):s==="monitor"?h.renderMonitor?.():s==="portfolio"?h.renderPortfolio?.():s==="news"?h.renderNews?.():s==="settings"?h.renderSettings?.():fxHome(ctx);
 return `<div class="fx-root">${fxNav(ctx)}<div class="fx-stage ${s==="home"?"fx-stage-home":"fx-stage-other"}" data-screen="${fxEscape(s)}">${body||""}</div></div>`;
}

function fxHandleClick(e){
 const button=e.target.closest?.("button");if(!button)return;
 const ds=button.dataset,bridge=window.StockRadarV2Bridge;if(!bridge)return;
 if(ds.nrScreen==="home"){fxLocal.search="";fxLocal.filter="all";fxLocal.limit=36}
 if("fxRefresh" in ds){bridge.refresh();return}
 if(ds.fxPeriod){fxLocal.period=ds.fxPeriod;bridge.render();return}
 if(ds.fxFilter){fxLocal.filter=ds.fxFilter;fxLocal.limit=36;const c=fxChosen(fxContext());if(c)bridge.select(c.symbol);else bridge.render();return}
 if("fxMore" in ds){fxLocal.limit+=36;bridge.render();return}
 if(ds.fxDeep){bridge.deep(ds.fxDeep);return}
}

function fxHandleInput(e){
 if(e.target?.id!=="fx-search-input")return;
 fxLocal.search=e.target.value;
 const ctx=fxContext(),list=document.getElementById?.("fx-results"),count=document.getElementById?.("fx-result-count"),expanded=ctx.screen==="stocks",pool=fxUniverse(ctx),cap=expanded?fxLocal.limit:9;
 if(list)list.innerHTML=fxStockRows(ctx,expanded);
 if(count)count.textContent=Math.min(pool.length,cap)+" / "+pool.length+"개 · AI 연구용";
}
const fxLocal={filter:'all',search:'',limit:36,period:'1M'};
document.addEventListener('click',fxHandleClick);document.addEventListener('input',fxHandleInput);
window.StockRadarFlowV2={render:fxRender,pick:()=>fxChosen(fxContext()),version:'ux-flow-20261102-v3-viewport'};
const fxBoot=()=>window.StockRadarV2Bridge?.render?.();
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',fxBoot);else fxBoot();
})();