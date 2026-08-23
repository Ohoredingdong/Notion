(()=>{
  const btn=document.getElementById('syncBtn');
  if(!btn) return;

  const status=document.getElementById('syncStatus');
  const SYNC_KEY='use-me-first-sync-code-v1';
  const ICON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h11"/><path d="m12 4 3 3-3 3"/><path d="M20 17H9"/><path d="m12 14-3 3 3 3"/></svg>';
  let repairing=false;

  function connected(){
    return !!localStorage.getItem(SYNC_KEY);
  }

  function repairSyncButton(){
    if(repairing) return;
    repairing=true;

    const bad=!!(status&&status.classList.contains('bad'));
    const tip=connected()?'동기화 관리':'동기화 설정';
    btn.dataset.tip=tip;
    btn.setAttribute('aria-label',tip);

    // Legacy renderSyncStatus() used textContent on this button, which deletes
    // the SVG and sync dot. Remove only stray text nodes and restore UI pieces.
    [...btn.childNodes].forEach(node=>{
      if(node.nodeType===Node.TEXT_NODE) node.remove();
    });

    if(!btn.querySelector('svg')) btn.insertAdjacentHTML('afterbegin',ICON);

    let dot=btn.querySelector('.syncDot');
    if(!dot){
      dot=document.createElement('i');
      dot.className='syncDot';
      dot.id='syncDot';
      btn.appendChild(dot);
    }
    dot.classList.toggle('bad',bad);
    dot.classList.toggle('on',connected()&&!bad);

    repairing=false;
  }

  // Replace the legacy implementation when the global binding is writable.
  // The MutationObserver below also protects the button if another script still
  // calls the old function through its original binding.
  try{
    window.renderSyncStatus=function(){
      if(status){
        status.textContent=connected()?'이 기기는 동기화 연결됨':'이 기기는 아직 로컬 저장만 사용 중';
        status.classList.remove('bad');
      }
      repairSyncButton();
    };
  }catch(e){}

  const buttonObserver=new MutationObserver(()=>queueMicrotask(repairSyncButton));
  buttonObserver.observe(btn,{childList:true,subtree:true,characterData:true});

  if(status){
    const statusObserver=new MutationObserver(()=>queueMicrotask(repairSyncButton));
    statusObserver.observe(status,{attributes:true,childList:true,characterData:true});
  }

  window.addEventListener('storage',e=>{
    if(e.key===SYNC_KEY) repairSyncButton();
  });

  repairSyncButton();
})();
