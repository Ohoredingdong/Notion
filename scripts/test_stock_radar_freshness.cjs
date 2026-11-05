/* Reproduce stale displayed values regardless of the selected price source. */
const assert=require('node:assert/strict'),fs=require('node:fs');
const script=fs.readFileSync('assets/stock-radar-clean-bridge.js','utf8');
const start=script.indexOf('function expectedClose(sources){');
const end=script.indexOf('\nfunction caseOf(',start);
assert(start>=0&&end>start);
let now=Date.parse('2026-11-05T08:00:00Z');
class FrozenDate extends Date {static now(){return now}}
const numeric=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
const helpers='const N=v=>typeof v==="number"&&Number.isFinite(v)?v:null, F=v=>String(v), E=v=>String(v), P=v=>String(v),tone=()=>"tone",link=()=>"",mini=()=>"";';
function load(macro,chart){
 const data={macro:{indicators:{kospi:macro}}};
 return new Function('D','series','Date',helpers+script.slice(start,end)+';return {indices,expectedClose};')(data,id=>id==='^KS11'?chart:null,FrozenDate);
}
const chart=date=>({bars:[{date:'2026-11-03',close:100},{date,close:98}],expected_session:'2026-11-05'});
let checks=0;
const check=(name,fn)=>{fn();checks++;console.log('PASS',name)};
check('Macro source discloses a missed completed close',()=>{
 assert.match(load({date:'2026-11-04',value:99,expected_session:'2026-11-05'},chart('2026-11-03')).indices(),/2026-11-05 마감값 갱신 대기/);
});
check('Newer chart does not hide stale completed-session warning',()=>{
 assert.match(load({date:'2026-11-03',value:99,expected_session:'2026-11-05'},chart('2026-11-04')).indices(),/2026-11-05 마감값 갱신 대기/);
});
check('Current completed close has no false missed-close warning',()=>{
 assert.doesNotMatch(load({date:'2026-11-05',value:99,expected_session:'2026-11-05'},chart('2026-11-05')).indices(),/마감값 갱신 대기/);
});
const clock={expected_session:'2026-11-04',next_session:'2026-11-05',next_close:'2026-11-05T06:30:00Z',delay_minutes:30};
check('File remains honest after its advertised next exchange close',()=>{
 const x=load({date:'2026-11-04',value:99,session_clock:clock},null);
 assert.match(x.indices(),/2026-11-05 마감값 갱신 대기/);
});
check('Provider delay is allowed before a new close is expected',()=>{
 now=Date.parse('2026-11-05T06:45:00Z');
 assert.doesNotMatch(load({date:'2026-11-04',value:99,session_clock:clock},null).indices(),/마감값 갱신 대기/);
 now=Date.parse('2026-11-05T08:00:00Z');
});
check('Neither missing dates nor absent prices manufacture freshness',()=>{
 assert.equal(load({},null).expectedClose([{},null]),null);
 assert.match(load({},null).indices(),/기준일 미확인/);
});
const line=script.split('\n').find(line=>line.startsWith('function latestIssued(records)'));
const latest=new Function('Date',line+';return latestIssued;')(FrozenDate);
check('No-call file refresh cannot become a new forecast issue time',()=>{
 assert.equal(latest([{status:'research_prediction',issued_at:'2026-11-04T22:00:00Z'},
 {status:'no_call',issued_at:'2026-11-05T08:00:00Z'}]),'2026-11-04T22:00:00Z');
});
check('Invalid and future issue timestamps are excluded',()=>{
 assert.equal(latest([{status:'research_prediction',issued_at:'bad'},
 {status:'research_prediction',issued_at:'2026-11-06T08:00:00Z'}]),null);
});
console.log('RADAR_FRESHNESS_PASS',checks);
