/* UI forecast selection: synthetic data, no price fabrication or orders. */
const fs=require('fs');
const assert=require('node:assert/strict');
const script=fs.readFileSync('assets/stock-radar-flow-v2.js','utf8');
const start=script.indexOf('function fxRecord(c,ctx){');
const end=script.indexOf('\nfunction fxUniverse(ctx){',start);
assert(start>=0&&end>start,'prediction helpers should exist');
const clock=Date.parse('2026-11-05T06:00:00Z');
class FrozenDate extends Date {static now(){return clock;}}
const functions=new Function('Date','fxN',script.slice(start,end)+
 '\nreturn {fxRecord,fxPrediction,fxForecastMeta};')(FrozenDate,v=>typeof v==='number'&&Number.isFinite(v)?v:null);
const {fxRecord,fxPrediction,fxForecastMeta}=functions;
let count=0;
const check=(value,msg)=>{assert(value,msg);count++;};
const future={symbol:'AAPL',mode:'daily',status:'research_prediction',
 issued_at:'2026-11-04T21:15:00Z',direction:'up',
 target:{start:'2026-11-05T14:30:00Z',end:'2026-11-05T21:00:00Z'},
 probabilities:{up:.42,flat:.34,down:.24}};
const newer={symbol:'AAPL',mode:'intraday',status:'no_call',
 issued_at:'2026-11-05T03:45:00Z',reason:'insufficient_regular_session_time',
 probabilities:null,target:null};
const data={direction:{generated_at:'2026-11-05T03:45:00Z',records:[newer,future]},raw:{companies:[{symbol:'AAPL'},{symbol:'TSLA'}]}};
const apple={symbol:'AAPL'};
let result=fxPrediction(apple,{data});
check(result.active&&result.value===.42&&result.r.mode==='daily','valid daily supersedes newer intraday no-call');
check(result.status.includes('다음 거래기간'),'future target disclosed');
check(fxForecastMeta({data}).modeled===1&&fxForecastMeta({data}).tracked===2,'model scope is counted correctly');
const unknown=fxPrediction({symbol:'TSLA'},{data});
check(!unknown.active&&unknown.value===null&&unknown.status.includes('모델 대상'),'unsupported company shows no fabricated percentage');
const expired={...future,issued_at:'2026-11-04T08:00:00Z',
 target:{start:'2026-11-04T14:30:00Z',end:'2026-11-04T21:00:00Z'}};
const kr={symbol:'005930.KS',mode:'intraday',status:'research_prediction',issued_at:'2026-11-05T03:45:00Z',
 direction:'flat',target:{start:'2026-11-05T03:55:00Z',end:'2026-11-05T04:25:00Z'},
 probabilities:{up:.3,flat:.4,down:.3}};
result=fxPrediction({symbol:'005930'},{data:{direction:{records:[kr]}}});
check(result.stale&&!result.active&&result.value===null,'expired intraday is not treated as current forecast');
result=fxPrediction(apple,{data:{direction:{records:[expired,newer]}}});
check(!result.active&&result.value===null&&result.status.includes('기간 종료'),'historical forecast cannot be presented as live');
const invalid={...future,probabilities:{up:.9,flat:.9,down:.9}};
result=fxPrediction(apple,{data:{direction:{records:[invalid]}}});
check(result.value===null&&!result.active,'invalid probability sums are rejected');
const reason=fxPrediction(apple,{data:{direction:{records:[newer]}}});
check(!reason.active&&reason.status.includes('정규장 자료'),'no-call explanation is visible');
console.log('PASS '+count+' signal-selection and coverage tests');
