const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const N=require('../designs/miniature-kitchen/recipe-nutrition.js');
const DAY='2026-11-10',KEYS=['kcal','carb','protein','fat','fiber','water','calcium','sodium','sugar'];
const sandbox={window:{}};
for(const file of ['catalog.js','nutrition-reference.js'])
 vm.runInNewContext(fs.readFileSync(require.resolve('../designs/miniature-kitchen/'+file),'utf8'),sandbox);
const actualReference=sandbox.window.KitchenNutritionReference,catalog=sandbox.window.KitchenCatalog;
const copy=value=>JSON.parse(JSON.stringify(value));
const recipe=(amounts,extra={})=>({id:'recipe-qa',f:Object.keys(amounts),s:[],p:[],amounts,...extra});
const item=(name,values={},extra={})=>({name,per100g:{...Object.fromEntries(KEYS.map(key=>[key,0])),...values},gramsPerUnit:{개:100},assumption:'명시적인 단위검사 중량 가정',...extra});
const reference=(items,extra={})=>({availableFrom:DAY,release:'단위검사 자료 2015',source:{label:'단위검사 참고자료',url:'https://example.org/qa'},items,...extra});
const estimate=(r,ref,options={})=>N.estimate(r,{day:DAY,reference:ref,...options});
function freeze(value){if(value&&typeof value==='object'){Object.freeze(value);Object.values(value).forEach(freeze);}return value;}

test('each entered nutrient takes precedence, including zero, while null falls back independently',()=>{
 const r=recipe({계란:'1개'}),flow={recipeFacts:{'recipe-qa':{kcal:0,protein:50,carb:null,sodium:0,source:'확인한 사용자 영양표'}}};
 const result=estimate(r,actualReference,{flow});
 assert.deepEqual(result.nutrients.kcal,{value:0,knownSubtotal:0,missing:[],kind:'entered'});
 assert.equal(result.nutrients.protein.value,50);assert.equal(result.nutrients.protein.kind,'entered');
 assert.equal(result.nutrients.sodium.value,0);assert.equal(result.nutrients.carb.value,.36);assert.equal(result.nutrients.carb.kind,'reference');
 assert.match(result.sourceLabel,/직접 입력 우선/);assert.match(result.sources[0].label,/확인한 사용자 영양표/);
});

test('future, missing and invalid availability dates disable references but preserve entered facts',()=>{
 const r=recipe({계란:'1개'}),flow={recipeFacts:{'recipe-qa':{protein:10}}};
 for(const availableFrom of ['2026-11-11','2026-02-30',undefined,'']){
  const ref={...actualReference,availableFrom};const result=estimate(r,ref,{flow});
  assert.equal(result.nutrients.kcal.value,null);assert.equal(result.nutrients.kcal.knownSubtotal,null);assert.equal(result.nutrients.kcal.kind,'unknown');
  assert.equal(result.nutrients.protein.value,10);assert.equal(result.nutrients.protein.kind,'entered');assert.equal(result.assumptions.length,0);
 }
 assert.equal(estimate(r,actualReference,{day:'2026-11-09'}).nutrients.kcal.value,null);
 for(const day of [undefined,'','2026-02-30','2026-11-10T00:00:00Z'])assert.throws(()=>estimate(r,actualReference,{day}),TypeError);
});

test('absent source ingredients, empty recipes and invalid fact numbers never become zero nutrition',()=>{
 for(const r of [recipe({알수없는재료:'100g'}),recipe({})]){
  const result=estimate(r,null,{flow:{recipeFacts:{'recipe-qa':{kcal:NaN,protein:-1,sugar:Infinity,carb:'20'}}}});
  for(const nutrient of Object.values(result.nutrients)){
   assert.equal(nutrient.value,null);assert.equal(nutrient.knownSubtotal,null);assert.equal(nutrient.kind,'unknown');
  }
 }
});

test('literal mass uses existing g/kg parsing without inferring a count or changing fractional precision',()=>{
 const ref=reference([item('식품',{kcal:10,protein:2})]);
 for(const quantity of ['100g','0.1kg','100그램']){
  const result=estimate(recipe({식품:quantity}),ref);assert.equal(result.nutrients.kcal.value,10);assert.equal(result.nutrients.protein.value,2);
 }
 const fraction=estimate(recipe({식품:'1/3g'}),ref);
 assert.equal(fraction.nutrients.kcal.value,.033333);assert.equal(fraction.nutrients.protein.value,.006667);
});

test('count and spoon conversions require a positive explicitly provided per-unit mass',()=>{
 const r=recipe({식품:'1/3개'}),ref=reference([item('식품',{kcal:100},{gramsPerUnit:{개:150}})]);
 assert.equal(estimate(r,ref).nutrients.kcal.value,50);
 assert.equal(estimate(recipe({식품:'플레인 2큰술'}),reference([item('식품',{kcal:100},{gramsPerUnit:{큰술:15}})])).nutrients.kcal.value,30);
 for(const grams of [undefined,0,-1,NaN,Infinity,'100']){
  const result=estimate(r,reference([item('식품',{kcal:100},{gramsPerUnit:{개:grams}})]));
  assert.equal(result.nutrients.kcal.value,null);assert.equal(result.nutrients.kcal.kind,'unknown');
 }
});

test('mL, litres and source water grams are never treated as mass or stored water mL',()=>{
 const ref=reference([item('식품',{kcal:100,water:null},{sourceWaterGrams:75,gramsPerUnit:{mL:1,L:1000}})]);
 for(const quantity of ['100mL','0.1L']){
  const result=estimate(recipe({식품:quantity}),ref);
  assert.equal(result.nutrients.kcal.value,null);assert.equal(result.nutrients.water.value,null);assert.equal(result.nutrients.water.knownSubtotal,null);
 }
 const real=estimate(recipe({계란:'100g'}),actualReference);assert.equal(real.nutrients.water.value,null);assert.equal(real.nutrients.water.knownSubtotal,null);
});

test('unmeasured amounts contribute only a source-confirmed zero; missing source values stay unknown',()=>{
 const salt=estimate(recipe({소금:'조금'}),actualReference);
 for(const key of ['kcal','carb','protein','fat','fiber','sugar']){
  assert.equal(salt.nutrients[key].value,0);assert.equal(salt.nutrients[key].knownSubtotal,0);assert.equal(salt.nutrients[key].kind,'reference');
 }
 for(const key of ['calcium','sodium','water'])assert.equal(salt.nutrients[key].value,null);
 const result=estimate(recipe({식품:'조금'}),reference([item('식품',{kcal:null,carb:undefined,protein:NaN})]));
 for(const key of ['kcal','carb','protein'])assert.equal(result.nutrients[key].value,null);
 assert.deepEqual(estimate(recipe({미매핑:'조금'}),actualReference).nutrients.kcal.missing,['미매핑']);
});

test('explicit non-mappings override a tempting match and aliases never match unrelated food names',()=>{
 const ref=reference([item('애호박',{kcal:100}),item('닭',{kcal:100})],{explicitNonMappings:['애호박']});
 const result=estimate(recipe({애호박:'100g',닭가슴살:'100g'}),ref);
 assert.equal(result.nutrients.kcal.kind,'unknown');assert.deepEqual(result.nutrients.kcal.missing,['애호박','닭가슴살']);
 assert.equal(estimate(recipe({달걀:'1개'}),actualReference).nutrients.kcal.value,71.5);
});

test('ingredients without written amounts stay missing and aliases do not count one ingredient twice',()=>{
 const r=recipe({계란:'1개'},{f:['계란','달걀','양파'],s:['후추']});
 const result=estimate(r,actualReference);
 assert.equal(result.nutrients.kcal.knownSubtotal,71.5);assert.deepEqual(result.nutrients.kcal.missing,['양파','후추']);
 assert.equal(result.sources.filter(source=>source.label.includes('Egg, whole')).length,1);
});

test('a written 20g alternative wins over an assumed slice mass',()=>{
 const ref=copy(actualReference);ref.items.find(row=>row.name==='치즈').gramsPerUnit={장:999};
 const result=estimate(recipe({치즈:'1장 또는 20g'}),ref);
 assert.equal(result.nutrients.kcal.value,80.8);assert.equal(result.nutrients.protein.value,4.574);assert.equal(result.nutrients.sodium.value,130.6);
});

test('missing calories, sugar and fibre are not reconstructed from other nutrients or filled with zero',()=>{
 const result=estimate(recipe({식품:'100g'}),reference([item('식품',{kcal:null,carb:10,protein:20,fat:30,sugar:null,fiber:null})]));
 for(const key of ['kcal','sugar','fiber']){
  assert.equal(result.nutrients[key].value,null);assert.equal(result.nutrients[key].knownSubtotal,null);assert.equal(result.nutrients[key].kind,'unknown');
 }
 assert.equal(result.nutrients.carb.value,10);assert.equal(result.nutrients.fat.value,30);
});

test('one-person estimates retain input, entered source and reference data exactly and disclose only used assumptions',()=>{
 const r=freeze(recipe({계란:'1개'})),flow=freeze({recipeFacts:{'recipe-qa':{sugar:0,source:'개인 확인값'}},plans:[{recipeId:'recipe-qa',portions:10}],expenses:[{amount:999999}]}),ref=freeze(copy(actualReference));
 const before=JSON.stringify({r,flow,ref}),result=estimate(r,ref,{flow,portions:20});
 assert.equal(result.nutrients.kcal.value,71.5);assert.equal(result.nutrients.sugar.value,0);assert.equal(JSON.stringify({r,flow,ref}),before);
 assert.equal(result.assumptions.length,1);assert.match(result.assumptions[0],/계란/);assert.doesNotMatch(result.assumptions.join(' '),/양파|콩기름/);
 assert.ok(result.sources.some(source=>source.label.includes('2015')));assert.deepEqual(result.roles,[]);
 result.assumptions[0]='변경';result.sources[0].label='변경';assert.equal(JSON.stringify({r,flow,ref}),before);
 const entered=estimate(r,ref,{flow:{recipeFacts:{'recipe-qa':Object.fromEntries(KEYS.map(key=>[key,0]))}}});
 assert.equal(entered.assumptions.length,0);assert.equal(entered.sources.length,1);assert.match(entered.sourceLabel,/직접 입력/);
});

// Independent sums of the published per-100g facts and explicitly declared masses.
// Order: kcal, carb, protein, fat, fibre, calcium, sodium, total sugar.
const actualExpected=[
 [407.089,65.62429,12.21742,9.73421,.8924,43.349,364.129,2.3262],
 [136.086,7.93784,12.75904,7.227,1.3294,539.034,12.738,3.064],
 [166.14,4.7847,28.0824,3.39,1.476,18.3,60.15,3.2349],
 [111.28,.36,6.28,9.255,0,28,71,.185],
 [161.3,2.118,13.601,10.485,0,92.3,155.8,1.768],
 [176.589,7.73629,13.10142,11.75021,1.3424,538.249,303.629,3.0712],
 [191.989,10.01829,15.26442,11.98821,2.0424,540.349,307.129,4.4572],
 [274.65,3.73035,17.6752,20.795,.738,204.15,275.675,2.08345]
];
const completeKeys=[
 ['kcal','carb','protein','fat','calcium','sodium'],[],[],[],[],
 ['kcal','carb','protein','fat','fiber','calcium','sodium','sugar'],
 ['kcal','carb','protein','fat','fiber','calcium','sodium','sugar'],
 ['kcal','carb','protein','fat','fiber','sugar']
];
for(const [index,r] of catalog.entries())test('actual '+r.name+' agrees with independent ingredient arithmetic and missing facts',()=>{
 const result=estimate(r,actualReference),keys=['kcal','carb','protein','fat','fiber','calcium','sodium','sugar'];
 for(const [column,key] of keys.entries()){
  const n=result.nutrients[key],expected=actualExpected[index][column];assert.equal(n.knownSubtotal,expected,key+' subtotal');
  if(completeKeys[index].includes(key)){assert.equal(n.value,expected,key+' complete');assert.equal(n.kind,'reference');assert.deepEqual(n.missing,[]);}
  else{assert.equal(n.value,null,key+' stays incomplete');assert.equal(n.kind,'partial');assert.ok(n.missing.length>0);}
 }
 assert.equal(result.nutrients.water.kind,'unknown');assert.equal(result.nutrients.water.value,null);assert.equal(result.nutrients.water.knownSubtotal,null);
 if(index===0){assert.deepEqual(result.nutrients.sugar.missing,['밥/즉석밥']);assert.deepEqual(result.nutrients.fiber.missing,['밥/즉석밥']);}
 if(index===1)assert.deepEqual(result.nutrients.kcal.missing,['애호박','된장']);
 if(index===2||index===4)assert.deepEqual(result.nutrients.sodium.missing,['소금','후추']);
 if(index===3)assert.deepEqual(result.nutrients.sodium.missing,['애호박','소금']);
 if(index===7)assert.deepEqual(result.nutrients.sodium.missing,['소금']);
 assert.ok(result.sources.every(source=>source.label.includes('2015')));
});
