(()=>{
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const QKEY='use-me-first-quantities-v1', IKEY='use-me-first-v4';
  const read=(k,f)=>{try{const v=JSON.parse(localStorage.getItem(k));return v??f}catch{return f}};
  const write=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const daysLeft=iso=>{if(!iso)return null;const a=new Date; a.setHours(0,0,0,0);const b=new Date(iso+'T00:00:00');return Math.ceil((b-a)/864e5)};
  const fullDate=iso=>{if(!iso)return'';const [y,m,d]=iso.split('-');return `${y}.${m}.${d}까지`};

  const icons={
    chef:'<svg viewBox="0 0 24 24"><path d="M7 18h10v3H7z"/><path d="M7.5 17v-6.1A4.5 4.5 0 0 1 9 2.2a4.6 4.6 0 0 1 3 1.1 4.6 4.6 0 0 1 3-1.1 4.5 4.5 0 0 1 1.5 8.7V17"/></svg>',
    bars:'<svg viewBox="0 0 24 24"><path d="M5 20V9M12 20V4M19 20v-7"/></svg>',
    cart:'<svg viewBox="0 0 24 24"><path d="M3 4h2l2.3 11h9.9l2-7H6.2"/><circle cx="9" cy="19" r="1.2"/><circle cx="17" cy="19" r="1.2"/></svg>',
    fork:'<svg viewBox="0 0 24 24"><path d="M6 3v7M3.5 3v4.5A2.5 2.5 0 0 0 6 10v11M8.5 3v4.5A2.5 2.5 0 0 1 6 10M16 3v18M16 3c3 1.5 4 4 4 7h-4"/></svg>',
    fridge:'<svg viewBox="0 0 24 24"><rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M7 11h10M9.5 6v2.4M9.5 14.6V17"/></svg>',
    bottle:'<svg viewBox="0 0 24 24"><path d="M10 3h4v3l2 2v11a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2V8l2-2V3Z"/><path d="M9 10h6"/></svg>',
    leaf:'<svg viewBox="0 0 24 24"><path d="M20 4C12 4 6 7.5 5 14c-.5 3.4 2 5.5 5.2 5 6.2-.9 8.8-7.2 9.8-15Z"/><path d="M5.5 20c2.4-4.4 5.7-7.6 10.1-10"/></svg>'
  };

  function titleIcon(card,kind){
    if(!card||card.querySelector('.v10-insight-icon'))return;
    const i=document.createElement('span');i.className='v10-insight-icon';i.innerHTML=icons[kind]||'';card.appendChild(i);
  }

  function normalizeLinks(){
    const all=$('.umf-head-all');if(all)all.textContent='전체 보기';
    const recipe=$('.umf-section-link');if(recipe){
      recipe.textContent=$('.recipeSec')?.classList.contains('show-all')?'접기':'전체 보기';
      if(!recipe.dataset.v10){recipe.dataset.v10='1';recipe.addEventListener('click',()=>setTimeout(()=>{recipe.textContent=$('.recipeSec')?.classList.contains('show-all')?'접기':'전체 보기'},0))}
    }
  }

  function decorateTabs(){
    const a=$('.umf-left .tab[data-tab="fridge"]'), b=$('.umf-left .tab[data-tab="season"]');
    if(a&&!a.querySelector('.v10-tab-ico'))a.insertAdjacentHTML('afterbegin',`<span class="v10-tab-ico">${icons.fridge}</span>`);
    if(b&&!b.querySelector('.v10-tab-ico'))b.insertAdjacentHTML('afterbegin',`<span class="v10-tab-ico">${icons.bottle}</span>`);
  }

  function decorateRecipeHeading(){
    const sh=$('.recipeSec>.sh');if(!sh||sh.querySelector('.v10-title-icon'))return;
    sh.insertAdjacentHTML('afterbegin',`<span class="v10-title-icon">${icons.chef}</span>`);
  }

  function ensureRightHeaders(){
    const cards=$$('.umf-insights .insight-card');
    titleIcon(cards[0],'bars'); titleIcon(cards[1],'cart'); titleIcon(cards[2],'fork');
    if(cards[0]&&!cards[0].querySelector('.v10-card-link')){
      const b=document.createElement('button');b.className='v10-card-link';b.type='button';b.textContent='자세히 보기';b.addEventListener('click',()=>cards[0].querySelector('.balance-note')?.scrollIntoView({block:'nearest',behavior:'smooth'}));cards[0].appendChild(b);
    }
    if(cards[1]&&!cards[1].querySelector('.v10-card-link')){
      const s=document.createElement('span');s.className='v10-card-link';s.textContent='전체 보기';cards[1].appendChild(s);
    }
    if(cards[2]&&!cards[2].querySelector('.v10-card-link')){
      const b=document.createElement('button');b.className='v10-card-link';b.type='button';b.textContent='기록 추가 +';b.addEventListener('click',()=>$('#umfLogBtn')?.click());cards[2].appendChild(b);
    }
    const note=$('#umfBalanceNote');if(note&&!note.querySelector('.v10-leaf'))note.insertAdjacentHTML('afterbegin',`<span class="v10-leaf">${icons.leaf}</span>`);
  }

  function ensureQuantityField(){
    const expiry=$('#expiry');if(!expiry||$('#umfQtyField'))return;
    const field=document.createElement('div');field.className='field';field.id='umfQtyField';field.innerHTML='<label>수량 <span style="font-weight:400;color:#9a9aa0">(선택)</span></label><input id="umfQty" placeholder="예: 300g, 10개, 1팩">';
    expiry.closest('.field')?.insertAdjacentElement('afterend',field);
    $('#save')?.addEventListener('click',()=>{
      const name=$('#name')?.value.trim(), qty=$('#umfQty')?.value.trim();
      if(!name)return;
      const map=read(QKEY,{});
      if(qty)map[name]=qty; else delete map[name];
      write(QKEY,map);
      setTimeout(()=>{patchRows();if($('#umfQty'))$('#umfQty').value=''},40);
    });
  }

  function patchRows(){
    const items=read(IKEY,[]), qty=read(QKEY,{});
    $$('#list .row').forEach(row=>{
      const name=$('.nm',row)?.textContent?.trim();if(!name)return;
      const item=items.find(x=>String(x.name||'').trim()===name);
      const ex=$('.ex',row), day=$('.day',row);
      if(item&&ex){const bits=[];if(qty[name])bits.push(qty[name]);if(item.expiry)bits.push(fullDate(item.expiry));ex.textContent=bits.join('   |   ')}
      if(item&&day){
        const d=daysLeft(item.expiry);day.classList.remove('v10-urgent','v10-today','v10-safe');
        if(d===0){day.textContent='오늘';day.classList.add('v10-today')}
        else if(d!=null&&d<=2){day.textContent=d<0?`D+${Math.abs(d)}`:`D-${d}`;day.classList.add('v10-urgent')}
        else {day.textContent='여유';day.classList.add('v10-safe')}
      }
      patchRowMenu(row);
    });
  }

  function patchRowMenu(row){
    const old=$('.rm',row);if(!old||old.dataset.v10Menu)return;
    const originalDelete=old.onclick;
    const btn=old.cloneNode(true);btn.dataset.v10Menu='1';btn.textContent='⋮';btn.setAttribute('aria-label','재료 메뉴');old.replaceWith(btn);
    btn.addEventListener('click',e=>{
      e.stopPropagation();
      $$('.umf-row-menu').forEach(x=>{if(x.parentElement!==row)x.remove()});
      const existing=$('.umf-row-menu',row);if(existing){existing.remove();return}
      const menu=document.createElement('div');menu.className='umf-row-menu';menu.innerHTML='<button type="button">삭제</button>';
      menu.querySelector('button').addEventListener('click',ev=>{ev.stopPropagation();menu.remove();if(typeof originalDelete==='function')originalDelete.call(old,ev)});
      row.appendChild(menu);
    });
  }

  function summaryArrows(){
    $$('.summary-cell').forEach(cell=>{if(!cell.querySelector('.v10-summary-arrow'))cell.insertAdjacentHTML('beforeend','<span class="v10-summary-arrow">›</span>')});
  }

  function run(){normalizeLinks();decorateTabs();decorateRecipeHeading();ensureRightHeaders();ensureQuantityField();patchRows();summaryArrows()}
  run();
  for(const s of['#list','#umfRecipeGrid','#umfMissingList','#umfMealList']){const n=$(s);if(n)new MutationObserver(()=>queueMicrotask(run)).observe(n,{childList:true,subtree:true})}
  document.addEventListener('click',e=>{if(!e.target.closest('.rm,.umf-row-menu'))$$('.umf-row-menu').forEach(x=>x.remove())});
  window.addEventListener('storage',()=>setTimeout(run,20));
  setTimeout(run,250);
})();
