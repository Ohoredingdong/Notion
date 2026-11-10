/* Read-only personal nutrition comparison; never supplies targets or missing food facts. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.KitchenNutritionInsight=api;})(typeof window!=='undefined'?window:globalThis,function(){
'use strict';
const META=Object.freeze({
 kcal:['열량','kcal'],carb:['탄수화물','g'],protein:['단백질','g'],fat:['지방','g'],
 fiber:['식이섬유','g'],water:['수분','mL'],calcium:['칼슘','mg'],sodium:['나트륨','mg'],sugar:['총당류','g']
});
const EXTRA=new Set(['calcium','sodium','sugar']);
const LIMITS=new Set(['sodium','sugar']);
const known=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0;
// Remove binary addition noise without rounding a small positive amount to zero.
const clean=value=>Number(value.toPrecision(15));
const realDay=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T12:00:00Z'))&&new Date(value+'T12:00:00Z').toISOString().slice(0,10)===value;
const comparison=(value,target)=>value>target?'over':value===target?'met':'below';

function daily({play={},flow={},day,preview=null}={}){
 if(!realDay(day))throw new TypeError('A real YYYY-MM-DD day is required.');
 const meals=(Array.isArray(play?.meals)?play.meals:[]).filter(meal=>meal?.day===day);
 const validPreview=preview&&['entered','reference'].includes(preview.kind);
 const nutrients=Object.fromEntries(Object.entries(META).map(([key,[label,unit]])=>{
  const values=meals.map(meal=>EXTRA.has(key)?flow?.extraNutrients?.[meal.id]?.[key]:meal.nutrients?.[key]).filter(known);
  const knownTotal=clean(values.reduce((total,value)=>total+value,0));
  if(!Number.isFinite(knownTotal))throw new RangeError('The nutrient total cannot be represented.');
  const enteredCount=values.length,missingCount=meals.length-enteredCount;
  const rawTarget=EXTRA.has(key)?flow?.extraTargets?.[key]:play?.targets?.[key];
  const target=known(rawTarget)&&rawTarget>0?rawTarget:null;
  const mode=LIMITS.has(key)?'limit':'target',complete=meals.length>0&&missingCount===0;
  let remaining=null,excess=null,status,lowerBound=false,projection=null;
  if(!meals.length)status='no-records';
  else if(mode==='limit'&&target!==null&&knownTotal>target){
   status='over';excess=clean(knownTotal-target);lowerBound=!complete;
   if(complete)remaining=0;
  }else if(missingCount)status='partial';
  else if(target===null)status='no-target';
  else status=comparison(knownTotal,target);
  if(complete&&target!==null){
   remaining=clean(Math.max(0,target-knownTotal));excess=clean(Math.max(0,knownTotal-target));
   const incoming=validPreview?preview.nutrients?.[key]:null;
   if(known(incoming)){
    const total=clean(knownTotal+incoming);
    if(!Number.isFinite(total))throw new RangeError('The projected nutrient total cannot be represented.');
    projection={value:incoming,total,remaining:clean(Math.max(0,target-total)),excess:clean(Math.max(0,total-target)),status:comparison(total,target),kind:preview.kind};
   }
  }
  return [key,{key,label,unit,mode,value:enteredCount?knownTotal:null,knownTotal,enteredCount,missingCount,target,remaining,excess,status,complete,lowerBound,projection}];
 }));
 return {day,mealCount:meals.length,nutrients};
}
return Object.freeze({daily});
});
