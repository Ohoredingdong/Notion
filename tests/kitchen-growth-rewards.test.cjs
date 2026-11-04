const test=require('node:test'),assert=require('node:assert/strict');
const M=require('../designs/miniature-kitchen/play-model.js');
const ids=['recipe-1','recipe-2'];
const meal=id=>({day:'2026-11-04',name:'계란 볶음밥',portion:'1회분',recipeId:id,nutrients:Object.fromEntries(Object.keys(M.NUTRIENTS).map(k=>[k,null]))});

test('older play envelopes remain field-exact and their former free flower/cup are not charged',()=>{
 const old=M.blank();delete old.roomBasics;const model=M.create(ids,old);
 assert.deepEqual(model.state(),old);assert.equal(Object.hasOwn(model.state(),'roomBasics'),false);
 assert.equal(M.ownsRoomReward(model.state(),{items:[]},'room-flowers'),true);
 assert.equal(M.ownsRoomReward(model.state(),{items:[]},'room-cup'),true);
 assert.equal(M.ownsRoomReward(model.state(),{items:[]},'room-frame'),false);
 assert.equal(model.buy('room-flowers'),false);assert.equal(model.buy('room-cup'),false);assert.deepEqual(model.state(),old);
 assert.equal(model.summary('').tickets,0);
});

test('new kitchens keep their basic cup and acquire a room reward once from earned tickets',()=>{
 const model=M.create(ids),world={items:[]};
 assert.equal(M.ownsRoomReward(model.state(),world,'room-cup'),true);
 assert.equal(model.buy('room-cup'),false);assert.deepEqual(model.state(),M.blank());
 assert.equal(M.ownsRoomReward(model.state(),world,'room-flowers'),false);
 assert.throws(()=>model.buy('room-flowers'));assert.deepEqual(model.state(),M.blank());
 const result=model.record(meal('recipe-1'));assert.equal(result.earned,true);assert.equal(model.summary('').tickets,1);
 assert.equal(model.buy('room-flowers'),true);assert.equal(model.summary('').tickets,0);
 assert.equal(model.buy('room-flowers'),false);assert.equal(model.summary('').tickets,0);
 assert.equal(M.ownsRoomReward(model.state(),world,'room-flowers'),true);
 model.remove(result.record.id);model.record(meal('recipe-1'));assert.equal(model.summary('').tickets,0);
 assert.equal(M.valid(model.state(),ids),true);
});

test('placed legacy props are free, while room rewards can never be equipped as door magnets',()=>{
 const model=M.create(ids),world={items:[{kind:'decor',art:'flowers'}]};
 assert.equal(M.ownsRoomReward(model.state(),world,'room-flowers'),true);
 model.record(meal('recipe-1'));model.buy('room-flowers');
 assert.throws(()=>model.equip('frozenLeft','room-flowers'));
 const tampered=model.state();tampered.equipped.frozenLeft='room-flowers';assert.equal(M.valid(tampered,ids),false);
 model.record(meal('recipe-2'));model.buy('tile');model.equip('frozenLeft','tile');
 assert.equal(model.state().equipped.frozenLeft,'tile');assert.equal(M.valid(model.state(),ids),true);
});

test('new optional ownership data is validated without changing valid old data',()=>{
 for(const basics of [['room-flowers'],['room-cup','room-cup'],'room-cup',null]){
  const bad=M.blank();bad.roomBasics=basics;assert.equal(M.valid(bad,ids),false);assert.throws(()=>M.create(ids,bad));
 }
 const world={serial:20,layer:20,doors:{freshLeft:true,freshRight:true,frozenLeft:false,frozenRight:false},items:[{id:'meal',kind:'meal',name:'계란 볶음밥',zone:'counter',x:.5,y:.96,z:1},{id:'frame',kind:'decor',art:'frame',name:'우드 액자',zone:'counter',x:.8,y:.9,z:2},{id:'basket',kind:'decor',art:'basket',name:'바구니',zone:'counter',x:.2,y:.9,z:3}]};
 assert.equal(M.validWorld(world),true);world.items[1].art='unknown';assert.equal(M.validWorld(world),false);
});
