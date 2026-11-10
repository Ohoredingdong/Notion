const test=require('node:test');
const assert=require('node:assert/strict');
const I=require('../designs/miniature-kitchen/nutrition-insight.js');

const DAY='2026-11-10';
const basics={kcal:500,carb:50,protein:20,fat:10,fiber:4,water:200};
const targets={kcal:2000,carb:200,protein:70,fat:60,fiber:25,water:2000};
const extras={calcium:100,sodium:500,sugar:10};
const extraTargets={calcium:800,sodium:2000,sugar:50};
const meal=(id,nutrients={},day=DAY)=>({id,day,nutrients:{...basics,...nutrients}});
const report=(meals,options={})=>I.daily({day:DAY,play:{meals,targets,...options.play},flow:{extraTargets,...options.flow},preview:options.preview});
function freeze(value){if(value&&typeof value==='object'){Object.freeze(value);Object.values(value).forEach(freeze);}return value;}

test('all nine nutrients retain units and only sodium and total sugar are limits',()=>{
 const r=report([meal('a')],{flow:{extraNutrients:{a:extras}}});
 assert.deepEqual(Object.keys(r.nutrients),['kcal','carb','protein','fat','fiber','water','calcium','sodium','sugar']);
 assert.equal(r.nutrients.sugar.label,'총당류');assert.equal(r.nutrients.sugar.unit,'g');
 assert.equal(r.nutrients.sodium.unit,'mg');assert.equal(r.nutrients.calcium.unit,'mg');assert.equal(r.nutrients.water.unit,'mL');
 for(const [key,n] of Object.entries(r.nutrients))assert.equal(n.mode,['sodium','sugar'].includes(key)?'limit':'target');
});

test('no meal records do not manufacture a zero intake or a full remaining allowance',()=>{
 const r=report([],{preview:{kind:'reference',nutrients:basics}});
 assert.equal(r.mealCount,0);
 for(const n of Object.values(r.nutrients)){
  assert.equal(n.status,'no-records');assert.equal(n.value,null);assert.equal(n.knownTotal,0);
  assert.equal(n.remaining,null);assert.equal(n.excess,null);assert.equal(n.complete,false);assert.equal(n.projection,null);
 }
});

test('complete personal records sum meals and compare with the existing personal targets',()=>{
 const r=report([meal('a'),meal('b',{carb:25,protein:10})],{flow:{extraNutrients:{a:extras,b:extras}}});
 assert.equal(r.mealCount,2);const carb=r.nutrients.carb;
 assert.equal(carb.value,75);assert.equal(carb.knownTotal,75);assert.equal(carb.enteredCount,2);assert.equal(carb.missingCount,0);
 assert.equal(carb.target,200);assert.equal(carb.remaining,125);assert.equal(carb.excess,0);assert.equal(carb.status,'below');assert.equal(carb.complete,true);
 assert.equal(r.nutrients.sodium.value,1000);assert.equal(r.nutrients.sodium.remaining,1000);
});

test('explicit zero is a known record while null and invalid nutrient values remain missing',()=>{
 const r=report([meal('a',{carb:0,protein:null,fat:NaN,fiber:-1,water:Infinity})],{flow:{extraNutrients:{a:{sodium:0,sugar:0,calcium:null}}}});
 assert.equal(r.nutrients.carb.value,0);assert.equal(r.nutrients.carb.enteredCount,1);assert.equal(r.nutrients.carb.remaining,200);
 assert.equal(r.nutrients.sodium.value,0);assert.equal(r.nutrients.sodium.remaining,2000);assert.equal(r.nutrients.sugar.value,0);
 for(const key of ['protein','fat','fiber','water','calcium']){
  const n=r.nutrients[key];assert.equal(n.value,null);assert.equal(n.knownTotal,0);assert.equal(n.missingCount,1);assert.equal(n.status,'partial');assert.equal(n.remaining,null);
 }
});

test('partial known sums never claim an exact remaining amount or a completed target',()=>{
 const r=report([meal('a',{carb:210}),meal('b',{carb:null})]);
 const n=r.nutrients.carb;assert.equal(n.value,210);assert.equal(n.status,'partial');assert.equal(n.enteredCount,1);assert.equal(n.missingCount,1);
 assert.equal(n.remaining,null);assert.equal(n.excess,null);assert.equal(n.lowerBound,false);assert.equal(n.complete,false);
});

test('extra nutrients join only the matching live meals and never include orphan, plan or other-day values',()=>{
 const r=report([meal('a'),meal('past',{},'2026-11-09'),meal('future',{},'2026-11-11')],{flow:{
  extraNutrients:{a:extras,past:{...extras,sodium:9000},future:{...extras,sodium:9000},canceled:{...extras,sodium:9000}},
  plans:[{day:DAY,portions:100,recipeId:'recipe-1'}]
 }});
 assert.equal(r.mealCount,1);assert.equal(r.nutrients.sodium.value,500);assert.equal(r.nutrients.sugar.value,10);
});

test('unset or invalid targets remain unknown instead of supplying generic recommendations',()=>{
 for(const invalid of [null,undefined,0,-1,NaN,Infinity,'200']){
  const r=report([meal('a')],{play:{targets:{carb:invalid}},flow:{extraTargets:{sodium:invalid},extraNutrients:{a:extras}},preview:{kind:'entered',nutrients:{carb:30,sodium:100}}});
  for(const key of ['carb','sodium']){
   const n=r.nutrients[key];assert.equal(n.target,null);assert.equal(n.status,'no-target');assert.equal(n.remaining,null);assert.equal(n.excess,null);assert.equal(n.projection,null);
  }
 }
});

test('complete records distinguish exactly met and exceeded targets or limits',()=>{
 const r=report([meal('a',{carb:200,protein:80})],{flow:{extraNutrients:{a:{...extras,sodium:2000,sugar:55}}}});
 assert.equal(r.nutrients.carb.status,'met');assert.equal(r.nutrients.carb.remaining,0);assert.equal(r.nutrients.carb.excess,0);
 assert.equal(r.nutrients.protein.status,'over');assert.equal(r.nutrients.protein.excess,10);
 assert.equal(r.nutrients.sodium.status,'met');assert.equal(r.nutrients.sodium.remaining,0);assert.equal(r.nutrients.sodium.lowerBound,false);
 assert.equal(r.nutrients.sugar.status,'over');assert.equal(r.nutrients.sugar.excess,5);assert.equal(r.nutrients.sugar.remaining,0);
});

test('a partial lower bound above a personal limit may warn without inventing the unknown total',()=>{
 const r=report([meal('a'),meal('b')],{flow:{extraNutrients:{a:{...extras,sodium:2200,sugar:60},b:{calcium:null,sodium:null,sugar:null}}},preview:{kind:'reference',nutrients:{sodium:10,sugar:1}}});
 for(const [key,excess] of [['sodium',200],['sugar',10]]){
  const n=r.nutrients[key];assert.equal(n.status,'over');assert.equal(n.complete,false);assert.equal(n.lowerBound,true);
  assert.equal(n.excess,excess);assert.equal(n.remaining,null);assert.equal(n.missingCount,1);assert.equal(n.projection,null);
 }
});

test('partial totals at or below a limit stay partial rather than declaring a safe allowance',()=>{
 for(const amount of [0,500,2000]){
  const r=report([meal('a'),meal('b')],{flow:{extraNutrients:{a:{...extras,sodium:amount},b:{calcium:null,sodium:null,sugar:null}}}});
  const n=r.nutrients.sodium;assert.equal(n.status,'partial');assert.equal(n.remaining,null);assert.equal(n.excess,null);assert.equal(n.lowerBound,false);
 }
});

test('a known individual portion projects each complete nutrient without changing current totals',()=>{
 const r=report([meal('a')],{flow:{extraNutrients:{a:extras}},preview:{kind:'entered',nutrients:{carb:160,protein:50,sodium:1600,sugar:0,fat:null}}});
 const carb=r.nutrients.carb;assert.equal(carb.value,50);assert.equal(carb.remaining,150);
 assert.deepEqual(carb.projection,{value:160,total:210,remaining:0,excess:10,status:'over',kind:'entered'});
 assert.equal(r.nutrients.protein.projection.status,'met');assert.equal(r.nutrients.sodium.projection.total,2100);assert.equal(r.nutrients.sodium.projection.excess,100);
 assert.equal(r.nutrients.sugar.projection.value,0);assert.equal(r.nutrients.sugar.projection.total,10);assert.equal(r.nutrients.fat.projection,null);
});

test('unknown preview values, incomplete daily records or an unsupported preview source never create forecasts',()=>{
 for(const incoming of [null,undefined,-1,NaN,Infinity,'30']){
  assert.equal(report([meal('a')],{preview:{kind:'reference',nutrients:{carb:incoming}}}).nutrients.carb.projection,null);
 }
 assert.equal(report([meal('a')],{preview:{kind:'guessed',nutrients:{carb:30}}}).nutrients.carb.projection,null);
 assert.equal(report([meal('a',{carb:null})],{preview:{kind:'entered',nutrients:{carb:30}}}).nutrients.carb.projection,null);
 assert.equal(report([meal('a')],{preview:{kind:'reference',nutrients:{carb:30}}}).nutrients.carb.projection.kind,'reference');
});

test('calendar validation is explicit and the calculation never treats future meals as consumed today',()=>{
 for(const day of [undefined,'','2026-02-30','2026-13-01','2026-11-10T12:00:00Z'])assert.throws(()=>I.daily({day}),TypeError);
 assert.equal(I.daily({day:'2028-02-29'}).mealCount,0);
 assert.equal(report([meal('future',{},'2026-11-11')]).nutrients.carb.value,null);
});

test('decimal addition does not create a false over-limit warning or erase a positive small amount',()=>{
 const r=report([meal('a'),meal('b')],{flow:{extraTargets:{sodium:.3,sugar:1},extraNutrients:{a:{calcium:0,sodium:.1,sugar:.00000001},b:{calcium:0,sodium:.2,sugar:0}}}});
 assert.equal(r.nutrients.sodium.value,.3);assert.equal(r.nutrients.sodium.status,'met');assert.equal(r.nutrients.sodium.excess,0);
 assert.equal(r.nutrients.sugar.value,.00000001);assert.ok(r.nutrients.sugar.value>0);
});

test('frozen records, plans, personal targets and preview sources remain byte-for-byte unchanged',()=>{
 const input=freeze({day:DAY,play:{meals:[meal('a')],targets},flow:{extraTargets,extraNutrients:{a:extras},plans:[{id:'p',day:DAY,portions:4}],recipeFacts:{'recipe-1':{carb:30,source:'확인한 개인 입력'}}},preview:{kind:'reference',nutrients:{carb:30,sodium:100},source:{label:'표시용 출처'}}});
 const before=JSON.stringify(input),r=I.daily(input);assert.equal(JSON.stringify(input),before);
 r.nutrients.carb.value=999;r.nutrients.sodium.projection.total=999;
 assert.equal(JSON.stringify(input),before);assert.equal(I.daily(input).nutrients.carb.value,50);assert.equal(I.daily(input).nutrients.sodium.projection.total,600);
});
