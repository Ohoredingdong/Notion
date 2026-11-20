'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {evaluateCohort,gitBlobSha}=require('./research_forward_cohort_audit.cjs');
const START='2026-11-13T14:30:00+00:00',END='2026-11-13T21:00:00+00:00';
const p={down:{down:.8,flat:.1,up:.1},flat:{down:.1,flat:.8,up:.1},up:{down:.1,flat:.1,up:.8}};
function fixture(){
 const ledger=[],outcomes=[],learning=[],types=[['AAPL','down',-2],['META','up',2],['DOCS','flat',0]];
 for(const [symbol,actual,movement] of types){
  const id='id-'+symbol,f={id,symbol,market:'US',mode:'daily',
   observed_until:'2026-11-12T21:00:00+00:00',received_at:'2026-11-12T23:53:30+00:00',
   issued_at:'2026-11-12T23:54:01+00:00',target:{start:START,end:END},
   neutral_band_pct:1,probabilities:p.flat,direction:'flat',
   frozen_baseline_probabilities:p.down,online_learning:{challenger_probabilities:p.up},
   directional_specialists:{candidates:Object.fromEntries(['movement_then_direction','balanced_linear','balanced_nonlinear'].map(k=>[k,{probabilities:p.flat,direction:'flat'}]))}};
  ledger.push(f);
  const brier=['down','flat','up'].reduce((v,k)=>v+(p.flat[k]-(k===actual?1:0))**2,0);
  outcomes.push({id,symbol,mode:'daily',status:'observed',issued_at:f.issued_at,target:f.target,
    target_open:100,target_close:100+movement,return_pct:movement,actual,predicted:'flat',
    correct:actual==='flat',brier_loss:brier,evaluated_at:'2026-11-14T00:58:18+00:00',
    source_checked_at:'2026-11-14T00:58:18+00:00',public_before_target_verified:true,
    delivery_verified_at:'2026-11-12T23:55:00+00:00'});
  learning.push({prediction_id:id,kind:'learn_after_score',actual,available_at:'2026-11-14T00:58:18+00:00',learned_at:'2026-11-14T00:58:19+00:00'});
 }
 const deliveries=[{status:'public_verified',verification_id:'first-public-1',
  verified_at:'2026-11-12T23:55:00+00:00',prediction_ids:ledger.map(x=>x.id),human_notification_received:false}];
 return {ledger,outcomes,learning,deliveries,start:START,end:END,expected:3};
}
test('flat-only candidate cannot pass two-way direction criteria',()=>{
 const r=evaluateCohort(fixture());
 assert.equal(r.cohort.scored,3);assert.equal(r.methods.movement_then_direction.correct,1);
 assert.equal(r.methods.movement_then_direction.directions.up.precision,null);
 assert.equal(r.methods.movement_then_direction.directions.down.recall,0);
 assert.equal(r.methods.movement_then_direction.collapse_to_flat,true);
 assert.equal(r.minimum_group_gate_met,false);assert.equal(r.timing_utility,'not_proven');
});
test('original neutral band, return and Brier remain immutable',()=>{
 const a=fixture();a.outcomes[0].actual='flat';assert.throws(()=>evaluateCohort(a),/learning\/outcome provenance mismatch|return\/label error/);
 const b=fixture();b.outcomes[0].return_pct=0;assert.throws(()=>evaluateCohort(b),/return\/label error/);
 const c=fixture();c.outcomes[0].brier_loss=.01;assert.throws(()=>evaluateCohort(c),/Brier error/);
});
test('future inputs or late publication reject the cohort',()=>{
 const a=fixture();a.ledger[0].received_at='2026-11-13T15:00:00+00:00';assert.throws(()=>evaluateCohort(a),/chronology violation/);
 const b=fixture();b.deliveries[0].verified_at='2026-11-13T15:00:00+00:00';assert.throws(()=>evaluateCohort(b),/public verification record/);
});
test('duplicate outcomes and learning events are not counted twice',()=>{
 const a=fixture();a.outcomes.push({...a.outcomes[0]});assert.throws(()=>evaluateCohort(a),/duplicated outcome/);
 const b=fixture();b.learning.push({...b.learning[0]});assert.throws(()=>evaluateCohort(b),/duplicated learning/);
});
test('missing outcomes or original frozen challengers are not filled in',()=>{
 const a=fixture();a.outcomes.pop();assert.throws(()=>evaluateCohort(a),/matured missing result/);
 const b=fixture();delete b.ledger[0].directional_specialists.candidates.balanced_linear;assert.throws(()=>evaluateCohort(b),/missing frozen candidate/);
});
test('one public website verification is not user receipt or executable quote proof',()=>{
 const r=evaluateCohort(fixture());
 assert.equal(r.human_receipt_verified,false);assert.equal(r.executable_quotes_verified,false);
 assert.equal(r.after_cost_edge_verified,false);assert.equal(r.exchange_raw_prices_verified,false);
 assert.equal(r.orders_enabled,false);
});
test('Git source object fingerprint is byte-specific',()=>{
 assert.equal(gitBlobSha(Buffer.from('test\n')),'9daeafb9864cf43055ae93beb0afd6c7d144bfa4');
});
