/* Inventory controls and synchronization. All changes commit through UMFStore. */
(()=>{
  'use strict';
  const store=window.UMFStore, domain=window.UMFDomain;
  if(!store||!domain)return;
  const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
  const BASE_S=['소금','후추','식용유','간장','진간장','국간장','설탕','식초','참기름','들기름','고춧가루','고추장','된장','쌈장','다진마늘','굴소스','맛술','액젓','멸치액젓','참치액','올리고당','물엿','케첩','마요네즈'];
  const BASE_P=['밥/즉석밥','김','참치캔','면/라면','식빵','김가루'];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const uniq=a=>[...new Set(a)];
  let showAll=true,editingId=null,editingOriginal=null,previousFocus=null,modalVersion=0,savingItem=false,savingCustom=false;
  function icon(n){
    const art=window.UMFKitchenArt;
    if(art?.foodArt&&art?.foodIdForName)return art.foodArt(art.foodIdForName(n));
    if(/두부/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M6 8.5 12 5l6 3.5v7L12 19l-6-3.5v-7Z" fill="#FFF1CE" stroke="#C7A257" stroke-width="1.5"/><path d="m6 8.5 6 3.4 6-3.4M12 11.9V19" stroke="#D8B66E" stroke-width="1.2"/></svg>';
    if(/시금치|상추|배추|달래|깻잎/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M18.5 5.5c-5.8.2-9.4 2.5-10.5 6.8-.8 3 1 5.6 4.1 5.8 4.8.2 7.4-3.8 6.4-12.6Z" fill="#C5E2BD" stroke="#6D9968" stroke-width="1.4"/><path d="M8.6 16.8c2.1-3 4.6-5.1 7.7-6.7" stroke="#6D9968" stroke-width="1.3" stroke-linecap="round"/></svg>';
    if(/애호박|호박/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M5 14c2.5-5 8.8-7.2 14-4.4-2 5.7-8.5 8.1-14 4.4Z" fill="#B8D98C" stroke="#6A9A50" stroke-width="1.4"/><path d="M6.5 13.6c3.2-.5 6.4-1.4 10.3-3.3" stroke="#6A9A50" stroke-width="1.1" stroke-linecap="round"/></svg>';
    if(/닭/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M10 8c2.8-1.4 6 .1 7.1 2.9 1.1 2.8-.1 6-2.8 7.1-2.7 1.1-5.8-.1-7-2.7-.6-1.3-.7-2.3-.5-3.7.2-1.3 1.5-2.9 3.2-3.6Z" fill="#F3C3B4" stroke="#BC745B" stroke-width="1.4"/><circle cx="7" cy="16.4" r="1.5" fill="#FFF7F2" stroke="#BC745B" stroke-width="1.1"/></svg>';
    if(/김치/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M6 15c3-5 8-7 12-7-1.2 3.5-3.3 6.7-6.9 8.6-2 .9-3.6.5-5.1-1.6Z" fill="#F2A164" stroke="#D16F47" stroke-width="1.4"/><path d="M8 14.5c2.6-2.2 5.3-3.6 8.4-4.4" stroke="#D16F47" stroke-width="1.1" stroke-linecap="round"/></svg>';
    if(/우유|요거트|요구르트/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M10 4h4l1 2.4V18a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2V6.4L10 4Z" fill="#DDF1F4" stroke="#72A4A7" stroke-width="1.4"/><path d="M10 8h5" stroke="#72A4A7" stroke-linecap="round"/></svg>';
    if(/양파/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M12 5c1.3 1.1 4.8 4.1 4.8 8a4.8 4.8 0 1 1-9.6 0C7.2 9 10.7 6 12 5Z" fill="#F0DCC1" stroke="#B58D64" stroke-width="1.4"/><path d="M12 6.2V18" stroke="#C9A176" stroke-width="1.1"/></svg>';
    if(/계란|달걀/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M12 5.2c3 0 5.5 3.8 5.5 7.7a5.5 5.5 0 1 1-11 0c0-3.9 2.5-7.7 5.5-7.7Z" fill="#FFF0C6" stroke="#CFA45B" stroke-width="1.4"/></svg>';
    return'<svg viewBox="0 0 24 24" fill="none"><path d="M5.5 10.5h13l-1.1 6.4a2 2 0 0 1-2 1.6H8.6a2 2 0 0 1-2-1.6l-1.1-6.4Z" fill="#ECEDE7" stroke="#7D857D" stroke-width="1.4"/></svg>';
  }

  function storageStatus(){
    const el=$('#umfStorageStatus');if(!el)return;
    el.textContent=store.error;el.hidden=!store.error;el.classList.toggle('bad',!!store.error);
  }
  function renderItems(){
    const state=store.getState(),box=$('#list');if(!box)return;
    const items=[...state.items].sort((a,b)=>(domain.daysLeft(a.expiry)??Infinity)-(domain.daysLeft(b.expiry)??Infinity)||a.name.localeCompare(b.name,'ko'));
    const shown=showAll?items:items.slice(0,6);box.replaceChildren();
    if(!items.length)box.innerHTML='<div class="empty">재료를 추가하면 내 냉장고에 맞는 메뉴를 찾아드려요.</div>';
    for(const item of shown){
      const d=domain.daysLeft(item.expiry),q=domain.parseQuantity(item.quantity),row=document.createElement('div');
      const status=q.empty?'소진':d===null?(item.expiry?'기한 확인':'미입력'):d<0?'기한 경과':d===0?'오늘':`D-${d}`;
      const cls=q.empty||d<0?'v10-urgent':d===0?'v10-today':d!==null&&d<=2?'v10-urgent':d===null?'umf-unknown':'v10-safe';
      const details=[item.quantity||'수량 미입력',d===null?(item.expiry?'기한 형식 확인':'기한 미입력'):item.expiry.replaceAll('-','.')+'까지'];
      row.className='row';row.dataset.id=item.id;row.dataset.expired=String(d!==null&&d<0);row.dataset.empty=String(q.empty);
      row.innerHTML=`<div class="ic" aria-hidden="true">${icon(item.name)}</div><div class="umf-row-copy"><div class="nm" title="${esc(item.name)}">${esc(item.name)}</div><div class="ex">${esc(details.join(' · '))}</div></div><div class="day ${cls}" title="${esc(d!==null&&d<0?`입력한 기한에서 ${-d}일 지남 · 추천 제외`:status)}">${esc(status)}</div><button type="button" class="rm" aria-label="${esc(item.name)} 재료 메뉴" aria-expanded="false">⋮</button>`;
      const menuButton=row.querySelector('.rm');
      menuButton.onclick=event=>{
        event.stopPropagation();const had=!!row.querySelector('.umf-row-menu');closeRowMenus();if(had)return;
        const menu=document.createElement('div');menu.className='umf-row-menu';
        menu.innerHTML=`<button type="button" data-action="edit" aria-label="${esc(item.name)} 수정">수정</button><button type="button" data-action="remove" aria-label="${esc(item.name)} 삭제">삭제</button>`;
        menu.querySelector('[data-action="edit"]').onclick=()=>openEdit(item.id);
        menu.querySelector('[data-action="remove"]').onclick=()=>store.updateAsync(s=>{s.items=s.items.filter(x=>x.id!==item.id)});
        row.appendChild(menu);menuButton.setAttribute('aria-expanded','true');
      };
      box.appendChild(row);
    }
    if($('#fc'))$('#fc').textContent=state.items.length;
    if($('#sum'))$('#sum').textContent=`재료 ${state.items.length}개`;
    const all=$('#all');if(all){all.hidden=items.length<=6;all.textContent=showAll?'접기':'전체 보기';all.setAttribute('aria-expanded',String(showAll));}
  }
  function closeRowMenus(){ $$('.umf-row-menu').forEach(x=>x.remove()); $$('.rm[aria-expanded]').forEach(x=>x.setAttribute('aria-expanded','false')); }
  function grid(names,selected,custom,selector,field,customField){
    const box=$(selector);if(!box)return;box.replaceChildren();
    for(const name of names){
      const wrap=document.createElement('div');wrap.className='umf-toggle-wrap';
      const button=document.createElement('button');button.type='button';button.className='tog'+(selected.includes(name)?' on':'');
      button.textContent=(selected.includes(name)?'✓ ':'')+name;button.setAttribute('aria-pressed',String(selected.includes(name)));
      button.onclick=()=>store.updateAsync(s=>{s[field]=s[field].includes(name)?s[field].filter(x=>x!==name):[...s[field],name]});wrap.appendChild(button);
      if(custom.includes(name)){
        const remove=document.createElement('button');remove.type='button';remove.className='umf-custom-remove';remove.textContent='×';remove.setAttribute('aria-label',name+' 항목 삭제');
        remove.onclick=()=>store.updateAsync(s=>{s[customField]=s[customField].filter(x=>x!==name);s[field]=s[field].filter(x=>x!==name)});wrap.appendChild(remove);
      }
      box.appendChild(wrap);
    }
  }
  function renderSets(){const s=store.getState();grid(uniq([...BASE_S,...s.customSeason,...s.season]),s.season,s.customSeason,'#sg','season','customSeason');grid(uniq([...BASE_P,...s.customPantry,...s.pantry]),s.pantry,s.customPantry,'#pg','pantry','customPantry');if($('#sc'))$('#sc').textContent=s.season.length+s.pantry.length;}
  function render(){renderItems();renderSets();storageStatus();}
  function openModal(selector,focusSelector){
    const modal=$(selector);if(!modal)return;modalVersion++;previousFocus=document.activeElement;modal.classList.add('on');
    modal.querySelector('.modal')?.setAttribute('role','dialog');modal.querySelector('.modal')?.setAttribute('aria-modal','true');
    $(focusSelector)?.focus();
  }
  function closeModal(selector){modalVersion++;$(selector)?.classList.remove('on');if(previousFocus?.isConnected)previousFocus.focus();}
  function formError(message){const el=$('#umfFormError');if(el){el.textContent=message;el.hidden=!message;}}
  function openAdd(name='',kind='fridge'){
    if(kind==='season'||kind==='pantry'){openCustom(kind,name);return;}
    editingId=null;editingOriginal=null;formError('');
    if($('#name'))$('#name').value=name;if($('#expiry'))$('#expiry').value='';if($('#umfQty'))$('#umfQty').value='';
    const title=$('#mb .mh b');if(title)title.textContent='재료 추가';if($('#save'))$('#save').textContent='추가하기';
    openModal('#mb','#name');
  }
  function openEdit(id){
    const item=store.getState().items.find(x=>x.id===id);if(!item)return;
    closeRowMenus();editingId=id;editingOriginal=JSON.stringify(item);formError('');if($('#name'))$('#name').value=item.name;if($('#expiry'))$('#expiry').value=item.expiry;if($('#umfQty'))$('#umfQty').value=item.quantity;
    const title=$('#mb .mh b');if(title)title.textContent='재료 수정';if($('#save'))$('#save').textContent='수정 저장';openModal('#mb','#name');
  }
  async function saveItem(){
    if(savingItem)return;
    const name=$('#name')?.value.normalize('NFKC').trim()||'',expiry=$('#expiry')?.value||'',quantity=$('#umfQty')?.value.trim()||'';
    if(!name){formError('재료명을 입력해 주세요.');$('#name')?.focus();return;}
    if(name.length>60){formError('재료명은 60자 이내로 입력해 주세요.');return;}
    if(quantity.length>40){formError('수량은 40자 이내로 입력해 주세요.');return;}
    if(expiry&&domain.daysLeft(expiry)===null){formError('소비 기한을 올바른 날짜로 입력해 주세요.');return;}
    if(/^\s*-\d/.test(quantity)){formError('수량은 0 이상으로 입력해 주세요.');return;}
    const editId=editingId,original=editingOriginal,id=editId||store.newId(),opened=modalVersion;let exists=true,conflict=false;
    savingItem=true;if($('#save'))$('#save').disabled=true;
    try{
      const ok=await store.updateAsync(s=>{if(editId){const index=s.items.findIndex(x=>x.id===editId);if(index<0){exists=false;return;}if(JSON.stringify(s.items[index])!==original){conflict=true;return;}s.items[index]={id,name,expiry,quantity};}else s.items.push({id,name,expiry,quantity});});
      if(opened!==modalVersion)return;
      if(!exists){formError('이 재료는 다른 화면에서 삭제됐어요. 다시 추가해 주세요.');return;}
      if(conflict){formError('이 재료가 다른 화면에서 수정됐어요. 창을 닫고 최신 내용을 확인한 뒤 다시 수정해 주세요.');return;}
      if(!ok){formError(store.error||'저장하지 못했어요. 다시 확인해 주세요.');return;}
      editingId=null;editingOriginal=null;closeModal('#mb');
    }finally{savingItem=false;if($('#save'))$('#save').disabled=false;}
  }
  function openCustom(type,name=''){
    if($('#customType'))$('#customType').value=type;if($('#customName'))$('#customName').value=name;
    if($('#customTitle'))$('#customTitle').textContent=type==='season'?'기본 양념 보유 등록':'상비 재료 보유 등록';
    if($('#customSave'))$('#customSave').textContent='보유한 재료로 체크';
    const error=$('#umfCustomError');if(error){error.textContent='';error.hidden=true;}
    openModal('#customModal','#customName');
  }
  async function saveCustom(){
    if(savingCustom)return;
    const type=$('#customType')?.value==='pantry'?'pantry':'season',name=$('#customName')?.value.normalize('NFKC').trim()||'';
    if(!name||name.length>60){const error=$('#umfCustomError');if(error){error.textContent='이름을 1~60자로 입력해 주세요.';error.hidden=false;}else $('#customName')?.focus();return;}
    const base=type==='season'?BASE_S:BASE_P,key=type==='season'?'customSeason':'customPantry';
    const opened=modalVersion;savingCustom=true;if($('#customSave'))$('#customSave').disabled=true;
    try{
      if(await store.updateAsync(s=>{if(!base.includes(name)&&!s[key].includes(name))s[key].push(name);if(!s[type].includes(name))s[type].push(name);})){
        if(opened===modalVersion)closeModal('#customModal');
      }
    }finally{savingCustom=false;if($('#customSave'))$('#customSave').disabled=false;}
  }
  const sync=store.createSyncEngine({
    store,fetch:(...args)=>fetch(...args),url:'https://dfklyngtjqvlirgrtdfb.supabase.co/functions/v1/use-me-first-sync',crypto:window.crypto,
    confirm:message=>window.confirm(message),
    onStatus:status=>{
      for(const selector of ['#syncStatus','#syncFeedback']){const el=$(selector);if(el){el.textContent=status.text;el.dataset.syncState=status.state;el.classList.toggle('bad',status.state==='error'||status.state==='conflict');}}
      for(const selector of ['#syncCreate','#syncConnect','#syncDisconnect','#syncUpload','#syncReload','#syncRestore']){const el=$(selector);if(el)el.disabled=status.busy;}
      const button=$('#syncBtn'),dot=$('#syncDot');if(button){button.title=status.text;button.setAttribute('aria-label',sync?.code?'동기화 관리':'동기화 설정');}
      if(dot){dot.classList.toggle('on',status.state==='ready');dot.classList.toggle('bad',status.state==='error'||status.state==='conflict');}
    }
  });
  function openSync(){
    if($('#syncCode'))$('#syncCode').value=sync.code;
    const help=$('#syncHelp');if(help)help.textContent='재료·수량·양념·식사 기록·즐겨찾기를 함께 동기화합니다. 첫 기기는 새 코드를 만들고, 다른 기기는 같은 코드를 입력하세요. 두 기기를 동시에 편집하면 동기화 전 확인이 필요할 수 있어요.';
    if($('#syncRestore'))$('#syncRestore').hidden=!store.recovery();
    openModal('#syncModal','#syncCode');
  }
  async function syncAction(action){const ok=await action();if($('#syncCode')&&ok)$('#syncCode').value=sync.code;if($('#syncRestore'))$('#syncRestore').hidden=!store.recovery();storageStatus();}
  $('.tabs')?.addEventListener('click',e=>{const b=e.target.closest('.tab');if(!b)return;$$('.tab').forEach(x=>{x.classList.toggle('on',x===b);x.setAttribute('aria-selected',String(x===b));});$('#fridge')?.classList.toggle('on',b.dataset.tab==='fridge');$('#season')?.classList.toggle('on',b.dataset.tab==='season');});
  $('#all')?.addEventListener('click',()=>{showAll=!showAll;renderItems();});
  $('#openAdd')?.addEventListener('click',()=>openAdd());
  $('#close')?.addEventListener('click',()=>closeModal('#mb'));$('#cancel')?.addEventListener('click',()=>closeModal('#mb'));$('#save')?.addEventListener('click',saveItem);
  for(const selector of ['#name','#umfQty','#expiry'])$(selector)?.addEventListener('keydown',e=>{if(e.isComposing||e.keyCode===229)return;if(e.key==='Enter'){e.preventDefault();saveItem();}});
  $('#addSeason')?.addEventListener('click',()=>openCustom('season'));$('#addPantry')?.addEventListener('click',()=>openCustom('pantry'));
  $('#customClose')?.addEventListener('click',()=>closeModal('#customModal'));$('#customCancel')?.addEventListener('click',()=>closeModal('#customModal'));$('#customSave')?.addEventListener('click',saveCustom);$('#customName')?.addEventListener('keydown',e=>{if(e.isComposing||e.keyCode===229)return;if(e.key==='Enter'){e.preventDefault();saveCustom();}});
  $('#syncBtn')?.addEventListener('click',openSync);$('#syncClose')?.addEventListener('click',()=>closeModal('#syncModal'));
  $('#syncCreate')?.addEventListener('click',()=>syncAction(()=>sync.create()));$('#syncConnect')?.addEventListener('click',()=>syncAction(()=>sync.connect($('#syncCode')?.value)));
  $('#syncUpload')?.addEventListener('click',()=>syncAction(()=>sync.upload()));$('#syncReload')?.addEventListener('click',()=>syncAction(()=>sync.reload()));$('#syncRestore')?.addEventListener('click',()=>syncAction(()=>sync.restore()));
  $('#syncDisconnect')?.addEventListener('click',()=>syncAction(()=>sync.disconnect()));
  $('#syncCopy')?.addEventListener('click',async()=>{const value=$('#syncCode')?.value;if(!value)return;try{await navigator.clipboard.writeText(value);$('#syncHelp').textContent='코드를 복사했어요.';}catch{$('#syncHelp').textContent='코드를 직접 선택해 복사해 주세요.';}});
  document.addEventListener('click',e=>{if(!e.target.closest('.rm,.umf-row-menu'))closeRowMenus();if(e.target.classList.contains('modalbg'))closeModal('#'+e.target.id);});
  document.addEventListener('keydown',e=>{
    const modal=$('.modalbg.on');if(!modal)return;
    if(e.key==='Escape'){closeModal('#'+modal.id);e.preventDefault();return;}
    if(e.key==='Tab'){
      const inputs=[...modal.querySelectorAll('button:not([disabled]),input:not([type="hidden"]),select,textarea,[tabindex="0"]')].filter(x=>!x.hidden&&x.getClientRects().length);
      if(!inputs.length)return;const first=inputs[0],last=inputs[inputs.length-1];
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
    }
  });
  store.subscribe(render);window.addEventListener('umf:storageerror',storageStatus);
  window.addEventListener('online',()=>sync.retry());window.addEventListener('storage',e=>{if(e.key===store.keys.SYNC||e.key===null)sync.connectionChanged();});
  window.addEventListener('umf:daychange',render);document.addEventListener('visibilitychange',()=>{if(!document.hidden)render();});
  window.UMFCore={openAdd,openEdit,icon,render,sync};
  render();sync.initialize();
})();
