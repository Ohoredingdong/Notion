/* Shared selection/model regressions. Fixtures are not financial evidence. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../assets/stock-catalog-ui.js'),'utf8');
const plain=value=>JSON.parse(JSON.stringify(value));
function runtime(){
 const handlers={};
 const sandbox={window:{},URL,document:{addEventListener(kind,fn){(handlers[kind]??=[]).push(fn)},getElementById(){return null}}};
 vm.runInNewContext(source,sandbox);
 return {ui:sandbox.window.StockCatalogUI,window:sandbox.window,handlers};
}
function fixture(){
 const items=[
  {country:'KR',symbol:'005930',name:'삼성전자',exchange:'KOSPI'},
  {country:'KR',symbol:'0001A0',name:'덕양에너젠',exchange:'KOSDAQ',source:'KRX KIND',source_url:'https://kind.krx.co.kr/corpgeneral/corpList.do'},
  {country:'KR',symbol:'000250',name:'삼천당제약',exchange:'KOSDAQ'},
  {country:'US',symbol:'AAPL',name:'Apple Inc. Common Stock',exchange:'NASDAQ'},
  {country:'US',symbol:'KO',name:'Coca-Cola Company Common Stock',exchange:'NYSE'},
  {country:'US',symbol:'BRK.B',name:'Berkshire Hathaway Inc. Class B',exchange:'NYSE'}];
 const raw={companies:[
  {symbol:'005930',name:'Samsung source alias',market:'KR',price:201500,currency:'KRW',history:{revenue:123}},
  {symbol:'AAPL',name:'Apple',market:'US',price:100,currency:'USD'},
  {symbol:'YMM',name:'Existing source outside directory',market:'US',price:5},
  {symbol:'SSL',name:'Another existing source',market:'US',price:7}]};
 const catalog={identifier_policy:'kr-six-character-alphanumeric-v2',generated_at:'2026-11-05T12:00:00Z',items,counts:{total:6,KR:3,US:3}};
 const records={};
 for(const item of items.filter(x=>x.country==='KR'))records['KR:'+item.symbol]={country:'KR',symbol:item.symbol,catalog_name:item.name,
  identity_verified:true,corp_code:'12345678',status:'available',currency:'KRW',source:'DART periodic reports',
  source_url:'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=fixture',period_end:'2026-06-30',metrics:{revenue:123456789},checked_at:catalog.generated_at};
 return {selected:'005930',favorites:[],data:{raw,catalog,financial:{identity_policy:'official-issuer-identity-v2',catalog_generated_at:catalog.generated_at,financial_available:{KR:3,US:0},records}}};
}
function freezeDeep(value){if(value&&typeof value==='object'){Object.values(value).forEach(freezeDeep);Object.freeze(value)}return value}
let checks=0;
function check(name,fn){fn();checks++;console.log('PASS',name)}

check('Raw order, original symbols and values survive the catalogue union without source mutation',()=>{
 const {ui}=runtime(),ctx=fixture(),before=JSON.stringify(ctx.data);
 freezeDeep(ctx.data.raw);freezeDeep(ctx.data.catalog);
 const list=ui.universe(ctx);
 assert.deepEqual(Array.from(list.slice(0,4),ui.selectionId),['005930','AAPL','YMM','SSL']);
 assert.equal(list.length,8);assert.equal(list[0].price,201500);assert.notEqual(list[0],ctx.data.raw.companies[0]);
 assert.equal(list[0].history,ctx.data.raw.companies[0].history);
 assert.equal(list[0].catalog_entry,ctx.data.catalog.items[0]);assert.equal(list[2].catalog_entry,null);
 assert.equal(JSON.stringify(ctx.data),before);
});
check('Official count and additional raw-only rows have separate numeric counts',()=>{
 const {ui}=runtime(),ctx=fixture();
 assert.equal(ui.count(ctx),6);assert.deepEqual(plain(ui.info(ctx)),{official:6,total:8,tracked:4,extra:2});
 assert.match(ui.panel(ctx),/공식 명부 6건 \+ 명부 미포함 기존 분석 2건/);
});
check('Raw and catalogue references cache one model; source replacement invalidates it',()=>{
 const {ui}=runtime(),ctx=fixture(),first=ui.universe(ctx);
 assert.equal(ui.universe({...ctx,selected:'US:KO'}),first);
 ctx.data.financial={...ctx.data.financial};assert.equal(ui.universe(ctx),first);
 ctx.data.raw={...ctx.data.raw};const next=ui.universe(ctx);assert.notEqual(next,first);
 ctx.data.catalog={...ctx.data.catalog};assert.notEqual(ui.universe(ctx),next);
});
check('Appending or removing rows in the same raw and catalogue arrays refreshes selection',()=>{
 const {ui}=runtime(),ctx=fixture(),first=ui.universe(ctx);
 ctx.data.raw.companies.push({symbol:'TEST-BAD',market:'US',name:'Injected raw fixture'});
 const appended=ui.universe(ctx),raw=ui.resolve('TEST-BAD',ctx);
 assert.notEqual(appended,first);assert.equal(appended.length,first.length+1);
 assert.equal(raw.catalog_only,false);assert.equal(ui.resolve(ui.selectionId(raw),ctx),raw);
 ctx.data.raw.companies.pop();assert.equal(ui.resolve('TEST-BAD',ctx),null);
 assert.equal(ui.universe(ctx).length,first.length);
 ctx.data.catalog.items.push({country:'US',symbol:'TEST-CATALOG',name:'Appended catalogue fixture',exchange:'NYSE'});
 const catalog=ui.resolve('US:TEST-CATALOG',ctx);
 assert.equal(catalog.catalog_only,true);assert.equal(ui.resolve(ui.selectionId(catalog),ctx),catalog);
 assert.equal(ui.universe(ctx).length,first.length+1);
 ctx.data.catalog.items.pop();assert.equal(ui.resolve('US:TEST-CATALOG',ctx),null);
 assert.equal(ui.universe(ctx).length,first.length);
});
check('Canonical, legacy, alphanumeric Korean and unique provider aliases resolve one identity',()=>{
 const {ui}=runtime(),ctx=fixture();
 for(const alias of ['005930','KR:005930','005930.KS'])assert.equal(ui.resolve(alias,ctx).universe_key,'KR:005930');
 for(const alias of ['0001A0','kr:0001a0','0001A0.KQ','KR:0001A0.KQ'])assert.equal(ui.resolve(alias,ctx).universe_key,'KR:0001A0');
 assert.equal(ui.selectionId(ui.resolve('0001A0',ctx)),'KR:0001A0');
 assert.equal(ui.resolve('000010',ctx),null);assert.equal(ui.resolve('0001A0.KS',ctx),null);
 for(const alias of ['BRK.B','US:BRK.B','BRK-B'])assert.equal(ui.resolve(alias,ctx).universe_key,'US:BRK.B');
});
check('A unique provider-form raw ticker joins the canonical share class without duplicate rows',()=>{
 const {ui}=runtime(),ctx=fixture();ctx.data.raw={companies:[{symbol:'BRK-B',market:'US',name:'Provider name',price:123}]};
 ctx.data.catalog={...ctx.data.catalog,items:[ctx.data.catalog.items.at(-1)]};
 const rows=ui.universe(ctx);assert.equal(rows.length,1);assert.equal(rows[0].catalog_only,false);
 assert.equal(ui.selectionId(rows[0]),'BRK-B');assert.equal(rows[0].universe_key,'US:BRK.B');
 assert.equal(ui.catalogItem(rows[0],ctx),ctx.data.catalog.items[0]);
});
check('Cross-country bare collisions reject ambiguous selection and every row still round-trips',()=>{
 const {ui}=runtime(),ctx=fixture();
 ctx.data.raw={companies:[{symbol:'ABC123',market:'KR',name:'Korean source'},{symbol:'ABC123',market:'US',name:'US source'}]};
 ctx.data.catalog={...ctx.data.catalog,items:[{country:'KR',symbol:'ABC123',name:'한국 법인',exchange:'KOSPI'},{country:'US',symbol:'ABC123',name:'US issuer',exchange:'NASDAQ'}]};
 const rows=ui.universe(ctx);assert.equal(ui.resolve('ABC123',ctx),null);
 for(const c of rows){assert.equal(ui.selectionId(c),c.universe_key);assert.equal(ui.resolve(ui.selectionId(c),ctx),c)}
 assert.notEqual(ui.resolve('KR:ABC123',ctx),ui.resolve('US:ABC123',ctx));
});
check('An ambiguous provider alias does not erase distinct qualified catalogue entries',()=>{
 const {ui}=runtime(),ctx=fixture();ctx.data.raw={companies:[]};
 ctx.data.catalog={...ctx.data.catalog,items:[{country:'US',symbol:'BRK.B',name:'First',exchange:'NYSE'},{country:'US',symbol:'BRK-B',name:'Second',exchange:'NYSE'}]};
 assert.equal(ui.resolve('BRK-B',ctx),null);
 assert.equal(ui.resolve('US:BRK.B',ctx).name,'First');assert.equal(ui.resolve('US:BRK-B',ctx).name,'Second');
});
check('Search includes raw name, official name and aliases without matching exchange labels',()=>{
 const {ui}=runtime(),ctx=fixture(),c=ui.resolve('005930',ctx),text=ui.searchText(c);
 for(const token of ['samsung source alias','삼성전자','005930','005930.ks'])assert.ok(text.includes(token));
 assert.ok(!text.includes('kospi'));assert.ok(!ui.searchText(ui.resolve('0001A0',ctx)).includes('kosdaq'));
 assert.ok(ui.searchText(ui.resolve('US:BRK.B',ctx)).includes('brk-b'));
});
check('Official statement identity uses the original catalogue name, not the raw display alias',()=>{
 const {ui}=runtime(),ctx=fixture(),c=ui.resolve('005930',ctx),item=ui.catalogItem(c,ctx);
 assert.equal(item,ctx.data.catalog.items[0]);assert.equal(c.name,'Samsung source alias');
 assert.equal(ui.statement(c,ctx),null);assert.ok(ui.statement(item,ctx));
});
check('Invalid catalogue policy falls back to preserved raw entries without falsely attaching finance',()=>{
 const {ui}=runtime(),ctx=fixture();ui.universe(ctx);delete ctx.data.catalog.identifier_policy;
 assert.equal(ui.count(ctx),0);assert.equal(ui.universe(ctx).length,4);
 assert.equal(ui.catalogItem(ui.resolve('005930',ctx),ctx),null);assert.equal(ui.resolve('0001A0',ctx),null);
});
check('Catalogue-only profile shows real statement and source links while quotes remain unavailable',()=>{
 const {ui}=runtime(),ctx=fixture(),c=ui.resolve('0001A0',ctx),html=ui.profile(c,ctx);
 assert.equal(c.price,null);assert.equal(c.currency,null);assert.equal(c.forecasts,undefined);
 assert.match(html,/class="fx-panel fx-catalog-preview" aria-label="선택 기업 종합 분석"/);
 assert.match(html,/<h3>덕양에너젠<\/h3>/);assert.match(html,/0001A0/);assert.match(html,/fx-catalog-finance/);
 assert.match(html,/DART periodic reports/);assert.match(html,/https:\/\/dart\.fss\.or\.kr/);assert.match(html,/https:\/\/kind\.krx\.co\.kr/);
 const quote=html.match(/<div class="fx-catalog-preview-info fx-catalog-quote">[\s\S]*?<\/div>/)[0];
 assert.match(quote,/저장 종가 미확인 · 차트 미수집/);assert.doesNotMatch(quote,/\d/);
 assert.match(html,/data-nr-detail="KR:0001A0"/);assert.match(html,/data-nr-star="KR:0001A0"/);
 assert.match(html,/data-catalog-back data-nr-screen="stocks"/);assert.equal(ui.profile(ui.resolve('005930',ctx),ctx),null);
});
check('Shared AI status controls profile percentages; no-call and expired records remain labelled',()=>{
 const {ui,window}=runtime(),ctx=fixture(),c=ui.resolve('US:KO',ctx);
 window.StockRadarFlowV2={signal:()=>({active:false,value:.99,status:'자료 부족',r:{status:'no_call'}})};
 let html=ui.profile(c,ctx);assert.match(html,/미발행 · 자료 대기/);assert.doesNotMatch(html,/99%/);
 window.StockRadarFlowV2.signal=()=>({active:false,stale:true,value:null,status:'기간 종료',r:{status:'research_prediction',issued_at:'past'}});
 assert.match(ui.profile(c,ctx),/기간 종료 · 과거 예측/);
 window.StockRadarFlowV2.signal=()=>({active:true,label:'상승',value:.7,status:'다음 거래기간 예측 · 연구용',r:{status:'research_prediction'}});
 assert.match(ui.profile(c,ctx),/상승 70%/);
});
check('Financial period/identity mismatch stays blocked after selecting from the common universe',()=>{
 const {ui}=runtime(),ctx=fixture(),c=ui.resolve('0001A0',ctx);
 ctx.data.financial.catalog_generated_at='mismatched';
 assert.doesNotMatch(ui.profile(c,ctx),/fx-catalog-finance-grid/);assert.match(ui.profile(c,ctx),/공식 재무제표: 아직 미확인/);
});
check('Legacy preview event delegates to common selection and focus has no private override',()=>{
 const {ui,window,handlers}=runtime(),ctx=fixture();let stopped=false,selected=null;
 window.StockRadarV2Bridge={snapshot:()=>ctx,select:id=>{selected=id;ctx.selected=id},render(){}};
 const button={dataset:{catalogPreview:'KR:0001A0'}};
 handlers.click[0]({target:{closest:()=>button},stopPropagation(){stopped=true}});
 assert.equal(selected,'KR:0001A0');assert.ok(stopped);assert.match(ui.focus(ctx),/덕양에너젠/);
 ctx.selected='AAPL';assert.equal(ui.focus(ctx),null);assert.equal(ui.getState().preview,null);
});
check('Source links and profile text cannot inject markup or non-HTTPS destinations',()=>{
 const {ui}=runtime(),ctx=fixture();ctx.data.catalog.items[1]={...ctx.data.catalog.items[1],name:'<img src=x>',source_url:'javascript:alert(1)'};
 const html=ui.profile(ui.resolve('0001A0',ctx),ctx);
 assert.doesNotMatch(html,/<img|href="javascript:/);assert.match(html,/&lt;img/);
});

const dataDir=process.env.RADAR_DATA_DIR||process.cwd();
if(fs.existsSync(path.join(dataDir,'stock-universe-catalog.json'))){
 const read=name=>JSON.parse(fs.readFileSync(path.join(dataDir,name),'utf8'));
 const ctx={favorites:[],data:{catalog:read('stock-universe-catalog.json'),raw:read('stock-opportunity-data.json'),financial:read('stock-financial-coverage.json')}};
 const {ui}=runtime();
 check('Actual source catalogue is selectable through the shared model with every issuer preserved',()=>{
  assert.equal(ctx.data.catalog.identifier_policy,'kr-six-character-alphanumeric-v2','Use current verified data via RADAR_DATA_DIR when local repo data is historical');
  const list=ui.universe(ctx),meta=ui.info(ctx);
  assert.equal(meta.official,ctx.data.catalog.items.length);assert.equal(meta.tracked,ctx.data.raw.companies.length);
  assert.equal(new Set(Array.from(list,c=>c.universe_key)).size,list.length);
  for(const item of ctx.data.catalog.items){const c=ui.resolve(item.country+':'+item.symbol,ctx);assert.ok(c,item.symbol);assert.equal(ui.catalogItem(c,ctx),item)}
  for(const c of list)assert.equal(ui.resolve(ui.selectionId(c),ctx),c);
  assert.ok(meta.official>1000);assert.ok(list.length>=meta.official);
  console.log('CATALOG_MODEL_ACTUAL',JSON.stringify(meta));
 });
 check('Actual verified finance outside the original raw cohort is displayed without invented quote fields',()=>{
  const candidate=ui.universe(ctx).find(c=>c.catalog_only&&['available','partial','stale'].includes(ui.statement(ui.catalogItem(c,ctx),ctx)?.status));
  assert.ok(candidate,'At least one actually verified catalogue-only statement is required');
  const report=ui.profile(candidate,ctx);assert.match(report,/fx-catalog-finance/);assert.match(report,/저장 종가 미확인/);
  assert.equal(candidate.price,null);assert.ok(ui.verifiedCount(ctx)>0);
 });
}
console.log('CATALOG_MODEL_PASS',checks);
