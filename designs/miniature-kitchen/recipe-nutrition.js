/* Read-only, one-person recipe estimates; no default facts, targets or storage writes. */
(function(root,factory){
 if(typeof module==='object'&&module.exports)module.exports=factory(require('./journey-model.js'));
 else root.KitchenRecipeNutrition=factory(root.KitchenJourneyModel);
})(typeof window!=='undefined'?window:globalThis,function(J){
'use strict';
const KEYS=['kcal','carb','protein','fat','fiber','water','calcium','sodium','sugar'];
const known=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0;
const text=value=>typeof value==='string'&&value.trim().length>0;
const record=value=>value&&typeof value==='object'&&!Array.isArray(value);
const round=value=>Math.round(value*1e6)/1e6;
const realDay=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T12:00:00Z'))&&new Date(value+'T12:00:00Z').toISOString().slice(0,10)===value;
const names=recipe=>{
 const list=record(recipe?.amounts)?Object.keys(recipe.amounts).filter(text):[];
 for(const key of ['f','s','p'])for(const name of Array.isArray(recipe?.[key])?recipe[key]:[])
  if(text(name)&&!list.some(existing=>J.same(existing,name)))list.push(name);
 return list;
};
function grams(raw,item){
 if(typeof raw!=='string')return null;
 const alternatives=raw.split(/\s*또는\s*/).map(part=>J.parseQuantity(part)).filter(Boolean);
 // A written mass alternative is preferable to assuming a slice or piece weight.
 const mass=alternatives.find(parsed=>parsed.baseUnit==='g');
 if(mass)return mass.baseAmount;
 for(const parsed of alternatives){
  // Food water g is not a conversion for a stored mL water amount or a volume.
  if(parsed.baseUnit==='mL')continue;
  const factor=item?.gramsPerUnit?.[parsed.unit];
  if(known(factor)&&factor>0){const amount=round(parsed.amount*factor);if(Number.isFinite(amount))return amount;}
 }
 return null;
}
function estimate(recipe,{flow={},reference=null,day}={}){
 if(!J||typeof J.parseQuantity!=='function')throw new TypeError('KitchenJourneyModel is required.');
 if(!realDay(day))throw new TypeError('A real YYYY-MM-DD day is required.');
 const available=record(reference)&&realDay(reference.availableFrom)&&reference.availableFrom<=day;
 const items=available&&Array.isArray(reference.items)?reference.items:[];
 const blocked=available&&Array.isArray(reference.explicitNonMappings)?reference.explicitNonMappings:[];
 const facts=record(flow?.recipeFacts?.[recipe?.id])?flow.recipeFacts[recipe.id]:{};
 const demands=names(recipe).map(name=>{
  const item=blocked.some(excluded=>text(excluded)&&J.same(excluded,name))?null:items.find(candidate=>
   record(candidate)&&text(candidate.name)&&[candidate.name,...(Array.isArray(candidate.aliases)?candidate.aliases.filter(text):[])].some(alias=>J.same(alias,name)));
  return {name,item,grams:item?grams(recipe?.amounts?.[name],item):null};
 });
 const assumptions=[],sources=[],seenAssumptions=new Set(),seenSources=new Set();
 let usedEntered=false,usedReference=false;
 const source=(item)=>{
  const origin=record(item.source)?item.source:record(reference?.source)?reference.source:{};
  const release=text(origin.release)?origin.release:text(reference?.release)?reference.release:'';
  const base=text(origin.label)?origin.label:'참고 식품 성분';
  const label=release&&!base.includes(release)?base+' · '+release:base;
  const url=typeof origin.url==='string'&&/^https?:\/\//.test(origin.url)?origin.url:'';
  const key=label+'|'+url;if(!seenSources.has(key)){seenSources.add(key);sources.push({label,url});}
  if(text(item.assumption)&&!seenAssumptions.has(item.assumption)){seenAssumptions.add(item.assumption);assumptions.push(item.assumption);}
 };
 const nutrients=Object.fromEntries(KEYS.map(key=>{
  if(known(facts[key])){usedEntered=true;return [key,{value:facts[key],knownSubtotal:facts[key],missing:[],kind:'entered'}];}
  const values=[],missing=[];
  for(const demand of demands){
   const per100=demand.item?.per100g?.[key];
   if(!known(per100)||(demand.grams===null&&per100!==0)){missing.push(demand.name);continue;}
   const value=per100===0?0:per100*demand.grams/100;
   if(!Number.isFinite(value)){missing.push(demand.name);continue;}
   values.push(value);usedReference=true;source(demand.item);
  }
  const sum=values.reduce((total,value)=>total+value,0),subtotal=values.length&&Number.isFinite(sum)?round(sum):null;
  const complete=demands.length>0&&missing.length===0&&subtotal!==null;
  return [key,{value:complete?subtotal:null,knownSubtotal:subtotal,missing,kind:complete?'reference':subtotal===null?'unknown':'partial'}];
 }));
 if(usedEntered)sources.unshift({label:'직접 입력한 1인분 영양'+(text(facts.source)?' · '+facts.source:''),url:''});
 const referenceLabel=text(reference?.source?.label)?reference.source.label:'출처를 확인한 참고 성분';
 const sourceLabel=usedEntered?(usedReference?'직접 입력 우선 · '+referenceLabel:'직접 입력 · 1인분 기준'):usedReference?referenceLabel:'영양 정보 확인 필요';
 const notes=['1인분 기준이며, 미확인 성분은 0으로 채우지 않습니다.'];
 if(usedReference&&text(reference.cookingNote))notes.push(reference.cookingNote);
 if(available&&text(reference.waterNote))notes.push(reference.waterNote);
 if(!available)notes.push('이 날짜에 사용할 수 있는 참고 자료가 없습니다.');
 return {nutrients,sourceLabel,assumptions,sources,roles:[],note:notes.join(' ')};
}
return Object.freeze({estimate});
});
