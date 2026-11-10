const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const J=require('../designs/miniature-kitchen/journey-model.js');
const C=require('../designs/miniature-kitchen/recipe-cost.js');

const sandbox={window:{KitchenJourneyModel:J}};
for(const file of ['catalog.js','recipe-price-reference.js','recipe-detail-view.js'])
  vm.runInNewContext(fs.readFileSync(require.resolve('../designs/miniature-kitchen/'+file),'utf8'),sandbox);
const detail=sandbox.window.KitchenRecipeDetail;
const format=detail.formatQuantityText;
const recipe=sandbox.window.KitchenCatalog.find(row=>row.id==='recipe-4');
const DAY='2026-11-10';
function freeze(value){if(value&&typeof value==='object'){Object.freeze(value);Object.values(value).forEach(freeze);}return value;}

test('actual zucchini recipe displays fractional servings without changing model quantities',()=>{
  const before=JSON.stringify(recipe);
  assert.equal(recipe.amounts.애호박,'1/3개');
  for(const [portions,raw,shown] of [[1,'0.333333개','1/3개'],[2,'0.666667개','2/3개'],
    [3,'1개','1개'],[4,'1.333333개','1 1/3개'],[0.5,'0.166667개','1/6개']]){
    const modelQuantity=J.scaleQuantity(recipe.amounts.애호박,portions);
    assert.equal(modelQuantity,raw);
    assert.equal(format(modelQuantity),shown);
    assert.equal(J.scaleQuantity(recipe.amounts.애호박,portions),raw);
  }
  assert.equal(JSON.stringify(recipe),before);
});

test('simple portions and spoon measures use readable fractions and mixed numbers',()=>{
  for(const [raw,shown] of [['0.25개','1/4개'],['0.5모','1/2모'],['0.75장','3/4장'],
    ['1.5공기','1 1/2공기'],['1.333333큰술','1 1/3큰술'],['0.125작은술','1/8작은술'],
    ['플레인 0.666667큰술','플레인 2/3큰술'],['1½개','1 1/2개'],['⅓개','1/3개']])
    assert.equal(format(raw),shown,raw);
});

test('positive small weights, volumes and counts never display as zero',()=>{
  for(const raw of ['0.005g','0.1g','0.000001g','0.0001kg','0.000001kg',
    '0.005mL','0.0001L','0.000001개']){
    assert.equal(format(raw),raw);
    assert.ok(J.parseQuantity(format(raw)).amount>0,raw);
  }
  assert.equal(format('0개'),'0개');
});

test('arbitrary decimals retain precision instead of becoming a convenient fraction',()=>{
  for(const raw of ['0.33개','0.3333개','0.62개','1.49큰술','0.123456개',
    '0.999999개','0.333333g','0.666667mL'])
    assert.equal(format(raw),raw);
});

test('unknown, informal, alternative and invalid quantities stay explicit',()=>{
  for(const raw of ['수량 미입력','보유량 확인 필요','조금','조금 · 2회분 확인',
    '1장 또는 20g','약 2개','1/0개','물 1컵','100컵',''])
    assert.equal(format(raw),raw);
});

test('rendered ingredient and price-basis quantities agree while source, stock and price remain exact',()=>{
  const world=freeze({items:[
    {id:'qa-zucchini',name:'애호박',kind:'food',quantity:'2/3개',expiry:'2026-11-20'},
    {id:'qa-egg',name:'계란',kind:'food',quantity:'2개',expiry:'2026-11-20'}
  ]});
  const flow=freeze({expenses:[],recipeFacts:{}});
  const reference=freeze(sandbox.window.KitchenRecipeReference);
  const availability=freeze(J.recipeAvailability(recipe,world,{day:DAY,portions:1}));
  const cost=freeze(C.suggest(recipe,{flow,day:DAY,portions:1,reference}));
  const values=freeze({kcal:null,carb:null,protein:null,fat:null,cost:null});
  const before=JSON.stringify({recipe,world,flow,reference,availability,cost,values});
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const html=detail.render({recipe,portions:1,availability,values,cost,
    esc,fmt:String,won:n=>n+'원',dish:()=>'<svg></svg>',button:label=>'<button>'+esc(label)+'</button>',
    availabilityTable:()=>'<table></table>'});
  assert.match(html,/필요 1\/3개/);
  assert.match(html,/보유 2\/3개/);
  assert.match(html,/사용량 1\/3개/);
  assert.doesNotMatch(html,/(?:필요|보유|사용량) 0\.(?:333333|666667)개/);
  assert.equal(JSON.stringify({recipe,world,flow,reference,availability,cost,values}),before);
  assert.deepEqual(C.suggest(recipe,{flow,day:DAY,portions:1,reference}),cost);
});
