(()=>{
  const KEY='use-me-first-v4',SK='use-me-first-seasonings-v1',PK='use-me-first-pantry-v1';
  const IMG={
    '두부김치':'assets/use-me-first/dubu-kimchi.webp',
    '김치볶음밥':'assets/use-me-first/kimchi-fried-rice.webp',
    '두부 김치덮밥':'assets/use-me-first/dubu-kimchi-rice.webp',
    '닭가슴살 양파 간장볶음':'assets/use-me-first/chicken-onion-soy-stirfry.webp'
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
  const read=(k)=>{try{const v=JSON.parse(localStorage.getItem(k));return Array.isArray(v)?v:[]}catch{return[]}};
  const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));
  const hasName=(items,key)=>items.some(x=>String(x.name||'').includes(key));
  function state(){return{items:read(KEY),season:new Set(read(SK)),pantry:new Set(read(PK))}}
  function check(r,st){const missing=[];r.f.forEach(x=>{if(!hasName(st.items,x))missing.push(x)});r.s.forEach(x=>{if(!st.season.has(x))missing.push(x)});r.p.forEach(x=>{if(!st.pantry.has(x))missing.push(x)});return missing}
  function actualUse(r,st){return r.f.map(k=>st.items.find(x=>String(x.name||'').includes(k))?.name).filter(Boolean)}
  let selected=null;
  function ensureShell(){
    const sec=document.querySelector('.recipeSec'); if(!sec)return null;
    let shell=document.getElementById('umfRecipeGridShell');
    if(shell)return shell;
    const legacy=sec.querySelector('.recipe');
    if(legacy) legacy.remove();
    shell=document.createElement('div');shell.id='umfRecipeGridShell';
    const tip=sec.querySelector('.tip');
    if(tip) sec.insertBefore(shell,tip); else sec.appendChild(shell);
    shell.innerHTML='<div class="umf-recipe-toolbar"><span class="umf-badge">🍳 배달 방지</span><span class="umf-badge" id="umfAvailableCount">가능 메뉴 0개</span></div><div class="umf-recipe-grid" id="umfRecipeGrid"></div><div class="umf-selection"><div class="umf-selection-label">선택한 메뉴에 실제로 쓰는 내 재료</div><div class="umf-selection-chips" id="umfSelectionChips"></div><div class="umf-selection-actions"><button class="primary" id="umfRecipeBtn">레시피 보기</button><button id="umfShuffleBtn">↻ 다른 메뉴 보기</button></div><div class="umf-recipe-detail" id="umfRecipeDetail"></div></div>';
    shell.querySelector('#umfRecipeBtn').onclick=()=>document.getElementById('umfRecipeDetail')?.classList.toggle('on');
    shell.querySelector('#umfShuffleBtn').onclick=()=>{const cards=[...document.querySelectorAll('.umf-menu-card:not(.missing)')];if(!cards.length)return;const current=Math.max(0,cards.findIndex(x=>x.classList.contains('selected')));cards[(current+1)%cards.length].click()};
    return shell;
  }
  function renderSelection(r,st){selected=r;document.querySelectorAll('.umf-menu-card').forEach(x=>x.classList.toggle('selected',x.dataset.name===r.name));const chips=document.getElementById('umfSelectionChips');const use=actualUse(r,st);chips.innerHTML=use.length?use.map(x=>`<span class="umf-selection-chip">${escape(x)}</span>`).join(''):'<span class="umf-selection-chip">냉장고 재료 확인</span>';document.getElementById('umfRecipeDetail').innerHTML=`<b>${escape(r.name)}</b><ol>${r.steps.map(x=>`<li>${escape(x)}</li>`).join('')}</ol>`;document.getElementById('umfRecipeDetail').classList.remove('on')}
  function render(){const shell=ensureShell();if(!shell)return;const st=state();const enriched=CATALOG.map(r=>({...r,missing:check(r,st)}));const available=enriched.filter(r=>!r.missing.length);const unavailable=enriched.filter(r=>r.missing.length).sort((a,b)=>a.missing.length-b.missing.length);const list=[...available,...unavailable].slice(0,8);document.getElementById('umfAvailableCount').textContent=`가능 메뉴 ${available.length}개`;const grid=document.getElementById('umfRecipeGrid');grid.innerHTML=list.map((r,i)=>{const src=IMG[r.name];return `<article class="umf-menu-card${r.missing.length?' missing':''}" data-name="${escape(r.name)}"><div class="umf-menu-photo"><span class="umf-menu-num">${i+1}</span>${src?`<img src="${src}" alt="${escape(r.name)}">`:`<div class="umf-menu-fallback">${escape(r.name)}</div>`}${r.missing.length?`<div class="umf-menu-missing">필요: ${escape(r.missing.slice(0,2).join(' · '))}</div>`:''}</div><div class="umf-menu-body"><div class="umf-menu-name">${escape(r.name)}</div><div class="umf-menu-desc">${escape(r.desc)}</div><div class="umf-menu-meta"><span>${escape(r.time)}</span><span>${escape(r.level)}</span></div></div></article>`}).join('');[...grid.children].forEach((el,i)=>{const r=list[i];if(!r.missing.length)el.onclick=()=>renderSelection(r,st)});const first=available.find(a=>list.some(x=>x.name===a.name));if(first)renderSelection(first,st);else{document.getElementById('umfSelectionChips').innerHTML='<span class="umf-selection-chip">기본 양념/상비 재료를 체크하면 메뉴가 열려요</span>';document.getElementById('umfRecipeDetail').innerHTML=''}}
  const obsTarget=document.getElementById('list');if(obsTarget)new MutationObserver(()=>setTimeout(render,0)).observe(obsTarget,{childList:true,subtree:true});document.addEventListener('click',e=>{if(e.target.closest('.tog,.tinyAdd,.add,.rm,.tab'))setTimeout(render,60)});window.addEventListener('storage',()=>render());setTimeout(render,120);
})();