(()=>{
'use strict';
const $=s=>document.querySelector(s),main=$('#rc-main'),header=$('#rc-header'),engine=$('#rc-engine');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
const fmt=(v,d=2)=>n(v)===null?'—':v.toLocaleString('ko-KR',{maximumFractionDigits:d});
const amount=(v,c)=>n(v)===null?'—':c==='KRW'?(Math.abs(v)>=1e12?fmt(v/1e12)+'조원':Math.abs(v)>=1e8?fmt(v/1e8)+'억원':fmt(v,0)+'원'):c?fmt(v)+' '+String(c):fmt(v);
const date=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}/.test(v)?v.slice(0,10):'기준일 미확인';
const tones=new Set(['mint','yellow','lilac','rose','sky','neutral']);
const tone=t=>tones.has(t)?t:'neutral';
const pill=(s,t='mint')=>'<span class="rc-pill rc-tone-'+tone(t)+'">'+esc(s)+'</span>';
const card=(title,body='',t='mint',right='')=>'<section class="rc-card"><div class="rc-card-head"><h2><i class="rc-bar rc-tone-'+tone(t)+'"></i>'+esc(title)+'</h2>'+right+'</div>'+body+'</section>';
const empty=(s='확인된 자료가 없습니다.')=>'<p class="rc-empty">'+esc(s)+'</p>';
function link(href,label){try{const u=new URL(href);if(u.protocol!=='https:'||u.username||u.password)return esc(label);return '<a href="'+esc(u.href)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' ↗</a>'}catch{return esc(label)}}
function load(key,fallback=null){try{return JSON.parse(localStorage.getItem(key)??'null')??fallback}catch{return fallback}}
function store(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true}catch{return false}}
const countries={KR:'한국',US:'미국',JP:'일본',CN:'중국',HK:'홍콩',TW:'대만',GB:'영국',DE:'독일',VN:'베트남',SG:'싱가포르'};
const pages={home:['홈'],market:['시장·산업','세계·한국 경제 변화 → 산업 비교 → 선택 기업 분석'],quality:['질적 분석','무엇을 팔고, 어떻게 돈을 벌고, 앞으로 무엇을 확인해야 할까요?'],finance:['재무','매출에서 현금과 가격까지, 같은 순서로 숫자의 흐름을 확인합니다.'],value:['가치·전망','지금 가격이 적정한지, 미래 성장에는 어떤 전제가 필요한지 비교합니다.'],filings:['공시','수집한 전체 공시는 종류별로, 중요한 변화는 먼저 확인합니다.'],chart:['차트','같은 가격 차트를 나란히 보고, 기술적 근거와 다음 확인 조건을 찾습니다.']};
const primary=['home','market','quality','filings','chart'],subs=['quality','finance','value','filings','chart'];
const valid=(obj,key)=>Object.hasOwn(obj,key);
const countryOf=c=>String(c?.country||c?.market||'').toUpperCase();
let p='home',country='KR',selected='',q='',sort='name',homeLimit=80,candidateNo=0,showcaseCount=0,newsExpanded=false,notice='',greendata=null,state={},frameWindow=null,pool=[],poolData=null,starting=Date.now(),lastPaint='';
function parse(initial=false){
 const u=new URL(location.href),page=u.searchParams.get('tab'),region=u.searchParams.get('country'),stock=u.searchParams.get('stock');
 p=valid(pages,page)?page:'home';
 country=valid(countries,region)?region:(initial && valid(countries,load('radar-cohesive-country-v1'))?load('radar-cohesive-country-v1'):'KR');
 selected=stock && /^[A-Za-z0-9:._^-]{1,72}$/.test(stock)?stock:(initial&&['KR','US'].includes(country)?String(load('radar-last-symbol-v5','')):'');
}
parse(true);
function push(){
 const u=new URL(location.href);u.searchParams.set('tab',p);u.searchParams.set('country',country);
 if(selected)u.searchParams.set('stock',selected);else u.searchParams.delete('stock');
 if(u.href!==location.href)history.pushState(null,'',u);
}
function id(c){if(c?.foreign_catalog)return c.selection_id;return frameWindow?.StockCatalogUI?.selectionId?.(c)||String(c?.symbol||'')}
function searchTerm(c){if(c?.foreign_catalog)return window.RadarCohesiveForeign.search(c);return frameWindow?.StockCatalogUI?.searchText?.(c)||[c?.name,c?.symbol,c?.sector,c?.industry].filter(Boolean).join(' ')}
function rowsFor(data){
 const raw=Array.isArray(data?.raw?.companies)?data.raw.companies:[];
 try{return frameWindow?.StockCatalogUI?.universe?.({data})||raw}catch{return raw}
}
function sync(){
 try{const w=engine.contentWindow,bridge=w.StockRadarV2Bridge,snap=bridge?.snapshot?.();if(!snap)return false;
  frameWindow=w;state=snap;
  if(snap.data!==poolData){poolData=snap.data;pool=rowsFor(poolData)}
  return true;
 }catch{return false}
}
function context(){
 const {data={},favorites=[]}=state;
 const local=load('radar-v8-stars',favorites),rawStars=Array.isArray(local)?local.filter(v=>typeof v==='string'):[];
 const ids=new Set(rawStars);
 const combined=pool.concat(window.RadarCohesiveForeign?.rows()||[]);
 const normalized=combined.filter(c=>ids.has(id(c))||(ids.has(c.symbol)&&countryOf(c)==='KR')).map(id);
 const companies=combined.filter(c=>countryOf(c)===country);
 const found=companies.find(c=>id(c)===selected||String(c.symbol)===selected||c.source_symbol===selected);
 const c=found||(!selected&&!window.RadarCohesiveForeign?.has(country)?companies.find(c=>!c.catalog_only)||companies[0]:null);
 return {...state,data,selected:c?id(c):selected,market:country,country,companies,favorites:normalized,helpers:frameWindow?.StockRadarV2Bridge?.helpers,company:c||null,allCompanies:combined};
}
// Direction is relative movement only, never an investment-quality judgment.
function compare(value,previous,{verified=false,label='동일 기준 이전 값',compactMissing=false}={}){
 const valid=verified===true&&n(value)!==null&&n(previous)!==null;
 const state=!valid?'missing':value>previous?'up':value<previous?'down':'flat';
 const word={up:'상승',down:'하락',flat:'동일',missing:'비교 없음'}[state];
 const title=valid?label+' 대비 '+word+' (이전 '+fmt(previous)+') · 좋고 나쁨의 판단 아님':label+' · 비교 가능한 이전 자료 미확인';
 return '<span class="rc-compare rc-compare-'+state+'" role="img" title="'+esc(title)+'" aria-label="'+esc(title)+'">'+({up:'↑',down:'↓',flat:'=',missing:compactMissing?'◦':'비교 없음'}[state])+'</span>';
}
function verifiedDaily(c){
 const d=c?.daily_change;
 return !!(d?.status==='verified'&&d.source_identity_verified===true&&d.consecutive_sessions===true&&d.previous_session===d.expected_previous_session&&d.previous_session<d.price_session&&d.price_session===c.price_session&&d.close===c.price&&d.provider_symbol===(c.yahoo_symbol||c.symbol)&&d.currency===c.currency);
}
function annualComparison(h){
 const e=h.revenue_growth_evidence,r=e?.source_rows;
 return !!(/연간|annual/i.test(h.basis||'')&&h.currency&&e?.status==='verified'&&e.source?.identity_verified===true&&e.source.currency===h.currency&&e.source.period_kind==='annual'&&r?.current?.value===h.revenue&&r?.prior?.value===h.revenue_previous&&r.current.period===h.filing_period&&r.prior.period===h.revenue_previous_period&&r.prior.period<r.current.period);
}
function stockRows(arr,{max=50,showPrice=true,ctx=context()}={}){
 if(!arr.length)return empty('이 조건에 맞는 종목이 없습니다.');
 const favorites=new Set(ctx.favorites);
 return arr.slice(0,max).map(c=>{
  const code=id(c), star=favorites.has(code), title=c.name||c.symbol;
  return '<div class="rc-stockrow"><button type="button" class="rc-star" data-rc-star="'+esc(code)+'" aria-pressed="'+star+'" aria-label="'+esc(title)+(star?' 관심기업 해제':' 관심기업 추가')+'">'+(star?'★':'☆')+'</button><button type="button" class="rc-stock-open" data-rc-stock="'+esc(code)+'" aria-pressed="'+(ctx.selected===code)+'"><span><b>'+esc(title)+'</b><small>'+esc(c.symbol)+' · '+esc(c.exchange||c.catalog_entry?.exchange||c.sector||countries[countryOf(c)]||'시장 미확인')+'</small></span><span>'+(showPrice&&n(c.price)!==null?amount(c.price,c.currency)+compare(c.price,c.daily_change?.previous_close,{verified:verifiedDaily(c),label:'직전 거래일 '+(c.daily_change?.previous_session||'미확인')})+'<small>'+esc(date(c.price_session))+'</small>':'›')+'</span></button></div>';
 }).join('');
}
window.RadarCohesive={esc,card,fmt,amount,pill,link,empty,id,stockRows,date,n,compare};
const searchHTML=()=>'<div class="rc-formrow"><input type="search" id="rc-home-search" aria-label="종목명·코드 검색" placeholder="종목 검색" value="'+esc(q)+'"><select id="rc-home-sort" aria-label="정렬"><option value="name" '+(sort==='name'?'selected':'')+'>이름순</option><option value="price" '+(sort==='price'?'selected':'')+'>저장가순</option><option value="star" '+(sort==='star'?'selected':'')+'>관심기업</option></select></div>';
function homeStocks(ctx){
 const term=q.normalize('NFKC').trim().toLocaleLowerCase(),fav=new Set(ctx.favorites);
 const a=ctx.companies.filter(c=>(sort!=='star'||fav.has(id(c)))&&(!term||searchTerm(c).normalize('NFKC').toLocaleLowerCase().includes(term))).sort((a,b)=>sort==='price'?(n(b.price)??-1)-(n(a.price)??-1):String(a.name||a.symbol).localeCompare(String(b.name||b.symbol),'ko'));
 return [a.length,stockRows(a,{max:homeLimit,ctx})];
}
function navBtn(name,active,caption){return '<button type="button" data-rc-tab="'+name+'" '+(active?'aria-current="page"':'')+'>'+esc(caption||pages[name][0])+'</button>'}
function indexRecord(data,key,sym){
 const world=data.worldFlow?.indicators?.find(m=>m.id===key),macro=data.macro?.indicators?.[key],chart=data.charts?.series?.[sym];
 const last=chart?.bars?.at(-1), opts=[];
 if(n(world?.value)!==null&&/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(world.session||''))opts.push({value:world.value,day:world.session,src:world.source?.url||world.source_url,status:world.status,caution:world.status!=='current',previous:world.previous_value,verified:world.comparison_verified===true&&world.comparison_basis==='previous_exchange_session'&&world.source?.identity_verified===true&&world.source.provider_symbol===sym&&world.source.response_symbol===sym&&world.previous_session<world.session,label:'직전 거래일 '+world.previous_session});
 if(n(macro?.value)!==null&&/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(macro.date||''))opts.push({value:macro.value,day:macro.date,src:macro.source_url,status:macro.status,caution:macro.status==='stale',previous:macro.daily_change?.previous_close,verified:verifiedDaily({...macro,price:macro.value,price_session:macro.date,symbol:sym}),label:'직전 거래일 '+(macro.daily_change?.previous_session||'미확인')});
 if(n(last?.close)!==null&&/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(last.date||''))opts.push({value:last.close,day:last.date,src:chart.source_url,status:'historical',caution:false});
 return opts.sort((a,b)=>b.day.localeCompare(a.day))[0];
}
const researchDate=ctx=>ctx.data.raw?.generated_at?'저장 연구 자료 · '+date(ctx.data.raw.generated_at):'자료 확인 중';
function drawHeader(ctx){
 const idx=[['코스피','kospi','^KS11'],['코스닥','kosdaq','^KQ11'],['나스닥','nasdaq','^IXIC'],['다우','dow','^DJI']];
 const index=idx.map(([label,key,sym])=>{const x=indexRecord(ctx.data,key,sym);return '<div class="rc-index"><b>'+label+'</b><strong>'+fmt(x?.value)+compare(x?.value,x?.previous,{verified:x?.verified,label:x?.label||'직전 거래일'})+'</strong><small>'+((x&&esc(x.day)+(x.caution?' · 갱신 대기':''))||'미연결')+'</small></div>'}).join('');
 const ctr=Object.entries(countries).map(([k,label])=>'<button type="button" data-rc-country="'+k+'" aria-pressed="'+(k===country)+'" title="'+(['KR','US'].includes(k)?'저장 종목 연결':'국가별 시장 개요 · 공식 원문 보기')+'">'+label+'</button>').join('');
 const active=['finance','value'].includes(p)?'quality':p;
 header.innerHTML='<div class="rc-shell"><div class="rc-indices" aria-label="4대 지수 · 저장값">'+index+'</div><div class="rc-brandline"><a class="rc-brand" href="?tab=home&country='+country+'" data-rc-tab="home"><span class="rc-mark" aria-hidden="true"><i></i><i></i><i></i></span>투자레이더</a><nav class="rc-country" aria-label="국가 선택">'+ctr+'</nav><span class="rc-edition rc-pill rc-tone-neutral">개인 연구용 · 저장 자료</span></div><div class="rc-primaryline"><nav class="rc-primary" aria-label="주 메뉴">'+primary.map(k=>navBtn(k,k===active,k==='quality'?'기업분석':null)).join('')+'</nav>'+(p==='home'?'<small class="rc-nav-date">'+esc(researchDate(ctx))+'</small>':'')+'</div></div>';
}
function drawTitle(ctx){
 if(p==='home')return '<h1 class="rc-visually-hidden">홈</h1>';
 const company=ctx.company,label=company?esc(company.name||company.symbol):'기업 미선택';
 const foreign=window.RadarCohesiveRegions?.has(ctx.country);
 const row='<div class="rc-selection"><div><small>선택 기업</small><strong>'+label+'</strong>'+(company?' <small>'+esc(company.symbol)+'</small>':'')+'</div>'+(p==='market'?'<small>산업·기업을 고르면 분석 탭에 연동됩니다</small>':'<nav class="rc-subnav" aria-label="기업 분석 탭">'+subs.map(k=>navBtn(k,k===p)).join('')+'</nav>')+'</div>';
 return row+'<div class="rc-title"><div><h1>'+pages[p][0]+'</h1><p>'+(p==='market'&&foreign?'선택 국가 지표와 공식 산업·기업 자료를 확인합니다.':pages[p][1])+'</p></div>'+pill(researchDate(ctx),'neutral')+'</div>';
}
const macroIcons={
 rates:'<path d="M3 13V9m4 4V6m4 7V3"/>',
 yield:'<path d="m2 11 4-4 3 2 4-6m-4 0h4v4"/>',
 prices:'<path d="M2.5 3h6l5 5-5 5-6-6z"/><circle cx="5.5" cy="5.5" r=".7"/>',
 fx:'<path d="M2 5h11l-3-3M14 11H3l3 3"/>',
 stocks:'<path d="M3 13h10M5 10V5m3 5V2m3 8V7"/>'
};
// Inline flag fallback: Windows can render regional-indicator emoji as letters.
const homeKoreaFlag='<svg viewBox="0 0 44 44" focusable="false"><g transform="rotate(32 22 22)"><path fill="#cc303e" d="M12 22a10 10 0 0 1 20 0Z"/><path fill="#194f9c" d="M12 22a10 10 0 0 0 20 0Z"/><circle fill="#cc303e" cx="17" cy="22" r="5"/><circle fill="#194f9c" cx="27" cy="22" r="5"/></g><g fill="none" stroke="#263039" stroke-width="1.35"><path transform="rotate(-56 10 11)" d="M5 9h10M5 11.5h10M5 14h10"/><path transform="rotate(56 34 11)" d="M29 9h4m2 0h4m-10 2.5h10m-10 2.5h4m2 0h4"/><path transform="rotate(56 10 33)" d="M5 30h10M5 32.5h4m2 0h4m-10 2.5h10"/><path transform="rotate(-56 34 33)" d="M29 30h4m2 0h4m-10 2.5h4m2 0h4m-10 2.5h4m2 0h4"/></g></svg>';
function macroPanel(ctx,kr){
 const source=ctx.data.macro?.indicators||{},title=kr?'한국 경제':'세계 경제';
 const spec=kr?[['한국 기준금리','bok_policy','금리가 오르면 대출 이자가 늘어 국내 소비가 줄 수 있어요.','rates'],['원/달러','usdkrw','환율이 오르면 수입 원가는 늘고, 같은 달러 매출도 원화로는 커져요.','fx'],['코스피','kospi','코스피가 내려도 업종별 등락은 달라요. 아래 산업 핵심에서 비교해요.','stocks']]:[['미국 기준금리','fed_policy','금리가 오르면 달러 대출이 비싸져 주택·기업 투자가 줄 수 있어요.','rates'],['미국 10년물','us_10y','국채 금리가 오르면 기업이 장기로 돈을 빌릴 때 이자가 늘 수 있어요.','yield'],['미국 물가','us_cpi','물가가 소득보다 빨리 오르면 소비가 줄어 유통·외식에 부담이 될 수 있어요.','prices']];
 const generated=ctx.data.macro?.generated_at;
 return '<section class="rc-card rc-macro-card"><div class="rc-macro-head"><div class="rc-macro-icon" aria-hidden="true">'+(kr?homeKoreaFlag:'🌍')+'</div><div class="rc-macro-identity"><div class="rc-macro-title"><h2>'+title+'</h2>'+pill('요약','mint')+'</div><small>'+(kr?'국내 경제 지표와 산업에 미치는 영향':'미국 주요 지표로 보는 세계 경제 흐름')+'</small></div></div><table class="rc-table rc-macro-table" aria-label="'+title+' 지표와 산업 영향"><colgroup><col class="rc-macro-col-reading"><col class="rc-macro-col-arrow"><col></colgroup><thead><tr><th scope="col">경제 지표 변화</th><th scope="col" class="rc-macro-arrow-head"><span class="rc-visually-hidden">연결</span></th><th scope="col">산업 영향 예시</th></tr></thead><tbody>'+spec.map(([label,k,impact,icon])=>{
 const ix=k==='kospi'?indexRecord(ctx.data,'kospi','^KS11'):null;
 const x=source[k], isPercent=['bok_policy','fed_policy','us_10y','us_cpi'].includes(k), v=n(x?.value);
 const datum=ix?fmt(ix.value):k==='fed_policy'&&n(x?.low)!==null&&n(x?.high)!==null?fmt(x.low)+'–'+fmt(x.high)+'%':k==='us_cpi'&&n(x?.yoy_pct)!==null?fmt(x.yoy_pct)+'%':v===null?null:fmt(v)+(isPercent?'%':'');
 const basis=datum===null?'':ix?ix.day+(ix.caution?' · 갱신 대기':''):date(x.date)+(x.status==='stale'?' · 갱신 대기':'');
 const d=x?.daily_change;
 let current=v,previous=null,verified=false,comparisonLabel='동일 기준 이전 관측';
 if(ix){current=ix.value;previous=ix.previous;verified=ix.verified;comparisonLabel=ix.label;}
 else if(k==='usdkrw'){previous=d?.previous_close;verified=d?.source_identity_verified===true&&d.provider_symbol==='KRW=X'&&d.close===v&&d.price_session===x.date&&d.previous_session===x.previous_observation_date&&d.previous_session<d.price_session;comparisonLabel='직전 제공처 관측 '+(d?.previous_session||'미확인')+' (거래소 종가 아님)';}
 else if(k==='us_cpi'){current=x?.yoy_pct;previous=x?.previous_yoy_pct;verified=!!x?.source_url;comparisonLabel='직전 월 전년동월비';}
 else if(k==='bok_policy'){previous=x?.previous;verified=!!x?.source_url;comparisonLabel='직전 정책 결정';}
 const direction=compare(current,previous,{verified,label:comparisonLabel});
 const sourceURL=ix?ix.src:x?.source_url;
 return '<tr><th scope="row"><div class="rc-macro-reading"><svg class="rc-macro-row-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'+macroIcons[icon]+'</svg><div class="rc-macro-text"><span class="rc-macro-label">'+ (sourceURL?link(sourceURL,label):esc(label))+'</span><small class="rc-macro-value"><strong>'+esc(datum??'미확인')+direction+'</strong>'+(basis?' <span>· '+esc(basis)+'</span>':'')+'</small></div></div></th><td class="rc-macro-arrow" aria-hidden="true">→</td><td class="rc-macro-impact">'+esc(impact)+'</td></tr>';
 }).join('')+'</tbody></table><small class="rc-count rc-macro-source">시장 자료 '+esc(date(generated))+' · 원본 발표 시점과 다를 수 있음</small></section>';
}
function spark(c,ctx){
 const saved=ctx.data.charts?.series?.[c?.symbol],s=Array.isArray(saved?.bars)?saved.bars.slice(-63).filter(v=>n(v?.close)!==null):[];
 if(s.length<2)return '<small>3개월 차트 미확인</small>';
 const prices=s.map(v=>v.close),lo=Math.min(...prices),hi=Math.max(...prices),pts=prices.map((v,i)=>[4+i*142/(prices.length-1),42-(v-lo)*34/(hi-lo||1)].join(',')).join(' ');
 return '<div><small>3개월 · '+esc(date(s.at(-1).date))+'</small><svg viewBox="0 0 150 48" role="img" aria-label="최근 저장 종가 추이"><polyline points="'+pts+'" stroke="#4b9878" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg></div>';
}
function strictCandidate(c,ctx,r){
 const raw=ctx.data?.raw;
 const t=Date.parse(raw?.generated_at||''),review=Date.parse(r?.reviewed_at||'');
 if(!Number.isFinite(t)||t>Date.now()+300000||Date.now()-t>18*3600000||!Number.isFinite(review)||review>Date.now()+300000||review<t)return false;
 const rawMatch=raw.companies?.filter(v=>v.symbol===c.symbol)||[];
 return rawMatch.length===1&&countryOf(rawMatch[0])===countryOf(c)&&r?.green_eligible===true&&r.state==='attractive'&&r.source_generated_at===raw.generated_at&&n(r.input_price)!==null&&r.input_price===c.price&&r.input_price_session===c.price_session&&r.input_forecast_eps===c.forecasts?.next_fy?.avg&&Array.isArray(r.checks)&&r.checks.length>0&&r.checks.every(x=>x.status==='pass');
}
function candidatePanel(ctx){
 const tracked=ctx.companies.filter(c=>!c.catalog_only);
 const reviews=new Map((greendata?.companies||[]).map(r=>[r.symbol,r]));
 const verified=tracked.filter(c=>strictCandidate(c,ctx,reviews.get(c.symbol)));
 const showcase=verified.length?verified.slice(0,3):[ctx.company,...tracked].filter((c,i,a)=>c&&!c.catalog_only&&a.findIndex(x=>x&&id(x)===id(c))===i).slice(0,3);
 const count=showcaseCount=showcase.length,c=count?showcase[candidateNo%count]:null,good=!!c&&verified.some(x=>id(x)===id(c));
 const right=count>1?'<div class="rc-prevnext"><button type="button" data-rc-choice="-1" aria-label="이전 종목">‹</button><small>'+((candidateNo%count)+1)+' / '+count+'</small><button type="button" data-rc-choice="1" aria-label="다음 종목">›</button></div>':'';
 if(!c)return '<section class="rc-card rc-candidate"><div class="rc-card-head"><h2><i class="rc-bar rc-tone-yellow"></i>오늘의 매수후보 검토</h2></div>'+empty('해당 시장의 검토 종목과 근거 자료가 연결되지 않았습니다.')+'</section>';
 const record=reviews.get(c.symbol), qualified=record?.source_generated_at===ctx.data.raw?.generated_at;
 const notes=ctx.helpers?.flowReasonLines?.(c)||[];
 const factors=[['전망','실적 가정','mint'],['산업',c.sector||'확인 전','sky'],['핵심 성장','제품·매출 원인','yellow'],['협력업체','공시 근거 확인','lilac']];
 const metrics=['매출','영업이익','영업이익률','영업현금흐름','매출채권 / 재고','부채 / 현금','PER / PBR / ROE'];
 const fin=c.history||{}, balance=c.balance||{}, valuation=c.valuation||{};
 const cur=typeof fin.currency==='string'?fin.currency:null, bcur=typeof balance.currency==='string'?balance.currency:cur;
 const per=valuation.trailing_pe??valuation.pe, pbr=valuation.price_to_book??valuation.pbr;
 const pct=v=>n(v)===null?'—':fmt(v)+'%';
 const money=(v,currency)=>currency?amount(v,currency):'—';
 const annual=annualComparison(fin),supp=annual&&fin.supplemental_period_status==='same_period';
 const excluded=new Set((fin.supplemental_excluded_fields||[]).map(x=>x.field));
 const previous=k=>excluded.has(k+'_previous')?null:fin[k+'_previous'];
 const basis=(fin.revenue_previous_period||'이전 기간 미확인')+' → '+(fin.filing_period||'기간 미확인')+' 동일 연간 기준';
 const num=(v,prior,verified,format,label=basis)=>'<span class="rc-number-comparison">'+esc(format(v))+compare(v,prior,{verified,label,compactMissing:true})+'</span>';
 const cash=v=>money(v,cur), snap=v=>money(v,bcur);
 const margin=fin.operating_margin_pct??fin.operating_margin;
 const priorMargin=fin.revenue_previous>0&&n(fin.operating_income_previous)!==null?fin.operating_income_previous/fin.revenue_previous*100:null;
 const vals=[num(fin.revenue,fin.revenue_previous,annual,cash),num(fin.operating_income,previous('operating_income'),supp,cash),num(margin,priorMargin,supp&&!excluded.has('operating_income_previous')&&n(fin.operating_income)!==null&&fin.revenue>0&&Math.abs(margin-fin.operating_income/fin.revenue*100)<0.011,pct),num(fin.cfo??fin.operating_cash_flow,previous('cfo'),supp&&n(fin.cfo)!==null,cash),[num(fin.accounts_receivable??balance.accounts_receivable,previous('accounts_receivable'),supp&&n(fin.accounts_receivable)!==null,cash),num(fin.inventory??balance.inventory,previous('inventory'),supp&&n(fin.inventory)!==null,cash)].join(' / '),[num(balance.total_debt??balance.debt,null,false,snap,'동일 집계 기준의 부채'),num(balance.cash,null,false,snap,'동일 집계 기준의 현금')].join(' / '),[num(per,null,false,fmt,'동일 기준의 PER'),num(pbr,null,false,fmt,'동일 기준의 PBR'),num(valuation.return_on_equity_pct??valuation.roe_pct??fin.roe_pct,null,false,pct,'동일 기준의 ROE')].join(' / ')];
 return '<section class="rc-card rc-candidate"><div class="rc-card-head"><h2><i class="rc-bar rc-tone-yellow"></i>오늘의 매수후보 검토</h2>'+right+'</div><div class="rc-candidate-info"><div><h3>'+esc(c.name||c.symbol)+'</h3>'+pill(good?'매수후보':'검토용 · 후보 미충족',good?'mint':'yellow')+'</div>'+spark(c,ctx)+'</div><small>검토 근거: '+esc(notes[0]||'성장·현금·가격·향후 성장 및 출처 확인 필요')+'</small><div class="rc-grid rc-candidate-grids"><table class="rc-table rc-candidate-metrics"><thead><tr><th scope="col">지표</th><th scope="col">저장값 <small>◦ 비교 없음</small></th></tr></thead><tbody>'+metrics.map((x,i)=>'<tr><th scope="row">'+x+'</th><td>'+vals[i]+'</td></tr>').join('')+'</tbody></table><div class="rc-candidate-factors">'+factors.map(([a,b,t])=>'<div class="rc-toned rc-tone-'+t+'"><b>'+a+'</b>'+esc(b)+'</div>').join('')+'</div></div><div class="rc-candidate-footer"><p class="rc-toned rc-tone-mint"><small>'+esc(good?'모든 엄격 검증 조건 충족 · 자동매매 신호 아님':qualified?'매수후보 기준 미충족 · 개별 근거 확인':'최신 자료와 일치하는 검증 미확인 · 후보 표시 안 함')+'</small></p><button type="button" data-rc-stock="'+esc(id(c))+'">이 기업 분석 ›</button></div></section>';
}
function kstDay(ms){
 return new Date(ms+9*3600000).toISOString().slice(0,10);
}
function homeHeadlines(ctx,now=Date.now()){
 const region=String(ctx.country||'').toLowerCase();
 if(!['kr','us'].includes(region))return [];
 const feed=Array.isArray(ctx.data?.newsLink?.items)?ctx.data.newsLink.items:[];
 const allowed=new Set(['market','policy','invest']);
 const topical=/증시|코스피|코스닥|나스닥|다우|금리|물가|환율|연준|경제성장|통화정책|반도체|공급망|무역|관세|수출|기업 실적|영업이익|고용|채권|원유|실업률/i;
 const noise=/심정지|수색|연수|부정행위|대입|리트|수능|추천주|매수추천|무료추천|급등주|종목상담|리딩방|세미나|수강생/;
 const found=[],titles=new Set(),urls=new Set();
 for(const x of feed.slice().sort((a,b)=>(Date.parse(b?.published_at)||0)-(Date.parse(a?.published_at)||0))){
  const stamp=Date.parse(x?.published_at),title=String(x?.title||'').trim();
  if(![region,'global','world'].includes(x?.region)||!title||!Number.isFinite(stamp)||stamp>now||now-stamp>3*86400000||x.tab==='opinion'||noise.test(title))continue;
  if(!allowed.has(x.topic_class)&&!(x.trusted_source===true&&topical.test(title)))continue;
  let u;try{u=new URL(x.url);if(u.protocol!=='https:'||u.username||u.password)continue;}catch{continue}
  const key=title.normalize('NFKC').toLowerCase().replace(/\[[^\]]*\]|[^\p{L}\p{N}]/gu,'');
  const canonical=new URL(u.href);canonical.hash='';for(const k of [...canonical.searchParams.keys()])if(/^(utm_|fbclid$|gclid$)/i.test(k))canonical.searchParams.delete(k);canonical.searchParams.sort();
  if(!key||titles.has(key)||urls.has(canonical.href))continue;
  titles.add(key);urls.add(canonical.href);
  found.push({...x,title,url:u.href,day:kstDay(stamp)});
 }
 return found;
}
function headlinePanel(ctx){
 const now=Date.now(),day=kstDay(now),all=homeHeadlines(ctx,now),count=all.filter(x=>x.day===day).length;
 const shown=newsExpanded?all:all.slice(0,10);
 const rows=shown.map(x=>'<article class="rc-brief-row"><b class="rc-brief-title">'+link(x.url,x.title)+'</b><span class="rc-brief-meta">'+esc([x.day.slice(5),x.source||'출처 미확인',x.topic_class==='policy'?'정책':x.topic_class==='invest'?'투자':'경제·시장'].join(' · '))+'</span></article>').join('');
 const scope=ctx.country==='KR'?'한국·세계':ctx.country==='US'?'미국·세계':'국가 자료 미연결';
 return card('오늘의 뉴스','<small class="rc-home-detail">'+esc(scope)+' · 오늘 '+fmt(count,0)+'건'+(all.length>count?' · 이전 기사 포함':'')+'</small><div class="rc-minilist rc-headline-list" tabindex="0" aria-label="경제시장 기사 목록">'+(rows||empty('아직 표시할 경제·시장 기사가 없습니다.'))+'</div><p class="rc-source-mini">'+(ctx.data.newsLink?.stale?'수집 지연 · ':'')+fmt(shown.length,0)+' / '+fmt(all.length,0)+'건 · RSS 제목, 원문 확인</p>'+(all.length>10?'<button type="button" data-rc-news-more aria-expanded="'+newsExpanded+'">'+(newsExpanded?'최근 10건만 보기':'관련 기사 '+fmt(all.length,0)+'건 보기')+'</button>':''),'sky');
}
function industryWatch(ctx){
 const arr=Array.isArray(ctx.data?.raw?.companies)?ctx.data.raw.companies:[];
 const validDay=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v));
 const obs=arr.filter(c=>countryOf(c)===ctx.country&&validDay(c.price_session));
 const day=obs.map(c=>c.price_session).sort().at(-1);
 const by=new Map();
 for(const c of obs){
  const s=String(c.sector||c.industry||'').trim();
  if(!s||/^(?:분류 미확인|기타|미분류|업종 미분류)$/i.test(s)||c.price_session!==day)continue;
  if(!by.has(s))by.set(s,{s,total:0,seen:new Set(),prices:[]});
  const row=by.get(s),key=String(c.source_symbol||c.symbol||'');if(!key||row.seen.has(key))continue;
  row.seen.add(key);row.total++;
  const value=n(ctx.helpers?.change?.(c));if(value!==null)row.prices.push({value,name:c.name||c.symbol});
 }
 const rows=[...by.values()].sort((a,b)=>b.prices.length-a.prices.length||b.total-a.total||a.s.localeCompare(b.s,'ko'));
 return {day,rows};
}
function industryPanel(ctx){
 const snap=industryWatch(ctx),f=ctx.data.worldFlow?.indicators||[];
 const idxs=ctx.country==='KR'?['kospi','kosdaq']:ctx.country==='US'?['nasdaq','sp500']:[];
 const indexDay=f.filter(x=>idxs.includes(x.id)&&x.status==='current').map(x=>x.session).filter(Boolean).sort().at(-1);
 const stale=Boolean(snap.day&&indexDay&&indexDay>snap.day);
 const pct=x=>(x>0?'+':'')+fmt(x,2)+'%';
 const rows=snap.rows.slice(0,8).map(({s,total,prices})=>{
  const nums=prices.map(x=>x.value).sort((a,b)=>a-b),mid=nums.length? (nums[Math.floor((nums.length-1)/2)]+nums[Math.floor(nums.length/2)])/2:null;
  const positive=nums.filter(x=>x>0).length,negative=nums.filter(x=>x<0).length,flat=nums.length-positive-negative;
  const leader=prices.slice().sort((a,b)=>Math.abs(b.value)-Math.abs(a.value))[0];
  const enough=nums.length>=3;
  const breadth=enough?nums.length+'종목 · 상승 '+positive+' / 하락 '+negative+(flat?' / 보합 '+flat:''):nums.length?nums.length+'종목 · 업종 판단 보류':total+'종목 · 등락 미확인';
  return '<article class="rc-brief-row"><div class="rc-industry-line"><b title="'+esc(s)+'">'+esc(s)+'</b>'+
    (enough?'<span class="rc-industry-median" aria-label="'+esc('등락률 중앙값 '+pct(mid))+'" title="표본 등락률 중앙값">'+esc(pct(mid))+'</span>':'')+
    '</div><span class="rc-brief-meta">'+esc(breadth)+'</span>'+
    (leader?'<span class="rc-brief-example" title="'+esc(leader.name+' '+pct(leader.value))+'">'+esc(leader.name+' '+pct(leader.value))+'</span>':'')+'</article>';
 }).join('');
 return card('산업 핵심','<small class="rc-home-detail">'+esc(snap.day?snap.day+' 종가 · '+(stale?'새 세션 갱신 대기':'추적 종목 표본'):'기준일 미확인')+'</small><div class="rc-minilist rc-industry-list" tabindex="0" aria-label="산업별 종가 흐름">'+(rows||empty('이 시장의 종가·업종 자료가 연결되지 않았습니다.'))+'</div><p class="rc-source-mini">등락률 중앙값 · 전체 업종 지수 아님</p><button type="button" data-rc-tab="market">산업 비교 ›</button>');
}
window.RadarCohesive.homeHeadlines=homeHeadlines;
window.RadarCohesive.industryWatch=industryWatch;
function home(ctx){
 const [count,list]=homeStocks(ctx),stars=new Set(ctx.favorites),starRows=ctx.companies.filter(c=>stars.has(id(c)));
 const foreign=window.RadarCohesiveForeign?.has(ctx.country), titles=foreign?window.RadarCohesiveForeign.homeIndustry(ctx):industryPanel(ctx),headlines=headlinePanel(ctx);
 const local=window.RadarCohesiveRegions?.render(ctx);
 return '<div class="rc-home"><div class="rc-home-body"><div class="rc-grid rc-home-top">'+(local||macroPanel(ctx,false)+macroPanel(ctx,true))+'</div><div class="rc-grid rc-home-bottom">'+candidatePanel(ctx)+titles+headlines+'</div></div><aside class="rc-home-side" aria-label="종목 목록">'+card('관심기업','<div class="rc-scrolllist" style="max-height:135px">'+(starRows.length?stockRows(starRows,{showPrice:false,ctx}):empty('목록에서 ☆을 눌러 관심기업으로 추가하세요.'))+'</div><button type="button" data-rc-search-focus style="width:100%;margin-top:8px">＋ 관심기업 추가</button>','yellow','<small>'+starRows.length+'개</small>')+card(foreign?'확인한 종목 목록':'전체 주식목록',searchHTML()+'<div class="rc-scrolllist" id="rc-home-rows">'+list+'</div><small class="rc-count" id="rc-home-count">검색 '+fmt(count,0)+'개 중 '+fmt(Math.min(homeLimit,count),0)+'개 표시</small><button type="button" data-rc-more '+(count<=homeLimit?'hidden':'')+'>더 보기</button>','neutral','<small>'+esc(countries[country])+'</small>')+'</aside></div>';
}
const pane=(name,c,ctx)=>{
 if(name==='market')return window.RadarCohesiveMarket?.render(c,ctx)||empty('산업 탭 연결을 확인해 주세요.');
 if(!c)return empty(selected?'이 국가 목록에서 선택 종목을 확인할 수 없어요. 시장·산업에서 다시 선택해 주세요.':'시장·산업에서 기업을 선택하면 이 탭에 자료가 표시됩니다.');
 if(c.foreign_catalog)return window.RadarCohesiveForeign.companyNote(c,name);
 if(name==='quality')return window.RadarCohesiveCompany?.quality(c,ctx)||empty();
 if(name==='finance')return window.RadarCohesiveCompany?.finance(c,ctx)||empty();
 if(name==='value')return window.RadarCohesiveEvidence?.value(c,ctx)||empty();
 if(name==='filings')return window.RadarCohesiveEvidence?.filings(c,ctx)||empty();
 if(name==='chart')return window.RadarCohesiveChart?.render(c,ctx)||empty();
 return home(ctx);
};
function render({scroll=false}={}){
 sync();const ctx=context(),active=document.activeElement,focus=active?.id||'',marketSearch=active?.dataset?.rcmSearch,start=active?.selectionStart,finish=active?.selectionEnd;
 const key=JSON.stringify([p,country,ctx.data.raw?.generated_at,ctx.data.macro?.generated_at,ctx.data.worldFlow?.generated_at,ctx.data.charts?.generated_at]);if(render.lastHeader!==key){drawHeader(ctx);render.lastHeader=key}
 const body=p==='home'?home(ctx):pane(p,ctx.company,ctx);
 const status=notice||(!ctx.data.raw&&Date.now()-starting>10000?'저장 종목 자료를 불러오지 못했습니다. 기존 화면에서 연결 상태를 확인해 주세요.':'');
 main.innerHTML=drawTitle(ctx)+'<div class="rc-view" data-rc-page="'+p+'">'+body+'</div>'+(status?'<p class="rc-status-line rc-error" role="status">'+esc(status)+'</p>':'');
 if((focus||marketSearch)&&active!==main){const el=focus?document.getElementById(focus):main.querySelector('[data-rcm-search='+marketSearch+']');el?.focus({preventScroll:true});if(Number.isInteger(start)&&typeof el?.setSelectionRange==='function')try{el.setSelectionRange(start,finish)}catch{}}
 if(scroll){window.scrollTo(0,0);main.focus({preventScroll:true})}
 render.snapshot=ctx.data;
}
function selectStock(code){
 const c=context().companies.find(r=>id(r)===code);if(!c)return;
 selected=id(c);
 if(!c.foreign_catalog){
  if(!store('radar-last-symbol-v5',selected))notice='선택 기업을 브라우저에 저장하지 못했습니다.';
  frameWindow?.StockRadarV2Bridge?.setSelectedSilently?.(selected);
 }
 if(p==='home')p='quality';
 push();render({scroll:p==='quality'});
}
function onClick(e){
 const b=e.target.closest?.('button,[data-rc-tab]');
 if(b){
  const d=b.dataset;
  if(valid(pages,d.rcTab)){e.preventDefault();p=d.rcTab;notice='';const c=context().company;if(c)selected=id(c);push();render({scroll:true});return}
  if(valid(countries,d.rcCountry)){window.RadarCohesiveForeign?.reset(d.rcCountry);country=d.rcCountry;selected='';q='';sort='name';homeLimit=80;candidateNo=0;newsExpanded=false;notice='';store('radar-cohesive-country-v1',country);push();render({scroll:true});return}
  if(d.rcStock){selectStock(d.rcStock);return}
  if(d.rcStar){
   const ctx=context(),c=ctx.companies.find(r=>id(r)===d.rcStar);if(!c)return;
   const old=load('radar-v8-stars',[]),items=new Set(Array.isArray(old)?old:[]);
   const key=id(c);
   if(items.has(key)||ctx.favorites.includes(key)){items.delete(key);if(countryOf(c)==='KR')items.delete(c.symbol)}else items.add(key);
   notice=store('radar-v8-stars',[...items])?'':'관심기업 목록을 저장하지 못했습니다.';
   render();[...main.querySelectorAll('[data-rc-star]')].find(el=>el.dataset.rcStar===key)?.focus({preventScroll:true});return;
  }
  if(d.rcChoice){const size=showcaseCount||1;candidateNo=(candidateNo+Number(d.rcChoice)+size)%size;render();main.querySelector('[data-rc-choice="'+d.rcChoice+'"]')?.focus({preventScroll:true});return}
  if('rcNewsMore' in d){newsExpanded=!newsExpanded;render();main.querySelector('[data-rc-news-more]')?.focus({preventScroll:true});return}
  if('rcMore' in d){homeLimit+=80;updateHomeRows();return}
  if('rcSearchFocus' in d){$('#rc-home-search')?.focus();return}
 }
 const ctx=context();
 const panel=({market:window.RadarCohesiveMarket,value:window.RadarCohesiveEvidence,filings:window.RadarCohesiveEvidence,chart:window.RadarCohesiveChart,finance:window.RadarCohesiveCompany,quality:window.RadarCohesiveCompany})[p];
 if(panel?.handle?.(e,ctx)){render();if('rcForeignMore' in (b?.dataset||{}))main.querySelector('[data-rc-foreign-more]')?.focus({preventScroll:true});}
}
function updateHomeRows(){
 const [total,html]=homeStocks(context());
 $('#rc-home-rows').innerHTML=html;
 $('#rc-home-count').textContent='검색 '+fmt(total,0)+'개 중 '+fmt(Math.min(homeLimit,total),0)+'개 표시';
 main.querySelector('[data-rc-more]').hidden=homeLimit>=total;
}
function homeInput(e){
 const target=e.target;
 if(target?.id==='rc-home-search'||target?.id==='rc-home-sort'){
  if(target.id==='rc-home-search')q=target.value;else sort=target.value;
  homeLimit=80;updateHomeRows();
  return;
 }
 if(p==='market'&&window.RadarCohesiveMarket?.handle?.(e,context()))render();

}
document.addEventListener('click',onClick);
document.addEventListener('input',homeInput);
document.addEventListener('change',e=>{if(e.target?.id!=='rc-home-sort'&&['market','filings','value','finance'].includes(p))homeInput(e)});
window.addEventListener('popstate',()=>{parse();q='';sort='name';homeLimit=80;render({scroll:true})});
window.addEventListener('storage',e=>{if(e.key==='radar-v8-stars')render()});
engine.addEventListener('load',()=>{sync();render()});
function observe(){
 if(document.visibilityState==='hidden')return;
 const old=render.snapshot;sync();
 if(state.data!==old&&state.data)render();
 if(!state.data?.raw&&Date.now()-starting>10000&&!lastPaint){lastPaint='slow';render()}
}
function green(){
 fetch('./stock-green-review.json',{cache:'no-cache',credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(d=>{
 if(d?.version==='strict-green-1.0'&&Array.isArray(d.companies)){greendata=d;if(p==='home')render()}
 }).catch(()=>{});
}
setInterval(observe,1000);setInterval(green,300000);render();green();window.RadarCohesiveForeign?.load(()=>render());
})();
