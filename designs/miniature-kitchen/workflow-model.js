/* Optional workflow fields in the existing preview envelope. No storage or network. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.KitchenWorkflowModel=api;})(typeof window!=='undefined'?window:globalThis,function(){
'use strict';
const clone=x=>JSON.parse(JSON.stringify(x)),own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T12:00:00Z'))&&new Date(x+'T12:00:00Z').toISOString().slice(0,10)===x;
const text=(x,max=160)=>typeof x==='string'&&x.trim().length>0&&x.length<=max;
const num=(x,max=1e9)=>typeof x==='number'&&Number.isFinite(x)&&x>=0&&x<=max;
const money=x=>num(x)&&Number.isInteger(x);
const list=x=>Array.isArray(x)&&x.length<=10000;
const unique=x=>new Set(x).size===x.length;
const zones=['freshLeft','freshRight','frozenLeft','frozenRight','seasoning','counter','doorFreshLeft','doorFreshRight','doorFrozenLeft','doorFrozenRight'];
const units={g:['g',1],kg:['g',1000],'그램':['g',1],'킬로그램':['g',1000],'밀리리터':['mL',1],'리터':['mL',1000],ml:['mL',1],mL:['mL',1],l:['mL',1000],L:['mL',1000],'개':['개',1],'알':['개',1],'모':['모',1],'팩':['팩',1],'병':['병',1],'봉':['봉',1],'조각':['조각',1],'장':['장',1],'공기':['공기',1],'큰술':['큰술',1],'작은술':['작은술',1],'인분':['인분',1],'캔':['캔',1]};
const round=x=>Math.round(x*1e6)/1e6;
function parseQuantity(input){
 if(typeof input!=='string')return null;
 const value=input.replace(/(\d)([¼½¾⅓⅔⅛⅜⅝⅞])/g,'$1 $2').normalize('NFKC').replace(/⁄/g,'/').trim();
 const m=value.match(/^(플레인\s+)?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:\s+(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?))?(?:\s*\/\s*(\d+(?:\.\d+)?))?\s*([A-Za-z가-힣]+)$/);
 if(!m||!own(units,m[6])||m[3]&&m[5])return null;
 let amount=Number(m[2].replace(/,/g,''));
 if(m[3]){if(Number(m[4])===0)return null;amount+=Number(m[3])/Number(m[4]);}
 if(m[5]){if(Number(m[5])===0)return null;amount/=Number(m[5]);}
 if(!num(amount,1e8))return null;
 const [baseUnit,factor]=units[m[6]];return {amount,unit:m[6],baseUnit,factor,baseAmount:round(amount*factor)};
}
const quantity=(base,parsed)=>String(round(base/parsed.factor))+parsed.unit;
const blank=()=>({version:1,budgets:{},expenses:[],shopping:[],plans:[],supplements:[],recipeFacts:{},recipeNotes:{},transactions:[],lastCanceled:null,extraTargets:{calcium:null,sodium:null,sugar:null},extraNutrients:{},theme:{background:'linen',labels:'standard',organizer:false},exclusions:''});
const validReceipt=r=>r&&text(r.purchaseId,140)&&list(r.items)&&r.items.length>0&&unique(r.items.map(i=>i?.id))&&r.items.every(i=>i&&text(i.id)&&text(i.name)&&typeof i.quantity==='string'&&i.quantity.length<=80&&(i.amount===null||money(i.amount))&&(i.registeredItemId===null||text(i.registeredItemId)));
function valid(s){
 if(!s||s.version!==1||!s.budgets||Array.isArray(s.budgets)||Object.entries(s.budgets).some(([k,v])=>!/^\d{4}-(0[1-9]|1[0-2])$/.test(k)||!money(v)))return false;
 for(const k of ['expenses','shopping','plans','supplements','transactions'])if(!list(s[k])||!unique(s[k].map(x=>x?.id)))return false;
 if(!s.expenses.every(r=>r&&text(r.id)&&day(r.day)&&text(r.name)&&money(r.amount)&&['groceries','eatingout','delivery'].includes(r.category)&&(r.receipt===undefined||validReceipt(r.receipt))))return false;
 if(!unique(s.expenses.filter(r=>r.receipt).map(r=>r.receipt.purchaseId)))return false;
 if(!s.shopping.every(r=>r&&text(r.id)&&text(r.name)&&typeof r.quantity==='string'&&r.quantity.length<=80&&(r.estimate===null||money(r.estimate))&&typeof r.checked==='boolean'))return false;
 if(!s.plans.every(r=>r&&text(r.id)&&day(r.day)&&['breakfast','lunch','dinner'].includes(r.slot)&&text(r.recipeId)&&num(r.portions,100)&&r.portions>0))return false;
 if(!s.supplements.every(r=>r&&text(r.id)&&text(r.name)&&['amount','schedule','ingredients'].every(k=>typeof r[k]==='string'&&r[k].length<=500)&&(r.origin===undefined||typeof r.origin==='string'&&r.origin.length<=500)&&(r.remaining===undefined||typeof r.remaining==='string'&&r.remaining.length<=80)&&list(r.days)&&unique(r.days)&&r.days.every(day)))return false;
 if(!s.recipeFacts||!s.recipeNotes||Array.isArray(s.recipeFacts)||Array.isArray(s.recipeNotes)||Object.keys(s.recipeFacts).length>1000||Object.keys(s.recipeNotes).length>1000)return false;
 for(const [id,r] of Object.entries(s.recipeFacts))if(!/^recipe-\d+$/.test(id)||!r||!['kcal','carb','protein','fat','fiber','water'].every(k=>r[k]===null||num(r[k],100000))||!(r.cost===null||money(r.cost))||!['calcium','sodium','sugar'].every(k=>r[k]===undefined||r[k]===null||num(r[k],100000))||typeof r.source!=='string'||r.source.length>300)return false;
 for(const [id,r] of Object.entries(s.recipeNotes))if(!/^recipe-\d+$/.test(id)||!r||typeof r.note!=='string'||r.note.length>3000||typeof r.variation!=='string'||r.variation.length>1000||(r.favorite!==undefined&&typeof r.favorite!=='boolean'))return false;
 if(!unique(s.transactions.map(r=>r.mealId)))return false;
 if(!s.transactions.every(r=>r&&text(r.id)&&text(r.mealId)&&typeof r.active==='boolean'&&(r.slot===undefined||['breakfast','lunch','dinner'].includes(r.slot))&&list(r.deductions)&&r.deductions.every(d=>d&&text(d.itemId)&&num(d.amount,1e8)&&d.amount>0&&text(d.baseUnit,20)&&Number.isInteger(d.manualRevision)&&d.manualRevision>=0&&d.manualRevision<=1e7&&(d.itemName===undefined||text(d.itemName))&&['beforeQuantity','afterQuantity'].every(k=>d[k]===undefined||typeof d[k]==='string'&&d[k].length<=80))))return false;
 if(s.lastCanceled!==null&&(!s.lastCanceled||!s.lastCanceled.record||!text(s.lastCanceled.record.id)||!day(s.lastCanceled.record.day)||!text(s.lastCanceled.record.name)))return false;
 if(s.extraTargets!==undefined&&(!s.extraTargets||!['calcium','sodium','sugar'].every(k=>s.extraTargets[k]===null||num(s.extraTargets[k],100000)&&s.extraTargets[k]>0)))return false;
 if(s.extraNutrients!==undefined&&(!s.extraNutrients||Object.keys(s.extraNutrients).length>20000||Object.entries(s.extraNutrients).some(([id,r])=>!text(id)||!r||!['calcium','sodium','sugar'].every(k=>r[k]===null||num(r[k],100000)))))return false;
 if(!s.theme||!['linen','stone'].includes(s.theme.background)||!['standard','minimal'].includes(s.theme.labels)||typeof s.theme.organizer!=='boolean'||typeof s.exclusions!=='string'||s.exclusions.length>500)return false;
 return true;
}
function create(saved){const s=saved?{...blank(),...clone(saved)}:blank();if(!valid(s))throw new Error('생활 기록 형식을 확인해 주세요.');return s;}
function applyDeductions(world,requests){
 const totals=new Map();
 for(const request of requests){const item=world.items.find(i=>i.id===request.itemId&&['food','seasoning'].includes(i.kind));if(!item)throw new Error('차감할 재료를 다시 확인해 주세요.');const have=parseQuantity(item.quantity),need=parseQuantity(request.quantity);if(!have||!need||have.baseUnit!==need.baseUnit||need.baseAmount<=0)throw new Error(item.name+'의 수량과 단위를 확인해 주세요. 개·모·g처럼 다른 단위는 자동 변환하지 않아요.');const previous=totals.get(item.id);totals.set(item.id,{item,have,amount:round((previous?.amount||0)+need.baseAmount)});}
 for(const {item,have,amount} of totals.values())if(amount>have.baseAmount+1e-6)throw new Error(item.name+'의 재고가 부족해요. 실제 사용량을 확인해 주세요.');
 const receipts=[];for(const {item,have,amount} of totals.values()){receipts.push({itemId:item.id,amount,baseUnit:have.baseUnit,manualRevision:item.manualRevision||0});item.quantity=quantity(round(have.baseAmount-amount),have);}return receipts;
}
function reverseDeductions(world,receipts,direction=1){
 const changes=[];for(const r of receipts){const item=world.items.find(i=>i.id===r.itemId),have=item&&parseQuantity(item.quantity);if(!item||!have||have.baseUnit!==r.baseUnit||(item.manualRevision||0)!==r.manualRevision)throw new Error('이후 수량을 직접 수정한 재료가 있어요. 재고를 확인한 뒤 기록을 수정해 주세요.');const next=round(have.baseAmount+r.amount*direction);if(next<0)throw new Error(item.name+'의 재고가 부족해 복구할 수 없어요.');changes.push({item,value:quantity(next,have)});}for(const c of changes)c.item.quantity=c.value;
}
function monthly(state,play,month){const expenses=state.expenses.filter(r=>r.day.slice(0,7)===month),meals=play.meals.filter(r=>r.day.slice(0,7)===month),complete=meals.filter(m=>['carb','protein','fat'].every(k=>m.nutrients[k]!==null));const energy={carb:0,protein:0,fat:0};for(const m of complete){energy.carb+=m.nutrients.carb*4;energy.protein+=m.nutrients.protein*4;energy.fat+=m.nutrients.fat*9;}const sum=Object.values(energy).reduce((a,b)=>a+b,0);return {expenses,meals,spending:expenses.reduce((s,r)=>s+r.amount,0),budget:state.budgets[month]??null,days:new Set(meals.map(r=>r.day)).size,complete:complete.length,ratio:sum?Object.fromEntries(Object.entries(energy).map(([k,v])=>[k,v/sum*100])):null};}
function addItem(world,input){if(!text(input.name)||typeof input.quantity!=='string'||input.quantity.length>80||typeof input.expiry!=='string'||input.expiry!==''&&!day(input.expiry)||!zones.includes(input.zone))throw new Error('이름·수량·기한·위치를 확인해 주세요.');let id;do{id='stock'+(++world.serial);}while(world.items.some(i=>i.id===id));world.layer++;world.items.push({id,kind:input.kind==='seasoning'?'seasoning':'food',name:input.name.trim(),quantity:input.quantity.trim(),expiry:input.expiry,zone:input.zone,x:.5,y:.63,z:world.layer,opened:input.opened||'',expiryType:input.expiryType||'printed',manualRevision:0,...(input.photo?{photo:input.photo,photoAsIcon:input.photoAsIcon!==false}:{}),...(input.expiryPhoto?{expiryPhoto:input.expiryPhoto}:{})});const door=input.zone.startsWith('door')?input.zone.slice(4,5).toLowerCase()+input.zone.slice(5):input.zone;if(own(world.doors,door))world.doors[door]=true;return id;}
function commitPurchase(state,input){
 if(!input||!text(input.purchaseId,140)||!day(input.day)||!money(input.amount)||!list(input.items)||!input.items.length||!unique(input.items.map(i=>i?.shoppingId)))throw new Error('구매 날짜와 실제 결제 금액을 확인해 주세요.');
 const previous=state.expenses.find(e=>e.receipt?.purchaseId===input.purchaseId);if(previous)return previous;
 const rows=input.items.map((entry,index)=>{const stock=state.shopping.find(i=>i.id===entry.shoppingId);if(!stock)throw new Error('이미 구매했거나 삭제한 항목이 있어요. 장보기 목록을 다시 확인해 주세요.');if(typeof entry.quantity!=='string'||entry.quantity.length>80||!(entry.amount===null||money(entry.amount)))throw new Error(stock.name+'의 구매 수량과 품목 금액을 확인해 주세요.');return {id:input.purchaseId+'-item-'+index,name:stock.name,quantity:entry.quantity.trim(),amount:entry.amount,registeredItemId:null};});
 if(state.expenses.some(e=>e.id===input.purchaseId))throw new Error('구매 기록 번호가 겹쳤어요. 장보기 목록에서 다시 확인해 주세요.');
 const expense={id:input.purchaseId,day:input.day,name:rows.length===1?rows[0].name:'장보기 '+rows.length+'개 품목',amount:input.amount,category:'groceries',receipt:{purchaseId:input.purchaseId,items:rows}};
 const ids=new Set(input.items.map(i=>i.shoppingId));state.expenses.push(expense);state.shopping=state.shopping.filter(i=>!ids.has(i.id));return expense;
}
function receiptItem(state,expenseId,purchaseItemId){return state.expenses.find(e=>e.id===expenseId)?.receipt?.items.find(i=>i.id===purchaseItemId)||null;}
function registerReceiptItem(world,state,expenseId,purchaseItemId,input){
 const entry=receiptItem(state,expenseId,purchaseItemId);if(!entry)throw new Error('저장된 구매 내역을 다시 확인해 주세요.');if(entry.registeredItemId)throw new Error('이미 냉장고에 등록한 구매 항목이에요. 재료 상세에서 확인해 주세요.');
 const id=addItem(world,input);entry.registeredItemId=id;return id;
}
return Object.freeze({blank,create,valid,day,parseQuantity,quantity,round,monthly,applyDeductions,reverseDeductions,addItem,zones,commitPurchase,receiptItem,registerReceiptItem});
});
