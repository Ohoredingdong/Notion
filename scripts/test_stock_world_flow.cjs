/* Deliberately synthetic adversarial fixtures; never written to a public feed. */
const assert=require('node:assert/strict');
const flow=require('../assets/stock-world-flow.js');
const now=Date.parse('2026-11-06T12:00:00Z');
const providers={kospi:'^KS11',kosdaq:'^KQ11',sp500:'^GSPC',nasdaq:'^IXIC',dax:'^GDAXI',shanghai:'000001.SS',nikkei225:'^N225',hang_seng:'^HSI',usdkrw:'KRW=X',dxy:'DX-Y.NYB',us10y:'BC_10YEAR',wti:'CL=F',gold:'GC=F',vix:'^VIX'};
function fixture(){
 return {version:flow.version,generated_at:'2026-11-06T11:00:00Z',status:'complete',regions:[],
  indicators:flow.config.map(([id,label,region,category,unit],index)=>{
   const previous=category==='yield'?4.1:100+index,value=previous+(category==='yield'?.03:1);
   return {id,label,region,category,unit,status:'current',value,previous_value:previous,
    change_value:value-previous,change_pct:category==='yield'?null:(value/previous-1)*100,
    change_bp:category==='yield'?(value-previous)*100:null,direction:'up',comparison_verified:true,
    quote_basis:category==='yield'?'treasury_par_yield':category==='index'?'exchange_regular_close':'provider_daily_close',
    session:'2026-11-05',previous_session:'2026-11-04',expected_session:'2026-11-05',
    observed_at:category==='index'?'2026-11-05T21:00:00Z':null,
    observed_at_precision:category==='index'?'exchange_close':'source_date',received_at:'2026-11-06T10:59:00Z',
    source:{provider:'TEST ONLY',url:'https://example.com/observation/'+id,provider_symbol:providers[id],response_symbol:providers[id],identity_verified:true,...(id==='us10y'?{field:'BC_10YEAR',source_unit:'percent'}:{})},
    freshness:{status:'current',next_expected_session:'2026-11-06',next_check_after:'2026-11-06T22:00:00Z'}};
  }),related_news:[{title:'TEST ONLY: reported market headline',url:'https://example.com/story',source:'TEST ONLY',published_at:'2026-11-06T10:00:00Z'}]};
}
function mutated(id,changes){const feed=fixture(),row=feed.indicators.find(row=>row.id===id);Object.assign(row,changes);return feed}
let count=0;
function test(name,fn){fn();count++;console.log('PASS',name)}
test('Fourteen observations produce six named regions, without a fabricated score',()=>{
 const result=flow.model(fixture(),now);assert.equal(result.current,14);assert.equal(result.available,6);assert.equal(result.counts.up,6);
 assert.equal(result.score,undefined);assert.match(result.scope,/독일 참고/);assert.match(flow.render({data:{worldFlow:fixture()}},now),/11\.05 기준 · 확인 14\/14/);
});
test('Yield uses percentage points and basis points, never percent return',()=>{
 const row=flow.model(fixture(),now).byId.us10y;assert.equal(row.changePct,null);assert(Math.abs(row.changeBp-3)<1e-10);
 assert.equal(flow.changeText(row),'+3bp');assert.match(flow.valueText(row),/4\.13 %/);
 const bad=mutated('us10y',{change_bp:.03});assert.equal(flow.model(bad,now).byId.us10y.current,false);
});
test('Price returns are independently recomputed from the same two observations',()=>{
 const row=flow.model(fixture(),now).byId.kospi;assert.equal(row.change,1);assert(Math.abs(row.changePct-1)<1e-10);
 assert.equal(flow.model(mutated('kospi',{change_pct:12}),now).byId.kospi.current,false);
 assert.equal(flow.model(mutated('kospi',{change_value:12}),now).byId.kospi.current,false);
 assert.equal(flow.model(mutated('kospi',{direction:'down'}),now).byId.kospi.current,false);
});
test('Booleans, strings, null and nonfinite values are not prices',()=>{
 for(const value of [true,'101',null,NaN,Infinity]){const row=flow.model(mutated('kospi',{value}),now).byId.kospi;assert.equal(row.value,null);assert.equal(row.current,false)}
});
test('Provider identity, quote units and source links are required',()=>{
 let feed=fixture(),row=feed.indicators[0];row.source.response_symbol='OTHER';assert.equal(flow.model(feed,now).byId.kospi.value,null);
 feed=fixture();feed.indicators[0].source.identity_verified=false;assert.equal(flow.model(feed,now).byId.kospi.current,false);
 feed=fixture();Object.assign(feed.indicators[0].source,{provider_symbol:'^GSPC',response_symbol:'^GSPC'});assert.equal(flow.model(feed,now).byId.kospi.value,null);
 feed=fixture();feed.indicators[0].source.url='javascript:alert(1)';assert.equal(flow.model(feed,now).byId.kospi.value,null);
 assert.equal(flow.model(mutated('usdkrw',{unit:'USD_per_KRW'}),now).byId.usdkrw.value,null);
});
test('Missing comparison proof never becomes a daily percentage',()=>{
 for(const change of [{comparison_verified:false},{previous_session:'2026-11-05'},{previous_value:0},{previous_session:'2026-02-30'}]){
  const row=flow.model(mutated('kospi',change),now).byId.kospi;assert.equal(row.current,false);assert.equal(row.changePct,null);assert.equal(row.value,101);
 }
});
test('Future and invalid observation clocks cannot supply current values',()=>{
 for(const change of [{received_at:'2026-11-07T10:00:00Z'},{observed_at:'2026-11-07T10:00:00Z'},{observed_at_precision:'unknown'},{session:'2026-02-30'}])
  assert.equal(flow.model(mutated('kospi',change),now).byId.kospi.value,null);
 const feed=fixture();feed.generated_at='2026-11-07T12:00:00Z';assert.equal(flow.model(feed,now).current,0);
});
test('Date-only Treasury observation never acquires an invented close time',()=>{
 const row=flow.model(fixture(),now).byId.us10y;assert.equal(row.raw.observed_at,null);
 assert.equal(flow.observationText(row),'2026-11-05 자료 · 발표 시각 미제공');assert.doesNotMatch(flow.observationText(row),/00:00|KST/);
 assert.equal(flow.model(mutated('us10y',{observed_at:'2026-11-05T21:00:00Z'}),now).byId.us10y.value,null);
});
test('A genuinely published Treasury date can precede the conservative recheck deadline, never the current ET date',()=>{
 const early=Date.parse('2026-11-06T21:00:00Z'),feed=mutated('us10y',{
  session:'2026-11-06',previous_session:'2026-11-05',received_at:'2026-11-06T20:59:00Z',
  freshness:{status:'current',next_expected_session:'2026-11-09',next_check_after:'2026-11-09T23:00:00Z'}});
 feed.generated_at='2026-11-06T21:00:00Z';
 assert.equal(flow.model(feed,early).byId.us10y.current,true);
 assert.equal(flow.model(feed,Date.parse('2026-11-09T23:00:00Z')).byId.us10y.current,false);
 const row=feed.indicators.find(row=>row.id==='us10y');row.session='2026-11-07';
 assert.equal(flow.model(feed,early).byId.us10y.value,null);
 // UTC has rolled over while New York is still on the previous source date.
 row.session='2026-11-06';row.received_at='2026-11-06T00:59:00Z';feed.generated_at='2026-11-06T00:59:00Z';
 assert.equal(flow.model(feed,Date.parse('2026-11-06T01:00:00Z')).byId.us10y.value,null);
 row.source.field='BC_2YEAR';assert.equal(flow.model(feed,early).byId.us10y.value,null);
});
test('A fresh wrapper does not make an older market session current',()=>{
 const feed=mutated('kospi',{expected_session:'2026-11-06'}),result=flow.model(feed,now);
 assert.equal(result.byId.kospi.state,'stale');assert.equal(result.current,13);assert.equal(result.regions[0].status,'partial');
 assert.equal(result.available,5);assert.equal(result.counts.up,5);
 assert.deepEqual(result.regions[0].basisIds,['kosdaq']);assert.match(result.byId.kospi.reason,/2026-11-06/);
});
test('The unchanged file expires at its next real exchange cutoff',()=>{
 const feed=fixture();assert.equal(flow.model(feed,Date.parse('2026-11-06T21:59:59Z')).current,14);
 const result=flow.model(feed,Date.parse('2026-11-06T22:00:00Z'));assert.equal(result.current,0);assert.equal(result.available,0);
 assert.equal(result.byId.kospi.value,101);assert.match(result.headline,/확인 대기/);
});
test('A documented next Monday preserves Friday data through the weekend',()=>{
 const feed=fixture();for(const row of feed.indicators){row.freshness.next_expected_session='2026-11-09';row.freshness.next_check_after='2026-11-09T22:00:00Z'}
 assert.equal(flow.model(feed,Date.parse('2026-11-08T12:00:00Z')).current,14);
});
test('A missing or internally inverted next-session clock is not freshness proof',()=>{
 for(const freshness of [{status:'current'},{status:'current',next_expected_session:'2026-11-04',next_check_after:'2026-11-06T22:00:00Z'}])
  assert.equal(flow.model(mutated('kospi',{freshness}),now).byId.kospi.current,false);
});
test('Regional mixed direction is based on signs, not an invented weighted average',()=>{
 const feed=mutated('kosdaq',{value:100,previous_value:101,change_value:-1,change_pct:(100/101-1)*100,direction:'down'}),result=flow.model(feed,now);
 assert.equal(result.regions[0].direction,'mixed');assert.equal(result.counts.mixed,1);assert.equal(result.counts.up,5);
 assert.equal(result.regions[0].average,undefined);
});
test('Backend prose and wrong reported counts cannot override independently derived counts',()=>{
 const feed=fixture();feed.summary={headline:'BUY NOW',regions_up:999,regions_total:1000};feed.regions=[{id:'KR',direction:'down'}];
 const result=flow.model(feed,now);assert.equal(result.counts.up,6);assert.doesNotMatch(flow.render({data:{worldFlow:feed}},now),/BUY NOW|999/);
});
test('Duplicate identities and unsupported feed versions are not quietly selected',()=>{
 const feed=fixture();feed.indicators.push({...feed.indicators[0]});assert.equal(flow.model(feed,now).byId.kospi.value,null);
 feed.version='legacy';assert.equal(flow.model(feed,now).current,0);
});
test('Missing feed has explicit unavailable regions and no fabricated values',()=>{
 const result=flow.model(null,now);assert.equal(result.current,0);assert.equal(result.available,0);assert.equal(result.indicators.length,14);
 assert.equal(result.indicators.every(row=>row.value===null),true);assert.match(flow.render({data:{}},now),/자료 미수집/);
});
test('Reported news is safely escaped and future or stale news is excluded',()=>{
 const feed=fixture();feed.related_news[0].title='<img src=x onerror=alert(1)> & headline';
 feed.related_news.push({title:'FUTURE',url:'https://example.com/a',published_at:'2026-11-07T10:00:00Z'},
 {title:'STALE',url:'https://example.com/b',published_at:'2026-11-01T10:00:00Z'},
 {title:'UNSAFE',url:'javascript:alert(1)',published_at:'2026-11-06T10:00:00Z'});
 const html=flow.render({data:{worldFlow:feed}},now);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img|FUTURE|STALE|UNSAFE/);
 assert.match(html,/인과관계 검증 자료는 아닙니다/);assert.match(html,/연속선물 가격으로 현물 가격과 다릅니다/);
});
test('All fourteen indicator details retain independent dates, source links and units',()=>{
 const html=flow.render({data:{worldFlow:fixture()}},now);assert.equal((html.match(/data-worldflow-indicator=/g)||[]).length,14);
 assert.equal((html.match(/<div class="fx-worldflow-source"><a /g)||[]).length,14);
 assert.doesNotMatch(html,/<footer\b/);
 assert.match(html,/원 \/ 1 USD/);assert.match(html,/USD \/ 배럴/);assert.match(html,/USD \/ 트로이온스/);assert.match(html,/1bp = 0\.01%p/);
});
test('Restored index tiles show four real source values and no fabricated Dow quote',()=>{
 const html=flow.render({data:{worldFlow:fixture()}},now);
 const cards=['kospi','kosdaq','nasdaq','sp500','dow'];
 for(const key of cards)assert(html.includes('data-worldflow-index="'+key+'"'));
 assert.equal(html.split('data-worldflow-index="').length-1,5);
 const kospi=html.split('data-worldflow-index="kospi"')[1].split('</article>')[0];
 const dow=html.split('data-worldflow-index="dow"')[1].split('</article>')[0];
 assert(kospi.includes('data-worldflow-index-value>101'));
 assert(dow.includes('data-worldflow-index-value>—'));
 assert(dow.includes('수집 미연결'));
 assert.equal(html.split('data-worldflow-region="').length-1,6);
});
test('Stale index closes fail closed instead of showing old numbers',()=>{
 const feed=fixture();
 feed.indicators.find(x=>x.id==='kospi').freshness.next_check_after='2026-11-06T10:00:00Z';
 const html=flow.render({data:{worldFlow:feed}},now);
 const tile=html.split('data-worldflow-index="kospi"')[1].split('</article>')[0];
 assert(tile.includes('data-worldflow-index-value>—'));
 assert(tile.includes('갱신 대기'));
});
console.log('WORLD_FLOW_CONTRACT_PASS',count);
