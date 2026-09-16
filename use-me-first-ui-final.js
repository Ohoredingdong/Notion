(()=>{
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const IK='use-me-first-v4',SK='use-me-first-seasonings-v1',PK='use-me-first-pantry-v1',LOG='use-me-first-meal-log-v1',QK='use-me-first-quantities-v1',FAV='use-me-first-favorites-v1';
  const read=(k,f)=>{try{const v=JSON.parse(localStorage.getItem(k));return v??f}catch{return f}};
  const write=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
  const readFav=()=>new Set(read(FAV,[]));
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const todayKey=()=>{const d=new Date;return`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
  const daysLeft=iso=>{if(!iso)return null;const a=new Date;a.setHours(0,0,0,0);const b=new Date(iso+'T00:00:00');return Math.ceil((b-a)/864e5)};
  const fullDate=iso=>{if(!iso)return'';const[y,m,d]=iso.split('-');return`${y}.${m}.${d}까지`};
  const currentItems=()=>read(IK,[]), currentSeason=()=>new Set(read(SK,[])), currentPantry=()=>new Set(read(PK,[]));

  const icons={
    calendar:'<svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 9h16"/></svg>',
    chef:'<svg viewBox="0 0 24 24"><path d="M7 18h10v3H7z"/><path d="M7.5 17v-6.1A4.5 4.5 0 0 1 9 2.2a4.6 4.6 0 0 1 3 1.1 4.6 4.6 0 0 1 3-1.1 4.5 4.5 0 0 1 1.5 8.7V17"/></svg>',
    bars:'<svg viewBox="0 0 24 24"><path d="M5 20V9M12 20V4M19 20v-7"/></svg>',
    cart:'<svg viewBox="0 0 24 24"><path d="M3 4h2l2.3 11h9.9l2-7H6.2"/><circle cx="9" cy="19" r="1.2"/><circle cx="17" cy="19" r="1.2"/></svg>',
    fork:'<svg viewBox="0 0 24 24"><path d="M6 3v7M3.5 3v4.5A2.5 2.5 0 0 0 6 10v11M8.5 3v4.5A2.5 2.5 0 0 1 6 10M16 3v18M16 3c3 1.5 4 4 4 7h-4"/></svg>',
    fridge:'<svg viewBox="0 0 24 24"><rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M7 11h10M9.5 6v2.4M9.5 14.6V17"/></svg>',
    bottle:'<svg viewBox="0 0 24 24"><path d="M10 3h4v3l2 2v11a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2V8l2-2V3Z"/><path d="M9 10h6"/></svg>',
    leaf:'<svg viewBox="0 0 24 24"><path d="M20 4C12 4 6 7.5 5 14c-.5 3.4 2 5.5 5.2 5 6.2-.9 8.8-7.2 9.8-15Z"/><path d="M5.5 20c2.4-4.4 5.7-7.6 10.1-10"/></svg>',
    warn:'<svg viewBox="0 0 24 24"><path d="M12 3 2.8 19h18.4L12 3Z"/><path d="M12 9v4M12 17h.01"/></svg>',
    ok:'<svg viewBox="0 0 24 24"><path d="M5 11h14M7 11v7h10v-7M9 11V8a3 3 0 0 1 6 0v3"/><path d="M9 5h6"/></svg>',
    heart:'<svg viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z"/></svg>'
  };
  const ingredientEmoji=name=>/토마토/.test(name)?'🍅':/치즈/.test(name)?'🧀':/버섯/.test(name)?'🍄':/당근/.test(name)?'🥕':/양파/.test(name)?'🧅':/계란|달걀/.test(name)?'🥚':/닭/.test(name)?'🍗':/우유/.test(name)?'🥛':/김치/.test(name)?'🥬':/두부/.test(name)?'◻️':'＋';

  function renderDate(){
    const el=$('#umfDateMain');if(!el)return;
    const d=new Date;el.textContent=new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'long',day:'numeric',weekday:'short'}).format(d);
  }
  function textPool(){return[...currentItems().map(x=>String(x.name||'')),...currentSeason(),...currentPantry()].join(' ')}
  function score(regex,target){const p=textPool();let n=0;for(const r of regex)if(r.test(p))n++;return Math.min(100,Math.round(n/target*100))}
  function ringGradient(vals){const e=[['protein','#75aef5'],['veg','#7ec78a'],['carb','#ffd166'],['ferment','#d7d9de']],sum=e.reduce((a,[k])=>a+Math.max(vals[k],1),0)||4;let cur=0,parts=[];for(const[k,c]of e){const pct=Math.max(vals[k],1)/sum*100;parts.push(`${c} ${cur.toFixed(1)}% ${(cur+pct).toFixed(1)}%`);cur+=pct}return`conic-gradient(${parts.join(',')})`}
  function renderBalance(){
    const vals={protein:score([/계란|달걀/,/닭|고기|참치|두부/,/우유|요거트|치즈/],3),veg:score([/시금치|상추|배추|김치|양파|대파|애호박|토마토|버섯|달래|깻잎|당근/],4),carb:score([/밥|쌀/,/면|라면/,/식빵|빵|감자|고구마/],2),ferment:score([/김치|된장|고추장/,/요거트|요구르트|우유|치즈/],2)};
    for(const[k,v]of Object.entries(vals)){const bar=$(`[data-balance="${k}"]`),txt=$(`[data-balance-pct="${k}"]`);if(bar)bar.style.width=v+'%';if(txt)txt.textContent=v+'%'}
    $('.umf-insights .insight-card:first-child')?.style.setProperty('--ring',ringGradient(vals));
    const note=$('#umfBalanceNote');if(note){const low=Object.entries(vals).sort((a,b)=>a[1]-b[1])[0],labels={protein:'단백질',veg:'채소',carb:'탄수화물',ferment:'발효·유제품'};note.innerHTML=`<span class="v10-leaf">${icons.leaf}</span>등록 재료 기준으로 보면 ${labels[low[0]]} 구성이 가장 약해요.`}
  }
  function parseMissing(){const out=new Map;$$('#umfRecipeGrid .umf-menu-missing').forEach(el=>String(el.textContent||'').replace(/^필요\s*·\s*/,'').split('·').map(x=>x.trim()).filter(Boolean).forEach(x=>out.set(x,(out.get(x)||0)+1)));return[...out.entries()].sort((a,b)=>b[1]-a[1]).slice(0,4)}
  function renderMissing(){
    const box=$('#umfMissingList');if(!box)return;const a=parseMissing();
    box.innerHTML=a.length?a.map(([name,count])=>`<div class="missing-item"><div class="v9-missing-main"><span class="v9-missing-ico">${ingredientEmoji(name)}</span><span class="v9-copy"><div class="missing-name">${esc(name)}</div><div class="missing-use">${count}개 추천 메뉴에서 필요</div></span></div><button class="missing-add" data-add-missing="${esc(name)}" aria-label="${esc(name)} 재료로 추가">+</button></div>`).join(''):'<div class="missing-item"><div><div class="missing-name">부족한 핵심 재료 없음</div><div class="missing-use">지금 있는 재료로 가능한 메뉴가 있어요.</div></div></div>';
    $$('[data-add-missing]',box).forEach(b=>b.onclick=()=>{const name=$('#name');$('#openAdd')?.click();setTimeout(()=>{if(name){name.value=b.dataset.addMissing;name.focus()}},30)})
  }
  function renderSummary(){
    let soon=0;const now=new Date;now.setHours(0,0,0,0);for(const x of currentItems()){if(!x.expiry)continue;const d=new Date(x.expiry+'T00:00:00'),diff=Math.ceil((d-now)/864e5);if(diff>=0&&diff<=2)soon++}
    const possible=$$('#umfRecipeGrid .umf-menu-card:not(.missing)').length,missing=parseMissing().length;
    if($('#umfSoonCount'))$('#umfSoonCount').textContent=soon+'개';if($('#umfPossibleCount'))$('#umfPossibleCount').textContent=possible+'개';if($('#umfMissingCount'))$('#umfMissingCount').textContent=missing+'개';
  }
  function recipeImage(name){const c=$$('#umfRecipeGrid .umf-menu-card').find(x=>(x.dataset.name||$('.umf-menu-name',x)?.textContent?.trim())===name);return $('img',c||document)?.getAttribute('src')||''}
  function renderMeals(){
    const box=$('#umfMealList');if(!box)return;const logs=read(LOG,[]).filter(x=>x.day===todayKey()).slice(0,3);
    box.innerHTML=logs.length?logs.map(x=>{const src=recipeImage(x.name);return`<div class="meal-item"><div class="v9-meal-main"><span class="v9-meal-thumb">${src?`<img src="${src}" alt="" loading="lazy">`:'🍽️'}</span><span class="v9-copy"><div class="meal-name">${esc(x.name)}</div><div class="meal-time">${new Intl.DateTimeFormat('ko-KR',{hour:'2-digit',minute:'2-digit'}).format(new Date(x.ts))}</div></span></div><span style="font-size:10px;color:#34a853">✓</span></div>`}).join(''):'<div class="meal-item"><div><div class="meal-name">아직 기록이 없어요</div><div class="meal-time">추천 메뉴에서 기록을 추가해보세요.</div></div></div>';
  }
  function logSelected(){const c=$('#umfRecipeGrid .umf-menu-card.selected');if(!c)return;const name=$('.umf-menu-name',c)?.textContent?.trim();if(!name)return;const logs=read(LOG,[]);logs.unshift({name,ts:Date.now(),day:todayKey()});write(LOG,logs.slice(0,40));renderMeals()}

  function decorateStatic(){
    const sub=$('.umf-dashboard-sub');if(sub)sub.textContent='지금 있는 재료로, 오늘도 맛있는 하루';
    const dateSub=$('#umfDateSub');if(dateSub)dateSub.textContent='오늘도 좋은 식사 되세요!';
    const date=$('.umf-date');if(date&&!$('.umf-date-icon',date))date.insertAdjacentHTML('afterbegin',`<span class="umf-date-icon" aria-hidden="true">${icons.calendar}</span>`);
    const leftHead=$('.umf-left>.head'),all=$('#all');if(leftHead&&all&&!leftHead.contains(all)){all.classList.add('umf-head-all');leftHead.appendChild(all)}if(all)all.textContent='전체 보기';
    const card=$('.umf-left .card'),add=$('#openAdd');if(card&&add&&!card.contains(add)){add.classList.add('umf-left-add');add.textContent='＋ 재료 추가하기';card.appendChild(add)}
    const ft=$('.umf-left .tab[data-tab="fridge"]'),st=$('.umf-left .tab[data-tab="season"]');if(ft&&!$('.v10-tab-ico',ft))ft.insertAdjacentHTML('afterbegin',`<span class="v10-tab-ico">${icons.fridge}</span>`);if(st&&!$('.v10-tab-ico',st))st.insertAdjacentHTML('afterbegin',`<span class="v10-tab-ico">${icons.bottle}</span>`);
    const rh=$('.recipeSec>.sh');if(rh&&!$('.v10-title-icon',rh))rh.insertAdjacentHTML('afterbegin',`<span class="v10-title-icon">${icons.chef}</span>`);if(rh&&!$('.umf-section-link',rh)){const b=document.createElement('button');b.type='button';b.className='umf-section-link';b.textContent='전체 보기';b.onclick=()=>{const sec=$('.recipeSec');if(!sec)return;const open=sec.classList.toggle('show-all');b.textContent=open?'접기':'전체 보기'};rh.appendChild(b)}
    const cards=$$('.umf-insights .insight-card'),kinds=['bars','cart','fork'];cards.forEach((c,i)=>{if(c&&!$('.v10-insight-icon',c)){const s=document.createElement('span');s.className='v10-insight-icon';s.innerHTML=icons[kinds[i]]||'';c.appendChild(s)}});
    if(cards[0]&&!$('.v10-card-link',cards[0])){const b=document.createElement('button');b.type='button';b.className='v10-card-link';b.textContent='자세히 보기';b.onclick=()=>$('#umfBalanceNote')?.scrollIntoView({block:'nearest',behavior:'smooth'});cards[0].appendChild(b)}
    if(cards[1]&&!$('.v10-card-link',cards[1])){const s=document.createElement('span');s.className='v10-card-link';s.textContent='전체 보기';cards[1].appendChild(s)}
    if(cards[2]&&!$('.v10-card-link',cards[2])){const b=document.createElement('button');b.type='button';b.className='v10-card-link';b.textContent='기록 추가 +';b.onclick=logSelected;cards[2].appendChild(b)}
    if(cards[0])$('.insight-title',cards[0]).textContent='오늘의 영양 밸런스';
    const labels=$$('.summary-label');if(labels[0])labels[0].textContent='곧 유통기한이 돌아오는 재료';if(labels[1])labels[1].textContent='지금 바로 만들 수 있는 레시피';if(labels[2])labels[2].textContent='부족한 재료';
    const summaryKinds=['warn','ok','warn'];$$('.summary-cell').forEach((cell,i)=>{if(!$('.summary-icon',cell)){const s=document.createElement('span');s.className=`summary-icon ${i===0?'warn':i===1?'ok':'need'}`;s.innerHTML=icons[summaryKinds[i]];cell.appendChild(s)}if(!$('.v10-summary-arrow',cell))cell.insertAdjacentHTML('beforeend','<span class="v10-summary-arrow">›</span>')});
  }
  function ensureQuantity(){
    if($('#umfQtyField'))return;const expiry=$('#expiry');if(!expiry)return;const f=document.createElement('div');f.className='field';f.id='umfQtyField';f.innerHTML='<label>수량 <span style="font-weight:400;color:#9a9aa0">(선택)</span></label><input id="umfQty" placeholder="예: 300g, 10개, 1팩">';expiry.closest('.field')?.insertAdjacentElement('afterend',f);
    $('#save')?.addEventListener('click',()=>{const name=$('#name')?.value.trim(),qty=$('#umfQty')?.value.trim();if(!name)return;const map=read(QK,{});if(qty)map[name]=qty;else delete map[name];write(QK,map);setTimeout(()=>{patchRows();if($('#umfQty'))$('#umfQty').value=''},30)},true);
  }
  function patchRows(){
    const items=currentItems(),qty=read(QK,{});$$('#list .row').forEach(row=>{const name=$('.nm',row)?.textContent?.trim();if(!name)return;const item=items.find(x=>String(x.name||'').trim()===name),ex=$('.ex',row),day=$('.day',row);if(item&&ex){const bits=[];if(qty[name])bits.push(qty[name]);if(item.expiry)bits.push(fullDate(item.expiry));ex.textContent=bits.join('   |   ')}if(item&&day){const d=daysLeft(item.expiry);day.classList.remove('v10-urgent','v10-today','v10-safe');if(d===0){day.textContent='오늘';day.classList.add('v10-today')}else if(d!=null&&d<=2){day.textContent=d<0?`D+${Math.abs(d)}`:`D-${d}`;day.classList.add('v10-urgent')}else{day.textContent='여유';day.classList.add('v10-safe')}}patchRowMenu(row)})
  }
  function patchRowMenu(row){const old=$('.rm',row);if(!old||old.dataset.finalMenu)return;const originalDelete=old.onclick,btn=old.cloneNode(true);btn.dataset.finalMenu='1';btn.textContent='⋮';btn.setAttribute('aria-label','재료 메뉴');old.replaceWith(btn);btn.onclick=e=>{e.stopPropagation();$$('.umf-row-menu').forEach(x=>{if(x.parentElement!==row)x.remove()});const existing=$('.umf-row-menu',row);if(existing){existing.remove();return}const menu=document.createElement('div');menu.className='umf-row-menu';menu.innerHTML='<button type="button">삭제</button>';menu.firstElementChild.onclick=ev=>{ev.stopPropagation();menu.remove();if(typeof originalDelete==='function')originalDelete.call(old,ev)};row.appendChild(menu)}}
  function decorateRecipeCards(){const fav=readFav();$$('#umfRecipeGrid .umf-menu-card').forEach(card=>{const name=card.dataset.name||$('.umf-menu-name',card)?.textContent?.trim();if(!name)return;let b=$('.umf-fav',card);if(!b){b=document.createElement('button');b.type='button';b.className='umf-fav';b.innerHTML=icons.heart;b.onclick=e=>{e.stopPropagation();const set=readFav();set.has(name)?set.delete(name):set.add(name);write(FAV,[...set]);b.classList.toggle('on',set.has(name));b.setAttribute('aria-label',set.has(name)?`${name} 즐겨찾기 해제`:`${name} 즐겨찾기`)};card.appendChild(b)}b.classList.toggle('on',fav.has(name));b.setAttribute('aria-label',fav.has(name)?`${name} 즐겨찾기 해제`:`${name} 즐겨찾기`)})}

  let pending=false;
  function refresh(){pending=false;decorateStatic();ensureQuantity();patchRows();decorateRecipeCards();renderBalance();renderMissing();renderSummary();renderMeals()}
  function schedule(){if(pending)return;pending=true;requestAnimationFrame(refresh)}
  function bind(){
    $('#umfTopAdd')?.addEventListener('click',()=>$('#openAdd')?.click());
    $('#umfLogBtn')?.addEventListener('click',logSelected);
    $('#umfClearMeals')?.addEventListener('click',()=>{write(LOG,read(LOG,[]).filter(x=>x.day!==todayKey()));renderMeals()});
    document.addEventListener('click',e=>{if(!e.target.closest('.rm,.umf-row-menu'))$$('.umf-row-menu').forEach(x=>x.remove());if(e.target.closest('.tog,.tab,.tinyAdd,.add,.umf-menu-card,#umfShuffleBtn'))setTimeout(schedule,40)});
    window.addEventListener('storage',schedule);
    const root=$('.umf-columns');if(root)new MutationObserver(records=>{const meaningful=records.some(r=>!r.target.closest?.('#umfMissingList,#umfMealList'));if(meaningful)schedule()}).observe(root,{childList:true,subtree:true});
  }
  renderDate();bind();refresh();setTimeout(schedule,120);
})();
