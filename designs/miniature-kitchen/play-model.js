/* Independent miniature journal model. No storage, DOM, nutrition guesses or inventory writes. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.KitchenPlayModel=api;})(typeof window!=='undefined'?window:globalThis,function(){
'use strict';
const NUTRIENTS=Object.freeze({kcal:['열량','kcal'],carb:['탄수화물','g'],protein:['단백질','g'],fat:['지방','g'],fiber:['식이섬유','g'],water:['수분','mL']});
const REWARDS=Object.freeze({tile:{name:'세라믹 타일',cost:1},daisy:{name:'데이지 마그넷',cost:2},photo:{name:'딸기 그림 액자',cost:2},plate:{name:'우리 집 이름표',cost:3}});
const clone=x=>JSON.parse(JSON.stringify(x));
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T12:00:00Z'))&&new Date(x+'T12:00:00Z').toISOString().slice(0,10)===x;
const text=(x,max=120)=>typeof x==='string'&&x.trim().length>0&&x.length<=max;
const amount=x=>x===null||typeof x==='number'&&Number.isFinite(x)&&x>=0&&x<=100000;
const unique=a=>new Set(a).size===a.length;
const blank=()=>({version:1,meals:[],targets:Object.fromEntries(Object.keys(NUTRIENTS).map(k=>[k,null])),discovered:[],awarded:[],owned:[],equipped:{frozenLeft:null,frozenRight:null},goal:'collection',plateLabel:'우리 집 부엌'});
function valid(s,ids){
 const allowed=new Set(ids);
 if(!s||s.version!==1||!s.targets||!Object.keys(NUTRIENTS).every(k=>amount(s.targets[k])&&(s.targets[k]===null||s.targets[k]>0)))return false;
 for(const key of ['meals','discovered','awarded','owned'])if(!Array.isArray(s[key])||s[key].length>10000)return false;
 if(!['discovered','awarded'].every(k=>unique(s[k])&&s[k].every(id=>allowed.has(id)))||!unique(s.owned)||!s.owned.every(id=>Object.hasOwn(REWARDS,id)))return false;
 if(!s.awarded.every(id=>s.discovered.includes(id))||s.owned.reduce((sum,id)=>sum+REWARDS[id].cost,0)>s.awarded.length)return false;
 if(!s.equipped||Object.keys(s.equipped).length!==2||!['frozenLeft','frozenRight'].every(k=>s.equipped[k]===null||s.owned.includes(s.equipped[k])))return false;
 const equipped=Object.values(s.equipped).filter(Boolean);if(!unique(equipped)||!['collection','recording','nutrition'].includes(s.goal)||!text(s.plateLabel,12))return false;
 if(!unique(s.meals.map(m=>m?.id)))return false;
 return s.meals.every(m=>m&&text(m.id)&&day(m.day)&&text(m.name)&&typeof m.portion==='string'&&m.portion.length<=80&&(m.recipeId===null||allowed.has(m.recipeId)&&s.awarded.includes(m.recipeId))&&m.source==='manual'&&m.nutrients&&Object.keys(NUTRIENTS).every(k=>amount(m.nutrients[k])));
}
function validWorld(w){
 const zones=['freshLeft','freshRight','frozenLeft','frozenRight','seasoning','counter','doorFreshLeft','doorFreshRight','doorFrozenLeft','doorFrozenRight'];
 if(!w||!Number.isInteger(w.serial)||w.serial<20||w.serial>1e7||!Number.isInteger(w.layer)||w.layer<1||w.layer>1e7||!w.doors||!zones.slice(0,4).every(k=>typeof w.doors[k]==='boolean')||!Array.isArray(w.items)||w.items.length>2000||!unique(w.items.map(i=>i?.id)))return false;
 if(w.items.filter(i=>i?.kind==='meal').length!==1||!w.items.some(i=>i?.kind==='meal'&&i.id==='meal'))return false;
 return w.items.every(i=>i&&text(i.id)&&/^[A-Za-z0-9_-]+$/.test(i.id)&&text(i.name)&&(i.depleted===undefined||typeof i.depleted==='boolean')&&['photo','expiryPhoto'].every(k=>i[k]===undefined||typeof i[k]==='string'&&i[k].length<250000&&/^data:image\/(?:jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(i[k]))&&(i.photoAsIcon===undefined||typeof i.photoAsIcon==='boolean')&&(i.opened===undefined||i.opened===''||day(i.opened))&&(i.expiryType===undefined||['printed','useBy','bestBefore','unknown'].includes(i.expiryType))&&(i.manualRevision===undefined||Number.isInteger(i.manualRevision)&&i.manualRevision>=0)&&['food','seasoning','meal','decor'].includes(i.kind)&&zones.includes(i.zone)&&['x','y'].every(k=>typeof i[k]==='number'&&Number.isFinite(i[k])&&i[k]>=0&&i[k]<=1)&&Number.isInteger(i.z)&&i.z>=1&&i.z<=1e7&&(i.kind!=='decor'||['utensils','flowers','cup','cookies'].includes(i.art))&&(['food','seasoning'].includes(i.kind)?typeof i.quantity==='string'&&i.quantity.length<=80&&typeof i.expiry==='string'&&(i.expiry===''||day(i.expiry)):true));
}
function create(ids,saved){
 const allowed=new Set(ids);if(saved&&!valid(saved,ids))throw new Error('기록 형식을 확인할 수 없어요.');
 let state=saved?clone(saved):blank(),seq=0,lastRemoved=null;
 const requireId=id=>{if(!allowed.has(id))throw new Error('레시피를 확인해 주세요.');};
 function summary(date){
  const rows=state.meals.filter(m=>m.day===date),cooked=[...new Set(state.meals.map(m=>m.recipeId).filter(Boolean))];
  return {rows:clone(rows),cooked,tickets:state.awarded.length-state.owned.reduce((sum,id)=>sum+REWARDS[id].cost,0),nutrients:Object.fromEntries(Object.keys(NUTRIENTS).map(k=>{const entered=rows.filter(m=>m.nutrients[k]!==null),value=entered.length?entered.reduce((a,m)=>a+m.nutrients[k],0):null,target=state.targets[k];return[k,{value,target,missing:rows.length-entered.length,percent:value!==null&&target!==null?value/target*100:null}];})),goal:state.goal==='collection'?{label:'요리 도감 3장 채우기',value:Math.min(cooked.length,3),target:3}:state.goal==='recording'?{label:'오늘 식사 한 끼 기록하기',value:Math.min(rows.length,1),target:1}:{label:'먹은 분량의 탄단지 기록하기',value:Math.min(rows.filter(m=>['carb','protein','fat'].every(k=>m.nutrients[k]!==null)).length,1),target:1}};
 }
 return {
  state:()=>clone(state),summary,
  discover(id){requireId(id);if(!state.discovered.includes(id))state.discovered.push(id);},
  setTargets(input){const next={};for(const k of Object.keys(NUTRIENTS)){const v=input[k];if(!amount(v)||v===0)throw new Error('목표는 0보다 큰 수 또는 빈칸으로 입력해 주세요.');next[k]=v;}state.targets=next;},
  record(input){
   if(state.meals.length>=10000)throw new Error('기록이 많아 새 입력을 멈췄어요.백업을 먼저 보관해 주세요.');
   if(!input||!day(input.day)||!text(input.name)||typeof input.portion!=='string'||input.portion.length>80||!input.nutrients||!Object.keys(NUTRIENTS).every(k=>amount(input.nutrients[k])))throw new Error('날짜와 식사·영양 입력값을 확인해 주세요.');
   if(input.recipeId!==null)requireId(input.recipeId);
   const record={id:'meal-'+(globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+'-'+(++seq)+'-'+Math.random().toString(36).slice(2)),day:input.day,name:input.name.trim(),portion:input.portion,recipeId:input.recipeId,nutrients:clone(input.nutrients),source:'manual'};
   while(state.meals.some(m=>m.id===record.id))record.id+='x';
   let earned=false;if(record.recipeId){if(!state.discovered.includes(record.recipeId))state.discovered.push(record.recipeId);if(!state.awarded.includes(record.recipeId)){state.awarded.push(record.recipeId);earned=true;}}
   state.meals.push(record);lastRemoved=null;return {record:clone(record),earned};
  },
  restoreMeal(record){const next=clone(state);next.meals.push(clone(record));if(!valid(next,ids))throw new Error('복구할 식사 기록을 확인해 주세요.');state=next;lastRemoved=null;},
  remove(id){const found=state.meals.find(m=>m.id===id);if(!found)return false;lastRemoved=clone(found);state.meals=state.meals.filter(m=>m.id!==id);return true;},
  undo(){if(!lastRemoved)return false;if(!state.meals.some(m=>m.id===lastRemoved.id))state.meals.push(lastRemoved);lastRemoved=null;return true;},
  buy(id){const r=REWARDS[id];if(!r)throw new Error('소품을 확인해 주세요.');if(state.owned.includes(id))return false;if(summary('').tickets<r.cost)throw new Error('꾸밈권이 더 필요해요. 새 요리를 처음 기록하면 1개를 받아요.');state.owned.push(id);return true;},
  equip(slot,id){if(!['frozenLeft','frozenRight'].includes(slot)||id!==null&&!state.owned.includes(id))throw new Error('가지고 있는 소품을 골라 주세요.');if(id)for(const key of Object.keys(state.equipped))if(state.equipped[key]===id)state.equipped[key]=null;state.equipped[slot]=id;},
  setGoal(goal){if(!['collection','recording','nutrition'].includes(goal))throw new Error('목표를 확인해 주세요.');state.goal=goal;},
  setLabel(label){if(!text(label,12))throw new Error('이름표는 1~12자로 입력해 주세요.');state.plateLabel=label.trim();}
 };
}
return {NUTRIENTS,REWARDS,blank,day,valid,validWorld,create};
});
