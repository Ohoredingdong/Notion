(()=>{
  // Force the corrected wide stylesheet. The page was still loading v3,
  // so the .umf-wide-layout/.umf-left rules never actually took effect.
  document.querySelectorAll('link[href*="use-me-first-horizontal-v3.css"]').forEach(link=>{link.disabled=true});
  if(!document.querySelector('link[href*="use-me-first-horizontal-v4.css"]')){
    const link=document.createElement('link');
    link.rel='stylesheet';
    link.href='use-me-first-horizontal-v4.css?v=7';
    document.head.appendChild(link);
  }

  // Keep the inventory controls in one independent left stack.
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
    }
  }
  if(w) w.classList.add('umf-wide-layout');

  // The old inline image helper can overwrite valid files with broken data URIs.
  // Always finish by restoring known-good assets after each menu render.
  const PHOTO={
    '계란찜':'assets/use-me-first/gyeran-jjim-ai.webp?v=7',
    '시금치나물':'assets/use-me-first/sigeumchi-namul-ai.webp?v=7',
    '두부부침':'assets/use-me-first/dubu-buchim-ai.webp?v=7',
    '김치두부찌개':'assets/use-me-first/kimchi-tofu-stew.svg?v=7'
  };
  function repairMenuImages(){
    document.querySelectorAll('#umfRecipeGrid .umf-menu-card').forEach(card=>{
      const src=PHOTO[card.dataset.name];
      if(!src) return;
      const img=card.querySelector('.umf-menu-photo img');
      const fb=card.querySelector('.umf-menu-fallback');
      if(!img) return;
      if(!img.src.includes(src.split('?')[0])) img.src=src;
      img.style.display='block';
      if(fb) fb.style.display='none';
      img.onerror=()=>{
        img.style.display='none';
        if(fb) fb.style.display='grid';
      };
    });
  }
  const grid=document.getElementById('umfRecipeGrid');
  if(grid){
    new MutationObserver(()=>setTimeout(repairMenuImages,0)).observe(grid,{childList:true,subtree:true});
    setTimeout(repairMenuImages,120);
    setTimeout(repairMenuImages,500);
  }

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
