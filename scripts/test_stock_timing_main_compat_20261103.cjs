/* Bounded current-main integration regression. Synthetic only; never operational prices. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const asset=fs.readFileSync('assets/stock-radar-flow-v2.js','utf8');
const marker='window.StockRadarFlowV2={render:fxRender,';
assert.ok(asset.includes(marker),'known runtime export injection anchor');
const instrumented=asset.replace(marker,'window.__researchTest={fxRecord,fxPrediction,fxUniverse,fxLocal};'+marker);
let clock=Date.parse('2026-11-03T05:00:00Z');
class FixedDate extends Date{static now(){return clock;}}
const mk=(symbol,mode,direction,issued,start,end,status='research_prediction')=>({
  symbol,market:'US',mode,issued_at:issued,target:status==='research_prediction'?{start,...(end===null?{}:{end})}:null,
  status,direction:status==='research_prediction'?direction:null,
  probabilities:status==='research_prediction'?{down:direction==='down'?0.6:0.2,flat:direction==='flat'?0.6:0.2,up:direction==='up'?0.6:0.2}:null
});
const daily=mk('AAPL','daily','down','2026-11-02T22:30:30Z','2026-11-03T14:30:00Z','2026-11-03T21:00:00Z');
const nocall=mk('AAPL','intraday',null,'2026-11-03T04:02:40Z',null,null,'no_call');
const ctx={
  screen:'stocks',market:'ALL',selected:'AAPL',favorites:[],
  data:{
    raw:{companies:[{symbol:'AAPL',name:'Apple',market:'US',priority:{score:0}}]},
    direction:{records:[daily,nocall]}
  }
};
const saved=JSON.stringify(ctx.data.direction.records);
const win={StockRadarV2Bridge:{snapshot:()=>ctx,helpers:{},render:()=>{}}};
vm.runInNewContext(instrumented,{window:win,document:{readyState:'loading',addEventListener:()=>{}},Date:FixedDate,localStorage:{getItem:()=>null},console},{filename:'assets/stock-radar-flow-v2.js'});
const {fxRecord,fxPrediction,fxUniverse,fxLocal}=win.__researchTest;
const stock=ctx.data.raw.companies[0];
const pick=filter=>{fxLocal.filter=filter;return Array.from(fxUniverse(ctx),r=>r.symbol);};
assert.equal(fxRecord(stock,ctx)?.mode,'daily','later intraday no-call cannot mask prospective valid daily');
assert.equal(fxPrediction(stock,ctx).active,true,'a valid future daily signal remains available as research-only');
assert.deepEqual(pick('ai'),['AAPL'],'valid research-only daily visible before target');
console.log('1/7: future daily survives newer intraday no-call');
clock=Date.parse('2026-11-03T16:00:00Z');
ctx.data.direction.records=[
  mk('AAPL','daily','up','2026-11-02T22:30:30Z','2026-11-02T14:30:00Z','2026-11-02T21:00:00Z'),
  mk('AAPL','intraday','down','2026-11-03T15:00:00Z','2026-11-03T15:15:00Z','2026-11-03T16:45:00Z')
];
assert.equal(fxRecord(stock,ctx).mode,'intraday','expired daily must not hide genuinely valid intraday');
assert.deepEqual(pick('down'),['AAPL'],'real valid intraday direction visible');
console.log('2/7: expired daily cannot hide fresh intraday');
ctx.data.direction.records=[mk('AAPL','daily','up','2026-11-02T22:30:30Z','2026-11-03T14:30:00Z','2026-11-03T21:00:00Z'),ctx.data.direction.records[1]];
assert.equal(fxRecord(stock,ctx).mode,'daily','prior research daily precedence retained while valid');
console.log('3/7: preferred current daily remains first');
ctx.data.direction.records=[mk('AAPL','daily','up','2026-11-02T22:30:30Z','2026-11-02T14:30:00Z','2026-11-02T21:00:00Z')];
const expired=fxPrediction(stock,ctx);
assert.equal(expired.stale,true);assert.equal(expired.active,false);
assert.equal(expired.value,null,'expired numerical confidence cannot be current');
assert.deepEqual(pick('ai'),[],'elapsed predictions excluded from signal filter');
console.log('4/7: expired confidence inactive but stored original visible outside signal filter');
ctx.data.direction.records=[mk('AAPL','daily','down','2026-11-02T22:30:30Z','2026-11-03T14:30:00Z',null)];
const unknown=fxPrediction(stock,ctx);
assert.equal(unknown.unknown,true);assert.equal(unknown.active,false);assert.equal(unknown.value,null);
assert.deepEqual(pick('ai'),[]);
console.log('5/7: missing end time remains explicitly unverified');
ctx.data.direction.records=[mk('AAPL','intraday','up','2026-11-03T15:45:00Z','2026-11-03T15:15:00Z','2026-11-03T16:45:00Z')];
assert.equal(fxPrediction(stock,ctx).active,false,'retroactively issued after target began cannot be current');
ctx.data.direction.records=[mk('AAPL','daily','up','2026-11-04T12:00:00Z','2026-11-04T14:30:00Z','2026-11-04T21:00:00Z')];
assert.equal(fxPrediction(stock,ctx).active,false,'future issue timestamp is not present evidence');
console.log('6/7: chronology rejects retroactive or future issuance');
// One preregistered fault: a forecast issued two minutes in the *future* does
// not exist yet and must not be a current UI signal, regardless of 5m clock grace.
ctx.data.direction.records=[mk('AAPL','daily','up',
  '2026-11-03T16:02:00Z','2026-11-03T16:15:00Z','2026-11-03T21:00:00Z')];
assert.equal(fxPrediction(stock,ctx).active,false,
  'near-future issued_at cannot be an already-issued research signal');
assert.deepEqual(pick('ai'),[],
  'not-yet-issued call must not enter current AI signal filter');
assert.equal(pick('all').length,1,
  'synthetic archived record remains inspectable without backdating');
console.log('Near-future issuance negative control: not-yet-issued is never current');
ctx.data.direction.records=[mk('AAPL','daily','up','2026-11-03T14:00:00Z','2026-11-03T14:30:00Z','2026-11-03T21:00:00Z')];
ctx.data.direction.records[0].probabilities={up:0.9,down:0.6,flat:0.1};
assert.equal(fxPrediction(stock,ctx).active,false,'invalid probability distribution cannot be current');
ctx.data.direction.records=[daily,nocall];
assert.equal(JSON.stringify(ctx.data.direction.records),saved,'immutable original evidence never rewritten');
console.log('7/7: invalid distribution fails closed and real records remain untouched');
console.log('Fixed-clock prospective UI research controls passed; NOT a trading-usefulness proof.');
