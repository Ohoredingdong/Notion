const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync(__dirname+'/../assets/radar-cohesive.js','utf8');
const context={};vm.createContext(context);
const extract=(start,end)=>src.slice(src.indexOf(start),src.indexOf(end,src.indexOf(start)));
vm.runInContext(`const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const n=v=>typeof v==='number'&&Number.isFinite(v)?v:null;const fmt=v=>n(v)===null?'—':String(v);`+extract('function compare(','function stockRows(')+extract('function indexRecord(','const researchDate='),context);
for(const [a,b,state] of [[3,2,'up'],[1,2,'down'],[2,2,'flat'],[-2,-3,'up'],[0,1,'down'],[null,2,'missing'],[NaN,1,'missing']])assert(context.compare(a,b,{verified:true}).includes('rc-compare-'+state));
assert(context.compare(4,2,{}).includes('missing'));assert(!context.compare(4,2,{verified:true,label:'<script>'}).includes('<script>'));
const data={worldFlow:JSON.parse(fs.readFileSync(__dirname+'/../stock-world-flow.json')),macro:JSON.parse(fs.readFileSync(__dirname+'/../stock-market-context.json'))};
for(const [key,sym] of [['kospi','^KS11'],['kosdaq','^KQ11'],['nasdaq','^IXIC']]){const x=context.indexRecord(data,key,sym);assert(x.verified);assert(context.compare(x.value,x.previous,{verified:x.verified}).includes('down'));}
const c=JSON.parse(fs.readFileSync(__dirname+'/../stock-opportunity-data.json')).companies.find(c=>c.symbol==='005930');assert(context.annualComparison(c.history));const h=structuredClone(c.history);h.revenue_growth_evidence.source.currency='USD';assert(!context.annualComparison(h));
assert(src.includes('+vals[i]+'));assert(!src.includes('+esc(vals[i])+'));
console.log('core comparison tests passed');
vm.runInContext(`const amount=v=>fmt(v),pill=()=>'',spark=()=>'',id=c=>c.symbol,empty=()=>'',greendata=null;let candidateNo=0,showcaseCount=0;const strictCandidate=()=>false;`+extract('function candidatePanel(','function kstDay('),context);
const html=context.candidatePanel({companies:[c],company:c,data:{raw:{}},helpers:{}});assert(!html.includes('&lt;span'));assert((html.match(/rc-compare-up/g)||[]).length>=6);assert((html.match(/rc-compare-missing/g)||[]).length===5);assert(html.indexOf('매출')<html.indexOf('영업이익'));
console.log('Home Samsung rendered arrows verified: annual 6 up; snapshot debt/cash and valuation 5 unavailable');
