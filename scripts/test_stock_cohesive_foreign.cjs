'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
process.chdir(path.join(__dirname,'..'));
const read=f=>fs.readFileSync(f,'utf8');
const tw=JSON.parse(read('stock-research-twse-catalog.json'));
const window={};
const cx=vm.createContext({window,URL,Date,fetch:async()=>({ok:true,json:async()=>tw})});
for(const f of ['data',''])vm.runInContext(read('assets/radar-cohesive-foreign'+(f?'-'+f:'')+'.js'),cx);
const api=window.RadarCohesiveForeign;
window.RadarCohesive={
 id:c=>c.selection_id,
 esc:s=>String(s??'').replace(/[&<>"']/g,'_'),
 fmt:(n,d=2)=>Number(n).toLocaleString('en',{maximumFractionDigits:d}),
 link:(u,n)=>'<a href="'+u+'">'+n+'</a>',
 card:(t,b)=>'<section>'+t+b+'</section>',
 empty:s=>s,
 stockRows:(a,{max})=>a.slice(0,max).map(x=>'<button data-rc-stock="'+x.selection_id+'">'+x.name+'</button>').join('')
};
const render=c=>api.renderMarket({country:c,companies:api.rows().filter(x=>x.country===c),favorites:[]},'');
const event=(country,type,dataset,value='')=>api.handle({type,target:{closest:()=>({dataset,value})}},{country});
(async()=>{
 assert.equal(api.rows().length,42);
 await new Promise(done=>api.load(done));
 const rows=api.rows(), t=rows.find(x=>x.selection_id==='TW:2330'), no=rows.find(x=>x.selection_id==='TW:1538');
 assert.equal(rows.length,1130);assert.equal(t.sector,'반도체');assert.equal(t.price,2030);assert.match(api.search(t),/TSMC/);
 assert.equal(no.price,undefined);
 assert.equal(tw.items.length,1088);assert.equal(Object.keys(tw.sector_prices).length,32);
 assert.equal(tw.sector_prices['24'].change_pct,2.58);assert.equal(tw.sector_prices['17'].change_pct,-2.65);
 for(const country of ['JP','CN','HK','GB','DE','VN','SG']){
  const subset=rows.filter(x=>x.country===country);
  assert.equal(subset.length,6);assert.equal(new Set(subset.map(x=>x.sector)).size,3);
  assert(subset.every(x=>x.price===undefined&&x.catalog_only&&/^https:/.test(x.sources.profile)));
  assert(render(country).includes('공식 산업 지표'));
  event(country,'click',{rcForeignSector:subset[0].sector});assert.equal((render(country).match(/data-rc-stock=/g)||[]).length,2);
  api.reset(country);assert.equal((render(country).match(/data-rc-stock=/g)||[]).length,6);
 }
 assert.match(render('HK'),/%p/);
 assert.match(render('TW'),/2\.58%/);
 event('TW','click',{rcForeignSector:'반도체'});assert.equal((render('TW').match(/data-rc-stock=/g)||[]).length,70);
 event('TW','click',{rcForeignMore:''});assert.equal((render('TW').match(/data-rc-stock=/g)||[]).length,96);
 event('TW','input',{rcmSearch:'company'},'ＴＳＭＣ');assert.equal((render('TW').match(/data-rc-stock=/g)||[]).length,1);assert.match(render('TW'),/TW:2330/);
 assert.match(api.companyNote(t,'finance'),/재무제표·비율은 아직 연결되지 않았습니다/);
 console.log('PASS: TWSE known/missing ID/official sectors, 7 samples, all 8 industry contexts, tabs/scoped reset/filter/alias/pagination');
})().catch(e=>{console.error(e);process.exitCode=1});
