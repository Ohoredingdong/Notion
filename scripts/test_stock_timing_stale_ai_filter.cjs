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

console.log('Research-only stale/unknown signal-filter tests all passed');
