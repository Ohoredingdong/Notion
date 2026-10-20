/* Insights are derived from the same saved state and recipe evaluation. */
(() => {
  'use strict';
  const S=window.UMFStore,D=window.UMFDomain,R=window.UMFRecipes;
  if(!S||!D||!R)return;
  const $=s=>document.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const dayKey=(date=new Date())=>[date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');
  const groups={
    protein:['계란','닭가슴살','닭고기','소고기','돼지고기','두부','순두부','연두부','참치캔','참치','연어','고등어','콩'],
    veg:['시금치','상추','배추','양파','대파','애호박','토마토','버섯','달래','깻잎','당근','양배추','오이','브로콜리','피망','파프리카','무','부추'],
    carb:['밥/즉석밥','쌀','면/라면','면','라면','국수','소면','파스타','식빵','빵','감자','고구마','떡','오트밀'],
    dairy:['요거트','우유','치즈','요구르트']
  };
  let undoMeals=[],lastLog=0,logBusy=false,mealBusy=false,visibleDay=dayKey(),dayTimer;

  function renderBalance(){
    const state=S.getState();
    const pool=[...new Set([...state.items.filter(x=>D.usable(x)).map(x=>D.canonical(x.name)),...state.season.map(D.canonical),...state.pantry.map(D.canonical)])];
    const counts={};
    for(const [key,names] of Object.entries(groups))counts[key]=pool.filter(n=>names.map(D.canonical).includes(n)).length;
    const largest=Math.max(1,...Object.values(counts));
    for(const [key,value] of Object.entries(counts)){
      const bar=$('[data-balance="'+key+'"]'),text=$('[data-balance-pct="'+key+'"]');
      if(bar)bar.style.width=(value/largest*100)+'%';
      if(text)text.textContent=value+'종';
    }
    const note=$('#umfBalanceNote');
    if(note)note.textContent=pool.length?'재료의 종류 수를 비교해요. 영양 점수나 섭취 비율은 아닙니다.':'재료를 등록하면 구성을 보여드려요. 샘플 재료는 포함하지 않습니다.';
  }
  function shortages(){
    const all=$('#umfMissingScope')?.value==='all';
    if(!all)return R.getSelected()?.missing.map(x=>({...x,count:1}))||[];
    const map=new Map();
    for(const entry of R.getRanked())for(const missing of entry.missing){
      const key=D.canonical(missing.name);
      if(map.has(key))map.get(key).count++;
      else map.set(key,{...missing,count:1});
    }
    return [...map.values()].sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name,'ko'));
  }
  function renderMissing(){
    const box=$('#umfMissingList');if(!box)return;
    const all=$('#umfMissingScope')?.value==='all',list=shortages(),selected=R.getSelected();
    const context=$('#umfMissingContext');
    if(context)context.textContent=all?'전체 8개 메뉴에서 자주 필요한 순서':selected?selected.recipe.name+' 기준':'먼저 메뉴를 선택해 주세요.';
    if(!all&&!selected)box.innerHTML='<div class="empty">선택된 메뉴가 없어요.</div>';
    else if(!list.length)box.innerHTML='<div class="empty good">필요한 재료가 모두 등록되어 있어요.<br>실제 분량은 레시피에서 확인해 주세요.</div>';
    else{
      const kind={fridge:'냉장고',season:'기본 양념',pantry:'상비 재료'};
      const reason={missing:'미보유',expired:'소비기한 경과 · 새 재료 필요',empty:'소진 · 새 재료 필요'};
      box.innerHTML=list.map(x=>'<div class="missing-item"><div class="missing-main"><span class="ingredient-mini" aria-hidden="true">'+window.UMFCore.icon(x.name)+'</span><div><div class="missing-name">'+esc(x.name)+'</div><div class="missing-use">'+esc(all?x.count+'개 메뉴에서 필요 · '+kind[x.kind]:reason[x.reason]+' · '+kind[x.kind])+'</div></div></div><button type="button" class="missing-add" data-name="'+esc(x.name)+'" data-kind="'+esc(x.kind)+'" aria-label="'+esc(x.name)+' 보유 등록">＋</button></div>').join('');
      for(const button of box.querySelectorAll('.missing-add'))button.addEventListener('click',()=>window.UMFCore.openAdd(button.dataset.name,button.dataset.kind));
    }
    if($('#umfMissingCount'))$('#umfMissingCount').textContent=list.length+'개';
    if($('#umfMissingCountLabel'))$('#umfMissingCountLabel').textContent=all?'전체 메뉴의 부족한 재료':'선택 메뉴의 부족한 재료';
  }
  function renderSummary(){
    const items=S.getState().items,valid=items.filter(x=>D.usable(x));
    const soon=valid.filter(x=>{const n=D.daysLeft(x.expiry);return n!==null&&n>=0&&n<=2;}).length;
    if($('#umfSoonCount'))$('#umfSoonCount').textContent=soon+'개';
    if($('#umfPossibleCount'))$('#umfPossibleCount').textContent=R.getRanked().filter(x=>x.available).length+'개';
    const expired=items.filter(x=>D.daysLeft(x.expiry)!==null&&D.daysLeft(x.expiry)<0).length;
    const empty=items.filter(x=>D.parseQuantity(x.quantity).empty).length;
    const unknown=valid.filter(x=>D.daysLeft(x.expiry)===null).length;
    const note=$('#umfExpiryNotice'),parts=[];
    if(expired)parts.push('기한 경과 '+expired+'개');
    if(empty)parts.push('소진 '+empty+'개');
    if(unknown)parts.push('기한 미입력·확인 '+unknown+'개');
    if(note){note.hidden=!parts.length;note.textContent=parts.join(' · ');}
  }
  function renderMeals(){
    const box=$('#umfMealList');if(!box)return;
    const all=$('#umfMealScope')?.value==='all',state=S.getState();
    const logs=state.meals.filter(x=>all||x.day===dayKey()).sort((a,b)=>b.ts-a.ts);
    box.innerHTML=logs.length?logs.map(x=>{
      const dt=new Date(x.ts),time=new Intl.DateTimeFormat('ko-KR',all?{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}:{hour:'2-digit',minute:'2-digit'}).format(dt);
      return '<div class="meal-item"><div><div class="meal-name">'+esc(x.name)+'</div><div class="meal-time">'+esc(time)+'</div></div><button type="button" class="meal-remove" data-id="'+esc(x.id)+'" aria-label="'+esc(x.name)+' '+esc(time)+' 기록 취소">취소</button></div>';
    }).join(''):'<div class="empty">아직 '+(all?'':'오늘 ')+'기록이 없어요.<br>메뉴를 선택하고 먹은 것으로 기록해 주세요.</div>';
    for(const button of box.querySelectorAll('.meal-remove')){button.disabled=mealBusy;button.addEventListener('click',()=>removeMeals(x=>x.id===button.dataset.id));}
    const clear=$('#umfClearMeals');if(clear)clear.disabled=mealBusy||!state.meals.some(x=>x.day===dayKey());
    if($('#umfUndoMeal'))$('#umfUndoMeal').disabled=mealBusy;
  }
  function feedback(message){if($('#umfMealFeedback'))$('#umfMealFeedback').textContent=message;}
  async function removeMeals(predicate){
    if(mealBusy)return;
    const ids=new Set(S.getState().meals.filter(predicate).map(x=>x.id));
    if(!ids.size){feedback('이미 취소된 기록이에요.');return;}
    mealBusy=true;renderMeals();
    let removed=[];
    try{
      if(await S.updateAsync(st=>{removed=st.meals.filter(x=>ids.has(x.id));st.meals=st.meals.filter(x=>!ids.has(x.id));})){
        if(removed.length){undoMeals=removed;if($('#umfUndoMeal'))$('#umfUndoMeal').hidden=false;}
        feedback(removed.length?removed.length+'개 기록을 취소했어요.':'이미 취소된 기록이에요.');
      }else feedback('기록을 취소하지 못했어요. 저장 상태를 확인해 주세요.');
    }finally{mealBusy=false;renderMeals();}
  }
  async function logSelected(){
    const current=R.getSelected(),now=Date.now();
    if(!current?.available){feedback('부족한 재료를 확인한 뒤, 재료를 갖춘 메뉴를 선택해 주세요.');return;}
    if(logBusy||now-lastLog<800)return;
    logBusy=true;const button=$('#umfLogBtn');if(button){button.dataset.busy='true';button.disabled=true;}
    let stillAvailable=true;
    try{
      const ok=await S.updateAsync(st=>{
        if(!D.evaluate(current.recipe,st).available){stillAvailable=false;return;}
        st.meals.unshift({id:S.newId(),name:current.recipe.name,ts:now,day:dayKey(new Date(now))});
      });
      if(ok&&stillAvailable){lastLog=now;feedback(current.recipe.name+'을 기록했어요. 남은 수량은 재료의 ⋮ → 수정에서 바꿀 수 있어요.');}
      else if(!stillAvailable)feedback('다른 화면에서 재료가 바뀌었어요. 추천을 다시 확인해 주세요.');
      else feedback('식사 기록을 저장하지 못했어요. 저장 상태를 확인해 주세요.');
    }finally{logBusy=false;if(button){delete button.dataset.busy;button.disabled=!R.getSelected()?.available;}}
  }
  function renderDate(){if($('#umfDateMain'))$('#umfDateMain').textContent=new Intl.DateTimeFormat('ko-KR',{month:'long',day:'numeric',weekday:'short'}).format(new Date());}
  function refresh(){renderDate();renderBalance();renderMissing();renderSummary();renderMeals();}
  function scheduleDay(){
    clearTimeout(dayTimer);const now=new Date(),next=new Date(now);next.setHours(24,0,1,0);
    dayTimer=setTimeout(checkDay,Math.max(1000,next-now));
  }
  function checkDay(){
    const next=dayKey();if(next!==visibleDay){visibleDay=next;window.dispatchEvent(new CustomEvent('umf:daychange'));}
    refresh();scheduleDay();
  }
  $('#umfTopAdd')?.addEventListener('click',()=>window.UMFCore.openAdd());
  $('#umfLogBtn')?.addEventListener('click',logSelected);
  $('#umfMissingScope')?.addEventListener('change',renderMissing);
  $('#umfMealScope')?.addEventListener('change',renderMeals);
  $('#umfClearMeals')?.addEventListener('click',()=>{if(window.confirm('오늘 먹은 기록을 비울까요? 재료와 다른 날짜의 기록은 유지됩니다.'))removeMeals(x=>x.day===dayKey());});
  $('#umfUndoMeal')?.addEventListener('click',async()=>{
    if(mealBusy||!undoMeals.length)return;
    const restoring=undoMeals.map(x=>({...x}));mealBusy=true;renderMeals();
    try{
      if(await S.updateAsync(st=>{const ids=new Set(st.meals.map(x=>x.id));st.meals.push(...restoring.filter(x=>!ids.has(x.id)));})){
        undoMeals=[];$('#umfUndoMeal').hidden=true;feedback('취소한 기록을 복원했어요.');
      }else feedback('기록을 복원하지 못했어요. 저장 상태를 확인해 주세요.');
    }finally{mealBusy=false;renderMeals();}
  });
  $('#umfExpandRecipes')?.addEventListener('click',event=>{
    const open=$('.recipeSec').classList.toggle('show-all');
    event.currentTarget.textContent=open?'접기':'전체 펼치기';event.currentTarget.setAttribute('aria-expanded',String(open));
  });
  // Arrow keys complement ordinary Tab/Enter interaction for the two tabs.
  $('.tabs')?.addEventListener('keydown',event=>{
    if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    const tabs=[...document.querySelectorAll('.tab')],current=tabs.indexOf(document.activeElement);
    const index=event.key==='Home'?0:event.key==='End'?tabs.length-1:(current+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
    event.preventDefault();tabs[index]?.click();tabs[index]?.focus();
  });
  S.subscribe(refresh);
  window.addEventListener('umf:selectionchange',()=>{renderMissing();renderSummary();});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkDay();});
  window.addEventListener('focus',checkDay);
  window.UMFInsights={refresh,shortages,logSelected,dayKey,checkDay};
  refresh();scheduleDay();
})();
