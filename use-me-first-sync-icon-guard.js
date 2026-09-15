(()=>{
  const btn=document.getElementById('syncBtn');
  if(!btn) return;

  const status=document.getElementById('syncStatus');
  const SYNC_KEY='use-me-first-sync-code-v1';
  const ICON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h11"/><path d="m12 4 3 3-3 3"/><path d="M20 17H9"/><path d="m12 14-3 3 3 3"/></svg>';
  let repairing=false;

  const connected=()=>!!localStorage.getItem(SYNC_KEY);
  const hasRealError=()=>/실패|오류|error/i.test((status?.textContent||'').trim());

  function repair(){
    if(repairing) return;
    repairing=true;

    const isConnected=connected();
    const bad=hasRealError();
    const label=isConnected?'동기화 관리':'동기화 설정';
    btn.dataset.tip=label;
    btn.setAttribute('aria-label',label);

    [...btn.childNodes].forEach(node=>{
      if(node.nodeType===Node.TEXT_NODE) node.remove();
    });
    if(!btn.querySelector('svg')) btn.insertAdjacentHTML('afterbegin',ICON);

    let dot=btn.querySelector('.syncDot');
    if(!dot){
      dot=document.createElement('i');
      dot.id='syncDot';
      dot.className='syncDot';
      btn.appendChild(dot);
    }
    dot.classList.toggle('on',isConnected&&!bad);
    dot.classList.toggle('bad',bad);

    repairing=false;
  }

  try{
    window.renderSyncStatus=function(){
      if(status){
        status.textContent=connected()?'이 기기는 동기화 연결됨':'이 기기는 아직 로컬 저장만 사용 중';
        status.classList.remove('bad');
      }
      repair();
    };
  }catch(e){}

  new MutationObserver(()=>queueMicrotask(repair)).observe(btn,{childList:true,subtree:true,characterData:true});
  if(status) new MutationObserver(()=>queueMicrotask(repair)).observe(status,{attributes:true,childList:true,characterData:true});
  window.addEventListener('storage',e=>{if(e.key===SYNC_KEY)repair()});
  repair();
})();
