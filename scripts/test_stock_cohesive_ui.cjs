'use strict';
const assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm'), path=require('node:path');
const root=process.env.RADAR_TEST_ROOT||path.join(__dirname,'..');
const read=(f)=>JSON.parse(fs.readFileSync(path.join(root,f),'utf8'));
const code=f=>fs.readFileSync(path.join(root,'assets',f),'utf8');
const data={raw:read('stock-opportunity-data.json'),charts:read('stock-radar-chart-data.json'),macro:read('stock-market-context.json'),worldFlow:read('stock-world-flow.json'),newsLink:read('news-link-data.json'),financial:read('stock-financial-coverage.json'),cases:read('stock-investment-cases.json'),events:read('stock-event-risks.json'),eventOutlook:read('stock-event-outlook.json'),catalog:read('stock-universe-catalog.json')};
const handlers={doc:{},win:{}}, map=new Map(), route=[];let main={innerHTML:'',querySelector:()=>({focus(){},hidden:false}),querySelectorAll:()=>[],focus(){}};
const store=new Map(), chrome={innerHTML:''}, result={innerHTML:''}, count={textContent:''};
const frame={addEventListener(){},contentWindow:{StockRadarV2Bridge:{snapshot:()=>({data,selected:'005930',favorites:[]}),setSelectedSilently(){},helpers:{flowReasonLines:()=>['기존 저장 근거']}}}};
map.set('#rc-main',main);map.set('#rc-header',chrome);map.set('#rc-engine',frame);map.set('#rc-home-rows',result);map.set('#rc-home-count',count);
const doc={querySelector:k=>map.get(k),addEventListener:(k,f)=>(handlers.doc[k]??=[]).push(f),visibilityState:'visible',activeElement:null};
const window={addEventListener:(k,f)=>handlers.win[k]=f,scrollTo(){}}, location={href:'https://example.com/stock-radar-research.html'};
const history={pushState(a,b,url){route.push(location.href);location.href=url.href}};
const localStorage={getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v)};
const sandbox=vm.createContext({window,document:doc,URL,location,history,localStorage,Date,console,setInterval(){},fetch:async()=>({ok:true,json:async()=>read('stock-green-review.json')})});
for(const f of ['market','company','evidence','chart',''])vm.runInContext(code('radar-cohesive'+(f?'-'+f:'')+'.js'),sandbox);
function dispatch(type,el){for(const f of handlers.doc[type]||[])f({type,target:el,preventDefault(){}})}
function click(dataset){dispatch('click',{dataset,closest(){return this},hasAttribute(name){return name==='data-rcm-sector'&&'rcmSector' in dataset}})}
assert.equal((chrome.innerHTML.match(/data-rc-country/g)||[]).length,10);
assert.equal((chrome.innerHTML.match(/class="rc-index"/g)||[]).length,4);
assert.match(main.innerHTML,/오늘의 매수후보 검토/);
assert.match(main.innerHTML,/검토용 · 후보 미충족/);
const c1=main.innerHTML.match(/rc-candidate-info"><div><h3>(.*?)</)?.[1];click({rcChoice:'1'});const c2=main.innerHTML.match(/rc-candidate-info"><div><h3>(.*?)</)?.[1];assert(c1&&c2&&c1!==c2);
dispatch('input',{id:'rc-home-search',value:'005930'});assert.match(result.innerHTML,/삼성전자/);
click({rcStar:'005930'});assert.deepEqual(JSON.parse(store.get('radar-v8-stars')),['005930']);assert.match(main.innerHTML,/관심기업 해제/);
click({rcStock:'005930'});assert.match(main.innerHTML,/<h1>질적 분석<\/h1>/);assert.match(location.href,/stock=005930/);
for(const [key,title,needle] of [['finance','재무',/영업현금흐름/],['value','가치·전망',/전망을 구분/],['filings','공시',/전체 공시/],['chart','차트',/판단선/]]){
 click({rcTab:key});assert(main.innerHTML.includes('<h1>'+title+'</h1>'));assert.match(main.innerHTML,/삼성전자/);assert.match(main.innerHTML,needle);assert(!/\bNaN\b|\bInfinity\b|href="javascript:/.test(main.innerHTML));
}
location.href=route.pop();handlers.win.popstate();assert.match(main.innerHTML,/<h1>공시<\/h1>/);
click({rcTab:'market'});assert.match(main.innerHTML,/산업 비교/);assert.match(main.innerHTML,/기업 선택/);
const s=data.raw.companies.find(c=>c.symbol==='005930').sector;click({rcmSector:s});assert.match(main.innerHTML,new RegExp('선택 산업: '+s));
click({rcCountry:'JP'});assert(!main.innerHTML.includes('삼성전자'));assert.match(main.innerHTML,/이 시장|일치하는 산업|기업 미선택/);
click({rcCountry:'KR'});click({rcTab:'home'});assert.match(main.innerHTML,/관심기업 해제/);
const actual=data.raw.companies.find(c=>c.symbol==='005930').history.operating_margin;
const candidate=main.innerHTML.match(/rc-candidate-info"><div><h3>(.*?)</)?.[1];
if(candidate==='삼성전자'&&Number.isFinite(actual))assert(main.innerHTML.includes(actual.toLocaleString('ko-KR',{maximumFractionDigits:2})+'%'));
click({rcStar:'005930'});assert.deepEqual(JSON.parse(store.get('radar-v8-stars')),[]);
console.log('PASS: stored feed integration, seven screens, 4 indices / 10 countries, candidate rotation, Korea ticker search, favorites, selection carryover, sector filter and history');

const H=window.RadarCohesive, now=Date.parse('2026-11-19T16:20:00+09:00');
const mk=(title,url,t='2026-11-19T15:00:00+09:00',extra={})=>({region:'kr',topic_class:'market',published_at:t,title,url,...extra});
const headlines=H.homeHeadlines({country:'KR',data:{newsLink:{items:[
 mk('실제 관련 뉴스 1','https://a.example/read?id=1&utm_source=x'), mk('실제 관련 뉴스 1','https://b.example/story'),
 mk('실제 관련 뉴스 2','https://a.example/read?id=2'), mk('수능 부정행위','https://a.example/unrelated'),
 mk('미래','https://a.example/future','2026-11-20T09:00:00+09:00'),
 mk('미연결','javascript:alert(1)'), mk('전일 지수','https://a.example/yesterday','2026-11-18T15:00:00+09:00'),
 mk('별도 국가','https://a.example/us','2026-11-19T15:00:00+09:00',{region:'us'})
]}}},now);
assert.deepEqual(Array.from(headlines,x=>x.title),['실제 관련 뉴스 1','실제 관련 뉴스 2','전일 지수']);
assert.deepEqual(Array.from(headlines,x=>x.day),['2026-11-19','2026-11-19','2026-11-18']);
const qday='2026-11-19', c=(symbol,sector,ret,price_session=qday)=>({market:'KR',symbol,sector,ret,price_session});
const board=H.industryWatch({country:'KR',helpers:{change:x=>x.ret},data:{raw:{companies:[c('A','전자',1),c('B','전자',4),c('C','전자',-1),c('D','전자',999,'2026-11-18'),c('B','전자',999),c('E','금융',null),c('F','분류 미확인',100)]}}});
assert.equal(board.day,qday);
assert.deepEqual(Array.from(board.rows,x=>[x.s,x.total,x.prices.length]),[['전자',3,3],['금융',1,0]]);
console.log('PASS: home news topical, safe, deduplicated and KST dates; industry same-session verified sample only');
