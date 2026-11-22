/**
 * Lotto 6/45 — auditable, prospective-only prediction evaluation.
 * Built-in Node.js modules only; NO future draw information in forecasts.
 * Prediction records are sealed before the sale cutoff and never rewritten.
 *
 * Scientific policy: A future success is only reported if the prediction was
 * committed before the draw. No finite test proves 100% future accuracy.
 */
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT=".";
const PATHS={
 history:ROOT+"/lotto-research-history.json",
 state:ROOT+"/lotto-research-state.json",
 ledger:ROOT+"/lotto-prediction-ledger.json"
};
const SOURCE_A="https://raw.githubusercontent.com/youngeun9100/project-l-data/main/data/winning_numbers.json";
const SOURCE_B="https://raw.githubusercontent.com/papaya5rhw1984/lotto-data/main/all.json";
const MODEL_VERSION="prospective-v1.0.0";
const METHODS=[
  ["logit","로지스틱 회귀 AI"],["ridge","릿지 회귀 AI"],
  ["stump","결정나무(단일분기) AI"],["hot30","최근 30회 빈도"],
  ["hotall","전체 누적 빈도"],["random","무작위 기준선"]
];
const EVIDENCE_IDS=METHODS.filter(x=>x[0]!=="random").map(x=>x[0]);
const LAMBDAS=[0.15,0.3,0.6,1.0];
const ALPHA=.01;
const COMBINATIONS=8145060;
const h=txt=>crypto.createHash("sha256").update(txt).digest("hex");
const canonical=o=>JSON.stringify(o);
const toDate=(iso)=>new Date(iso+"T12:00:00+09:00");
const plusDays=(str,days)=>new Date(toDate(str).getTime()+days*86400000).toISOString().slice(0,10);
const readJson=(path,fallback)=>fs.existsSync(path)?JSON.parse(fs.readFileSync(path,"utf8")):fallback;
const saveJson=(path,value)=>fs.writeFileSync(path,JSON.stringify(value,null,2)+"\n");
const roundTo=(v,n=6)=>Math.round(v*10**n)/10**n;

function clean(raw,source){
  let arr=source==="a"?raw.draws:raw;
  if(!Array.isArray(arr)||arr.length<1000)throw new Error(source+" history unavailable/incomplete");
  let rows=arr.map((x,i)=>({
    draw:source==="a"?x.draw:x.draw_no,
    date:String(x.date).slice(0,10),
    numbers:(source==="a"?x.numbers:x.numbers).slice().sort((a,b)=>a-b),
    bonus:source==="a"?x.bonus:x.bonus_no
  }));
  if(rows.some((r,i)=>r.draw!==i+1||!/^20\d\d-\d\d-\d\d$/.test(r.date)||
    r.numbers.length!==6||new Set(r.numbers).size!==6||
    r.numbers.some(n=>!Number.isInteger(n)||n<1||n>45)||
    !Number.isInteger(r.bonus)||r.bonus<1||r.bonus>45||r.numbers.includes(r.bonus)))
    throw new Error(source+" invalid draw entries");
  return rows;
}
async function fetchJson(url){
  const controller=new AbortController();
  const tid=setTimeout(()=>controller.abort(),24000);
  try{
    const r=await fetch(url+(url.includes("?")?"&":"?")+"lotto_ts="+Date.now(),{
      signal:controller.signal,headers:{"User-Agent":"Notion-Lotto-Research/1.0","Accept":"application/json"}});
    if(!r.ok)throw new Error(url+" returned HTTP "+r.status);
    return await r.json();
  }finally{clearTimeout(tid);}
}
async function verifiedHistory(){
  const [a,b]=await Promise.all([fetchJson(SOURCE_A),fetchJson(SOURCE_B)]);
  const A=clean(a,"a"),B=clean(b,"b");
  if(A.length!==B.length)throw new Error("Sources have different latest rounds: "+A.length+"/"+B.length+". No update.");
  for(let i=0;i<A.length;i++)if(canonical(A[i])!==canonical(B[i]))
    throw new Error("Independent sources disagree on round "+(i+1)+". No update.");
  const saved=readJson(PATHS.history,null);
  if(saved){
    if(!Array.isArray(saved.draws)||saved.draws.length>A.length)throw new Error("History regression: existing data longer");
    for(let i=0;i<saved.draws.length;i++)if(canonical(saved.draws[i])!==canonical(A[i]))
      throw new Error("Previously verified draw changed: "+(i+1));
  }
  return A;
}
function build(draws){
 const y=draws.map(d=>new Set(d.numbers)),N=draws.length;
 const cnt=Array.from({length:N+1},()=>new Uint16Array(46));
 const last=Array.from({length:N+1},()=>new Uint16Array(46));
 for(let t=0;t<N;t++){
  cnt[t+1].set(cnt[t]);last[t+1].set(last[t]);
  for(const n of draws[t].numbers){cnt[t+1][n]++;last[t+1][n]=t+1;}
 }
 const f=(t,n)=>{
  function z(span){
   const s=Math.min(t,span),freq=cnt[t][n]-cnt[t-s][n],mean=s*6/45,
    sd=Math.sqrt(s*(6/45)*(39/45));
   return Math.max(-2,Math.min(2,(freq-mean)/Math.max(sd,.01)))/2;
  }
  const t0=Math.max(1,t),mean=t0*6/45,sd=Math.sqrt(t0*(6/45)*(39/45));
  return [1,(n-23)/23,Math.max(-2,Math.min(2,(cnt[t][n]-mean)/Math.max(sd,.01)))/2,
   z(10),z(30),z(100),Math.min(100,t-last[t][n])/50-1,
   t>0?Number(y[t-1].has(n)):0,t>1?Number(y[t-2].has(n)):0,
   (n%2)-.5,Math.sin(2*Math.PI*n/10),Math.cos(2*Math.PI*n/10)];
 };
 return {draws,y,cnt,last,f};
}
const sigmoid=v=>1/(1+Math.exp(-Math.max(-15,Math.min(15,v))));
function trainSGD(ctx,end,kind){
 const w=new Float64Array(12),isLog=kind==="logit";
 w[0]=isLog?Math.log(6/39):6/45;
 for(let t=101;t<end;t++){
  const g=new Float64Array(12);
  for(let n=1;n<=45;n++){
   const x=ctx.f(t,n);
   let v=0;for(let j=0;j<12;j++)v+=w[j]*x[j];
   const prediction=isLog?sigmoid(v):v;
   const err=Number(ctx.y[t].has(n))-prediction;
   for(let j=0;j<12;j++)g[j]+=err*x[j]/45;
  }
  const lr=(isLog?.05:.12)/Math.sqrt(1+(t-101)/250);
  for(let j=0;j<12;j++)w[j]+=lr*(g[j]-(j===0?0:.003*w[j]));
 }
 return Array.from(w);
}
function trainStump(ctx,end){
 // Fixed 30-draw-frequency feature and threshold zero: no test-driven tuning.
 const pos=[0,0],total=[0,0];
 for(let t=101;t<end;t++)for(let n=1;n<=45;n++){
  const bucket=ctx.f(t,n)[4]>=0?1:0;
  total[bucket]++;pos[bucket]+=Number(ctx.y[t].has(n));
 }
 return total.map((num,k)=>(pos[k]+6)/(num+45));
}
function fit(ctx,end){return {logit:trainSGD(ctx,end,"logit"),ridge:trainSGD(ctx,end,"ridge"),stump:trainStump(ctx,end)};}
function predictScores(ctx,t,models,id){
 const out=new Float64Array(46);
 for(let n=1;n<=45;n++){
  if(id==="hot30")out[n]=ctx.cnt[t][n]-ctx.cnt[Math.max(0,t-30)][n];
  else if(id==="hotall")out[n]=ctx.cnt[t][n];
  else if(id==="stump")out[n]=models.stump[ctx.f(t,n)[4]>=0?1:0];
  else if(id==="logit"||id==="ridge"){
   const x=ctx.f(t,n),w=models[id];
   let z=0;for(let j=0;j<12;j++)z+=x[j]*w[j];
   out[n]=id==="logit"?sigmoid(z):Math.max(0,Math.min(1,z));
  }
 }
 return out;
}
function randomTicket(round){
 let a=Array.from({length:45},(_,i)=>i+1);
 let seed=Number.parseInt(h("lotto-research-pinned-random-v1:"+round).slice(0,8),16)>>>0;
 const random=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return(seed>>>0)/4294967296;};
 for(let i=44;i>0;i--){const j=Math.floor(random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}
 return a.slice(0,6).sort((a,b)=>a-b);
}
function ticket(ctx,t,models,id){
 if(id==="random")return randomTicket(t+1);
 const sc=predictScores(ctx,t,models,id);
 return Array.from({length:45},(_,i)=>i+1).sort((a,b)=>sc[b]-sc[a]||a-b)
   .slice(0,6).sort((a,b)=>a-b);
}
function grade(nums,draw){
 const hit=nums.filter(n=>draw.numbers.includes(n)).length;
 return {hit,grade:hit===6?1:hit===5&&nums.includes(draw.bonus)?2:hit===5?3:hit===4?4:hit===3?5:0};
}
function brier(ctx,start,end,fitmodel){
 const results={};for(const id of ["logit","ridge","stump"])results[id]=0;
 for(let t=start;t<end;t++)for(const id of Object.keys(results)){
  const ps=predictScores(ctx,t,fitmodel,id);
  for(let n=1;n<=45;n++)results[id]+=(ps[n]-Number(ctx.y[t].has(n)))**2;
 }
 for(const id of Object.keys(results))results[id]=roundTo(results[id]/((end-start)*45),9);
 return results;
}
function retrospective(ctx){
 const end=Math.min(1000,ctx.draws.length);
 const model=fit(ctx,end);
 const start=1000;
 const stats=Object.fromEntries(METHODS.map(([id,name])=>[id,{name,tickets:0,hits:0,grades:[0,0,0,0,0,0]}]));
 for(let t=start;t<ctx.draws.length;t++)for(const [id] of METHODS){
  const entry=grade(ticket(ctx,t,model,id),ctx.draws[t]);
  const s=stats[id];s.tickets++;s.hits+=entry.hit;if(entry.grade)s.grades[entry.grade]++;
 }
 const val=brier(ctx,800,1000,fit(ctx,800));
 const test=ctx.draws.length>1000?brier(ctx,1000,ctx.draws.length,model):{};
 for(const s of Object.values(stats))s.meanHits=s.tickets?roundTo(s.hits/s.tickets,6):null;
 return {status:"retrospective_exploratory_not_prospective",start_draw:1001,end_draw:ctx.draws.length,
   "test_used_for_previous_model_development":true,
   validation_801_1000_brier:val,final_1001_onward_brier:test,
   equal_probability_brier:roundTo((6/45)*(39/45),9),models:stats};
}
function nextDrawDate(last){return plusDays(last.date,7);}
function cutoffDate(date){return new Date(date+"T20:00:00+09:00");}
function verifyLedger(ledger){
 if(!Array.isArray(ledger))throw new Error("Ledger must be an array");
 let prior="GENESIS";
 const seen=new Set();
 for(const entry of ledger){
  if(entry.previous_hash!==prior||!entry.digest)throw new Error("Broken ledger hash chain");
  const {digest,...body}=entry;
  if(h(canonical(body))!==digest)throw new Error("Ledger digest mismatch at round "+entry.target_draw);
  if(seen.has(entry.target_draw))throw new Error("Duplicate forecast for round "+entry.target_draw);
  if(entry.known_through_draw>=entry.target_draw)throw new Error("Future information in forecast");
  for(const [id] of METHODS){
    const a=entry.tickets[id];
    if(!a||a.length!==6||new Set(a).size!==6||a.some(n=>n<1||n>45))throw new Error("Bad ticket "+id);
  }
  seen.add(entry.target_draw);prior=digest;
 }
 return prior;
}
function evalue(hits){
 // Valid sequential e-process under the hypothesis of fair independent draws:
 // each 6-number ticket has hypergeometric hit distribution, conditional on history.
 const terms=[];
 const comb=(n,k)=>{let v=1;for(let i=1;i<=k;i++)v=v*(n-i+1)/i;return v;};
 const weights=Array.from({length:7},(_,k)=>comb(6,k)*comb(39,6-k)/COMBINATIONS);
 for(const lambda of LAMBDAS){
  let mgf=0;for(let j=0;j<=6;j++)mgf+=weights[j]*Math.exp(lambda*j);
  const z=lambda*hits.reduce((a,b)=>a+b,0)-hits.length*Math.log(mgf);
  terms.push(Math.exp(Math.min(700,z)));
 }
 return terms.reduce((a,b)=>a+b,0)/terms.length;
}
function prospective(ledger,draws){
 const checked=ledger.filter(e=>e.target_draw<=draws.length);
 const stats={};
 for(const [id,name] of METHODS){
  const hits=[],ranks=[0,0,0,0,0,0],late=[];
  for(const entry of checked){
   const real=draws[entry.target_draw-1];
   const legal=entry.created_at_utc&&new Date(entry.created_at_utc).getTime()<cutoffDate(real.date).getTime() &&
    entry.known_through_draw<entry.target_draw;
   if(!legal){late.push(entry.target_draw);continue;}
   const result=grade(entry.tickets[id],real);
   hits.push(result.hit);if(result.grade)ranks[result.grade]++;
  }
  const ev=id==="random"?null:evalue(hits);
  const passed=id!=="random"&&hits.length>=100&&ev>=EVIDENCE_IDS.length/ALPHA;
  stats[id]={name,settled_predictions:hits.length,number_matches:hits.reduce((a,b)=>a+b,0),
    average_matches:hits.length?roundTo(hits.reduce((a,b)=>a+b,0)/hits.length,6):null,
    exact_first_prizes:ranks[1],prizes:ranks,excluded_late_rounds:late,
    e_value:ev===null?null:roundTo(ev,6),evidence_threshold:EVIDENCE_IDS.length/ALPHA,
    fair_draw_advantage_evidence:passed};
 }
 return {status:"prospective_precommitted_only",first_eligible_draw:1252,verified_rounds:checked.length,
  model_version:MODEL_VERSION,statistical_threshold:{familywise_alpha:ALPHA,
   test:"anytime-valid mixture e-process; five candidate methods, Bonferroni threshold 500",
   min_draws:100,
   exact_first_prize_is_not_100_percent_prediction:true},
  models:stats,any_model_with_verified_advantage:EVIDENCE_IDS.some(id=>stats[id].fair_draw_advantage_evidence),
  future_100_percent_accuracy_claimed:false};
}
function buildForecast(ctx,ledger){
 const last=ctx.draws.at(-1),target=last.draw+1,date=nextDrawDate(last);
 const now=new Date();
 if(now>=cutoffDate(date))return null;
 if(ledger.some(e=>e.target_draw===target))return null;
 const model=fit(ctx,ctx.draws.length),tickets={};
 for(const [id] of METHODS)tickets[id]=ticket(ctx,ctx.draws.length,model,id);
 const prior=ledger.length?ledger.at(-1).digest:"GENESIS";
 const entry={target_draw:target,target_draw_date:date,known_through_draw:last.draw,
  last_known_result_hash:h(canonical(last)),created_at_utc:now.toISOString(),
  model_version:MODEL_VERSION,method_spec:"frozen logistic/ridge SGD, fixed stump30, simple frequency, seeded random",
  previous_hash:prior,tickets};
 entry.digest=h(canonical(entry));
 return entry;
}
function selfTest(){
 const rows=[];
 const seen=new Set();
 for(let i=0;i<1050;i++){
  const a=[];for(let j=0;j<6;j++){let v=((i*13+j*7)%45)+1;while(a.includes(v))v=v%45+1;a.push(v);}
  let bonus=1;while(a.includes(bonus))bonus++;
  rows.push({draw:i+1,date:plusDays("2002-12-07",i*7),numbers:a.sort((a,b)=>a-b),bonus});
 }
 const ctx=build(rows),models=fit(ctx,1000);
 for(const [id] of METHODS){
  const nums=ticket(ctx,1000,models,id);
  if(nums.length!==6||new Set(nums).size!==6)throw new Error("self test ticket invalid "+id);
 }
 const fake={target_draw:1051,target_draw_date:plusDays("2002-12-07",1050*7),known_through_draw:1050,
  created_at_utc:"2020-01-01T00:00:00Z",previous_hash:"GENESIS",tickets:{}};
 for(const [id] of METHODS)fake.tickets[id]=ticket(ctx,1050,models,id);
 fake.digest=h(canonical(fake));verifyLedger([fake]);
 if(Math.abs(evalue([])-1)>1e-10||Math.abs(evalue([0,1,2])-1)<0.0001)throw new Error("e-value failed sanity");
 const s=prospective([fake],rows);if(s.models.logit.settled_predictions!==0)throw new Error("future draw incorrectly scored");
 console.log("LOTTO RESEARCH SELF TEST PASS: six unique numbers, ledger integrity, future embargo, scoring");
}
async function main(){
 const draws=await verifiedHistory();
 const oldLedger=readJson(PATHS.ledger,[]);
 verifyLedger(oldLedger);
 const oldState=readJson(PATHS.state,null);
 if(oldState&&oldState.latest_verified_draw>draws.length)throw new Error("Cannot regress latest draw");
 const ctx=build(draws);
 const exp=retrospective(ctx);
 const ledger=oldLedger.slice();
 const next=buildForecast(ctx,ledger);
 if(next)ledger.push(next);
 verifyLedger(ledger);
 const pros=prospective(ledger,draws);
 const latest=draws.at(-1);
 const state={schema_version:1,generated_at_utc:new Date().toISOString(),
  source_validation:{status:"two_independent_sources_agree",source_a:SOURCE_A,source_b:SOURCE_B,
   total_draws:draws.length,mismatch_count:0,history_sha256:h(canonical(draws))},
  latest_verified_draw:latest.draw,latest_verified_date:latest.date,latest_result:latest,
  next_target_draw:latest.draw+1,latest_forecast:ledger.find(e=>e.target_draw===latest.draw+1)||null,
  retrospective:exp,prospective:pros,
  claim_status:pros.any_model_with_verified_advantage?"some_statistical_evidence_of_number_match_advantage_not_guaranteed":"no_verified_advantage",
  guarantee_100_percent:false,
  policy:"Only pre-draw, hash-chained, independently verified predictions count. Historical tuning is exploratory. A 100% future prediction claim is not supported."
 };
 saveJson(PATHS.history,{schema_version:1,draws});
 saveJson(PATHS.ledger,ledger);
 saveJson(PATHS.state,state);
 console.log(JSON.stringify({status:"ok",verified_draws:draws.length,new_forecast:next?.target_draw??null,
  prospective_scored:pros.verified_rounds,retrospective:exp.models,claim_status:state.claim_status}));
}
if(process.argv.includes("--self-test"))selfTest();
else main().catch(e=>{console.error("LOTTO RESEARCH FAIL-CLOSED:",e.stack||e);process.exitCode=1;});
