/* Storyboard hubs. Read existing records; navigation never seeds example values. */
(() => {
'use strict';
const K=window.MiniKitchen,J=window.KitchenJournal,F=window.KitchenWorkflowModel,G=window.KitchenJourneyModel,M=window.KitchenPlayModel,C=window.KitchenCatalog,A=window.UMFKitchenArt;
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>Number(v).toLocaleString('ko-KR',{maximumFractionDigits:2}),money=v=>v===null||v===undefined?'원가 미입력':fmt(v)+'원';
const dayString=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`,today=()=>dayString(new Date());
const routeButton=(label,route,extra='')=>`<button type="button" data-workflow="${route}" ${extra}>${label}</button>`;
const action=(label,route,arg,cls='')=>`<button type="button" class="${cls}" data-wf="${route}" data-arg="${esc(arg)}">${label}</button>`;
const dish=r=>window.KitchenStoryboardArt.dish(r),nutrient=(v,u)=>v===null||v===undefined?'미입력':fmt(v)+u;
const panelIds={fridge:'panel-fridge',meals:'todayKitchen',records:'panel-records',kitchen:'panel-kitchen'};
const pageGroups={recommendation:'meals',plans:'meals',nutrition:'records',budget:'records',supplements:'records',monthly:'records',growth:'kitchen',decor:'kitchen',connections:'kitchen'};
let ranked=[],updating=false,recordDay=today(),planDay=today(),monthView=today().slice(0,7);
function showTab(name,{focus=false,sync=true}={}){
 if(!panelIds[name])return;
 for(const [key,id]of Object.entries(panelIds))document.getElementById(id).hidden=key!==name;
 document.body.dataset.home=name;
 for(const tab of document.querySelectorAll('[data-home-tab]')){const active=tab.dataset.homeTab===name;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;}
 document.body.dataset.homePage=document.getElementById(panelIds[name]).querySelector('[data-home-page]:not([hidden])')?.dataset.homePage||'';
 if(sync)syncScene();
 if(focus)document.querySelector(`[data-home-tab="${name}"]`)?.focus({preventScroll:true});
}
function selectSubtab(name,{focus=false,sync=true}={}){
 const group=pageGroups[name];if(!group)return;showTab(group,{sync:false});const panel=document.getElementById(panelIds[group]);
 for(const page of panel.querySelectorAll('[data-home-page]'))page.hidden=page.dataset.homePage!==name;
 for(const tab of panel.querySelectorAll('.panel-tabs [data-home-subtab]')){const active=tab.dataset.homeSubtab===name;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;}
 panel.scrollTop=0;document.body.dataset.homePage=name;if(sync)syncScene();
 if(focus){const target=panel.querySelector(`[data-home-subtab="${name}"]`);(target?.getClientRects().length?target:panel.querySelector(".hub-heading button"))?.focus({preventScroll:true});}
}
function syncScene(){if(document.body.dataset.home==='fridge')K.setCamera('fridge');else if(document.body.dataset.home==='kitchen'&&!$('#homeDecor').hidden)K.setCamera('counter');}
function showScene(camera){
 if(camera==='counter')selectSubtab('decor',{sync:false});else{if(!$('#homeDecor').hidden)selectSubtab('growth',{sync:false});showTab('fridge',{sync:false});}
 const host=camera==='counter'?$('#decorStage'):$('#fridgeSceneHost'),view=$('.kitchen-view');if(view.parentElement!==host)host.appendChild(view);
}
function recommendation(){return ranked[0]||null;}
function recommendationView(candidate,compact=false){
 if(!candidate)return '<p class="home-empty">조건에 맞는 레시피가 없어요. 재고와 피할 재료를 확인해 주세요.</p>'+routeButton('레시피 조건 보기','recipes');
 const {recipe:r,availability:a,nutrients:n,cost,reasons}=candidate,missing=a.rows.filter(row=>row.status==='shortage'),unknown=a.rows.filter(row=>row.status==='unknown'||row.unknownExpiryIds?.length);
 const stock=a.ready?'보유 수량으로 준비 가능':missing.length?'부족 재료 '+missing.length+'종':'수량 확인 필요';
 return `<button type="button" class="home-recipe-photo" data-wf="recipe" data-arg="${esc(r.id)}" aria-label="${esc(r.name)} 레시피 보기"><span class="home-dish">${dish(r)}</span></button>
 <div class="home-recipe-copy"><div class="home-recipe-top"><h3>${esc(r.name)}</h3><span class="home-status" data-stock-status="${esc(a.status)}">${stock}</span></div><div class="home-recipe-facts"><span>${esc(r.time)}</span><span data-home-cost>${money(cost)}</span><span data-home-kcal>${n.kcal===null?'열량 미입력':fmt(n.kcal)+' kcal'}</span></div>
 ${compact?'':`<div class="home-recipe-macros" aria-label="레시피 1회분 영양"><span>탄수화물 <b>${nutrient(n.carb,'g')}</b></span><span>단백질 <b>${nutrient(n.protein,'g')}</b></span><span>지방 <b>${nutrient(n.fat,'g')}</b></span></div>`}
 ${!compact&&(missing.length||unknown.length)?`<p class="home-recipe-condition">${missing.length?`<span class="home-shortage">부족 · ${missing.slice(0,2).map(row=>esc(row.name)).join(' · ')}${missing.length>2?' 외 '+(missing.length-2)+'종':''}</span>`:''}${unknown.length?`<span class="home-unknown">수량·단위 확인 ${unknown.length}종</span>`:''}</p>`:''}</div>
 ${compact?`<div class="home-actions">${action('레시피 보기','recipe',r.id,'home-primary')}</div>`:`<div class="home-actions home-recipe-actions">${action('이 요리로 식단에 추가','planRecipe',r.id,'home-primary')}${action('자세히','recipe',r.id)}</div><details class="home-reasons"><summary>추천 기준·입력 정보</summary><p class="home-reason">${reasons.map(esc).join(' · ')||'재고와 입력한 영양·원가를 살펴보고 골라요.'}</p>${unknown.length?`<p class="home-unknown">수량·단위 확인 · ${unknown.map(row=>esc(row.name)).join(' · ')}</p>`:''}${action('영양·원가 입력','recipeFacts',r.id)}</details>`}`;
}
function committedProps(props){return props.map(i=>`<span class="home-prop-mini" data-home-prop="${esc(i.id)}" data-home-art="${esc(i.art)}" style="--prop-x:${Number(i.x)*100}%;left:var(--prop-x);top:${Math.max(0,Math.min(100,i.y*100))}%;z-index:${Number(i.z)||0}" aria-hidden="true">${K.getArt(i)}</span>`).join('');}
function macroStrip(report){return `<div class="record-macros">${['carb','protein','fat'].map(k=>{const n=report.nutrients[k];return `<div data-record-balance="${k}"><span>${M.NUTRIENTS[k][0]}</span><strong>${n.value===null?'—':fmt(n.value)}<small>g</small></strong><small>${n.target===null?'목표 미설정':'/ '+fmt(n.target)+'g'}</small><div class="record-track"><i style="width:${n.percent===null?0:Math.min(100,n.percent)}%"></i></div>${n.missing?`<small>${n.missing}끼 미입력</small>`:''}</div>`;}).join('')}</div>`;}
function monthlyCalendar(flow,play){
 const [year,month]=monthView.split('-').map(Number),offset=new Date(year,month-1,1).getDay(),days=new Date(year,month,0).getDate();
 const marked=new Set([...play.meals.map(m=>m.day),...flow.expenses.map(e=>e.day)]);
 return `<div class="calendar-weekdays" aria-hidden="true">${['일','월','화','수','목','금','토'].map(d=>`<span>${d}</span>`).join('')}</div><div class="home-calendar" aria-label="${year}년 ${month}월 기록 날짜">${'<span></span>'.repeat(offset)}${Array.from({length:days},(_,i)=>{const day=monthView+'-'+String(i+1).padStart(2,'0');return `<button type="button" data-home-day="${day}" ${day===recordDay?'aria-current="date"':''} aria-label="${month}월 ${i+1}일${marked.has(day)?' 기록 있음':''}">${i+1}${marked.has(day)?'<i aria-hidden="true"></i>':''}</button>`;}).join('')}</div>`;
}
function update(){
 if(updating||!G||!$('#todayKitchen'))return;updating=true;
 try{
  const day=today(),world=K.exportWorld(),flow=J.getWorkflow(),play=J.getSnapshot(),daily=J.summary(day),record=J.summary(recordDay),month=F.monthly(flow,play,monthView);
  ranked=G.recommend(C,world,flow,play,{day});const selected=recommendation();
  const props=world.items.filter(i=>i.kind==='decor'&&!i.depleted),propMarkup=committedProps(props);
  if($('#homeProps'))$('#homeProps').innerHTML=propMarkup;
  if($('#homeSceneDecor'))$('#homeSceneDecor').innerHTML=propMarkup;
  $('#todayStamp').textContent=new Date().toLocaleDateString('ko-KR',{month:'long',day:'numeric',weekday:'short'});
  const notice=$('#homeStorageNotice');notice.hidden=J.status==='saved';notice.setAttribute('aria-label',J.status==='temporary'?'임시 세션입니다. 닫기 전에 백업해 주세요.':'새 저장이 중단됐어요. 기존 기록과 백업을 확인해 주세요.');notice.innerHTML='<span>'+(J.status==='temporary'?'임시 세션':'저장 중단')+'</span>'+action('백업','backupTools','');
  const soon=new Date();soon.setDate(soon.getDate()+3);const near=world.items.filter(i=>['food','seasoning'].includes(i.kind)&&!i.depleted&&i.expiry&&i.expiry>=day&&i.expiry<=dayString(soon)).sort((a,b)=>a.expiry.localeCompare(b.expiry));
  $('#homeRecommendation').innerHTML=`<div class="home-recipe-toolbar"><span class="home-priority">${near.length?`<span class="home-priority-art" aria-hidden="true">${K.getArt(near[0])}</span><span>먼저 먹을 재료 <strong>${near.slice(0,2).map(i=>esc(i.name)).join(' · ')}</strong></span>`:'<span>냉장고에 있는 재료로 한 끼</span>'}</span>${routeButton('전체 레시피','recipes')}</div><div class="home-featured-recipe" data-home-recipe="${esc(selected?.recipe.id||'')}">${recommendationView(selected)}</div><div class="home-recipe-grid">${ranked.slice(1,3).map(({recipe:r,nutrients:n,cost})=>`<button type="button" class="home-small-recipe" data-wf="recipe" data-arg="${esc(r.id)}"><span class="home-small-dish">${dish(r)}</span><span class="home-small-recipe-copy"><strong>${esc(r.name)}</strong><small>${esc(r.time)} · ${money(cost)}</small><small>${n.kcal===null?'열량 미입력':fmt(n.kcal)+' kcal'}</small></span></button>`).join('')}</div>`;
  const plans=flow.plans.filter(p=>p.day===planDay),slots={breakfast:'아침',lunch:'점심',dinner:'저녁'};
  $('#homePlans').innerHTML=`<div class="home-block-heading"><div><p>미리 골라 두는 한 끼</p><h3>내 식단</h3></div>${routeButton('계획 추가·수정','plan')}</div><label class="home-date-picker">식단 날짜<input type="date" id="homePlanDay" value="${planDay}"></label>${plans.length?plans.map(p=>{const r=C.find(r=>r.id===p.recipeId),done=flow.transactions.some(t=>t.planId===p.id&&t.active&&play.meals.some(m=>m.id===t.mealId));return `<div class="home-plan-row"><div class="home-plan-art">${dish(r)}</div><div><small>${slots[p.slot]||'식사'} · ${done?'기록 완료':'계획됨'}</small><strong>${esc(r.name)}</strong><span>기준 ${fmt(p.portions)}회분</span></div>${done?routeButton('기록 보기','nutrition'):action('먹었어요','logPlan',p.id,'home-primary')}</div>`;}).join(''):`<div class="home-empty-state"><span data-icon="diary">${A.icon('diary')}</span><p>아직 계획한 식사가 없어요.<br>레시피에서 한 끼를 골라 보세요.</p><button type="button" data-home-open="recommendation">레시피 찾기</button></div>`}<p class="home-note">계획만 저장하면 재고는 그대로예요. 먹은 식사로 확정할 때 반영해요.</p><div class="home-actions">${action('계획한 부족 재료 장보기','planShopping',planDay)}${routeButton('식사 직접 기록','nutrition')}</div>`;
  $('#homeNutrition').innerHTML=`<div class="home-block-heading"><div><p>직접 기록한 식사 기준</p><h3>먹은 식사와 영양</h3></div>${routeButton('모든 기록','hub')}</div><label class="home-date-picker">기록 날짜<input type="date" id="homeRecordDay" value="${recordDay}"></label>${macroStrip(record)}<div class="record-meals-heading"><h4>이날의 식사</h4><strong>${record.nutrients.kcal.value===null?'열량 미입력':'총 '+fmt(record.nutrients.kcal.value)+' kcal'}</strong></div>${record.rows.length?record.rows.map(m=>`<button type="button" class="record-meal-row" data-wf="editMeal" data-arg="${esc(m.id)}"><span>${dish({name:m.name})}</span><span><strong>${esc(m.name)}</strong><small>${esc(m.portion||'분량 메모 없음')}</small></span><b>${m.nutrients.kcal===null?'미입력':fmt(m.nutrients.kcal)+' kcal'}</b><span aria-hidden="true">›</span></button>`).join(''):'<p class="home-empty">아직 식사 기록이 없어요. 먹은 한 끼부터 남겨 보세요.</p>'}${record.nutrients.kcal.missing?`<p class="home-note">${record.nutrients.kcal.missing}끼는 열량 미입력 · 합계는 입력한 값만 반영했어요.</p>`:''}<div class="home-actions">${routeButton('식사 추가','nutrition','class="home-primary"')}${routeButton('나의 목표','targets')}</div><p class="home-note">미입력 영양은 0으로 가정하지 않아요. 목표는 직접 정한 값이에요.</p>`;
  const currentMonth=F.monthly(flow,play,day.slice(0,7)),remaining=currentMonth.budget===null?null:currentMonth.budget-currentMonth.spending;
  $('#homeBudget').innerHTML=`<div class="home-block-heading"><div><p>${Number(day.slice(5,7))}월 · 실제 구매 지출</p><h3>이번 달 식비</h3></div>${routeButton('예산·지출 수정','budget')}</div><div class="budget-overview"><div><span>예산</span><strong>${currentMonth.budget===null?'미설정':fmt(currentMonth.budget)}<small>${currentMonth.budget===null?'':'원'}</small></strong></div><div><span>실제 지출</span><strong>${fmt(currentMonth.spending)}<small>원</small></strong></div><div><span>남은 금액</span><strong data-home-budget class="${remaining!==null&&remaining<0?'is-over':''}">${remaining===null?'예산 미설정':fmt(remaining)+'<small>원</small>'}</strong></div></div><div class="home-shopping-summary">장보기 ${flow.shopping.filter(s=>!s.checked).length}개 <small>예상 금액은 지출에 반영하지 않아요.</small></div><div class="home-actions">${routeButton('장보기','shopping','class="home-primary"')}${routeButton('구매·지출 기록','budget')}</div><p class="home-note">레시피의 예상 원가를 실제 구매 지출에 다시 더하지 않아요.</p>`;
  const checked=flow.supplements.filter(s=>s.days.includes(day)).length;
  $('#homeSupplements').innerHTML=`<div class="home-block-heading"><div><p>오늘 복용 기록 ${checked}/${flow.supplements.length}</p><h3>영양제</h3></div>${routeButton('제품 관리','supplements')}</div>${flow.supplements.length?flow.supplements.map(s=>`<div class="home-supplement-row"><label class="home-supplement"><input type="checkbox" data-home-supplement="${esc(s.id)}" ${s.days.includes(day)?'checked':''}><span><strong>${esc(s.name)}</strong><small>${esc(s.schedule||'내 복용 일정 미입력')}</small></span></label>${action('성분·일정','editSupplement',s.id)}</div>`).join(''):'<div class="home-empty-state"><p>먹고 있는 제품과<br>내 복용 일정을 남겨 보세요.</p>'+routeButton('영양제 등록','supplements')+'</div>'}<p class="home-note">제품 표시를 확인해 기록해요. 복용 체크를 식사 영양값에 합산하지 않아요.</p>`;
  $('#homeMonthly').innerHTML=`<div class="home-block-heading"><div><p>식사·영양·식비를 모아 보는</p><h3>한 달의 기록</h3></div><label class="home-month-picker"><span class="sr-only">기록 월</span><input type="month" id="homeMonth" value="${monthView}"></label></div>${monthlyCalendar(flow,play)}<div class="home-month-stats"><span>식사<b>${month.meals.length}<small>끼</small></b></span><span>기록일<b>${month.days}<small>일</small></b></span><span>식비<b>${fmt(month.spending)}<small>원</small></b></span></div><div class="month-ratio"><h4>입력된 식사의 탄단지 비율</h4>${month.ratio?`<div class="month-ratio-track">${['carb','protein','fat'].map(k=>`<i class="ratio-${k}" style="width:${month.ratio[k]}%"></i>`).join('')}</div><p>${['carb','protein','fat'].map(k=>M.NUTRIENTS[k][0]+' '+fmt(month.ratio[k])+'%').join(' · ')}</p><small>탄단지를 모두 입력한 ${month.complete}끼의 에너지 비율</small>`:'<p class="home-empty">탄단지를 함께 기록하면 비율을 볼 수 있어요.</p>'}</div><div class="home-actions">${routeButton('월간 상세','monthly')}${routeButton('식비 관리','budget')}</div>`;
  const owned=play.owned.map(id=>M.REWARDS[id].name),goal=daily.goal;
  $('#homeGrowth').innerHTML=`<section class="growth-goal-card"><div class="home-block-heading"><div><h3>나의 목표</h3></div>${routeButton('꾸밈권 '+daily.tickets,'rewards')}</div><div class="home-goal-choices">${[['collection','요리 도감'],['recording','기록 습관'],['nutrition','영양 기록']].map(([id,label])=>`<button type="button" data-home-goal="${id}" aria-pressed="${play.goal===id}">${label}</button>`).join('')}</div><div class="home-goal-heading"><strong>${esc(goal.label)}</strong><span>${goal.value} / ${goal.target}</span></div><div class="home-goal-track" role="progressbar" aria-label="${esc(goal.label)}" aria-valuemin="0" aria-valuemax="${goal.target}" aria-valuenow="${goal.value}"><i style="width:${Math.min(100,100*goal.value/goal.target)}%"></i></div><div class="home-goal-summary"><span>요리 도감 <b>${daily.cooked.length}/${C.length}</b></span><span>꾸밈권 <b>${daily.tickets}개</b></span></div><div class="home-actions growth-goal-actions">${routeButton('요리 도감 '+daily.cooked.length+'/'+C.length,'book')}<button type="button" class="home-primary" data-home-open="decor">부엌 꾸미기</button></div></section><button type="button" class="growth-preview home-kitchen-scene" data-home-open="decor" aria-label="내 부엌 꾸미기 열기">${K.getFridgeArt?.()||''}<span id="growthSceneDecor" class="committed-scene-props" aria-hidden="true">${propMarkup}</span><span class="growth-preview-callout">나의 부엌 꾸미기 ›</span></button><p class="home-note growth-owned-note">${owned.length?'보유 소품 · '+owned.map(esc).join(' · '):'새 요리를 처음 식사로 기록하면 꾸밈권을 받아요.'}</p>`;
  $('#homeConnections').innerHTML=`<div class="home-block-heading"><div><p>나의 설정과 기록 보관</p><h3>설정·백업</h3></div></div><p class="home-save-state">${J.status==='saved'?'이 브라우저에 기록을 저장하고 있어요.':J.status==='temporary'?'현재 임시 세션이에요. 닫기 전에 백업해 주세요.':'기존 기록을 확인해 주세요. 새 저장이 중단됐어요.'}</p><div class="home-actions">${action('백업·복구','backupTools','','home-primary')}${routeButton('하루 영양 목표','targets')}${routeButton('설정 열기','settings')}<button type="button" id="expandDisplays">표시창 확대</button><button type="button" id="help">조작 방법</button></div><details class="home-data-status"><summary>지원 기능과 정보 기준</summary><p>제품·기한 사진은 이 기기에서 글자를 읽고 직접 검수해요. 냉장고 전체 사진의 식재료 자동 판별과 새 미니어처 생성은 연결 전이에요.</p><p>영양·원가는 입력한 값으로 계산해요. 공식 식품 성분·가격·개인 권장량과 기기 간 동기화는 연결 전이에요. 기존 운영 앱 기록과 별도로 보관해요.</p></details>`;
  const sidebar=$('#desktopSummary');if(sidebar)sidebar.innerHTML=`<p class="home-label">오늘 먼저 먹을 재료로</p>${recommendationView(selected,true)}<div class="home-sidebar-links"><button type="button" data-home-open="recommendation">레시피</button><button type="button" data-home-open="budget">식비</button><button type="button" data-home-open="growth">내 부엌</button></div>`;
  K.refreshDisplays();
 }finally{updating=false;}
}
document.addEventListener('click',event=>{
 const tab=event.target.closest('[data-home-tab]');if(tab){showTab(tab.dataset.homeTab);return;}
 const sub=event.target.closest('[data-home-subtab],[data-home-open]');if(sub){selectSubtab(sub.dataset.homeSubtab||sub.dataset.homeOpen);return;}
 const date=event.target.closest('[data-home-day]');if(date){recordDay=date.dataset.homeDay;update();selectSubtab('nutrition');return;}
 const goal=event.target.closest('[data-home-goal]');if(goal)try{J.transact(({play})=>play.setGoal(goal.dataset.homeGoal));$(`[data-home-goal="${goal.dataset.homeGoal}"]`)?.focus();}catch(e){K.announce(e.message);}
});
document.addEventListener('keydown',event=>{
 const tab=event.target.closest('[role="tab"]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 const tabs=[...tab.parentElement.querySelectorAll('[role="tab"]')],index=tabs.indexOf(tab),next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
 event.preventDefault();const target=tabs[next];if(target.dataset.homeTab)showTab(target.dataset.homeTab,{focus:true});else selectSubtab(target.dataset.homeSubtab,{focus:true});
});
document.addEventListener('change',event=>{
 const input=event.target;
 if(input.id==='homePlanDay'&&F.day(input.value)){planDay=input.value;update();$('#homePlanDay')?.focus({preventScroll:true});return;}
 if(input.id==='homeRecordDay'&&F.day(input.value)){recordDay=input.value;update();$('#homeRecordDay')?.focus({preventScroll:true});return;}
 if(input.id==='homeMonth'&&/^\d{4}-\d{2}$/.test(input.value)){monthView=input.value;update();$('#homeMonth')?.focus({preventScroll:true});return;}
 if(!input.matches('[data-home-supplement]'))return;
 const id=input.dataset.homeSupplement,checked=input.checked,day=today();
 try{J.transact(({flow})=>{const item=flow.supplements.find(s=>s.id===id);if(!item)throw new Error('영양제 기록을 확인해 주세요.');item.days=item.days.filter(d=>d!==day);if(checked)item.days.push(day);});$(`[data-home-supplement="${CSS.escape(id)}"]`)?.focus();}catch(e){K.announce(e.message);update();}
});
window.KitchenHome=Object.freeze({update,recommendation,showTab,selectSubtab,showScene});update();
})();
