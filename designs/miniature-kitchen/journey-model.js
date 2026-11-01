/* Pure serving, stock, shopping and recommendation rules for the existing preview. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.KitchenJourneyModel=api;})(typeof window!=='undefined'?window:globalThis,function(){
'use strict';
const EPS=1e-6;
const UNITS={g:['g',1],kg:['g',1000],그램:['g',1],킬로그램:['g',1000],ml:['mL',1],mL:['mL',1],밀리리터:['mL',1],l:['mL',1000],L:['mL',1000],리터:['mL',1000],개:['개',1],알:['개',1],모:['모',1],팩:['팩',1],병:['병',1],봉:['봉',1],조각:['조각',1],장:['장',1],공기:['공기',1],큰술:['큰술',1],작은술:['작은술',1],인분:['인분',1],캔:['캔',1]};
const ALIASES=[['계란','달걀'],['양파','깐 양파'],['버섯','표고','표고버섯','느타리','느타리버섯','팽이','팽이버섯','양송이','양송이버섯','새송이','새송이버섯'],['밥','즉석밥','쌀밥','흰밥','백미밥','잡곡밥','현미밥','햇반']];
const NUTRIENTS=['kcal','carb','protein','fat','fiber','water','calcium','sodium','sugar'];
const normalized=s=>String(s??'').normalize('NFKC').replace(/\s+/g,'').toLowerCase();
const aliases=new Map(ALIASES.flatMap(group=>group.map(name=>[normalized(name),normalized(group[0])])));
const canonical=s=>aliases.get(normalized(s))||normalized(s);
const alternatives=s=>[...new Set(String(s??'').split('/').map(canonical).filter(Boolean))];
const same=(a,b)=>alternatives(a).some(x=>alternatives(b).includes(x));
const round=n=>Math.round(n*1e6)/1e6;
const known=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
const copy=x=>JSON.parse(JSON.stringify(x));
const validDay=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s+'T12:00:00Z'))&&new Date(s+'T12:00:00Z').toISOString().slice(0,10)===s;
function requireDay(day){if(!validDay(day))throw new TypeError('A real YYYY-MM-DD day is required.');return day;}
function requirePortions(portions){if(typeof portions!=='number'||!Number.isFinite(portions)||portions<=0||portions>100)throw new TypeError('Portions must be greater than 0 and at most 100.');return portions;}
function parseQuantity(input){
 if(typeof input!=='string')return null;
 const text=input.replace(/(\d)([¼½¾⅓⅔⅛⅜⅝⅞])/g,'$1 $2').normalize('NFKC').replace(/⁄/g,'/').trim();
 // A preparation label is retained, never interpreted as a different ingredient or unit.
 const m=text.match(/^(플레인\s+)?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:\s+(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?))?(?:\s*\/\s*(\d+(?:\.\d+)?))?\s*([A-Za-z가-힣]+)$/);
 if(!m||!Object.hasOwn(UNITS,m[6])||m[3]&&m[5])return null;
 let amount=Number(m[2].replace(/,/g,''));
 if(m[3]){if(Number(m[4])===0)return null;amount+=Number(m[3])/Number(m[4]);}
 if(m[5]){if(Number(m[5])===0)return null;amount/=Number(m[5]);}
 if(!known(amount)||amount>1e8)return null;
 const [baseUnit,factor]=UNITS[m[6]];
 return {amount,unit:m[6],baseUnit,factor,baseAmount:round(amount*factor),prefix:m[1]||''};
}
function formatQuantity(base,parsed){return (parsed.prefix||'')+String(round(base/parsed.factor))+parsed.unit;}
function scaleQuantity(text,portions=1){
 requirePortions(portions);const parsed=parseQuantity(text);
 if(parsed)return formatQuantity(round(parsed.amount*parsed.factor*portions),parsed);
 return portions===1?String(text??''):String(text??'')+' · '+portions+'회분 확인';
}
function stocks(world,day){
 return (Array.isArray(world?.items)?world.items:[]).filter(i=>['food','seasoning'].includes(i?.kind)).map((item,index)=>({item,index,parsed:parseQuantity(item.quantity),expired:!!item.expiry&&(!validDay(item.expiry)||item.expiry<day),unknownExpiry:!item.expiry}));
}
function demands(recipe,portions){
 const amounts=recipe?.amounts||{},names=[...Object.keys(amounts)];
 for(const name of [...(recipe?.f||[]),...(recipe?.s||[]),...(recipe?.p||[])])if(!names.some(existing=>same(existing,name)))names.push(name);
 return names.map(name=>{const original=typeof amounts[name]==='string'?amounts[name]:'수량 미입력',parsed=parseQuantity(original);return {name,required:scaleQuantity(original,portions),parsed,rawNeeded:parsed?parsed.amount*parsed.factor*portions:null,needed:parsed?round(parsed.amount*parsed.factor*portions):null,portions,planIds:[]};});
}
function analyze(demand,stock,remaining,assigned){
 const matching=stock.filter(s=>same(s.item.name,demand.name)),usable=matching.filter(s=>!s.expired&&!s.item.depleted&&(!s.parsed||(remaining?.get(s.item.id)??s.parsed.baseAmount)>0)),expired=matching.filter(s=>s.expired),parsed=demand.parsed;
 const numeric=parsed?usable.filter(s=>s.parsed?.baseUnit===parsed.baseUnit):[],unknown=usable.filter(s=>!s.parsed),incompatible=parsed?usable.filter(s=>s.parsed&&s.parsed.baseUnit!==parsed.baseUnit):usable.filter(s=>s.parsed);
 const available=round(numeric.reduce((n,s)=>n+(remaining?.get(s.item.id)??s.parsed.baseAmount),0)),needed=demand.needed;
 const row={name:demand.name,required:demand.required,needed,available:!numeric.length&&(unknown.length||incompatible.length)?null:available,knownAvailable:available,baseUnit:parsed?.baseUnit||null,unit:parsed?.unit||null,factor:parsed?.factor||null,availableQuantity:parsed?formatQuantity(available,parsed):null,missing:null,shortageQuantity:null,quantity:'',quantityUnknown:!parsed,status:'unknown',reason:'',lotIds:numeric.map(s=>s.item.id),expiredIds:expired.map(s=>s.item.id),unknownIds:unknown.map(s=>s.item.id),incompatibleIds:incompatible.map(s=>s.item.id),unknownExpiryIds:[],allocations:[],planIds:[...demand.planIds],portions:demand.portions};
 if(!parsed){row.status=usable.length?'unknown':'shortage';row.reason=usable.length?'필요량의 숫자·단위를 직접 확인해 주세요.':expired.length?'기한이 지난 기록을 제외하면 보유 기록이 없어요. 필요량을 확인해 주세요.':'보유 기록이 없어요. 필요량의 숫자·단위도 확인해 주세요.';row.quantity=demand.required;return row;}
 let left=needed;
 const ordered=[...numeric].sort((a,b)=>(a.item.expiry||'9999').localeCompare(b.item.expiry||'9999')||a.index-b.index);
 for(const s of ordered){
  const have=remaining?.get(s.item.id)??s.parsed.baseAmount,used=assigned?round(assigned.get(s.item.id)||0):round(Math.min(have,Math.max(0,left)));
  if(used<=0)continue;
  row.allocations.push({itemId:s.item.id,quantity:formatQuantity(used,s.parsed),amount:used,baseUnit:parsed.baseUnit,manualRevision:s.item.manualRevision||0});
  if(s.unknownExpiry)row.unknownExpiryIds.push(s.item.id);
  left=round(Math.max(0,left-used));
 }
 if(row.unknownExpiryIds.length){row.reason='보유량은 기록돼 있어요. 사용할 묶음의 기한을 확인해 주세요.';row.quantity='';}
 else if(left<=EPS){row.status='enough';row.missing=0;row.shortageQuantity=formatQuantity(0,parsed);row.quantity=row.shortageQuantity;row.reason=row.unknownExpiryIds.length?'수량은 기록돼 있어요. 사용할 묶음의 기한을 확인해 주세요.':'기록한 수량이 필요량을 충족해요.';}
 else if(unknown.length||incompatible.length){row.reason=unknown.length?'수량을 모르는 보유 재료가 있어 부족량을 확정할 수 없어요.':'보유량과 레시피의 단위가 달라 직접 확인해야 해요.';row.quantity=demand.required;}
 else{row.status='shortage';row.missing=left;row.shortageQuantity=formatQuantity(left,parsed);row.quantity=row.shortageQuantity;row.reason=expired.length?'기한이 지난 묶음을 제외한 부족량이에요.':'기록한 재고를 뺀 부족량이에요.';}
 return row;
}
// Allocate a finite batch once across all demands. Residual edges let a flexible
// alternative release a batch needed by a stricter ingredient, avoiding extra buys.
function evaluateDemands(list,stock){
 const usable=stock.filter(s=>!s.expired&&!s.item.depleted&&s.parsed?.baseAmount>0).sort((a,b)=>(a.item.expiry||'9999').localeCompare(b.item.expiry||'9999')||a.index-b.index);
 const count=usable.length+list.length+2,source=count-2,sink=count-1,graph=Array.from({length:count},()=>[]),links=[];
 function edge(a,b,capacity){const forward={to:b,reverse:graph[b].length,capacity,initial:capacity},back={to:a,reverse:graph[a].length,capacity:0,initial:0};graph[a].push(forward);graph[b].push(back);return forward;}
 usable.forEach((s,i)=>edge(source,i,s.parsed.baseAmount));
 const order=list.map((d,i)=>({d,i})).sort((a,b)=>alternatives(a.d.name).length-alternatives(b.d.name).length||a.i-b.i);
 for(const {d,i} of order){
  if(!d.parsed||d.needed<=0)continue;
  edge(usable.length+i,sink,d.needed);
  usable.forEach((s,j)=>{if(s.parsed.baseUnit===d.parsed.baseUnit&&same(s.item.name,d.name)){const e=edge(j,usable.length+i,Math.min(s.parsed.baseAmount,d.needed));links.push({stock:s,demand:i,edge:e});}});
 }
 const tiny=1e-9;
 for(;;){
  const level=Array(count).fill(-1),queue=[source];level[source]=0;
  for(let at=0;at<queue.length;at++)for(const e of graph[queue[at]])if(e.capacity>tiny&&level[e.to]<0){level[e.to]=level[queue[at]]+1;queue.push(e.to);}
  if(level[sink]<0)break;
  const next=Array(count).fill(0);
  function send(node,amount){
   if(node===sink)return amount;
   for(;next[node]<graph[node].length;next[node]++){
    const e=graph[node][next[node]];if(e.capacity<=tiny||level[e.to]!==level[node]+1)continue;
    const moved=send(e.to,Math.min(amount,e.capacity));
    if(moved>tiny){e.capacity-=moved;graph[e.to][e.reverse].capacity+=moved;return moved;}
   }
   return 0;
  }
  while(send(source,Infinity)>tiny){}
 }
 const assignments=list.map(()=>new Map()),used=new Map();
 for(const link of links){const amount=round(link.edge.initial-link.edge.capacity);if(amount>0){assignments[link.demand].set(link.stock.item.id,amount);used.set(link.stock.item.id,round((used.get(link.stock.item.id)||0)+amount));}}
 return list.map((d,i)=>{
  const available=new Map(stock.filter(s=>s.parsed).map(s=>[s.item.id,round(s.parsed.baseAmount-(used.get(s.item.id)||0)+(assignments[i].get(s.item.id)||0))]));
  return analyze(d,stock,available,assignments[i]);
 });
}
function recipeAvailability(recipe,world,{day,portions=1}={}){
 requireDay(day);requirePortions(portions);const stock=stocks(world,day),rows=evaluateDemands(demands(recipe,portions),stock);
 const missing=rows.filter(r=>r.status==='shortage'),unknown=rows.filter(r=>r.status==='unknown'||r.quantityUnknown||r.unknownExpiryIds.length),hasRequirements=rows.length>0;
 const allocatedIds=new Set(rows.flatMap(row=>row.allocations.map(a=>a.itemId)));
 const relevant=stock.filter(s=>rows.some(r=>same(r.name,s.item.name))),urgent=relevant.filter(s=>allocatedIds.has(s.item.id)&&!s.expired&&!s.item.depleted&&s.parsed?.baseAmount>0&&s.item.expiry&&Date.parse(s.item.expiry+'T12:00:00Z')-Date.parse(day+'T12:00:00Z')<=3*86400000).map(s=>copy(s.item));
 return {status:missing.length?'shortage':unknown.length||!hasRequirements?'check':'ready',ready:hasRequirements&&!missing.length&&!unknown.length,portions,rows,missing,unknown,urgent,expired:relevant.filter(s=>s.expired).map(s=>copy(s.item))};
}
function planShopping(plans,catalog,world,{day}={}){
 requireDay(day);const combined=new Map(),errors=[];
 for(const plan of Array.isArray(plans)?plans:[]){
  if(plan?.day!==day)continue;
  const recipe=(Array.isArray(catalog)?catalog:[]).find(r=>r.id===plan.recipeId);
  if(!recipe||!known(plan.portions)||plan.portions<=0||plan.portions>100){errors.push({planId:plan.id,reason:recipe?'계획 분량을 확인해 주세요.':'계획의 요리를 찾을 수 없어요.'});continue;}
  for(const d of demands(recipe,plan.portions)){
   const key=alternatives(d.name).sort().join('/')+'|'+(d.parsed?.baseUnit||'unknown:'+d.required),old=combined.get(key);
   if(old&&d.parsed){old.rawNeeded+=d.rawNeeded;old.needed=round(old.rawNeeded);old.required=formatQuantity(old.needed,old.parsed);old.planIds.push(plan.id);old.portions=round(old.portions+plan.portions);}
   else if(old){old.planIds.push(plan.id);old.portions=round(old.portions+plan.portions);old.required=d.required+' · 여러 식단의 필요량 확인';}
   else combined.set(key,{...d,planIds:[plan.id]});
  }
 }
 const stock=stocks(world,day),all=evaluateDemands([...combined.values()],stock);
 return {rows:all.filter(r=>r.status!=='enough'||r.unknownExpiryIds.length),unknown:all.filter(r=>r.status==='unknown'||r.quantityUnknown||r.unknownExpiryIds.length),satisfied:all.filter(r=>r.status==='enough'&&!r.unknownExpiryIds.length),errors};
}
function recommend(catalog,world,flow={},play={}, {day,portions=1}={}){
 requireDay(day);requirePortions(portions);const month=day.slice(0,7),budget=known(flow.budgets?.[month])?flow.budgets[month]:null,spent=(flow.expenses||[]).filter(e=>e.day?.slice(0,7)===month&&known(e.amount)).reduce((n,e)=>n+e.amount,0),remaining=budget===null?null:round(budget-spent),exclusions=String(flow.exclusions||'').split(/[,\n]/).map(x=>x.trim()).filter(Boolean),meals=(play.meals||[]).filter(m=>m.day===day),core=['carb','protein','fat'];
 return (Array.isArray(catalog)?catalog:[]).filter(recipe=>!exclusions.some(name=>demands(recipe,1).some(d=>same(d.name,name)))).map((recipe,index)=>{
  const availability=recipeAvailability(recipe,world,{day,portions}),facts=flow.recipeFacts?.[recipe.id],nutrients=Object.fromEntries(NUTRIENTS.map(k=>[k,known(facts?.[k])?round(facts[k]*portions):null])),cost=known(facts?.cost)?round(facts.cost*portions):null,budgetStatus=remaining===null?'unset':cost===null?'unknown':cost<=remaining?'within':'over';
  const canCompare=core.every(k=>known(play.targets?.[k])&&play.targets[k]>0&&nutrients[k]!==null)&&meals.length>0&&meals.every(m=>core.every(k=>known(m.nutrients?.[k])));
  let nutritionFit=null;
  if(canCompare)nutritionFit=round(core.reduce((n,k)=>{const consumed=meals.reduce((sum,m)=>sum+m.nutrients[k],0),left=Math.max(0,play.targets[k]-consumed);return n+Math.min(nutrients[k],left)/play.targets[k];},0));
  const urgentNames=[...new Set(availability.urgent.map(i=>canonical(i.name)))],reasons=[];
  if(urgentNames.length)reasons.push('3일 이내 재료 '+urgentNames.length+'종 활용');
  reasons.push(availability.ready?'기록된 재료 수량 충족':availability.status==='shortage'?'부족 재료 '+availability.missing.length+'종 확인':'보유량·단위·기한 확인 필요');
  if(budgetStatus==='within')reasons.push('입력한 원가가 남은 월 예산 이내');
  if(budgetStatus==='over')reasons.push('입력한 원가가 남은 월 예산 초과');
  if(cost===null)reasons.push('재료비 미입력');
  if(core.some(k=>nutrients[k]===null))reasons.push('탄단지 정보 미입력');
  else if(canCompare)reasons.push('입력한 오늘 기록·목표와 비교');
  const budgetRank={within:0,unset:0,unknown:1,over:2}[budgetStatus];
  const rank=[budgetRank,availability.status==='ready'?0:availability.status==='check'?1:2,-urgentNames.length,availability.missing.length,availability.unknown.length,-(nutritionFit??-1),index];
  return {recipe:copy(recipe),availability,nutrients,cost,reasons,budgetStatus,budgetRemaining:remaining,nutritionStatus:canCompare?'entered-targets':'not-enough-data',nutritionFit,score:null,_rank:rank};
 }).sort((a,b)=>{for(let i=0;i<a._rank.length;i++)if(a._rank[i]!==b._rank[i])return a._rank[i]-b._rank[i];return 0;}).map(row=>{delete row._rank;return row;});
}
return Object.freeze({parseQuantity,scaleQuantity,formatQuantity,canonical,same,recipeAvailability,planShopping,recommend});
});
