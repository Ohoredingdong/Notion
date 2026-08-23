(()=>{
  const KEY='use-me-first-v4',SK='use-me-first-seasonings-v1',PK='use-me-first-pantry-v1';
  const IMG={
    '두부김치':'assets/use-me-first/dubu-kimchi.webp',
    '김치볶음밥':'assets/use-me-first/kimchi-fried-rice.webp',
    '두부 김치덮밥':'assets/use-me-first/dubu-kimchi-rice.webp',
    '닭가슴살 양파 간장볶음':'assets/use-me-first/chicken-onion-soy-stirfry.webp',
    '시금치나물':'assets/use-me-first/spinach-namul.svg',
    '두부부침':'assets/use-me-first/tofu-pan-fry.svg',
    '김치두부찌개':'assets/use-me-first/kimchi-tofu-stew.svg',
    '닭가슴살 두부 간장조림':'assets/use-me-first/chicken-tofu-soy-braise.svg'
  };
  const CATALOG=[
    {name:'두부김치',f:['두부','김치'],s:[],p:[],time:'7분',level:'아주 쉬움',desc:'두부와 김치를 바로 곁들이는 가장 빠른 한 접시',steps:['두부를 먹기 좋게 썰어 따뜻하게 데워요.','김치를 먹기 좋게 썰어요.','두부와 김치를 함께 담아요.']},
    {name:'김치볶음밥',f:['김치'],s:['식용유'],p:['밥/즉석밥'],time:'10분',level:'쉬움',desc:'김치와 밥으로 만드는 든든한 한 그릇',steps:['김치를 잘게 썰어요.','식용유에 김치를 볶아요.','밥을 넣고 고르게 볶아요.']},
    {name:'두부 김치덮밥',f:['두부','김치'],s:[],p:['밥/즉석밥'],time:'8분',level:'쉬움',desc:'두부와 김치를 밥 위에 올리는 간단 덮밥',steps:['두부를 따뜻하게 데워요.','김치를 잘게 썰어요.','밥 위에 두부와 김치를 올려요.']},
    {name:'닭가슴살 양파 간장볶음',f:['닭가슴살','양파'],s:['간장','식용유'],p:[],time:'15분',level:'보통',desc:'닭가슴살과 양파를 간장으로 볶는 한 끼 반찬',steps:['닭가슴살과 양파를 썰어요.','식용유에 닭가슴살을 익혀요.','양파와 간장을 넣고 볶아요.']},
    {name:'시금치나물',f:['시금치'],s:['소금','참기름'],p:[],time:'8분',level:'쉬움',desc:'시금치를 데쳐 가볍게 무치는 기본 반찬',steps:['시금치를 짧게 데쳐요.','찬물에 헹군 뒤 물기를 짜요.','소금과 참기름으로 가볍게 무쳐요.']},
    {name:'두부부침',f:['두부'],s:['식용유','소금'],p:[],time:'10분',level:'쉬움',desc:'노릇하게 구워 바로 먹는 담백한 두부 반찬',steps:['두부의 물기를 제거해요.','소금을 아주 약하게 뿌려요.','식용유를 두른 팬에 양면을 노릇하게 구워요.']},
    {name:'김치두부찌개',f:['두부','김치'],s:['다진마늘','고춧가루'],p:[],time:'18분',level:'보통',desc:'김치와 두부로 끓이는 따뜻한 한 냄비',steps:['김치를 냄비에 넣고 끓여요.','다진마늘과 고춧가루를 넣어요.','두부를 넣고 충분히 끓여요.']},
    {name:'닭가슴살 두부 간장조림',f:['닭가슴살','두부'],s:['간장','다진마늘'],p:[],time:'18분',level:'보통',desc:'단백질 재료 두 가지를 간장으로 담백하게 조려요',steps:['닭가슴살과 두부를 먹기 좋게 썰어요.','닭가슴살을 먼저 익혀요.','두부와 간장, 다진마늘을 넣고 짧게 조려요.']},
    {name:'시금치 데침',f:['시금치'],s:[],p:[],time:'5분',level:'아주 쉬움',desc:'양념 없이도 바로 먹을 수 있는 가장 간단한 활용',steps:['물을 끓여요.','시금치를 짧게 데쳐요.','물기를 빼고 바로 곁들여요.']},
    {name:'따뜻한 두부',f:['두부'],s:[],p:[],time:'4분',level:'아주 쉬움',desc:'두부를 따뜻하게 데워 바로 먹는 최소 조리 메뉴',steps:['두부를 먹기 좋게 썰어요.','전자레인지나 끓는 물로 따뜻하게 데워요.']},
    {name:'닭가슴살 찜',f:['닭가슴살'],s:[],p:[],time:'12분',level:'아주 쉬움',desc:'양념 없이도 익혀 먹을 수 있는 기본 단백질 메뉴',steps:['닭가슴살을 속까지 충분히 익혀요.','먹기 좋게 썰어 바로 먹어요.']},
    {name:'양파찜',f:['양파'],s:[],p:[],time:'8분',level:'아주 쉬움',desc:'양파의 단맛을 살려 부드럽게 익혀 먹어요',steps:['양파를 굵게 썰어요.','전자레인지 또는 찜기로 부드럽게 익혀요.']}
  ];
  const read=k=>{try{const v=JSON.parse(localStorage.getItem(k));return Array.isArray(v)?v:[]}catch{return[]}};
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const has=(items,key)=>items.some(x=>String(x.name||'').includes(key));
  const getState=()=>({items:read(KEY),season:new Set(read(SK)),pantry:new Set(read(PK))});
  const missing=(r,s)=>[...r.f.filter(x=>!has(s.items,x)),...r.s.filter(x=>!s.season.has(x)),...r.p.filter(x=>!s.pantry.has(x))];
  const actualUse=(r,s)=>r.f.map(k=>s.items.find(x=>String(x.name||'').includes(k))?.name).filter(Boolean);
  const shell=document.getElementById('umfRecipeGridShell');
  const grid=document.getElementById('umfRecipeGrid');
  const count=document.getElementById('umfAvailableCount');
  const chips=document.getElementById('umfSelectionChips');
  const detail=document.getElementById('umfRecipeDetail');
  const recipeBtn=document.getElementById('umfRecipeBtn');
  const shuffleBtn=document.getElementById('umfShuffleBtn');
  if(!shell||!grid||!count||!chips||!detail)return;
  let selectedName='';

  function renderSelection(r,s){
    selectedName=r.name;
    [...grid.children].forEach(el=>el.classList.toggle('selected',el.dataset.name===r.name));
    const use=actualUse(r,s);
    chips.innerHTML=use.length?use.map(x=>`<span class="umf-selection-chip">${esc(x)}</span>`).join(''):'<span class="umf-selection-chip">냉장고 재료 확인</span>';
    detail.innerHTML=`<b>${esc(r.name)}</b><ol>${r.steps.map(x=>`<li>${esc(x)}</li>`).join('')}</ol>`;
    detail.classList.remove('on');
  }

  function render(){
    const s=getState();
    const rows=CATALOG.map(r=>({...r,miss:missing(r,s)}));
    const available=rows.filter(r=>!r.miss.length);
    const unavailable=rows.filter(r=>r.miss.length).sort((a,b)=>a.miss.length-b.miss.length);
    const list=[...available,...unavailable].slice(0,8);
    count.textContent=`가능 메뉴 ${available.length}개`;
    grid.replaceChildren(...list.map((r,i)=>{
      const card=document.createElement('article');
      card.className='umf-menu-card'+(r.miss.length?' missing':'');
      card.dataset.name=r.name;
      const src=IMG[r.name];
      card.innerHTML=`<div class="umf-menu-photo"><span class="umf-menu-num">추천 ${i+1}</span>${src?`<img src="${src}?v=2" alt="${esc(r.name)}" loading="eager" onerror="this.style.display='none';this.nextElementSibling.style.display='grid'">`:`<div class="umf-menu-fallback">${esc(r.name)}</div>`}<div class="umf-menu-fallback" style="${src?'display:none;':''}">${esc(r.name)}</div>${r.miss.length?`<div class="umf-menu-missing">필요: ${esc(r.miss.slice(0,2).join(' · '))}</div>`:''}</div><div class="umf-menu-body"><div class="umf-menu-name">${esc(r.name)}</div><div class="umf-menu-desc">${esc(r.desc)}</div><div class="umf-menu-meta"><span>${esc(r.time)}</span><span>${esc(r.level)}</span></div></div>`;
      if(!r.miss.length)card.addEventListener('click',()=>renderSelection(r,s));
      return card;
    }));
    const chosen=available.find(r=>r.name===selectedName)||available[0];
    if(chosen)renderSelection(chosen,s);else{selectedName='';chips.innerHTML='<span class="umf-selection-chip">기본 양념/상비 재료를 체크하면 메뉴가 열려요</span>';detail.innerHTML='';}
  }

  recipeBtn?.addEventListener('click',()=>detail.classList.toggle('on'));
  shuffleBtn?.addEventListener('click',()=>{const cards=[...grid.querySelectorAll('.umf-menu-card:not(.missing)')];if(!cards.length)return;const i=Math.max(0,cards.findIndex(x=>x.classList.contains('selected')));cards[(i+1)%cards.length].click();});
  document.addEventListener('click',e=>{if(e.target.closest('.tog,.tinyAdd,.add,.rm,.tab'))setTimeout(render,80)});
  window.addEventListener('storage',render);
  const listNode=document.getElementById('list');if(listNode)new MutationObserver(()=>setTimeout(render,0)).observe(listNode,{childList:true,subtree:true});
  render();
})();