'use strict';
// Read-only paired cohort diagnostic. Operating forecasts and history stay untouched.
const fs=require('node:fs'), crypto=require('node:crypto');
const CLASSES=['down','flat','up'];
const PINNED={
 'stock-forecast-ledger.jsonl':'7eace60187c32cafa1bf10b628c2fd33c020de72',
 'stock-forecast-outcomes.jsonl':'e102f7a9cc5b53dad00740d72abc49897c79d896',
 'stock-forecast-learning-events.jsonl':'f4f61b06a7f39450a263014a8dd0f8aae549c2dc',
 'stock-forecast-deliveries.jsonl':'814bd0cf4e80ffa390adb54f4c29a75b70252183'
};
function ok(condition,msg){if(!condition)throw Error(msg);}
function date(s,label){let v=Date.parse(s);ok(Number.isFinite(v),'invalid '+label);return v;}
function index(rows,k,label){let m=new Map();for(const r of rows){let id=r[k];ok(typeof id==='string'&&id.length,'missing '+label+' ID');ok(!m.has(id),'duplicated '+label+' ID '+id);m.set(id,r);}return m;}
function probs(p,label){ok(p&&CLASSES.every(k=>Number.isFinite(p[k])&&p[k]>=0&&p[k]<=1),'invalid probabilities '+label);ok(Math.abs(CLASSES.reduce((a,k)=>a+p[k],0)-1)<1e-8,'unnormalized probabilities '+label);return p;}
function choose(p){return CLASSES.reduce((a,b)=>p[b]>p[a]?b:a,CLASSES[0]);}
const VECTORS={
 incumbent:f=>({p:f.probabilities,d:f.direction}),
 frequency:f=>({p:f.frozen_baseline_probabilities}),
 online_challenger:f=>({p:f.online_learning?.challenger_probabilities}),
 movement_then_direction:f=>({p:f.directional_specialists?.candidates?.movement_then_direction?.probabilities,d:f.directional_specialists?.candidates?.movement_then_direction?.direction}),
 balanced_linear:f=>({p:f.directional_specialists?.candidates?.balanced_linear?.probabilities,d:f.directional_specialists?.candidates?.balanced_linear?.direction}),
 balanced_nonlinear:f=>({p:f.directional_specialists?.candidates?.balanced_nonlinear?.probabilities,d:f.directional_specialists?.candidates?.balanced_nonlinear?.direction})
};
function score(cohort,vector){
 const cm=[[0,0,0],[0,0,0],[0,0,0]];let n=0,correct=0,brier=0,logloss=0;
 const bySymbol=[];
 for(const {f,o} of cohort){
  const v=vector(f);ok(v&&v.p,'missing frozen candidate '+f.id);
  const p=probs(v.p,f.id),d=v.d||choose(p);ok(d===choose(p),'candidate direction mismatch '+f.id);
  const a=o.actual;ok(CLASSES.includes(a),'unknown actual '+f.id);
  cm[CLASSES.indexOf(a)][CLASSES.indexOf(d)]++;
  brier+=CLASSES.reduce((z,k)=>z+(p[k]-(k===a?1:0))**2,0);
  logloss-=Math.log(Math.max(1e-15,p[a]));n++;if(a===d)correct++;
  bySymbol.push({symbol:f.symbol,actual:a,predicted:d,correct:a===d});
 }
 const directions={};
 for(let i=0;i<CLASSES.length;i++){
  const a=cm[i].reduce((x,y)=>x+y,0),calls=cm.reduce((x,row)=>x+row[i],0),hits=cm[i][i];
  directions[CLASSES[i]]={actual:a,calls,hits,missed:a-hits,false_calls:calls-hits,recall:a?hits/a:null,precision:calls?hits/calls:null};
 }
 return {n,correct,accuracy:correct/n,brier_loss:brier/n,log_loss:logloss/n,confusion_matrix:cm,directions,collapse_to_flat:directions.up.calls===0&&directions.down.calls===0,by_symbol:bySymbol};
}
function evaluateCohort({ledger,outcomes,learning,deliveries,start,end,expected=12}){
 const lidx=index(ledger,'id','forecast'),oidx=index(outcomes,'id','outcome'),eidx=index(learning,'prediction_id','learning');
 index(deliveries,'verification_id','delivery');
 const cohort=[];
 for(const f of ledger){
  if(f.market!=='US'||f.mode!=='daily'||f.target?.start!==start||f.target?.end!==end)continue;
  const o=oidx.get(f.id),e=eidx.get(f.id);
  ok(o&&e,'matured missing result/learning stays unknown '+f.id);
  ok(o.symbol===f.symbol&&o.mode===f.mode&&o.target?.start===start&&o.target?.end===end&&o.status==='observed','target mismatch '+f.id);
  ok(e.actual===o.actual&&e.kind==='learn_after_score'&&o.issued_at===f.issued_at,'learning/outcome provenance mismatch '+f.id);
  const times=[date(f.observed_until,'observation'),date(f.received_at,'receipt'),date(f.issued_at,'issuance'),date(start,'target start'),date(end,'target end'),date(o.source_checked_at,'source check'),date(o.evaluated_at,'evaluation'),date(e.available_at,'learning available'),date(e.learned_at,'learning event')];
  ok(times.every((v,i)=>i===0||v>=times[i-1])&&times[2]<times[3]&&times[3]<times[4],'chronology violation '+f.id);
  ok(o.public_before_target_verified===true&&date(o.delivery_verified_at,'first public')<times[3],'no first public before target '+f.id);
  ok(deliveries.some(d=>d.status==='public_verified'&&d.prediction_ids?.includes(f.id)&&date(d.verified_at,'delivery verify')<times[3]),'no public verification record '+f.id);
  ok(f.neutral_band_pct>0&&o.target_open>0&&o.target_close>0,'invalid price/band '+f.id);
  const pct=100*(o.target_close/o.target_open-1);
  const actual=pct>f.neutral_band_pct?'up':pct< -f.neutral_band_pct?'down':'flat';
  ok(Math.abs(pct-o.return_pct)<1e-7&&actual===o.actual&&o.predicted===f.direction&&o.correct===(f.direction===actual),'return/label error '+f.id);
  const p=probs(f.probabilities,f.id);
  const b=CLASSES.reduce((z,k)=>z+(p[k]-(k===actual?1:0))**2,0);
  ok(choose(p)===f.direction&&Math.abs(b-o.brier_loss)<1e-8,'frozen probability/Brier error '+f.id);
  cohort.push({f,o});
 }
 ok(cohort.length===expected,'expected '+expected+' complete original rows, got '+cohort.length);
 ok(new Set(cohort.map(x=>x.f.symbol)).size===cohort.length,'overlapping symbol/target');
 const methods=Object.fromEntries(Object.entries(VECTORS).map(([name,vector])=>[name,score(cohort,vector)]));
 const days=new Set(cohort.map(x=>x.f.target.start.slice(0,10)));
 const dirs=methods.incumbent.directions;
 const minimum=cohort.length>=120&&days.size>=20&&CLASSES.every(k=>dirs[k].actual>=10)&&dirs.up.calls>=10&&dirs.down.calls>=10;
 return {status:'descriptive_only_not_selection',source:'single-provider, not exchange-authenticated',
  cohort:{market:'US',mode:'daily',start,end,scored:cohort.length,market_days:[...days],symbols:cohort.map(x=>x.f.symbol),original_ids:cohort.map(x=>x.f.id)},
  archive_counts:{original_ledger:ledger.length,outcomes:outcomes.length,learning_events:learning.length,delivery_events:deliveries.length},
  methods,minimum_group_gate_met:minimum,independent_untouched_confirmation:false,
  exchange_raw_prices_verified:false,human_receipt_verified:deliveries.some(d=>d.human_notification_received===true),
  executable_quotes_verified:false,after_cost_edge_verified:false,timing_utility:'not_proven',orders_enabled:false};
}
function gitBlobSha(bytes){return crypto.createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');}
function main(){
 const root=process.argv[2]||'.',files={},fingerprints={};
 for(const [filename,sha] of Object.entries(PINNED)){
  const bytes=fs.readFileSync(require('node:path').join(root,filename));
  ok(gitBlobSha(bytes)===sha,'changed original blob: '+filename+'; refuse reuse of this examined cohort');
  files[filename]=bytes.toString('utf8').split(/\r?\n/).filter(Boolean).map(JSON.parse);
  fingerprints[filename]={git_blob_sha1:sha,content_sha256:crypto.createHash('sha256').update(bytes).digest('hex')};
 }
 const report=evaluateCohort({ledger:files['stock-forecast-ledger.jsonl'],outcomes:files['stock-forecast-outcomes.jsonl'],
  learning:files['stock-forecast-learning-events.jsonl'],deliveries:files['stock-forecast-deliveries.jsonl'],
  start:'2026-11-13T14:30:00+00:00',end:'2026-11-13T21:00:00+00:00'});
 report.source_fingerprints=fingerprints;
 process.stdout.write(JSON.stringify(report,null,2)+'\n');
}
if(require.main===module){try{main();}catch(e){process.stderr.write('RESEARCH_ONLY_AUDIT_REJECTED '+e.message+'\n');process.exitCode=1;}}
module.exports={evaluateCohort,gitBlobSha};
