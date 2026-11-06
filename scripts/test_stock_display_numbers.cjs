const assert=require('node:assert/strict'),fs=require('node:fs');
const bridge=fs.readFileSync('assets/stock-radar-clean-bridge.js','utf8');
const code=bridge.slice(bridge.indexOf('function dailyChangeValue('),bridge.indexOf('function pointData('));
let chart=null;
const {change,dailyChangeValue}=new Function('N','chartFor',code+';return {change,dailyChangeValue};')(
 v=>typeof v==='number'&&Number.isFinite(v)?v:null,()=>chart);
const c={symbol:'TEST',source_symbol:'TEST',market:'US',currency:'USD',price:110,price_session:'2026-11-05'};
const proof={version:'completed-session-change-v1',status:'verified',market:'US',provider_symbol:'TEST',currency:'USD',
 source_identity_verified:true,price_session:'2026-11-05',close:110,previous_session:'2026-11-04',previous_close:100,
 expected_previous_session:'2026-11-04',consecutive_sessions:true,change_1d_pct:10,basis:'provider_close_auto_adjust_false'};
let count=0;const test=(name,fn)=>{chart=null;fn();count++;console.log('PASS',name)};
test('Consecutive session proof is independently recomputed',()=>assert(Math.abs(change({...c,daily_change:proof})-10)<1e-10));
test('An appended multi-session jump never becomes a daily return',()=>{
 chart={chart_status:'snapshot_appended',bars:[{date:'2026-10-30',close:90},{date:'2026-11-05',close:110}]};
 assert.equal(change(c),null);
});
test('Even an aligned legacy chart needs explicit exchange-session proof',()=>{
 chart={chart_status:'aligned',bars:[{date:'2026-11-03',close:90},{date:'2026-11-05',close:110}]};assert.equal(change(c),null);
});
test('The same quote with valid chart proof can supply a daily return',()=>{
 chart={chart_status:'aligned',bars:[{date:'2026-11-04',close:100},{date:'2026-11-05',close:110}],daily_change:proof};
 assert(Math.abs(change(c)-10)<1e-10);
});
test('Currency, company, session, calendar, split and arithmetic failures are rejected',()=>{
 for(const patch of [{currency:'CNY'},{provider_symbol:'OTHER'},{market:'KR'},{price_session:'2026-11-04'},
  {previous_session:'2026-11-03'},{expected_previous_session:'2026-11-03'},{consecutive_sessions:false},
  {source_identity_verified:false},{status:'unavailable'},{change_1d_pct:25},{close:111},{previous_close:0},
  {change_1d_pct:'10'},{previous_session:'2026-02-30',expected_previous_session:'2026-02-30'}])
  assert.equal(dailyChangeValue(c,{...proof,...patch}),null,JSON.stringify(patch));
});
test('Conflicting independently valid sources are withheld',()=>{
 chart={chart_status:'aligned',bars:[{date:'2026-11-04',close:105},{date:'2026-11-05',close:110}],daily_change:{...proof,previous_close:105,change_1d_pct:(110/105-1)*100}};
 assert.equal(change({...c,daily_change:proof}),null);
});
const flow=fs.readFileSync('assets/stock-radar-flow-v2.js','utf8');
const utilities=flow.slice(flow.indexOf('function fxN('),flow.indexOf('function fxContext('));
const amount=flow.slice(flow.indexOf('function fxAmount('),flow.indexOf('function fxSafeHref('));
const facts=flow.slice(flow.indexOf('function fxV5Facts('),flow.indexOf('function fxV5FocusItems('));
const {fxAmount,fxV5Facts}=new Function(utilities+amount+facts+';return {fxAmount,fxV5Facts};')();
test('An ADR financial amount retains its reporting currency',()=>{
 const text=fxV5Facts({currency:'USD',history:{currency:'CNY',fcf:123456789}}).find(row=>row[0].includes('FCF'))[1];
 assert.match(text,/CNY$/);assert.doesNotMatch(text,/USD/);
 assert.match(fxAmount(123456789,'GBP'),/GBP$/);assert.match(fxAmount(123456789,'JPY'),/JPY$/);
});
test('Unknown reporting currency does not silently inherit trading currency',()=>{
 for(const currency of [null,'ZZZ','XXX','unknown'])assert.equal(fxAmount(1200,currency),'통화 미확인');
 assert.equal(fxAmount(null,'USD'),'—');
 assert.equal(fxV5Facts({currency:'USD',history:{fcf:1234}}).find(row=>row[0].includes('FCF'))[1],'통화 미확인');
});
test('Every history amount in cockpit and detail uses the history currency',()=>{
 assert.doesNotMatch(flow,/fxAmount\((?:h|history)\.[^,]+,c\.currency\)/);
 assert.match(flow,/fxAmount\(history\.revenue,history\.currency\)/);
 assert.match(flow,/fxAmount\(h\.net_income,h\.currency\)/);
});
const sentiment=flow.slice(flow.indexOf('function fxSentimentObservation('),flow.indexOf('function fxV5Sentiment('));
const observation=new Function(utilities+sentiment+';return fxSentimentObservation;')();
const clock=Date.parse('2026-11-06T09:00:00Z');
const context=()=>({data:{sentiment:{market:'us',source_timestamp:'2026-11-06T01:00:00Z',headline:{score:19.8}},
 koreaSentiment:{market:'kr',date:'2026-11-05',kospi:{index:31.7}},
 worldFlow:{version:'stock-world-flow-v1',indicators:[
  {id:'kospi',expected_session:'2026-11-06',freshness:{next_expected_session:'2026-11-09',next_check_after:'2026-11-09T07:00:00Z'}},
  {id:'sp500',expected_session:'2026-11-05',freshness:{next_expected_session:'2026-11-06',next_check_after:'2026-11-06T21:30:00Z'}}]}}});
test('Sentiment freshness uses observation time rather than a fresh file wrapper',()=>{
 const ctx=context();ctx.data.koreaSentiment.generated_at='2026-11-06T08:59:00Z';
 assert.equal(observation(ctx,true,clock).score,31.7);assert.equal(observation(ctx,true,clock).stale,true);
 assert.equal(observation(ctx,false,clock).stale,false);
 assert.equal(observation(ctx,false,Date.parse('2026-11-06T21:31:00Z')).stale,true);
});
test('Future US timestamp and Korean date are withheld',()=>{
 const ctx=context();ctx.data.sentiment.source_timestamp='2026-11-06T09:01:00Z';ctx.data.koreaSentiment.date='2026-11-07';
 assert.equal(observation(ctx,false,clock).score,null);assert.equal(observation(ctx,true,clock).score,null);
});
test('A Korean same-day reading before the completed session is not current',()=>{
 const ctx=context();ctx.data.koreaSentiment.date='2026-11-06';ctx.data.worldFlow.indicators[0].expected_session='2026-11-05';
 assert.equal(observation(ctx,true,Date.parse('2026-11-06T03:00:00Z')).valid,false);
});
console.log('DISPLAY_NUMBER_CONTRACT_PASS',count);
