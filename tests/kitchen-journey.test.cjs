const test=require('node:test');
const assert=require('node:assert/strict');
const J=require('../designs/miniature-kitchen/journey-model.js');
const F=require('../designs/miniature-kitchen/workflow-model.js');
const DAY='2026-11-01';
const item=(id,name,quantity,expiry='2026-11-05',extra={})=>({id,name,kind:'food',quantity,expiry,...extra});
const world=(...items)=>({items});
const recipe=(id,amounts,extra={})=>({id,name:id,amounts,f:Object.keys(amounts),s:[],p:[],...extra});
const plan=(id,recipeId,portions,day=DAY)=>({id,recipeId,portions,day,slot:'lunch'});
const check=(r,w,portions=1)=>J.recipeAvailability(r,w,{day:DAY,portions});
function freeze(x){if(x&&typeof x==='object'){Object.freeze(x);Object.values(x).forEach(freeze);}return x;}

test('fractional, mixed, Unicode and explicitly written measurement quantities are scaled exactly',()=>{
 assert.equal(J.scaleQuantity('1/4개',3),'0.75개');
 assert.equal(J.scaleQuantity('1/3개',3),'1개');
 assert.equal(J.scaleQuantity('0.5작은술',3),'1.5작은술');
 assert.equal(J.scaleQuantity('1 1/2큰술',2),'3큰술');
 assert.equal(J.scaleQuantity('1½큰술',2),'3큰술');
 assert.equal(J.scaleQuantity('½개',3),'1.5개');
 assert.equal(J.scaleQuantity('플레인 2큰술',3),'플레인 6큰술');
 assert.equal(J.parseQuantity('1,000그램').baseAmount,1000);
 assert.equal(J.parseQuantity('0.5킬로그램').baseAmount,500);
 assert.equal(J.parseQuantity('２５０밀리리터').baseUnit,'mL');
});

test('invalid quantities never become exact numbers or inferred densities',()=>{
 for(const text of ['조금','약 2개','1,00g','1/0개','-1개','Infinityg','1큰술쯤','1.2.3g','물 1컵','100컵'])assert.equal(J.parseQuantity(text),null,text);
 assert.equal(J.scaleQuantity('조금',3),'조금 · 3회분 확인');
 assert.throws(()=>J.scaleQuantity('1개',0));
 assert.throws(()=>J.scaleQuantity('1개',101));
 assert.throws(()=>check(recipe('r',{계란:'1개'}),world(),'2026'));
 assert.throws(()=>J.recipeAvailability(recipe('r',{계란:'1개'}),world(),{day:'2026-02-30'}));
});

test('same-unit multiple batches supply exact need and allocate earliest expiry first',()=>{
 const r=recipe('r',{계란:'3개'}),w=world(item('later','계란','2개','2026-11-08'),item('first','달걀','1알','2026-11-02'));
 const a=check(r,w);assert.equal(a.status,'ready');assert.equal(a.rows[0].available,3);assert.deepEqual(a.rows[0].allocations.map(a=>[a.itemId,a.quantity]),[['first','1알'],['later','2개']]);
});

test('only explicit mass and volume conversions are automatic',()=>{
 assert.equal(check(recipe('r',{두부:'150g'}),world(item('tofu','두부','0.5kg')),3).status,'ready');
 assert.equal(check(recipe('r',{우유:'750mL'}),world(item('milk','우유','1L'))).status,'ready');
 for(const [need,have] of [['150g','1모'],['1큰술','3작은술'],['1작은술','150ml']]){
  const r=recipe('r',{재료:need}),a=check(r,world(item('i','재료',have)));
  assert.equal(a.status,'check');assert.equal(a.rows[0].missing,null);assert.deepEqual(a.rows[0].incompatibleIds,['i']);
 }
});

test('expired, depleted and zero batches never make a recipe ready',()=>{
 const a=check(recipe('r',{계란:'3개'}),world(item('past','계란','10개','2026-10-31'),item('empty','계란','0개'),item('gone','계란','10개',undefined,{depleted:true}),item('usable','계란','1개')));
 assert.equal(a.status,'shortage');assert.equal(a.rows[0].missing,2);assert.equal(a.rows[0].shortageQuantity,'2개');assert.deepEqual(a.rows[0].allocations.map(r=>r.itemId),['usable']);assert.deepEqual(a.rows[0].expiredIds,['past']);
});

test('today is usable and invalid/missing expiry stays explicit',()=>{
 assert.equal(check(recipe('r',{계란:'1개'}),world(item('today','계란','1개',DAY))).status,'ready');
 const a=check(recipe('r',{계란:'1개'}),world(item('unknown','계란','1개','')));assert.equal(a.status,'check');assert.deepEqual(a.rows[0].unknownExpiryIds,['unknown']);
 const b=check(recipe('r',{계란:'1개'}),world(item('bad','계란','1개','2026-02-30')));assert.equal(b.status,'shortage');assert.deepEqual(b.rows[0].expiredIds,['bad']);
});

test('unknown extra stock does not cancel sufficient known stock, but prevents a false exact shortage',()=>{
 const r=recipe('r',{계란:'3개'});
 assert.equal(check(r,world(item('known','계란','3개'),item('unknown','계란','몇 개'))).status,'ready');
 const a=check(r,world(item('known','계란','1개'),item('unknown','계란','몇 개')));assert.equal(a.status,'check');assert.equal(a.rows[0].knownAvailable,1);assert.equal(a.rows[0].missing,null);assert.equal(a.rows[0].shortageQuantity,null);
});

test('unknown recipe amounts and absent amount definitions cannot claim availability',()=>{
 const a=check(recipe('r',{소금:'조금'}),world(item('salt','소금','1봉')));assert.equal(a.status,'check');assert.equal(a.rows[0].needed,null);
 const b=check({id:'r',f:['계란'],amounts:{}},world(item('egg','계란','6개')));assert.equal(b.status,'check');
 assert.equal(check({id:'r'},world()).status,'check');
});

test('explicit ingredient aliases work without matching ingredient names inside processed food',()=>{
 assert.equal(check(recipe('r',{버섯:'100g','밥/즉석밥':'1공기'}),world(item('m','양송이버섯','100g'),item('r','즉석밥','1공기'))).status,'ready');
 assert.equal(check(recipe('r',{계란:'1개'}),world(item('x','계란빵','2개'))).status,'shortage');
 assert.equal(check(recipe('r',{밥:'1공기'}),world(item('x','쌀','1공기'))).status,'shortage');
});

test('an amount alias and ingredient index do not double-count the same recipe requirement',()=>{
 const a=check(recipe('r',{'깐 양파':'1개'},{f:['양파']}),world(item('x','양파','1개')));assert.equal(a.rows.length,1);assert.equal(a.status,'ready');
});

test('3 planned portions carry fractional amounts through to shopping',()=>{
 const recipes=[recipe('r',{계란:'1개',양파:'1/4개',식용유:'1작은술',밥:'1공기'})];
 const x=J.planShopping([plan('p','r',3)],recipes,world(item('egg','계란','6개')),{day:DAY});
 assert.deepEqual(x.rows.map(r=>[r.name,r.quantity]),[['양파','0.75개'],['식용유','3작은술'],['밥','3공기']]);assert.equal(x.satisfied[0].name,'계란');
});

test('multiple plans combine ingredient needs before subtracting shared stock once',()=>{
 const recipes=[recipe('a',{계란:'1개'}),recipe('b',{달걀:'2개'})];
 const x=J.planShopping([plan('p1','a',3),plan('p2','b',2)],recipes,world(item('egg','계란','2개')),{day:DAY});
 assert.equal(x.rows.length,1);assert.equal(x.rows[0].required,'7개');assert.equal(x.rows[0].quantity,'5개');assert.equal(x.rows[0].missing,5);assert.deepEqual(x.rows[0].planIds,['p1','p2']);
});

test('overlapping alternatives cannot allocate the same lot twice across distinct shopping demands',()=>{
 const recipes=[recipe('a',{'양파/대파':'1개'}),recipe('b',{양파:'1개'})];
 const x=J.planShopping([plan('p1','a',1),plan('p2','b',1)],recipes,world(item('onion','양파','1개')),{day:DAY});
 assert.equal(x.rows.length,1);assert.equal(x.rows[0].quantity,'1개');assert.equal(x.rows[0].name,'양파/대파');assert.equal(x.satisfied[0].name,'양파');
});

test('shopping respects known unit conversion and excludes unrelated planned dates',()=>{
 const recipes=[recipe('a',{두부:'150g'})];
 const x=J.planShopping([plan('p1','a',3),plan('other','a',10,'2026-11-02')],recipes,world(item('tofu','두부','0.4kg')),{day:DAY});
 assert.equal(x.rows[0].quantity,'50g');assert.deepEqual(x.rows[0].planIds,['p1']);
});

test('shopping does not turn unknown units, unknown dates or informal recipe amounts into exact shortages',()=>{
 const recipes=[recipe('a',{두부:'150g',소금:'조금',계란:'1개'})];
 const x=J.planShopping([plan('p','a',3)],recipes,world(item('tofu','두부','1모'),item('egg','계란','3개','')),{day:DAY});
 assert.equal(x.rows.length,3);assert.equal(x.rows.find(r=>r.name==='소금').status,'shortage');assert.ok(x.rows.filter(r=>r.name!=='소금').every(r=>r.status==='unknown'));assert.ok(x.rows.every(r=>r.missing===null));assert.equal(x.rows.find(r=>r.name==='계란').quantity,'');assert.match(x.rows.find(r=>r.name==='소금').quantity,/3회분 확인/);
});

test('missing recipe or invalid plan portions are errors rather than silently generated 1x shopping',()=>{
 const r=[recipe('r',{계란:'1개'})];const x=J.planShopping([plan('bad','missing',3),plan('bad2','r',0),plan('bad3','r',NaN)],r,world(),{day:DAY});assert.equal(x.rows.length,0);assert.equal(x.errors.length,3);
});

test('recommendation exposes missing facts as null, preserving known zero',()=>{
 const r=[recipe('r',{계란:'1개'})],w=world(item('egg','계란','2개'));
 const a=J.recommend(r,w,{}, {},{day:DAY})[0];assert.equal(a.cost,null);assert.equal(a.nutrients.kcal,null);assert.equal(a.nutritionStatus,'not-enough-data');assert.ok(a.reasons.includes('재료비 미입력'));
 const b=J.recommend(r,w,{recipeFacts:{r:{cost:0,kcal:0,carb:0,protein:0,fat:0}}},{},{day:DAY})[0];assert.equal(b.cost,0);assert.equal(b.nutrients.kcal,0);assert.equal(b.nutrients.carb,0);
});

test('recommendation scales only entered facts and uses actual remaining month budget',()=>{
 const r=[recipe('r',{계란:'1개'})],w=world(item('egg','계란','3개'));
 const f={budgets:{'2026-11':10000},expenses:[{day:DAY,amount:7000},{day:'2026-10-31',amount:9000}],recipeFacts:{r:{cost:1500,kcal:200,carb:20,protein:10,fat:5}}};
 const a=J.recommend(r,w,f,{},{day:DAY,portions:3})[0];assert.equal(a.cost,4500);assert.equal(a.nutrients.carb,60);assert.equal(a.budgetRemaining,3000);assert.equal(a.budgetStatus,'over');
});

test('known affordable alternatives precede unknown and over-budget costs without treating unknown as free',()=>{
 const r=[recipe('unknown',{계란:'1개'}),recipe('over',{계란:'1개'}),recipe('within',{계란:'1개'})],w=world(item('egg','계란','3개'));
 const f={budgets:{'2026-11':2000},recipeFacts:{over:{cost:3000},within:{cost:1500}}};
 assert.deepEqual(J.recommend(r,w,f,{},{day:DAY}).map(x=>[x.recipe.id,x.budgetStatus]),[['within','within'],['unknown','unknown'],['over','over']]);
});

test('recommendation ranks quantity-confirmed recipes and then urgent ingredients with explanations',()=>{
 const r=[recipe('short',{두부:'1모'}),recipe('ordinary',{우유:'100ml'}),recipe('urgent',{계란:'1개'})],w=world(item('milk','우유','1L','2026-11-30'),item('egg','계란','1개','2026-11-02'));
 const x=J.recommend(r,w,{}, {},{day:DAY});assert.deepEqual(x.map(x=>x.recipe.id),['urgent','ordinary','short']);assert.ok(x[0].reasons.includes('3일 이내 재료 1종 활용'));assert.ok(x[0].reasons.includes('기록된 재료 수량 충족'));
});

test('targets are compared only with complete entered meal facts and are never official recommendations',()=>{
 const r=[recipe('r',{계란:'1개'})],w=world(item('egg','계란','3개')),f={recipeFacts:{r:{carb:20,protein:10,fat:5}}},targets={carb:200,protein:70,fat:60};
 for(const meals of [[],[{day:DAY,nutrients:{carb:40,protein:null,fat:20}}]]){
  const a=J.recommend(r,w,f,{targets,meals},{day:DAY})[0];assert.equal(a.nutritionStatus,'not-enough-data');assert.equal(a.nutritionFit,null);
 }
 const a=J.recommend(r,w,f,{targets,meals:[{day:DAY,nutrients:{carb:40,protein:20,fat:20}}]},{day:DAY})[0];assert.equal(a.nutritionStatus,'entered-targets');assert.ok(a.nutritionFit>0);assert.ok(a.reasons.includes('입력한 오늘 기록·목표와 비교'));
});

test('excluded ingredients are applied using exact aliases rather than substring guesses',()=>{
 const r=[recipe('egg',{계란:'1개'}),recipe('bread',{계란빵:'1개'})];assert.deepEqual(J.recommend(r,world(),{exclusions:'달걀'},{},{day:DAY}).map(x=>x.recipe.id),['bread']);
});

test('all public functions leave frozen world, recipes, plans, play and workflow unchanged',()=>{
 const r=freeze([recipe('r',{계란:'1개'})]),w=freeze(world(item('egg','계란','3개'))),plans=freeze([plan('p','r',3)]),f=freeze({budgets:{'2026-11':10000},recipeFacts:{r:{cost:1000,carb:10,protein:10,fat:2}}}),p=freeze({targets:{carb:200,protein:70,fat:60},meals:[]});
 const before=JSON.stringify({r,w,plans,f,p});check(r[0],w);J.planShopping(plans,r,w,{day:DAY});const rows=J.recommend(r,w,f,p,{day:DAY});rows[0].recipe.name='changed';assert.equal(JSON.stringify({r,w,plans,f,p}),before);
});


test('repeated fractional plans aggregate before rounding, including actual 1/3 recipe portions',()=>{
 const recipes=[recipe('r',{애호박:'1/3개'})],plans=[plan('a','r',1),plan('b','r',1),plan('c','r',1)];
 assert.equal(J.planShopping(plans,recipes,world(),{day:DAY}).rows[0].quantity,'1개');
 assert.equal(J.planShopping([plan('a','r',3)],recipes,world(),{day:DAY}).rows[0].quantity,'1개');
});

test('availability and real deductions agree at literal-unit and mixed-fraction boundaries',()=>{
 const cases=[['1킬로그램','250g','0.75킬로그램'],['1리터','250mL','0.75리터'],['100그램','25g','75그램'],['100밀리리터','25mL','75밀리리터'],['1½개','0.5개','1개'],['1 1/2큰술','0.5큰술','1큰술'],['１,０００g','250g','750g']];
 for(const [have,need,after] of cases){
  const w=world(item('x','재료',have));const a=check(recipe('r',{재료:need}),w);assert.equal(a.ready,true,have);
  const requests=a.rows.flatMap(r=>r.allocations.map(a=>({itemId:a.itemId,quantity:a.quantity})));
  const receipt=F.applyDeductions(w,requests);assert.equal(w.items[0].quantity,after,have);F.reverseDeductions(w,receipt);assert.equal(F.parseQuantity(w.items[0].quantity).baseAmount,J.parseQuantity(have).baseAmount);
 }
});

test('both quantity parsers accept the same supported boundaries and reject inferred units',()=>{
 for(const input of ['1/4개','1½큰술','1 1/2큰술','½개','플레인 2큰술','1,000그램','0.5킬로그램','２５０밀리리터','1/0개','조금','약 2개','1큰술쯤','100컵']){
  const a=J.parseQuantity(input),b=F.parseQuantity(input);assert.equal(!!a,!!b,input);
  if(a){const {prefix,...common}=a;assert.deepEqual(b,common,input);}
 }
});


test('a single recipe cannot allocate one lot twice through overlapping ingredient alternatives',()=>{
 const r=recipe('r',{'양파/대파':'1개',양파:'1개'}),w=world(item('onion','양파','1개'));
 const a=check(r,w);assert.equal(a.ready,false);assert.equal(a.status,'shortage');
 assert.equal(a.rows.flatMap(r=>r.allocations).reduce((n,a)=>n+a.amount,0),1);
 assert.equal(a.missing.reduce((n,r)=>n+r.missing,0),1);
});

test('flexible alternatives leave stock for stricter ingredients regardless of plan or lot order',()=>{
 const r=[recipe('flexible',{'양파/대파':'1개'}),recipe('strict',{양파:'1개'})],p=[plan('a','flexible',1),plan('b','strict',1)],lots=[item('onion','양파','1개'),item('scallion','대파','1개')];
 for(const plans of [p,[...p].reverse()])for(const stock of [lots,[...lots].reverse()]){
  const a=J.planShopping(plans,r,world(...stock),{day:DAY});assert.equal(a.rows.length,0);assert.equal(a.satisfied.length,2);
  const allocations=a.satisfied.flatMap(r=>r.allocations);assert.equal(allocations.filter(a=>a.itemId==='onion').reduce((n,a)=>n+a.amount,0),1);assert.equal(allocations.filter(a=>a.itemId==='scallion').reduce((n,a)=>n+a.amount,0),1);
 }
});

test('partial quantities from unknown-expiry batches cannot produce an exact shopping shortage',()=>{
 const r=[recipe('r',{계란:'1개'})],w=world(item('unknown-date','계란','1개',''));
 const x=J.planShopping([plan('p','r',3)],r,w,{day:DAY});assert.equal(x.rows[0].status,'unknown');assert.equal(x.rows[0].missing,null);assert.equal(x.rows[0].shortageQuantity,null);assert.equal(x.rows[0].quantity,'');
 assert.equal(check(r[0],w,3).status,'check');
});

test('a lot fully allocated to another plan cannot remain as incompatible available stock',()=>{
 const r=[recipe('count',{양파:'1개'}),recipe('mass',{양파:'100g'})],w=world(item('onion','양파','1개'));
 const x=J.planShopping([plan('p1','count',1),plan('p2','mass',1)],r,w,{day:DAY});assert.equal(x.rows.length,1);assert.equal(x.rows[0].status,'shortage');assert.equal(x.rows[0].quantity,'100g');assert.deepEqual(x.rows[0].incompatibleIds,[]);
});


test('cheese sheets use their explicit count unit without assuming a sheet is one piece or a weight',()=>{
 const w=world(item('cheese','치즈','4장')),r=recipe('r',{치즈:'1장'});
 const a=check(r,w,3);assert.equal(a.ready,true);assert.equal(a.rows[0].required,'3장');
 F.applyDeductions(w,a.rows[0].allocations.map(a=>({itemId:a.itemId,quantity:a.quantity})));assert.equal(w.items[0].quantity,'1장');
 assert.equal(check(r,world(item('other','치즈','4개'))).status,'check');
 assert.equal(check(r,world(item('other','치즈','100g'))).status,'check');
});

test('missing ingredients remain missing by name even when their recipe amounts require confirmation',()=>{
 const r=recipe('r',{소금:'조금'}),a=check(r,world());assert.equal(a.status,'shortage');assert.equal(a.missing.length,1);assert.equal(a.missing[0].name,'소금');assert.equal(a.missing[0].missing,null);assert.equal(a.missing[0].shortageQuantity,null);assert.equal(a.missing[0].quantityUnknown,true);assert.equal(a.unknown.length,1);
 const x=J.planShopping([plan('p','r',3)],[r],world(),{day:DAY});assert.equal(x.rows[0].status,'shortage');assert.equal(x.rows[0].quantity,'조금 · 3회분 확인');assert.equal(x.unknown.length,1);
 const withStock=check(r,world(item('salt','소금','50g')));assert.equal(withStock.status,'check');assert.equal(withStock.missing.length,0);
});


test('urgent-use recommendation reasons refer to actually allocated lots, not just matching names',()=>{
 const r=recipe('r',{두부:'150g'}),w=world(item('unknown-weight','두부','1모','2026-11-02'),item('usable','두부','200g','2026-11-30'));
 const a=check(r,w);assert.equal(a.ready,true);assert.deepEqual(a.urgent,[]);assert.deepEqual(a.rows[0].allocations.map(a=>a.itemId),['usable']);
 const x=J.recommend([r],w,{},{},{day:DAY})[0];assert.ok(x.reasons.every(reason=>!reason.includes('3일 이내')));
 const b=check(r,world(item('urgent','두부','200g','2026-11-02')));assert.deepEqual(b.urgent.map(i=>i.id),['urgent']);
});
