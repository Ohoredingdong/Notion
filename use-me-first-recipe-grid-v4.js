(()=>{
  const KEY='use-me-first-v4',SK='use-me-first-seasonings-v1',PK='use-me-first-pantry-v1';
  const IMG={
    '계란 볶음밥':'assets/use-me-first/kimchi-fried-rice.webp?v=10',
    '두부 된장국':'assets/use-me-first/kimchi-dubu-jjigae-ai.webp?v=10',
    '닭가슴살 샐러드':'assets/use-me-first/chicken-onion-soy-stirfry.webp?v=10',
    '애호박 계란전':'assets/use-me-first/egg-steam.webp?v=10',
    '요거트 계란 샐러드':'assets/use-me-first/gyeran-jjim-ai.webp?v=10',
    '두부 스테이크':'assets/use-me-first/dubu-buchim-ai.webp?v=10',
    '버섯 두부볶음':'assets/use-me-first/dubu-kimchi.webp?v=10',
    '토마토 치즈 오믈렛':'assets/use-me-first/gyeran-jjim-ai.webp?v=10'
  };
  const C=[
    {name:'계란 볶음밥',f:['계란','양파'],s:['식용유','간장'],p:['밥/즉석밥'],time:'15분',level:'쉬움',desc:'간단한 재료로 빠르게 완성하는 한 끼 식사',steps:['양파를 잘게 썰어요.','식용유에 양파와 계란을 볶아요.','밥과 간장을 넣고 고르게 볶아요.']},
    {name:'두부 된장국',f:['두부','애호박','양파'],s:['된장','다진마늘'],p:[],time:'20분',level:'보통',desc:'구수하고 담백한 한국인의 기본 국',steps:['애호박과 양파를 먹기 좋게 썰어요.','물에 된장과 다진마늘을 풀어 끓여요.','두부와 채소를 넣고 익혀요.']},
    {name:'닭가슴살 샐러드',f:['닭가슴살','토마토'],s:['소금','후추'],p:[],time:'15분',level:'쉬움',desc:'신선한 채소와 담백한 닭가슴살로 가볍고 든든하게',steps:['닭가슴살을 완전히 익혀 먹기 좋게 썰어요.','토마토를 썰어요.','소금과 후추로 가볍게 간해 함께 담아요.']},
    {name:'애호박 계란전',f:['애호박','계란'],s:['소금','식용유'],p:[],time:'12분',level:'쉬움',desc:'애호박과 계란으로 만드는 담백한 팬 요리',steps:['애호박을 얇게 썰어요.','계란을 풀고 소금을 조금 넣어요.','애호박에 계란물을 입혀 앞뒤로 익혀요.']},
    {name:'요거트 계란 샐러드',f:['요거트','계란'],s:['소금','후추'],p:[],time:'10분',level:'쉬움',desc:'삶은 계란을 요거트로 가볍게 버무리는 간단 샐러드',steps:['계란을 완숙으로 익혀 으깨요.','요거트를 넣어 섞어요.','소금과 후추로 간해요.']},
    {name:'두부 스테이크',f:['두부','양파'],s:['간장','식용유'],p:[],time:'15분',level:'쉬움',desc:'두부를 노릇하게 굽고 양파 간장소스를 곁들이는 한 접시',steps:['두부 물기를 닦고 도톰하게 썰어요.','식용유를 두른 팬에 두부를 노릇하게 구워요.','양파와 간장을 살짝 볶아 두부에 올려요.']},
    {name:'버섯 두부볶음',f:['두부','버섯','양파'],s:['간장','식용유'],p:[],time:'15분',level:'보통',desc:'버섯과 두부를 함께 볶아 담백하게 즐기는 반찬',steps:['두부와 양파, 버섯을 썰어요.','두부를 먼저 노릇하게 익혀요.','버섯과 양파, 간장을 넣고 볶아요.']},
    {name:'토마토 치즈 오믈렛',f:['계란','토마토','치즈'],s:['소금','식용유'],p:[],time:'12분',level:'쉬움',desc:'토마토와 치즈를 넣어 부드럽게 접어 만드는 오믈렛',steps:['계란을 풀고 소금을 조금 넣어요.','토마토를 작게 썰어요.','팬에 계란물을 붓고 토마토와 치즈를 넣어 접어요.']}
  ];
  const read=k=>{try{const v=JSON.parse(localStorage.getItem(k));return Array.isArray(v)?v:[]}catch{return[]}};
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const has=(items,k)=>items.some(x=>String(x.name||'').includes(k));
  const state=()=>({items:read(KEY),season:new Set(read(SK)),pantry:new Set(read(PK))});
  const missing=(r,st)=>[...r.f.filter(x=>!has(st.items,x)),...r.s.filter(x=>!st.season.has(x)),...r.p.filter(x=>!st.pantry.has(x))];
  const actual=(r,st)=>r.f.map(k=>st.items.find(x=>String(x.name||'').includes(k))?.name).filter(Boolean);
  function renderSelection(r,st){
    document.querySelectorAll('#umfRecipeGrid .umf-menu-card').forEach(x=>x.classList.toggle('selected',x.dataset.name===r.name));
    const u=actual(r,st),chips=document.getElementById('umfSelectionChips'),detail=document.getElementById('umfRecipeDetail');
    if(chips)chips.innerHTML=u.length?u.map(x=>`<span class="umf-selection-chip">${esc(x)}</span>`).join(''):'<span class="umf-selection-chip">냉장고 재료 확인</span>';
    if(detail){detail.innerHTML=`<b>${esc(r.name)}</b><ol>${r.steps.map(x=>`<li>${esc(x)}</li>`).join('')}</ol>`;detail.classList.remove('on')}
  }
  function render(){
    const grid=document.getElementById('umfRecipeGrid');if(!grid)return;
    const st=state(),list=C.map(r=>({...r,missing:missing(r,st)})),av=list.filter(r=>!r.missing.length);
    const count=document.getElementById('umfAvailableCount');if(count)count.textContent=`지금 가능 ${av.length} / 전체 ${list.length}`;
    grid.replaceChildren(...list.map((r,i)=>{
      const el=document.createElement('article');el.className='umf-menu-card'+(r.missing.length?' missing':'');el.dataset.name=r.name;
      const src=IMG[r.name];
      el.innerHTML=`<div class="umf-menu-photo"><span class="umf-menu-num">추천 ${i+1}</span><img src="${src}" alt="${esc(r.name)}" loading="eager" decoding="async"><div class="umf-menu-fallback" style="display:none">이미지를 준비 중이에요<br>${esc(r.name)}</div>${r.missing.length?`<div class="umf-menu-missing">필요 · ${esc(r.missing.slice(0,2).join(' · '))}</div>`:''}</div><div class="umf-menu-body"><div class="umf-menu-name">${esc(r.name)}</div><div class="umf-menu-desc">${esc(r.desc)}</div><div class="umf-menu-meta"><span>${esc(r.time)}</span><span>${esc(r.level)}</span></div></div>`;
      const img=el.querySelector('img'),fb=el.querySelector('.umf-menu-fallback');
      img.onerror=()=>{img.style.display='none';fb.style.display='grid'};img.onload=()=>{img.style.display='block';fb.style.display='none'};
      if(!r.missing.length)el.onclick=()=>renderSelection(r,st);
      return el;
    }));
    if(av.length)renderSelection(av[0],st);else{
      const chips=document.getElementById('umfSelectionChips'),detail=document.getElementById('umfRecipeDetail');
      if(chips)chips.innerHTML='<span class="umf-selection-chip">기본 양념/상비 재료를 체크하면 메뉴가 열려요</span>';
      if(detail)detail.innerHTML='';
    }
  }
  const rb=document.getElementById('umfRecipeBtn');if(rb)rb.onclick=()=>document.getElementById('umfRecipeDetail')?.classList.toggle('on');
  const sb=document.getElementById('umfShuffleBtn');if(sb)sb.onclick=()=>{const cards=[...document.querySelectorAll('#umfRecipeGrid .umf-menu-card:not(.missing)')];if(!cards.length)return;const i=Math.max(0,cards.findIndex(x=>x.classList.contains('selected')));cards[(i+1)%cards.length].click()};
  const listNode=document.getElementById('list');if(listNode)new MutationObserver(()=>setTimeout(render,0)).observe(listNode,{childList:true,subtree:true});
  document.addEventListener('click',e=>{if(e.target.closest('.tog,.tinyAdd,.add,.rm,.tab'))setTimeout(render,60)});
  window.addEventListener('storage',render);setTimeout(render,100);
})();
