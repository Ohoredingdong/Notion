/* Fail-closed screening tests: AI direction must never become a buying probability. */
const fs = require('fs');
const assert = require('node:assert/strict');
const js = fs.readFileSync('assets/stock-radar-flow-v2.js','utf8');
const start = js.indexOf('const FX_EVIDENCE_IDS=');
const end = js.indexOf('\nfunction fxDetail(ctx){',start);
assert(start >= 0 && end > start, 'review logic must exist in the production widget');
const block = js.slice(start,end);
const ids = ['inputs','official','cash_quality','working_capital','earnings_quality','debt','business','valuation','macro','governance','forecast','liquidity'];
let linked;
const evaluate = new Function('fxHelpers',block+'\nreturn fxInvestmentEvidence;')(()=>({caseOf:()=>linked}));
const now = Date.now(), stamp = ms=>new Date(ms).toISOString();
const raw = {generated_at: stamp(now-60*1000)};
const stock = {symbol:'DEMO',price:100,price_session:'2026-11-05',forecasts:{next_fy:{avg:8}}};
function make(overrides={}) {
  const checks=ids.map(id=>({id,status:'pass'}));
  for(const [id,status] of Object.entries(overrides))checks.find(x=>x.id===id).status=status;
  linked={state:'attractive',input_price:100,input_price_session:stock.price_session,
    input_forecast_eps:8,green_review:{source_generated_at:raw.generated_at,reviewed_at:stamp(now-20*1000),
    valid_until:stamp(now+120*60*1000),green_eligible:true,checks}};
  return evaluate(stock,{data:{raw,direction:{records:[{symbol:'DEMO',probabilities:{up:.99}}]}}});
}
let n=0;const check=(x,message)=>{assert(x,message);n++};
let a=make();
check(a.available&&a.percent===100&&a.eligible&&a.status==='조건부 매수 검토','12 verified checks can qualify');
check(a.groups.length===4,'all four fundamentals/risk groups are displayed');
a=make({valuation:'missing'});
check(a.available&&a.percent===92&&!a.eligible&&a.status==='검증 대기','99% AI must not bypass missing independent valuation');
check(a.groups[2].value==='근거 부족','valuation warning must appear');
a=make({macro:'review'});
check(!a.eligible&&a.status==='위험 검토','unresolved political or macro risk blocks approval');
a=make({inputs:'blocked'});
check(!a.eligible&&a.status==='자료 충돌','mismatched source snapshots block approval');
a=make();linked.green_review.checks.pop();a=evaluate(stock,{data:{raw}});
check(!a.available&&a.percent===null,'incomplete checklist must not show a percentage');
a=make();linked.green_review.valid_until=stamp(now-1000);a=evaluate(stock,{data:{raw}});
check(!a.available&&!a.eligible,'expired research must fail closed');
a=make();linked.input_price=105;a=evaluate(stock,{data:{raw}});
check(!a.available,'mismatched entry prices must fail closed');
a=make();linked.green_review.checks[0].id='official';a=evaluate(stock,{data:{raw}});
check(!a.available,'duplicate IDs and missing criterion must fail closed');
a=make({valuation:'missing',forecast:'missing',cash_quality:'review'});
check(a.percent===75&&!a.eligible,'a high partial coverage rate is not buying probability');
check(block.includes('FX_EVIDENCE_IDS')&&!block.includes('probabilities.up'),'direction likelihood does not affect checklist coverage');
console.log('PASS: '+n+' independent composite investment screening assertions');
