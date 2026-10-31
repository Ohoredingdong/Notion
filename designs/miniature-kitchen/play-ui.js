/* Journal, nutrition, collection and cosmetic rewards for this preview only. */
(() => {
'use strict';
const MAGNETS = './designs/miniature-kitchen/assets/magnets.png';
const KEY='miniature-kitchen-preview-v1',M=window.KitchenPlayModel,F=window.KitchenWorkflowModel,K=window.MiniKitchen,C=window.KitchenCatalog,A=window.UMFKitchenArt;
const $=s=>document.querySelector(s),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const today=()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');};
let magnetSerial=0;
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
 $('#kitchenProgress>span').textContent='도감 '+report.cooked.length+'/'+C.length+' · 꾸밈권 '+report.tickets;
 $('#openJournal').textContent='식사·영양과 도감';
 $('.design-note>span').textContent=statusText();
 updateDecorations();window.KitchenWorkflows?.update();
}
function charm(id,label=''){if(id==='plate')return `<span class="charm-nameplate">${esc(label)}</span>`;const box={tile:[64,70,560,560],daisy:[628,70,610,600],photo:[64,644,560,560]}[id];const clip='journal-magnet-'+(++magnetSerial);return `<svg class="magnet-art" viewBox="${box.join(' ')}" aria-hidden="true"><defs><clipPath id="${clip}"><rect x="${box[0]}" y="${box[1]}" width="${box[2]}" height="${box[3]}"/></clipPath></defs><image href="${MAGNETS}" width="1254" height="1254" clip-path="url(#${clip})"/></svg>`;}
function updateDecorations(){
 const root=$('#fridgeDisplays');root.querySelectorAll('.fridge-charm').forEach(n=>n.remove());const s=model.state(),world=K.getSnapshot();
 const stage=$('.fridge-stage').getBoundingClientRect(),room=$('.room').getBoundingClientRect();
 for(const [position,id] of Object.entries(s.equipped))if(id&&!world.doors[position]&&!K.isDoorClosing(position)){const right=position==='frozenRight',n=document.createElement('span'),size=Math.max(28,Math.min(58,stage.width*.16));n.className='fridge-charm';n.dataset.charm=id;n.setAttribute('aria-hidden','true');Object.assign(n.style,{left:Math.round(stage.x-room.x+stage.width*(right?.75:.255)-size/2)+'px',top:Math.round(stage.y-room.y+stage.height*.72)+'px',width:size+'px',height:size+'px'});n.innerHTML=charm(id,s.plateLabel);root.appendChild(n);}
}
function nav(){return `<nav class="journal-tabs" aria-label="식사와 성장에서 볼 곳">${[['nutrition','영양'],['book','도감'],['rewards','꾸밈'],['backup','백업']].map(([id,label])=>`<button type="button" data-journal="${id}" aria-pressed="${tab===id}">${label}</button>`).join('')}</nav>`;}
function show(next=tab){tab=next;const titles={nutrition:'내 식사와 영양',book:'나의 요리 도감',rewards:'부엌을 꾸미는 보상',backup:'이 시안의 기록 보관'};K.showTray(titles[tab],nav()+({nutrition:nutrition,book:book,rewards:rewards,backup:backup}[tab])(),'MY KITCHEN JOURNAL');window.KitchenWorkflows?.enhanceJournal(tab);}
function fields(values={},targets=false){return `<div class="journal-fields">${keys.map(k=>{const [name,unit]=M.NUTRIENTS[k];return `<label>${name} <small>${unit}</small><input name="${k}" type="number" step="any" min="${targets?'0.01':'0'}" max="100000" value="${values[k]??''}" placeholder="${targets?'미설정':'미입력'}"></label>`;}).join('')}</div>`;}
function nutrition(){
 const r=model.summary(viewDay),s=model.state();return `<div class="journal-day"><label>살펴볼 날짜<input type="date" id="journalDay" value="${viewDay}" required></label><button type="button" class="small-action primary" data-log>식사 기록</button></div><p class="journal-note">먹은 분량의 영양값을 직접 입력해요. 빈칸은 미입력으로 남고, 목표는 직접 정할 수 있어요.</p><div class="nutrient-gauges">${keys.map(k=>{const n=r.nutrients[k],[name,unit]=M.NUTRIENTS[k],percent=n.percent===null?0:Math.min(100,n.percent);return `<section class="nutrient-gauge" data-nutrient="${k}"><span>${name}</span><strong>${n.value===null?'미입력':number(n.value)+' <small>'+unit+'</small>'}</strong><div class="gauge-track" ${n.percent!==null?'role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+number(percent)+'" aria-label="'+name+' 목표 대비"':''}><i style="width:${percent}%"></i></div><small>${n.target===null?'목표 미설정':n.percent===null?'목표 '+n.target+' '+unit:Math.round(n.percent)+'% · 목표 '+n.target+' '+unit}${n.missing?' · '+n.missing+'건 미입력':''}</small></section>`;}).join('')}</div><details class="journal-section"><summary>하루 목표 설정</summary><form id="targetsForm">${fields(s.targets,true)}<button class="small-action primary" type="submit">목표 저장</button></form></details><section class="journal-section"><div class="journal-heading"><h3>기록한 식사</h3><button class="small-action" type="button" data-undo-meal>취소 복구</button></div>${r.rows.length?r.rows.map(m=>`<article class="journal-meal"><div><strong>${esc(m.name)}</strong><small>${esc(m.portion||'먹은 분량 메모 없음')} · 직접 입력</small></div><button type="button" data-wf="editMeal" data-arg="${esc(m.id)}">수정</button><button type="button" data-remove-meal="${esc(m.id)}">기록 취소</button></article>`).join(''):'<p class="journal-empty">아직 기록이 없어요. 실제로 먹은 한 끼부터 남겨 보세요.</p>'}</section><div class="journal-feedback" role="status"></div>`;
}
function book(){
 const s=model.state(),r=model.summary(today());return `<div class="journal-heading"><p><strong>${r.cooked.length} / ${C.length}</strong> 요리 기록</p><p>꾸밈권 <strong>${r.tickets}</strong></p></div><p class="journal-note">새 요리를 처음 식사로 기록하면 도감이 채워지고 꾸밈권 1개를 받아요. 재료와 조리법은 지금부터 볼 수 있어요.</p><section class="goal-card"><label>내가 고르는 목표<select id="journalGoal">${[['collection','요리 도감 3장 채우기'],['recording','오늘 식사 한 끼 기록하기'],['nutrition','먹은 분량의 탄단지 기록하기']].map(([key,label])=>`<option value="${key}" ${key===s.goal?'selected':''}>${label}</option>`).join('')}</select></label><strong>${r.goal.value}/${r.goal.target}${r.goal.value===r.goal.target?' · 달성했어요':''}</strong></section><div class="recipe-book">${C.map(recipe=>{const count=s.meals.filter(m=>m.recipeId===recipe.id).length,discovered=s.discovered.includes(recipe.id);return `<button type="button" data-book-recipe="${recipe.id}" class="book-card ${count?'is-cooked':''}"><span class="book-art ${count?'':'not-cooked'}">${A.dishArt({id:recipe.name})}</span><strong>${esc(recipe.name)}</strong><small>${count?'요리 기록 '+count+'회':discovered?'발견했어요 · 첫 요리 기다리는 중':'살펴볼 수 있어요'}</small><span class="book-stamp">${count?'도감 등록':recipe.time}</span></button>`;}).join('')}</div>`;
}
function detail(id){if(window.KitchenWorkflows)return window.KitchenWorkflows.recipe(id);const recipe=find(id);if(!recipe)return;model.discover(id);save();K.showTray(recipe.name,`<div class="journal-recipe-art">${A.dishArt({id:recipe.name})}</div><p class="journal-note">${esc(recipe.desc)} · ${esc(recipe.time)}</p><h3>재료</h3><dl class="recipe-amounts">${Object.entries(recipe.amounts).map(([name,amount])=>`<div><dt>${esc(name)}</dt><dd>${esc(amount)}</dd></div>`).join('')}</dl>${recipe.water?'<p class="journal-note">'+esc(recipe.water)+'</p>':''}<h3>만드는 순서</h3><ol class="recipe-steps">${recipe.steps.map(step=>`<li>${esc(step)}</li>`).join('')}</ol><div class="tray-actions"><button type="button" class="small-action" data-preview-recipe="${id}">조리대에 놓기</button><button type="button" class="small-action primary" data-log="${id}">먹은 식사 기록</button></div>`,'MY RECIPE BOOK');}
function logForm(recipeId=null){
 if(window.KitchenWorkflows)return window.KitchenWorkflows.logMeal(recipeId);
 const recipe=find(recipeId),chosen=recipeId||'';K.showTray('먹은 한 끼를 기록해요',`<form id="mealForm"><div class="journal-fields"><label>날짜<input type="date" name="day" value="${viewDay}" required></label><label>도감에 연결할 요리<select name="recipeId"><option value="">직접 입력한 식사</option>${C.map(r=>`<option value="${r.id}" ${r.id===chosen?'selected':''}>${esc(r.name)}</option>`).join('')}</select></label><label>식사 이름<input name="name" value="${esc(recipe?.name||'')}" required maxlength="120" placeholder="먹은 음식"></label><label>먹은 분량 메모<input name="portion" maxlength="80" placeholder="예: 반 공기, 1인분"></label></div><h3 class="journal-subtitle">먹은 분량 전체의 영양값</h3><p class="journal-note">제품 영양표나 확인한 자료를 보고 입력하세요. 레시피에서 영양값을 자동 추정하지 않아요. 모르는 값은 비워 두어도 식사를 기록할 수 있어요.</p>${fields()}<button type="submit" class="small-action primary">식사 기록하기</button><div class="journal-feedback" role="status"></div></form>`,'MY MEAL');
}
function rewards(){
 const s=model.state(),r=model.summary(today());return `<div class="journal-heading"><strong>꾸밈권 ${r.tickets}개</strong><span>소품 ${s.owned.length} / ${Object.keys(M.REWARDS).length}</span></div><p class="journal-note">처음 기록한 서로 다른 요리마다 꾸밈권 1개를 받아요. 같은 요리는 다시 지급되지 않고, 기록을 취소해도 받은 꾸밈권은 유지돼요.</p><label class="journal-select">붙일 곳<select id="rewardSlot"><option value="frozenLeft" ${slot==='frozenLeft'?'selected':''}>냉동 왼쪽 문</option><option value="frozenRight" ${slot==='frozenRight'?'selected':''}>냉동 오른쪽 문</option></select></label><div class="reward-catalog">${Object.entries(M.REWARDS).map(([id,reward])=>{const owned=s.owned.includes(id),equipped=s.equipped[slot]===id;return `<article class="reward-card"><span class="reward-art">${charm(id,s.plateLabel)}</span><strong>${reward.name}</strong><small>${owned?'가지고 있어요':'꾸밈권 '+reward.cost+'개'}</small><button type="button" class="small-action ${owned?'':'primary'}" ${!owned&&r.tickets<reward.cost?'disabled':''} data-reward="${id}">${equipped?'붙여 두었어요':owned?'여기에 붙이기':'선택해서 받기'}</button></article>`;}).join('')}</div>${s.owned.includes('plate')?`<form id="plateForm" class="journal-section"><label>이름표 문구<input name="label" value="${esc(s.plateLabel)}" maxlength="12" required></label><button class="small-action" type="submit">문구 바꾸기</button></form>`:''}<button type="button" class="small-action" data-clear-charm>선택한 문의 소품 떼기</button><button type="button" class="small-action primary" data-see-fridge>냉장고에서 보기</button><div class="journal-feedback" role="status"></div>`;
}
function backup(){return `<p class="journal-note">이 시안의 재료·문 상태·식사·영양 목표·도감·소품을 함께 보관해요. 기존 앱 기록은 읽거나 변경하지 않아요.</p><p class="journal-save-status">${statusText()}</p><label class="journal-select">복사해서 보관할 기록<textarea id="journalExport" rows="5" readonly>${esc(JSON.stringify(envelope(),null,2))}</textarea></label>${originalRaw?'<details class="journal-section"><summary>읽지 못한 이전 원본 보관</summary><textarea rows="4" readonly>'+esc(originalRaw)+'</textarea></details>':''}<form id="importForm" class="journal-section"><label>이 시안의 백업 붙여넣기<textarea name="backup" rows="5" required></textarea></label><p class="journal-note">형식을 확인한 뒤 이 시안의 현재 기록을 교체해요. 읽기 오류나 다른 화면과 충돌이 있으면 원본 저장은 유지하고 임시로 불러와요.</p><button class="small-action primary" type="submit">이 기록 불러오기</button><div class="journal-feedback" role="status"></div></form>`;}
function feedback(message){const node=$('#trayContent .journal-feedback');if(node)node.textContent=message;else $('#liveMessage').textContent=message;}
function inputNumbers(form){return Object.fromEntries(keys.map(k=>[k,form.get(k)===''?null:Number(form.get(k))]));}
document.addEventListener('click',event=>{const b=event.target.closest('button');if(!b)return;try{
 if(b.id==='openJournal'){if(window.KitchenWorkflows)window.KitchenWorkflows.selectedAction();else show('nutrition');}if(b.dataset.journal)show(b.dataset.journal);
 if(b.dataset.bookRecipe)detail(b.dataset.bookRecipe);
 if(b.hasAttribute('data-log'))logForm(b.dataset.log||null);
 if(b.dataset.previewRecipe)K.chooseRecipe(find(b.dataset.previewRecipe).name);
 if(b.dataset.removeMeal){if(window.KitchenWorkflows)window.KitchenWorkflows.cancelMeal(b.dataset.removeMeal);else{model.remove(b.dataset.removeMeal);save();show('nutrition');feedback('기록을 취소했어요. 영양 합계도 다시 계산했어요.');}}
 if(b.hasAttribute('data-undo-meal')){if(window.KitchenWorkflows){window.KitchenWorkflows.undoMeal();return;}if(model.undo()){save();show('nutrition');feedback('방금 취소한 기록을 복구했어요.');}else feedback('복구할 취소 기록이 없어요.');}
 if(b.dataset.reward){const received=model.buy(b.dataset.reward);model.equip(slot,b.dataset.reward);save();show('rewards');feedback(received?'소품을 받았어요. 냉장고에 붙여 두었어요.':'선택한 문에 붙였어요.');}
 if(b.hasAttribute('data-clear-charm')){model.equip(slot,null);save();show('rewards');}
 if(b.hasAttribute('data-see-fridge')){document.querySelector('.camera-tabs [data-camera="fridge"]').click();K.closeTray();}
}catch(e){feedback(e.message);}});
document.addEventListener('change',event=>{try{const e=event.target;if(e.id==='journalDay'&&M.day(e.value)){viewDay=e.value;show('nutrition');}if(e.id==='journalGoal'){model.setGoal(e.value);save();show('book');}if(e.id==='rewardSlot'){slot=e.value;show('rewards');}if(e.name==='recipeId'&&e.closest('#mealForm')){const r=find(e.value);if(r)$('#mealForm [name="name"]').value=r.name;}}catch(e){feedback(e.message);}});
document.addEventListener('submit',event=>{const form=event.target;if(!['mealForm','targetsForm','plateForm','importForm'].includes(form.id))return;event.preventDefault();const f=new FormData(form);try{
 if(form.id==='mealForm'){const result=model.record({day:f.get('day'),name:f.get('name'),portion:f.get('portion'),recipeId:f.get('recipeId')||null,nutrients:inputNumbers(f)});viewDay=f.get('day');save();show('nutrition');feedback(result.earned?'식사를 기록했어요. 도감이 채워지고 꾸밈권 1개를 받았어요.':'식사를 기록했어요.');}
 if(form.id==='targetsForm'){model.setTargets(inputNumbers(f));save();show('nutrition');feedback('직접 정한 목표를 저장했어요.');}
 if(form.id==='plateForm'){model.setLabel(f.get('label'));save();show('rewards');}
 if(form.id==='importForm'){if(window.KitchenWorkflows){window.KitchenWorkflows.previewImport(f.get('backup'));return;}const data=JSON.parse(f.get('backup'));if(!validEnvelope(data))throw new Error('이 시안의 올바른 백업 형식인지 확인해 주세요. 원본은 변경하지 않았어요.');loading=true;model=M.create(ids,data.play);K.restoreWorld(data.world);loading=false;save();show('backup');feedback('백업을 불러왔어요.');}
}catch(e){loading=false;feedback(e instanceof SyntaxError?'백업 JSON을 읽을 수 없어요. 현재 기록은 유지돼요.':e.message);}});
window.addEventListener('mini-kitchen:change',()=>{if(!loading)save();});
window.addEventListener('mini-kitchen:layout',updateDecorations);
window.addEventListener('mini-kitchen:recipe',event=>{const recipe=C.find(r=>r.name===event.detail.name);if(recipe){model.discover(recipe.id);save();}});
window.addEventListener('storage',event=>{if(event.key===KEY&&event.newValue!==lastRaw){blocked=true;status='conflict';update();}});
window.addEventListener('pageshow',update);
function transact(mutator){
 const nextPlay=M.create(ids,model.state()),nextWorld=K.exportWorld(),nextFlow=F.create(workflow);
 const result=mutator({world:nextWorld,play:nextPlay,flow:nextFlow});
 const candidate={version:1,world:nextWorld,play:nextPlay.state(),workflow:nextFlow};
 if(!validEnvelope(candidate))throw new Error('입력한 기록을 확인해 주세요. 이전 기록은 유지돼요.');
 const previous={model,workflow,world:K.exportWorld()};
 try{loading=true;model=nextPlay;workflow=nextFlow;K.restoreWorld(nextWorld,true);}catch(e){model=previous.model;workflow=previous.workflow;K.restoreWorld(previous.world,true);throw e;}finally{loading=false;}
 save();return result;
}
function replaceEnvelope(data){
 if(!validEnvelope(data))throw new Error('올바른 백업 형식인지 확인해 주세요.');
 const previous=JSON.stringify(envelope());
 if(storage&&!blocked){const raw=storage.getItem(KEY);if(raw!==lastRaw){blocked=true;status='conflict';update();throw new Error('다른 화면에서 기록이 바뀌었어요. 현재 기록을 다시 열어 확인해 주세요.');}if(raw!==null)storage.setItem(KEY+'-recovery',raw);}
 recoveryRaw=previous;loading=true;
 try{model=M.create(ids,data.play);workflow=F.create(data.workflow);envelopeExtra={...data};K.restoreWorld(data.world);}finally{loading=false;}
 save();return true;
}
window.KitchenJournal=Object.freeze({getSnapshot:()=>model.state(),summary:date=>model.summary(date||today()),getWorkflow:()=>JSON.parse(JSON.stringify(workflow)),getEnvelope:()=>JSON.parse(JSON.stringify(envelope())),transact,replaceEnvelope,validEnvelope,show,showLog:logForm,refresh:update,discover(id){model.discover(id);save();},get recovery(){return recoveryRaw||originalRaw;},get status(){return status;},storageKey:KEY});
update();
})();
