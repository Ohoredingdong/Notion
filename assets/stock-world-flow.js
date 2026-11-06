/* Completed-session observations, never a fabricated world score or a live quote. */
((root)=>{"use strict";
 const VERSION="stock-world-flow-v1";
 const CONFIG=[
  ["kospi","코스피","KR","index","index_points"],
  ["kosdaq","코스닥","KR","index","index_points"],
  ["sp500","S&P 500","US","index","index_points"],
  ["nasdaq","나스닥","US","index","index_points"],
  ["dax","DAX","EU","index","index_points"],
  ["shanghai","상하이종합","CN","index","index_points"],
  ["nikkei225","닛케이 225","JP","index","index_points"],
  ["hang_seng","항셍","HK","index","index_points"],
  ["usdkrw","원/달러","GLOBAL","fx","KRW_per_USD"],
  ["dxy","달러지수","GLOBAL","index","index_points"],
  ["us10y","미국 10년 국채","US","yield","percent"],
  ["wti","WTI 연속선물","GLOBAL","commodity","USD_per_barrel"],
  ["gold","금 연속선물","GLOBAL","commodity","USD_per_troy_ounce"],
  ["vix","VIX","US","volatility","index_points"]
 ];
 const PROVIDERS={kospi:"^KS11",kosdaq:"^KQ11",sp500:"^GSPC",nasdaq:"^IXIC",dax:"^GDAXI",shanghai:"000001.SS",nikkei225:"^N225",hang_seng:"^HSI",usdkrw:"KRW=X",dxy:"DX-Y.NYB",us10y:"BC_10YEAR",wti:"CL=F",gold:"GC=F",vix:"^VIX"};
 const REGIONS=[
  ["KR","한국",["kospi","kosdaq"]], ["US","미국",["sp500","nasdaq"]],
  ["EU","유럽 · 독일 참고",["dax"]], ["CN","중국",["shanghai"]],
  ["JP","일본",["nikkei225"]], ["HK","홍콩",["hang_seng"]]
 ];
 const E=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const finite=v=>typeof v==="number"&&Number.isFinite(v);
 const stamp=v=>typeof v==="string"&&/(?:Z|[+-]\d\d:\d\d)$/.test(v)?Date.parse(v):NaN;
 const day=v=>typeof v==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+"T00:00:00Z"))&&new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
 const near=(a,b)=>finite(a)&&finite(b)&&Math.abs(a-b)<=1e-5+Math.abs(b)*1e-8;
 const num=(v,d=2)=>finite(v)?v.toLocaleString("ko-KR",{maximumFractionDigits:d}):"—";
 const signed=(v,unit="%",d=2)=>finite(v)?(v>0?"+":"")+num(v,d)+unit:"변화 미확인";
 const safe=v=>{try{const u=new URL(v);return u.protocol==="https:"&&!u.username&&!u.password?u.href:""}catch{return""}};
 const direction=v=>v>0?"up":v<0?"down":"flat";
 const words={up:"상승",down:"하락",flat:"보합",mixed:"혼조",unknown:"확인 대기"};
 const arrows={up:"↑",down:"↓",flat:"–",mixed:"↕",unknown:"·"};
 function time(v){const n=stamp(v);return Number.isFinite(n)?new Date(n).toLocaleString("ko-KR",{timeZone:"Asia/Seoul",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false})+" KST":"시각 미확인"}
 function indicator(raw,config,now,validFeed){
  const [id,label,region,category,unit]=config,source=raw?.source||{},fresh=raw?.freshness||{};
  const item={id,label,region,category,unit,raw:raw||{},source,href:safe(source.url),value:null,previous:null,
   change:null,changePct:null,changeBp:null,state:"unavailable",reason:"자료 미수집",current:false,direction:"unknown",session:null,previousSession:null};
  if(!validFeed||!raw)return item;
  const receipt=stamp(raw.received_at),observed=stamp(raw.observed_at),dateOnly=raw.observed_at_precision==="source_date";
  const identity=source.identity_verified===true&&source.provider_symbol===PROVIDERS[id]&&source.response_symbol===source.provider_symbol&&!!item.href;
  const schema=raw.id===id&&raw.category===category&&raw.unit===unit&&["current","stale","unavailable"].includes(raw.status);
  const observation=day(raw.session)&&finite(receipt)&&receipt<=now+300000&&
   (dateOnly?raw.observed_at===null:raw.observed_at_precision==="exchange_close"&&finite(observed)&&observed<=now+300000&&observed<=receipt+300000)&&
   raw.session<=new Date(now+86400000).toISOString().slice(0,10);
  const basis=["exchange_regular_close","provider_daily_close","treasury_par_yield"].includes(raw.quote_basis)&&
   (category!=="yield"||raw.quote_basis==="treasury_par_yield");
  if(!identity||!schema||!observation||!basis||!finite(raw.value)||raw.value<=0||raw.status==="unavailable"){
   item.reason=raw.status==="unavailable"?"제공 자료 없음":"수치·출처 검증 대기";return item;
  }
  item.value=raw.value;item.session=raw.session;
  const compared=raw.comparison_verified===true&&day(raw.previous_session)&&raw.previous_session<raw.session&&finite(raw.previous_value)&&raw.previous_value>0;
  const delta=compared?raw.value-raw.previous_value:null,pct=compared?(raw.value/raw.previous_value-1)*100:null;
  const arithmetic=compared&&near(raw.change_value,delta)&&(category==="yield"?
   raw.change_pct===null&&near(raw.change_bp,delta*100):near(raw.change_pct,pct)&&raw.change_bp==null)&&raw.direction===direction(delta);
  if(!arithmetic){item.state="unverified";item.reason="직전 세션 비교 검증 대기";return item}
  item.previous=raw.previous_value;item.previousSession=raw.previous_session;item.change=delta;
  item.changePct=category==="yield"?null:pct;item.changeBp=category==="yield"?delta*100:null;item.direction=direction(delta);
  let expected=day(raw.expected_session)?raw.expected_session:null;
  const next=stamp(fresh.next_check_after),nextDay=day(fresh.next_expected_session)?fresh.next_expected_session:null;
  const clock=finite(next)&&nextDay!==null&&(!expected||nextDay>expected);
  if(clock&&now>=next)expected=expected&&expected>nextDay?expected:nextDay;
  if(expected&&raw.session<expected){item.state="stale";item.reason=expected+" 자료 갱신 대기"}
  else if(!expected||!clock){item.state="stale";item.reason="시장별 갱신 일정 미확인"}
  else if(raw.session!==expected||raw.status!=="current"||fresh.status!=="current"){
   item.state="stale";item.reason=raw.session<expected?expected+" 자료 갱신 대기":"기준 세션 확인 필요";
  }else{item.state="current";item.reason="시장별 최신 완료 자료";item.current=true}
  return item;
 }
 function model(feed,now=Date.now()){
  const generated=stamp(feed?.generated_at);
  const valid=feed?.version===VERSION&&Array.isArray(feed.indicators)&&finite(generated)&&generated<=now+300000;
  const grouped=new Map();
  if(valid)for(const row of feed.indicators){if(row&&typeof row.id==="string")grouped.set(row.id,grouped.has(row.id)?null:row)}
  const indicators=CONFIG.map(config=>indicator(grouped.get(config[0]),config,now,valid));
  const byId=Object.fromEntries(indicators.map(row=>[row.id,row]));
  const regions=REGIONS.map(([id,label,ids])=>{
   const basis=ids.map(key=>byId[key]).filter(row=>row.current),moves=new Set(basis.map(row=>row.direction));
   const move=basis.length?(moves.size===1?basis[0].direction:"mixed"):"unknown";
   return {id,label,ids,basisIds:basis.map(row=>row.id),direction:move,status:basis.length===ids.length?"current":basis.length?"partial":"unavailable"};
  });
  const counts={up:0,down:0,flat:0,mixed:0,unknown:0};regions.forEach(row=>counts[row.status==="current"?row.direction:"unknown"]++);
  const available=regions.length-counts.unknown,parts=["up","down","flat","mixed"].filter(key=>counts[key]).map(key=>words[key]+" "+counts[key]+"곳");
  const headline=available?"주요 증시 · "+parts.join(" · ")+(counts.unknown?" · "+counts.unknown+"개 지역 확인 대기":""):"지역별 최신 시장 자료 확인 대기";
  const news=(valid&&Array.isArray(feed?.related_news)?feed.related_news:[]).filter(row=>typeof row?.title==="string"&&row.title.trim()&&safe(row.url)&&finite(stamp(row.published_at))&&stamp(row.published_at)<=now+300000&&now-stamp(row.published_at)<=72*3600000).sort((a,b)=>stamp(b.published_at)-stamp(a.published_at));
  return {valid,generatedAt:valid?feed.generated_at:null,indicators,byId,regions,counts,available,headline,news,
   current:indicators.filter(row=>row.current).length,total:CONFIG.length,
   scope:"한국·미국·유럽(독일 참고)·중국·일본·홍콩의 8개 주가지수 · 종합 점수 아님"};
 }
 function valueText(row){
  if(!finite(row?.value))return "미확인";
  const suffix={index_points:"",percent:"%",KRW_per_USD:"원 / 1 USD",USD_per_barrel:"USD / 배럴",USD_per_troy_ounce:"USD / 트로이온스"};
  return num(row.value,2)+(suffix[row.unit]?" "+suffix[row.unit]:"");
 }
 function changeText(row){return row?.category==="yield"?signed(row.changeBp,"bp",2):signed(row?.changePct)}
 function observationText(row){
  if(!row.session)return "기준일 미확인";
  return row.raw.observed_at_precision==="source_date"?row.session+" 자료 · 발표 시각 미제공":row.session+" 정규장 종가 · "+time(row.raw.observed_at);
 }
 function link(href,text,attrs=""){return safe(href)?`<a href="${E(safe(href))}" target="_blank" rel="noopener noreferrer" ${attrs}>${E(text)}</a>`:`<span>${E(text)}</span>`}
 function detailRow(row){
  const previous=finite(row.previous)?num(row.previous,2)+(row.category==="yield"?"%":""):"미확인";
  const precision=row.raw.observed_at_precision==="source_date"?"날짜 기준 자료이며 장중 시세가 아닙니다.":"완료 정규장 종가이며 장중 시세가 아닙니다.";
  return `<article class="fx-worldflow-observation is-${row.state}" data-worldflow-indicator="${row.id}" data-status="${row.state}">
   <div class="fx-worldflow-observation-head"><h4>${E(row.label)}</h4><span>${row.current?"기준 충족":E(row.reason)}</span></div>
   <div class="fx-worldflow-values"><strong data-worldflow-value>${E(valueText(row))}</strong><b class="is-${row.direction}" data-worldflow-change>${E(changeText(row))}</b></div>
   <p>${E(observationText(row))}</p><p>직전 비교: ${E(row.previousSession||"세션 미확인")} · ${E(previous)}${row.category==="yield"?" · 1bp = 0.01%p":""}</p>
   <p>${E(precision)}${row.category==="commodity"?" 연속선물 가격으로 현물 가격과 다릅니다.":""}</p>
   <footer>${link(row.href,(row.source.provider||"제공처")+" 원문 ↗")}<span>수신 ${E(time(row.raw.received_at))}</span></footer>
  </article>`;
 }
 function render(ctx,now=Date.now()){
  const m=model(ctx?.data?.worldFlow,now),top=m.news[0];
  const sessions=m.indicators.filter(row=>row.value!==null&&row.session).map(row=>row.session).sort();
  const dates=sessions.length?[sessions[0],sessions.at(-1)].filter((value,index,list)=>index===0||value!==list[0]):[];
  const dateLabel=dates.length?dates.map(value=>value.slice(5).replace("-",".")).join("–")+" 기준":"기준일 미확인";
  const regions=m.regions.map(row=>`<span class="fx-worldflow-region is-${row.direction}" data-worldflow-region="${row.id}" data-direction="${row.direction}" title="${E(row.label)} · 비교 확인 ${row.basisIds.length}/${row.ids.length}"><span>${E(row.id==="EU"?"독일 참고":row.label)}</span><b>${arrows[row.direction]} ${words[row.direction]}</b>${row.status==="partial"?'<i>일부</i>':""}</span>`).join("");
  const cues=[["us10y","미 10년"],["dxy","달러지수"],["usdkrw","원/달러"],["wti","WTI 선물"],["gold","금 선물"]].map(([id,label])=>{
   const row=m.byId[id];
   return `<span data-worldflow-cue="${id}" class="${row.current?"":"is-pending"}" title="${E(valueText(row)+" · "+observationText(row)+" · "+row.reason)}"><span>${label}</span><b>${row.current?E(row.category==="yield"?num(row.value,2)+"%":""):"갱신 대기"}</b>${row.current?`<em>${E(changeText(row))}</em>`:""}</span>`;
  }).join("");
  return `<section class="fx-worldflow" aria-label="세계시장 흐름" data-worldflow-version="${VERSION}">
   <div class="fx-worldflow-head"><h2>세계시장 흐름</h2><p data-worldflow-headline>${E(m.headline)}</p><button type="button" data-worldflow-open aria-haspopup="dialog">기준·출처 <span aria-hidden="true">↗</span></button></div>
   <div class="fx-worldflow-regions" aria-label="지역별 주가지수 방향">${regions}</div>
   <div class="fx-worldflow-cues" aria-label="금리·환율·원자재 변화">${cues}</div>
   <div class="fx-worldflow-news"><span>관련 보도</span>${top?link(top.url,top.title,`title="${E(top.title+" · "+(top.source||"제공처")+" · "+time(top.published_at))}"`):'<span>최근 확인된 보도 없음</span>'}<small data-worldflow-current="${m.current}" title="${E(dates.join(" ~ "))} · 시장별 마감·일별 자료 · 현재 비교 가능 ${m.current}/${m.total}">${E(dateLabel)} · 확인 ${m.current}/${m.total}</small></div>
   <dialog class="fx-worldflow-dialog" aria-labelledby="fx-worldflow-dialog-title">
    <div class="fx-worldflow-dialog-head"><div><h3 id="fx-worldflow-dialog-title">세계시장 흐름 · 기준과 출처</h3><p>${E(m.scope)}</p></div><button type="button" data-worldflow-close aria-label="시장 자료 닫기">닫기 ×</button></div>
    <div class="fx-worldflow-dialog-body"><p class="fx-worldflow-method">지역 방향은 최신 비교가 확인된 지수의 부호만 반영합니다. 같은 지역 안에서 상승·하락·보합이 섞이면 ‘혼조’로 표시합니다. 국가별 마감일은 서로 다를 수 있습니다. 금리·달러·유가·금은 별도 관측이며 주가 변동의 원인으로 단정하지 않습니다.</p>
     <p class="fx-worldflow-method">파일 수집 ${E(time(m.generatedAt))} · 현재 비교 가능 ${m.current}/${m.total} · 자료 갱신 시각으로 개별 시장의 신선도를 대신하지 않습니다.</p>
     <div class="fx-worldflow-observations">${m.indicators.map(detailRow).join("")}</div>
     <section class="fx-worldflow-reports"><h4>관련 보도 원문</h4><p>보도 제목을 그대로 연결합니다. 시장 변화의 인과관계 검증 자료는 아닙니다.</p>${m.news.length?m.news.slice(0,4).map(row=>`<article>${link(row.url,row.title)}<small>${E(row.source||"기사 제공처")} · ${E(time(row.published_at))}</small></article>`).join(""):'<p>최근 확인된 보도 없음</p>'}</section>
    </div>
   </dialog>
  </section>`;
 }
 root.StockWorldFlow={version:VERSION,model,render,valueText,changeText,observationText,config:CONFIG};
 if(typeof module!=="undefined"&&module.exports)module.exports=root.StockWorldFlow;
 if(root.document)root.document.addEventListener("click",event=>{
  if(event.target.closest?.("[data-worldflow-open]")){
   const dialog=root.document.querySelector(".fx-worldflow-dialog");if(dialog&&!dialog.open)dialog.showModal();
  }else if(event.target.closest?.("[data-worldflow-close]"))root.document.querySelector(".fx-worldflow-dialog")?.close();
 });
})(typeof window!=="undefined"?window:globalThis);
