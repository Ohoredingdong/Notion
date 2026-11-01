/* Daily kitchen overview. Derived views only: never rewrites inventory or seeds records. */
(() => {
  'use strict';
  const K=window.MiniKitchen,J=window.KitchenJournal,F=window.KitchenWorkflowModel,
    G=window.KitchenJourneyModel,M=window.KitchenPlayModel,C=window.KitchenCatalog;
  const $=s=>document.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=v=>Number(v).toLocaleString('ko-KR',{maximumFractionDigits:2});
  const money=v=>v===null||v===undefined?'원가 미입력':fmt(v)+'원';
  const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
  const button=(label,route,extra='')=>`<button type="button" data-workflow="${route}" ${extra}>${label}</button>`;
  const action=(label,route,arg,cls='')=>`<button type="button" class="${cls}" data-wf="${route}" data-arg="${esc(arg)}">${label}</button>`;
  const dish=r=>window.UMFKitchenArt.dishArt({id:r.name});
  const nutrient=(v,u)=>v===null||v===undefined?'미입력':fmt(v)+u;
  let ranked=[],updating=false;
  const panelIds={fridge:'panel-fridge',meals:'todayKitchen',records:'panel-records',kitchen:'panel-kitchen'};
  const pageGroups={recommendation:'meals',plans:'meals',nutrition:'records',budget:'records',supplements:'records',monthly:'records',growth:'kitchen',connections:'kitchen'};
  function showTab(name,{focus=false}={}){
    if(!panelIds[name])return;
    for(const [key,id] of Object.entries(panelIds))document.getElementById(id).hidden=key!==name;
    document.body.dataset.home=name;
    for(const tab of document.querySelectorAll('[data-home-tab]')){const active=tab.dataset.homeTab===name;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;if(active&&focus)tab.focus({preventScroll:true});}
    if(name==='fridge')K.refreshLayout?.();
  }
  function selectSubtab(name,{focus=false}={}){
    const group=pageGroups[name];if(!group)return;showTab(group);
    const panel=document.getElementById(panelIds[group]);
    for(const page of panel.querySelectorAll('[data-home-page]'))page.hidden=page.dataset.homePage!==name;
    for(const tab of panel.querySelectorAll('[data-home-subtab]')){const active=tab.dataset.homeSubtab===name;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;if(active&&focus)tab.focus({preventScroll:true});}
    panel.scrollTop=0;
  }
  function recommendation(){return ranked[0]||null;}
  function recommendationView(candidate,compact=false){
    if(!candidate)return '<p class="home-empty">조건에 맞는 요리가 없어요. 피할 재료와 재고를 확인해 주세요.</p>'+button('요리 조건 보기','recipes');
    const {recipe:r,availability:a,nutrients:n,cost,reasons}=candidate;
    const missing=a.rows.filter(row=>row.status==='shortage'),unknown=a.rows.filter(row=>row.status==='unknown'||row.unknownExpiryIds?.length);
    return `<div class="home-recipe-top"><span class="home-status" data-stock-status="${esc(a.status)}">${a.ready?'기록한 수량으로 준비 가능':missing.length?'부족 재료 '+missing.length+'종':'수량 확인 필요'}</span><span class="home-label">현재 재고 · 입력 정보 기준</span></div>
      <div class="home-recipe-body"><div class="home-dish">${dish(r)}</div><div class="home-recipe-copy"><h3>${esc(r.name)}</h3><p>${esc(r.time)} · 기준 1회분</p><div class="home-recipe-facts"><span data-home-kcal>${n.kcal===null?'열량 미입력':fmt(n.kcal)+' kcal'}</span><span data-home-cost>${money(cost)}</span></div></div></div>
      ${compact?'':`<div class="home-recipe-macros" aria-label="추천 요리 1회분 영양"><span>탄수화물 <b>${nutrient(n.carb,'g')}</b></span><span>단백질 <b>${nutrient(n.protein,'g')}</b></span><span>지방 <b>${nutrient(n.fat,'g')}</b></span></div>`}
      <p class="home-reason">${reasons.map(esc).join(' · ')||'재료 기록을 살펴보고 골라 보세요.'}</p>
      ${missing.length?`<p class="home-shortage">부족한 재료 · ${missing.slice(0,3).map(row=>esc(row.name)+(row.shortageQuantity?' '+esc(row.shortageQuantity):'')).join(' · ')}${missing.length>3?' 외 '+(missing.length-3)+'종':''}</p>`:''}
      ${unknown.length&&!compact?`<p class="home-unknown">수량·단위 확인 · ${unknown.map(row=>esc(row.name)).join(' · ')}</p>`:''}
      <div class="home-actions">${action('요리 살펴보기','recipe',r.id,'home-primary')}${compact?'':action('영양·원가 입력','recipeFacts',r.id)}</div>`;
  }
  function update(){
    if(updating||!G||!$('#todayKitchen'))return;updating=true;
    try{
      const day=today(),world=K.exportWorld(),flow=J.getWorkflow(),play=J.getSnapshot(),daily=J.summary(day),month=F.monthly(flow,play,day.slice(0,7));
      ranked=G.recommend(C,world,flow,play,{day});
      const selected=recommendation();
      const notice=$('#homeStorageNotice');notice.hidden=J.status==='saved';notice.innerHTML='<span>'+(J.status==='temporary'?'임시 세션 · 닫기 전 백업':'저장 중단 · 기존 기록 확인')+'</span>'+action('백업','backupTools','');
      $('#homeRecommendation').innerHTML=`<div class="home-block-heading"><div><p>오늘 먼저 먹을 재료로</p><h3>오늘의 추천메뉴</h3></div>${button('전체 요리','recipes')}</div><div data-home-recipe="${esc(selected?.recipe.id||'')}">${recommendationView(selected)}</div>`;
      const plans=flow.plans.filter(p=>p.day===day),slots={breakfast:'아침',lunch:'점심',dinner:'저녁'};
      $('#homePlans').innerHTML=`<div class="home-block-heading"><div><p>${day.replaceAll('-','.')} · ${plans.length}끼 계획</p><h3>오늘의 식단</h3></div>${button('식단 계획','plan')}</div>${plans.length?plans.map(p=>{const r=C.find(r=>r.id===p.recipeId),done=flow.transactions.some(t=>t.planId===p.id&&t.active&&play.meals.some(m=>m.id===t.mealId));return `<div class="home-plan-row"><div class="home-plan-art">${dish(r)}</div><div><small>${slots[p.slot]||'식사'}${done?' · 기록 완료':''}</small><strong>${esc(r.name)}</strong><span>기준 ${fmt(p.portions)}회분</span></div>${done?button('기록 보기','nutrition'):action('먹었어요','logPlan',p.id,'home-primary')}</div>`;}).join(''):`<p class="home-empty">오늘 먹을 요리를 미리 골라 두세요.<br>계획은 먹은 식사로 기록할 때 재고에 반영돼요.</p>`}<div class="home-actions">${action('계획한 부족 재료 장보기','planShopping',day)}${button('식사 직접 기록','nutrition')}</div>`;
      $('#homeNutrition').innerHTML=`<div class="home-block-heading"><div><p>${day.replaceAll('-','.')} · 직접 기록한 식사 기준</p><h3>오늘의 영양 기록</h3></div>${button('모든 기록','hub')}</div><div class="home-month-stats"><span>먹은 식사<b>${daily.rows.length}<small>끼</small></b></span><span>기록한 열량<b>${nutrient(daily.nutrients.kcal?.value,'')}<small>kcal</small></b></span></div><p class="home-note">탄수화물·단백질·지방은 위의 오늘의 균형에서 먹은 양과 목표를 비교해요. 미입력 영양값은 0으로 계산하지 않아요.</p><div class="home-actions">${button('식사 기록·수정','nutrition','class="home-primary"')}${button('하루 목표 설정','targets')}</div>`;
      const remaining=month.budget===null?null:month.budget-month.spending;
      $('#homeBudget').innerHTML=`<div class="home-block-heading"><div><p>${Number(day.slice(5,7))}월 · 기록한 실지출 ${fmt(month.spending)}원</p><h3>남은 식비</h3></div></div><strong class="home-amount ${remaining!==null&&remaining<0?'is-over':''}" data-home-budget>${remaining===null?'예산 미설정':fmt(remaining)+'<small>원</small>'}</strong><p class="home-note">${remaining===null?'월 예산을 정하면 남은 금액을 함께 보여드려요.':'예산 '+fmt(month.budget)+'원 · 구매한 지출만 반영'}</p><div class="home-actions">${button('예산·지출','budget')}${button('장보기 '+flow.shopping.filter(s=>!s.checked).length+'개','shopping')}</div>`;
      const checked=flow.supplements.filter(s=>s.days.includes(day)).length;
      $('#homeSupplements').innerHTML=`<div class="home-block-heading"><div><p>등록한 제품 중 오늘 체크 ${checked}/${flow.supplements.length}</p><h3>영양제</h3></div>${button('관리','supplements')}</div>${flow.supplements.length?flow.supplements.map(s=>`<label class="home-supplement"><input type="checkbox" data-home-supplement="${esc(s.id)}" ${s.days.includes(day)?'checked':''}><span><strong>${esc(s.name)}</strong><small>${esc(s.schedule||'내 복용 일정 미입력')}</small></span></label>`).join(''):'<p class="home-empty">먹고 있는 영양제와<br>내 복용 일정을 기록해 보세요.</p>'}<p class="home-note">복용 체크는 식사 영양값에 합산하지 않아요.</p>`;
      $('#homeMonthly').innerHTML=`<div class="home-block-heading"><div><p>기록을 모아 보는</p><h3>한 달의 식탁</h3></div>${button('월간 보기','monthly')}</div><div class="home-month-stats"><span>식사 기록일<b>${month.days}<small>일</small></b></span><span>기록한 식사<b>${month.meals.length}<small>끼</small></b></span><span>기록한 식비<b>${fmt(month.spending)}<small>원</small></b></span></div><p class="home-note">${month.ratio?'기록된 '+month.complete+'끼의 에너지 비율 · 탄수화물 '+fmt(month.ratio.carb)+'% / 단백질 '+fmt(month.ratio.protein)+'% / 지방 '+fmt(month.ratio.fat)+'%':'탄단지를 함께 기록하면 월간 에너지 비율도 볼 수 있어요.'}</p>`;
      const owned=play.owned.map(id=>M.REWARDS[id].name),goal=daily.goal;
      $('#homeGrowth').innerHTML=`<div class="home-block-heading"><div><p>기록이 쌓이는 나의 부엌</p><h3>${esc(goal.label)}</h3></div>${button('목표 선택','book')}</div><div class="home-goal"><strong>${goal.value}<small> / ${goal.target}</small></strong><span>요리 도감 ${daily.cooked.length}/${C.length} · 꾸밈권 ${daily.tickets}개</span></div><div class="home-goal-track" role="progressbar" aria-label="${esc(goal.label)}" aria-valuemin="0" aria-valuemax="${goal.target}" aria-valuenow="${goal.value}"><i style="width:${Math.min(100,100*goal.value/goal.target)}%"></i></div><p class="home-note">${owned.length?'내 소품 · '+owned.map(esc).join(' · '):'새 요리를 처음 식사로 기록하면 꾸밈권 1개를 받아요.'}</p><div class="home-actions">${button('요리 도감','book')}${button('보상·소품 고르기','rewards')}${button('부엌 꾸미기','decor')}</div>`;
      const temporary=J.status!=='saved';
      $('#homeConnections').innerHTML=`<div class="home-block-heading"><div><p>새로 들인 재료는</p><h3>사진으로 등록하기</h3></div></div><div class="home-actions">${button('제품·기한 사진 2장','photos','class="home-primary"')}${button('냉장고 전체 사진','fridgePhoto')}${button('직접 입력','manualAdd')}</div><p class="home-note">제품·기한 사진은 이 기기에서 글자를 읽고 직접 검수해요. 냉장고 전체 사진의 재료 자동 판별과 새 미니어처 생성은 아직 지원하지 않아요.</p><details class="home-data-status"><summary>영양 정보와 기록 보관</summary><p>영양·재료비는 확인해 입력한 값으로 계산해요. 공식 식품 성분·가격 데이터와 개인별 권장량은 연결 전이에요.</p><p>${temporary?'현재 임시 세션입니다. 화면을 닫기 전에 백업으로 기록을 보관해 주세요.':'이 브라우저에 시안 기록을 저장하고 있어요.'} 기존 앱 기록과 별도이며 기기 간 자동 동기화는 지원하지 않아요.</p>${action('백업·복구 열기','backupTools','')}</details><div class="home-actions">${button('설정·저장 상태','settings')}<button type="button" id="expandDisplays">표시창 확대</button><button type="button" id="help">조작 방법</button></div>`;
      const sidebar=$('#desktopSummary');if(sidebar)sidebar.innerHTML=`<p class="home-label">오늘의 식탁</p><h2>먼저 먹을 재료로</h2>${recommendationView(selected,true)}<div class="home-sidebar-links">${button('오늘의 식단','plan')}${button('식비·예산','budget')}${button('영양제','supplements')}${button('월간 기록','monthly')}${button('요리 도감','book')}${button('부엌 꾸미기','decor')}</div>`;
      K.refreshDisplays();
    }finally{updating=false;}
  }
  document.addEventListener('click',event=>{
    const tab=event.target.closest('[data-home-tab]');if(tab){showTab(tab.dataset.homeTab);return;}
    const sub=event.target.closest('[data-home-subtab]');if(sub)selectSubtab(sub.dataset.homeSubtab);
  });
  document.addEventListener('keydown',event=>{
    const tab=event.target.closest('[role="tab"]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    const tabs=[...tab.parentElement.querySelectorAll('[role="tab"]')],index=tabs.indexOf(tab),next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
    event.preventDefault();const target=tabs[next];if(target.dataset.homeTab)showTab(target.dataset.homeTab,{focus:true});else selectSubtab(target.dataset.homeSubtab,{focus:true});
  });
  document.addEventListener('change',event=>{
    const input=event.target.closest('[data-home-supplement]');if(!input)return;
    const id=input.dataset.homeSupplement,checked=input.checked,day=today();
    try{J.transact(({flow})=>{const item=flow.supplements.find(s=>s.id===id);if(!item)throw new Error('영양제 기록을 확인해 주세요.');item.days=item.days.filter(d=>d!==day);if(checked)item.days.push(day);});$(`[data-home-supplement="${CSS.escape(id)}"]`)?.focus();}catch(e){K.announce(e.message);update();}
  });
  window.KitchenHome=Object.freeze({update,recommendation,showTab,selectSubtab});update();
})();
