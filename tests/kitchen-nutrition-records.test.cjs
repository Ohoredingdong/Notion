const test=require('node:test');
const assert=require('node:assert/strict');
const F=require('../designs/miniature-kitchen/workflow-model.js');
const M=require('../designs/miniature-kitchen/play-model.js');

const DAY='2026-11-10',KEYS=['kcal','carb','protein','fat','fiber','water','calcium','sodium','sugar'];
const clone=value=>JSON.parse(JSON.stringify(value));
const source=(fields=['kcal','protein','sodium'])=>({kind:'reference-confirmed',referenceId:'usda-sr28-selected-2015-v1',fields:[...fields],baseValues:Object.fromEntries(fields.map((key,index)=>[key,index*10])),values:Object.fromEntries(fields.map((key,index)=>[key,index*5]))});
function fixture(){
 const flow=F.blank(),play=M.create(['recipe-1']),world={serial:20,layer:20,doors:{freshLeft:true,freshRight:true,frozenLeft:true,frozenRight:true},items:[
  {id:'qa-eggs',name:'계란',kind:'food',quantity:'6개',expiry:'2026-11-20',zone:'freshLeft',x:.5,y:.5,z:1},
  {id:'meal',name:'계란 볶음밥',kind:'meal',zone:'counter',x:.5,y:.5,z:2}
 ]};
 const {record}=play.record({day:DAY,name:'명시적인 QA 식사',portion:'1인분',recipeId:'recipe-1',nutrients:{kcal:400,carb:60,protein:15,fat:10,fiber:null,water:null}});
 flow.plans.push({id:'qa-plan',day:DAY,slot:'lunch',recipeId:'recipe-1',portions:4});
 flow.transactions.push({id:'qa-transaction',mealId:record.id,active:true,portions:1,slot:'lunch',deductions:[]});
 flow.extraNutrients[record.id]={calcium:null,sodium:null,sugar:null};
 return {flow,play,world,record};
}
function withSource(value){const {flow}=fixture();flow.transactions[0].nutritionSource=value;return flow;}
function freeze(value){if(value&&typeof value==='object'){Object.freeze(value);Object.values(value).forEach(freeze);}return value;}

test('legacy v1 plans and meal transactions without new fields remain valid and byte-exact after a JSON round trip',()=>{
 const {flow,play,world}=fixture();assert.equal(F.valid(flow),true);assert.equal(M.valid(play.state(),['recipe-1']),true);assert.equal(M.validWorld(world),true);
 const raw=JSON.stringify({version:1,world,play:play.state(),workflow:flow});
 const recovered=JSON.parse(raw);recovered.workflow=F.create(recovered.workflow);
 assert.equal(JSON.stringify(recovered),raw);assert.equal(recovered.version,1);assert.equal(recovered.workflow.version,1);
 assert.equal(Object.hasOwn(recovered.workflow.plans[0],'servingBasis'),false);
 assert.equal(Object.hasOwn(recovered.workflow.transactions[0],'nutritionSource'),false);
});

test('cooking basis and a confirmed nine-field source preserve zero, limits and source identity through recovery',()=>{
 const {flow}=fixture();flow.plans[0].servingBasis='cooking';flow.transactions[0].nutritionSource=source(KEYS);
 for(const key of KEYS){flow.transactions[0].nutritionSource.baseValues[key]=0;flow.transactions[0].nutritionSource.values[key]=100000;}
 const raw=JSON.stringify(flow);assert.equal(F.valid(flow),true);
 const recovered=F.create(JSON.parse(raw));assert.equal(JSON.stringify(recovered),raw);
 assert.equal(recovered.transactions[0].nutritionSource.referenceId,'usda-sr28-selected-2015-v1');
 assert.deepEqual(recovered.transactions[0].nutritionSource.fields,KEYS);assert.equal(recovered.plans[0].portions,4);assert.equal(recovered.transactions[0].portions,1);
});

test('only an absent basis or the exact cooking discriminator is accepted',()=>{
 for(const basis of [null,'','personal','Cooking',0,false,[],{}]){
  const {flow}=fixture();flow.plans[0].servingBasis=basis;assert.equal(F.valid(flow),false,JSON.stringify(basis));
  assert.throws(()=>F.create(flow),/형식/);
 }
 for(const basis of [undefined,'cooking']){const {flow}=fixture();flow.plans[0].servingBasis=basis;assert.equal(F.valid(flow),true);}
});

test('malformed source objects, kinds and reference IDs are rejected instead of silently discarded',()=>{
 const bad=[null,false,0,[],{},source()];bad[bad.length-1].kind='reference';
 for(const value of bad){assert.equal(F.valid(withSource(value)),false);assert.throws(()=>F.create(withSource(value)),/형식/);}
 for(const referenceId of [null,undefined,0,'','   ','x'.repeat(101)]){
  const value=source();value.referenceId=referenceId;assert.equal(F.valid(withSource(value)),false);
 }
 const limit=source();limit.referenceId='x'.repeat(100);assert.equal(F.valid(withSource(limit)),true);
 const absent=fixture().flow;absent.transactions[0].nutritionSource=undefined;assert.equal(F.valid(absent),true);
});

test('confirmed fields must be a nonempty unique subset of the nine supported nutrient keys',()=>{
 for(const fields of [null,'carb',[],['carb','carb'],['addedSugar'],['totalSugar'],['sugars'],['protein',null],[...KEYS,'carb']]){
  const value=source(KEYS);value.fields=fields;assert.equal(F.valid(withSource(value)),false,JSON.stringify(fields));
 }
 for(const fields of [['carb'],['sugar','sodium'],KEYS])assert.equal(F.valid(withSource(source(fields))),true);
});

test('every declared base and consumed value requires a finite number from zero through 100000',()=>{
 for(const key of KEYS)for(const slot of ['baseValues','values']){
  for(const invalid of [null,undefined,NaN,Infinity,-Infinity,-.000001,100000.000001,'1',false,{}]){
   const value=source([key]);value[slot][key]=invalid;assert.equal(F.valid(withSource(value)),false,key+' '+slot+' '+String(invalid));
  }
  for(const valid of [0,.000001,1.25,100000]){
   const value=source([key]);value[slot][key]=valid;assert.equal(F.valid(withSource(value)),true,key+' '+slot+' '+valid);
  }
 }
 for(const slot of ['baseValues','values'])for(const invalid of [null,undefined,false,0,[],{}]){
  const value=source();value[slot]=invalid;assert.equal(F.valid(withSource(value)),false,slot+' '+String(invalid));
 }
});

test('cancel, JSON recovery and restore retain the source snapshot without altering its nutritional values',()=>{
 const {flow,play,world,record}=fixture(),tx=flow.transactions[0];
 tx.nutritionSource=source();const nutritionRaw=JSON.stringify(tx.nutritionSource);
 tx.deductions=F.applyDeductions(world,[{itemId:'qa-eggs',quantity:'1개'}]);assert.equal(world.items[0].quantity,'5개');
 F.reverseDeductions(world,tx.deductions);tx.active=false;flow.lastCanceled={record:clone(record)};play.remove(record.id);
 assert.equal(world.items[0].quantity,'6개');assert.equal(JSON.stringify(tx.nutritionSource),nutritionRaw);assert.equal(F.valid(flow),true);
 const recovered=F.create(clone(flow)),restored=M.create(['recipe-1'],play.state());
 restored.restoreMeal(recovered.lastCanceled.record);F.reverseDeductions(world,recovered.transactions[0].deductions,-1);recovered.transactions[0].active=true;recovered.lastCanceled=null;
 assert.equal(JSON.stringify(recovered.transactions[0].nutritionSource),nutritionRaw);assert.equal(recovered.transactions[0].mealId,record.id);
 assert.equal(world.items[0].quantity,'5개');assert.equal(restored.state().meals[0].id,record.id);assert.equal(F.valid(recovered),true);
});

test('recovery clones only the explicitly confirmed field snapshot and leaves manual or missing nutrients untagged',()=>{
 const {flow}=fixture();flow.transactions[0].nutritionSource=source(['carb']);
 const frozen=freeze(flow),raw=JSON.stringify(frozen),recovered=F.create(frozen);
 assert.equal(JSON.stringify(frozen),raw);assert.deepEqual(recovered.transactions[0].nutritionSource.fields,['carb']);
 assert.equal(Object.hasOwn(recovered.transactions[0].nutritionSource.baseValues,'protein'),false);
 assert.equal(Object.hasOwn(recovered.transactions[0].nutritionSource.values,'sugar'),false);
 recovered.transactions[0].nutritionSource.values.carb=999;recovered.transactions[0].nutritionSource.fields.push('protein');
 assert.equal(JSON.stringify(frozen),raw);assert.equal(frozen.transactions[0].nutritionSource.values.carb,0);
});
