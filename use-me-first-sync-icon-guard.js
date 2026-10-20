/* Reflect the real sync state after the common widget controls move the button. */
(() => {
  'use strict';
  const button=document.getElementById('syncBtn'),status=document.getElementById('syncStatus');
  if(!button||!status)return;
  const connected=()=>{try{return !!window.UMFCore?.sync.code;}catch{return false;}};
  function render(){
    const bad=['error','conflict'].includes(status.dataset.syncState);
    const label=connected()?'동기화 관리':'동기화 설정';
    button.setAttribute('aria-label',label);button.dataset.tip=label;button.title=status.textContent;
    let dot=button.querySelector('.syncDot');
    if(!dot){dot=document.createElement('i');dot.id='syncDot';dot.className='syncDot';button.appendChild(dot);}
    dot.classList.toggle('on',connected()&&status.dataset.syncState==='ready');
    dot.classList.toggle('bad',bad);
  }
  new MutationObserver(render).observe(status,{attributes:true,childList:true,characterData:true,subtree:true});
  window.addEventListener('storage',e=>{if(e.key===window.UMFStore?.keys.SYNC)render();});
  render();
})();
