/* Full-universe UI contracts. Synthetic rows test invariants, never financial evidence. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {performance}=require('node:perf_hooks');
const POLICY='kr-six-character-alphanumeric-v2';
const NOW=Date.parse('2026-11-06T08:00:00Z');
const generated='2026-11-06T07:30:00Z',catalogTime='2026-11-06T03:24:32Z';
const kr=(symbol='0001A0',name='검증 한국 기업')=>({country:'KR',symbol,name,exchange:'KOSDAQ',source_symbol:symbol});
const us=(symbol='KO',name='Verified US issuer')=>({country:'US',symbol,name,exchange:'NYSE'});
function record(item,overrides={}){
 const provider=item.country==='KR'?item.symbol+(item.exchange==='KOSDAQ'?'.KQ':'.KS'):item.symbol.replace('.','-');
 return {symbol:provider,provider_symbol:provider,market:item.country,catalog_symbol:item.symbol,
  catalog_name:item.name,catalog_exchange:item.exchange,name:item.name,identity_verified:true,source_identity_policy:POLICY,
  status:'research_prediction',mode:'daily',direction:'up',probabilities:{up:.5,flat:.3,down:.2},
  issued_at:'2026-11-06T07:00:00Z',received_at:'2026-11-06T06:59:00Z',observed_until:'2026-11-05T21:00:00Z',
  target:{start:'2026-11-09T00:00:00Z',end:'2026-11-09T06:30:00Z'},
  collection_status:'fetched',source_collection_attempted:true,price_available:true,
  source_identity_verified:true,source_response_symbol:provider,
  price_provenance:{provider_symbol:provider,history_sha256:'a'.repeat(64),source_sha256:'b'.repeat(64),
   fetched_at:'2026-11-06T06:58:00Z',last_session:'2026-11-05'},...overrides};
}
const noCall=(item,extra={})=>record(item,{status:'no_call',probabilities:null,target:null,direction:null,...extra});
function fixture(items,records,raw=[]){
 const skipped=records.filter(r=>['deadline_skipped','circuit_skipped'].includes(r.collection_status)).length;
 const prediction=records.filter(r=>r.status==='research_prediction').length,failed=records.length-prediction-skipped;
 return {selected:items[0].country+':'+items[0].symbol,market:'ALL',screen:'stocks',favorites:[],data:{
  catalog:{identifier_policy:POLICY,generated_at:catalogTime,items,counts:{total:items.length}},
  raw:{companies:raw},direction:{generated_at:generated,records:[]},
  extended:{version:'stock-extended-direction-v1',source_identity_policy:POLICY,source_catalog_generated_at:catalogTime,
   generated_at:generated,generation_mode:'full_universe',automatic_orders:false,records,
   coverage:{total:items.length,attempted:prediction+failed,prediction,no_call:failed+skipped,failed,not_attempted:skipped,
    price_available:records.filter(r=>r.price_available===true).length,manifest_complete:true,coverage_complete:skipped===0},
   run:{attempted:prediction+failed,research_prediction:prediction,no_call:failed,not_attempted:skipped,
    started_at:'2026-11-06T06:55:00Z',completed_at:generated}}}};
}
function runtime(ctx){
 let clock=NOW;
 class Clock extends Date{constructor(...args){super(...(args.length?args:[clock]))}static now(){return clock}}
 const listeners={};
 const sandbox={URL,Date:Clock,console,localStorage:{getItem(){return null}},window:{},document:{readyState:'loading',
  addEventListener(kind,fn){(listeners[kind]??=[]).push(fn)},getElementById(){return null}}};
 sandbox.window.StockRadarV2Bridge={snapshot:()=>ctx,helpers:{},render(){}};
 vm.createContext(sandbox);
 for(const filename of ['stock-catalog-ui.js','stock-radar-flow-v2.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../assets',filename),'utf8'),sandbox);
 return {ui:sandbox.window.StockRadarFlowV2,catalog:sandbox.window.StockCatalogUI,clock:value=>clock=value,
  selected:id=>sandbox.window.StockCatalogUI.resolve(id,ctx),ctx};
}
const plain=value=>JSON.parse(JSON.stringify(value));
let checks=0;
function test(name,fn){fn();checks++;console.log('PASS',name)}

test('Canonical share class and provider alias join one raw company and one forecast',()=>{
 const item=us('MOG.A','Moog Class A'),ctx=fixture([item],[record(item)],[{market:'US',symbol:'MOG-A',name:'Moog source',price:123}]);
 const {ui,catalog}=runtime(ctx),c=catalog.resolve('US:MOG.A',ctx);
 assert.equal(catalog.universe(ctx).length,1);assert.equal(catalog.selectionId(c),'MOG-A');
 assert.equal(ui.signal(c,ctx).value,.5);assert.equal(ui.forecastMeta(ctx).modeled,1);assert.equal(ui.forecastMeta(ctx).active,1);
});
test('Exact country keys never attach another market or an unqualified forecast',()=>{
 const a=kr('ABC123'),b=us('ABC123'),ctx=fixture([a,b],[record(a)]),{ui,selected}=runtime(ctx);
 assert.equal(ui.signal(selected('KR:ABC123'),ctx).active,true);
 assert.equal(ui.signal(selected('US:ABC123'),ctx).r,null);
 ctx.data.direction={records:[{...record(b),market:undefined,country:undefined}]};
 assert.equal(ui.signal(selected('US:ABC123'),ctx).r,null);
});
test('Wrong KR venue, other US share class and false issuer name fail exact identity binding',()=>{
 for(const patch of [{symbol:'0001A0.KS',provider_symbol:'0001A0.KS'},{catalog_name:'Different issuer'},{catalog_exchange:'KOSPI'},{identity_verified:false}]){
  const item=kr(),ctx=fixture([item],[record(item,patch)]),{ui,selected}=runtime(ctx);
  assert.equal(ui.signal(selected('KR:0001A0'),ctx).r,null);assert.equal(ui.coverage(ctx).valid,false);
 }
 const item=us('BRK.B'),ctx=fixture([item],[record(item,{symbol:'BRK-A',provider_symbol:'BRK-A'})]),{ui,selected}=runtime(ctx);
 assert.equal(ui.signal(selected('US:BRK.B'),ctx).r,null);
});
test('Unsupported provider spelling remains a terminal no-call under its original identity',()=>{
 const item=us('TEST$A'),ctx=fixture([item],[noCall(item,{symbol:item.symbol,provider_symbol:null,price_provenance:null,
  collection_status:'unsupported',error_kind:'unsupported_symbol',source_collection_attempted:false})]),{ui,selected}=runtime(ctx);
 const signal=ui.signal(selected('US:TEST$A'),ctx),coverage=ui.coverage(ctx);
 assert.match(signal.headline,/생성 불가.*미지원/);assert.equal(signal.value,null);
 assert.equal(coverage.prediction,0);assert.equal(coverage.failed,1);assert.equal(coverage.not_attempted,0);assert.equal(coverage.valid,true);
});
test('No result, skipped work and a completed unsuccessful attempt have distinct Korean states',()=>{
 const items=[us('PENDING'),us('SHORT'),us('ABSENT')],ctx=fixture(items,[noCall(items[0],{collection_status:'deadline_skipped',error_kind:'deadline'}),
  noCall(items[1],{error_kind:'insufficient_history',reason:'fewer_than_500_daily_training_samples'})]);
 const {ui,selected}=runtime(ctx);
 assert.match(ui.signal(selected('US:PENDING'),ctx).headline,/미처리.*시간 제한/);
 assert.match(ui.signal(selected('US:SHORT'),ctx).headline,/생성 불가.*가격 이력 부족/);
 assert.match(ui.signal(selected('US:ABSENT'),ctx).headline,/미처리.*결과 대기/);
 for(const item of items)assert.equal(ui.signal(selected('US:'+item.symbol),ctx).value,null);
 assert.equal(ui.coverage(ctx).valid,false);assert.equal(ui.coverage(ctx).missing,1);
});
test('Current generation counters partition all official identities without counting old cached predictions',()=>{
 const items=[us('NEW'),us('SHORT'),us('WAIT')],ctx=fixture(items,[record(items[0],{collection_status:'cache_current',source_collection_attempted:false}),
  noCall(items[1],{error_kind:'insufficient_history'}),noCall(items[2],{collection_status:'circuit_skipped',error_kind:'provider_circuit_open'})]);
 const {ui}=runtime(ctx),out=ui.coverage(ctx);
 assert.equal(out.valid,true);assert.equal(out.complete,false);
 assert.deepEqual([out.total,out.prediction,out.failed,out.not_attempted,out.attempted],[3,1,1,1,2]);
 const html=ui.render();assert.match(html,/data-fx-coverage="prediction">1<\/b>/);assert.match(html,/생성 불가/);assert.match(html,/미처리/);
 assert.match(html,/가격 이력 부족/);assert.match(html,/수집 대기/);assert.match(html,/기준/);
});
test('False completeness, mismatched counts and a changed catalogue cannot claim a completed current run',()=>{
 for(const mutate of [ctx=>ctx.data.extended.coverage.prediction++,ctx=>ctx.data.extended.run.no_call++,
  ctx=>ctx.data.extended.source_catalog_generated_at='different',ctx=>ctx.data.extended.coverage.coverage_complete=false,
  ctx=>ctx.data.extended.coverage.manifest_complete=false,ctx=>ctx.data.extended.coverage.price_available++,
  ctx=>ctx.data.extended.run.completed_at='2026-11-06T09:00:00Z',
  ctx=>ctx.data.extended.run.started_at='2026-11-06T07:01:00Z']){
  const item=us(),ctx=fixture([item],[record(item)]);mutate(ctx);const {ui}=runtime(ctx);
  assert.equal(ui.coverage(ctx).valid,false);assert.match(ui.render(),/집계·명부 일치 확인 필요/);
  assert.match(ui.render(),/data-fx-coverage="prediction">확인 전/);
 }
});
test('Duplicate extended identities are excluded instead of choosing arbitrary output',()=>{
 const item=us(),ctx=fixture([item],[record(item),record(item,{probabilities:{up:.1,flat:.2,down:.7},direction:'down'})]);
 const {ui,selected}=runtime(ctx);assert.equal(ui.signal(selected('US:KO'),ctx).r,null);
 assert.equal(ui.coverage(ctx).valid,false);assert.equal(ui.coverage(ctx).invalid,2);
});
test('Full-universe percentages require independently verified price provenance',()=>{
 const item=us();for(const patch of [{price_available:false},{source_identity_verified:false},
  {source_response_symbol:'ANOTHER'},{price_provenance:null},
  {price_provenance:{provider_symbol:'KO',history_sha256:'a'.repeat(64),source_sha256:'bad',fetched_at:'2026-11-06T06:58:00Z'}},
  {price_provenance:{provider_symbol:'KO',history_sha256:'a'.repeat(64),source_sha256:'b'.repeat(64),fetched_at:'2026-11-06T07:01:00Z'}}]){
  const ctx=fixture([item],[record(item,patch)]),{ui,selected}=runtime(ctx);
  assert.equal(ui.signal(selected('US:KO'),ctx).active,false);assert.equal(ui.coverage(ctx).valid,false);
 }
});
test('Malformed probabilities, future issue clocks and future input timestamps never show percentages',()=>{
 const item=us();
 for(const patch of [{probabilities:{up:.5,flat:.5,down:.5}},{probabilities:{up:true,flat:0,down:0}},
  {probabilities:{up:NaN,flat:.3,down:.2}},{issued_at:'2026-11-06T09:00:00Z'},
  {received_at:'2026-11-06T07:01:00Z'},{observed_until:'2026-11-06T07:01:00Z'}]){
  const ctx=fixture([item],[record(item,patch)]),{ui,catalog,selected}=runtime(ctx),c=selected('US:KO');
  assert.equal(ui.signal(c,ctx).active,false);assert.equal(ui.signal(c,ctx).value,null);
  assert.doesNotMatch(catalog.profile(c,ctx).match(/fx-catalog-preview-core[\s\S]*?<\/div>/)[0],/\d[.,\d]*%/);
 }
});
test('An active core call survives a newer no-call and an active extended call supersedes expired core data',()=>{
 const item=us(),ctx=fixture([item],[record(item,{probabilities:{up:.7,flat:.2,down:.1}})]),{ui,selected}=runtime(ctx),c=selected('US:KO');
 ctx.data.direction={records:[record(item,{probabilities:{up:.6,flat:.2,down:.2}}),noCall(item,{issued_at:'2026-11-06T07:20:00Z'})]};
 assert.equal(ui.signal(c,ctx).value,.6);
 ctx.data.direction={records:[record(item,{issued_at:'2026-11-04T07:00:00Z',received_at:undefined,observed_until:undefined,
  target:{start:'2026-11-05T00:00:00Z',end:'2026-11-05T06:30:00Z'}})]};
 assert.equal(ui.signal(c,ctx).value,.7);
});
test('Clock advance expires both the selected signal and its cached coverage meta',()=>{
 const item=us(),ctx=fixture([item],[record(item)]),{ui,selected,clock}=runtime(ctx),c=selected('US:KO');
 assert.equal(ui.forecastMeta(ctx).active,1);clock(Date.parse('2026-11-09T06:30:01Z'));
 assert.equal(ui.signal(c,ctx).active,false);assert.equal(ui.forecastMeta(ctx).active,0);
 assert.match(ui.signal(c,ctx).headline,/기간 종료/);
});
test('Snapshot replacement and array append/remove invalidate forecast indices',()=>{
 const a=us('AAA'),b=us('BBB'),ctx=fixture([a,b],[record(a)]),{ui,selected}=runtime(ctx);
 assert.equal(ui.signal(selected('US:BBB'),ctx).r,null);
 ctx.data.extended.records.push(record(b));assert.equal(ui.signal(selected('US:BBB'),ctx).active,true);
 ctx.data.extended.records.pop();assert.equal(ui.signal(selected('US:BBB'),ctx).r,null);
 ctx.data.extended={...ctx.data.extended,records:[record(b)]};assert.equal(ui.signal(selected('US:AAA'),ctx).r,null);
});
test('8,600 identities are indexed once and repeated lookups stay linear in records',()=>{
 const items=Array.from({length:8600},(_,i)=>kr(String(100000+i),'Scale issuer '+i));
 let visits=0;const records=new Proxy(items.map(item=>record(item)),{get(target,prop,receiver){if(/^\d+$/.test(String(prop)))visits++;return Reflect.get(target,prop,receiver)}});
 const ctx=fixture(items,records),{ui,catalog}=runtime(ctx);visits=0;const start=performance.now();
 const companies=catalog.universe(ctx);for(const c of companies)assert.equal(ui.signal(c,ctx).active,true);
 assert.equal(ui.forecastMeta(ctx).active,items.length);assert.equal(ui.coverage(ctx).prediction,items.length);
 for(const c of companies)assert.equal(ui.signal(c,{...ctx}).active,true);
 assert.ok(visits<=records.length*3,'record element reads '+visits+' exceed linear bound');
 console.log('SCALE_DIAGNOSTIC',JSON.stringify({identities:items.length,recordElementReads:visits,elapsedMs:Math.round(performance.now()-start)}));
});
test('Current saved raw/catalogue union handles MOG-A without manufacturing a second company',()=>{
 const root=process.env.RADAR_DATA_DIR||path.join(__dirname,'..');
 const catalog=JSON.parse(fs.readFileSync(path.join(root,'stock-universe-catalog.json'),'utf8'));
 const raw=JSON.parse(fs.readFileSync(path.join(root,'stock-opportunity-data.json'),'utf8'));
 const ctx={data:{catalog,raw},favorites:[],market:'ALL'}, {catalog:ui}=runtime(ctx);
 const original=raw.companies.find(r=>r.symbol==='MOG-A');
 if(original&&catalog.items.some(r=>r.country==='US'&&r.symbol==='MOG.A')){
  const matches=ui.universe(ctx).filter(c=>c.universe_key==='US:MOG.A');assert.equal(matches.length,1);
  assert.equal(ui.resolve('US:MOG.A',ctx).price,original.price);
 }
 const known=new Set(catalog.items.map(r=>r.country+':'+r.symbol));
 const extras=raw.companies.filter(r=>!known.has(r.market+':'+r.symbol.replace(/\.(KS|KQ)$/,''))&&
  !(r.market==='US'&&known.has('US:'+r.symbol.replace('-','.'))));
 assert.equal(ui.universe(ctx).length,catalog.items.length+extras.length);
});
const bridge=fs.readFileSync(path.join(__dirname,'../assets/stock-radar-clean-bridge.js'),'utf8');
const freshnessStart=bridge.indexOf('function extendedForecastFreshness('),freshnessEnd=bridge.indexOf('\nfunction ageMinutes(',freshnessStart);
assert.ok(freshnessStart>0&&freshnessEnd>freshnessStart);
const freshness=new Function(bridge.slice(freshnessStart,freshnessEnd)+';return extendedForecastFreshness')();
test('Daily full-universe cadence does not inherit the rolling four-hour warning',()=>{
 const item=us(),feed=fixture([item],[record(item)]).data.extended;
 const current=freshness(feed,Date.parse('2026-11-06T16:00:00Z'));
 assert.equal(current.warning,null);assert.equal(current.active,1);assert.equal(current.nextDue,'2026-11-09T06:55:00.000Z');
 assert.equal(freshness({...feed,generation_mode:undefined,coverage:undefined},Date.parse('2026-11-06T16:00:00Z')).rollingDelayed,true);
});
test('Actual target expiry stays separate from weekend cadence and delayed next publication',()=>{
 const item=us(),feed=fixture([item],[record(item)]).data.extended;
 const expired=freshness(feed,Date.parse('2026-11-09T07:00:00Z'));
 assert.equal(expired.active,0);assert.equal(expired.warning,null);assert.match(expired.note,/기간 종료.*다음 발행/);
 assert.match(freshness(feed,Date.parse('2026-11-09T10:00:01Z')).warning,/일간 갱신 지연/);
 assert.match(freshness({...feed,generated_at:'2026-11-10T07:30:00Z'},NOW).warning,/기준시각 확인/);
 assert.match(bridge,/if\(ai>75&&researchHours\)/);
});
console.log('FORECAST_COVERAGE_UI_PASS',checks);
