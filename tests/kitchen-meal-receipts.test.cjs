const test=require('node:test');
const assert=require('node:assert/strict');
const F=require('../designs/miniature-kitchen/workflow-model.js');

function legacyTransaction(){return {id:'txn-old',mealId:'meal-old',active:true,portions:1,deductions:[{itemId:'egg',amount:2,baseUnit:'개',manualRevision:0}]};}

test('legacy meal transactions retain their exact fields when newer display metadata is absent',()=>{
 const state=F.blank();state.transactions.push(legacyTransaction());const raw=JSON.stringify(state);
 assert.equal(F.valid(state),true);assert.equal(JSON.stringify(F.create(JSON.parse(raw))),raw);
 assert.equal(Object.hasOwn(state.transactions[0],'slot'),false);
 assert.equal(Object.hasOwn(state.transactions[0].deductions[0],'beforeQuantity'),false);
});

test('committed before/after labels are stable historical evidence while cancellation restores only that use',()=>{
 const world={items:[{id:'egg',name:'계란',kind:'food',quantity:'6개',manualRevision:0}]};
 const deductions=F.applyDeductions(world,[{itemId:'egg',quantity:'2개'}]).map(d=>({...d,itemName:'계란',beforeQuantity:'6개',afterQuantity:'4개'}));
 const state=F.blank();state.transactions.push({id:'txn',mealId:'meal',active:true,slot:'dinner',portions:1,deductions});
 assert.equal(F.valid(state),true);F.applyDeductions(world,[{itemId:'egg',quantity:'1개'}]);
 F.reverseDeductions(world,deductions);assert.equal(world.items[0].quantity,'5개');
 assert.equal(deductions[0].beforeQuantity,'6개');assert.equal(deductions[0].afterQuantity,'4개');
 assert.deepEqual(F.create(JSON.parse(JSON.stringify(state))).transactions,state.transactions);
});

test('invalid optional meal-slot and display snapshots cannot enter an otherwise valid workflow backup',()=>{
 const base=F.blank();base.transactions.push(legacyTransaction());
 const mutations=[s=>s.transactions[0].slot='brunch',s=>s.transactions[0].deductions[0].itemName={html:'unsafe'},s=>s.transactions[0].deductions[0].beforeQuantity=6,s=>s.transactions[0].deductions[0].afterQuantity='x'.repeat(81)];
 for(const mutate of mutations){const state=structuredClone(base);mutate(state);const raw=JSON.stringify(state);assert.equal(F.valid(state),false);assert.throws(()=>F.create(state));assert.equal(JSON.stringify(state),raw);}
});

test('optional recipe favorites preserve old notes and reject malformed imported flags',()=>{
 const state=F.blank();state.recipeNotes['recipe-1']={note:'계란은 마지막에',variation:'',favorite:true};
 const restored=F.create(JSON.parse(JSON.stringify(state)));assert.deepEqual(restored.recipeNotes,state.recipeNotes);
 restored.recipeNotes['recipe-1'].favorite='yes';assert.equal(F.valid(restored),false);
 delete restored.recipeNotes['recipe-1'].favorite;assert.equal(F.valid(restored),true);
});
