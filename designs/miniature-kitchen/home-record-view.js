/* Short-frame record views. Pagination and panels never write journal data. */
(() => {
'use strict';
const ui={meal:0,dayMeal:0,supplement:0,receipt:0,manage:false,monthView:'calendar',budgetView:'summary',mealDay:'',receiptMonth:'',receiptCount:null};
let mealSnapshot=new Map();
const A=()=>window.KitchenSceneArt||window.UMFKitchenArt;
const icon=name=>A()?.icon(name)||'';
const size=()=>document.querySelector('.shell')?.clientWidth>=560?4:2;
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=value=>Number(value).toLocaleString('ko-KR',{maximumFractionDigits:2});
const clampPage=(key,count)=>ui[key]=Math.max(0,Math.min(ui[key],Math.max(0,count-1)));
const tabs=(kind,entries,current)=>`<div class="record-local-tabs" role="tablist" aria-label="${kind==='month'?'월간 표시':'식비 표시'}">${entries.map(([id,label])=>`<button type="button" role="tab" data-record-${kind}-view="${id}" aria-selected="${id===current}" tabindex="${id===current?0:-1}">${label}</button>`).join('')}</div>`;
function pager(key,count,label=''){
 const page=clampPage(key,count);if(count<=1)return '';
 return `<nav class="record-pager" aria-label="${label||'기록'} 페이지"><button type="button" data-record-page="${key}|-1" aria-label="이전 ${label||'기록'}" ${page===0?'disabled':''}>‹</button><span aria-live="polite">${page+1} / ${count}</span><button type="button" data-record-page="${key}|1" aria-label="다음 ${label||'기록'}" ${page===count-1?'disabled':''}>›</button></nav>`;
}
function selectedMeal(ctx,key='meal'){
 const rows=ctx.record.rows||[];clampPage(key,rows.length);return rows[ui[key]]||null;
}
function mealCard(ctx,meal,compact=false){
 if(!meal)return `<div class="record-no-meal">${icon('bowl')}<span>기록한 식사가 없어요.</span></div>`;
 const recipe=meal.recipeId&&ctx.catalog.find(r=>r.id===meal.recipeId),transaction=ctx.flow.transactions.find(t=>t.mealId===meal.id&&t.active),slot={breakfast:'아침',lunch:'점심',dinner:'저녁'}[transaction?.slot]||meal.portion||'먹은 식사',action=recipe?'recipe':'editMeal',id=recipe?recipe.id:meal.id;
 return `<button type="button" class="record-meal-row${compact?' is-compact':''}" data-wf="${action}" data-arg="${esc(id)}"><span>${recipe?ctx.dish(recipe):icon('diary')}</span><span><small>${esc(slot)}</small><strong>${esc(meal.name)}</strong></span><b>${meal.nutrients.kcal===null?'열량 미입력':fmt(meal.nutrients.kcal)+' kcal'}</b><span aria-hidden="true">›</span></button>`;
}
function renderNutrition(ctx){
 const snapshot=new Map(ctx.record.rows.map(meal=>[meal.id,JSON.stringify(meal)]));
 if(ui.mealDay!==ctx.recordDay){ui.mealDay=ctx.recordDay;ui.meal=0;ui.dayMeal=0;ui.manage=false;}
 else{const changed=ctx.record.rows.findIndex(meal=>mealSnapshot.get(meal.id)!==snapshot.get(meal.id));if(changed>=0){ui.meal=changed;ui.dayMeal=changed;ui.manage=false;}}
 mealSnapshot=snapshot;
 const meal=selectedMeal(ctx),count=ctx.record.rows.length;
 if(ui.manage)return `<div class="record-hub record-hub-manage"><header class="record-manage-heading"><button type="button" data-record-manage="close">‹ 기록</button><h3>목표·기록 관리</h3></header><div class="record-two-actions">${ctx.routeButton('나의 목표','targets')}<button type="button" data-home-sourceinfo>성분·식사 정보</button></div><section class="record-manage-meal"><div class="record-manage-selection"><span title="${esc(meal?.name||'')}">${esc(meal?.name||'기록한 식사가 없어요.')}</span>${pager('meal',count,'식사')}</div>${meal?`<div class="record-two-actions">${ctx.action('기록 수정','editMeal',meal.id)}${ctx.action('기록 취소','cancelMeal',meal.id,'record-cancel')}</div>`:''}</section>${ctx.routeButton('직접 식사 입력','logMeal',`class="record-direct-input" data-record-day="${ctx.recordDay}"`)}</div>`;
 return `<div class="record-hub record-hub-nutrition"><div class="home-record-date"><span>${ctx.recordDay===ctx.day?'오늘의 균형':'이날의 균형'}</span><input type="date" id="homeRecordDay" value="${ctx.recordDay}" aria-label="기록 날짜"></div><section class="home-daily-card">${ctx.macroStrip(ctx.record)}</section><div class="record-meals-heading"><h4>${ctx.recordDay===ctx.day?'오늘의 식사':'이날의 식사'} <small>${count}회</small></h4><strong>${ctx.record.nutrients.kcal.value===null?'열량 미입력':'총 '+fmt(ctx.record.nutrients.kcal.value)+' kcal'}</strong></div><div class="record-meal-browser">${mealCard(ctx,meal)}${pager('meal',count,'식사')}</div><footer class="record-two-actions record-hub-footer"><button type="button" data-home-open="recommendation">＋ 식사 추가</button><button type="button" data-record-manage="open">목표·기록 관리</button></footer></div>`;
}
function renderSupplements(ctx){
 const rows=ctx.flow.supplements,perPage=size(),pages=Math.ceil(rows.length/perPage);clampPage('supplement',pages);
 const checked=rows.filter(r=>r.days.includes(ctx.recordDay)).length,visible=rows.slice(ui.supplement*perPage,(ui.supplement+1)*perPage);
 return `<div class="record-hub record-hub-supplements"><div class="record-supplement-date"><span>복용 기록 <b>${checked} / ${rows.length}</b></span><input type="date" id="homeSupplementDay" value="${ctx.recordDay}" aria-label="복용 기록 날짜"></div><div class="record-supplement-list">${visible.length?visible.map(r=>`<div class="home-supplement-row"><label class="home-supplement"><input type="checkbox" data-home-supplement="${esc(r.id)}" ${r.days.includes(ctx.recordDay)?'checked':''}><span class="supplement-product-art" aria-hidden="true"></span><span><strong>${esc(r.name)}</strong><small>${esc(r.schedule||'복용 일정 미입력')} · 직접 입력</small></span></label><button type="button" data-wf="supplement" data-arg="${esc(r.id)}" data-record-day="${ctx.recordDay}" aria-label="${esc(r.name)} 제품 정보">›</button></div>`).join(''):'<div class="record-no-meal"><span>등록한 영양제가 없어요.</span></div>'}</div><footer class="record-hub-footer record-supplement-footer${pages>1?' has-pages':''}">${pages>1?`<button type="button" data-record-page="supplement|-1" aria-label="이전 영양제" ${ui.supplement===0?'disabled':''}>‹</button>`:''}${ctx.routeButton(rows.length?'제품 관리':'영양제 등록','supplements',`data-record-day="${ctx.recordDay}"`)}${pages>1?`<button type="button" data-record-page="supplement|1" aria-label="다음 영양제" ${ui.supplement===pages-1?'disabled':''}>›</button>`:''}</footer><p class="record-hub-note">${pages>1?`${ui.supplement+1} / ${pages}쪽 · `:''}제품 표시를 확인해 기록한 내용이에요.</p></div>`;
}
function supplementDay(ctx){
 const rows=ctx.flow.supplements;
 if(!rows.length)return '<p class="record-day-supplements">등록한 영양제가 없어요.</p>';
 if(rows.length>2)return `<button type="button" class="record-day-supplements record-supplement-link" data-home-open="supplements">영양제 복용 ${rows.filter(r=>r.days.includes(ctx.recordDay)).length} / ${rows.length}　›</button>`;
 return `<div class="record-day-supplements"><span>복용</span>${rows.map(r=>`<label><input type="checkbox" data-home-supplement="${esc(r.id)}" ${r.days.includes(ctx.recordDay)?'checked':''}><span>${esc(r.name)}</span></label>`).join('')}</div>`;
}
function renderMonthly(ctx){
 const month=ctx.month||ctx.currentMonth,mode=ui.monthView,nutritionDays=new Set(month.meals.filter(m=>['carb','protein','fat'].some(k=>m.nutrients[k]!==null)).map(m=>m.day)).size;
 if(mode==='day')return `<div class="record-hub record-hub-monthly is-day">${tabs('month',[['calendar','달력'],['day','선택일 기록']],mode)}${ctx.dayDateMarkup}<div class="record-day-summary"><section class="record-day-ratio">${ctx.ratioMarkup}</section><section class="record-day-meals">${mealCard(ctx,selectedMeal(ctx,'dayMeal'),true)}${pager('dayMeal',ctx.record.rows.length,'식사')}</section></div>${supplementDay(ctx)}<footer class="record-two-actions record-hub-footer"><button type="button" data-home-open="nutrition">기록 보기</button><button type="button" data-home-open="budget">식비 관리</button></footer></div>`;
 return `<div class="record-hub record-hub-monthly is-calendar">${tabs('month',[['calendar','달력'],['day','선택일 기록']],mode)}${ctx.dateMarkup}<div class="home-month-calendar">${ctx.calendarMarkup}</div><div class="home-month-stats"><span>식사 <b>${month.meals.length}<small>회</small></b></span><span>영양 기록 <b>${nutritionDays}<small>일</small></b></span><span>실제 식비 <b>${fmt(month.spending)}<small>원</small></b></span></div></div>`;
}
function renderBudget(ctx){
 const month=ctx.currentMonth||ctx.month,receipts=month.expenses.filter(e=>e.receipt).slice().reverse();
 if(ui.receiptMonth!==ctx.monthView){ui.receiptMonth=ctx.monthView;ui.receiptCount=null;ui.receipt=0;ui.budgetView='summary';}
 if(ui.receiptCount!==null&&receipts.length>ui.receiptCount){ui.budgetView='history';ui.receipt=0;}ui.receiptCount=receipts.length;clampPage('receipt',receipts.length);
 const tab=tabs('budget',[['summary','식비 요약'],['history',`구매 내역 ${receipts.length}`]],ui.budgetView);
 if(ui.budgetView==='history'){
  const receipt=receipts[ui.receipt];
  return `<div class="record-hub record-hub-budget is-history">${tab}${ctx.dateMarkup}${receipt?`<button type="button" class="record-receipt-card" data-wf="receipt" data-arg="${esc(receipt.id)}"><span>${icon('basket')}</span><span><strong>${esc(receipt.name)}</strong><small>${esc(receipt.day)}</small></span><b>${fmt(receipt.amount)}원</b><span aria-hidden="true">›</span></button>${pager('receipt',receipts.length,'구매 내역')}`:'<div class="record-no-meal"><span>저장한 구매 내역이 없어요.</span></div>'}<footer class="record-hub-footer">${ctx.routeButton('전체 지출·구매 내역','budget',`data-record-month="${ctx.monthView}"`)}</footer></div>`;
 }
 return `<div class="record-hub record-hub-budget is-summary">${tab}${ctx.dateMarkup}<div class="budget-overview"><div><span>예산</span><strong>${month.budget===null?'미설정':fmt(month.budget)}<small>${month.budget===null?'':'원'}</small></strong></div><div><span>실제 지출</span><strong>${fmt(month.spending)}<small>원</small></strong></div><div><span>남은 금액</span><strong data-home-budget class="${ctx.remaining!==null&&ctx.remaining<0?'is-over':''}">${ctx.remaining===null?'미설정':fmt(ctx.remaining)}<small>${ctx.remaining===null?'':'원'}</small></strong></div></div><div class="home-shopping-summary"><span>장보기 예상</span><strong>${ctx.shoppingKnown.length?fmt(ctx.estimate)+'원':ctx.shopping.length?'가격 미입력':'0원'}</strong><small>지출 미반영${ctx.shoppingKnown.length<ctx.shopping.length?' · '+(ctx.shopping.length-ctx.shoppingKnown.length)+'개 가격 미입력':''}</small></div><footer class="record-two-actions record-hub-footer">${ctx.routeButton('장보기','shopping','class="home-primary"')}${ctx.routeButton('예산·지출 수정','budget',`data-record-month="${ctx.monthView}"`)}</footer></div>`;
}
function refresh(selector){window.KitchenHome?.update();if(selector){const next=document.querySelector(selector);(next&&!next.disabled?next:next?.parentElement?.querySelector('button:not(:disabled)'))?.focus({preventScroll:true});}}
document.addEventListener('click',event=>{
 const date=event.target.closest('[data-home-day]');if(date){ui.monthView='day';return;}
 const page=event.target.closest('[data-record-page]');if(page){event.preventDefault();const [key,step]=page.dataset.recordPage.split('|');if(['meal','dayMeal','supplement','receipt'].includes(key))ui[key]=Math.max(0,ui[key]+Number(step));refresh(`[data-record-page="${CSS.escape(page.dataset.recordPage)}"]`);return;}
 const manage=event.target.closest('[data-record-manage]');if(manage){event.preventDefault();ui.manage=manage.dataset.recordManage==='open';refresh();return;}
 const month=event.target.closest('[data-record-month-view]');if(month){ui.monthView=month.dataset.recordMonthView;refresh(`[data-record-month-view="${ui.monthView}"]`);return;}
 const budget=event.target.closest('[data-record-budget-view]');if(budget){ui.budgetView=budget.dataset.recordBudgetView;refresh(`[data-record-budget-view="${ui.budgetView}"]`);}
},true);
document.addEventListener('keydown',event=>{
 const tab=event.target.closest('[data-record-month-view],[data-record-budget-view]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 event.preventDefault();event.stopImmediatePropagation();const entries=[...tab.parentElement.querySelectorAll('[role=tab]')],index=entries.indexOf(tab),target=entries[event.key==='Home'?0:event.key==='End'?entries.length-1:(index+(event.key==='ArrowRight'?1:-1)+entries.length)%entries.length];
 if(target.dataset.recordMonthView){ui.monthView=target.dataset.recordMonthView;refresh(`[data-record-month-view="${ui.monthView}"]`);}else{ui.budgetView=target.dataset.recordBudgetView;refresh(`[data-record-budget-view="${ui.budgetView}"]`);}
},true);
window.KitchenRecordHub=Object.freeze({renderNutrition,renderSupplements,renderMonthly,renderBudget,getViewState:()=>({...ui})});
})();
