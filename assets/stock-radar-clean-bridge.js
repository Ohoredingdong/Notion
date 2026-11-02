(()=>{'use strict';
let D={},selected='005930',screen='home',market='ALL',favorites=[],busy=false,errors=[];
function E(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}

function N(v){return typeof v==="number"&&Number.isFinite(v)?v:null;}

function F(v,d=1){return N(v)===null?"—":v.toLocaleString("ko-KR",{maximumFractionDigits:d});}

function P(v){return N(v)===null?"—":(v>0?"+":"")+F(v,2)+"%";}

function money(v,c){return N(v)===null?"—":F(v,c==="KRW"?0:2)+(c==="KRW"?"원":" "+(c||""));}

function T(v){const d=new Date(v||"");return Number.isFinite(+d)?d.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit",hour12:false})+" KST":"시각 미확인";}

function tone(v){return N(v)===null?"nr-neutral":v>0?"nr-up":v<0?"nr-down":"nr-neutral";}

function I(k){const paths={home:'<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',search:'<circle cx="10" cy="10" r="6.5"/><path d="m15 15 6 6"/>',star:'<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',chart:'<path d="M4 4v16h16M7 14l4-5 4 3 5-7"/>',check:'<rect x="4" y="3" width="16" height="18" rx="3"/><path d="m8 12 3 3 5-6"/>',news:'<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 8h10M7 12h6M7 16h10"/>',settings:'<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',arrow:'<path d="m9 5 7 7-7 7"/>',plus:'<path d="M5 12h14M12 5v14"/>'};return `<svg class="nr-icon" viewBox="0 0 24 24" aria-hidden="true">${paths[k]||paths.chart}</svg>`;}

function rows(){return Array.isArray(D.raw?.companies)?D.raw.companies:[];}

function company(id){return rows().find(x=>String(x.symbol)===String(id));}

function series(id){const r=D.charts?.series?.[id];return r&&r.status!=="unavailable"&&Array.isArray(r.bars)&&r.bars.length>1?r:null;}

function change(c){const s=series(String(c?.symbol)),a=s?.bars;if(!s||!c||s.price_session!==c.price_session||!a||a.length<2||N(c.price)===null||Math.abs(a.at(-1).close-c.price)>Math.max(.01,c.price*1e-6))return null;return a.at(-2).close?(a.at(-1).close/a.at(-2).close-1)*100:null;}

function pointData(ids,period){const sets=ids.map(series);if(!sets.length||sets.some(x=>!x||!x.bars?.length))return null;const end=sets.map(x=>x.bars.at(-1).date).sort()[0],days={"1W":7,"1M":31,"3M":93,"6M":190}[period]||93;const from=new Date(Date.parse(end+"T00:00:00Z")-days*86400000).toISOString().slice(0,10);let dates=sets[0].bars.map(b=>b.date).filter(x=>x>=from&&x<=end);dates=dates.filter(x=>sets.every(s=>s.bars.some(b=>b.date===x)));if(dates.length<2)return null;const mapped=sets.map(s=>{const map=new Map(s.bars.map(b=>[b.date,b.close])),prices=dates.map(d=>map.get(d));return {symbol:s.symbol,name:s.name,currency:s.currency,prices,returns:prices.map(v=>(v/prices[0]-1)*100)}});return {dates,series:mapped,sets};}

function mini(s,r){const arr=s?.bars?.slice(-22).map(b=>b.close).filter(v=>N(v)!==null)||[];if(arr.length<2)return "";const lo=Math.min(...arr),hi=Math.max(...arr),p=arr.map((v,i)=>`${i*80/(arr.length-1)},${40-(v-lo)/(hi-lo||1)*35}`).join(" ");return `<svg class="nr-mini-chart" viewBox="0 0 80 44" aria-label="저장된 지수 추이"><polyline points="${p}" fill="none" stroke="${r<0?"#4b84d7":"#e57286"}" stroke-width="1.5"/></svg>`;}

function url(u){try{const v=new URL(u);return v.protocol==="https:"?v.href:""}catch{return"";}}

function link(u,label){const href=url(u);return href?`<a href="${E(href)}" target="_blank" rel="noopener noreferrer">${E(label)}</a>`:`<span>${E(label)} · 출처 확인 전</span>`;}

function indices(){const specs=[["^KS11","코스피","kospi"],["^KQ11","코스닥","kosdaq"],["^IXIC","나스닥","nasdaq"],["^GSPC","S&P 500","sp500"]];return specs.map(([id,name,k])=>{const s=series(id),a=s?.bars,last=a?.at(-1),prev=a?.at(-2),m=D.macro?.indicators?.[k]||{},newer=last?.date&&(!m.date||last.date>m.date),v=newer?last.close:m.value,delta=newer&&N(prev?.close)!==null&&prev.close?(last.close/prev.close-1)*100:m.change_1d_pct,day=newer?last.date:m.date;return `<article class="nr-panel nr-index"><div class="nr-head" style="margin-bottom:0"><h3>${name}</h3>${link(s?.source_url||m.source_url,"출처")}</div><div class="nr-num">${F(v,2)}</div><div class="${tone(delta)}" style="font-size:12px;font-weight:750">${P(delta)}</div>${mini(s,delta)}<div class="nr-sub" style="margin-top:8px">${E(day||"기준일 미확인")} · 저장 일봉</div></article>`}).join("")}

function caseOf(c){const k=(D.cases?.companies||[]).find(x=>String(x.symbol)===String(c.symbol));return D.cases?.source_generated_at===D.raw?.generated_at&&k?.input_price===c.price&&k?.input_price_session===c.price_session&&k?.input_forecast_eps===c.forecasts?.next_fy?.avg?k:null;}

function flowReasonLines(c){const k=caseOf(c),out=[];for(const v of k?.why||[])if(v?.text)out.push(v.text);for(const v of k?.risks||[])if(typeof v==="string")out.push(v);else if(v?.text)out.push(v.text);for(const v of k?.missing||[])if(typeof v==="string")out.push(v);if(!out.length)out.push("현재 공시·실적과 동일한 기준일의 공식 자료 대조가 필요합니다.");if(N(c.technical?.volume_ratio)!==null)out.push("20일 평균 거래량 대비 "+F(c.technical.volume_ratio,2)+"배");return [...new Set(out)].slice(0,4);}

function compactAlerts(){const items=[];for(const c of D.events?.companies||[])for(const v of c.events||[]){const source=v.sources?.[0];if(!source?.url)continue;items.push({...v,companyName:c.name,source})}items.sort((a,b)=>String(b.event_date).localeCompare(String(a.event_date)));return `<div class="nr-list-compact">${items.slice(0,4).map((v,i)=>`<article><span class="nr-list-num">${i+1}</span><div>${link(v.source.url,v.title)}<small>${E(v.companyName)} · ${E(v.event_date||"날짜 미확인")}${v.auto_detected?" · 자동 탐지":""}</small></div></article>`).join("")||'<p class="nr-sub">저장된 주요 이슈가 없습니다.</p>'}</div>`;}

function qualityHTML(){const x=D.learning?.overall||{};return `<div class="nr-head"><h3>예측 사후검증</h3><button class="nr-link" data-nr-forecast>전체 연구 성적표 ${I("arrow")}</button></div><div class="nr-quality"><strong>${F(x.correct,0)} / ${F(x.samples,0)}</strong><span>일치 / 평가 표본 · 연구용</span></div><p class="nr-small-note">실전 수익성·타이밍 유용성 미입증 · 자료 ${T(D.learning?.generated_at)}</p>`;}

function renderMonitor(){const live=!!(D.toss?.enabled&&D.toss?.api_base);const watch=rows().filter(c=>favorites.includes(c.symbol));return `<div class="nr-screen-head"><div><h2>감시 상태</h2><p>실시간 알림 스트림이 아닌, 저장된 종가로 관심 기업을 확인하는 화면입니다.</p></div></div><div class="nr-status-banner warn"><b>${live?"조회 서버 설정 있음 · 응답 확인 전":"실시간 시세 연결 전"}</b><span>실시간 조건 감시나 푸시가 구현된 것처럼 표시하지 않습니다.</span></div><div class="nr-screen-grid"><section class="nr-panel"><h3>관심 종목 · 저장 종가 기준</h3><div class="nr-monitor-list">${watch.map(c=>`<button data-nr-detail="${E(c.symbol)}"><span>${E(c.name)}<small>${E(c.symbol)}</small></span><b>${money(c.price,c.currency)}</b><em class="${tone(change(c))}">${P(change(c))}</em></button>`).join("")||'<p class="nr-sub">관심 종목을 먼저 등록해 주세요.</p>'}</div></section><section class="nr-panel"><h3>데이터 감시 안내</h3><p class="nr-sub">가격은 완료된 거래 세션 기준입니다. 알림 발송과 실시간 호가는 아직 연결되어 있지 않습니다.</p><button class="nr-action" data-nr-screen="settings">연결 상태 확인</button></section></div>`;}

function renderPortfolio(){const watch=rows().filter(c=>favorites.includes(c.symbol));return `<div class="nr-screen-head"><div><h2>포트폴리오 · 모의투자</h2><p>실계좌 연결 전에는 보유 자산과 수익률을 생성하지 않습니다.</p></div></div><div class="nr-screen-grid"><section class="nr-panel"><div class="nr-head"><h3>관심 종목 ${watch.length}개</h3></div><div class="nr-monitor-list">${watch.map(c=>`<button data-nr-detail="${E(c.symbol)}"><span>${E(c.name)}<small>${E(c.symbol)}</small></span><b>${money(c.price,c.currency)}</b></button>`).join("")||'<p class="nr-sub">종목 목록에서 별표를 눌러 관심 종목을 등록하세요.</p>'}</div></section><section class="nr-panel"><div class="nr-head"><h3>모의투자</h3><span class="nr-badge warn">실계좌 미연결</span></div><div class="nr-empty-big"><b>실제 자금을 사용하지 않고 매매 판단을 연습합니다.</b><p>실제 투자 성과와 연구 예측 결과를 혼합하지 않습니다.</p><a class="nr-action primary" href="./stock-paper-investing.html" target="_blank" rel="noopener">모의투자 열기</a></div></section></div>`;}

function renderNews(){const m=D.macro?.indicators||{},f=m.usdkrw||{},ten=m.us_10y||{},bok=m.bok_policy||{};return `<div class="nr-screen-head"><div><h2>뉴스 · 경제 브리핑</h2><p>기업 이벤트는 원문 확인이 필요한 자동 탐지 결과를 포함합니다.</p></div><a class="nr-action" href="./news-link-hub-v3.html" target="_blank" rel="noopener">뉴스 원문 허브</a></div><div class="nr-news-grid"><section class="nr-panel"><h3>공시·이벤트 탐지</h3>${compactAlerts()}</section><section class="nr-panel"><h3>경제 지표</h3><div class="nr-ops-grid"><div class="nr-op"><small>원/달러 · ${E(f.date||"—")}</small><strong>${F(f.value,2)}원</strong></div><div class="nr-op"><small>미국 10년물 · ${E(ten.date||"—")}</small><strong>${F(ten.value,2)}%</strong></div><div class="nr-op"><small>한국은행 기준금리 · ${E(bok.date||"—")}</small><strong>${F(bok.value,2)}%</strong></div></div></section></div>`;}

function renderSettings(){const alive=!!(D.toss?.enabled&&D.toss?.api_base);return `<div class="nr-screen-head"><div><h2>설정 · 데이터 연결</h2><p>새로운 UI는 기존 고급 기업 분석과 분리하여 충돌 없이 운영합니다.</p></div></div><div class="nr-screen-grid"><section class="nr-panel"><h3>운영 상태</h3><div class="nr-setting-row"><b>저장 종목</b><span>${rows().length}개</span></div><div class="nr-setting-row"><b>토스증권 실시간</b><span>${alive?"서버 설정됨 · 응답 미검증":"미연결"}</span></div><div class="nr-setting-row"><b>자동 주문</b><span>비활성</span></div><button class="nr-action" data-nr-reload>저장 자료 새로고침</button></section><section class="nr-panel"><h3>원래의 심층 재무분석</h3><p class="nr-sub">기존 V1의 전체 기업 분석 기능은 별도의 페이지로 보존했습니다.</p><a class="nr-action primary" href="./stock-value-radar-advanced.html" target="_blank" rel="noopener">심층 분석 열기</a></section></div>`;}

async function read(name){const ac=new AbortController(),t=setTimeout(()=>ac.abort(),22000);try{const r=await fetch("./"+name+"?v="+Date.now(),{cache:"no-store",signal:ac.signal});if(!r.ok)throw Error("HTTP "+r.status);return await r.json()}finally{clearTimeout(t)}}

async function load(){if(busy)return;busy=true;const files={raw:"stock-opportunity-data.json",charts:"stock-radar-chart-data.json",direction:"stock-direction-forecast.json",learning:"stock-forecast-learning.json",markets:"stock-market-groups.json",events:"stock-event-risks.json",macro:"stock-market-context.json",cases:"stock-investment-cases.json",toss:"toss-live-config.json"};const keys=Object.keys(files),results=await Promise.allSettled(keys.map(k=>read(files[k])));errors=[];keys.forEach((k,i)=>{if(results[i].status==="fulfilled")D[k]=results[i].value;else{errors.push(k);delete D[k]}});if(!Array.isArray(D.raw?.companies)){errors.push("종목 원자료");delete D.raw}if(!company(selected)&&rows().length)selected=String(rows()[0].symbol);busy=false;render();}

function isMarket(c,m){if(m==="ALL")return true;const k=c.source_symbol||c.symbol,info=D.markets?.members?.[k]||D.markets?.members?.[c.symbol]||D.markets?.members?.[k+".KS"]||D.markets?.members?.[k+".KQ"];const venue=info?.venue||({KSC:"KOSPI",KOE:"KOSDAQ",NMS:"NASDAQ",NGM:"NASDAQ",NCM:"NASDAQ",NYQ:"NYSE"}[c.exchange])||"UNKNOWN";if(m==="DOW")return D.markets?.dow?.status==="current"&&D.markets?.dow?.symbols?.includes(k);return venue===m;}

function marketLabel(c){const k=c.source_symbol||c.symbol,info=D.markets?.members?.[k]||D.markets?.members?.[c.symbol]||D.markets?.members?.[k+".KS"]||D.markets?.members?.[k+".KQ"];return info?.venue||({KSC:"KOSPI",KOE:"KOSDAQ",NMS:"NASDAQ",NGM:"NASDAQ",NCM:"NASDAQ",NYQ:"NYSE"}[c.exchange])|| (c.market==="KR"?"한국 · 세부시장 확인 전":c.market==="US"?"미국 · 세부시장 확인 전":"미확인");}

function snapshot(){return {screen,selected,data:D,favorites:[...favorites],market};}

function choose(id){const c=company(id);if(!c)return;selected=String(c.symbol);render();}

function goto(v){if(!["home","stocks","stockdetail","scenario","monitor","portfolio","news","performance","settings"].includes(v))return;screen=v;render();window.scrollTo({top:0,behavior:"instant"});}

function toggleStar(id){const v=String(id);favorites=favorites.includes(v)?favorites.filter(x=>x!==v):[...favorites,v];try{localStorage.setItem("radar-v8-stars",JSON.stringify(favorites))}catch{}render();}

function deep(id){if(company(id))window.open("./stock-value-radar-advanced.html","_blank","noopener");}

function render(){const host=document.getElementById("nr-home-content");if(!host)return;host.innerHTML=window.StockRadarFlowV2?.render?.()||'<div class="nr-panel" style="padding:24px">투자 레이더 분석 화면을 불러오는 중입니다.</div>';const status=document.getElementById("source-status");if(status)status.textContent=(D.raw?.generated_at?"저장 데이터 "+T(D.raw.generated_at):"원자료 확인 중")+(errors.length?" · 수집 오류: "+errors.join(", "):"") + " · 실시간 호가 아님";}

function click(ev){const b=ev.target.closest?.("button");if(!b)return;const d=b.dataset;if(d.nrScreen){goto(d.nrScreen);return}if(d.nrView){deep(selected);return}if(d.nrSelect){choose(d.nrSelect);return}if(d.nrDetail){choose(d.nrDetail);goto("stockdetail");return}if(d.nrStar){toggleStar(d.nrStar);return}if(d.rfMarket){market=d.rfMarket;render();return}if("nrReload" in d){load();return}if("nrForecast" in d){window.open("./stock-forecast.html","_blank","noopener");return}}

function init(){try{favorites=JSON.parse(localStorage.getItem("radar-v8-stars")||"[]");if(!Array.isArray(favorites))favorites=[]}catch{favorites=[]}document.body.classList.add("neutral-ready");const params=new URLSearchParams(location.search);if(params.has("stock"))selected=params.get("stock");document.addEventListener("click",click);window.StockRadarV2Bridge={snapshot,render,refresh:load,select:choose,deep,helpers:{I,change,pointData,indices,flowReasonLines,caseOf,compactAlerts,T,tone,qualityHTML,renderMonitor,renderPortfolio,renderNews,renderSettings}};window.RadarMarkets={match:isMarket,label:marketLabel};render();load();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();