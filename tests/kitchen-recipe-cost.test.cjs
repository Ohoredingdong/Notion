const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const C=require('../designs/miniature-kitchen/recipe-cost.js');
const J=require('../designs/miniature-kitchen/journey-model.js');
const DAY='2026-11-10';
const recipe=(amounts,id='recipe-1')=>({id,name:'검증 요리',amounts,f:Object.keys(amounts),s:[],p:[]});
const line=(name,quantity,amount,id='line-1')=>({id,name,quantity,amount,registeredItemId:null});
function purchase(id,day,items,total=items.reduce((sum,item)=>sum+(item.amount??0),0)){
  return {id,day,name:'장보기',category:'groceries',amount:total,receipt:{purchaseId:id,items}};
}
const estimate=(r,flow={},portions=1,day=DAY)=>C.estimate(r,{flow,day,portions});
function freeze(value){if(value&&typeof value==='object'){Object.freeze(value);Object.values(value).forEach(freeze);}return value;}

test('unknown inputs stay unknown; an explicitly entered zero is a real known total',()=>{
  const r=recipe({계란:'1개'}),empty=estimate(r);
  assert.equal(empty.kind,'unknown');assert.equal(empty.total,null);assert.equal(empty.knownSubtotal,null);
  assert.deepEqual(empty.missing.map(row=>row.name),['계란']);assert.equal(empty.rows[0].cost,null);
  const zero=estimate(r,{recipeFacts:{'recipe-1':{cost:0,source:'직접 확인'}}},2);
  assert.equal(zero.kind,'entered');assert.equal(zero.total,0);assert.equal(zero.knownSubtotal,0);
  assert.deepEqual(zero.rows,[]);assert.deepEqual(zero.missing,[]);assert.equal(zero.sources[0].detail,'직접 확인');
});

test('entered recipe totals take precedence without inventing ingredient allocations',()=>{
  const r=recipe({계란:'1개'}),flow={recipeFacts:{'recipe-1':{cost:1300,source:'나의 재료비'}},
    expenses:[purchase('receipt',DAY,[line('계란','10개',5000)])]};
  const result=estimate(r,flow,1.5);
  assert.equal(result.kind,'entered');assert.equal(result.total,1950);assert.deepEqual(result.rows,[]);
  assert.equal(result.sources.length,1);assert.equal(result.sources[0].kind,'entered');
  assert.match(result.basisNote,/임의 배분하지/);
});

test('original purchase-pack quantity, aliases and fractional portions determine the estimate',()=>{
  const r=recipe({계란:'1/2개'}),flow={expenses:[purchase('eggs','2026-11-05',[line('달걀','10알',4500)])]};
  const result=C.estimate(r,{flow,day:DAY,portions:3,world:{items:[{name:'계란',quantity:'1개'}]}});
  assert.equal(result.kind,'purchase');assert.equal(result.total,675);assert.equal(result.rows[0].required,'1.5개');
  assert.equal(result.rows[0].quantity,'10알');assert.equal(result.rows[0].unitPrice,450);
  assert.equal(result.rows[0].source,'eggs');assert.equal(result.rows[0].day,'2026-11-05');
});

test('compatible mass units and ingredient aliases scale independently across several ingredients',()=>{
  const r=recipe({두부:'150g',버섯:'70g'}),flow={expenses:[purchase('groceries',DAY,
    [line('두부','0.6kg',3000,'tofu'),line('양송이버섯','200그램',1000,'mushroom')])]};
  const result=estimate(r,flow,2);
  assert.equal(result.kind,'purchase');assert.equal(result.total,2200);
  assert.deepEqual(result.rows.map(row=>row.cost),[1500,700]);assert.equal(result.sources.length,2);
});

test('partial prices expose only a known subtotal and name every missing component',()=>{
  const r=recipe({계란:'1개',토마토:'1개',소금:'조금'}),flow={expenses:[purchase('eggs',DAY,[line('계란','10개',5000)])]};
  const result=estimate(r,flow);
  assert.equal(result.kind,'partial');assert.equal(result.total,null);assert.equal(result.knownSubtotal,500);
  assert.deepEqual(result.missing.map(row=>row.name),['토마토','소금']);
  assert.deepEqual(result.rows.map(row=>row.cost),[500,null,null]);assert.match(result.basisNote,/부분 합계/);
});

test('incompatible measures, informal quantities and alternative measures do not become prices',()=>{
  const r=recipe({두부:'150g',간장:'1작은술',치즈:'1장 또는 20g',소금:'조금'}),flow={expenses:[purchase('cart',DAY,
    [line('두부','1모',2000,'tofu'),line('간장','150mL',3000,'soy'),line('치즈','10장',5000,'cheese'),line('소금','1kg',2000,'salt')])]};
  const result=estimate(r,flow);
  assert.equal(result.kind,'unknown');assert.equal(result.total,null);assert.equal(result.knownSubtotal,null);
  assert.equal(result.missing.length,4);assert.ok(result.rows.every(row=>row.cost===null));
});

test('only the latest eligible receipt at or before the chosen date contributes',()=>{
  const r=recipe({계란:'1개'}),flow={expenses:[
    purchase('old','2026-11-01',[line('계란','10개',4000)]),
    purchase('latest','2026-11-09',[line('계란','10개',5000)]),
    purchase('future','2026-11-11',[line('계란','10개',9000)]),
    {...purchase('not-groceries',DAY,[line('계란','10개',100000)]),category:'eatingout'},
    purchase('invalid-date','2026-02-30',[line('계란','10개',1000)])]};
  assert.equal(estimate(r,flow).total,500);assert.equal(estimate(r,flow).rows[0].source,'latest');
  assert.equal(estimate(r,flow,1,'2026-11-03').total,400);
  assert.equal(estimate(r,{expenses:[]}).kind,'unknown','a removed/cancelled receipt supplies no price');
});

test('equal-date records use the last saved eligible entry deterministically',()=>{
  const flow={expenses:[purchase('first',DAY,[line('계란','10개',4000)]),purchase('second',DAY,[line('달걀','10알',5500)])]};
  assert.equal(estimate(recipe({계란:'1개'}),flow).total,550);
});

test('receipt discounts or fees are disclosed rather than silently redistributed',()=>{
  const flow={expenses:[purchase('discount',DAY,[line('계란','10개',5000,'eggs'),line('우유','1L',3000,'milk')],7000)]};
  const result=estimate(recipe({계란:'1개'}),flow);
  assert.equal(result.total,500);assert.equal(result.rows[0].receiptAdjusted,true);
  assert.equal(result.sources[0].receiptAmount,7000);assert.equal(result.sources[0].itemAmountsTotal,8000);
  assert.equal(result.sources[0].adjustmentUnallocated,true);assert.match(result.basisNote,/할인·추가금/);
  assert.match(result.basisNote,/실제 구매 지출과 별도/);
});

test('unreconciled receipts keep their limitation visible',()=>{
  const flow={expenses:[purchase('partial-lines',DAY,[line('계란','10개',5000,'eggs'),line('우유','1L',null,'milk')],7000)]};
  const result=estimate(recipe({계란:'1개'}),flow);
  assert.equal(result.total,500);assert.equal(result.sources[0].unreconciled,true);
  assert.equal(result.sources[0].itemAmountsTotal,null);assert.match(result.basisNote,/대조하지 못한/);
});

test('zero receipt line prices remain known zero rather than disappearing as falsy',()=>{
  const flow={expenses:[purchase('free',DAY,[line('계란','10개',0)])]};
  const result=estimate(recipe({계란:'1개'}),flow);
  assert.equal(result.kind,'purchase');assert.equal(result.total,0);assert.equal(result.knownSubtotal,0);
  assert.deepEqual(result.missing,[]);
});

test('empty or malformed receipt data never creates a fake zero or throws through the view',()=>{
  for(const flow of [null,{expenses:'bad'},{expenses:[null,{},purchase('bad',DAY,[null,line('계란','0개',5000),
    line('계란','10개',NaN),line('계란','10개',Infinity),line('계란','10개',-1),line('계란','10개','5000')],0)]},
    {recipeFacts:{'recipe-1':{cost:'1200'}}}]){
    const result=estimate(recipe({계란:'1개'}),flow);
    assert.equal(result.kind,'unknown');assert.equal(result.total,null);assert.equal(result.knownSubtotal,null);
  }
  for(const r of [null,{},recipe({계란:'0개'}),{id:'recipe-1',amounts:'invalid',f:[null]}]){
    assert.equal(estimate(r).kind,'unknown');assert.equal(estimate(r).total,null);
  }
});

test('a real day and finite positive serving count are required',()=>{
  const r=recipe({계란:'1개'});
  for(const day of [undefined,'2026-02-30','2026-11','2026-11-1',null])
    assert.throws(()=>C.estimate(r,{day}),/real YYYY-MM-DD/);
  for(const portions of [0,-1,NaN,Infinity,'2',101,null])
    assert.throws(()=>C.estimate(r,{day:DAY,portions}),/Portions/);
});

test('all estimate paths leave the recipe, saved workflow and receipt text unchanged',()=>{
  const r=freeze(recipe({계란:'1개',토마토:'1/2개'})),flow=freeze({expenses:[purchase('immutable',DAY,[line('계란','10개',5000)])]});
  const before=JSON.stringify({r,flow});estimate(r,flow,2);assert.equal(JSON.stringify({r,flow}),before);
  const entered=freeze({recipeFacts:{'recipe-1':{cost:1000,source:'기존 값'}}});
  const enteredBefore=JSON.stringify(entered);estimate(r,entered,3);assert.equal(JSON.stringify(entered),enteredBefore);
});

test('the same pure API is exposed in a browser without CommonJS or network access',()=>{
  const sandbox={window:{KitchenJourneyModel:J},console};
  vm.runInNewContext(fs.readFileSync(require.resolve('../designs/miniature-kitchen/recipe-cost.js'),'utf8'),sandbox);
  assert.equal(typeof sandbox.window.KitchenRecipeCost.estimate,'function');
  assert.equal(sandbox.window.KitchenRecipeCost.estimate(recipe({계란:'1개'}),{day:DAY}).kind,'unknown');
});

// Reference amounts below are explicit test fixtures, not product prices.
const reference=items=>({day:'2026-10-23',items:items.map(item=>({...item,source:item.source??'QA reference fixture'}))});
const suggest=(r,flow={},ref=reference([]),portions=1,day=DAY)=>C.suggest(r,{flow,day,portions,reference:ref});
const mainRecipe=(amounts,primary,seasonings=[])=>({...recipe(amounts),f:primary,p:[],s:seasonings});

test('suggest keeps entered and complete purchase totals as full-recipe estimates',()=>{
  const r=mainRecipe({계란:'1개',간장:'1작은술'},['계란'],['간장']);
  const manual=suggest(r,{recipeFacts:{'recipe-1':{cost:0,source:'내 값'}}});
  assert.equal(manual.scope,'recipe');assert.equal(manual.kind,'entered');assert.equal(manual.total,0);
  assert.deepEqual(manual.excluded,[]);
  const flow={expenses:[purchase('complete',DAY,[line('계란','10개',5000,'eggs'),line('간장','10작은술',1000,'soy')])]};
  const full=suggest(r,flow,reference([{name:'계란',quantity:'10개',amount:1000}]));
  assert.equal(full.scope,'recipe');assert.equal(full.kind,'purchase');assert.equal(full.total,600);
  assert.equal(full.rows[0].sourceKind,'purchase');assert.equal(full.rows[0].usedQuantity,'1개');
  assert.deepEqual(full.excluded,[]);
});

test('a complete primary-only reference sum explicitly excludes seasonings',()=>{
  const r=mainRecipe({계란:'2개',양파:'1/4개',소금:'조금'},['계란','양파'],['소금']);
  const result=suggest(r,{},reference([{name:'계란',quantity:'10개',amount:5000,product:'QA eggs'},
    {name:'양파',quantity:'2개',amount:2000,product:'QA onion'}]));
  assert.equal(result.scope,'main');assert.equal(result.kind,'reference');assert.equal(result.total,1250);
  assert.deepEqual(result.excluded,['소금']);assert.deepEqual(result.missing,[]);
  assert.deepEqual(result.rows.map(row=>row.name),['계란','양파']);
  assert.match(result.basisNote,/주재료만/);assert.match(result.basisNote,/양념\(소금\)/);
  assert.match(result.basisNote,/실시간 가격/);assert.equal(result.sources[0].day,'2026-10-23');
});

test('eligible past receipts precede reference prices without turning an incomplete recipe into a full cost',()=>{
  const r=mainRecipe({계란:'1개',양파:'1/4개',소금:'조금'},['계란','양파'],['소금']);
  const flow={expenses:[purchase('past','2026-10-01',[line('달걀','10알',6000)])]};
  const result=suggest(r,flow,reference([{name:'계란',quantity:'10개',amount:3000},{name:'양파',quantity:'2개',amount:2000}]));
  assert.equal(result.scope,'main');assert.equal(result.kind,'mixed');assert.equal(result.total,850);
  assert.equal(result.rows[0].source,'past');assert.equal(result.rows[0].sourceKind,'purchase');
  assert.equal(result.rows[1].sourceKind,'reference');
  assert.equal(estimate(r,flow).kind,'partial','the original complete-recipe estimate semantics stay unchanged');
});

test('primary-only known receipt prices remain purchase estimates with their limited scope',()=>{
  const r=mainRecipe({계란:'1개',소금:'조금'},['계란'],['소금']);
  const result=suggest(r,{expenses:[purchase('eggs',DAY,[line('계란','10개',5000)])]});
  assert.equal(result.kind,'purchase');assert.equal(result.scope,'main');assert.equal(result.total,500);
  assert.deepEqual(result.excluded,['소금']);
});

test('missing primary prices preserve a partial subtotal, while no quoted main ingredient stays unknown',()=>{
  const r=mainRecipe({계란:'2개',토마토:'1개',소금:'조금'},['계란','토마토'],['소금']);
  const partial=suggest(r,{},reference([{name:'계란',quantity:'10개',amount:5000}]));
  assert.equal(partial.kind,'partial');assert.equal(partial.scope,'main');assert.equal(partial.total,null);
  assert.equal(partial.knownSubtotal,1000);assert.deepEqual(partial.missing.map(row=>row.name),['토마토']);
  const unknown=suggest(r);assert.equal(unknown.kind,'unknown');assert.equal(unknown.total,null);
  assert.equal(unknown.knownSubtotal,null);assert.equal(unknown.missing.length,2);
  assert.match(unknown.basisNote,/계산하지 않았/);
});

test('a future or unsourced reference cannot price a past recipe',()=>{
  const r=mainRecipe({계란:'1개',소금:'조금'},['계란'],['소금']);
  const future=reference([{name:'계란',quantity:'10개',amount:5000}]);future.day='2026-11-11';
  assert.equal(suggest(r,{},future).kind,'unknown');
  const itemFuture=reference([{name:'계란',quantity:'10개',amount:5000,day:'2026-11-11'}]);
  assert.equal(suggest(r,{},itemFuture).kind,'unknown');
  assert.equal(suggest(r,{}, {day:'2026-10-23',items:[{name:'계란',quantity:'10개',amount:5000}]}).kind,'unknown');
});

test('count-to-mass and spoon-to-mass remain unknown without explicit labelled reference assumptions',()=>{
  const r=mainRecipe({양파:'1/4개',요거트:'플레인 2큰술',소금:'조금'},['양파','요거트'],['소금']);
  const ref=reference([{name:'양파',quantity:'1kg',amount:3000},{name:'요거트',quantity:'300g',amount:3000}]);
  assert.equal(suggest(r,{},ref).kind,'unknown');
  ref.measurements=[{name:'양파',fromQuantity:'1개',toQuantity:'200g',label:'QA 계산 가정: 양파 1개=200g'},
    {name:'요거트',fromQuantity:'1큰술',toQuantity:'15g',label:'QA 계산 가정: 요거트 1큰술=15g'}];
  const converted=suggest(r,{},ref);
  assert.equal(converted.kind,'reference');assert.equal(converted.scope,'main');assert.equal(converted.total,450);
  assert.deepEqual(converted.rows.map(row=>row.usedQuantity),['50g','30g']);
  assert.ok(converted.rows.every(row=>row.assumption?.startsWith('QA 계산 가정')));
  assert.equal(converted.assumptions.length,2);assert.match(converted.basisNote,/실제 관측값이 아니/);
});

test('reference assumptions never reinterpret a receipt quantity or the original full estimate',()=>{
  const r=mainRecipe({양파:'1/4개',소금:'조금'},['양파'],['소금']);
  const flow={expenses:[purchase('actual',DAY,[line('양파','1kg',9000)])]};
  const ref=reference([]);ref.measurements=[{name:'양파',fromQuantity:'1개',toQuantity:'200g',label:'QA 가정'}];
  assert.equal(suggest(r,flow,ref).kind,'unknown');assert.equal(estimate(r,flow).kind,'unknown');
  ref.items.push({name:'양파',quantity:'1kg',amount:3000,source:'QA reference'});
  const result=suggest(r,flow,ref);assert.equal(result.total,150);assert.equal(result.rows[0].sourceKind,'reference');
  assert.equal(result.rows[0].source,'QA reference');
});

test('an explicit written cheese alternative uses its matching unit and reports the chosen quantity',()=>{
  const r=mainRecipe({치즈:'1장 또는 20g',소금:'조금'},['치즈'],['소금']);
  const result=suggest(r,{},reference([{name:'치즈',quantity:'10장',amount:5000}]),2);
  assert.equal(result.kind,'reference');assert.equal(result.total,1000);
  assert.equal(result.rows[0].usedQuantity,'2장');assert.equal(result.rows[0].assumption,null);
  const flow={expenses:[purchase('mass-purchase',DAY,[line('치즈','200g',2000)])]};
  const receipt=suggest(r,flow,reference([{name:'치즈',quantity:'10장',amount:5000}]));
  assert.equal(receipt.kind,'purchase');assert.equal(receipt.total,200);assert.equal(receipt.rows[0].usedQuantity,'20g');
});

test('explicit reference zero and unknown primary amounts remain distinct',()=>{
  const r=mainRecipe({계란:'1개',소금:'조금'},['계란'],['소금']);
  const zero=suggest(r,{},reference([{name:'계란',quantity:'10개',amount:0}]));
  assert.equal(zero.kind,'reference');assert.equal(zero.total,0);assert.equal(zero.knownSubtotal,0);
  const noAmount=suggest(mainRecipe({계란:'수량 미입력',소금:'조금'},['계란'],['소금']),{},reference([{name:'계란',quantity:'10개',amount:0}]));
  assert.equal(noAmount.kind,'unknown');assert.equal(noAmount.total,null);assert.equal(noAmount.knownSubtotal,null);
});

test('invalid measurement definitions cannot silently manufacture a unit conversion',()=>{
  const r=mainRecipe({양파:'1/4개',소금:'조금'},['양파'],['소금']);
  const ref=reference([{name:'양파',quantity:'1kg',amount:3000}]);
  for(const measurement of [{name:'양파',fromQuantity:'1개',toQuantity:'200g'},
    {name:'양파',fromQuantity:'0개',toQuantity:'200g',label:'QA 가정'},
    {name:'양파',fromQuantity:'1개',toQuantity:'조금',label:'QA 가정'},
    {name:'당근',fromQuantity:'1개',toQuantity:'200g',label:'QA 가정'}]){
    assert.equal(suggest(r,{}, {...ref,measurements:[measurement]}).kind,'unknown');
  }
});

test('reference suggestions leave recipes, original receipts, facts, spending and reference data exact',()=>{
  const r=freeze(mainRecipe({계란:'1개',양파:'1/4개',소금:'조금'},['계란','양파'],['소금']));
  const flow=freeze({expenses:[purchase('discount',DAY,[line('계란','10개',5000,'eggs'),line('우유','1L',3000,'milk')],7000)],recipeFacts:{}});
  const ref=freeze({...reference([{name:'양파',quantity:'1kg',amount:3000,source:{url:'https://example.invalid/qa-only'},samples:2}]),
    measurements:[{name:'양파',fromQuantity:'1개',toQuantity:'200g',label:'QA 가정'}]});
  const before=JSON.stringify({r,flow,ref}),result=suggest(r,flow,ref,2);
  assert.equal(result.total,1300);assert.equal(result.scope,'main');assert.equal(result.kind,'mixed');
  assert.match(result.basisNote,/할인·추가금/);assert.equal(JSON.stringify({r,flow,ref}),before);
  result.sources[1].source.url='changed result only';assert.equal(ref.items[0].source.url,'https://example.invalid/qa-only');
});

function runtimePrices(){
  const sandbox={window:{}};
  for(const path of ['catalog.js','recipe-price-reference.js'])
    vm.runInNewContext(fs.readFileSync(require.resolve('../designs/miniature-kitchen/'+path),'utf8'),sandbox);
  return {catalog:sandbox.window.KitchenCatalog,prices:sandbox.window.KitchenRecipeReference};
}

test('the selected public price facts retain their dated package amounts and source identity',()=>{
  const {prices}=runtimePrices(),pin='da2abfa6c7019c7ed86b078dd0fd4ac20e83dcff';
  // These eight facts were checked against the pinned publisher snapshot.
  // Yogurt is 85g x4; cheese declares 18g x14 slices; onion declares 1500g/bag.
  const facts=[['계란','15개',9480,116,1075],['두부','300g',1680,17,967],
    ['애호박','1개',990,3,934],['버섯','100g',2140,3,931],['요거트','340g',3980,5,1249],
    ['치즈','14장',8480,2,1260],['양파','1500g',3733,3,295],['밥/즉석밥','210g',2000,133,292]];
  assert.equal(prices.day,'2026-10-23');assert.equal(prices.items.length,facts.length);
  assert.equal(prices.availableFrom,'2026-11-10','app availability is separate from the older observation day');
  for(const [name,quantity,cost,samples,id]of facts){
    const actual=prices.items.find(item=>item.name===name);
    assert.ok(actual,name);assert.equal(actual.quantity,quantity);assert.equal(actual.amount,cost);
    assert.equal(actual.samples,samples);assert.equal(actual.source.productId,id);
    assert.equal(actual.source.day,prices.day);assert.ok(actual.source.url.includes(pin));
    assert.match(actual.source.label,new RegExp(samples+'개 매장 중앙값'));assert.ok(actual.product);
  }
  assert.ok(prices.source.url.includes(pin));assert.match(prices.source.notice,/현재가·전국 평균·실제 구매가가 아닙니다/);
  assert.match(prices.source.notice,/직접 대조는 하지 못/);
  assert.ok(!prices.items.some(item=>['닭가슴살','토마토'].includes(item.name)));
  assert.equal(prices.measurements.length,3);
  const assumptions=[['양파','1개','200g'],['요거트','1큰술','15g'],['밥/즉석밥','1공기','210g']];
  for(const [name,fromQuantity,toQuantity]of assumptions){
    const actual=prices.measurements.find(row=>row.name===name);
    assert.equal(actual.fromQuantity,fromQuantity);assert.equal(actual.toQuantity,toQuantity);assert.match(actual.label,/^계산 가정:/);
  }
});

test('all eight runtime recipes match independent main-ingredient arithmetic without inventing missing prices',()=>{
  const {catalog,prices}=runtimePrices(),original=JSON.stringify({catalog,prices});freeze(catalog);freeze(prices);
  const day='2026-11-10';
  const egg=9480/15,onionQuarter=3733/1500*200/4,tofu=1680/300*150,yogurt=3980/340*15*2;
  const expected={'recipe-1':egg+onionQuarter+2000,'recipe-2':tofu+990/4+onionQuarter,
    'recipe-4':990/3+egg,'recipe-5':yogurt+egg*2,'recipe-6':tofu+onionQuarter,
    'recipe-7':tofu+2140/100*70+onionQuarter};
  const results=catalog.map(r=>({recipe:r,result:C.suggest(r,{day,flow:{},reference:prices})}));
  assert.equal(results.filter(row=>row.result.kind==='reference'&&row.result.total!==null).length,6);
  for(const {recipe:r,result}of results){
    assert.equal(result.scope,'main');assert.deepEqual([...result.excluded],[...r.s]);
    for(const row of result.rows.filter(row=>row.cost!==null)){
      assert.equal(row.sourceKind,'reference');assert.equal(row.day,prices.day);assert.ok(row.usedQuantity);
    }
    if(Object.hasOwn(expected,r.id)){
      assert.equal(result.kind,'reference');assert.equal(result.missing.length,0);
      // Existing quantity parsing keeps six decimal places; display is whole KRW.
      assert.ok(Math.abs(result.total-expected[r.id])<.001,r.name);
      assert.equal(Math.round(result.total),Math.round(expected[r.id]));
    }
  }
  const chicken=results.find(row=>row.recipe.id==='recipe-3').result;
  assert.equal(chicken.kind,'unknown');assert.equal(chicken.total,null);assert.equal(chicken.knownSubtotal,null);
  assert.deepEqual(chicken.missing.map(row=>row.name),['닭가슴살','토마토']);
  const omelette=results.find(row=>row.recipe.id==='recipe-8').result;
  assert.equal(omelette.kind,'partial');assert.equal(omelette.total,null);
  assert.ok(Math.abs(omelette.knownSubtotal-(egg*2+8480/14))<1e-6);
  assert.deepEqual(omelette.missing.map(row=>row.name),['토마토']);
  assert.equal(omelette.rows.find(row=>row.name==='치즈').usedQuantity,'1장');
  const noAssumptions={...prices,measurements:[]};
  assert.equal(C.suggest(catalog[0],{day,reference:noAssumptions}).kind,'partial');
  assert.equal(C.suggest(catalog[4],{day,reference:noAssumptions}).kind,'partial');
  assert.equal(JSON.stringify({catalog,prices}),original);
});

test('reference availability blocks later app knowledge even when its observation date is older',()=>{
  const r=mainRecipe({계란:'1개',소금:'조금'},['계란'],['소금']);
  const ref={...reference([{name:'계란',quantity:'10개',amount:5000}]),availableFrom:'2026-11-10'};
  for(const day of ['2026-11-05','2026-11-09']){
    const result=suggest(r,{},ref,1,day);
    assert.equal(result.kind,'unknown');assert.equal(result.total,null);assert.equal(result.knownSubtotal,null);
    assert.deepEqual(result.referenceDays,[]);assert.equal(Object.hasOwn(result,'referenceDay'),false);
    assert.deepEqual(result.sources,[]);
  }
  const available=suggest(r,{},ref,1,'2026-11-10');
  assert.equal(available.kind,'reference');assert.equal(available.total,500);
  assert.equal(available.referenceDay,'2026-10-23');assert.deepEqual(available.referenceDays,['2026-10-23']);
});

test('invalid availability dates disable reference prices rather than being treated as absent',()=>{
  const r=mainRecipe({계란:'1개',소금:'조금'},['계란'],['소금']);
  for(const availableFrom of [undefined,null,'bad','2026-02-30','2026-11-1',123]){
    const ref={...reference([{name:'계란',quantity:'10개',amount:5000}]),availableFrom};
    assert.equal(suggest(r,{},ref).kind,'unknown');
  }
  assert.equal(suggest(r,{},reference([{name:'계란',quantity:'10개',amount:5000}])).kind,'reference',
    'omitting the optional field retains the existing synthetic-reference contract');
});

test('receipt prices and entered totals remain usable before a reference becomes available',()=>{
  const r=mainRecipe({계란:'1개',양파:'1/4개',소금:'조금'},['계란','양파'],['소금']);
  const ref={...reference([{name:'계란',quantity:'10개',amount:3000},{name:'양파',quantity:'2개',amount:2000}]),availableFrom:'2026-11-10'};
  const flow={expenses:[purchase('past','2026-11-04',[line('계란','10개',5000)])]};
  const partial=suggest(r,flow,ref,1,'2026-11-05');
  assert.equal(partial.kind,'partial');assert.equal(partial.total,null);assert.equal(partial.knownSubtotal,500);
  assert.equal(partial.rows[0].sourceKind,'purchase');assert.deepEqual(partial.referenceDays,[]);
  const entered=suggest(r,{...flow,recipeFacts:{'recipe-1':{cost:0,source:'기존 입력'}}},ref,1,'2026-11-05');
  assert.equal(entered.kind,'entered');assert.equal(entered.total,0);assert.equal(entered.scope,'recipe');
  const full=suggest(recipe({계란:'1개'}),flow,ref,1,'2026-11-05');
  assert.equal(full.kind,'purchase');assert.equal(full.scope,'recipe');assert.equal(full.total,500);
});

test('observed reference days describe the sources actually used and do not collapse several dates to one',()=>{
  const r=mainRecipe({계란:'1개',양파:'1/4개',소금:'조금'},['계란','양파'],['소금']);
  const ref={...reference([{name:'계란',quantity:'10개',amount:5000,day:'2026-10-21'},
    {name:'양파',quantity:'2개',amount:2000,day:'2026-10-22'}]),availableFrom:'2026-11-10'};
  const result=suggest(r,{},ref);
  assert.equal(result.total,750);assert.deepEqual(result.referenceDays,['2026-10-21','2026-10-22']);
  assert.equal(Object.hasOwn(result,'referenceDay'),false);
});

test('the actual app price reference is unavailable on November5 but yields six estimates on its adoption day',()=>{
  const {catalog,prices}=runtimePrices(),before=JSON.stringify({catalog,prices});
  const early=catalog.map(recipe=>C.suggest(recipe,{day:'2026-11-05',flow:{},reference:prices}));
  assert.ok(early.every(result=>result.kind==='unknown'&&result.total===null&&result.knownSubtotal===null));
  assert.ok(early.every(result=>result.sources.length===0&&result.referenceDays.length===0));
  const current=catalog.map(recipe=>C.suggest(recipe,{day:'2026-11-10',flow:{},reference:prices}));
  assert.equal(current.filter(result=>result.total!==null).length,6);
  for(const result of current.filter(result=>result.sources.length))assert.equal(result.referenceDay,'2026-10-23');
  assert.equal(JSON.stringify({catalog,prices}),before);
});
