'use strict';
// Independent synthetic UI guard, no live data or outcome mutation.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('assets/stock-radar-flow-v2.js','utf8');
const marker='window.StockRadarFlowV2={';
assert.ok(source.includes(marker),'actual radar renderer marker missing');
const vmContext={
 window:{StockRadarV2Bridge:{helpers:{T:x=>x}}},
 document:{readyState:'loading',addEventListener(){}},
 localStorage:{getItem(){return null;}}, Date,console
};
vm.runInNewContext(source.replace(marker,'window.__basisTests={bars:fxBars,outcomes:fxOutcomes};'+marker),vmContext,{timeout:2000});
const {bars,outcomes}=vmContext.window.__basisTests;
function context(mode){
 const record={id:'SYNTH-'+mode,symbol:'005930.KS',market:'KR',mode,
   status:'research_prediction',direction:'flat',
   issued_at:'2026-11-03T12:00:00Z',
   target:{start:'2099-11-04T00:00:00Z',end:'2099-11-04T06:30:00Z'},
   probabilities:{up:0.2,flat:0.6,down:0.2},neutral_band_pct:1.47};
 return {data:{direction:{records:[record]},learning:{groups:{}}}};
}
for(const mode of ['daily','intraday']){
 const ctx=context(mode),before=JSON.stringify(ctx.data.direction);
 const html=bars({symbol:'005930.KS',name:'Synthetic'},ctx);
 assert.match(html,/fx-ai-heading/,'must render an active synthetic signal');
 assert.match(html,/대상 구간 시작 시가\s*→\s*종료 종가/,mode+' missing target basis');
 assert.match(html,/전일 종가/,mode+' missing previous close distinction');
 assert.equal(JSON.stringify(ctx.data.direction),before,'render changed frozen record');
}
const record={id:'SYNTH-outcome',symbol:'005930.KS',mode:'daily',status:'observed',
 issued_at:'2026-11-02T13:54:46Z',target:{start:'2026-11-03T00:00:00Z',end:'2026-11-03T06:30:00Z'},
 evaluated_at:'2026-11-03T11:22:36Z',predicted:'flat',actual:'flat',correct:true,
 public_before_target_verified:true};
const ctx={data:{outcomes:[record],learning:{evaluation_counts:{eligible_scored:1}}}};
const before=JSON.stringify(ctx.data.outcomes),html=outcomes(ctx);
assert.match(html,/최근 관측 기록/);
assert.match(html,/대상 구간 시작 시가\s*→\s*종료 종가/,'outcome table missing basis');
assert.match(html,/전일 종가/,'outcome table missing previous close distinction');
assert.equal(JSON.stringify(ctx.data.outcomes),before);
console.log('Three synthetic target-basis UI controls passed');