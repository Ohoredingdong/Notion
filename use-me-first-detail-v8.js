(()=>{
  const FAV_KEY='use-me-first-favorites-v1';
  const $=s=>document.querySelector(s);
  const readFav=()=>{try{return new Set(JSON.parse(localStorage.getItem(FAV_KEY))||[])}catch{return new Set()}};
  const saveFav=set=>localStorage.setItem(FAV_KEY,JSON.stringify([...set]));

  function svgCalendar(){return '<span class="umf-date-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 9h16"/></svg></span>'}
  function summarySvg(kind){
    const icons={
      warn:'<svg viewBox="0 0 24 24"><path d="M12 3 2.8 19h18.4L12 3Z"/><path d="M12 9v4M12 17h.01"/></svg>',
      ok:'<svg viewBox="0 0 24 24"><path d="M5 11h14M7 11v7h10v-7M9 11V8a3 3 0 0 1 6 0v3"/><path d="M9 5h6"/></svg>',
      need:'<svg viewBox="0 0 24 24"><path d="M3 5h2l2 10h10l2-7H7"/><circle cx="9" cy="19" r="1.2"/><circle cx="17" cy="19" r="1.2"/></svg>'
    };
    return icons[kind]||'';
  }

  function restructure(){
    const date=$('.umf-date');
    if(date&&!date.querySelector('.umf-date-icon'))date.insertAdjacentHTML('afterbegin',svgCalendar());

    const leftHead=$('.umf-left>.head');
    const all=$('#all');
    if(leftHead&&all&&!leftHead.contains(all)){
      all.classList.add('umf-head-all');
      leftHead.appendChild(all);
    }
    const card=$('.umf-left .card');
    const add=$('#openAdd');
    if(card&&add&&!card.contains(add)){
      add.classList.add('umf-left-add');
      add.textContent='＋ 재료 추가하기';
      card.appendChild(add);
    }

    const recipeHead=$('.recipeSec>.sh');
    if(recipeHead&&!recipeHead.querySelector('.umf-section-link')){
      const b=document.createElement('button');
      b.type='button';b.className='umf-section-link';b.textContent='전체 보기 ›';
      b.addEventListener('click',()=>{
        const sec=$('.recipeSec');if(!sec)return;
        const open=sec.classList.toggle('show-all');
        b.textContent=open?'접기 ↑':'전체 보기 ›';
      });
      recipeHead.appendChild(b);
    }

    const cells=[...document.querySelectorAll('.summary-cell')];
    const kinds=['warn','ok','need'];
    cells.forEach((cell,i)=>{
      if(cell.querySelector('.summary-icon'))return;
      const span=document.createElement('span');
      span.className=`summary-icon ${kinds[i]||''}`;
      span.innerHTML=summarySvg(kinds[i]);
      cell.appendChild(span);
    });
  }

  function decorateCards(){
    const fav=readFav();
    document.querySelectorAll('#umfRecipeGrid .umf-menu-card').forEach(card=>{
      if(card.querySelector('.umf-fav'))return;
      const name=card.dataset.name||card.querySelector('.umf-menu-name')?.textContent?.trim();
      if(!name)return;
      const b=document.createElement('button');
      b.type='button';b.className='umf-fav'+(fav.has(name)?' on':'');
      b.setAttribute('aria-label',fav.has(name)?`${name} 즐겨찾기 해제`:`${name} 즐겨찾기`);
      b.innerHTML='<svg viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z"/></svg>';
      b.addEventListener('click',e=>{
        e.stopPropagation();
        const set=readFav();
        if(set.has(name))set.delete(name);else set.add(name);
        saveFav(set);
        const on=set.has(name);b.classList.toggle('on',on);b.setAttribute('aria-label',on?`${name} 즐겨찾기 해제`:`${name} 즐겨찾기`);
      });
      card.appendChild(b);
    });
  }

  restructure();decorateCards();
  const grid=$('#umfRecipeGrid');
  if(grid)new MutationObserver(()=>{queueMicrotask(decorateCards)}).observe(grid,{childList:true,subtree:true});
  setTimeout(()=>{restructure();decorateCards()},250);
})();
