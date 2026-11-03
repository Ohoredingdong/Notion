/* Synthetic fixed-clock production-JS selection test: no prices, orders, or live accounts. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('assets/stock-radar-flow-v2.js','utf8');
const anchor='window.StockRadarFlowV2={render:fxRender,';
assert.ok(source.includes(anchor),'review selector probe anchor before running');
const instrumented=source.replace(anchor,'window.__pendingProbe={fxRecord,fxPrediction,fxUniverse,fxLocal};'+anchor);
let clock=Date.parse('2026-11-02T22:30:31Z');
class FrozenClock extends Date{static now(){return clock;}}
const old={
 id:'previous-original',symbol:'^KS11',market:'KR',mode:'daily',
 status:'research_prediction',direction:'up',
 issued_at:'2026-11-02T13:54:46Z',
 probabilities:{down:.27,flat:.31,up:.42},
 target:{start:'2026-11-03T00:00:00Z',end:'2026-11-03T06:30:00Z'},
 display_origin:'earlier_public_frozen_record',user_receipt_verified:false,
 recommendation:false
};
const current={
 symbol:'^KS11',market:'KR',mode:'daily',status:'no_call',
 direction:null,probabilities:null,reason:'insufficient_session_time'
};
const symbol='^KS11';
const ctx={
 screen:'stocks',market:'ALL',selected:symbol,favorites:[],
 data:{raw:{companies:[{symbol,market:'KR',name:'KOSPI Index',priority:{score:1}}]},
 direction:{records:[current],prior_public_forecasts:[old]}}
};
const original=JSON.stringify(ctx);
const w={StockRadarV2Bridge:{snapshot:()=>ctx,helpers:{},render:()=>{}}};
const document={readyState:'loading',addEventListener:()=>{}};
vm.runInNewContext(instrumented,{window:w,document,Date:FrozenClock,console},
{filename:'assets/stock-radar-flow-v2.js'});
const {fxRecord,fxPrediction,fxUniverse,fxLocal}=w.__pendingProbe;
const c=ctx.data.raw.companies[0];
assert.equal(fxRecord(c,ctx)?.id,old.id,'valid earlier publicly frozen pending record must remain visible despite newer no-call');
assert.equal(fxPrediction(c,ctx).r?.direction,'up');
assert.match(fxPrediction(c,ctx).status,/기존|재발행/,'must distinguish earlier research publication from newly issued current forecast');
console.log('1/6 pending formerly published direction survives a later no-call without reissuance');
fxLocal.filter='ai';
assert.deepEqual(Array.from(fxUniverse(ctx),c=>c.symbol),[symbol],'in-date earlier signal may be inspected under AI research signal');
console.log('2/6 AI signal filter includes valid earlier forecast');
clock=Date.parse('2026-11-03T06:31:00Z');
assert.equal(fxPrediction(c,ctx).stale,true);
assert.deepEqual(Array.from(fxUniverse(ctx),c=>c.symbol),[],'existing parent stale guard must still block expired signal');
console.log('3/6 previously published record expires and is excluded by original stale gate');
clock=Date.parse('2026-11-02T22:30:31Z');
const newer={...old,id:'new-live',direction:'down',issued_at:'2026-11-02T22:30:30Z',
 probabilities:{down:.42,flat:.31,up:.27},display_origin:undefined};
ctx.data.direction.records.push(newer);
assert.equal(fxRecord(c,ctx)?.id,'new-live','a later actually frozen current prediction must take priority');
console.log('4/6 newer real prediction wins over carryover');
ctx.data.direction.records.pop();
ctx.data.direction.prior_public_forecasts=[];
assert.equal(fxPrediction(c,ctx).active,false,'without a verified prior entry no-call must remain no-call');
console.log('5/6 no-call without prior proof is not converted into new signal');
ctx.data.direction.prior_public_forecasts=[old];
assert.equal(JSON.stringify(ctx),original,'rendering must not modify the original, immutable mock records');
console.log('6/6 immutable forecast, no-call and public-proof status remain unchanged');
console.log('Pending published research-signal UI tests passed');
