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
function mealPicture(ctx,meal){
 const photo=[meal?.photo,meal?.attachment].find(value=>typeof value==='string'&&value.length<250000&&/^data:image\/(?:jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(value));
 if(photo)return `<img class="journal-meal-photo" src="${esc(photo)}" alt="${esc(meal.name)} 기록 사진">`;
 const recipe=meal?.recipeId&&ctx.catalog.find(row=>row.id===meal.recipeId);
 return recipe?ctx.dish(recipe):`<span class="journal-handwritten-meal" aria-label="직접 입력한 식사">${icon('diary')}</span>`;
}
function calendarMarkup(ctx){
 const [year,month]=ctx.monthView.split('-').map(Number),offset=new Date(year,month-1,1).getDay(),days=new Date(year,month,0).getDate(),weeks=Math.max(5,Math.ceil((offset+days)/7)),byDay=new Map();
 for(const meal of (ctx.month||ctx.currentMonth).meals){const list=byDay.get(meal.day)||[];list.push(meal);byDay.set(meal.day,list);}
 const cells=Array.from({length:42},(_,index)=>{
  const date=index-offset+1;if(date<1||date>days)return '<span class="journal-calendar-blank" aria-hidden="true"></span>';
  const day=ctx.monthView+'-'+String(date).padStart(2,'0'),meals=byDay.get(day)||[],checked=ctx.flow.supplements.some(row=>row.days.includes(day)),current=day===ctx.recordDay;
  return `<button type="button" class="journal-calendar-day${meals.length?' has-meal':''}${day===ctx.day?' is-today':''}" data-home-day="${day}" ${current?'aria-current="date"':''} aria-label="${month}월 ${date}일 · ${meals.length?meals.map(meal=>meal.name).join(', '):'식사 기록 없음'}${checked?' · 영양제 복용 기록 있음':''}"><span class="journal-date-number">${date}</span>${meals.length?`<span class="journal-food-stamp" aria-hidden="true">${mealPicture(ctx,meals[0])}</span>${meals.length>1?`<small class="journal-more-meals">+${meals.length-1}</small>`:''}`:''}${checked?'<span class="journal-supplement-dot" aria-hidden="true"></span>':''}</button>`;
 }).join('');
 return `<div class="journal-calendar-weekdays" aria-hidden="true">${['일','월','화','수','목','금','토'].map(name=>`<span>${name}</span>`).join('')}</div><div class="journal-calendar-grid" data-week-count="${weeks}" style="--journal-week-count:${weeks}" aria-label="${year}년 ${month}월 음식 그림일기">${cells}</div>`;
}
function journalBudget(ctx){
 const month=ctx.month||ctx.currentMonth,remaining=month.budget===null?null:month.budget-month.spending;
 return `<div class="journal-budget-strip"><button type="button" class="journal-budget-link" data-home-open="budget" aria-label="${ctx.monthView} 식비 관리 · 실제 지출 ${fmt(month.spending)}원${remaining===null?' · 예산 미설정':' · 남은 예산 '+fmt(remaining)+'원'}"><span>${icon('basket')}<span><small>${ctx.monthView===ctx.day.slice(0,7)?'이번 달 실제 식비':Number(ctx.monthView.slice(5))+'월 실제 식비'}</small><strong>${fmt(month.spending)}<span>원</span></strong></span></span><span class="journal-budget-remaining"><small>${month.budget===null?'예산 미설정':'예산 '+fmt(month.budget)+'원'}</small>${remaining===null?'':`<b class="${remaining<0?'is-over':''}">${remaining<0?'초과 ':'남음 '}${fmt(Math.abs(remaining))}원</b>`}</span><span class="journal-budget-chevron" aria-hidden="true">›</span></button>${ctx.routeButton('장보기','shopping','class="journal-shopping-action"')}</div>`;
}
function selectedEntryPreview(ctx){
 const meal=selectedMeal(ctx,'dayMeal'),count=ctx.record.rows.length,date=Number(ctx.recordDay.slice(5,7))+'월 '+Number(ctx.recordDay.slice(8))+'일',label=ctx.recordDay===ctx.day?'오늘의 식사':'이날의 식사';
 return `<button type="button" class="journal-selected-entry" data-record-month-view="day" aria-label="${esc(date+' '+(meal?meal.name:'식사 기록 없음')+' 그림일기 자세히')}"><span class="journal-selected-picture" aria-hidden="true">${meal?mealPicture(ctx,meal):icon('diary')}</span><span class="journal-selected-copy"><small>${esc(date+' · '+label)}${count>1?' · '+fmt(count)+'회':''}</small><strong>${esc(meal?.name||'기록한 식사가 없어요')}</strong></span><span class="journal-selected-chevron" aria-hidden="true">›</span></button>`;
}
function journalEntry(ctx){
 const meal=selectedMeal(ctx,'dayMeal'),count=ctx.record.rows.length,recipe=meal?.recipeId&&ctx.catalog.find(row=>row.id===meal.recipeId),transaction=meal&&ctx.flow.transactions.find(row=>row.mealId===meal.id&&row.active),slot={breakfast:'아침',lunch:'점심',dinner:'저녁'}[transaction?.slot]||'식사 기록';
 const picture=mealPicture(ctx,meal),pictureMarkup=recipe?`<button type="button" class="journal-entry-picture" data-wf="recipe" data-arg="${esc(recipe.id)}" aria-label="${esc(meal.name)} 레시피 자세히">${picture}</button>`:`<span class="journal-entry-picture">${picture}</span>`;
 const content=meal?`${pictureMarkup}<div class="journal-entry-copy"><p>${esc(slot)}${count>1?' · '+(ui.dayMeal+1)+' / '+count:''}</p><h3>${esc(meal.name)}</h3>${meal.portion?`<span class="journal-entry-portion">${esc(meal.portion)}</span>`:''}<strong class="journal-entry-kcal">${meal.nutrients.kcal===null?'열량 미입력':fmt(meal.nutrients.kcal)+' kcal'}</strong><div class="journal-entry-macros">${['carb','protein','fat'].map((key,index)=>`<span>${['탄','단','지'][index]} ${meal.nutrients[key]===null?'—':fmt(meal.nutrients[key])+'g'}</span>`).join('')}</div></div>`:`<div class="journal-entry-empty">${icon('diary')}<strong>아직 비어 있는 하루예요</strong><span>먹은 식사를 기록하면 이곳에 그림이 남아요.</span></div>`;
 return `<div class="record-hub record-hub-monthly journal-diary is-day"><header class="journal-day-heading"><button type="button" data-record-month-view="calendar" aria-label="음식 그림일기 달력으로 돌아가기">${icon('diary')}</button>${ctx.dayDateMarkup}</header><div class="journal-entry-content">${content}</div>${supplementDay(ctx)}<footer class="journal-day-actions${count>1?' has-pages':''}">${count>1?`<button type="button" data-record-page="dayMeal|-1" aria-label="이전 식사" ${ui.dayMeal===0?'disabled':''}>‹</button>`:''}<button type="button" data-home-open="recommendation">＋ 식사 추가</button><button type="button" data-home-open="budget">식비 관리</button>${count>1?`<button type="button" data-record-page="dayMeal|1" aria-label="다음 식사" ${ui.dayMeal===count-1?'disabled':''}>›</button>`:''}</footer></div>`;
}
function renderMonthly(ctx){
 if(ui.monthView==='day')return journalEntry(ctx);
 return `<div class="record-hub record-hub-monthly journal-diary is-calendar">${ctx.dateMarkup}<div class="journal-calendar" aria-label="먹은 식사 그림일기">${calendarMarkup(ctx)}</div>${selectedEntryPreview(ctx)}${journalBudget(ctx)}</div>`;
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
 const date=event.target.closest('[data-home-day]');if(date){ui.monthView='day';requestAnimationFrame(()=>document.querySelector('#homeMonthly .journal-day-heading>button')?.focus({preventScroll:true}));return;}
 const page=event.target.closest('[data-record-page]');if(page){event.preventDefault();const [key,step]=page.dataset.recordPage.split('|');if(['meal','dayMeal','supplement','receipt'].includes(key))ui[key]=Math.max(0,ui[key]+Number(step));refresh(`[data-record-page="${CSS.escape(page.dataset.recordPage)}"]`);return;}
 const manage=event.target.closest('[data-record-manage]');if(manage){event.preventDefault();ui.manage=manage.dataset.recordManage==='open';refresh();return;}
 const month=event.target.closest('[data-record-month-view]');if(month){ui.monthView=month.dataset.recordMonthView;refresh(ui.monthView==='day'?'#homeMonthly .journal-day-heading>button':'#homeMonthly .journal-calendar-day[aria-current="date"]');return;}
 const budget=event.target.closest('[data-record-budget-view]');if(budget){ui.budgetView=budget.dataset.recordBudgetView;refresh(`[data-record-budget-view="${ui.budgetView}"]`);}
},true);
document.addEventListener('keydown',event=>{
 const calendarDay=event.target.closest('.journal-calendar-day[data-home-day]');
 if(calendarDay&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)){
  event.preventDefault();event.stopImmediatePropagation();const entries=[...calendarDay.parentElement.querySelectorAll('[data-home-day]')],index=entries.indexOf(calendarDay),column=new Date(calendarDay.dataset.homeDay+'T12:00:00').getDay(),step={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7,Home:-column,End:6-column}[event.key];
  entries[Math.max(0,Math.min(entries.length-1,index+step))]?.focus({preventScroll:true});return;
 }
 const tab=event.target.closest('[role="tab"][data-record-month-view],[role="tab"][data-record-budget-view]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 event.preventDefault();event.stopImmediatePropagation();const entries=[...tab.parentElement.querySelectorAll('[role=tab]')],index=entries.indexOf(tab),target=entries[event.key==='Home'?0:event.key==='End'?entries.length-1:(index+(event.key==='ArrowRight'?1:-1)+entries.length)%entries.length];
 if(target.dataset.recordMonthView){ui.monthView=target.dataset.recordMonthView;refresh(`[data-record-month-view="${ui.monthView}"]`);}else{ui.budgetView=target.dataset.recordBudgetView;refresh(`[data-record-budget-view="${ui.budgetView}"]`);}
},true);
window.KitchenRecordHub=Object.freeze({renderNutrition,renderSupplements,renderMonthly,renderBudget,showCalendar(){ui.monthView='calendar';ui.dayMeal=0;},getViewState:()=>({...ui})});
})();
