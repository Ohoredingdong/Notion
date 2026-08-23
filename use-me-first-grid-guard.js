(()=>{
  const clean=()=>{
    const sec=document.querySelector('.recipeSec');
    if(!sec)return;
    // Legacy single-recipe card must never coexist with the 8-card grid.
    sec.querySelectorAll(':scope > .recipe').forEach(el=>el.remove());

    // Keep exactly one generated recommendation shell, even if an old/cached
    // script executes twice in an embedded browser/webview.
    const shells=[...document.querySelectorAll('#umfRecipeGridShell')];
    shells.slice(1).forEach(el=>el.remove());

    // Defensive cleanup for duplicated grids accidentally appended outside shell.
    const primary=shells[0]||document.querySelector('#umfRecipeGridShell');
    document.querySelectorAll('.umf-recipe-grid').forEach((grid,i)=>{
      if(i===0)return;
      const owner=grid.closest('#umfRecipeGridShell');
      if(owner && owner!==primary) owner.remove();
      else if(!owner) grid.remove();
    });
  };
  clean();
  const mo=new MutationObserver(()=>clean());
  mo.observe(document.documentElement,{childList:true,subtree:true});
  window.addEventListener('pageshow',clean);
  window.addEventListener('load',()=>{clean();setTimeout(clean,100);setTimeout(clean,500);setTimeout(clean,1500)});
})();