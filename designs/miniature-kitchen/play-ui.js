/* Journal, nutrition, collection and cosmetic rewards for this preview only. */
(() => {
'use strict';
const MAGNETS = './designs/miniature-kitchen/assets/magnets.png';
const KEY='miniature-kitchen-preview-v1',M=window.KitchenPlayModel,F=window.KitchenWorkflowModel,K=window.MiniKitchen,C=window.KitchenCatalog,A=window.KitchenSceneArt||window.UMFKitchenArt;
const $=s=>document.querySelector(s),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const today=()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');};
let magnetSerial=0,rewardPane='rewards',rewardChoice='room-flowers',firstRecordId=null,rewardReturn='home';
const roomProps={flowers:{name:'데이지 유리병',desc:'작은 꽃으로 부엌에 포근한 분위기를 더해요.'},cup:{name:'우드 트레이와 찻잔',desc:'잠깐의 차 한 잔을 위한 따뜻한 자리예요.'},utensils:{name:'도자기 도구통',desc:'자주 쓰는 조리 도구를 가지런히 놓아요.'},cookies:{name:'쿠키 유리병',desc:'달콤한 간식을 담아 조리대에 놓아요.'}};
const ids=C.map(r=>r.id),keys=Object.keys(M.NUTRIENTS),find=id=>C.find(r=>r.id===id),number=x=>Math.round(x*10)/10;
let storage,lastRaw=null,blocked=false,status='temporary',originalRaw=null,loading=false,viewDay=today(),tab='nutrition',slot='frozenLeft',model=M.create(ids),workflow=F.blank(),envelopeExtra={},recoveryRaw=null;
function validEnvelope(v){
 if(!(v&&v.version===1&&M.valid(v.play,ids)&&M.validWorld(v.world)&&v.world.items.filter(i=>i.kind==='meal').length===1&&v.world.items.every(i=>i.kind!=='meal'||C.some(r=>r.name===i.name))&&(v.workflow===undefined||F.valid(v.workflow))))return false;
 if(v.workflow){const f=v.workflow;if(!f.plans.every(p=>ids.includes(p.recipeId))||!Object.keys(f.recipeFacts).every(id=>ids.includes(id))||!Object.keys(f.recipeNotes).every(id=>ids.includes(id))||!f.transactions.every(t=>!t.active||v.play.meals.some(m=>m.id===t.mealId)))return false;if(f.lastCanceled&&!M.valid({...v.play,meals:[...v.play.meals,f.lastCanceled.record]},ids))return false;}
 return true;
}
try{storage=window.localStorage;lastRaw=storage.getItem(KEY);if(lastRaw!==null){const data=JSON.parse(lastRaw);if(!validEnvelope(data))throw new Error('invalid');model=M.create(ids,data.play);workflow=F.create(data.workflow);envelopeExtra={...data};loading=true;K.restoreWorld(data.world);loading=false;}status='saved';}catch(e){loading=false;if(storage&&lastRaw!==null){originalRaw=lastRaw;blocked=true;status='blocked';}else storage=null;}
const envelope=()=>({...envelopeExtra,version:1,world:K.exportWorld(),play:model.state(),workflow:JSON.parse(JSON.stringify(workflow))});
function save(){
 if(loading)return;
 if(storage&&!blocked){try{const raw=storage.getItem(KEY);if(raw!==lastRaw){blocked=true;status='conflict';}else{const next=envelope();if(!validEnvelope(next))throw new Error('invalid');const value=JSON.stringify(next);storage.setItem(KEY,value);lastRaw=value;status='saved';}}catch(_){status='temporary';}}
 update();
}
function statusText(){return {saved:'이 시안에 저장 · 기존 앱 기록과 별도',temporary:'임시 세션 · 백업에서 기록을 보관해 주세요',blocked:'이전 저장 원본 보존 · 새 저장 중단',conflict:'다른 화면의 기록 변경 · 새로 열거나 백업해 주세요'}[status];}
function update(){
 const s=model.state(),report=model.summary(today());
 const progress=$('#kitchenProgress>span'),journal=$('#openJournal'),note=$('.design-note>span');
 if(progress)progress.textContent='도감 '+report.cooked.length+'/'+C.length+' · 꾸밈권 '+report.tickets;
 if(journal)journal.textContent='식사·영양과 도감';
 if(note)note.textContent=statusText();
 updateDecorations();window.KitchenWorkflows?.update();
}
function charm(id,label=''){if(id==='plate')return `<span class="charm-nameplate">${esc(label)}</span>`;const box={tile:[64,70,560,560],daisy:[628,70,610,600],photo:[64,644,560,560]}[id];const clip='journal-magnet-'+(++magnetSerial);return `<svg class="magnet-art" viewBox="${box.join(' ')}" aria-hidden="true"><defs><clipPath id="${clip}"><rect x="${box[0]}" y="${box[1]}" width="${box[2]}" height="${box[3]}"/></clipPath></defs><image href="${MAGNETS}" width="1254" height="1254" clip-path="url(#${clip})"/></svg>`;}
function updateDecorations(){
 const root=$('#fridgeDisplays');document.querySelectorAll('.fridge-charm,.decor-door-charm').forEach(n=>n.remove());const s=model.state(),world=K.getSnapshot();
 const pending=K.getDecorEquippedDraft?.(),backdrop=$('.decor-fridge-backdrop');
 if(pending&&backdrop&&document.body.dataset.camera==='counter'&&$('#decorStage')?.getClientRects().length){
  for(const [position,id] of Object.entries(pending))if(id){const n=document.createElement('span');n.className='decor-door-charm';n.dataset.slot=position;n.dataset.charm=id;n.setAttribute('aria-hidden','true');n.innerHTML=charm(id,s.plateLabel);backdrop.appendChild(n);}
 }
 const stage=$('.fridge-stage').getBoundingClientRect(),room=$('.room').getBoundingClientRect();
 for(const [position,id] of Object.entries(s.equipped))if(id&&!K.isDoorClosing(position)){
  const n=document.createElement('span');n.className='fridge-charm';n.dataset.charm=id;n.setAttribute('aria-hidden','true');n.innerHTML=charm(id,s.plateLabel);
  if(world.doors[position]){
   const parent=document.querySelector('[data-cargo="'+position+'"] .door-storage');if(!parent)continue;
   n.classList.add('is-interior');Object.assign(n.style,{left:'25%',top:'9%',width:'50%',height:'24%'});parent.appendChild(n);
  }else{
   const right=position==='frozenRight',size=Math.max(28,Math.min(58,stage.width*.16));Object.assign(n.style,{left:Math.round(stage.x-room.x+stage.width*(right?.75:.255)-size/2)+'px',top:Math.round(stage.y-room.y+stage.height*.72)+'px',width:size+'px',height:size+'px'});root.appendChild(n);
  }
 }
}
function nav(){return `<nav class="journal-tabs" aria-label="식사와 성장에서 볼 곳">${[['nutrition','영양'],['book','도감'],['rewards','꾸밈'],['backup','백업']].map(([id,label])=>`<button type="button" data-journal="${id}" aria-pressed="${tab===id}">${label}</button>`).join('')}</nav>`;}
function show(next=tab,arg=null){
 const prior=tab;tab=next;if(next==='firstRecord')firstRecordId=arg;
 if(next==='rewards'&&prior!=='rewards'){rewardReturn=prior==='firstRecord'?'firstRecord':prior==='book'?'book':'home';rewardPane='rewards';rewardChoice='room-flowers';}
 const titles={nutrition:'내 식사와 영양',book:'요리 도감',firstRecord:'첫 요리·보상 확인',rewards:'소품 선택',backup:'이 시안의 기록 보관'};
 K.showTray(titles[tab],nav()+({nutrition,book,firstRecord,rewards,backup}[tab])(),'MY KITCHEN JOURNAL');window.KitchenWorkflows?.enhanceJournal(tab);
 if(['book','firstRecord','rewards'].includes(tab)){
  document.querySelector('#trayContent .workflow-nav')?.remove();document.querySelector('#trayContent .journal-tabs')?.remove();
  const dest=tab==='book'?'home':tab==='firstRecord'?'book':rewardReturn;
  $('#trayContent').insertAdjacentHTML('afterbegin',`<button type="button" class="growth-screen-back" data-growth-back="${dest}" aria-label="이전 화면으로">‹</button>`);
  $('#tray').dataset.screenId={book:'D2',firstRecord:'D3',rewards:'D4'}[tab];
 }
}
function fields(values={},targets=false){return `<div class="journal-fields">${keys.map(k=>{const [name,unit]=M.NUTRIENTS[k];return `<label>${name} <small>${unit}</small><input name="${k}" type="number" step="any" min="${targets?'0.01':'0'}" max="100000" value="${values[k]??''}" placeholder="${targets?'미설정':'미입력'}"></label>`;}).join('')}</div>`;}
function nutrition(){
 const r=model.summary(viewDay),s=model.state();return `<div class="journal-day"><label>살펴볼 날짜<input type="date" id="journalDay" value="${viewDay}" required></label><button type="button" class="small-action primary" data-log>식사 기록</button></div><p class="journal-note">먹은 분량의 영양값을 직접 입력해요. 빈칸은 미입력으로 남고, 목표는 직접 정할 수 있어요.</p><div class="nutrient-gauges">${keys.map(k=>{const n=r.nutrients[k],[name,unit]=M.NUTRIENTS[k],percent=n.percent===null?0:Math.min(100,n.percent);return `<section class="nutrient-gauge" data-nutrient="${k}"><span>${name}</span><strong>${n.value===null?'미입력':number(n.value)+' <small>'+unit+'</small>'}</strong><div class="gauge-track" ${n.percent!==null?'role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+number(percent)+'" aria-label="'+name+' 목표 대비"':''}><i style="width:${percent}%"></i></div><small>${n.target===null?'목표 미설정':n.percent===null?'목표 '+n.target+' '+unit:Math.round(n.percent)+'% · 목표 '+n.target+' '+unit}${n.missing?' · '+n.missing+'건 미입력':''}</small></section>`;}).join('')}</div><details class="journal-section"><summary>하루 목표 설정</summary><form id="targetsForm">${fields(s.targets,true)}<button class="small-action primary" type="submit">목표 저장</button></form></details><section class="journal-section"><div class="journal-heading"><h3>기록한 식사</h3><button class="small-action" type="button" data-undo-meal>취소 복구</button></div>${r.rows.length?r.rows.map(m=>`<article class="journal-meal"><div><strong>${esc(m.name)}</strong><small>${esc(m.portion||'먹은 분량 메모 없음')} · 직접 입력</small></div><button type="button" data-wf="editMeal" data-arg="${esc(m.id)}">수정</button><button type="button" data-remove-meal="${esc(m.id)}">기록 취소</button></article>`).join(''):'<p class="journal-empty">아직 기록이 없어요. 실제로 먹은 한 끼부터 남겨 보세요.</p>'}</section><div class="journal-feedback" role="status"></div>`;
}
function book(){
 const s=model.state(),r=model.summary(today());return `<section class="story-book"><div class="story-book-progress"><span>첫 요리 기록 <strong>${r.cooked.length} / ${C.length}</strong></span><span class="ticket-pill">꾸밈권 ${r.tickets}</span></div><div class="recipe-book">${C.map(recipe=>{const count=s.meals.filter(m=>m.recipeId===recipe.id).length;return `<article class="book-card ${count?'is-cooked':''}"><button type="button" class="book-open" ${count?'data-first-record-recipe':'data-book-recipe'}="${recipe.id}" aria-label="${esc(recipe.name)} ${count?'첫 요리 기록 보기':'레시피 보기'}"><span class="book-art ${count?'':'not-cooked'}">${window.KitchenStoryboardArt.dish(recipe)}${count?'<span class="book-photo-stamp">기록 완료</span>':'<span class="book-unrecorded-lock" aria-hidden="true">⌑</span>'}</span><strong>${esc(recipe.name)}</strong><small>${count?'요리 기록 '+count+'회':'미기록'}</small></button></article>`;}).join('')}<article class="book-card book-find"><button type="button" data-workflow="recipes"><span class="book-find-icon" aria-hidden="true">⌕</span><strong>다른 요리 찾기</strong><span aria-hidden="true">›</span></button></article></div><details class="book-goal-settings"><summary>나의 목표</summary><label>목표 선택<select id="journalGoal">${[['collection','요리 도감 3장 채우기'],['recording','오늘 식사 한 끼 기록하기'],['nutrition','먹은 분량의 탄단지 기록하기']].map(([key,label])=>`<option value="${key}" ${key===s.goal?'selected':''}>${label}</option>`).join('')}</select></label><span>${r.goal.value} / ${r.goal.target}</span></details></section>`;
}
function giftIcon(){return '<svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><path d="M8 21h32v22H8z" fill="#e6b374"/><path d="M5 14h38v10H5z" fill="#f4cb91"/><path d="M21 14h7v29h-7z" fill="#f1e0b9"/><path d="M24 14C6 16 10 0 20 7l4 7Zm0 0C42 16 38 0 28 7l-4 7Z" stroke="#d69a51" stroke-width="3"/></svg>';}
function firstRecord(){
 const s=model.state(),id=s.awarded.includes(firstRecordId)?firstRecordId:s.awarded.at(-1),recipe=find(id),first=s.meals.find(m=>m.recipeId===id);if(!recipe)return '<section class="first-record-empty"><h3>첫 요리를 기다리고 있어요</h3><p>먹은 식사를 기록하면 도감이 채워져요.</p><button type="button" class="small-action primary" data-workflow="recipes">첫 요리 기록하기</button></section>';
 return `<section class="first-record"><div class="first-record-hero">${window.KitchenStoryboardArt.dish(recipe)}<span class="first-record-stamp">기록 완료</span></div><div class="first-record-copy"><h3>${esc(recipe.name)}을 기록했어요</h3>${first?`<small>${esc(first.day)} · ${esc(first.portion||'식사 기록')}</small>`:'<small>현재 식사 기록은 취소됐어요. 보상 지급 이력은 유지돼요.</small>'}</div><div class="first-record-gift">${giftIcon()}<div><strong>꾸밈권 +1</strong><small>지급 완료 · 한 번만 지급</small></div></div><div class="first-record-actions"><button type="button" class="small-action primary" data-journal="rewards">소품 고르기 <span aria-hidden="true">›</span></button><button type="button" class="small-action" data-journal="book">요리 도감</button></div></section>`;
}
function detail(id){if(window.KitchenWorkflows)return window.KitchenWorkflows.recipe(id);const recipe=find(id);if(!recipe)return;model.discover(id);save();K.showTray(recipe.name,`<div class="journal-recipe-art">${window.KitchenStoryboardArt.dish({id:recipe.name})}</div><p class="journal-note">${esc(recipe.desc)} · ${esc(recipe.time)}</p><h3>재료</h3><dl class="recipe-amounts">${Object.entries(recipe.amounts).map(([name,amount])=>`<div><dt>${esc(name)}</dt><dd>${esc(amount)}</dd></div>`).join('')}</dl>${recipe.water?'<p class="journal-note">'+esc(recipe.water)+'</p>':''}<h3>만드는 순서</h3><ol class="recipe-steps">${recipe.steps.map(step=>`<li>${esc(step)}</li>`).join('')}</ol><div class="tray-actions"><button type="button" class="small-action primary" data-log="${id}">먹은 식사 기록</button></div>`,'MY RECIPE BOOK');}
function logForm(recipeId=null){
 if(window.KitchenWorkflows)return window.KitchenWorkflows.logMeal(recipeId);
 const recipe=find(recipeId),chosen=recipeId||'';K.showTray('먹은 한 끼를 기록해요',`<form id="mealForm"><div class="journal-fields"><label>날짜<input type="date" name="day" value="${viewDay}" required></label><label>도감에 연결할 요리<select name="recipeId"><option value="">직접 입력한 식사</option>${C.map(r=>`<option value="${r.id}" ${r.id===chosen?'selected':''}>${esc(r.name)}</option>`).join('')}</select></label><label>식사 이름<input name="name" value="${esc(recipe?.name||'')}" required maxlength="120" placeholder="먹은 음식"></label><label>먹은 분량 메모<input name="portion" maxlength="80" placeholder="예: 반 공기, 1인분"></label></div><h3 class="journal-subtitle">먹은 분량 전체의 영양값</h3><p class="journal-note">제품 영양표나 확인한 자료를 보고 입력하세요. 레시피에서 영양값을 자동 추정하지 않아요. 모르는 값은 비워 두어도 식사를 기록할 수 있어요.</p>${fields()}<button type="submit" class="small-action primary">식사 기록하기</button><div class="journal-feedback" role="status"></div></form>`,'MY MEAL');
}
function rewards(){
 const s=model.state(),r=model.summary(today()),w=K.exportWorld(),basic=rewardPane==='owned',all=M.roomRewards.map(id=>[id,M.REWARDS[id]]),entries=basic?all.filter(([id])=>M.ownsRoomReward(s,w,id)):all;
 if(!entries.some(([id])=>id===rewardChoice))rewardChoice=entries[0]?.[0]||'room-flowers';
 const selected=M.REWARDS[rewardChoice],owned=M.ownsRoomReward(s,w,rewardChoice),draft=K.getDecorDraftState(),reserved=draft.cost||0,already=draft.pendingRewards?.includes(rewardChoice),available=owned||r.tickets>=selected.cost+reserved-(already?selected.cost:0),propArt=id=>K.getArt({kind:'decor',art:M.REWARDS[id].art});
 return `<section class="story-props"><div class="prop-selection-heading"><span class="ticket-pill">${giftIcon()} 꾸밈권 ${r.tickets}</span></div><div class="prop-selection-tabs" role="tablist" aria-label="소품 종류"><button type="button" role="tab" data-reward-pane="owned" aria-selected="${basic}">보유 소품</button><button type="button" role="tab" data-reward-pane="rewards" aria-selected="${!basic}">보상 소품</button></div><div class="prop-photo-options">${entries.map(([id,item])=>`<button type="button" class="prop-photo-card" data-growth-selectprop="${id}" aria-pressed="${rewardChoice===id}"><span class="prop-card-photo">${propArt(id)}${rewardChoice===id?'<span class="prop-selected-check" aria-hidden="true">✓</span>':''}</span><strong>${esc(item.name)}</strong><small>${M.ownsRoomReward(s,w,id)?'보유 중':'꾸밈권 '+item.cost}</small></button>`).join('')||'<p class="prop-empty">첫 요리를 기록하고 소품을 골라 보세요.</p>'}</div>${entries.length?`<article class="prop-selection-preview"><div class="prop-preview-copy"><h3>${esc(selected.name)}</h3><p>${esc(selected.desc)}</p><span class="prop-cost">${owned?'보유 소품':giftIcon()+' 꾸밈권 '+selected.cost}</span></div><div class="prop-preview-art">${propArt(rewardChoice)}</div></article><button type="button" class="small-action primary prop-select-apply" ${!available?'disabled':''} data-reward="${rewardChoice}">${available?'배치해보기':'꾸밈권이 더 필요해요'} <span aria-hidden="true">›</span></button><p class="prop-selection-note">${owned?'배치를 확인한 뒤 적용하면 저장돼요.':'적용할 때 꾸밈권 '+selected.cost+'개를 사용해요. 취소하면 그대로예요.'}</p>`:''}<details class="legacy-room-props"><summary>기존 조리대 소품</summary><div class="legacy-prop-actions"><button type="button" class="small-action" data-add-prop="utensils">도자기 도구통</button><button type="button" class="small-action" data-add-prop="cookies">쿠키 유리병</button></div></details><details class="legacy-door-props"><summary>냉장고 문 소품</summary><label class="journal-select">붙일 곳<select id="rewardSlot"><option value="frozenLeft" ${slot==='frozenLeft'?'selected':''}>냉동 왼쪽 문</option><option value="frozenRight" ${slot==='frozenRight'?'selected':''}>냉동 오른쪽 문</option></select></label><div class="legacy-prop-actions">${Object.entries(M.REWARDS).filter(([,item])=>item.kind!=='room').map(([id,item])=>`<button type="button" class="small-action" data-reward="${id}" ${!s.owned.includes(id)&&r.tickets<item.cost?'disabled':''}>${esc(item.name)} · ${s.owned.includes(id)?'보유':'꾸밈권 '+item.cost}</button>`).join('')}</div>${s.owned.includes('plate')?`<form id="plateForm"><label>이름표 문구<input name="label" value="${esc(s.plateLabel)}" maxlength="12" required></label><button class="small-action" type="submit">문구 바꾸기</button></form>`:''}<button type="button" class="small-action" data-clear-charm>문 소품 떼어 보기</button></details><div class="journal-feedback" role="status"></div></section>`;
}
function backup(){return `<p class="journal-note">이 시안의 재료·문 상태·식사·영양 목표·도감·소품을 함께 보관해요. 기존 앱 기록은 읽거나 변경하지 않아요.</p><p class="journal-save-status">${statusText()}</p><label class="journal-select">복사해서 보관할 기록<textarea id="journalExport" rows="5" readonly>${esc(JSON.stringify(envelope(),null,2))}</textarea></label>${originalRaw?'<details class="journal-section"><summary>읽지 못한 이전 원본 보관</summary><textarea rows="4" readonly>'+esc(originalRaw)+'</textarea></details>':''}<form id="importForm" class="journal-section"><label>이 시안의 백업 붙여넣기<textarea name="backup" rows="5" required></textarea></label><p class="journal-note">형식을 확인한 뒤 이 시안의 현재 기록을 교체해요. 읽기 오류나 다른 화면과 충돌이 있으면 원본 저장은 유지하고 임시로 불러와요.</p><button class="small-action primary" type="submit">이 기록 불러오기</button><div class="journal-feedback" role="status"></div></form>`;}
function feedback(message){const node=$('#trayContent .journal-feedback');if(node)node.textContent=message;else $('#liveMessage').textContent=message;}
function inputNumbers(form){return Object.fromEntries(keys.map(k=>[k,form.get(k)===''?null:Number(form.get(k))]));}
document.addEventListener('click',event=>{const b=event.target.closest('button');if(!b)return;try{
 if(b.id==='openJournal'){if(window.KitchenWorkflows)window.KitchenWorkflows.selectedAction();else show('nutrition');}if(b.dataset.journal)show(b.dataset.journal);
 if(b.dataset.rewardPane){rewardPane=b.dataset.rewardPane;show('rewards');}
 if(b.dataset.growthSelectprop){rewardChoice=b.dataset.growthSelectprop;show('rewards');}
 if(b.dataset.growthBack){if(b.dataset.growthBack==='home'){K.closeTray();window.KitchenHome?.selectSubtab('growth');}else show(b.dataset.growthBack,firstRecordId);}
 if(b.dataset.firstRecordRecipe)show('firstRecord',b.dataset.firstRecordRecipe);
 if(b.dataset.bookRecipe)detail(b.dataset.bookRecipe);
 if(b.hasAttribute('data-log'))logForm(b.dataset.log||null);
 if(b.dataset.previewRecipe)K.chooseRecipe(find(b.dataset.previewRecipe).name);
 if(b.dataset.removeMeal){if(window.KitchenWorkflows)window.KitchenWorkflows.cancelMeal(b.dataset.removeMeal);else{model.remove(b.dataset.removeMeal);save();show('nutrition');feedback('기록을 취소했어요. 영양 합계도 다시 계산했어요.');}}
 if(b.hasAttribute('data-undo-meal')){if(window.KitchenWorkflows){window.KitchenWorkflows.undoMeal();return;}if(model.undo()){save();show('nutrition');feedback('방금 취소한 기록을 복구했어요.');}else feedback('복구할 취소 기록이 없어요.');}
 if(b.dataset.reward)K.previewDecorReward(b.dataset.reward,{slot});
 if(b.hasAttribute('data-clear-charm')){K.setDecorEquippedDraft(slot,null);K.setCamera('counter');K.closeTray();K.announce('소품을 뗀 미리보기예요. 적용하면 저장해요.');}
 if(b.hasAttribute('data-see-fridge')){K.setCamera('fridge');K.closeTray();}
 if(b.hasAttribute('data-growth-open-fridge')){transact(({world})=>{for(const key of Object.keys(world.doors))world.doors[key]=true;});delete document.body.dataset.fridgeState;$('#panel-fridge').dataset.screenId='A1';K.closeTray();window.KitchenHome?.showTab('fridge');K.setCamera('fridge');}
}catch(e){feedback(e.message);}});
document.addEventListener('change',event=>{try{const e=event.target;if(e.id==='journalDay'&&M.day(e.value)){viewDay=e.value;show('nutrition');}if(e.id==='journalGoal'){model.setGoal(e.value);save();show('book');}if(e.id==='rewardSlot'){slot=e.value;show('rewards');}if(e.name==='recipeId'&&e.closest('#mealForm')){const r=find(e.value);if(r)$('#mealForm [name="name"]').value=r.name;}}catch(e){feedback(e.message);}});
document.addEventListener('keydown',event=>{const current=event.target.closest('[data-reward-pane]');if(!current||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();event.stopImmediatePropagation();rewardPane=event.key==='Home'?'owned':event.key==='End'?'rewards':current.dataset.rewardPane==='owned'?'rewards':'owned';show('rewards');document.querySelector('[data-reward-pane="'+rewardPane+'"]')?.focus({preventScroll:true});},true);
document.addEventListener('submit',event=>{const form=event.target;if(!['mealForm','targetsForm','plateForm','importForm'].includes(form.id))return;event.preventDefault();const f=new FormData(form);try{
 if(form.id==='mealForm'){const result=model.record({day:f.get('day'),name:f.get('name'),portion:f.get('portion'),recipeId:f.get('recipeId')||null,nutrients:inputNumbers(f)});viewDay=f.get('day');save();show('nutrition');feedback(result.earned?'식사를 기록했어요. 도감이 채워지고 꾸밈권 1개를 받았어요.':'식사를 기록했어요.');}
 if(form.id==='targetsForm'){model.setTargets(inputNumbers(f));save();show('nutrition');feedback('직접 정한 목표를 저장했어요.');}
 if(form.id==='plateForm'){model.setLabel(f.get('label'));save();show('rewards');}
 if(form.id==='importForm'){if(window.KitchenWorkflows){window.KitchenWorkflows.previewImport(f.get('backup'));return;}const data=JSON.parse(f.get('backup'));if(!validEnvelope(data))throw new Error('이 시안의 올바른 백업 형식인지 확인해 주세요. 원본은 변경하지 않았어요.');loading=true;model=M.create(ids,data.play);K.restoreWorld(data.world);loading=false;save();show('backup');feedback('백업을 불러왔어요.');}
}catch(e){loading=false;feedback(e instanceof SyntaxError?'백업 JSON을 읽을 수 없어요. 현재 기록은 유지돼요.':e.message);}});
window.addEventListener('mini-kitchen:change',event=>{if(!loading){if(event.detail?.preview)update();else save();}});
window.addEventListener('mini-kitchen:layout',updateDecorations);
window.addEventListener('mini-kitchen:recipe',event=>{const recipe=C.find(r=>r.name===event.detail.name);if(recipe){model.discover(recipe.id);save();}});
window.addEventListener('storage',event=>{if(event.key===KEY&&event.newValue!==lastRaw){blocked=true;status='conflict';update();}});
window.addEventListener('pageshow',update);
function transact(mutator){
 const nextPlay=M.create(ids,model.state()),nextWorld=K.exportWorld(),nextFlow=F.create(workflow);
 const result=mutator({world:nextWorld,play:nextPlay,flow:nextFlow});
 const candidate={version:1,world:nextWorld,play:nextPlay.state(),workflow:nextFlow};
 if(!validEnvelope(candidate))throw new Error('입력한 기록을 확인해 주세요. 이전 기록은 유지돼요.');
 if(blocked)throw new Error('기록 저장이 중단돼 있어요. 백업에서 원본을 확인해 주세요.');
 if(storage){
  let raw;try{raw=storage.getItem(KEY);}catch(_){status='temporary';update();throw new Error('저장 공간을 읽을 수 없어요. 현재 내용을 유지했어요.');}
  if(raw!==lastRaw){blocked=true;status='conflict';update();throw new Error('다른 화면에서 기록이 바뀌었어요. 현재 기록을 다시 열어 확인해 주세요.');}
 }
 const previous={model,workflow,world:K.exportWorld()},value=JSON.stringify({...envelopeExtra,...candidate});let writing=false,failure=null;
 try{loading=true;model=nextPlay;workflow=nextFlow;K.restoreWorld(nextWorld,true);if(storage){writing=true;storage.setItem(KEY,value);lastRaw=value;status='saved';}}
 catch(e){model=previous.model;workflow=previous.workflow;K.restoreWorld(previous.world,true);status='temporary';failure=writing?new Error('저장할 수 없어요. 이전 기록과 미리보기를 유지했어요. 다시 시도해 주세요.'):e;}
 finally{loading=false;}
 update();if(failure)throw failure;return result;
}
function replaceEnvelope(data){
 if(!validEnvelope(data))throw new Error('올바른 백업 형식인지 확인해 주세요.');
 const previous=JSON.stringify(envelope());
 if(storage&&!blocked){const raw=storage.getItem(KEY);if(raw!==lastRaw){blocked=true;status='conflict';update();throw new Error('다른 화면에서 기록이 바뀌었어요. 현재 기록을 다시 열어 확인해 주세요.');}if(raw!==null)storage.setItem(KEY+'-recovery',raw);}
 recoveryRaw=previous;loading=true;
 try{model=M.create(ids,data.play);workflow=F.create(data.workflow);envelopeExtra={...data};K.restoreWorld(data.world);}finally{loading=false;}
 save();return true;
}
window.KitchenJournal=Object.freeze({giftIcon,getSnapshot:()=>model.state(),summary:date=>model.summary(date||today()),getWorkflow:()=>JSON.parse(JSON.stringify(workflow)),getEnvelope:()=>JSON.parse(JSON.stringify(envelope())),transact,replaceEnvelope,validEnvelope,show,showLog:logForm,refresh:update,discover(id){model.discover(id);save();},get recovery(){return recoveryRaw||originalRaw;},get status(){return status;},storageKey:KEY});
update();
})();
