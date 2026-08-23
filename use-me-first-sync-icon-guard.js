(()=>{
  // Final layout repair: keep all inventory controls in one left stack so the
  // tall recipe panel can never stretch the header/tabs apart.
  const w=document.querySelector('.w');
  if(w&&!w.querySelector(':scope > .umf-left')){
    const head=w.querySelector(':scope > .head');
    const tabs=w.querySelector(':scope > .tabs');
    const fridge=w.querySelector(':scope > #fridge');
    const season=w.querySelector(':scope > #season');
    const recipe=w.querySelector(':scope > .recipeSec');
    if(head&&tabs&&fridge&&season&&recipe){
      const left=document.createElement('div');
      left.className='umf-left';
      left.append(head,tabs,fridge,season);
      w.insertBefore(left,recipe);
      w.classList.add('umf-wide-layout');
    }
  }else if(w){
    w.classList.add('umf-wide-layout');
  }

  // The inline AI image helper used to load before the menu cards existed.
  // Load it once more after the recipe grid has rendered so cards 5–8 are
  // patched with their generated food photos instead of showing a broken state.
  setTimeout(()=>{
    if(document.getElementById('umfRecipeGrid')){
      const s=document.createElement('script');
      s.src='use-me-first-ai-inline-v2.js?v=3';
      s.async=true;
      document.head.appendChild(s);
    }
  },350);

  const btn=document.getElementById('syncBtn');
  if(!btn) return;
  const status=document.getElementById('syncStatus');
  const SYNC_KEY='use-me-first-sync-code-v1';
  const ICON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h11"/><path d="m12 4 3 3-3 3"/><path d="M20 17H9"/><path d="m12 14-3 3 3 3"/></svg>';
  let repairing=false;
  const connected=()=>!!localStorage.getItem(SYNC_KEY);
  const hasRealError=()=>/실패|오류|error/i.test((status?.textContent||'').trim());

  function repairSyncButton(){
    if(repairing) return;
    repairing=true;
    const isConnected=connected(),bad=hasRealError();
    const tip=isConnected?'동기화 관리':'동기화 설정';
    btn.dataset.tip=tip;
    btn.setAttribute('aria-label',tip);
    [...btn.childNodes].forEach(node=>{if(node.nodeType===Node.TEXT_NODE)node.remove()});
    if(!btn.querySelector('svg'))btn.insertAdjacentHTML('afterbegin',ICON);
    let dot=btn.querySelector('.syncDot');
    if(!dot){dot=document.createElement('i');dot.className='syncDot';dot.id='syncDot';btn.appendChild(dot)}
    if(status)status.classList.toggle('bad',bad);
    dot.classList.toggle('bad',bad);
    dot.classList.toggle('on',isConnected&&!bad);
    repairing=false;
  }

  try{
    window.renderSyncStatus=function(){
      if(status){status.textContent=connected()?'이 기기는 동기화 연결됨':'이 기기는 아직 로컬 저장만 사용 중';status.classList.remove('bad')}
      repairSyncButton();
    };
  }catch(e){}

  new MutationObserver(()=>queueMicrotask(repairSyncButton)).observe(btn,{childList:true,subtree:true,characterData:true});
  if(status)new MutationObserver(()=>queueMicrotask(repairSyncButton)).observe(status,{attributes:true,childList:true,characterData:true});
  window.addEventListener('storage',e=>{if(e.key===SYNC_KEY)repairSyncButton()});
  repairSyncButton();
})();
