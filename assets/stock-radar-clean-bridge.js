(()=>{'use strict';
let D={},selected='005930',screen='home',market='ALL',favorites=[],rules=[],paper=[],busy=false,errors=[];
function E(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}

function N(v){return typeof v==="number"&&Number.isFinite(v)?v:null;}

function F(v,d=1){return N(v)===null?"—":v.toLocaleString("ko-KR",{maximumFractionDigits:d});}

function P(v){return N(v)===null?"—":(v>0?"+":"")+F(v,2)+"%";}

function money(v,c){return N(v)===null?"—":v.toLocaleString("ko-KR",{minimumFractionDigits:c==="KRW"?0:2,maximumFractionDigits:c==="KRW"?0:2})+(c==="KRW"?"원":" "+(c||""));}

function T(v){const d=new Date(v||"");return Number.isFinite(+d)?d.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit",hour12:false})+" KST":"시각 미확인";}

function tone(v){return N(v)===null?"nr-neutral":v>0?"nr-up":v<0?"nr-down":"nr-neutral";}

function I(k){const paths={home:'<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',search:'<circle cx="10" cy="10" r="6.5"/><path d="m15 15 6 6"/>',star:'<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',chart:'<path d="M4 4v16h16M7 14l4-5 4 3 5-7"/>',check:'<rect x="4" y="3" width="16" height="18" rx="3"/><path d="m8 12 3 3 5-6"/>',news:'<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 8h10M7 12h6M7 16h10"/>',settings:'<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',arrow:'<path d="m9 5 7 7-7 7"/>',plus:'<path d="M5 12h14M12 5v14"/>'};return `<svg class="nr-icon" viewBox="0 0 24 24" aria-hidden="true">${paths[k]||paths.chart}</svg>`;}

function rows(){return Array.isArray(D.raw?.companies)?D.raw.companies:[];}

function company(id){return rows().find(x=>String(x.symbol)===String(id));}

function series(id){const r=D.charts?.series?.[id];return r&&r.status!=="unavailable"&&Array.isArray(r.bars)&&r.bars.length>1?r:null;}

function chartFor(id){
 const c=company(id),source=series(String(id));
 if(!source?.bars?.length)return null;
 const original=source.bars.filter(b=>typeof b?.date==="string"&&N(b.close)!==null);
 if(original.length<2)return null;
 const last=original.at(-1),nowDate=String(c?.price_session||"");
 if(source.price_session&&source.price_session!==last.date)return {...source,bars:original,chart_status:"metadata_mismatch",historical_end:last.date};
 if(!c||!nowDate||N(c.price)===null)return {...source,bars:original,chart_status:"historical_only",historical_end:last.date};
 if(c.currency&&source.currency&&c.currency!==source.currency)return null;
 const dateLast=Date.parse(last.date+"T00:00:00Z"),dateNow=Date.parse(nowDate+"T00:00:00Z");
 if(!Number.isFinite(dateLast)||!Number.isFinite(dateNow))return {...source,bars:original,chart_status:"dates_unverified",historical_end:last.date};
 if(dateNow===dateLast){
  const match=Math.abs(last.close-c.price)<=Math.max(.02,Math.abs(c.price)*1e-6);
  return {...source,bars:original,chart_status:match?"aligned":"provider_value_mismatch",historical_end:last.date};
 }
 if(dateNow<dateLast)return {...source,bars:original.filter(x=>x.date<=nowDate),chart_status:"history_newer_than_snapshot",historical_end:last.date};
 const actions=Array.isArray(source.corporate_actions)?source.corporate_actions:[];
 if(actions.some(a=>{const at=String(a.date||a.ex_date||a.effective_date||"");return at>last.date&&at<=nowDate}))return {...source,bars:original,chart_status:"corporate_action_pending",historical_end:last.date};
 const gap=(dateNow-dateLast)/86400000;
 if(gap>12)return {...source,bars:original,chart_status:"history_outdated",historical_end:last.date};
 const appended={date:nowDate,close:c.price,volume:null,origin:"latest_research_snapshot",not_interpolated:true};
 return {...source,bars:[...original,appended],chart_status:"snapshot_appended",historical_end:last.date};
}
function change(c){
 const x=chartFor(String(c?.symbol)),b=x?.bars;
 if(!c||!x||!["aligned","snapshot_appended"].includes(x.chart_status)||b.length<2)return null;
 const before=b.at(-2)?.close,last=b.at(-1)?.close;
 return N(before)!==null&&N(last)!==null&&before!==0?(last/before-1)*100:null;
}
function pointData(ids,period){
 const sets=ids.map(chartFor);
 if(!sets.length||sets.some(x=>!x||x.bars?.length<2))return null;
 const end=sets.map(s=>s.bars.at(-1).date).sort()[0],days={"1W":7,"1M":31,"3M":93,"6M":190}[period]||93;
 const from=new Date(Date.parse(end+"T00:00:00Z")-days*86400000).toISOString().slice(0,10);
 let dates=sets[0].bars.map(b=>b.date).filter(d=>d>=from&&d<=end);
 dates=dates.filter(d=>sets.every(s=>s.bars.some(b=>b.date===d)));
 if(dates.length<2)return null;
 const mapped=sets.map(s=>{const m=new Map(s.bars.map(b=>[b.date,b.close])),values=dates.map(d=>m.get(d));return {symbol:s.symbol,name:s.name,currency:s.currency,prices:values,returns:values.map(v=>(v/values[0]-1)*100),status:s.chart_status,historical_end:s.historical_end}});
 return {dates,series:mapped,sets,calendar_end:end};
}
function mini(s,r){const arr=s?.bars?.slice(-22).map(b=>b.close).filter(v=>N(v)!==null)||[];if(arr.length<2)return "";const lo=Math.min(...arr),hi=Math.max(...arr),p=arr.map((v,i)=>`${i*80/(arr.length-1)},${40-(v-lo)/(hi-lo||1)*35}`).join(" ");return `<svg class="nr-mini-chart" viewBox="0 0 80 44" aria-label="저장된 지수 추이"><polyline points="${p}" fill="none" stroke="${r<0?"#4b84d7":"#e57286"}" stroke-width="1.5"/></svg>`;}

function url(u){try{const v=new URL(u);return v.protocol==="https:"?v.href:""}catch{return"";}}

function link(u,label){const href=url(u);return href?`<a href="${E(href)}" target="_blank" rel="noopener noreferrer">${E(label)}</a>`:`<span>${E(label)} · 출처 확인 전</span>`;}

function indices(){const specs=[["^KS11","코스피","kospi"],["^KQ11","코스닥","kosdaq"],["^IXIC","나스닥","nasdaq"],["^GSPC","S&P 500","sp500"]];return specs.map(([id,name,k])=>{const s=series(id),a=s?.bars,last=a?.at(-1),prev=a?.at(-2),m=D.macro?.indicators?.[k]||{},newer=last?.date&&(!m.date||last.date>m.date),v=newer?last.close:m.value,delta=newer&&N(prev?.close)!==null&&prev.close?(last.close/prev.close-1)*100:m.change_1d_pct,day=newer?last.date:m.date;return `<article class="nr-panel nr-index"><div class="nr-head" style="margin-bottom:0"><h3>${name}</h3>${link(s?.source_url||m.source_url,"출처")}</div><div class="nr-num">${F(v,2)}</div><div class="${tone(delta)}" style="font-size:12px;font-weight:750">${P(delta)}</div>${mini(s,delta)}<div class="nr-sub" style="margin-top:8px">${E(day||"기준일 미확인")} · 저장 일봉</div></article>`}).join("")}

function caseOf(c){const k=(D.cases?.companies||[]).find(x=>String(x.symbol)===String(c.symbol));return D.cases?.source_generated_at===D.raw?.generated_at&&k?.input_price===c.price&&k?.input_price_session===c.price_session&&k?.input_forecast_eps===c.forecasts?.next_fy?.avg?k:null;}

function flowReasonLines(c){const k=caseOf(c),out=[];for(const v of k?.why||[])if(v?.text)out.push(v.text);for(const v of k?.risks||[])if(typeof v==="string")out.push(v);else if(v?.text)out.push(v.text);for(const v of k?.missing||[])if(typeof v==="string")out.push(v);if(!out.length)out.push("현재 공시·실적과 동일한 기준일의 공식 자료 대조가 필요합니다.");if(N(c.technical?.volume_ratio)!==null)out.push("20일 평균 거래량 대비 "+F(c.technical.volume_ratio,2)+"배");return [...new Set(out)].slice(0,4);}

function compactAlerts(){const items=[];for(const c of D.events?.companies||[])for(const v of c.events||[]){const source=v.sources?.[0];if(!source?.url)continue;items.push({...v,companyName:c.name,source})}items.sort((a,b)=>String(b.event_date).localeCompare(String(a.event_date)));return `<div class="nr-list-compact">${items.slice(0,4).map((v,i)=>`<article><span class="nr-list-num">${i+1}</span><div>${link(v.source.url,v.title)}<small>${E(v.companyName)} · ${E(v.event_date||"날짜 미확인")}${v.auto_detected?" · 자동 탐지":""}</small></div></article>`).join("")||'<p class="nr-sub">저장된 주요 이슈가 없습니다.</p>'}</div>`;}

function qualityHTML(){const x=D.learning?.overall||{};return `<div class="nr-head"><h3>예측 사후검증</h3><button class="nr-link" data-nr-forecast>전체 연구 성적표 ${I("arrow")}</button></div><div class="nr-quality"><strong>${F(x.correct,0)} / ${F(x.samples,0)}</strong><span>일치 / 평가 표본 · 연구용</span></div><p class="nr-small-note">실전 수익성·타이밍 유용성 미입증 · 자료 ${T(D.learning?.generated_at)}</p>`;}

function renderMonitor(){
 const live=!!(D.toss?.enabled&&D.toss.api_base),list=rows(),checks=rules.map((r,i)=>{
  const c=company(r.symbol),price=N(c?.price),met=price!==null&&(r.kind==="gte"?price>=r.value:price<=r.value);
  return `<div class="nr-manual-row"><div><b>${E(c?.name||r.symbol)}</b><small>${r.kind==="gte"?"저장 종가가 설정가 이상":"저장 종가가 설정가 이하"} · ${money(r.value,c?.currency)}</small><small>${E(c?.price_session||"관측 시점 없음")} · 저장 종가 ${money(price,c?.currency)}</small></div><span class="nr-check-state ${price===null?"unknown":met?"match":"pending"}">${price===null?"조회 전":met?"조건 충족":"미충족"}</span><button class="nr-delete" data-nr-rule-remove="${i}" type="button" aria-label="조건 삭제">삭제</button></div>`;
 });
 return `<div class="nr-screen-head"><div><h2>감시 조건 & 상태</h2><p>관심 종목의 저장 종가와 가격 조건을 비교합니다. 서버의 실시간 푸시는 연결되지 않았습니다.</p></div><span class="nr-badge warn">${live?"조회 서버 설정됨 · 실제 응답 확인 전":"실시간 시세 미연결"}</span></div>
 <div class="nr-screen-grid nr-feature-grid"><section class="nr-panel"><div class="nr-head"><h3>조건 만들기</h3><span class="nr-sub">내 브라우저에만 저장</span></div>
 <form id="radar-rule-form" class="nr-form">
 <label for="radar-rule-symbol">종목</label><select id="radar-rule-symbol" required ${list.length?"":"disabled"}>${list.map(c=>`<option value="${E(c.symbol)}" ${c.symbol===selected?"selected":""}>${E(c.name)} · ${E(c.symbol)}</option>`).join("")}</select>
 <label for="radar-rule-kind">기준</label><select id="radar-rule-kind"><option value="gte">저장 종가가 설정가 이상</option><option value="lte">저장 종가가 설정가 이하</option></select>
 <label for="radar-rule-value">가격 (해당 종목의 거래통화)</label><input id="radar-rule-value" required type="number" step="any" min="0.01" placeholder="설정 가격 입력">
 <button class="nr-action primary" type="submit" ${list.length?"":"disabled"}>+ 감시 조건 저장</button></form>
 <div class="nr-validation-note">이 조건은 페이지 새로고침 또는 데이터 갱신 시에만 평가됩니다. 자동 알림 발송이나 실시간 체결 확인 기능이 아닙니다.</div></section>
 <section class="nr-panel"><div class="nr-head"><h3>내 감시 조건</h3><span class="nr-sub">${rules.length}개</span></div><div class="nr-manual-list">${checks.join("")||'<p class="nr-sub">저장된 조건이 없습니다. 왼쪽에서 추가해 주세요.</p>'}</div>
 <button class="nr-action" type="button" data-nr-reload>저장 종가 다시 조회</button></section></div>`;
}
function renderPortfolio(){
 const saved=paper.map((p,i)=>({p,i,c:company(p.symbol)}));
 const groups={};
 for(const {p,c} of saved){
  if(!c||N(c.price)===null)continue;
  const k=c.currency||"UNKNOWN",g=groups[k]||(groups[k]={code:k,value:0,cost:0,items:[]});
  const marketValue=c.price*p.qty,initial=p.cost*p.qty;
  g.value+=marketValue;g.cost+=initial;
  g.items.push({name:c.name,symbol:c.symbol,v:marketValue,price:c.price,currency:c.currency});
 }
 const colors=["#4c85e3","#8a83df","#42b2a8","#efbe6a","#e788a8","#8cabb8"];
 const donuts=Object.values(groups).map(g=>{
  const points=g.items.map((x,i)=>({...x,part:g.value?x.v/g.value*100:0,color:colors[i%colors.length]}));
  let acc=0;const gradient=points.map(x=>{const start=acc;acc+=x.part;return `${x.color} ${start.toFixed(2)}% ${acc.toFixed(2)}%`}).join(",");
  return `<div class="nr-paper-overview"><div class="nr-donut" style="background:conic-gradient(${gradient||"#dde6f5 0 100%"})"><div><small>${E(g.code)} 모의 평가</small><b>${money(g.value,g.code)}</b></div></div>
  <div class="nr-paper-values"><div><small>기록된 매수원가</small><strong>${money(g.cost,g.code)}</strong></div><div><small>장부상 손익 (세금·수수료 전)</small><strong class="${tone(g.value-g.cost)}">${money(g.value-g.cost,g.code)} · ${g.cost?P((g.value/g.cost-1)*100):"—"}</strong></div><small>통화별로만 합산하며 환율 변환은 하지 않습니다.</small></div></div>`;
 }).join("");
 const list=saved.map(({p,c,i})=>{
  const amount=c&&N(c.price)!==null?c.price*p.qty:null,book=p.cost*p.qty;
  const changeValue=amount===null?null:amount-book;
  return `<tr><td>${E(c?.name||p.symbol)}</td><td>${F(p.qty,4)}</td><td>${money(p.cost,c?.currency)}</td><td>${money(amount,c?.currency)}</td><td class="${tone(changeValue)}">${money(changeValue,c?.currency)}</td><td><button class="nr-delete" data-nr-paper-remove="${i}" type="button">삭제</button></td></tr>`;
 }).join("");
 const all=rows();
 return `<div class="nr-screen-head"><div><h2>포트폴리오 & 모의투자</h2><p>실계좌와 분리된 수기 모의 보유내역입니다. 실제 자산이나 실현손익으로 표시하지 않습니다.</p></div><span class="nr-badge warn">실계좌 미연결</span></div>
 <div class="nr-screen-grid nr-feature-grid"><section class="nr-panel"><div class="nr-head"><h3>모의 보유 종목 등록</h3><span class="nr-sub">브라우저에 저장 · 주문 아님</span></div>
 <form id="radar-paper-form" class="nr-form"><label for="radar-paper-symbol">종목</label><select id="radar-paper-symbol" required ${all.length?"":"disabled"}>${all.map(c=>`<option value="${E(c.symbol)}" ${c.symbol===selected?"selected":""}>${E(c.name)} · ${E(c.symbol)}</option>`).join("")}</select>
 <label for="radar-paper-qty">수량</label><input id="radar-paper-qty" type="number" min="0.0001" max="1000000000" step="any" placeholder="예: 2" required>
 <label for="radar-paper-cost">1주당 가상 매수 가격 (해당 종목 통화)</label><input id="radar-paper-cost" type="number" min="0.01" max="1000000000000" step="any" placeholder="가상 매수가 입력" required>
 <button class="nr-action primary" type="submit" ${all.length?"":"disabled"}>+ 모의 보유내역 추가</button></form>
 <div class="nr-validation-note">추가 시 현재 거래가로 주문하지 않습니다. 사용자가 입력한 가상 수량과 원가만 기록합니다. 동일 종목은 가중평균 원가로 합산됩니다.</div>
 <a class="nr-action" href="./stock-paper-investing.html" target="_blank" rel="noopener noreferrer">별도 모의매매 훈련 위젯 열기</a></section>
 <section class="nr-panel"><div class="nr-head"><h3>모의 포트폴리오</h3><span class="nr-sub">${paper.length}개 종목</span></div>
 ${donuts||'<div class="nr-empty-big"><b>아직 모의 보유내역이 없습니다.</b><p>왼쪽에서 직접 입력한 가상 포트폴리오만 표시됩니다.</p></div>'}
 <div class="nr-table-scroll"><table class="nr-table"><thead><tr><th>종목</th><th>수량</th><th>가상 원가</th><th>평가액</th><th>장부상 손익</th><th></th></tr></thead><tbody>${list||'<tr><td colspan="6">등록된 종목이 없습니다.</td></tr>'}</tbody></table></div>
 <p class="nr-small-note">저장된 최종 종가 기준 단순 평가입니다. 세금·수수료·배당·실제 체결가는 포함되지 않습니다.</p></section></div>`;
}
function renderNews(){const m=D.macro?.indicators||{},f=m.usdkrw||{},ten=m.us_10y||{},bok=m.bok_policy||{};return `<div class="nr-screen-head"><div><h2>뉴스 · 경제 브리핑</h2><p>기업 이벤트는 원문 확인이 필요한 자동 탐지 결과를 포함합니다.</p></div><a class="nr-action" href="./news-link-hub-v3.html" target="_blank" rel="noopener">뉴스 원문 허브</a></div><div class="nr-news-grid"><section class="nr-panel"><h3>공시·이벤트 탐지</h3>${compactAlerts()}</section><section class="nr-panel"><h3>경제 지표</h3><div class="nr-ops-grid"><div class="nr-op"><small>원/달러 · ${E(f.date||"—")}</small><strong>${F(f.value,2)}원</strong></div><div class="nr-op"><small>미국 10년물 · ${E(ten.date||"—")}</small><strong>${F(ten.value,2)}%</strong></div><div class="nr-op"><small>한국은행 기준금리 · ${E(bok.date||"—")}</small><strong>${F(bok.value,2)}%</strong></div></div></section></div>`;}

function renderSettings(){const alive=!!(D.toss?.enabled&&D.toss?.api_base);return `<div class="nr-screen-head"><div><h2>설정 · 데이터 연결</h2><p>새로운 UI는 기존 고급 기업 분석과 분리하여 충돌 없이 운영합니다.</p></div></div><div class="nr-screen-grid"><section class="nr-panel"><h3>운영 상태</h3><div class="nr-setting-row"><b>저장 종목</b><span>${rows().length}개</span></div><div class="nr-setting-row"><b>토스증권 실시간</b><span>${alive?"서버 설정됨 · 응답 미검증":"미연결"}</span></div><div class="nr-setting-row"><b>자동 주문</b><span>비활성</span></div><button class="nr-action" data-nr-reload>저장 자료 새로고침</button></section><section class="nr-panel"><h3>원래의 심층 재무분석</h3><p class="nr-sub">기존 V1의 전체 기업 분석 기능은 별도의 페이지로 보존했습니다.</p><a class="nr-action primary" href="./stock-value-radar-advanced.html" target="_blank" rel="noopener">심층 분석 열기</a></section></div>`;}

async function read(name){
 const ac=new AbortController(),timeout=setTimeout(()=>ac.abort(),22000);
 try{
  const response=await fetch("./"+name+"?v="+Date.now(),{cache:"no-store",signal:ac.signal});
  if(!response.ok)throw Error("HTTP "+response.status);
  if(!name.endsWith(".jsonl"))return await response.json();
  const lines=(await response.text()).split("\n").map(v=>v.trim()).filter(Boolean);
  return lines.map((line,index)=>{try{return JSON.parse(line)}catch{throw Error(name+" invalid JSONL line "+(index+1))}});
 }finally{clearTimeout(timeout)}
}

async function load(){
 if(busy)return;
 busy=true;render();
 const files={raw:"stock-opportunity-data.json",charts:"stock-radar-chart-data.json",direction:"stock-direction-forecast.json",learning:"stock-forecast-learning.json",markets:"stock-market-groups.json",events:"stock-event-risks.json",macro:"stock-market-context.json",cases:"stock-investment-cases.json",autopilot:"stock-forecast-autopilot.json",entry:"stock-entry-plan-summary.json",green:"stock-green-review-summary.json",toss:"toss-live-config.json",outcomes:"stock-forecast-outcomes.jsonl",sentiment:"fear-greed-data.json",koreaSentiment:"stock-korea-fear-greed.json"};
 const keys=Object.keys(files),updated={...D},problems=[];
 try{
  const results=await Promise.allSettled(keys.map(key=>read(files[key])));
  keys.forEach((key,index)=>{
   let okay=results[index].status==="fulfilled";
   const val=okay?results[index].value:null;
   if(okay&&key==="raw")okay=!!val&&Array.isArray(val.companies)&&val.companies.length>0;
   if(okay&&key==="charts")okay=!!val?.series&&typeof val.series==="object";
   if(okay&&key==="direction")okay=Array.isArray(val?.records);
   if(okay&&key==="learning")okay=val?.overall&&typeof val.overall==="object";
   if(okay&&key==="outcomes")okay=Array.isArray(val);
   if(okay&&key==="koreaSentiment")okay=val?.market==="kr"&&typeof val?.date==="string"&&N(val.kospi?.index)!==null&&N(val.kosdaq?.index)!==null;
   if(okay&&key==="sentiment")okay=val?.market==="us"&&N(val.headline?.score)!==null;
   if(okay){
    const beforeTime=Date.parse(updated[key]?.generated_at||"");
    const afterTime=Date.parse(val?.generated_at||"");
    if(Number.isFinite(beforeTime)&&Number.isFinite(afterTime)&&afterTime<beforeTime){
     problems.push(key+" 이전 시점 응답 · 현재 자료 유지");
    }else updated[key]=val;
   }else if(updated[key]!=null)problems.push(key+" 조회 실패 · 직전 정상 자료 유지");
   else problems.push(key+" 조회 실패");
  });
  D=updated;
  if(!Array.isArray(D.raw?.companies)||!D.raw.companies.length)problems.push("종목 원자료 이용 불가");
  if(!company(selected)&&rows().length)selected=String(rows()[0].symbol);
 }catch(err){
  problems.push("자료 갱신 처리 실패");
 }finally{
  errors=problems;busy=false;render();
 }
}
function isMarket(c,m){if(m==="ALL")return true;const k=c.source_symbol||c.symbol,info=D.markets?.members?.[k]||D.markets?.members?.[c.symbol]||D.markets?.members?.[k+".KS"]||D.markets?.members?.[k+".KQ"];const venue=info?.venue||({KSC:"KOSPI",KOE:"KOSDAQ",NMS:"NASDAQ",NGM:"NASDAQ",NCM:"NASDAQ",NYQ:"NYSE"}[c.exchange])||"UNKNOWN";if(m==="DOW")return D.markets?.dow?.status==="current"&&D.markets?.dow?.symbols?.includes(k);return venue===m;}

function marketLabel(c){const k=c.source_symbol||c.symbol,info=D.markets?.members?.[k]||D.markets?.members?.[c.symbol]||D.markets?.members?.[k+".KS"]||D.markets?.members?.[k+".KQ"];return info?.venue||({KSC:"KOSPI",KOE:"KOSDAQ",NMS:"NASDAQ",NGM:"NASDAQ",NCM:"NASDAQ",NYQ:"NYSE"}[c.exchange])|| (c.market==="KR"?"한국 · 세부시장 확인 전":c.market==="US"?"미국 · 세부시장 확인 전":"미확인");}

function loadValue(key){try{const a=JSON.parse(localStorage.getItem(key)||"[]");return Array.isArray(a)?a:[]}catch{return []}}

function storeValue(key,a){try{localStorage.setItem(key,JSON.stringify(a))}catch{}}

function forms(ev){
 const id=ev.target?.id;if(!["radar-rule-form","radar-paper-form"].includes(id))return;
 ev.preventDefault();
 const value=x=>document.getElementById(x)?.value;
 const symbol=String(value(id==="radar-rule-form"?"radar-rule-symbol":"radar-paper-symbol")||"");
 const c=company(symbol);if(!c)return;
 if(id==="radar-rule-form"){
  const kind=value("radar-rule-kind"),price=Number(value("radar-rule-value"));
  if(!["gte","lte"].includes(kind)||!Number.isFinite(price)||price<=0)return;
  rules.push({symbol,kind,value:price});
  storeValue("radar-manual-rules-v2",rules);
 }else{
  const qty=Number(value("radar-paper-qty")),cost=Number(value("radar-paper-cost"));
  if(!Number.isFinite(qty)||qty<=0||!Number.isFinite(cost)||cost<=0||qty>1e9||cost>1e12)return;
  const old=paper.find(p=>p.symbol===symbol);
  if(old){const n=old.qty+qty;old.cost=(old.qty*old.cost+qty*cost)/n;old.qty=n;}
  else paper.push({symbol,qty,cost});
  storeValue("radar-paper-holdings-v2",paper);
 }
 render();
}
function snapshot(){return {screen,selected,data:D,favorites:[...favorites],market,rules:[...rules],paper:[...paper]};}

function choose(id){
 const c=company(id);if(!c)return;
 selected=String(c.symbol);
 if(screen==="home"||screen==="stocks"){
  if(market!=="ALL"&&!isMarket(c,market))market="ALL";
  window.StockRadarFlowV2?.ensureSelectedVisible?.(c);
 }
 render();
}

function goto(v){if(!["home","stocks","stockdetail","scenario","monitor","portfolio","news","performance","settings"].includes(v))return;screen=v;render();window.scrollTo({top:0,behavior:"instant"});}

function toggleStar(id){const v=String(id);favorites=favorites.includes(v)?favorites.filter(x=>x!==v):[...favorites,v];try{localStorage.setItem("radar-v8-stars",JSON.stringify(favorites))}catch{}render();}

function deep(id){if(company(id))window.open("./stock-value-radar-advanced.html?symbol="+encodeURIComponent(String(id)),"_blank","noopener");}

function render(){const host=document.getElementById("nr-home-content");if(!host)return;host.innerHTML=window.StockRadarFlowV2?.render?.()||'<div class="nr-panel" style="padding:24px">투자 레이더 분석 화면을 불러오는 중입니다.</div>';const status=document.getElementById("source-status");if(status)status.textContent=(busy?"데이터 갱신 중 · ":"")+(D.raw?.generated_at?"저장 데이터 "+T(D.raw.generated_at):"원자료 확인 중")+(errors.length?" · 주의: "+errors.join(" / "):"") + " · 실시간 호가 아님";}

function click(ev){const b=ev.target.closest?.("button");if(!b)return;const d=b.dataset;if("nrRuleRemove" in d){const i=Number(d.nrRuleRemove);if(Number.isInteger(i)&&i>=0&&i<rules.length){rules.splice(i,1);storeValue("radar-manual-rules-v2",rules);render()}return}if("nrPaperRemove" in d){const i=Number(d.nrPaperRemove);if(Number.isInteger(i)&&i>=0&&i<paper.length){paper.splice(i,1);storeValue("radar-paper-holdings-v2",paper);render()}return}if(d.nrScreen){goto(d.nrScreen);return}if(d.nrView){deep(selected);return}if(d.nrSelect){choose(d.nrSelect);return}if(d.nrDetail){choose(d.nrDetail);goto("stockdetail");return}if(d.nrStar){toggleStar(d.nrStar);return}if(d.rfMarket){market=d.rfMarket;const c=window.StockRadarFlowV2?.pick?.();if(c)selected=String(c.symbol);render();return}if("nrReload" in d){load();return}if("nrForecast" in d){window.open("./stock-forecast.html","_blank","noopener");return}}

function init(){try{favorites=JSON.parse(localStorage.getItem("radar-v8-stars")||"[]");if(!Array.isArray(favorites))favorites=[]}catch{favorites=[]}rules=loadValue("radar-manual-rules-v2").filter(v=>typeof v.symbol==="string"&&["gte","lte"].includes(v.kind)&&N(v.value)!==null&&v.value>0).slice(0,100);paper=loadValue("radar-paper-holdings-v2").filter(v=>typeof v.symbol==="string"&&N(v.qty)!==null&&v.qty>0&&N(v.cost)!==null&&v.cost>0).slice(0,200);document.body.classList.add("neutral-ready");const params=new URLSearchParams(location.search);if(params.has("stock"))selected=params.get("stock");document.addEventListener("click",click);document.addEventListener("submit",forms);window.StockRadarV2Bridge={snapshot,render,refresh:load,select:choose,setSelectedSilently:id=>{if(company(id))selected=String(id)},deep,helpers:{I,change,pointData,chartFor,indices,flowReasonLines,caseOf,compactAlerts,T,tone,qualityHTML,renderMonitor,renderPortfolio,renderNews,renderSettings}};window.RadarMarkets={match:isMarket,label:marketLabel};render();load();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();