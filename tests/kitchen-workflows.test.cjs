const test=require('node:test');
const assert=require('node:assert/strict');
const F=require('../designs/miniature-kitchen/workflow-model.js');
const M=require('../designs/miniature-kitchen/play-model.js');
const w=()=>({serial:20,layer:20,doors:{freshLeft:true,freshRight:true,frozenLeft:true,frozenRight:true},items:[{id:'egg',name:'계란',kind:'food',quantity:'6개',expiry:'2026-10-31',zone:'freshLeft',x:.5,y:.5,z:1},{id:'milk',name:'우유',kind:'food',quantity:'1L',expiry:'2026-11-01',zone:'freshRight',x:.5,y:.5,z:2},{id:'meal',name:'계란 볶음밥',kind:'meal',zone:'counter',x:.5,y:.5,z:3}]});
test('quantities convert only matching physical units and preserve fractions',()=>{
 assert.equal(F.parseQuantity('1/4개').baseAmount,.25);assert.equal(F.parseQuantity('1L').baseAmount,1000);assert.equal(F.parseQuantity('0.5kg').baseAmount,500);assert.equal(F.parseQuantity('0개').baseAmount,0);
 for(const bad of ['1/0개','-1g','NaN개','1개;alert(1)','약간','1e100g'])assert.equal(F.parseQuantity(bad),null,bad);
 const x=w();F.applyDeductions(x,[{itemId:'milk',quantity:'200ml'}]);assert.equal(x.items[1].quantity,'0.8L');
 assert.throws(()=>F.applyDeductions(x,[{itemId:'milk',quantity:'200g'}]),/단위/);
});
test('multi-item deductions are atomic and duplicate lines cannot overdraw stock',()=>{
 const x=w(),before=structuredClone(x);assert.throws(()=>F.applyDeductions(x,[{itemId:'milk',quantity:'200ml'},{itemId:'egg',quantity:'7개'}]),/부족/);assert.deepEqual(x,before);
 assert.throws(()=>F.applyDeductions(x,[{itemId:'egg',quantity:'4개'},{itemId:'egg',quantity:'3개'}]),/부족/);assert.deepEqual(x,before);
 const tx=F.applyDeductions(x,[{itemId:'egg',quantity:'1개'},{itemId:'egg',quantity:'1개'}]);assert.equal(x.items[0].quantity,'4개');assert.equal(tx.length,1);assert.equal(tx[0].amount,2);
});
test('cancel restores only its own use, including after another meal, and can be redone',()=>{
 const x=w(),a=F.applyDeductions(x,[{itemId:'egg',quantity:'2개'}]);F.applyDeductions(x,[{itemId:'egg',quantity:'1개'}]);assert.equal(x.items[0].quantity,'3개');
 F.reverseDeductions(x,a);assert.equal(x.items[0].quantity,'5개');F.reverseDeductions(x,a,-1);assert.equal(x.items[0].quantity,'3개');
});
test('manual recounts and deleted stock block undo without overwriting later data',()=>{
 const x=w(),a=F.applyDeductions(x,[{itemId:'egg',quantity:'2개'},{itemId:'milk',quantity:'200ml'}]);x.items[1].manualRevision=1;x.items[1].quantity='0.6L';const before=structuredClone(x);assert.throws(()=>F.reverseDeductions(x,a),/직접 수정/);assert.deepEqual(x,before);
 x.items=x.items.filter(i=>i.id!=='egg');assert.throws(()=>F.reverseDeductions(x,a),/직접 수정/);
});
test('monthly cash totals and energy ratios use actual expense and complete entered meals',()=>{
 const s=F.blank();s.budgets['2026-10']=400000;s.expenses=[{id:'a',day:'2026-10-01',name:'장보기',amount:232700,category:'groceries'},{id:'b',day:'2026-10-31',name:'구매',amount:3300,category:'groceries'},{id:'c',day:'2026-11-01',name:'다음 달',amount:5000,category:'delivery'}];
 const p={meals:[{day:'2026-10-31',nutrients:{carb:65,protein:18,fat:14}},{day:'2026-10-30',nutrients:{carb:null,protein:10,fat:0}}]};const r=F.monthly(s,p,'2026-10');assert.equal(r.spending,236000);assert.equal(r.budget-r.spending,164000);assert.equal(r.days,2);assert.equal(r.complete,1);assert.ok(Math.abs(r.ratio.carb-260/458*100)<1e-9);
});
test('existing preview worlds stay valid; unsafe photo URLs and optional metadata are rejected',()=>{
 const x=w();assert.equal(M.validWorld(x),true);x.items[0].zone='doorFreshLeft';x.items[0].opened='2026-10-30';x.items[0].manualRevision=1;assert.equal(M.validWorld(x),true);
 x.items[0].photo='javascript:alert(1)';assert.equal(M.validWorld(x),false);x.items[0].photo='data:image/svg+xml;base64,AAAA';assert.equal(M.validWorld(x),false);delete x.items[0].photo;
 x.items[0].expiryPhoto='https://untrusted.example/date.png';assert.equal(M.validWorld(x),false);x.items[0].expiryPhoto='data:image/png;base64,AAAA';assert.equal(M.validWorld(x),true);x.items[0].photoAsIcon='yes';assert.equal(M.validWorld(x),false);delete x.items[0].photoAsIcon;x.items[0].opened='2026-02-30';assert.equal(M.validWorld(x),false);
});
test('workflow records round-trip and invalid budgets, dates, receipts and goals are rejected',()=>{
 const s=F.blank();assert.equal(F.valid(s),true);assert.deepEqual(F.create(JSON.parse(JSON.stringify(s))),s);
 for(const mutate of [s=>s.budgets['2026-13']=1,s=>s.budgets['2026-10']=-1,s=>s.plans.push({id:'x',day:'2026-02-30',recipeId:'recipe-1',slot:'dinner',portions:1}),s=>s.extraTargets.calcium=0,s=>s.extraNutrients.x={calcium:NaN,sodium:null,sugar:null}]){const x=F.blank();mutate(x);assert.equal(F.valid(x),false);}
});
test('restoring a canceled meal retains its original ID and cannot farm first-recipe rewards',()=>{
 const p=M.create(['recipe-1']);const {record}=p.record({day:'2026-10-31',name:'식사',portion:'1회분',recipeId:'recipe-1',nutrients:{kcal:458,carb:65,protein:18,fat:14,fiber:null,water:null}});p.remove(record.id);const p2=M.create(['recipe-1'],p.state());p2.restoreMeal(record);assert.equal(p2.state().meals[0].id,record.id);assert.equal(p2.state().awarded.length,1);assert.throws(()=>p2.restoreMeal(record));assert.equal(p2.state().meals.length,1);
});
