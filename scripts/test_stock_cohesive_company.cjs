const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const window={RadarCohesive:{}};vm.runInNewContext(fs.readFileSync(__dirname+'/../assets/radar-cohesive-company.js','utf8'),{window,URL});const m=window.RadarCohesiveCompany;
assert.match(m.quality(null),/기업을 선택/);assert.match(m.finance(null),/기업을 선택/);
const missing=m.finance({});assert.match(missing,/판단 보류/);assert(!missing.includes('NaN'));assert(!missing.includes('Infinity'));
const unsafe=m.quality({business:{summary:'<img src=x onerror=alert(1)>',website:'javascript:alert(1)'},sources:{profile:'javascript:alert(2)'}});
assert(!unsafe.includes('<img'));assert(!unsafe.includes('href="javascript:'));assert.match(unsafe,/&lt;img/);
const c={history:{currency:'KRW',revenue:0,operating_income:0,cfo:0,filing_period:'2025-12-31',basis:'최근 연간 수치 (TTM 아님)'},balance:{cash:123,currency:'USD'}};
let html=m.finance(c);assert.match(html,/0억 KRW/);assert(!html.includes('123'));assert(!html.includes('NaN'));assert(!html.includes('Infinity'));
const order=['매출','영업이익','영업이익률','영업현금흐름','매출채권/재고','부채/현금','PER/PBR/ROE'].map(x=>html.indexOf('tabindex="0">'+x+'<'));
assert(order.every((v,i)=>v>=0&&(i===0||v>order[i-1])));assert.match(html,/tabindex="0"/);assert.match(html,/role="tooltip"/);
const live=JSON.parse(fs.readFileSync(__dirname+'/../stock-opportunity-data.json')).companies;
for(const company of live){for(const f of [m.quality,m.finance]){const h=f(company,{});assert(!h.includes('undefined'));assert(!h.includes('NaN'));assert(!h.includes('Infinity'));}}
console.log('PASS: missing, zero, unknown currency, XSS, unsafe URLs, seven-card order, focus tooltip, '+live.length+' existing companies');
