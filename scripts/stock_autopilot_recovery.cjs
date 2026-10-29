'use strict';
const allowed=new Set(['Install model and session readers','Request public build','Verify exact public predictions, directional report and code','Verify public autonomous cycle and code']);
function plan(run,jobs,repository){
 if(run.name!=='Stock Prospective Forecasts'||run.path!=='.github/workflows/stock-forecasts.yml')return {retry:false,reason:'not_owned_workflow'};
 if(run.head_branch!=='main'||run.head_repository?.full_name!==repository)return {retry:false,reason:'untrusted_or_research_branch'};
 if(run.conclusion!=='failure'||run.run_attempt!==1)return {retry:false,reason:'not_first_failure'};
 const failures=jobs.flatMap(j=>j.steps||[]).filter(s=>s.conclusion==='failure').map(s=>s.name);
 if(!failures.length||failures.some(n=>!allowed.has(n)))return {retry:false,reason:'needs_diagnosis_not_blind_rerun',failures};
 return {retry:true,reason:'single_infrastructure_retry',failures};
}
module.exports={plan};
if(require.main===module){const assert=require('node:assert/strict');const r={name:'Stock Prospective Forecasts',path:'.github/workflows/stock-forecasts.yml',head_branch:'main',head_repository:{full_name:'a/b'},conclusion:'failure',run_attempt:1};const jobs=[{steps:[{name:'Request public build',conclusion:'failure'}]}];assert.equal(plan(r,jobs,'a/b').retry,true);assert.equal(plan({...r,run_attempt:2},jobs,'a/b').retry,false);assert.equal(plan({...r,conclusion:'success'},jobs,'a/b').retry,false);assert.equal(plan({...r,head_branch:'fork'},jobs,'a/b').retry,false);assert.equal(plan(r,jobs,'other/repo').retry,false);assert.equal(plan(r,[{steps:[{name:'Test future targets',conclusion:'failure'}]}],'a/b').retry,false);assert.equal(plan(r,[],'a/b').retry,false);console.log('7 bounded infrastructure recovery checks passed');}
