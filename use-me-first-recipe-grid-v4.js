(()=>{
const KEY='use-me-first-v4',SK='use-me-first-seasonings-v1',PK='use-me-first-pantry-v1';
const IMG={
 '두부김치':'assets/use-me-first/dubu-kimchi.webp?v=9',
 '김치볶음밥':'assets/use-me-first/kimchi-fried-rice.webp?v=9',
 '두부 김치덮밥':'assets/use-me-first/dubu-kimchi-rice.webp?v=9',
 '닭가슴살 양파 간장볶음':'assets/use-me-first/chicken-onion-soy-stirfry.webp?v=9',
 '계란찜':'assets/use-me-first/gyeran-jjim-ai.webp?v=9',
 '시금치나물':'assets/use-me-first/sigeumchi-namul-ai.webp?v=9',
 '두부부침':'assets/use-me-first/dubu-buchim-ai.webp?v=9',
 '김치두부찌개':'assets/use-me-first/dubu-kimchi-rice.webp?v=9'
};
const C=[
 {name:'두부김치',f:['두부','김치'],s:[],p:[],time:'7분',level:'아주 쉬움',desc:'두부와 김치를 바로 곁들이는 가장 빠른 한 접시',steps:['두부를 먹기 좋게 썰어 따뜻하게 데워요.','김치를 먹기 좋게 썰어요.','두부와 김치를 함께 담아요.']},
 {name:'김치볶음밥',f:['김치'],s:['식용유'],p:['밥/즉석밥'],time:'10분',level:'쉬움',desc:'김치와 밥으로 만드는 든든한 한 그릇',steps:['김치를 잘게 썰어요.','식용유에 김치를 볶아요.','밥을 넣고 고르게 볶아요.']},
 {name:'두부 김치덮밥',f:['두부','김치'],s:[],p:['밥/즉석밥'],time:'8분',level:'쉬움',desc:'두부와 김치를 밥 위에 올리는 간단 덮밥',steps:['두부를 따뜻하게 데워요.','김치를 잘게 썰어요.','밥 위에 두부와 김치를 올려요.']},
 {name:'닭가슴살 양파 간장볶음',f:['닭가슴살','양파'],s:['간장','식용유'],p:[],time:'15분',level:'보통',desc:'닭가슴살과 양파를 간장으로 볶는 한 끼 반찬',steps:['닭가슴살과 양파를 썰어요.','식용유에 닭가슴살을 익혀요.','양파와 간장을 넣고 볶아요.']},
 {name:'계란찜',f:['계란'],s:['소금'],p:[],time:'15분',level:'아주 쉬움',desc:'계란으로 부드럽고 촉촉하게 만드는 기본 반찬',steps:['계란을 풀어요.','소금과 물을 조금 넣어 섞어요.','약한 불이나 전자레인지로 부드럽게 익혀요.']},
 {name:'시금치나물',f:['시금치'],s:['소금','참기름'],p:[],time:'8분',level:'쉬움',desc:'시금치를 데쳐 고소하게 무치는 기본 반찬',steps:['시금치를 짧게 데쳐요.','찬물에 헹군 뒤 물기를 짜요.','소금과 참기름으로 가볍게 무쳐요.']},
 {name:'두부부침',f:['두부'],s:['식용유','소금'],p:[],time:'10분',level:'쉬움',desc:'두부를 노릇하게 부쳐 바로 먹는 담백한 반찬',steps:['두부 물기를 닦아요.','소금을 살짝 뿌려요.','식용유를 두른 팬에 양면을 노릇하게 구워요.']},
 {name:'김치두부찌개',f:['두부','김치'],s:['다진마늘','고춧가루'],p:[],time:'20분',level:'보통',desc:'김치와 두부로 끓이는 따뜻한 한 냄비',steps:['김치에 물을 붓고 끓여요.','다진마늘과 고춧가루를 넣어요.','두부를 넣고 충분히 끓여요.']}
];
const read=k=>{try{const v=JSON.parse(localStorage.getItem(k));return Array.isArray(v)?v:[]}catch{return[]}};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));
const has=(items,k)=>items.some(x=>String(x.name||'').includes(k));
const state=()=>({items:read(KEY),season:new Set(read(SK)),pantry:new Set(read(PK))});
const missing=(r,st)=>[...r.f.filter(x=>!has(st.items,x)),...r.s.filter(x=>!st.season.has(x)),...r.p.filter(x=>!st.pantry.has(x))];
const actual=(r,st)=>r.f.map(k=>st.items.find(x=>String(x.name||'').includes(k))?.name).filter(Boolean);
function renderSelection(r,st){
 document.querySelectorAll('#umfRecipeGrid .umf-menu-card').forEach(x=>x.classList.toggle('selected',x.dataset.name===r.name));
 const u=actual(r,st);document.getElementById('umfSelectionChips').innerHTML=u.length?u.map(x=>`<span class="umf-selection-chip">${esc(x)}</span>`).join(''):'<span class="umf-selection-chip">냉장고 재료 확인</span>';
 document.getElementById('umfRecipeDetail').innerHTML=`<b>${esc(r.name)}</b><ol>${r.steps.map(x=>`<li>${esc(x)}</li>`).join('')}</ol>`;document.getElementById('umfRecipeDetail').classList.remove('on');
}
function render(){
 const grid=document.getElementById('umfRecipeGrid');if(!grid)return;
 const st=state();const list=C.map(r=>({...r,missing:missing(r,st)}));const av=list.filter(r=>!r.missing.length);
 document.getElementById('umfAvailableCount').textContent=`가능 메뉴 ${av.length}개`;
 grid.replaceChildren(...list.map((r,i)=>{const el=document.createElement('article');el.className='umf-menu-card'+(r.missing.length?' missing':'');el.dataset.name=r.name;
 const src=IMG[r.name];
 el.innerHTML=`<div class="umf-menu-photo"><span class="umf-menu-num">추천 ${i+1}</span><img src="${src}" alt="${esc(r.name)}" loading="eager" decoding="async"><div class="umf-menu-fallback" style="display:none">이미지를 준비 중이에요<br>${esc(r.name)}</div>${r.missing.length?`<div class="umf-menu-missing">필요 · ${esc(r.missing.slice(0,2).join(' · '))}</div>`:''}</div><div class="umf-menu-body"><div class="umf-menu-name">${esc(r.name)}</div><div class="umf-menu-desc">${esc(r.desc)}</div><div class="umf-menu-meta"><span>${esc(r.time)}</span><span>${esc(r.level)}</span></div></div>`;
 const img=el.querySelector('img'),fb=el.querySelector('.umf-menu-fallback');img.onerror=()=>{img.style.display='none';fb.style.display='grid';console.error('[UseMeFirst image failed]',r.name,src)};img.onload=()=>{img.style.display='block';fb.style.display='none'};
 if(!r.missing.length)el.onclick=()=>renderSelection(r,st);return el;}));
 if(av.length)renderSelection(av[0],st);else{document.getElementById('umfSelectionChips').innerHTML='<span class="umf-selection-chip">기본 양념/상비 재료를 체크하면 메뉴가 열려요</span>';document.getElementById('umfRecipeDetail').innerHTML='';}
}
const rb=document.getElementById('umfRecipeBtn');if(rb)rb.onclick=()=>document.getElementById('umfRecipeDetail')?.classList.toggle('on');
const sb=document.getElementById('umfShuffleBtn');if(sb)sb.onclick=()=>{const cards=[...document.querySelectorAll('#umfRecipeGrid .umf-menu-card:not(.missing)')];if(!cards.length)return;const i=Math.max(0,cards.findIndex(x=>x.classList.contains('selected')));cards[(i+1)%cards.length].click()};
const listNode=document.getElementById('list');if(listNode)new MutationObserver(()=>setTimeout(render,0)).observe(listNode,{childList:true,subtree:true});
document.addEventListener('click',e=>{if(e.target.closest('.tog,.tinyAdd,.add,.rm,.tab'))setTimeout(render,60)});window.addEventListener('storage',render);setTimeout(render,100);
})();