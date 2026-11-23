const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
process.chdir(path.join(__dirname,'..'));
const window={RadarCohesive:{
 esc:x=>String(x??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]),
 fmt:x=>Number(x).toLocaleString('ko-KR'),link:(u,n)=>'<a href="'+u+'">'+n+'</a>',
 compare:(x,p,{verified})=>verified?(x>p?'↑':x<p?'↓':'='):'비교 없음'
}};
const cutoff=Date.parse('2026-11-24T00:00:00Z');
class FixtureDate extends Date{static now(){return cutoff}}
const cx={window,Date:FixtureDate};vm.createContext(cx);
for(const file of ['radar-cohesive-region-snapshots.js','radar-cohesive-regions.js'])vm.runInContext(fs.readFileSync('assets/'+file,'utf8'),cx);
const api=window.RadarCohesiveRegions;
const data={worldFlow:{indicators:Object.values(api.regions).filter(s=>s.key).map(s=>({
 id:s.key,value:1234,previous_value:1200,session:'2026-11-19',previous_session:'2026-11-18',
 expected_session:'2026-11-20',quote_basis:'exchange_regular_close',status:'stale',
 comparison_basis:'previous_exchange_session',comparison_verified:true,
 source:{identity_verified:true,provider_symbol:s.symbol,response_symbol:s.symbol,provider:'Fixture',url:'https://example.test/'}
}))}};
assert.deepEqual(Object.keys(api.regions).sort(),['JP','CN','HK','TW','GB','DE','VN','SG'].sort());
for(const c of Object.keys(api.regions)){
 const h=api.render({country:c,data,companies:[]});
 assert(h.includes('data-rc-region="'+c+'"'));
 assert(h.includes('레이더 종목 명부·개별 시세·기업 분석 미연결'));
 assert(h.includes('공식 원문 바로가기'));
 assert(h.includes('소비자물가 · 전년동월비'));
 assert(h.includes('2026-10 기준'));
 assert(h.includes('지수 공식 원문'));
 for(const l of api.regions[c].links)assert(new URL(l[1]).protocol==='https:');
}
for(const c of ['KR','US','constructor']){assert.equal(api.render({country:c,data}), '');assert.equal(api.benchmark(c,data),null);}
for(const c of ['GB','VN','SG']){
 assert.equal(api.benchmark(c,data,cutoff),null);
 assert(api.render({country:c,data}).includes('저장 지수 미연결'));
}
for(const c of ['JP','CN','HK','DE']){
 const b=api.benchmark(c,data,cutoff);
 assert.equal(b.state,'저장 종가 · 갱신 대기');assert.equal(b.session,'2026-11-19');
}
const taiwan=api.benchmark('TW',data,cutoff);assert.equal(taiwan.value,36811.89);assert.equal(taiwan.previous_value,36033.29);assert(taiwan.verified);assert(taiwan.state.includes('자동 갱신 미연결'));
assert.equal(api.benchmark('TW',data,Date.parse('2026-11-22T00:00:00Z')),null);
const fake=structuredClone(data);fake.worldFlow.indicators.find(x=>x.id==='nikkei225').source.response_symbol='AAPL';assert.equal(api.benchmark('JP',fake,cutoff),null);
const noCompare=structuredClone(data);noCompare.worldFlow.indicators.find(x=>x.id==='hang_seng').comparison_verified=false;assert.equal(api.benchmark('HK',noCompare,cutoff).verified,false);
console.log('PASS: eight isolated foreign markets, CPI contexts, attributed Taiwan and four dated historical values, unsupported/stale/future/identity/direction fail closed, KR/US unchanged');
