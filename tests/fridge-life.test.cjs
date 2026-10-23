'use strict';
const test=require('node:test'), assert=require('node:assert/strict');
const L=require('../use-me-first-life-model.js');
const memory=initial=>{const values=new Map(initial);return {values,getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,value)};};

test('optional life records never initialize or mutate existing inventory on reads or writes', async()=>{
  const raw=' {"private":"existing inventory"} ', storage=memory([['use-me-first-state-v5',raw]]), store=L.createStore({storage});
  assert.deepEqual(store.getState(),L.blank());assert.equal(storage.values.size,1);
  assert.equal(await store.update(s=>{s.budget=300000;}),true);
  assert.equal(storage.getItem('use-me-first-state-v5'),raw);assert.equal(store.getState().budget,300000);
});

test('malformed, future and invalid calendar records block writes without replacing the original',async()=>{
  for(const raw of ['{broken',JSON.stringify({...L.blank(),version:2}),JSON.stringify({...L.blank(),claims:['2026-02-30']})]){
    const storage=memory([[L.KEY,raw]]), store=L.createStore({storage});
    assert.match(store.error,/기록/);assert.equal(await store.update(s=>{s.budget=100;}),false);assert.equal(storage.getItem(L.KEY),raw);
  }
});

test('invalid amounts, dates, unknown nutrient rows and locked decorations cannot be saved',async()=>{
  const storage=memory(), store=L.createStore({storage});
  for(const mutate of [s=>{s.budget=-1;},s=>{s.theme='sage';},s=>{s.claims.push('2026-10-23','2026-10-23');},s=>{s.nutrition.push({id:'a',name:'x',day:'2026-10-23',kcal:null,carb:null,protein:null,fat:null,source:'manual'});},s=>{s.budget=Infinity;}]){
    assert.equal(await store.update(mutate),false);assert.equal(storage.getItem(L.KEY),null);assert.match(store.error,/저장/);
    store.getState();assert.match(store.error,/저장/,'a render read does not swallow a failed write');
  }
  assert.equal(await store.update(s=>{s.claims.push('2026-10-23');s.theme='sage';}),true);
  assert.equal(store.error,'');
});

test('serialized transactions reread the latest data across stores; rejected locks cannot write',async()=>{
  const storage=memory();let queue=Promise.resolve();const locks={request:(_key,fn)=>{const next=queue.then(fn);queue=next;return next;}};
  const a=L.createStore({storage,locks}), b=L.createStore({storage,locks});
  await Promise.all([a.update(s=>{s.claims.push('2026-10-22');}),b.update(s=>{s.claims.push('2026-10-23');})]);
  assert.deepEqual(a.getState().claims,['2026-10-22','2026-10-23']);const raw=storage.getItem(L.KEY);
  const denied=L.createStore({storage,locks:{request:async()=>{throw Error('denied');}}});
  assert.equal(await denied.update(s=>{s.budget=1;}),false);assert.equal(storage.getItem(L.KEY),raw);assert.match(denied.error,/기다리지/);
});

test('unavailable storage and quota errors retain records and surface failed persistence',async()=>{
  const denied=L.createStore();assert.equal(await denied.update(s=>{s.budget=1;}),false);assert.match(denied.error,/저장/);
  const storage=memory([[L.KEY,JSON.stringify(L.blank())]]), raw=storage.getItem(L.KEY);storage.setItem=()=>{throw Error('quota');};const store=L.createStore({storage});
  assert.equal(await store.update(s=>{s.budget=1;}),false);assert.equal(storage.getItem(L.KEY),raw);assert.match(store.error,/quota/);
});

test('monthly ratios use only complete manual rows and distinguish missing inputs from zero',()=>{
  const s=L.blank(), row={id:'a',name:'밥',day:'2026-10-23',kcal:null,carb:10,protein:10,fat:0,source:'manual'};
  s.nutrition=[row,{...row,id:'b',protein:null},{...row,id:'old',day:'2026-09-01'}];
  s.expenses=[{id:'e',name:'장보기',day:'2026-10-23',category:'groceries',amount:12345}];
  assert.equal(L.valid(s),true);
  const r=L.report(s,{meals:[{day:'2026-10-22'},{day:'2026-09-01'}]},'2026-10');
  assert.deepEqual(r.ratio,{carb:50,protein:50,fat:0});assert.equal(r.complete,1);assert.equal(r.rows.length,2);assert.equal(r.days,1);assert.equal(r.meals,1);assert.equal(r.spending,12345);
  assert.equal(L.report(L.blank(),{meals:[]},'2026-10').ratio,null);
  assert.equal(L.day('2024-02-29'),true);assert.equal(L.day('2026-02-29'),false);
});
