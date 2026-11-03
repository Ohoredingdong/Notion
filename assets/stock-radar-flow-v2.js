(()=>{'use strict';
function fxEscape(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}

function fxN(v){return typeof v==="number"&&Number.isFinite(v)?v:null;}

function fxNum(v,d=1){return fxN(v)===null?"—":v.toLocaleString("ko-KR",{maximumFractionDigits:d});}

function fxPct(v){return fxN(v)===null?"—":(v>0?"+":"")+fxNum(v,2)+"%";}

function fxMoney(v,c){return fxN(v)===null?"—":v.toLocaleString("ko-KR",{minimumFractionDigits:c==="KRW"?0:2,maximumFractionDigits:c==="KRW"?0:2})+(c==="KRW"?"원":" "+(c||""));}

function fxContext(){return window.StockRadarV2Bridge?.snapshot?.()||{data:{},selected:"",screen:"home",favorites:[],market:"ALL"};}

function fxHelpers(){return window.StockRadarV2Bridge?.helpers||{};}

function fxRecord(c,ctx){
 const key=String(c?.symbol||"").toUpperCase().replace(/\.(KS|KQ)$/,"");
 const records=(ctx.data?.direction?.records||[]).filter(r=>String(r.symbol||"").toUpperCase().replace(/\.(KS|KQ)$/,"")===key);
 records.sort((a,b)=>{
  const ta=Date.parse(a.issued_at||""),tb=Date.parse(b.issued_at||"");
  if(Number.isFinite(ta)&&Number.isFinite(tb)&&ta!==tb)return tb-ta;
  if(Number.isFinite(tb)&&!Number.isFinite(ta))return 1;
  if(Number.isFinite(ta)&&!Number.isFinite(tb))return -1;
  return Number(b.mode==="intraday")-Number(a.mode==="intraday");
 });
 return records[0]||null;
}
function fxModelQuality(ctx){
 const learning=ctx.data?.learning||{},overall=learning.overall||{},policy=learning.policy||{};
 const audit=ctx.data?.accuracyAudit||null;
 const aligned=!!audit&&audit.source?.learning_generated_at===learning.generated_at&&audit.source?.forecasts_generated_at===ctx.data?.direction?.generated_at;
 const n=fxN(overall.samples),correct=fxN(overall.correct),days=fxN(overall.calendar_days),acc=fxN(overall.accuracy),up=fxN(overall.recall?.up);
 const minN=fxN(policy.minimum_paired_targets)??120,minDays=fxN(policy.minimum_sessions)??20;
 const paired=learning.baseline_paired||{};
 const brier=fxN(paired.baseline?.brier_loss)!==null&&fxN(paired.model?.brier_loss)!==null?paired.baseline.brier_loss-paired.model.brier_loss:null;
 const threshold=fxN(policy.minimum_brier_gain)??.01;
 const hasEnough=n!==null&&n>=minN&&days!==null&&days>=minDays;
 const hasBrier=brier!==null&&brier>=threshold;
 const accepted=aligned&&hasEnough&&hasBrier&&audit?.promotion_gates?.promotion_evidence_sufficient===true&&audit?.promotion_gates?.live_profitability_proven===true;
 return {status:!hasEnough?"표본·기간 부족":!hasBrier?"확률 품질 개선 미달":accepted?"검증 범위 제한 확인":"실전 효용 미입증",accepted,aligned,n,correct,days,acc,up,minN,minDays,brier,threshold,hasEnough,hasBrier};
}
function fxPrediction(c,ctx){
 const r=fxRecord(c,ctx),p=r?.probabilities||{};
 const choices=["up","flat","down"],numbers=choices.map(k=>fxN(p[k]));
 const validDistribution=numbers.every(n=>n!==null&&n>=0&&n<=1)&&Math.abs(numbers.reduce((a,b)=>a+b,0)-1)<=0.025;
 const knownDirection=choices.includes(r?.direction);
 const val=validDistribution&&knownDirection?fxN(p[r.direction]):null;
 const active=r?.status==="research_prediction"&&val!==null;
 const until=Date.parse(r?.target?.end||""),issued=Date.parse(r?.issued_at||"");
 const invalidDates=Number.isFinite(until)&&Number.isFinite(issued)&&until<issued;
 const futureIssued=Number.isFinite(issued)&&issued>Date.now()+5*60*1000;
 const usable=active&&!invalidDates&&!futureIssued;
 const stale=usable&&Number.isFinite(until)&&until<Date.now();
 const unknown=usable&&!Number.isFinite(until);
 const label=!usable?"미산출":r.direction==="up"?"상승":r.direction==="down"?"하락":"횡보";
 const klass=!usable||stale||unknown?"stale":r.direction==="up"?"up":r.direction==="down"?"down":"flat";
 const status=r?.status==="research_prediction"&&!usable?(futureIssued?"미래 발행 시각 오류 · 사용 불가":"분포·목표기간 오류 · 사용 불가"):
  !usable?"현재 연구 신호 없음":stale?"기간 종료 · 과거 기록":unknown?"기간 정보 미확인 · 연구용":"연구용 방향 분류";
 return {r,p,label,klass,value:usable?val:null,stale,unknown,active:usable,status};
}
function fxUniverse(ctx){
 const h=fxHelpers(),fav=new Set(ctx.favorites||[]);
 const data=[...(ctx.data?.raw?.companies||[])];
 data.sort((a,b)=>{
  if(ctx.screen==="home"){const pin=Number(String(b.symbol)===String(ctx.selected))-Number(String(a.symbol)===String(ctx.selected));if(pin)return pin;}
  return Number(fav.has(b.symbol))-Number(fav.has(a.symbol))+(Number(b.priority?.display_score??b.priority?.score??0)-Number(a.priority?.display_score??a.priority?.score??0))/1000;
 });
 return data.filter(c=>{
  if(ctx.market!=="ALL"){
   if(typeof window.RadarMarkets?.match==="function"){if(!window.RadarMarkets.match(c,ctx.market))return false}
   else if(ctx.market==="KOSPI"&&!(c.market==="KR"&&!String(c.symbol).endsWith(".KQ")))return false;
   else if(ctx.market==="KOSDAQ"&&!(c.market==="KR"&&String(c.symbol).endsWith(".KQ")))return false;
   else if(ctx.market==="NASDAQ"&&c.market!=="US")return false;
   else if(ctx.market==="DOW")return false;
  }
  if(fxLocal.filter==="star"&&!fav.has(c.symbol))return false;
  if(["up","flat","down"].includes(fxLocal.filter)){const sig=fxPrediction(c,ctx);if(!sig.active||sig.stale||sig.unknown||sig.r?.direction!==fxLocal.filter)return false;}
  if(fxLocal.filter==="ai"){const sig=fxPrediction(c,ctx);if(!sig.active||sig.stale||sig.unknown)return false;}
  return !fxLocal.search||(String(c.name||"")+" "+String(c.symbol)).toLowerCase().includes(fxLocal.search.toLowerCase());
 });
}

function fxChosen(ctx){
 const arr=fxUniverse(ctx);
 return arr.find(c=>String(c.symbol)===String(ctx.selected))||arr[0]||null;
}

function fxSignalChip(c,ctx){
 const x=fxPrediction(c,ctx);
 return `<span class="fx-signal ${x.klass}">${fxEscape(x.label)}${x.value===null?"":" "+fxNum(x.value*100,0)+"%"}</span><small class="fx-signal-note">${x.stale?"기간 종료":x.unknown?"시점 확인":x.active?"연구용":x.r?.status==="research_prediction"?"검증 오류":"발행 없음"}</small>`;
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
 <div class="fx-chips direction">${[["all","전체"],["ai","기간 유효"],["up","상승"],["down","하락"],["star","★ 관심"]].map(([key,title])=>`<button type="button" data-fx-filter="${key}" class="${fxLocal.filter===key?"active":""}" aria-pressed="${fxLocal.filter===key}">${title}</button>`).join("")}</div>
 <label class="fx-search">${h.I?.("search")||"⌕"}<input id="fx-search-input" type="search" aria-label="종목명·코드로 검색" placeholder="종목명 · 코드 검색" value="${fxEscape(fxLocal.search)}"></label></div>
 <div class="fx-columns"><span>기업 / 시장</span><span>저장 종가</span><span>AI 방향</span></div>
 <div class="fx-results" id="fx-results">${fxStockRows(ctx,expanded)}</div>
 <div class="fx-list-footer"><span id="fx-result-count">${Math.min(pool.length,cap)} / ${pool.length}개 · AI 연구용</span>${pool.length>cap?`<button type="button" ${expanded?"data-fx-more":"data-nr-screen=\"stocks\""}>${expanded?"더 보기":"전체 보기"}</button>`:'<button type="button" data-nr-screen="stocks">신호 필터 →</button>'}</div></section>`;
}

function fxChart(c){
 const h=fxHelpers(),p=h.pointData?.([String(c.symbol)],fxLocal.period),line=p?.series?.[0],vals=line?.prices||[];
 if(vals.length<2)return '<div class="fx-chart-empty">비교 가능한 저장 종가가 없습니다. 기간을 바꾸거나 자료 상태를 확인해 주세요.</div>';
 const original=p.sets?.[0],history=(original?.bars||[]).filter(b=>b?.origin!=="latest_research_snapshot"&&b?.not_interpolated!==true);
 const ma=n=>{
  const map=new Map(),buf=[];let total=0;
  for(const b of history){
   const v=fxN(b.close);if(v===null)continue;
   buf.push(v);total+=v;
   if(buf.length>n)total-=buf.shift();
   if(buf.length===n)map.set(b.date,total/n);
  }
  return p.dates.map(date=>map.get(date)??null);
 };
 const m20=ma(20),m60=ma(60),extra=[...m20,...m60].filter(v=>v!==null);
 const W=700,H=230,L=58,R=64,T=14,B=31,low=Math.min(...vals,...extra),high=Math.max(...vals,...extra),pad=(high-low||Math.abs(high)*.01||1)*.14;
 const x=i=>L+i*(W-L-R)/Math.max(1,vals.length-1),y=v=>T+(high+pad-v)*(H-T-B)/(high-low+2*pad);
 const points=vals.map((v,i)=>`${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" "),rising=vals.at(-1)>=vals[0],stroke=rising?"#d95574":"#3b78d0";
 const maLine=(numbers,color)=>{
  const parts=[],draw=[];for(let i=0;i<numbers.length;i++){
   if(numbers[i]===null){if(parts.length>1)draw.push(`<polyline points="${parts.join(' ')}" fill="none" stroke="${color}" stroke-width="2.15" opacity=".92"/>`);parts.length=0;continue}
   parts.push(`${x(i).toFixed(1)},${y(numbers[i]).toFixed(1)}`);
  }
  if(parts.length>1)draw.push(`<polyline points="${parts.join(' ')}" fill="none" stroke="${color}" stroke-width="2.15" opacity=".92"/>`);
  return draw.join("");
 };
 const ticks=[0,.5,1].map(t=>{const v=low+(high-low)*t;return `<line x1="${L}" x2="${W-R+3}" y1="${y(v)}" y2="${y(v)}" stroke="#e9eff8" stroke-dasharray="4 5"/><text x="${L-8}" y="${y(v)+4}" fill="#8ea1bc" font-size="12" text-anchor="end">${fxNum(v,0)}</text>`}).join("");
 const latest=p.dates.at(-1),hist=original?.historical_end,additional=original?.chart_status==="snapshot_appended";
 const vol=new Map(history.map(b=>[b.date,b.volume])),numbers=p.dates.map(d=>fxN(vol.get(d)));
 const max=Math.max(0,...numbers.filter(v=>v!==null));
 const bars=max>0?numbers.map((v,i)=>v===null?"":`<rect x="${x(i)-3}" y="${H-B-18*v/max}" width="6" height="${18*v/max}" fill="#b8c9e8" opacity=".73"/>`).join(""):"";
 const actualPoints=additional?vals.slice(0,-1).map((v,i)=>`${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" "):points;
 const final=additional?`<line x1="${x(vals.length-2)}" y1="${y(vals.at(-2))}" x2="${x(vals.length-1)}" y2="${y(vals.at(-1))}" stroke="${stroke}" stroke-width="3.2" stroke-dasharray="7 5"/>`:"";
 const annotation=additional?`실제 일봉 ${fxEscape(hist)} · 이후 저장 종가 ${fxEscape(latest)} (마지막 선 점선)`:original?.chart_status==="aligned"?"완료 일봉 기준 종가":"차트 기준일 "+fxEscape(hist||"미확인");
 return `<svg class="fx-chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${fxEscape(c.name)} 실제 저장된 종가 및 계산된 20일, 60일 이동평균선">
 <defs><linearGradient id="fx-price-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${stroke}" stop-opacity=".18"/><stop offset="1" stop-color="${stroke}" stop-opacity=".018"/></linearGradient></defs>
 ${ticks}<polygon points="${L},${H-B} ${points} ${W-R},${H-B}" fill="url(#fx-price-fill)"/>
 ${bars}${maLine(m60,"#a994e9")}${maLine(m20,"#ecb94c")}
 <polyline points="${actualPoints}" fill="none" stroke="${stroke}" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>
 ${final}
 <circle cx="${x(vals.length-1)}" cy="${y(vals.at(-1))}" r="4.5" fill="${stroke}" stroke="white" stroke-width="2"/>
 <rect x="${W-R+5}" y="${Math.max(2,Math.min(H-30,y(vals.at(-1))-13))}" width="${R-9}" height="25" rx="7" fill="#284d7b"/>
 <text x="${W-R+(R-9)/2+5}" y="${Math.max(2,Math.min(H-30,y(vals.at(-1))-13))+17}" text-anchor="middle" fill="#fff" font-size="11" font-weight="750">${fxNum(vals.at(-1),0)}</text>
 </svg>
 <div class="fx-v5-ma-legend"><span><i class="close"></i>종가</span>${m20.some(v=>v!==null)?'<span><i class="ma20"></i>MA20</span>':''}${m60.some(v=>v!==null)?'<span><i class="ma60"></i>MA60</span>':''}<span>거래량: 저장된 실제 일봉</span></div>
 <div class="fx-chart-foot"><span>${fxEscape(p.dates[0])}</span><span>${fxEscape(annotation)}</span><span>${fxEscape(latest)}</span></div>`;
}
function fxStockGroupQuality(c,ctx){
 const symbol=String(c?.symbol||"").toUpperCase().replace(/\.(KS|KQ)$/,"");
 const mode=fxRecord(c,ctx)?.mode;
 if(!mode)return null;
 const candidates=Object.entries(ctx.data?.learning?.groups||{}).filter(([key,value])=>{
  const parts=key.toUpperCase().split("|");
  return parts[0].replace(/\.(KS|KQ)$/,"")===symbol&&parts[1]?.toLowerCase()===mode&&fxN(value?.metrics?.samples)!==null;
 }).sort((a,b)=>{
  const provider=key=>key.includes("provider-latency-30m-v1")?1:0;
  return provider(b[0])-provider(a[0])||(b[1].metrics.samples-a[1].metrics.samples);
 });
 const found=candidates[0];
 if(!found)return null;
 const m=found[1].metrics||{};
 return {mode,samples:m.samples,correct:fxN(m.correct),accuracy:fxN(m.accuracy),sessions:fxN(m.calendar_days),enough:m.samples>=120&&m.calendar_days>=20};
}
function fxBars(c,ctx){
 const sig=fxPrediction(c,ctx),r=sig.r,stockQuality=fxStockGroupQuality(c,ctx);
 if(sig.value===null)return `<div class="fx-chart-empty">${fxEscape(sig.status||"유효한 연구 신호가 없습니다.")}</div>`;
 return `<div class="fx-ai-heading"><span class="fx-signal ${sig.klass}">${sig.label}</span><strong class="${sig.klass}">${fxNum(sig.value*100,1)}%</strong></div>
 ${[["상승","up"],["횡보","flat"],["하락","down"]].map(([n,k])=>{const v=fxN(r.probabilities?.[k]);return `<div class="fx-prob-row"><span>${n}</span><span class="fx-bar"><i class="${k}" style="width:${v===null?0:Math.max(0,Math.min(100,v*100))}%"></i></span><b>${v===null?"—":fxNum(v*100,1)+"%"}</b></div>`}).join("")}
 <p class="fx-footnote">${fxEscape(sig.status)}<br>방향 판정: 대상 구간 시작 시가 → 종료 종가 · 횡보 기준 ±${fxNum(r.neutral_band_pct,2)}% · 전일 종가 대비 등락과 다름<br>${r.target?.end?"목표 종료 "+fxEscape(fxHelpers().T?.(r.target.end)):"목표 시점 미확인"} · 매수·수익률 확률 아님${stockQuality?`<br>${fxEscape(stockQuality.mode==="intraday"?"단기":"일간")} 종목별 사후 관측 ${fxNum(stockQuality.correct,0)}/${fxNum(stockQuality.samples,0)}건 · ${stockQuality.enough?"추가 검증 필요":"표본 매우 부족"}`:""}</p>`;
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

function fxV5Format(v,d=1){return fxN(v)===null?"—":fxNum(v,d)}

function fxV5Facts(c){
 const f=c.forecasts||{},h=c.history||{},b=c.balance||{},t=c.technical||{};
 const metrics=[
  ["예상 PER",fxN(f.next_fy_pe)===null?"—":fxNum(f.next_fy_pe,1)+"배"],
  ["EPS 수정",fxPct(f.eps_revision30_pct)],
  ["매출 변화",fxN(h.revenue_growth)===null?"—":fxPct(h.revenue_growth)],
  ["현금흐름 FCF",fxAmount(h.fcf,c.currency)],
  ["순차입금/EBITDA",fxN(b.net_debt_ebitda)===null?"—":fxNum(b.net_debt_ebitda,1)+"배"],
  ["20일 거래량",fxN(t.volume_ratio)===null?"—":fxNum(t.volume_ratio,2)+"배"]
 ];
 return metrics;
}

function fxV5FocusItems(c,which){
 const assessment=c.assessment||{},s=c.short||{},h=c.history||{},t=c.technical||{},f=c.forecasts||{};
 const stringify=x=>typeof x==="string"?x:x?.text||x?.reason||x?.label||"";
 let items=which==="bull"?
  [assessment.why?.[0],fxN(f.eps_revision30_pct)!==null&&f.eps_revision30_pct>0?"EPS 추정 상향 "+fxPct(f.eps_revision30_pct):null,fxN(h.revenue_growth)!==null&&h.revenue_growth>0?"보고기간 매출 성장 "+fxPct(h.revenue_growth):null,fxN(h.fcf)!==null&&h.fcf>0?"보고된 잉여현금흐름 양수":null]:
  [...(assessment.risks||[]).slice(0,3),...(assessment.missing||[]).slice(0,2),fxN(f.eps_revision30_pct)!==null&&f.eps_revision30_pct<0?"EPS 추정치 하향 "+fxPct(f.eps_revision30_pct):null];
 items=items.map(stringify).filter(Boolean).slice(0,3);
 if(!items.length)items=[which==="bull"?"공식 실적·사업 근거 대조 전":"최신 공시 및 위험 지표 추가 검증 필요"];
 return items.map(v=>`<div class="fx-v5-bullet ${which==='bull'?'good':'bad'}"><span>${which==='bull'?'○':'!'}</span><p>${fxEscape(v)}</p></div>`).join("");
}

function fxV5StockNews(ctx,c){
 const data=ctx.data?.events?.companies||[],id=String(c.symbol).replace(/\.(KS|KQ)$/,"");
 const matched=data.find(x=>String(x.symbol||"").replace(/\.(KS|KQ)$/,"")===id);
 let items=[];
 const visit=(owner,x)=>{const first=(x.sources||[]).find(y=>fxSafeHref(y?.url));if(first)items.push({...x,owner,source:first})};
 (matched?.events||[]).forEach(x=>visit(matched.name||c.name,x));
 if(items.length<3)for(const company of data)for(const x of company.events||[]){if(items.length>=6)break;visit(company.name,x)}
 const seen=new Set();
 items=items.filter(x=>{const key=x.source.url;if(seen.has(key))return false;seen.add(key);return true})
  .sort((a,b)=>String(b.event_date||"").localeCompare(String(a.event_date||""))).slice(0,3);
 return items.map((x,i)=>`<div class="fx-v5-newsrow"><span class="fx-v5-newsindex">${i+1}</span><div><a href="${fxEscape(fxSafeHref(x.source.url))}" rel="noopener noreferrer" target="_blank">${fxEscape(x.title||"기업 이슈 확인")}</a><small>${fxEscape(x.owner||"기업")} · ${fxEscape(x.event_date||"일자 확인 전")} · ${x.auto_detected?"키워드 자동 탐지":fxEscape(x.source.publisher||"원문")}</small></div></div>`).join("")||`<p class="fx-v5-empty">연결된 기업 이벤트가 없습니다.</p>`;
}

function fxV5Checks(c,ctx){
 const assessment=c.assessment||{},checks=Array.isArray(assessment.checks)?assessment.checks:[],audit=c.extension_audit||{};
 const period=c.history?.filing_period,listed=checks.slice(0,4).map(x=>({label:String(x.label||"사전 점검"),pass:x.ok===true}));
 const fallback=[{label:"최신 공시·회계기간 공식 확인",pass:false},{label:"FCF·부채 항목 원문 대조",pass:false},{label:"EPS 추정치·가격 시점 검토",pass:false},{label:"거래량·가격 위험 점검",pass:false}];
 const items=listed.length?listed:fallback,passed=items.filter(x=>x.pass).length;
 const summary=ctx.data?.caseSummary;
 const validSummary=summary?.source_generated_at===ctx.data?.raw?.generated_at&&fxN(summary.counts?.attractive)!==null;
 const positive=validSummary&&Array.isArray(summary.positive_companies)&&summary.positive_companies.some(x=>String(x.symbol||x)===String(c.symbol));
 const sourceAudit=!!period&&audit.period===period&&audit.status==="compared";
 return `<div class="fx-v5-checklist">${items.map(x=>`<div class="fx-v5-checkrow"><span class="${x.pass?'yes':'todo'}">${x.pass?'✓':'!'}</span><span>${fxEscape(x.label)}</span></div>`).join("")}</div>
 <div class="fx-v5-footnote">${passed}/${items.length}개 내부 체크 · ${validSummary?(positive?"엄격 실사 후보 별도 확인":'전체 엄격 실사 승인 '+fxNum(summary.counts.attractive,0)+'건'):"엄격 실사 최신 검증 필요"} · ${sourceAudit?"일부 회계기간 대조":"원문 대조 별도"} · 매수 승인 아님</div>`;
}
function fxV5Portfolio(ctx){
 const holdings=(ctx.paper||[]).filter(x=>fxN(x.qty)!==null&&x.qty>0&&fxN(x.cost)!==null);
 if(!holdings.length)return `<div class="fx-v5-noholding"><b>모의 보유종목 없음</b><span>포트폴리오에서 수기 등록할 수 있습니다.</span></div>
 <button type="button" data-nr-screen="portfolio">모의 보유 등록·평가 보기 ›</button>`;
 const first=holdings[0],c=ctx.data?.raw?.companies?.find(x=>x.symbol===first.symbol);
 const current=fxN(c?.price),estimated=current===null?null:current*first.qty,initial=first.qty*first.cost;
 return `<div class="fx-v5-holding"><strong>${fxEscape(c?.name||first.symbol)}</strong><span>${fxN(estimated)===null?"현재 종가 미확인":fxMoney(estimated,c?.currency)} </span></div>
 <div class="fx-v5-holding-pnl">모의 장부상 손익 <strong class="${estimated===null?'':estimated>=initial?'nr-up':'nr-down'}">${estimated===null?"—":fxMoney(estimated-initial,c?.currency)}</strong></div>
 ${holdings.length>1?`<small>외 ${holdings.length-1}개 종목 · 통화별 별도 합산</small>`:""}<button type="button" data-nr-screen="portfolio">내 모의 포트폴리오 보기 ›</button>`;
}

function fxV5Side(ctx,c){
 const h=fxHelpers(),quality=fxModelQuality(ctx),overall=ctx.data?.learning?.overall||{},acc=fxN(overall.accuracy),sample=fxN(overall.samples),correct=fxN(overall.correct);
 return `<aside class="fx-v5-aside" id="fx-risk-slot">
 <section class="fx-panel fx-v5-sidecard fx-v5-sidecheck">
 <div class="fx-v5-sidehead"><h3>${h.I?.('check')||"☑"} 투자 체크리스트</h3><button data-nr-detail="${fxEscape(c?.symbol||'')}" type="button">자세히 ›</button></div>
 ${c?fxV5Checks(c,ctx):'<div class="fx-v5-empty">종목 선택 후 확인</div>'}
 </section>
 <section class="fx-panel fx-v5-sidecard fx-v5-sidenews">
 <div class="fx-v5-sidehead"><h3>${h.I?.('news')||"▤"} 주요 기업 뉴스</h3><button data-nr-screen="news" type="button">전체 보기 ›</button></div>
 <div class="fx-v5-newsfeed">${c?fxV5StockNews(ctx,c):'<p class="fx-v5-empty">뉴스 없음</p>'}</div>
 </section>
 <section class="fx-panel fx-v5-sidecard fx-v5-sidevalidation">
 <div class="fx-v5-sidehead"><h3>${h.I?.('chart')||"▣"} AI 예측 사후검증</h3><button data-nr-screen="performance" type="button">검증 ›</button></div>
 <div class="fx-v5-accuracy"><div class="fx-v5-ring" style="--percent:${acc===null?0:Math.max(0,Math.min(100,acc*100))}%"><div>${acc===null?"—":fxNum(acc*100,1)+"%"}</div></div>
 <div class="fx-v5-scorebreak"><small>독립 평가 기준 · 연구용</small><strong>${correct===null||sample===null?"평가 전":fxNum(correct,0)+" / "+fxNum(sample,0)+"건"}</strong><span>${quality.days===null?"검증 기간 미확인":`평가 ${fxNum(quality.days,0)}/${fxNum(quality.minDays,0)}일 · 상승 포착 ${quality.up===null?"—":fxNum(quality.up*100,1)+"%"}`} · 실전 미입증</span></div></div>
 </section>
 <section class="fx-panel fx-v5-sidecard fx-v5-sideportfolio">
 <div class="fx-v5-sidehead"><h3>${h.I?.('star')||"☆"} 내 모의 포트폴리오</h3><button data-nr-screen="portfolio" type="button">전체 보기 ›</button></div>
 ${fxV5Portfolio(ctx)}
 </section>
 </aside>`;
}

function fxSafeTargets(c){
 const raw=c?.targets||{};
 const value=k=>{const n=fxN(raw[k]);return n!==null&&n>0?n:null;};
 const low=value("low"),median=value("median"),high=value("high");
 const inverted=(low!==null&&median!==null&&low>median)||(median!==null&&high!==null&&median>high)||(low!==null&&high!==null&&low>high);
 if(inverted)return {low:null,median:null,high:null,valid:false,reason:"목표가 상·중·하 순서 불일치"};
 const complete=[low,median,high].every(v=>v!==null);
 return {low,median,high,valid:complete,reason:complete?"":'목표가 집계 일부 누락'};
}
function fxV5Cockpit(ctx){
 const c=fxChosen(ctx),h=fxHelpers();
 if(!c)return `<section class="fx-panel fx-v5-cockpit"><div class="fx-chart-empty">조건에 맞는 기업이 없습니다. 시장·신호 필터를 변경해 주세요.</div></section>`;
 const f=c.forecasts||{},a=c.assessment||{},t=fxSafeTargets(c),b=c.balance||{},tech=c.technical||{},history=c.history||{},first=ctx.data?.charts?.series?.[c.symbol];
 const delta=h.change?.(c),market=window.RadarMarkets?.label?.(c)||c.market;
 const focus=fxV5Facts(c);
 const inputs=[
  ["낙관 상단",t.high,"bull"],["중앙 목표",t.median,"base"],["비관 하단",t.low,"bear"]
 ];
 const extras=fxN(c.price)?`저장 종가 대비 상단 ${fxN(t.high)===null?"—":fxPct((t.high/c.price-1)*100)}`:"목표가 비교 시점 확인";
 const lastChart=h.chartFor?.(c.symbol)||first,volume=lastChart?.bars?.at(-1)?.volume;
 const volumeAligned=lastChart?.bars?.at(-1)?.date===c.price_session&&fxN(volume)!==null;
 return `<section class="fx-panel fx-v5-cockpit" aria-label="선택 기업 종합 분석">
 <div class="fx-v5-stockhead">
  <div class="fx-v5-stocktitle"><small>${fxEscape(market||"시장 확인 전")} · ${fxEscape(c.sector||"업종 확인 전")}</small><div><h2>${fxEscape(c.name)}</h2><span>${fxEscape(c.symbol)}</span><button type="button" data-nr-star="${fxEscape(c.symbol)}" aria-label="관심 종목 저장" class="fx-v5-star ${(ctx.favorites||[]).includes(c.symbol)?'on':''}">${(ctx.favorites||[]).includes(c.symbol)?'★':'☆'}</button></div></div>
  <div class="fx-v5-quote"><strong>${fxMoney(c.price,c.currency)}</strong><b class="${h.tone?.(delta)||''}">${fxPct(delta)}</b></div>
  <div class="fx-v5-volume"><span>기준 거래량</span><strong>${volumeAligned?fxNum(volume,0)+"주":"동일 시점 미수집"}</strong><small>종가 ${fxEscape(c.price_session||"기준일 미확인")}</small></div>
 </div>
 <div class="fx-v5-toptrio">
   <div class="fx-v5-chart"><div class="fx-v5-subhead"><h3>${h.I?.('chart')||"↗"} 실제 주가 흐름</h3><div class="fx-periods">${[["1W","1주"],["1M","1개월"],["3M","3개월"],["6M","6개월"]].map(([key,label])=>`<button type="button" data-fx-period="${key}" class="${fxLocal.period===key?'active':''}">${label}</button>`).join("")}</div></div><div class="fx-v5-chartarea">${fxChart(c)}</div></div>
   <div class="fx-v5-ai"><div class="fx-v5-subhead"><h3>AI 방향 분석</h3><span class="fx-v5-ai-tag">연구용</span></div>${fxBars(c,ctx)}<div class="fx-v5-ai-disclaimer">${fxEscape(fxModelQuality(ctx).status)} · 모델 분류≠매수 성공률</div></div>
   <div class="fx-v5-targets"><div class="fx-v5-subhead"><h3>가격 시나리오</h3><button type="button" data-nr-screen="scenario">비교 ›</button></div>
    <div class="fx-v5-targetlist">${inputs.map(([title,n,cls])=>`<div class="fx-v5-targetrow ${cls}"><small>${title}</small><strong>${fxMoney(n,c.currency)}</strong><span>${fxN(n)===null||fxN(c.price)===null||!c.price?"목표 없음":fxPct((n/c.price-1)*100)}</span></div>`).join("")}</div>
    <p>${fxEscape(t.reason||extras)} · 실현확률 미산출</p>
   </div>
 </div>
 <div class="fx-v5-middle">
  <section class="fx-v5-bull"><div class="fx-v5-subhead"><h3>투자 근거 · 긍정 요인</h3></div>${fxV5FocusItems(c,"bull")}</section>
  <section class="fx-v5-bear"><div class="fx-v5-subhead"><h3>투자 위험 · 확인 사항</h3></div>${fxV5FocusItems(c,"bear")}</section>
  <section class="fx-v5-metrics"><div class="fx-v5-subhead"><h3>기업 핵심 지표</h3></div><div class="fx-v5-metricgrid">${focus.slice(0,4).map(([title,value])=>`<div><small>${fxEscape(title)}</small><b>${fxEscape(value)}</b></div>`).join("")}</div></section>
 </div>
 <div class="fx-v5-bottom">
   <section><div class="fx-v5-subhead"><h3>실적 · 성장 점검</h3></div><div class="fx-v5-bottom-facts">
     <div><small>매출</small><strong>${fxAmount(history.revenue,c.currency)}</strong></div>
     <div><small>EPS 전망 수정</small><strong class="${fxN(f.eps_revision30_pct)===null?'':f.eps_revision30_pct>=0?'nr-up':'nr-down'}">${fxPct(f.eps_revision30_pct)}</strong></div>
     <div><small>다음 FY EPS 성장</small><strong>${fxPct(f.eps_growth_next_fy_pct)}</strong></div></div>
     <small class="fx-v5-datanote">회계기간 ${fxEscape(history.filing_period||"확인 전")} · 결산기 비교</small>
   </section>
   <section><div class="fx-v5-subhead"><h3>재무 안정성 · 밸류</h3></div><div class="fx-v5-bottom-facts"><div><small>FCF</small><strong>${fxAmount(history.fcf,c.currency)}</strong></div><div><small>순차입금/EBITDA</small><strong>${fxN(b.net_debt_ebitda)===null?"—":fxNum(b.net_debt_ebitda,2)+"배"}</strong></div><div><small>예상 PER</small><strong>${fxN(f.next_fy_pe)===null?"—":fxNum(f.next_fy_pe,1)+"배"}</strong></div></div><small class="fx-v5-datanote">출처 및 최신 기간은 상세 분석에서 확인</small></section>
   <section><div class="fx-v5-subhead"><h3>수급 대신 거래량 정보</h3></div><div class="fx-v5-bottom-facts">
    <div><small>20일 거래량 배수</small><strong>${fxN(tech.volume_ratio)===null?"—":fxNum(tech.volume_ratio,2)+"배"}</strong></div>
    <div><small>시장 대비 20일</small><strong>${fxN(tech.relative20_pp)===null?"—":fxPct(tech.relative20_pp)+"p"}</strong></div>
    <div><small>직전 20일 고점</small><strong>${fxMoney(tech.prior_high20,c.currency)}</strong></div>
   </div><small class="fx-v5-datanote">외국인·기관 순매수: 데이터 미연결</small></section>
 </div>
 <div class="fx-v5-actions"><button class="fx-v5-strong" data-nr-detail="${fxEscape(c.symbol)}" type="button">⌕ 심층 분석 · 재무·공시·위험</button><button data-nr-screen="scenario" type="button">↗ 시나리오 비교</button><button data-nr-screen="performance" type="button">✓ 예측 검증</button><button data-nr-screen="portfolio" type="button">☆ 관심·모의투자</button></div>
 </section>`;
}

function fxV5Sentiment(ctx){
 const korea=fxLocal.sentimentMarket==="kr";
 const us=ctx.data?.sentiment||{},kr=ctx.data?.koreaSentiment||{};
 const time=String(kr.date||"");
 const validKorea=kr.market==="kr"&&/^\d{4}-\d{2}-\d{2}$/.test(time)&&Number.isFinite(Date.parse(time+"T00:00:00Z"))&&fxN(kr.kospi?.index)!==null&&kr.kospi.index>=0&&kr.kospi.index<=100;
 const usScore=fxN(us.headline?.score),usTime=us.source_timestamp||us.headline?.timestamp;
 const validUS=us.market==="us"&&usScore!==null&&usScore>=0&&usScore<=100&&Number.isFinite(Date.parse(usTime||""));
 const valid=korea?validKorea:validUS;
 const score=korea?(validKorea?kr.kospi.index:null):(validUS?usScore:null);
 const label=valid?(score<25?"극단적 공포":score<45?"공포":score<55?"중립":score<75?"탐욕":"극단적 탐욕"):"지표 확인 전";
 const percent=score===null?0:Math.max(0,Math.min(100,score)),color=percent<45?"#e17c65":percent<55?"#d5b15c":"#32a981";
 const sourceDate=korea?time:(validUS?new Date(usTime).toLocaleDateString("ko-KR",{timeZone:"Asia/Seoul",month:"2-digit",day:"2-digit"}):"");
 const formattedDate=korea?time.replace(/^\d{4}-(\d\d)-(\d\d)$/,"$1.$2"):sourceDate;
 const kosdaq=fxN(kr.kosdaq?.index);
 const sub=valid?(korea?`코스피 · ${label}`:label):"데이터 미확인";
 const secondary=korea&&validKorea&&kosdaq!==null?`코스닥 ${fxNum(kosdaq,1)} · ${fxEscape(kr.kosdaq?.label||"지표")}`:"";
 const sourceLabel=korea?"출처: 한국 공포탐욕지수":"CNN Fear & Greed";
 const sourceHref=korea?"https://www.koreafeargreed.com":"https://www.cnn.com/markets/fear-and-greed";
 const next=korea?"미국 CNN 공포·탐욕 보기":"한국 코스피 공포·탐욕 보기";
 return `<section class="fx-v5-sentiment ${korea?"is-korea":"is-us"}" aria-label="${korea?"한국 코스피":"미국 CNN"} 공포·탐욕 지수" title="${korea?"한국 코스피·코스닥 기반 민간 산출 지수. CNN과 산출 방식이 다릅니다.":"미국 CNN 공포·탐욕 지수. 한국 시장 심리를 나타내지 않습니다."}">
  <div class="fx-v5-sentiment-copy"><div class="fx-v5-sentiment-title"><strong>${korea?"한국 공포·탐욕":"미국 공포·탐욕"}</strong>
  <button type="button" data-fx-sentiment-next aria-label="${next}" title="${next}">›</button></div>
  <small class="fx-v5-sentiment-reading">${fxEscape(sub)}</small></div>
  <div class="fx-v5-sentiment-meter" role="img" aria-label="${valid?(korea?"한국 코스피":"미국 CNN")+" 공포·탐욕 "+fxNum(score,1)+"점":"지수 데이터 확인 전"}"
    style="--sentiment:${percent}%;--sentiment-color:${color}"><span>${valid?fxNum(score,korea?1:0):"—"}</span></div>
  <small class="fx-v5-sentiment-date"><a href="${sourceHref}" target="_blank" rel="noopener noreferrer" title="${sourceLabel}">${sourceLabel} ↗</a>
    <span>${valid?fxEscape(formattedDate)+" 장 마감":"기준일 확인 전"}</span>
    ${secondary?`<span title="한국 코스닥 공포·탐욕 지수">${secondary}</span>`:""}
  </small>
 </section>`;
}
function fxHome(ctx){
 const h=fxHelpers(),c=fxChosen(ctx),connected=!!(ctx.data?.toss?.enabled&&ctx.data.toss.api_base);
 return `<div class="fx-v5-home">
  <section class="fx-v5-marketline"><div class="fx-v5-markettitle"><h2>시장 현황</h2><p>저장된 최근 완료 지수</p></div><div class="fx-v5-markets nr-market-grid">${h.indices?.()||""}</div>${fxV5Sentiment(ctx)}</section>
  <div class="fx-v5-main">${fxStockPanel(ctx,false)}
   <div class="fx-v5-central" id="fx-focus-slot">${fxV5Cockpit(ctx)}</div>${fxV5Side(ctx,c)}
  </div>
  </div>`;
}
function fxStockPage(ctx){
 const pool=fxUniverse(ctx);
 return `<div class="fx-intro"><div><h2>AI 종목 신호</h2><p>${pool.length}개 검색 결과 · 가격 방향 연구 분포이며 매수 추천이 아닙니다.</p></div><span class="fx-stamp">실시간 호가 아님</span></div><div class="fx-page-grid">${fxStockPanel(ctx,true)}<div class="fx-focus-slot" id="fx-focus-slot">${fxFocus(ctx)}</div></div>${fxSteps(ctx)}`;
}

function fxAmount(v,c){
 if(fxN(v)===null)return "—";
 const n=Math.abs(v);
 if(c==="KRW")return n>=1e12?fxNum(v/1e12,2)+"조원":n>=1e8?fxNum(v/1e8,1)+"억원":fxNum(v,0)+"원";
 if(c==="USD")return n>=1e9?fxNum(v/1e9,2)+"B USD":n>=1e6?fxNum(v/1e6,2)+"M USD":fxMoney(v,c);
 return fxMoney(v,c);
}

function fxSafeHref(v){
 try{const u=new URL(String(v));return u.protocol==="https:"?u.href:""}catch{return""}
}

function fxSourceLinks(c){
 const sources=c?.sources||{};
 const opts=[["공식 공시·IR",sources.official],["가격·거래량",sources.history],["EPS·목표가",sources.estimates],["현금흐름",sources.cashflow],["재무상태",sources.balance]];
 const active=opts.filter(([,href])=>fxSafeHref(href));
 return `<div class="fx-d-source-links">${active.map(([label,href])=>`<a href="${fxEscape(fxSafeHref(href))}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`).join("")||'<span>공식 원문 연결이 확인되지 않았습니다.</span>'}</div>`;
}

function fxFact(label,value,note){
 return `<div class="fx-d-fact"><span>${fxEscape(label)}</span><strong>${fxEscape(value)}</strong>${note?`<small>${fxEscape(note)}</small>`:""}</div>`;
}

function fxNewsFor(ctx,c){
 const key=String(c?.symbol||"").replace(/\.(KS|KQ)$/,"");
 const group=(ctx.data?.events?.companies||[]).find(x=>String(x.symbol||"").replace(/\.(KS|KQ)$/,"")===key);
 const items=(group?.events||[]).filter(x=>x.sources?.some(a=>fxSafeHref(a.url))).sort((a,b)=>String(b.event_date||"").localeCompare(String(a.event_date||""))).slice(0,3);
 return items.length?items.map((entry,i)=>{
  const source=entry.sources.find(x=>fxSafeHref(x.url));
  return `<div class="fx-d-news-row"><b>${i+1}</b><div><a href="${fxEscape(fxSafeHref(source.url))}" target="_blank" rel="noopener noreferrer">${fxEscape(entry.title||"제목 확인 필요")}</a><small>${fxEscape(entry.event_date||"날짜 미확인")} · ${fxEscape(source.publisher||"원문")} ${entry.auto_detected?"· 자동 탐지":""}</small></div></div>`;
 }).join(""):'<p class="fx-d-empty">해당 기업의 확인 가능한 이벤트가 없습니다. 공식 공시에서 추가 확인이 필요합니다.</p>';
}
function fxDetail(ctx){
 const c=ctx.data?.raw?.companies?.find(r=>String(r.symbol)===String(ctx.selected));
 if(!c)return `<div class="fx-empty-state">기업을 먼저 선택해 주세요.</div>`;
 const f=c.forecasts||{},h=c.history||{},balance=c.balance||{},tech=c.technical||{},a=c.assessment||{},short=c.short||{};
 const stateNames={ready:"제공처 기준 조건 충족",verify:"공식 대조 필요",price:"가격 조건 대기",risk:"위험 우선 확인",data:"자료 보강 필요"};
 const state=stateNames[a.state]||"종합 실사 검토 전";
 const downside=Array.isArray(a.risks)?a.risks:[],missing=Array.isArray(a.missing)?a.missing:[];
 const asText=x=>typeof x==="string"?x:x?.text||x?.reason||x?.label||"";
 const audit=c.extension_audit||{},auditFields=Array.isArray(audit.fields)?audit.fields:[],auditPeriodMatches=!!(h.filing_period&&audit.period&&h.filing_period===audit.period);
 const auditOk=auditPeriodMatches&&audit.status==="compared"?auditFields.filter(x=>x.accepted===true).length:null;
 const checks=Array.isArray(a.checks)?a.checks.slice(0,4):[];
 const warnings=[...downside.map(asText),...missing.map(asText)].filter(Boolean).slice(0,4);
 const disclaimer=ctx.data?.raw?.generated_at?"자료 수집: "+fxEscape(fxHelpers().T?.(ctx.data.raw.generated_at)||"시간 확인 중"):"저장 데이터 수집 시각 확인 전";
 const priceCondition=a.price_condition||{};
 return `<div class="fx-detail-v4">
  <div class="fx-intro fx-detail-intro"><div><h2>${fxEscape(c.name)} · 상세 분석 통합</h2><p>${fxEscape(c.symbol)} · ${fxEscape(c.sector||"업종 확인 전")} · 가격 · 실적 · 현금흐름 · 위험 · 뉴스까지 한 화면에서 확인</p></div><span class="fx-stamp">${disclaimer}</span></div>
  <div class="fx-detail-content">
   <div class="fx-detail-upper">
    <div class="fx-detail-primary">${fxFocus(ctx)}</div>
    <section class="fx-panel fx-decision-panel"><div class="fx-panel-heading"><h3>투자 판단 현황</h3><span class="fx-d-status">${fxEscape(state)}</span></div>
     <div class="fx-decision-company"><span>장기 관점</span><strong>${fxEscape(a.next_action||"공식 실사 및 가격 조건 확인 필요")}</strong></div>
     <div class="fx-d-mini-grid">
      ${fxFact("검토 상한가",fxMoney(priceCondition.ceiling,c.currency),"독립 적정가치 아님")}
      ${fxFact("단기 방향",fxEscape(short.label||"단기 자료 없음"),"5~20거래일 연구")}
      ${fxFact("가격 조건",priceCondition.price_condition_usable===false||a.price_condition_usable===false?"사용 보류":fxN(priceCondition.move_pct)===null?"미산출":fxPct(priceCondition.move_pct),"원문 대조 별도")}
      ${fxFact("분석 우선점수",fxN(c.priority?.display_score??c.priority?.score)===null?"—":fxNum(c.priority?.display_score??c.priority?.score,0)+" / 100","투자 성공 확률 아님")}
     </div><div class="fx-d-notice">AI 연구 예측과 종합 실사 판단은 서로 다른 근거입니다. 과거 공식 대조 ${auditOk===null?"기간·원문 미확인":auditOk+" / "+auditFields.length+"개 허용범위 대조"}</div>
    </section>
   </div>
   <div class="fx-detail-mid">
    <section class="fx-panel fx-d-metrics"><div class="fx-panel-heading"><h3>가치평가 · 가격 부담</h3><span>애널리스트 집계</span></div>
      <div class="fx-d-facts">
       ${fxFact("다음 FY 예상 PER",fxN(f.next_fy_pe)===null?"—":fxNum(f.next_fy_pe,2)+"배","완료 종가 / 예상 EPS")}
       ${fxFact("목표가 중앙값",fxMoney(fxSafeTargets(c).median,c.currency),"적정가치 확정값 아님")}
       ${fxFact("순차입금 / EBITDA",fxN(balance.net_debt_ebitda)===null?"—":fxNum(balance.net_debt_ebitda,2)+"배","기준 "+(balance.asof||"미확인"))}
       ${fxFact("단기 20일 전고점",fxMoney(tech.prior_high20,c.currency),"지지·저항 추정값")}
      </div></section>
    <section class="fx-panel fx-d-metrics"><div class="fx-panel-heading"><h3>EPS 전망 · 수정 추이</h3><span>회계연도 구분</span></div>
      <div class="fx-d-facts">
       ${fxFact("다음 FY 예상 EPS",fxMoney(f.next_fy?.avg,c.currency),fxN(f.analysts)===null?"기관 수 미확인":fxNum(f.analysts,0)+"개 집계")}
       ${fxFact("EPS 30일 수정",fxPct(f.eps_revision30_pct),"동일 회계연도 비교")}
       ${fxFact("다음 FY 예상 EPS 성장",fxPct(f.eps_growth_next_fy_pct),"추정치 간 비교")}
       ${fxFact("20일 평균 거래량 대비",fxN(tech.volume_ratio)===null?"—":fxNum(tech.volume_ratio,2)+"배","저장 거래량 지표")}
      </div></section>
    <section class="fx-panel fx-d-metrics"><div class="fx-panel-heading"><h3>실적 · 현금흐름</h3><span>${fxEscape(h.filing_period||"회계기간 확인 전")}</span></div>
      <div class="fx-d-facts">
       ${fxFact("매출",fxAmount(h.revenue,c.currency),h.basis||"보고 기간 확인")}
       ${fxFact("영업이익",fxAmount(h.operating_income,c.currency))}
       ${fxFact("당기순이익",fxAmount(h.net_income,c.currency))}
       ${fxFact("잉여현금흐름 FCF",fxAmount(h.fcf,c.currency),"회계기간/투자지출 대조")}
      </div></section>
   </div>
   <div class="fx-detail-lower">
     <section class="fx-panel fx-d-summary"><div class="fx-panel-heading"><h3>투자 근거 · 단기/장기</h3></div>
      <p class="fx-d-text">${fxEscape(c.business_summary||c.business_description||c.profile?.business||"사업 요약을 확인할 수 없어 공식 IR 확인이 필요합니다.")}</p>
      <div class="fx-d-points">${[a.next_action,...(short.reasons||[]).slice(0,1)].filter(Boolean).map(x=>`<span>✓ ${fxEscape(asText(x))}</span>`).join("")||'<span>확정된 투자 근거는 원문을 확인해야 합니다.</span>'}</div>
     </section>
     <section class="fx-panel fx-d-summary"><div class="fx-panel-heading"><h3>리스크 · 무효화 조건</h3></div>
      <div class="fx-d-points">${checks.map(x=>`<span>${x.ok===true?"✓":"○"} ${fxEscape(x.label||"검증 내용 확인")}: ${x.ok===true?"입력 기준 통과":"확인 필요"}</span>`).join("")}${warnings.map(x=>`<span>! ${fxEscape(x)}</span>`).join("")||'<span>현재 실사·문서·금리 리스크를 별도 확인해야 합니다.</span>'}</div>
     </section>
     <section class="fx-panel fx-d-summary"><div class="fx-panel-heading"><h3>기업 뉴스 · 원문</h3><span>자동탐지 원문 재확인</span></div>
       <div class="fx-d-news">${fxNewsFor(ctx,c)}</div>${fxSourceLinks(c)}
     </section>
   </div>
  </div>${fxSteps(ctx)}</div>`;
}
function fxScenarioPlot(c){
 const t=fxSafeTargets(c),h=fxHelpers(),series=h.pointData?.([String(c.symbol)],"3M"),vals=series?.series?.[0]?.prices||[];
 const current=fxN(c.price),refs=[["상단 목표",t.high,"#d85876"],["중앙 목표",t.median,"#377bd1"],["하단 목표",t.low,"#28a074"]].filter(x=>fxN(x[1])!==null);
 if(current===null||refs.length===0)return '<div class="fx-chart-empty">저장 종가와 목표가를 비교할 데이터가 없습니다.</div>';
 const prices=[current,...refs.map(x=>x[1]),...vals],low=Math.min(...prices),high=Math.max(...prices),pad=(high-low||Math.abs(high)*.015||1)*.14;
 const W=800,H=260,L=69,R=67,T=25,B=35,y=n=>T+(high+pad-n)*(H-T-B)/(high-low+2*pad);
 const pivot=414,right=738;const grid=[0,.25,.5,.75,1].map(k=>{const v=low+(high-low)*k;return `<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="#e7eff9" stroke-dasharray="4 5"/><text x="${L-8}" y="${y(v)+4}" text-anchor="end" fill="#91a5bb" font-size="12">${fxNum(v,0)}</text>`}).join("");
 const plot=vals.length>=2?`<polyline points="${vals.map((v,i)=>`${L+i*(pivot-L)/Math.max(vals.length-1,1)},${y(v)}`).join(" ")}" stroke="#447ecf" stroke-width="3" fill="none" stroke-linejoin="round"/><circle cx="${pivot}" cy="${y(vals.at(-1))}" r="5" fill="#3c78ca" stroke="white" stroke-width="2"/>`: `<text x="170" y="145" fill="#899bb6" font-size="13">이전 일봉 데이터 확인 전</text>`;
 const horizontals=refs.map(([label,v,color],i)=>`<line x1="${pivot+45}" x2="${right}" y1="${y(v)}" y2="${y(v)}" stroke="${color}" stroke-width="3" stroke-dasharray="9 5"/><rect x="${right-3}" y="${y(v)-13}" width="58" height="26" rx="7" fill="${color}"/><text x="${right+26}" y="${y(v)+4}" fill="white" text-anchor="middle" font-size="11.5" font-weight="750">${fxNum(v,0)}</text>`).join("");
 const linkLine=`<line x1="${pivot}" x2="${pivot+36}" y1="${y(current)}" y2="${y(current)}" stroke="#889cb6" stroke-width="2" stroke-dasharray="6 4"/>`;
 return `<svg class="fx-scenario-plot" viewBox="0 0 ${W} ${H}" role="img" aria-label="${fxEscape(c.name)} 실제 과거 종가와 3개 저장 목표가 수준을 비교하는 차트. 날짜별 미래 경로는 예측하지 않았습니다.">
 <rect x="${pivot+23}" y="${T-7}" width="${W-R-pivot-15}" height="${H-T-B+13}" rx="12" fill="#f6f9ff"/>
 ${grid}<text x="175" y="17" text-anchor="middle" font-size="12" fill="#526d93" font-weight="800">실제 과거 종가</text>
 <text x="594" y="17" text-anchor="middle" font-size="12" fill="#526d93" font-weight="800">상단·중앙·하단 목표 수준 (미래 경로 아님)</text>
 <line x1="${pivot+17}" x2="${pivot+17}" y1="${T-8}" y2="${H-B+8}" stroke="#cddbf0" stroke-width="1" stroke-dasharray="4 4"/>
 ${plot}${linkLine}${horizontals}
 <circle cx="${pivot}" cy="${y(current)}" r="5" fill="#213e64" stroke="#fff" stroke-width="2.5"/>
 <text x="${pivot-4}" y="${Math.max(T+9,y(current)-11)}" text-anchor="end" font-size="12" font-weight="800" fill="#234467">${fxNum(current,0)}</text>
 <text x="${L}" y="${H-8}" font-size="11" fill="#8aa0b9">${fxEscape(series?.dates?.[0]||"과거")}</text>
 <text x="${pivot}" y="${H-8}" text-anchor="end" font-size="11" fill="#8aa0b9">${fxEscape(c.price_session||"현재 종가")}</text>
 <text x="${pivot+47}" y="${H-8}" font-size="11" fill="#8aa0b9">목표가 집계 (날짜별 예측 아님)</text>
 </svg>`;
}
function fxScenario(ctx){
 const c=ctx.data?.raw?.companies?.find(r=>String(r.symbol)===String(ctx.selected));
 if(!c)return '<section class="fx-empty-state">기업을 먼저 선택해 주세요.</section>';
 const t=fxSafeTargets(c),f=c.forecasts||{},a=c.assessment||{},tech=c.technical||{},current=fxN(c.price);
 const order=[["낙관 상단",t.high,"up","상단"],["중앙 기준",t.median,"base","중앙"],["비관 하단",t.low,"down","하단"]];
 const conditions=[
  ["EPS 추정치 상향·전고점 돌파 확인",fxN(tech.prior_high20)===null?"실적 발표·공시 재검증":`20일 전고점 ${fxMoney(tech.prior_high20,c.currency)} 재확인`],
  ["EPS·목표가 집계 유지 여부 확인",fxN(f.eps_revision30_pct)===null?"동일 회계연도 EPS 정합성 확인":`최근 EPS 수정 ${fxPct(f.eps_revision30_pct)}`],
  ["사업·금리·수요 위험과 지지선 확인",fxN(tech.support10)===null?"주요 하방 무효화 조건 재검증":`과거 10일 저점 ${fxMoney(tech.support10,c.currency)} 확인`]
 ];
 const fig=order.map(([title,v,cl,alt],i)=>`<section class="fx-scenario-option ${cl}">
 <div class="fx-scenario-option-heading"><span>${title}</span><small>${fxN(v)===null?"집계 없음":fxN(current)===null||current===0?"가격 차이 계산 불가":fxPct((v/current-1)*100)+" · 저장 종가 대비"}</small></div>
 <strong>${fxMoney(v,c.currency)}</strong><p>${fxEscape(conditions[i][0])}</p><small>${fxEscape(conditions[i][1])}</small>
 </section>`).join("");
 const up=fxN(t.high)!==null&&current? (t.high/current-1)*100:null,down=fxN(t.low)!==null&&current?(t.low/current-1)*100:null;
 const earliest=ctx.data?.raw?.generated_at?fxHelpers().T?.(ctx.data.raw.generated_at):"기준 시각 확인 필요";
 const risks=(a.risks||[]).slice(0,2).map(x=>fxEscape(typeof x==="string"?x:x?.text||x?.label||"")).filter(Boolean);
 return `<div class="fx-scenario-v4">
 <div class="fx-intro"><div><h2>${fxEscape(c.name)} · 시나리오 한눈에</h2><p>저장된 목표가 수준과 AI 방향 연구를 따로 비교합니다. 투자 전략의 조건은 최신 공시로 재확인해야 합니다.</p></div><span class="fx-stamp">${fxEscape(c.price_session||"기준일 미확인")} 종가 ${fxMoney(c.price,c.currency)}</span></div>
 <div class="fx-scenario-main">
  <section class="fx-panel fx-scenario-chart-panel"><div class="fx-panel-heading"><div><h3>실제 종가와 3가지 목표가 구간</h3><p>${fxEscape(t.reason||"애널리스트 집계 가격을 수준으로만 표시합니다.")} · 미래 가격 경로 아님</p></div><span class="fx-mini-chip">미래 경로 예측 아님 · 목표가만 비교</span></div>
    ${fxScenarioPlot(c)}<div class="fx-scenario-legend"><span><i style="background:#447ecf"></i>실제 일별 종가</span><span><i style="background:#d85876"></i>낙관 상단</span><span><i style="background:#377bd1"></i>중앙 기준</span><span><i style="background:#28a074"></i>비관 하단</span></div>
  </section>
  <section class="fx-panel fx-scenario-ai-panel"><div class="fx-panel-heading"><h3>AI 연구 방향 분포</h3><span class="fx-mini-chip">예측 확률 ≠ 목표가 확률</span></div><div class="fx-ai-card">${fxBars(c,ctx)}</div>
   <p class="fx-mini-notice">분류 확률은 각 목표가가 실현될 가능성을 나타내지 않습니다.</p>
  </section>
 </div>
 <div class="fx-scenario-options">${fig}</div>
 <div class="fx-scenario-footer">
  <section class="fx-panel fx-scenario-conditions"><div class="fx-panel-heading"><h3>판단을 바꾸는 조건</h3></div>
   ${[a.next_action,...risks].filter(Boolean).slice(0,3).map(x=>`<p>• ${fxEscape(x)}</p>`).join("")||'<p>정기 공시·EPS 변경·거래량 조건을 차례로 확인하세요.</p>'}
  </section>
  <section class="fx-panel fx-scenario-difference"><div class="fx-panel-heading"><h3>상승 여력 / 하락 위험</h3></div><div class="fx-scen-difference-grid">
   <div><small>상단 목표가 대비</small><strong class="fx-up">${up===null?"—":fxPct(up)}</strong></div>
   <div><small>하단 목표가 대비</small><strong class="fx-down">${down===null?"—":fxPct(down)}</strong></div></div>
  </section>
  <section class="fx-panel fx-scenario-next"><div class="fx-panel-heading"><h3>다음 확인 단계</h3></div>
    <p>저장 종가·목표가를 최신 원문과 비교한 다음 AI 사후검증을 확인하세요.</p>
    <div class="fx-scen-buttons"><button type="button" data-nr-screen="stockdetail">종목 심층 분석</button><button type="button" data-nr-screen="performance">예측 검증</button></div>
  </section>
 </div>
 ${fxSteps(ctx)}
 </div>`;
}
function fxPerformance(ctx){
 const h=fxHelpers(),o=ctx.data?.learning?.overall||{},rec=o.recall||{},quality=fxModelQuality(ctx);
 const facts=[["사후 방향 일치율",fxN(o.accuracy)===null?"—":fxNum(o.accuracy*100,1)+"%"],["독립 평가 일치 / 표본",fxNum(o.correct,0)+" / "+fxNum(o.samples,0)],["실제 상승 포착률",fxN(rec.up)===null?"—":fxNum(rec.up*100,1)+"%"],["실제 하락 포착률",fxN(rec.down)===null?"—":fxNum(rec.down*100,1)+"%"]];
 const utility=ctx.data?.autopilot?.timing_utility?.status, proven=utility==="proven";
 return `<div class="fx-intro"><div><h2>AI 예측 검증</h2><p>실제 결과와 비교하되, 적중률과 매매 수익률을 구분합니다.</p></div><span class="fx-stamp">자료 ${fxEscape(h.T?.(ctx.data?.learning?.generated_at)||"확인 전")}</span></div>
 <div class="nr-performance-grid">${facts.map(([label,n])=>`<section class="nr-panel"><small>${label}</small><strong>${n}</strong></section>`).join("")}</div>
 <div class="fx-validation-grid">${fxOutcomes(ctx)}<section class="nr-panel fx-validation-aside">${h.qualityHTML?.()||""}<div class="nr-validation-note"><b>검증 판정: ${fxEscape(quality.status)}</b><p>독립 평가 ${quality.n===null?"—":fxNum(quality.n,0)}/${fxNum(quality.minN,0)}건 · ${quality.days===null?"—":fxNum(quality.days,0)}/${fxNum(quality.minDays,0)}일 · 상승 포착 ${quality.up===null?"—":fxNum(quality.up*100,1)+"%"}</p><p>Brier 개선 ${quality.brier===null?"—":fxNum(quality.brier,4)} / 최소 ${fxNum(quality.threshold,3)} · ${quality.hasBrier?"기준 충족":"기준 미달"} · 매매 타이밍·수익성 미입증</p><p>95% Wilson 구간: ${fxN(o.wilson_95_interval?.[0])===null?"—":fxNum(o.wilson_95_interval[0]*100,1)+"~"+fxNum(o.wilson_95_interval[1]*100,1)+"%"} (평가 관측 독립 가정) · 고확률 70% 이상 표본 ${fxNum(o.high_confidence?.samples,0)}건</p><p>정확도 감사: ${quality.aligned?"현재 예측·검증 자료의 시점 일치 확인":"자료 시점 불일치 또는 감사 대기 · 승격 보류"} · AI 확률은 매수 성공률이 아닙니다.</p></div><button data-nr-forecast class="nr-action">전체 예측 성적표</button></section></div>${fxSteps(ctx)}`;
}
function fxOutcomes(ctx){
 const h=fxHelpers(),input=Array.isArray(ctx.data?.outcomes)?ctx.data.outcomes:[],seen=new Set();
 const eligible=input.filter(r=>{
  if(r.status!=="observed"||r.public_before_target_verified!==true)return false;
  const id=String(r.id||[r.symbol,r.mode,r.issued_at,r.target?.start].join("|"));
  if(seen.has(id))return false;seen.add(id);return true;
 });
 const visible=eligible.slice().sort((a,b)=>Date.parse(b.evaluated_at||0)-Date.parse(a.evaluated_at||0)).slice(0,8);
 const independent=fxN(ctx.data?.learning?.evaluation_counts?.eligible_scored)??fxN(ctx.data?.learning?.overall?.samples);
 const dir={up:"상승",down:"하락",flat:"횡보"};
 return `<section class="nr-panel fx-audit-table"><div class="nr-head"><h3>최근 관측 기록</h3><span class="nr-sub">관측 ${eligible.length}건 중 최근 ${visible.length}건</span></div>
 <div class="fx-table-clip"><table class="fx-audit"><thead><tr><th>관측 시각</th><th>종목</th><th>예측</th><th>실제</th><th>일치 여부</th></tr></thead><tbody>
 ${visible.length?visible.map(r=>`<tr><td>${fxEscape(h.T?.(r.evaluated_at)||"시각 미확인")}</td><td>${fxEscape(r.symbol||"—")}</td><td>${fxEscape(dir[r.predicted]||r.predicted||"—")}</td><td>${fxEscape(dir[r.actual]||r.actual||"—")}</td><td><span class="fx-mark ${r.correct===true?'yes':'no'}">${r.correct===true?'일치':'불일치'}</span></td></tr>`).join(""):'<tr><td colspan="5">발행·관측이 확인된 기록이 없습니다.</td></tr>'}
 </tbody></table></div>
 <p class="fx-table-hint">방향 판정: 대상 구간 시작 시가 → 종료 종가. 예측마다 고정된 판정 폭으로 상승·횡보·하락을 분류하며 전일 종가 대비 등락과 다릅니다.<br>이 표는 원시 관측 기록이고, 위의 정확도는 ${independent===null?"별도 정책으로 선별된":"중복·겹침 등을 제외한 독립 평가 "+fxNum(independent,0)+"건"} 기준입니다. 두 모수는 다를 수 있습니다. 실제 체결·수익 기록이 아닙니다.</p></section>`;
}
function fxRender(){
 const ctx=fxContext(),h=fxHelpers(),s=ctx.screen||"home";
 const body=s==="home"?fxHome(ctx):s==="stocks"?fxStockPage(ctx):s==="stockdetail"?fxDetail(ctx):s==="scenario"?fxScenario(ctx):s==="performance"?fxPerformance(ctx):s==="monitor"?h.renderMonitor?.():s==="portfolio"?h.renderPortfolio?.():s==="news"?h.renderNews?.():s==="settings"?h.renderSettings?.():fxHome(ctx);
 return `<div class="fx-root">${fxNav(ctx)}<div id="source-status" class="fx-source-status" role="status" aria-live="polite">연구용 저장 자료 · 실시간 시세 아님</div><div class="fx-stage ${s==="home"?"fx-stage-home":"fx-stage-other"}" data-screen="${fxEscape(s)}">${body||""}</div></div>`;
}
function fxHandleClick(e){
 const button=e.target.closest?.("button");if(!button)return;
 const ds=button.dataset,bridge=window.StockRadarV2Bridge;if(!bridge)return;
 if(ds.nrScreen==="home"){fxLocal.search="";fxLocal.filter="all";fxLocal.limit=36;bridge.render();return}
 if("fxSentimentNext" in ds){fxLocal.sentimentMarket=fxLocal.sentimentMarket==="us"?"kr":"us";try{localStorage.setItem("radar-sentiment-market",fxLocal.sentimentMarket)}catch{}bridge.render();return}
 if("fxRefresh" in ds){bridge.refresh();return}
 if(ds.fxPeriod){fxLocal.period=ds.fxPeriod;bridge.render();return}
 if(ds.fxFilter){fxLocal.filter=ds.fxFilter;fxLocal.limit=36;const c=fxChosen(fxContext());if(c)bridge.select(c.symbol);else bridge.render();return}
 if("fxMore" in ds){fxLocal.limit+=36;bridge.render();return}
 if(ds.fxDeep){bridge.deep(ds.fxDeep);return}
}

function fxEnsureSelectedVisible(c){
 if(!c)return;
 if(fxLocal.search&&!String(c.name+" "+c.symbol).toLowerCase().includes(fxLocal.search.trim().toLowerCase()))fxLocal.search="";
 if(fxLocal.filter==="star"&&!fxContext().favorites?.includes(c.symbol))fxLocal.filter="all";
 if(["up","down","flat","ai"].includes(fxLocal.filter)){
  const forecast=fxPrediction(c,fxContext());
  if(!forecast.active||forecast.stale||forecast.unknown||(fxLocal.filter!=="ai"&&forecast.r?.direction!==fxLocal.filter))fxLocal.filter="all";
 }
}
function fxHandleInput(e){
 if(e.target?.id!=="fx-search-input")return;
 fxLocal.search=e.target.value;
 let ctx=fxContext(),pool=fxUniverse(ctx);
 const bridge=window.StockRadarV2Bridge;
 if(pool.length&&!pool.some(c=>String(c.symbol)===String(ctx.selected)))bridge?.setSelectedSilently?.(pool[0].symbol);
 ctx=fxContext();
 const list=document.getElementById?.("fx-results"),count=document.getElementById?.("fx-result-count"),focus=document.getElementById?.("fx-focus-slot"),risk=document.getElementById?.("fx-risk-slot"),expanded=ctx.screen==="stocks",cap=expanded?fxLocal.limit:9;
 if(list)list.innerHTML=fxStockRows(ctx,expanded);
 if(focus)focus.innerHTML=ctx.screen==="home"?fxV5Cockpit(ctx):fxFocus(ctx);
 if(risk&&ctx.screen==="home"){const chosen=fxChosen(ctx);risk.outerHTML=fxV5Side(ctx,chosen)}
 else if(risk)risk.innerHTML=fxRisk(ctx);
 if(count)count.textContent=Math.min(pool.length,cap)+" / "+pool.length+"개 · AI 연구용";
}
const fxLocal={filter:'all',search:'',limit:36,period:'1M',sentimentMarket:'us'};
document.addEventListener('click',fxHandleClick);document.addEventListener('input',fxHandleInput);
window.StockRadarFlowV2={render:fxRender,pick:()=>fxChosen(fxContext()),ensureSelectedVisible:fxEnsureSelectedVisible,version:'ux-flow-20261102-v3-viewport'};
const fxBoot=()=>{try{const previous=localStorage.getItem("radar-sentiment-market");if(previous==="kr"||previous==="us")fxLocal.sentimentMarket=previous}catch{}window.StockRadarV2Bridge?.render?.()};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',fxBoot);else fxBoot();
})();