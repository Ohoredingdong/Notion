/* Synthetic fixed-clock, production-asset behavior checks: no price records, trading or live source. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const asset = fs.readFileSync('assets/stock-radar-flow-v2.js', 'utf8');
const marker = 'window.StockRadarFlowV2={render:fxRender,';
assert.equal(asset.includes(marker), true, 'review injection anchor before testing actual production JS');
const instrumented = asset.replace(marker, 'window.__timingResearch={fxUniverse,fxPrediction,fxLocal};'+marker);

let now = Date.parse('2026-11-02T22:00:00Z');
class FrozenClock extends Date { static now() { return now; } }
const rec = (symbol, direction, end, status='research_prediction')=>({
  symbol, market:'US', mode:'daily', status,
  direction:status==='research_prediction'?direction:null,
  probabilities:status==='research_prediction'?{down:direction==='down'?0.60:0.2,flat:0.2,up:direction==='up'?0.60:0.2}:null,
  issued_at:'2026-11-02T13:54:46Z',
  target: {start:'2026-11-02T23:00:00Z',...(end===null?{}:{end})}
});
const symbols=['AAPL','NVDA','MSFT','TSLA','AMD'];
const ctx = {
  screen:'stocks',market:'ALL',selected:'NVDA',favorites:[],
  data: {
    raw:{companies:symbols.map(symbol=>({symbol,name:symbol,market:'US',priority:{score:0}}))},
    direction:{records:[
      {...rec('AAPL','up','2026-11-02T21:00:00Z'),target:{start:'2026-11-02T14:30:00Z',end:'2026-11-02T21:00:00Z'}},
      rec('NVDA','up','2026-11-03T05:00:00Z'),
      rec('MSFT','up','2026-11-03T05:00:00Z','no_call'),
      rec('TSLA','up',null),
      rec('AMD','down','2026-11-03T05:00:00Z')
    ]}
  }
};
const original = JSON.stringify(ctx);
const win={StockRadarV2Bridge:{snapshot:()=>ctx,helpers:{},render:()=>{}}};
const document={readyState:'loading',addEventListener:()=>{}};
vm.runInNewContext(instrumented,{window:win,document,Date:FrozenClock,console},{filename:'assets/stock-radar-flow-v2.js'});
const {fxUniverse,fxPrediction,fxLocal} = win.__timingResearch;
const picks=(filter)=>{fxLocal.filter=filter;return Array.from(fxUniverse(ctx),c=>c.symbol);};
const bySym=s=>ctx.data.raw.companies.find(c=>c.symbol===s);

assert.equal(fxPrediction(bySym('AAPL'),ctx).stale,true,'expired frozen signal must be explicitly marked stale');
assert.equal(fxPrediction(bySym('TSLA'),ctx).unknown,true,'missing target-end clock must be unknown');
assert.equal(fxPrediction(bySym('AAPL'),ctx).active,false,'expired forecast is never an active actionable signal');
assert.equal(fxPrediction(bySym('AAPL'),ctx).value,null,'expired forecast confidence cannot appear as a current pill');
assert.equal(fxPrediction(bySym('TSLA'),ctx).active,false,'unknown target-end cannot be active');
assert.equal(fxPrediction(bySym('TSLA'),ctx).value,null,'unknown target-end confidence cannot appear as current');
assert.equal(fxPrediction(bySym('NVDA'),ctx).active,true,'nonexpired forward forecast must remain active');
assert.equal(fxPrediction(bySym('NVDA'),ctx).value,0.60,'valid forward confidence is retained');
assert.deepEqual(picks('all'),symbols,'historical and no-call entries must remain inspectable in all records');
console.log('1/6: expired historical evidence remains in all-record view');
assert.deepEqual(picks('ai'),['NVDA','AMD'],'AI signal filter must exclude elapsed, missing-clock, and no-call records');
console.log('2/6: AI active-signal filtering excludes expired and indeterminate records');
assert.deepEqual(picks('up'),['NVDA'],'UP filter must not reuse an expired UP signal');
console.log('3/6: expired UP excluded without hiding fresh UP');
assert.deepEqual(picks('down'),['AMD'],'DOWN filter must preserve a valid future DOWN signal');
console.log('4/6: fresh DOWN preserved');
assert.equal(fxPrediction(bySym('MSFT'),ctx).active,false,'no-call must never be a fresh model signal');
console.log('5/6: no-call remains non-actionable');
assert.equal(JSON.stringify(ctx),original,'neither original records nor probabilities/targets can be rewritten');
console.log('6/6: frozen synthetic evidence is not rewritten');

// New fixed-clock cross-mode control. No exchange data or invented trading outcome.
now = Date.parse('2026-11-03T15:30:00Z');
const crossMode = JSON.parse(JSON.stringify(ctx));
crossMode.data.direction.records = [
  {...rec('NVDA','up','2026-11-02T21:00:00Z'),mode:'daily',
    issued_at:'2026-10-30T22:38:20Z',
    target:{start:'2026-11-02T14:30:00Z',end:'2026-11-02T21:00:00Z'}},
  {...rec('NVDA','down','2026-11-03T15:45:00Z'),mode:'intraday',
    issued_at:'2026-11-03T14:40:00Z',
    target:{start:'2026-11-03T15:15:00Z',end:'2026-11-03T15:45:00Z'}}
];
const frozenCrossMode = JSON.stringify(crossMode.data.direction.records);
assert.equal(fxPrediction(bySym('NVDA'),crossMode).r.mode,'intraday',
  'stale daily must not mask usable intraday research forecast');
fxLocal.filter='ai';
assert.ok(Array.from(fxUniverse(crossMode),c=>c.symbol).includes('NVDA'),
  'valid intraday must remain visible in current AI filter');
fxLocal.filter='down';
assert.ok(Array.from(fxUniverse(crossMode),c=>c.symbol).includes('NVDA'),
  'valid intraday DOWN must remain visible in corresponding direction filter');
// Preserve the existing fresh-daily preference where both rows are still valid.
crossMode.data.direction.records[0].target = {
  start:'2026-11-03T14:30:00Z',end:'2026-11-03T21:00:00Z'
};
assert.equal(fxPrediction(bySym('NVDA'),crossMode).r.mode,'daily',
  'current daily still takes precedence over current intraday');
assert.equal(JSON.stringify(crossMode.data.direction.records[1]),
  JSON.stringify(JSON.parse(frozenCrossMode)[1]),'intraday original row is immutable');
console.log('Cross-mode fixed-clock test: stale daily cannot hide usable intraday; fresh daily precedence preserved');

// Predeclared 2026-11-03 no-call precedence negative control against real main's
// stale status masking. These are synthetic records and never operational prices.
now = Date.parse('2026-11-03T04:05:00Z');
const noCallCtx = JSON.parse(JSON.stringify(ctx));
noCallCtx.data.direction.records = [
  {...rec('AAPL','down','2026-11-03T21:00:00Z'),mode:'daily',
    issued_at:'2026-11-02T22:30:30Z',
    target:{start:'2026-11-03T14:30:00Z',end:'2026-11-03T21:00:00Z'}},
  {...rec('AAPL','flat',null,'no_call'),mode:'intraday',
    issued_at:'2026-11-03T04:02:42Z',
    reason:'insufficient_regular_session_time',target:null}
];
const frozenNoCall = JSON.stringify(noCallCtx.data.direction.records);
const selectedDaily = fxPrediction(bySym('AAPL'),noCallCtx);
assert.equal(selectedDaily.r.mode,'daily',
  'a newer intraday no-call must not conceal the still-valid frozen daily forecast');
assert.equal(selectedDaily.active,true,
  'valid daily research forecast remains discoverable before its future target');
fxLocal.filter='ai';
assert.ok(Array.from(fxUniverse(noCallCtx),c=>c.symbol).includes('AAPL'),
  'prospective daily research remains in the active research-only filter');
now = Date.parse('2026-11-03T21:01:00Z');
const expiredDaily = fxPrediction(bySym('AAPL'),noCallCtx);
assert.equal(expiredDaily.active,false,
  'daily research forecast expires without promoting the old no-call');
assert.equal(expiredDaily.value,null,
  'past daily numerical confidence must not be presented as current');
assert.ok(!Array.from(fxUniverse(noCallCtx),c=>c.symbol).includes('AAPL'),
  'expired daily plus no-call do not create a live AI signal');
assert.equal(JSON.stringify(noCallCtx.data.direction.records),frozenNoCall,
  'no-call precedence and expiry checks must never rewrite frozen records');
console.log('No-call precedence fixed-clock test: valid daily remains visible until expiry without rewriting evidence');

console.log('Research-only stale/unknown signal-filter tests all passed');
