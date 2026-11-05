/* Storyboard hubs. Read existing records; navigation never seeds example values. */
(() => {
'use strict';
const K=window.MiniKitchen,J=window.KitchenJournal,F=window.KitchenWorkflowModel,G=window.KitchenJourneyModel,M=window.KitchenPlayModel,C=window.KitchenCatalog,A=window.KitchenSceneArt||window.UMFKitchenArt;
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>Number(v).toLocaleString('ko-KR',{maximumFractionDigits:2}),money=v=>v===null||v===undefined?'원가 미입력':fmt(v)+'원';
const dayString=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`,today=()=>dayString(new Date());
const routeButton=(label,route,extra='')=>`<button type="button" data-workflow="${route}" ${extra}>${label}</button>`;
const action=(label,route,arg,cls='')=>`<button type="button" class="${cls}" data-wf="${route}" data-arg="${esc(arg)}">${label}</button>`;
const dish=(r,fit)=>window.KitchenStoryboardArt.dish(r,fit),nutrient=(v,u)=>v===null||v===undefined?'미입력':fmt(v)+u;
const panelIds={fridge:'panel-fridge',meals:'todayKitchen',records:'panel-records',kitchen:'panel-kitchen'};
const pageGroups={recommendation:'meals',plans:'meals',nutrition:'records',budget:'records',supplements:'records',monthly:'records',growth:'kitchen',decor:'kitchen',connections:'kitchen'};
let ranked=[],updating=false,recordDay=today(),planDay=today(),monthView=today().slice(0,7),recipeFilters={time:'',budget:'',exclude:'',ingredient:''},calendarExpanded=false;
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
function showPlans(day=planDay){if(F.day(day))planDay=day;update();selectSubtab('plans');return planDay;}
function showRecipes(options={}){if(options.reset)recipeFilters={time:'',budget:'',exclude:'',ingredient:''};else for(const key of ['time','budget','exclude','ingredient'])if(Object.hasOwn(options,key))recipeFilters[key]=String(options[key]||'');update();selectSubtab('recommendation');}
function getRecipeFilters(){return {...recipeFilters};}
function recommendation(){return ranked[0]||null;}
function recommendationView(candidate,compact=false){
 if(!candidate)return '<div class="recipe-no-results"><p>조건에 맞는 레시피가 없어요.</p><button type="button" data-home-filter-reset>조건 초기화</button></div>';
 const {recipe:r,availability:a,nutrients:n,cost}=candidate;
 return `<button type="button" class="home-recipe-photo" data-wf="recipe" data-arg="${esc(r.id)}" aria-label="${esc(r.name)} 레시피 보기"><span class="home-dish">${dish(r)}</span></button><button type="button" class="home-recipe-favorite" data-wf="favoriteRecipe" data-arg="${esc(r.id)}" aria-label="${J.getWorkflow().recipeNotes[r.id]?.favorite?'찜 해제':'요리 찜하기'}" aria-pressed="${!!J.getWorkflow().recipeNotes[r.id]?.favorite}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20S3 14.2 3 8.3A4.6 4.6 0 0 1 12 7a4.6 4.6 0 0 1 9 1.3C21 14.2 12 20 12 20Z"/></svg></button><div class="home-recipe-copy"><h3>${esc(r.name)}</h3><div class="home-recipe-facts"><span>${A.icon('clock')} ${esc(r.time)}</span><span>${A.icon('basket')} ${money(cost)}</span></div><div class="home-recipe-bottom"><div class="home-recipe-macros"><b data-home-kcal>${n.kcal===null?'열량 미입력':fmt(n.kcal)+' kcal'}</b>${['carb','protein','fat'].map((k,i)=>`<span>${['탄','단','지'][i]} ${nutrient(n[k],'g')}</span>`).join('')}</div><button type="button" class="home-recipe-arrow" data-wf="recipe" data-arg="${esc(r.id)}" aria-label="${esc(r.name)} 자세히">›</button></div><span class="sr-only" data-stock-status="${esc(a.status)}">${a.ready?'보유 수량으로 준비 가능':'부족한 재료와 수량을 확인해 주세요.'}</span></div>`;
}
function dateBar(id,value,type='date'){
 const parsed=new Date(value+(type==='month'?'-01':'')+'T12:00:00'),display=type==='month'?parsed.toLocaleDateString('ko-KR',{year:'numeric',month:'long'}):parsed.toLocaleDateString('ko-KR',{month:'long',day:'numeric',weekday:'short'});
 return `<div class="home-date-bar"><button type="button" data-home-date-shift="${id}" data-step="-1" aria-label="이전 ${type==='month'?'달':'날짜'}">‹</button><label class="home-date-value"><strong>${display}</strong><input type="${type}" id="${id}" value="${value}" aria-label="${type==='month'?'기록 월':'기록 날짜'}"></label><button type="button" data-home-date-shift="${id}" data-step="1" aria-label="다음 ${type==='month'?'달':'날짜'}">›</button></div>`;
}
function ratioView(report){
 const complete=report.rows.filter(m=>['carb','protein','fat'].every(k=>m.nutrients[k]!==null)),energy={carb:0,protein:0,fat:0};
 for(const m of complete){energy.carb+=m.nutrients.carb*4;energy.protein+=m.nutrients.protein*4;energy.fat+=m.nutrients.fat*9;}
 const sum=Object.values(energy).reduce((a,b)=>a+b,0),r=sum?Object.fromEntries(Object.entries(energy).map(([k,v])=>[k,v/sum*100])):null;
 return r?`<div class="home-ratio-donut" role="img" aria-label="탄수화물 ${fmt(r.carb)}%, 단백질 ${fmt(r.protein)}%, 지방 ${fmt(r.fat)}%" style="--carb-end:${r.carb}%;--protein-end:${r.carb+r.protein}%"><span><b>${report.nutrients.kcal.value===null?'—':fmt(report.nutrients.kcal.value)}</b><small>kcal</small></span></div><div class="home-ratio-legend">${['carb','protein','fat'].map(k=>`<span class="ratio-key-${k}">${M.NUTRIENTS[k][0]} <b>${fmt(r[k])}%</b></span>`).join('')}</div>`:'<div class="home-ratio-donut is-empty"><span><b>—</b><small>탄단지 미입력</small></span></div><p class="home-ratio-empty">탄단지를 함께 기록하면<br>비율을 볼 수 있어요.</p>';
}
function committedProps(props){return props.map(i=>`<span class="home-prop-mini" data-home-prop="${esc(i.id)}" data-home-art="${esc(i.art)}" style="--prop-x:${Number(i.x)*100}%;left:var(--prop-x);top:${Math.max(0,Math.min(100,i.y*100))}%;z-index:${Number(i.z)||0}" aria-hidden="true">${K.getArt(i)}</span>`).join('');}
function macroStrip(report){return `<div class="record-macros">${['carb','protein','fat'].map(k=>{const n=report.nutrients[k];return `<div data-record-balance="${k}"><span>${M.NUTRIENTS[k][0]}</span><strong>${n.value===null?'—':fmt(n.value)}<small>g</small></strong><small>${n.target===null?'목표 미설정':'/ '+fmt(n.target)+'g'}</small><div class="record-track"><i style="width:${n.percent===null?0:Math.min(100,n.percent)}%"></i></div>${n.missing?`<small>${n.missing}끼 미입력</small>`:''}</div>`;}).join('')}</div>`;}
function monthlyCalendar(flow,play){
 const [year,month]=monthView.split('-').map(Number),offset=new Date(year,month-1,1).getDay(),days=new Date(year,month,0).getDate(),marked=new Set([...play.meals.map(m=>m.day),...flow.supplements.flatMap(s=>s.days)]);
 return `<div class="calendar-weekdays" aria-hidden="true">${['일','월','화','수','목','금','토'].map(d=>`<span>${d}</span>`).join('')}</div><div class="home-calendar" aria-label="${year}년 ${month}월 전체 날짜">${Array.from({length:offset+days},(_,i)=>{const n=i-offset+1;if(n<1)return '<span></span>';const day=monthView+'-'+String(n).padStart(2,'0');return `<button type="button" data-home-day="${day}" ${day===recordDay?'aria-current="date"':''} aria-label="${month}월 ${n}일${marked.has(day)?' 기록 있음':''}">${n}${marked.has(day)?'<i aria-hidden="true"></i>':''}</button>`;}).join('')}</div>`;
}
function showRecords(day=recordDay,subtab='nutrition'){if(F.day(day)){recordDay=day;monthView=day.slice(0,7);}update();selectSubtab(['nutrition','supplements','monthly','budget'].includes(subtab)?subtab:'nutrition');return recordDay;}
function update(){
 if(updating||!G||!$('#todayKitchen'))return;updating=true;
 try{
  const day=today(),world=K.exportWorld(),flow=J.getWorkflow(),play=J.getSnapshot(),daily=J.summary(day),record=J.summary(recordDay),month=F.monthly(flow,play,monthView);
  ranked=G.recommend(C,world,flow,play,{day}).filter(({recipe:r,cost})=>(!recipeFilters.time||Number(String(r.time).match(/\d+/)?.[0])<=Number(recipeFilters.time))&&(!recipeFilters.budget||cost!==null&&cost<=Number(recipeFilters.budget))&&!recipeFilters.exclude.split(/[,\n]/).map(x=>x.trim()).filter(Boolean).some(n=>Object.keys(r.amounts).some(v=>G.same(n,v)))&&(!recipeFilters.ingredient||Object.keys(r.amounts||{}).some(v=>G.same(recipeFilters.ingredient,v))));const selected=recommendation();
  const props=world.items.filter(i=>i.kind==='decor'&&!i.depleted),propMarkup=committedProps(props);
  if($('#homeProps'))$('#homeProps').innerHTML=propMarkup;
  if($('#homeSceneDecor'))$('#homeSceneDecor').innerHTML=propMarkup;
  $('#todayStamp').textContent=new Date().toLocaleDateString('ko-KR',{month:'long',day:'numeric',weekday:'short'});
  const notice=$('#homeStorageNotice');notice.dataset.storageStatus=J.status;notice.hidden=J.status==='saved';notice.setAttribute('aria-label',J.status==='temporary'?'임시 세션입니다. 닫기 전에 백업해 주세요.':'새 저장이 중단됐어요. 기존 기록과 백업을 확인해 주세요.');notice.innerHTML='<span>'+(J.status==='temporary'?'임시 세션':'저장 중단')+'</span>'+action('백업','backupTools','');
  const soon=new Date();soon.setDate(soon.getDate()+3);const near=world.items.filter(i=>['food','seasoning'].includes(i.kind)&&!i.depleted&&i.expiry&&i.expiry>=day&&i.expiry<=dayString(soon)).sort((a,b)=>a.expiry.localeCompare(b.expiry));
  $('#homeRecommendation').dataset.screenId='B1';
  $('#homeRecommendation').innerHTML=window.KitchenRecipeHub.renderRecommendation({ranked,near,filters:recipeFilters,esc,fmt,money,dish,action,routeButton,recommendationView});
  const plans=flow.plans.filter(p=>p.day===planDay),slots={breakfast:'아침',lunch:'점심',dinner:'저녁'};
  $('#homePlans').dataset.screenId='B4';
  $('#homePlans').innerHTML=window.KitchenRecipeHub.renderPlans({plans,slots,flow,play,catalog:C,day,planDay,dateMarkup:dateBar('homePlanDay',planDay),esc,fmt,dish,action,routeButton});
  $('#homeNutrition').innerHTML=window.KitchenRecordHub.renderNutrition({record,flow,play,catalog:C,recordDay,day,esc,fmt,money,dish,action,routeButton,macroStrip});
  const currentMonth=F.monthly(flow,play,monthView),remaining=currentMonth.budget===null?null:currentMonth.budget-currentMonth.spending,shopping=flow.shopping,shoppingKnown=shopping.filter(s=>s.estimate!==null&&s.estimate!==undefined),estimate=shoppingKnown.reduce((n,s)=>n+Number(s.estimate||0),0);
  $('#homeBudget').innerHTML=window.KitchenRecordHub.renderBudget({record,flow,play,catalog:C,recordDay,day,monthView,month,currentMonth,remaining,shopping,shoppingKnown,estimate,dateMarkup:dateBar('homeBudgetMonth',monthView,'month'),esc,fmt,money,dish,action,routeButton,macroStrip});
  $('#homeSupplements').innerHTML=window.KitchenRecordHub.renderSupplements({record,flow,play,catalog:C,recordDay,day,esc,fmt,money,dish,action,routeButton,macroStrip});
  $('#homeMonthly').innerHTML=window.KitchenRecordHub.renderMonthly({record,flow,play,catalog:C,recordDay,day,monthView,month,currentMonth,ratioMarkup:ratioView(record),calendarMarkup:monthlyCalendar(flow,play),dateMarkup:dateBar('homeMonth',monthView,'month'),dayDateMarkup:dateBar('homeMonthDay',recordDay),esc,fmt,money,dish,action,routeButton,macroStrip});
  const owned=M.roomRewards.filter(id=>M.ownsRoomReward(play,world,id)).map(id=>M.REWARDS[id].name),goal=daily.goal,firstDone=play.awarded.length>0;
  $('#homeGrowth').dataset.screenId='D1';
  $('#homeGrowth').innerHTML=window.KitchenGrowthHub.renderGrowth({firstDone,goal,daily,propsMarkup:propMarkup,esc,fmt,routeButton,action,icons:A,fridgeArt:K.getFridgeArt?.(),giftIcon:J.giftIcon()});
  let progress=$('#homeFridgeProgress');if(!progress){progress=document.createElement('button');progress.type='button';progress.id='homeFridgeProgress';progress.dataset.homeOpen='growth';$('#panel-fridge').appendChild(progress);}progress.hidden=!daily.cooked.length;progress.innerHTML=`<span><strong>나의 진행</strong><span>${dish(C.find(r=>r.id===daily.cooked[0])||C[0])}</span></span><span><b>요리 도감 ${daily.cooked.length} / ${C.length}</b><small>${goal.value>=goal.target?'오늘의 목표 완료 ✓':'다음 요리도 기록해 보세요.'}</small></span><span class="home-applied-ticket">꾸밈권 ${daily.tickets}</span><span aria-hidden="true">›</span>`;
  let fridgeOpen=$('#growthFridgeOpen');if(!fridgeOpen){fridgeOpen=document.createElement('button');fridgeOpen.type='button';fridgeOpen.id='growthFridgeOpen';fridgeOpen.dataset.growthOpenFridge='';fridgeOpen.innerHTML='냉장고 열기 <span aria-hidden="true">›</span>';$('#fridgeSceneHost').appendChild(fridgeOpen);}
  $('#homeConnections').innerHTML=`<div class="home-block-heading"><div><p>나의 설정과 기록 보관</p><h3>설정·백업</h3></div></div><p class="home-save-state">${J.status==='saved'?'이 브라우저에 기록을 저장하고 있어요.':J.status==='temporary'?'현재 임시 세션이에요. 닫기 전에 백업해 주세요.':'기존 기록을 확인해 주세요. 새 저장이 중단됐어요.'}</p><div class="home-actions">${action('백업·복구','backupTools','','home-primary')}${routeButton('하루 영양 목표','targets')}${routeButton('설정 열기','settings')}<button type="button" id="expandDisplays">표시창 확대</button><button type="button" id="help">조작 방법</button></div><details class="home-data-status"><summary>지원 기능과 정보 기준</summary><p>제품·기한 사진은 이 기기에서 글자를 읽고 직접 검수해요. 냉장고 전체 사진의 식재료 자동 판별과 새 미니어처 생성은 연결 전이에요.</p><p>영양·원가는 입력한 값으로 계산해요. 공식 식품 성분·가격·개인 권장량과 기기 간 동기화는 연결 전이에요. 기존 운영 앱 기록과 별도로 보관해요.</p></details>`;
  const sidebar=$('#desktopSummary');if(sidebar)sidebar.innerHTML=`<p class="home-label">오늘 먼저 먹을 재료로</p>${recommendationView(selected,true)}<div class="home-sidebar-links"><button type="button" data-home-open="recommendation">레시피</button><button type="button" data-home-open="budget">식비</button><button type="button" data-home-open="growth">내 부엌</button></div>`;
  K.refreshDisplays();
 }finally{updating=false;}
}
document.addEventListener('click',event=>{
 const tab=event.target.closest('[data-home-tab]');if(tab){showTab(tab.dataset.homeTab);return;}
 const sub=event.target.closest('[data-home-subtab],[data-home-open]');if(sub){selectSubtab(sub.dataset.homeSubtab||sub.dataset.homeOpen);return;}
 const calendar=event.target.closest('[data-home-calendar-toggle]');if(calendar){calendarExpanded=!calendarExpanded;update();return;}
 const source=event.target.closest('[data-home-sourceinfo]');if(source){const report=J.summary(recordDay);K.showTray('성분·식사 정보',`<p class="workflow-hint">식사와 영양은 직접 입력한 기록 기준이에요. 확인되지 않은 영양값은 미입력으로 남겨요.</p>${report.rows.length?report.rows.map(m=>`<section class="workflow-card"><strong>${esc(m.name)}</strong><p>${esc(m.portion||'분량 메모 없음')}</p><small>${['kcal','carb','protein','fat'].map(k=>M.NUTRIENTS[k][0]+' '+nutrient(m.nutrients[k],M.NUTRIENTS[k][1])).join(' · ')}</small></section>`).join(''):'<p>이 날짜에 등록된 식사가 없어요.</p>'}<p class="workflow-note">영양 합계는 입력한 값만 더해요. 목표는 직접 설정한 값이며 공식 개인 권장량과 자동 연동하지 않아요.</p>`,'RECORD');return;}
 const reset=event.target.closest('[data-home-filter-reset]');if(reset){recipeFilters={time:'',budget:'',exclude:'',ingredient:''};update();return;}
 const shift=event.target.closest('[data-home-date-shift]');if(shift){const id=shift.dataset.homeDateShift,step=Number(shift.dataset.step),monthly=id==='homeMonth'||id==='homeBudgetMonth',value=monthly?monthView+'-01':id==='homePlanDay'?planDay:recordDay,d=new Date(value+'T12:00:00');if(monthly)d.setMonth(d.getMonth()+step);else d.setDate(d.getDate()+step);if(monthly){monthView=dayString(d).slice(0,7);recordDay=monthView+'-01';}else if(id==='homePlanDay')planDay=dayString(d);else{recordDay=dayString(d);if(id==='homeMonthDay')monthView=recordDay.slice(0,7);}update();return;}
 const date=event.target.closest('[data-home-day]');if(date){recordDay=date.dataset.homeDay;update();return;}
 const goal=event.target.closest('[data-home-goal]');if(goal)try{J.transact(({play})=>play.setGoal(goal.dataset.homeGoal));$(`[data-home-goal="${goal.dataset.homeGoal}"]`)?.focus();}catch(e){K.announce(e.message);}
});
document.addEventListener('keydown',event=>{
 const tab=event.target.closest('[data-home-tab],[data-home-subtab]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 const tabs=[...tab.parentElement.querySelectorAll('[role="tab"]')],index=tabs.indexOf(tab),next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
 event.preventDefault();const target=tabs[next];if(target.dataset.homeTab)showTab(target.dataset.homeTab,{focus:true});else selectSubtab(target.dataset.homeSubtab,{focus:true});
});
document.addEventListener('change',event=>{
 const input=event.target;
 if(input.id==='homePlanDay'&&F.day(input.value)){planDay=input.value;update();$('#homePlanDay')?.focus({preventScroll:true});return;}
 if(['homeRecordDay','homeSupplementDay'].includes(input.id)&&F.day(input.value)){recordDay=input.value;update();$('#'+input.id)?.focus({preventScroll:true});return;}
 if(['homeMonth','homeBudgetMonth'].includes(input.id)&&/^\d{4}-\d{2}$/.test(input.value)){monthView=input.value;recordDay=monthView+'-01';update();$('#'+input.id)?.focus({preventScroll:true});return;}
 if(input.id==='homeMonthDay'&&F.day(input.value)){recordDay=input.value;monthView=input.value.slice(0,7);update();$('#homeMonthDay')?.focus({preventScroll:true});return;}
 const filterKeys={homeRecipeTime:'time',homeRecipeBudget:'budget',homeRecipeExclude:'exclude'};if(filterKeys[input.id]){recipeFilters[filterKeys[input.id]]=input.value;update();$('#'+input.id)?.focus({preventScroll:true});return;}
 if(!input.matches('[data-home-supplement]'))return;
 const id=input.dataset.homeSupplement,checked=input.checked,day=recordDay;
 try{J.transact(({flow})=>{const item=flow.supplements.find(s=>s.id===id);if(!item)throw new Error('영양제 기록을 확인해 주세요.');item.days=item.days.filter(d=>d!==day);if(checked)item.days.push(day);});$(`[data-home-supplement="${CSS.escape(id)}"]`)?.focus();}catch(e){K.announce(e.message);update();}
});
window.KitchenHome=Object.freeze({update,recommendation,showTab,selectSubtab,showScene,showRecords,getRecordDay:()=>recordDay,showPlans,showRecipes,getRecipeFilters});update();
})();
