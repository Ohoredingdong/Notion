const test=require('node:test');
const assert=require('node:assert/strict');
const F=require('../designs/miniature-kitchen/workflow-model.js');
const M=require('../designs/miniature-kitchen/play-model.js');
const state=()=>({...F.blank(),shopping:[{id:'eggs',name:'계란',quantity:'10개',estimate:5400,checked:true},{id:'milk',name:'우유',quantity:'1개',estimate:3200,checked:true},{id:'tofu',name:'두부',quantity:'1모',estimate:null,checked:false}]});
const purchase=(overrides={})=>({purchaseId:'receipt-example',day:'2026-11-04',amount:8000,items:[{shoppingId:'eggs',quantity:'10개',amount:5400},{shoppingId:'milk',quantity:'1개',amount:3200}],...overrides});
const world=()=>({serial:20,layer:20,doors:{freshLeft:true,freshRight:true,frozenLeft:true,frozenRight:true},items:[{id:'meal',kind:'meal',name:'계란 볶음밥',zone:'counter',x:.5,y:.5,z:1}]});
test('checkout stores one actual expense independently from row estimates and does not create stock',()=>{
 const s=state(),w=world(),before=structuredClone(w);const e=F.commitPurchase(s,purchase());
 assert.equal(e.amount,8000);assert.equal(e.receipt.items.reduce((n,i)=>n+i.amount,0),8600);assert.equal(s.expenses.length,1);assert.deepEqual(s.shopping.map(i=>i.id),['tofu']);assert.deepEqual(w,before);assert.equal(F.valid(s),true);
 assert.equal(F.monthly(s,{meals:[]},'2026-11').spending,8000);
});
test('the same receipt is idempotent and a competing stale checkout cannot duplicate the expense',()=>{
 const s=state();F.commitPurchase(s,purchase());const before=structuredClone(s);assert.equal(F.commitPurchase(s,purchase()).id,'receipt-example');assert.deepEqual(s,before);
 assert.throws(()=>F.commitPurchase(s,purchase({purchaseId:'another-receipt'})),/이미 구매/);assert.deepEqual(s,before);
});
test('a missing line or invalid real amount/date leaves the cart and ledger untouched',()=>{
 for(const input of [purchase({amount:NaN}),purchase({amount:-1}),purchase({day:'2026-02-30'}),purchase({items:[{shoppingId:'eggs',quantity:'10개',amount:5400},{shoppingId:'missing',quantity:'1개',amount:100}]})]){
  const s=state(),before=structuredClone(s);assert.throws(()=>F.commitPurchase(s,input));assert.deepEqual(s,before);
 }
});
test('explicit zero actual payment and unknown item prices stay distinct',()=>{
 const s=state(),e=F.commitPurchase(s,purchase({amount:0,items:[{shoppingId:'tofu',quantity:'1모',amount:null}]}));assert.equal(e.amount,0);assert.equal(e.receipt.items[0].amount,null);assert.equal(F.valid(s),true);
});
test('a reviewed purchased line creates exactly one lot while preserving saved cash',()=>{
 const s=state(),w=world();const e=F.commitPurchase(s,purchase());const before=s.expenses.map(x=>({id:x.id,amount:x.amount,day:x.day}));const line=e.receipt.items[0];
 const id=F.registerReceiptItem(w,s,e.id,line.id,{name:'계란',quantity:'10개',expiry:'2026-11-10',opened:'',kind:'food',zone:'freshLeft'});
 assert.equal(w.items.length,2);assert.equal(w.items.find(i=>i.id===id).kind,'food');assert.equal(line.registeredItemId,id);assert.deepEqual(s.expenses.map(x=>({id:x.id,amount:x.amount,day:x.day})),before);assert.equal(F.valid(s),true);assert.equal(M.validWorld(w),true);
 const snapshot={s:structuredClone(s),w:structuredClone(w)};assert.throws(()=>F.registerReceiptItem(w,s,e.id,line.id,{name:'계란',quantity:'10개',expiry:'',zone:'freshLeft'}),/이미/);assert.deepEqual({s,w},snapshot);
});
test('saved receipts round-trip and legacy expenses remain untouched and valid',()=>{
 const legacy=F.blank();legacy.expenses.push({id:'legacy',day:'2026-11-01',name:'기존 구매',amount:128000,category:'groceries'});const before=JSON.stringify(legacy);const restored=F.create(JSON.parse(before));assert.equal(JSON.stringify(restored),before);
 const s=state();F.commitPurchase(s,purchase());assert.deepEqual(F.create(JSON.parse(JSON.stringify(s))),s);const bad=structuredClone(s);bad.expenses[0].receipt.items[0].registeredItemId={bad:true};assert.equal(F.valid(bad),false);
 const duplicate=structuredClone(s);duplicate.expenses.push({...structuredClone(duplicate.expenses[0]),id:'different-expense-id'});assert.equal(F.valid(duplicate),false);
});
