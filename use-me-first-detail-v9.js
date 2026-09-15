(()=>{
  const $=s=>document.querySelector(s);

  function ingredientEmoji(name=''){
    if(/토마토/.test(name))return'🍅';
    if(/치즈/.test(name))return'🧀';
    if(/버섯/.test(name))return'🍄';
    if(/당근/.test(name))return'🥕';
    if(/양파/.test(name))return'🧅';
    if(/계란|달걀/.test(name))return'🥚';
    if(/닭/.test(name))return'🍗';
    if(/우유/.test(name))return'🥛';
    if(/김치/.test(name))return'🥬';
    if(/두부/.test(name))return'◻️';
    return'＋';
  }

  function copyPass(){
    const sub=$('.umf-dashboard-sub');if(sub)sub.textContent='지금 있는 재료로, 오늘도 맛있는 하루';
    const dateSub=$('#umfDateSub');if(dateSub)dateSub.textContent='오늘도 좋은 식사 되세요!';
    const nutrition=$('.umf-insights .insight-card:first-child .insight-title');if(nutrition)nutrition.textContent='오늘의 영양 밸런스';

    const rightCards=[...document.querySelectorAll('.umf-insights .insight-card')];
    if(rightCards[1]){
      const sub=rightCards[1].querySelector('.insight-sub');
      if(sub)sub.textContent='추가하면 메뉴가 더 넓어져요';
    }
    if(rightCards[2]){
      const sub=rightCards[2].querySelector('.insight-sub');
      if(sub)sub.textContent='오늘 기록';
    }

    const labels=[...document.querySelectorAll('.summary-label')];
    if(labels[0])labels[0].textContent='곧 유통기한이 돌아오는 재료';
    if(labels[1])labels[1].textContent='지금 바로 만들 수 있는 레시피';
    if(labels[2])labels[2].textContent='부족한 재료';
  }

  function patchMissing(){
    document.querySelectorAll('#umfMissingList .missing-item').forEach(row=>{
      if(row.querySelector('.v9-missing-main'))return;
      const first=row.firstElementChild;
      const name=first?.querySelector('.missing-name')?.textContent?.trim()||'';
      if(!first||!name)return;
      first.classList.add('v9-missing-main');
      const ico=document.createElement('span');
      ico.className='v9-missing-ico';ico.textContent=ingredientEmoji(name);
      const copy=document.createElement('span');copy.className='v9-copy';
      while(first.firstChild)copy.appendChild(first.firstChild);
      first.append(ico,copy);
    });
  }

  function recipeImage(name){
    const cards=[...document.querySelectorAll('#umfRecipeGrid .umf-menu-card')];
    const card=cards.find(c=>(c.dataset.name||c.querySelector('.umf-menu-name')?.textContent?.trim())===name);
    return card?.querySelector('img')?.getAttribute('src')||'';
  }

  function patchMeals(){
    document.querySelectorAll('#umfMealList .meal-item').forEach(row=>{
      if(row.querySelector('.v9-meal-main'))return;
      const first=row.firstElementChild;
      const name=first?.querySelector('.meal-name')?.textContent?.trim()||'';
      if(!first||!name||/아직 기록/.test(name))return;
      first.classList.add('v9-meal-main');
      const thumb=document.createElement('span');thumb.className='v9-meal-thumb';
      const src=recipeImage(name);
      thumb.innerHTML=src?`<img src="${src}" alt="">`:'🍽️';
      const copy=document.createElement('span');copy.className='v9-copy';
      while(first.firstChild)copy.appendChild(first.firstChild);
      first.append(thumb,copy);
    });
  }

  function hideRedundantState(){
    const toolbar=$('.umf-recipe-toolbar');if(toolbar)toolbar.setAttribute('aria-hidden','true');
  }

  function run(){copyPass();patchMissing();patchMeals();hideRedundantState()}
  run();

  for(const s of['#umfMissingList','#umfMealList','#umfRecipeGrid']){
    const node=$(s);if(node)new MutationObserver(()=>queueMicrotask(run)).observe(node,{childList:true,subtree:true});
  }
  window.addEventListener('storage',()=>setTimeout(run,20));
  setTimeout(run,220);
})();
