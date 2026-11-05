/* Regression checks for issuer identity and source-limited financial display. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const sandbox = {window:{},document:{addEventListener(){},getElementById(){return null}}};
vm.runInNewContext(fs.readFileSync('assets/stock-catalog-ui.js','utf8'),sandbox);
const ui = sandbox.window.StockCatalogUI;
const issuer = {country:'KR',symbol:'0001A0',name:'덕양에너젠',exchange:'KOSPI'};
const record = {country:'KR',symbol:'0001A0',catalog_name:'덕양에너젠',identity_verified:true,corp_code:'12345678',
  status:'partial',source:'DART periodic reports',currency:'KRW',metrics:{revenue:123456789},
  checked_at:'2026-11-05T10:00:00+00:00',period_end:'2026-06-30'};
function context(row=record) {
  return {data:{catalog:{identifier_policy:'kr-six-character-alphanumeric-v2',generated_at:'2026-11-05T10:00:00Z',items:[issuer]},
    financial:{identity_policy:'official-issuer-identity-v2',catalog_generated_at:'2026-11-05T10:00:00Z',records:{'KR:0001A0':row}}}};
}
let checks = 0;
function check(name,fn) { fn();checks++;console.log('PASS',name); }
check('Verified matching issuer can display its statement',()=>{
  const ctx=context();assert.equal(ui.statement(issuer,ctx),record);assert.equal(ui.verifiedCount(ctx),1);
  assert.match(ui.statementPanel(issuer,ctx),/1\.235억 원/);
});
check('Missing fields are uncollected, not a claim of no filing',()=>{
  const panel=ui.statementPanel(issuer,context());
  assert.match(panel,/미수집·미확인/);assert.doesNotMatch(panel,/공시 없음/);
});
check('Pre-migration finance feed is not displayable',()=>{
  const ctx=context();delete ctx.data.financial.identity_policy;
  assert.equal(ui.statement(issuer,ctx),null);assert.equal(ui.verifiedCount(ctx),0);
});
check('Unverified historical values cannot reach the panel or counts',()=>{
  const ctx=context({...record,identity_verified:false,metrics:{revenue:987654321}});
  assert.equal(ui.statement(issuer,ctx),null);assert.equal(ui.verifiedCount(ctx),0);
  assert.doesNotMatch(ui.statementPanel(issuer,ctx),/9\.877억 원/);
});
check('Wrong symbol/name/country/corporate identifier is rejected',()=>{
  for(const changes of [{symbol:'000010'},{catalog_name:'다른 회사'},{country:'US'},{corp_code:''},{corp_code:'123'}]) {
    assert.equal(ui.statement(issuer,context({...record,...changes})),null);
  }
});
check('Old numeric-stripped catalogue cannot be counted as verified',()=>{
  const ctx=context();delete ctx.data.catalog.identifier_policy;
  assert.equal(ui.verifiedCount(ctx),0);
});
check('Mixed publication snapshots cannot attach finance to a newer directory',()=>{
  const ctx=context();ctx.data.catalog.generated_at='2026-11-05T10:05:00Z';
  assert.equal(ui.statement(issuer,ctx),null);assert.equal(ui.verifiedCount(ctx),0);
});
check('Error-only record is not financial coverage',()=>{
  assert.equal(ui.verifiedCount(context({...record,status:'source_blocked'})),0);
  assert.match(ui.statementPanel(issuer,context({...record,status:'source_blocked'})),/아직 미확인/);
});
check('Previously verified values expose latest refresh failure',()=>{
  assert.match(ui.statementPanel(issuer,context({...record,last_refresh_error:'HTTP 403'})),/최근 재수집 실패/);
});
check('Partial coverage reports failure only when the current run actually failed',()=>{
  const ctx=context();
  ctx.data.financial.refresh_status='partial';ctx.data.financial.current_run_failed=false;
  assert.match(ui.panel(ctx),/법인 대조 재무 1개 · 일부 미확인/);
  assert.doesNotMatch(ui.panel(ctx),/일부 수집 실패/);
  ctx.data.financial.current_run_failed=true;
  assert.match(ui.panel(ctx),/법인 대조 재무 1개 · 일부 수집 실패/);
});
check('Financial amounts preserve reported currencies without implying a USD conversion',()=>{
  for(const currency of ['USD','CNY','JPY','GBP','EUR','HKD']) {
    const panel=ui.statementPanel(issuer,context({...record,currency,metrics:{revenue:1000000,reported_eps:1.25}}));
    assert.ok(panel.includes('1M '+currency));assert.ok(panel.includes('1.25 '+currency+'/주'));
    if(currency!=='USD')assert.doesNotMatch(panel,/ USD/);
  }
  assert.match(ui.statementPanel(issuer,context({...record,currency:'KRW',metrics:{revenue:100000000}})),/1억 원/);
  assert.match(ui.statementPanel(issuer,context({...record,currency:'JPY',metrics:{revenue:-1000000}})),/−1M JPY/);
});
check('Missing or unrecognized currency is unconfirmed rather than defaulting to USD',()=>{
  for(const currency of [undefined,null,'','unknown','ZZZ','XXX']) {
    const panel=ui.statementPanel(issuer,context({...record,currency,metrics:{revenue:1000000,reported_eps:1.25}}));
    assert.match(panel,/통화 미확인/);assert.doesNotMatch(panel,/ USD|undefined\/주|null\/주|ZZZ\/주|XXX\/주/);
  }
});
check('US statement requires exact ticker plus SEC CIK',()=>{
  const us={country:'US',symbol:'FN',name:'Fabrinet'},row={...record,country:'US',symbol:'FN',catalog_name:'Fabrinet',cik:'0012345678'};
  const ctx=context();ctx.data.catalog.items=[us];ctx.data.financial.records={'US:FN':row};
  assert.equal(ui.statement(us,ctx),row);delete row.cik;assert.equal(ui.statement(us,ctx),null);
});
check('Public filing source labels and links cannot inject HTML',()=>{
  const ctx=context({...record,source:'<img src=x onerror=alert(1)>',source_url:'javascript:alert(1)'});
  const panel=ui.statementPanel(issuer,ctx);
  assert.doesNotMatch(panel,/<img|href="javascript:/);assert.match(panel,/&lt;img/);
});
console.log('CATALOG_INTEGRITY_PASS',checks);
