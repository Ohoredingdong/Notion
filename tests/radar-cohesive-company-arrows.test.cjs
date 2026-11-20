const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const window={RadarCohesive:{compare:(a,b,o)=>`<i data-compare="${o.verified?(a>b?'up':a<b?'down':'flat'):'unknown'}"></i>`}};
vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname,'../assets/radar-cohesive-company.js'),'utf8'),{window,URL});
const h={basis:'annual',currency:'USD',filing_period:'2025-12-31',revenue_previous_period:'2024-12-31',supplemental_period_status:'same_period',revenue:200,revenue_previous:100,operating_income:10,operating_income_previous:20,cfo:5,cfo_previous:5,fcf:-5,fcf_previous:-10,capex:10,capex_previous:15,eps:2,eps_previous:1};
h.revenue_growth_evidence={status:'verified',source:{identity_verified:true,currency:'USD'},source_rows:{current:{value:200,period:h.filing_period},prior:{value:100,period:h.revenue_previous_period}}};
const company={history:h,valuation:{trailing_pe:20,book_value_per_share:5},balance:{currency:'USD',cash:30}};
const render=c=>window.RadarCohesiveCompany.finance(c);
let out=render(company);assert.match(out,/매출<\/th>(?:(?!<\/tr>).)*?data-compare="up"/s);assert.match(out,/data-compare="down"/);assert.match(out,/data-compare="flat"/);assert.match(out,/PER\(TTM\)(?:(?!<\/tr>).)*?data-compare="unknown"/s);assert.match(out,/FCF (?:(?!<\/tr>).)*?data-compare="up"/s);assert.match(out,/BPS\(제공처\)(?:(?!<\/tr>).)*?data-compare="unknown"/s);
for(const change of [{supplemental_period_status:'period_mismatch'},{basis:'quarterly'},{currency:'KRW'},{revenue_growth_evidence:{status:'unverified'}}]){
 out=render({...company,history:{...h,...change}});assert.match(out,/영업이익<\/th>(?:(?!<\/tr>).)*?data-compare="unknown"/s);
}
out=render({...company,history:{...h,supplemental_excluded_fields:[{field:'operating_income_previous'}]}});assert.match(out,/영업이익<\/th>(?:(?!<\/tr>).)*?data-compare="unknown"/s);
assert.match(render({...company,history:{...h,cfo:NaN}}),/영업현금흐름<\/th>(?:(?!<\/tr>).)*?data-compare="unknown"/s);
assert.match(render({}),/총부채\/자본 검증 전/);assert.match(render(null),/기업을 선택/);
console.log('company financial arrows: 14 assertions passed');
