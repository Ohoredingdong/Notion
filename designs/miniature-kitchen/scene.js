/* Miniature scene; the journal adapter persists only its separate preview key. */
(() => {
  'use strict';
  const FRIDGE = './designs/miniature-kitchen/assets/fridge-atlas.png';
  const DECOR = './designs/miniature-kitchen/assets/decor-atlas.png';
  const A=window.UMFKitchenArt, $=s=>document.querySelector(s), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
  const mode=document.body.dataset.mode==='widget'?'widget':'app';
  const date=(offset=0)=>{const d=new Date();d.setDate(d.getDate()+offset);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');};
  const panels={
    freshLeft:{name:'냉장 왼쪽',kind:'냉장',x:.009,y:.004,w:.495,h:.538,zx:.052,zy:.047,zw:.425,zh:.475},
    freshRight:{name:'냉장 오른쪽',kind:'냉장',x:.507,y:.004,w:.484,h:.538,zx:.535,zy:.047,zw:.423,zh:.475},
    frozenLeft:{name:'냉동 왼쪽',kind:'냉동',x:.009,y:.547,w:.495,h:.418,zx:.055,zy:.573,zw:.418,zh:.342},
    frozenRight:{name:'냉동 오른쪽',kind:'냉동',x:.507,y:.547,w:.484,h:.418,zx:.538,zy:.573,zw:.415,zh:.342}
  };
  const props={utensils:{name:'도자기 도구통',crop:[48,15,550,648]},flowers:{name:'데이지 유리병',crop:[735,25,510,640]},cup:{name:'우드 트레이와 찻잔',crop:[24,685,694,495]},cookies:{name:'쿠키 유리병',crop:[773,675,445,504]}};
  let serial=20, layer=20, cropSerial=0, decorating=false, selected=null, active=null, previousFocus=null;
  const closing=new Set(),closingTimers=new Map();
  const doors={freshLeft:false,freshRight:false,frozenLeft:false,frozenRight:false};
  const items=[
    {id:'egg',kind:'food',name:'계란',quantity:'6개',expiry:date(),zone:'freshLeft',x:.26,y:.32,z:1},
    {id:'milk',kind:'food',name:'우유',quantity:'500ml',expiry:date(1),zone:'freshLeft',x:.76,y:.32,z:2},
    {id:'tofu',kind:'food',name:'두부',quantity:'1모',expiry:date(3),zone:'freshLeft',x:.26,y:.63,z:3},
    {id:'broccoli',kind:'food',name:'브로콜리',quantity:'1개',expiry:date(2),zone:'freshLeft',x:.74,y:.95,z:4},
    {id:'tomato',kind:'food',name:'토마토',quantity:'3개',expiry:date(4),zone:'freshRight',x:.28,y:.63,z:5},
    {id:'fish',kind:'food',name:'생선',quantity:'2조각',expiry:date(14),zone:'frozenLeft',x:.43,y:.48,z:6},
    ...['간장','고추장','된장','소금'].map((name,index)=>({id:'spice'+index,kind:'seasoning',name,quantity:'',expiry:date(30+index*10),zone:'seasoning',x:.1+index*.265,y:.98,z:7+index})),
    {id:'meal',kind:'meal',name:'계란 볶음밥',zone:'counter',x:.46,y:.96,z:12},
    {id:'flowers',kind:'decor',art:'flowers',name:props.flowers.name,zone:'counter',x:.83,y:.91,z:13},
    {id:'cup',kind:'decor',art:'cup',name:props.cup.name,zone:'counter',x:.12,y:.98,z:14}
  ];
  function crop(asset,box,total,cls='') {
    const id='mini-crop-'+(++cropSerial),[x,y,w,h]=box;
    return `<svg class="${cls}" viewBox="${box.join(' ')}" preserveAspectRatio="none" aria-hidden="true" focusable="false"><defs><clipPath id="${id}"><rect x="${x}" y="${y}" width="${w}" height="${h}"/></clipPath></defs><image href="${asset}" x="0" y="0" width="${total[0]}" height="${total[1]}" clip-path="url(#${id})"/></svg>`;
  }
  const decorArt=key=>crop(DECOR,props[key].crop,[1286,1223],'decor-art');
  function art(item) {
    if(item.kind==='decor')return decorArt(item.art);
    if(item.kind==='meal')return A.dishArt({id:item.name});
    if(item.kind==='seasoning')return A.seasoningArt(item.name,'food-art');
    return A.foodArt(A.foodIdForName(item.name));
  }
  function announce(message){$('#liveMessage').textContent=message;}
  function compact(){return mode==='widget'||$('.shell').clientWidth<960;}
  function syncLayout(){
    // One 1536 × 1024 room: furniture, food and backdrop share its scale.
    // Reserve the header/tabs and a small floor margin in the FIRST viewport.
    const shell=$('.shell'),view=$('.kitchen-view'),room=$('.room');
    const available=Math.min(innerWidth-28,mode==='widget'?692:1452);
    const top=$('.masthead').offsetHeight+$('.camera-tabs').offsetHeight+12;
    // Frame the installed fridge, not the unused foreground floor. Its apparent
    // size stays the same while the appliance fits the actual tile bay behind it.
    const camera=document.body.dataset.camera;
    const frame={
      fridge:{height:880,top:16,width:700,center:768,maxWidth:1536},
      seasoning:{height:640,top:80,width:600,center:300,maxWidth:600},
      counter:{height:640,top:304,width:600,center:1236,maxWidth:600}
    }[camera];
    // Reserve the journal summary without changing the accepted scene framing.
    const controls=104-50*clamp((innerWidth-560)/160,0,1);
    const scale=Math.max(.2,Math.min(819.2/frame.height,available/frame.width,Math.max(280,innerHeight-top-controls-24)/frame.height));
    shell.style.setProperty('--scene-scale',String(scale));
    shell.style.setProperty('--scene-height',scale*frame.height+'px');
    shell.style.setProperty('--scene-y',-scale*frame.top+'px');
    shell.style.setProperty('--scene-max-width',scale*frame.maxWidth+28+'px');
    shell.style.setProperty('--object',Math.max(94,44/scale)+'px');
    shell.style.setProperty('--seasoning',Math.max(100,44/scale)+'px');
    view.classList.toggle('is-compact',compact());
    const x=clamp(room.clientWidth/2-frame.center*scale,Math.min(0,room.clientWidth-1536*scale),0);
    shell.style.setProperty('--scene-x',x+'px');
    renderDisplays();
  }
  function setCamera(camera) {
    cleanup();document.body.dataset.camera=camera;
    for(const b of document.querySelectorAll('.camera-tabs button'))b.setAttribute('aria-pressed',String(b.dataset.camera===camera));
    $('#roomMessage').textContent={fridge:'냉장고 문을 열어, 우리 집 재료를 살펴봐요.',seasoning:'작은 양념병을 옮겨, 나만의 선반을 정리해요.',counter:'오늘의 한 끼와 좋아하는 소품을 놓아봐요.'}[camera];
    $('#sceneNote').textContent=camera==='seasoning'?'양념병을 누르면 수량·기한을 살펴볼 수 있어요.':decorating?'소품을 끌어 놓고, 누르면 앞뒤 순서도 바꿀 수 있어요.':'음식과 소품을 눌러 살펴봐요.';
    syncLayout();constrainItems();
  }
  function renderDisplays() {
    const root=$('#fridgeDisplays');if(!root)return;
    const stage=$('.fridge-stage').getBoundingClientRect(),room=$('.room').getBoundingClientRect();
    root.hidden=document.body.dataset.camera!=='fridge';
    // Calendar-day comparison avoids DST and midnight timezone rounding.
    const dayNumber=value=>{const [y,m,d]=value.split('-').map(Number);return Date.UTC(y,m-1,d)/86400000;};
    const today=dayNumber(date());
    const near=items.filter(r=>(r.kind==='food'||r.kind==='seasoning')&&r.expiry&&dayNumber(r.expiry)-today<=3).sort((a,b)=>a.expiry.localeCompare(b.expiry));
    const counts={overdue:0,today:0,tomorrow:0,soon:0};
    for(const item of near){const days=dayNumber(item.expiry)-today;counts[days<0?'overdue':days===0?'today':days===1?'tomorrow':'soon']++;}
    const distribution=Object.entries(counts).filter(([,count])=>count).map(([tone,count])=>`<i data-expiry-tone="${tone}" style="flex:${count}"></i>`).join('');
    const distributionLabel=`기한 경과 ${counts.overdue}건, 오늘 ${counts.today}건, 내일 ${counts.tomorrow}건, 2~3일 이내 ${counts.soon}건`;
    const cleanName=name=>String(name).normalize('NFKC').replace(/\s+/g,'').toLowerCase();
    const names=new Set(items.filter(r=>(r.kind==='food'||r.kind==='seasoning')&&(!r.expiry||dayNumber(r.expiry)>=today)).map(r=>cleanName(r.name)));
    root.innerHTML=['freshLeft','freshRight'].map(key=>{
      const p=panels[key],left=key==='freshLeft',meal=items.find(r=>r.kind==='meal'),hidden=doors[key]||closing.has(key);
      // Fit inside the door's flat surface, leaving the curved edge and handle
      // clear. Keep text at native size rather than scaling a tall dashboard.
      const width=panels.freshRight.w*.70*stage.width,doorHeight=p.h*stage.height;
      const height=Math.min(doorHeight*.72,Math.max(126,Math.min(176,doorHeight*.51)));
      const layout=height<116?'summary':width<100||height<158?'compact':'standard';
      const x=stage.x-room.x+(p.x+p.w*(left?.10:.20))*stage.width;
      // The original atlas already has recessed screens at y188..394. Center
      // the live screen over that recess so it never peeks out below the UI.
      const center=layout==='summary'?.47:layout==='compact'?.49:.518;
      const y=stage.y-room.y+p.y*stage.height+doorHeight*center-height/2;
      const visible=near.slice(0,layout==='summary'?1:layout==='standard'?3:2),overdue=counts.overdue>0;
      const recipe=window.KitchenCatalog.find(r=>r.name===meal.name);
      const title=left?'유통기한 임박':'오늘의 추천메뉴';
      const empty=layout==='summary'?'임박 재료<br>없어요':'3일 이내<br>임박 재료 없어요';
      // This is a count of registered ingredient names, not a quantity check
      // or a claim that the whole recipe can be cooked with the current stock.
      const required=recipe?[...new Set([...recipe.f,...recipe.s,...recipe.p])]:[];
      const missing=required.filter(name=>!names.has(cleanName(name))&&!name.split('/').some(alias=>names.has(cleanName(alias))));
      const registered=required.length-missing.length,ratio=required.length?100*registered/required.length:0;
      const counters=`<dl class="lcd-counters" aria-label="기한별 재료·양념 기록"><div data-expiry-tone="today"><dt>오늘</dt><dd>${counts.today}</dd></div><div data-expiry-tone="tomorrow"><dt>내일</dt><dd>${counts.tomorrow}</dd></div><div data-expiry-tone="soon"><dt>2~3일</dt><dd>${counts.soon}</dd></div></dl>`;
      const total=counts.overdue?`경과 ${counts.overdue}`:`${near.length}건`;
      const totalBadge=left?`<span class="lcd-total ${overdue?'is-overdue':''}" aria-label="관리 기록 총 ${near.length}건, 기한 경과 ${counts.overdue}건">${total}</span>`:'';
      const rows=visible.map(r=>{
        const days=dayNumber(r.expiry)-today,tone=days<0?'overdue':days===0?'today':days===1?'tomorrow':'soon';
        const label=days<0?'지남':days===0?'오늘':days===1?'내일':days+'일 내';
        return `<div class="lcd-row" data-expiry-tone="${tone}"><span class="lcd-food">${art(r)}</span><div class="lcd-item-copy"><b title="${esc(r.name)}">${esc(r.name)}</b><div class="lcd-item-meta"><small class="lcd-deadline" title="${esc(r.expiry)}${days<0?' · 기한 지남':''}">${label}</small><span class="lcd-quantity" title="${esc(r.quantity)}">${esc(r.quantity)}</span></div></div></div>`;
      }).join('');
      const stock=recipe?`<div class="lcd-stock" title="기록된 재료 이름 중 일치하는 종류 수 · 기한 경과 항목 제외 · 수량 미검증"><div class="lcd-stock-label"><span>재료<span class="lcd-stock-word"> 기록</span></span><b>${registered}/${required.length}</b></div><div class="lcd-stock-track" role="meter" aria-label="기록된 재료 종류 · 이름 기준, 수량 미검증" aria-valuemin="0" aria-valuemax="${required.length||1}" aria-valuenow="${registered}"><i style="width:${ratio}%"></i></div></div>`:'<div class="lcd-stock"><span>재료 미입력</span></div>';
      const missingNote=recipe?`<p class="lcd-missing" title="${esc(missing.join(' · '))}"><span>${missing.length?'미등록 재료':'재료 이름 기록됨'}</span>${missing.length?`<b>${esc(missing.slice(0,2).join(' · '))}${missing.length>2?' 외 '+(missing.length-2):''}</b>`:'<b>수량은 확인해 주세요</b>'}</p>`:'';
      const content=left?`${counters}<div class="lcd-list" style="--lcd-rows:${visible.length||1}">${rows||'<p class="lcd-empty">'+empty+'</p>'}</div><div class="lcd-footer lcd-expiry-footer"><span>${overdue?'경과 '+counts.overdue+'건':near.length?'임박 '+near.length+'건':'보관 '+items.filter(r=>r.kind==='food'||r.kind==='seasoning').length+'건'}</span><div class="lcd-expiry-track" role="img" aria-label="${distributionLabel}">${distribution}</div></div>`:`<div class="lcd-menu"><div class="lcd-dish">${A.dishArt({id:meal.name})}</div><b class="lcd-recipe">${esc(meal.name)}</b></div><div class="lcd-footer lcd-recipe-facts"><span>${esc(recipe?.time||'시간 미입력')}</span><span class="lcd-level">${esc(recipe?.level||'')}</span></div><div class="lcd-recipe-detail">${stock}${missingNote}</div>`;
      return `<section class="fridge-lcd ${hidden?'':'is-on'}" data-lcd="${key}" data-lcd-layout="${layout}" aria-label="${title} 디스플레이" style="left:${Math.round(x)}px;top:${Math.round(y)}px;width:${Math.round(width)}px;height:${Math.round(height)}px" ${hidden?'hidden':''}><div class="lcd-screen"><div class="lcd-header"><strong class="lcd-title">${title}</strong>${totalBadge}</div>${content}</div></section>`;
    }).join('');window.dispatchEvent(new Event('mini-kitchen:layout'));
  }
  $('#cabinet').innerHTML=crop(FRIDGE,[833,10,570,994],[1536,1024]);
  for(const [key,p] of Object.entries(panels)) {
    const zone=document.createElement('div');zone.className='drop-zone';zone.dataset.zone=key;zone.setAttribute('aria-label',p.name+' 재료');Object.assign(zone.style,{left:p.zx*100+'%',top:p.zy*100+'%',width:p.zw*100+'%',height:p.zh*100+'%'});$('#fridgeInteriors').appendChild(zone);
    const door=document.createElement('button');door.type='button';door.className='door'+(key.endsWith('Right')?' right':'')+(key.startsWith('frozen')?' frozen':'');door.dataset.door=key;Object.assign(door.style,{left:p.x*100+'%',top:p.y*100+'%',width:p.w*100+'%',height:p.h*100+'%'});$('#fridgeDoors').appendChild(door);door.addEventListener('transitionend',event=>{if(event.target===door&&event.propertyName==='transform')finishClosing(key);});
  }
  function place(button,item){button.style.left=item.x*100+'%';button.style.top=item.y*100+'%';button.style.zIndex=String(item.z);}
  function constrainItems(){for(const button of document.querySelectorAll('.drop-zone>.item')){const item=items.find(r=>r.id===button.dataset.item),width=button.parentElement.clientWidth;if(!item||!width||getComputedStyle(button).visibility!=='visible')continue;const half=Math.min(.5,button.offsetWidth/2/width);item.x=clamp(item.x,half,1-half);place(button,item);}}
  function itemButton(item) {
    const b=document.createElement('button');b.type='button';b.className='item '+item.kind;b.dataset.item=item.id;if(item.art)b.dataset.art=item.art;
    b.innerHTML=art(item)+(item.quantity?`<span class="quantity">${esc(item.quantity)}</span>`:'')+`<span class="item-name">${esc(item.name)}</span>`;
    b.setAttribute('aria-label',item.name+(item.quantity?' '+item.quantity:'')+(item.expiry?' · '+item.expiry:'')+(item.kind==='decor'?' · 소품 위치 바꾸기':' · 누르면 살펴보기, 끌어서 이동'));b.classList.toggle('is-selected',selected===item.id);place(b,item);return b;
  }
  function render() {
    document.body.classList.toggle('is-decorating',decorating);$('#decorationTools').hidden=!decorating;$('#decorate').setAttribute('aria-pressed',String(decorating));$('#decorate>span:last-child').textContent=decorating?'꾸미기 완료':'꾸미기';
    for(const [key,p] of Object.entries(panels)) {
      const door=$('[data-door="'+key+'"]'),open=doors[key];door.innerHTML=crop(FRIDGE,[137+570*p.x,10+994*p.y,570*p.w,994*p.h],[1536,1024])+`<span class="door-back"></span><span class="door-label">${p.kind}</span>`;door.classList.toggle('is-open',open);door.setAttribute('aria-expanded',String(open));door.setAttribute('aria-label',p.name+' 문 '+(open?'닫기':'열기'));door.tabIndex=0;
      const zone=$('[data-zone="'+key+'"]');zone.hidden=!open;zone.inert=!open;
    }
    for(const zone of document.querySelectorAll('.drop-zone')){for(const child of zone.querySelectorAll('.item'))child.remove();for(const item of items.filter(r=>r.zone===zone.dataset.zone))zone.appendChild(itemButton(item));}constrainItems();renderDisplays();window.dispatchEvent(new Event('mini-kitchen:change'));
  }
  function finishClosing(key){clearTimeout(closingTimers.get(key));closingTimers.delete(key);if(closing.delete(key))renderDisplays();}
  function toggle(key){cleanup();finishClosing(key);const willClose=doors[key];if(willClose&&!matchMedia('(prefers-reduced-motion: reduce)').matches){closing.add(key);closingTimers.set(key,setTimeout(()=>finishClosing(key),650));}doors[key]=!doors[key];render();announce(panels[key].name+' 문을 '+(doors[key]?'열었어요.':'닫았어요.'));}
  function openTray(title,content,eyebrow='MY LITTLE KITCHEN') {
    previousFocus=document.activeElement;$('#trayTitle').textContent=title;$('#trayEyebrow').textContent=eyebrow;$('#trayContent').innerHTML=content;if(!$('#tray').open)$('#tray').showModal();$('#tray').scrollTop=0;
  }
  function closeTray(){$('#tray').close();if(previousFocus?.isConnected)previousFocus.focus({preventScroll:true});}
  function showAdd(){openTray('부엌에 재료를 담아봐요',`<p class="tray-note">시안용 재료예요. 고른 재료는 열린 냉장칸에 놓이고, 눌러서 수량과 기한을 바꿀 수 있어요.</p><div class="palette">${['계란','우유','두부','브로콜리','토마토','대파','당근','생선'].map(name=>`<button type="button" data-add-food="${esc(name)}">${A.foodArt(A.foodIdForName(name))}<strong>${esc(name)}</strong><small>부엌에 담기</small></button>`).join('')}</div>`);}
  function showDecor() {
    decorating=true;setCamera('counter');render();openTray('마음에 드는 소품을 놓아봐요',`<p class="tray-note">소품을 골라 조리대에 놓고 자유롭게 옮겨요. 소품을 누르면 앞뒤 순서와 배치를 바꿀 수 있어요.</p><div class="palette">${Object.entries(props).map(([key,p])=>`<button type="button" data-add-prop="${key}">${decorArt(key)}<strong>${p.name}</strong><small>${items.some(r=>r.art===key)?'이미 놓았어요 · 하나 더 놓기':'조리대에 놓기'}</small></button>`).join('')}</div><h3 class="placed-title">놓아둔 소품</h3><p class="tray-note">뒤에 가려진 소품도 여기서 고를 수 있어요.</p><div class="placed-props">${items.filter(r=>r.kind==='decor').map(r=>`<button type="button" data-select-prop="${esc(r.id)}">${art(r)}<span>${esc(r.name)}<br>선택해서 배치 바꾸기</span></button>`).join('')}</div><div class="tray-actions"><button type="button" class="small-action primary" data-close>부엌에서 옮겨보기</button></div>`);
  }
  function showRecipes(){openTray('오늘은 어떤 한 끼가 좋을까요?',`<p class="tray-note">조리대에 놓을 요리 카드를 골라봐요. 기존 요리 8종을 살펴봐요. 영양은 식사 기록에 직접 입력한 값으로 계산해요.</p><div class="recipe-sheet">${window.KitchenCatalog.map(({name,f})=>`<button type="button" class="recipe-option" data-recipe="${name}" aria-pressed="${items.find(r=>r.kind==='meal').name===name}">${A.dishArt({id:name})}<strong>${name}</strong><small>${f.join(' · ')}</small></button>`).join('')}</div>`,'TODAY’S LITTLE MEAL');}
  function showItem(item) {
    selected=item.id;render();if(item.kind==='meal'){showRecipes();return;}
    if(item.kind==='decor') {
      decorating=true;render();openTray(item.name,`<div class="ingredient-preview">${art(item)}</div><p class="tray-note">창을 닫고 소품을 끌어 위치를 바꿔보세요. 겹쳐 놓고 앞뒤 순서도 고를 수 있어요.</p><div class="tray-actions"><button type="button" class="small-action" data-layer="back" data-id="${esc(item.id)}">뒤로 보내기</button><button type="button" class="small-action" data-layer="front" data-id="${esc(item.id)}">앞으로 가져오기</button><button type="button" class="small-action" data-remove="${esc(item.id)}">소품 치우기</button><button type="button" class="small-action primary" data-close>옮기기</button></div>`);return;
    }
    const zones={...Object.fromEntries(Object.entries(panels).map(([key,p])=>[key,p.name])),seasoning:'양념 선반',counter:'조리대'};
    openTray(item.name,`<form id="ingredientForm"><div class="ingredient-form"><div class="ingredient-preview">${art(item)}</div><div class="form-fields"><label>수량<input name="quantity" value="${esc(item.quantity)}" maxlength="40" placeholder="예: 2개"></label><label>유통·소비기한<input name="expiry" type="date" min="1900-01-01" max="9999-12-31" value="${esc(item.expiry)}"></label><label>놓을 곳<select name="zone">${Object.entries(zones).map(([key,name])=>`<option value="${key}" ${item.zone===key?'selected':''}>${name}</option>`).join('')}</select></label><span class="hint">이 시안의 예시 값만 바뀌어요.</span></div></div><div class="tray-actions"><button type="button" class="small-action" data-close>닫기</button><button type="submit" class="small-action primary">시안에 적용</button></div></form>`,'OUR INGREDIENTS');
    $('#ingredientForm').addEventListener('submit',event=>{event.preventDefault();const f=new FormData(event.currentTarget),next=f.get('zone');item.quantity=f.get('quantity').trim();item.expiry=f.get('expiry');if(item.zone!==next){item.zone=next;item.x=.5;item.y=.63;item.z=++layer;}if(panels[next])doors[next]=true;if(compact())setCamera(panels[next]?'fridge':next==='seasoning'?'seasoning':'counter');render();closeTray();announce(item.name+'의 시안 값을 바꿨어요.');});
  }
  function moveLayer(id,direction){const item=items.find(r=>r.id===id);if(!item)return;const order=items.filter(r=>r.zone===item.zone&&r!==item).sort((a,b)=>a.z-b.z);if(direction==='front')order.push(item);else order.unshift(item);order.forEach((r,i)=>{r.z=i+1;});render();closeTray();announce(item.name+'을 '+(direction==='front'?'앞에':'뒤에')+' 놓았어요.');}
  let ghost=null, scrollFrame=0, pointer=null;
  function cleanup(){cancelAnimationFrame(scrollFrame);scrollFrame=0;pointer=null;if(active){active.button.classList.remove('is-dragging');try{active.button.releasePointerCapture(active.pointer);}catch(_){}active=null;}ghost?.remove();ghost=null;for(const zone of document.querySelectorAll('.is-over'))zone.classList.remove('is-over');}
  function dropAt(x,y){return document.elementFromPoint(x,y)?.closest('.drop-zone');}
  function highlightDrop(x,y){for(const z of document.querySelectorAll('.is-over'))z.classList.remove('is-over');const target=dropAt(x,y);if(active&&target&&(!panels[target.dataset.zone]||doors[target.dataset.zone])&&(active.item.kind!=='decor'||target.dataset.zone==='counter'))target.classList.add('is-over');}
  function scrollDrag(){
    scrollFrame=0;if(!active?.moved||!pointer)return;
    const edge=72,y=pointer.y,delta=y<edge?-Math.ceil(18*Math.min(1,(edge-y)/edge)):y>innerHeight-edge?Math.ceil(18*Math.min(1,(y-innerHeight+edge)/edge)):0;
    if(!delta)return;
    const before=window.scrollY;window.scrollBy(0,delta);
    if(window.scrollY!==before){highlightDrop(pointer.x,pointer.y);scrollFrame=requestAnimationFrame(scrollDrag);}
  }
  document.addEventListener('pointerdown',event=>{
    const button=event.target.closest('.room .item');if(!button||active||event.isPrimary===false||event.button!==0)return;const item=items.find(r=>r.id===button.dataset.item);if(!item)return;if(item.kind==='decor'&&!decorating)return;
    const rect=button.getBoundingClientRect();active={item,button,pointer:event.pointerId,startX:event.clientX,startY:event.clientY,moved:false,w:rect.width,h:rect.height,ax:(event.clientX-rect.left)/rect.width,ay:(event.clientY-rect.top)/rect.height};button.focus({preventScroll:true});button.setPointerCapture?.(event.pointerId);event.preventDefault();
  });
  window.addEventListener('pointermove',event=>{
    const drag=active;if(!drag||event.pointerId!==drag.pointer)return;if(!drag.moved&&Math.hypot(event.clientX-drag.startX,event.clientY-drag.startY)<6)return;event.preventDefault();
    if(!drag.moved){drag.moved=true;drag.button.classList.add('is-dragging');ghost=itemButton(drag.item);ghost.classList.add('ghost');ghost.removeAttribute('data-item');ghost.setAttribute('aria-hidden','true');ghost.tabIndex=-1;ghost.disabled=true;Object.assign(ghost.style,{width:drag.w+'px',height:drag.h+'px'});document.body.appendChild(ghost);}
    ghost.style.left=event.clientX-drag.w*drag.ax+'px';ghost.style.top=event.clientY-drag.h*drag.ay+'px';pointer={x:event.clientX,y:event.clientY};highlightDrop(pointer.x,pointer.y);if(!scrollFrame)scrollFrame=requestAnimationFrame(scrollDrag);
  },{passive:false});
  window.addEventListener('pointerup',event=>{
    const drag=active;if(!drag||event.pointerId!==drag.pointer)return;event.preventDefault();const target=dropAt(event.clientX,event.clientY),wasMoved=drag.moved;cleanup();if(!wasMoved){showItem(drag.item);return;}
    const zone=target?.dataset.zone;if(!zone||(panels[zone]&&!doors[zone])||((drag.item.kind==='decor'||drag.item.kind==='meal')&&zone!=='counter')){announce('놓을 수 있는 선반이나 조리대에 옮겨주세요.');return;}
    const rect=target.getBoundingClientRect();drag.item.zone=zone;drag.item.x=clamp((event.clientX-drag.w*drag.ax+drag.w/2-rect.left)/rect.width,drag.w/2/rect.width,1-drag.w/2/rect.width);drag.item.y=clamp((event.clientY+drag.h*(1-drag.ay)-rect.top)/rect.height,Math.min(1,drag.h/rect.height),1);drag.item.z=++layer;selected=drag.item.id;render();announce(drag.item.name+'을 원하는 자리에 놓았어요.');
  });
  window.addEventListener('pointercancel',cleanup);window.addEventListener('blur',cleanup);window.addEventListener('resize',()=>{cleanup();syncLayout();constrainItems();});
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&active){event.preventDefault();cleanup();announce('이동을 취소했어요.');return;}const button=event.target.closest('.room .item');if(!button)return;const item=items.find(r=>r.id===button.dataset.item);if(!item)return;
    if(event.key==='Enter'||event.key===' '){event.preventDefault();showItem(item);return;}
    const vector={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];if(vector&&(item.kind!=='decor'||decorating)){event.preventDefault();const step=event.shiftKey ? .1 : .025;item.x=clamp(item.x+vector[0]*step,.15,.85);item.y=clamp(item.y+vector[1]*step,.2,1);item.z=++layer;place(button,item);window.dispatchEvent(new Event('mini-kitchen:change'));announce(item.name+' 위치를 바꿨어요.');}
  });
  document.addEventListener('click',event=>{
    const button=event.target.closest('button');if(!button)return;if(button.dataset.door)toggle(button.dataset.door);if(button.dataset.camera)setCamera(button.dataset.camera);
    if(button.id==='addFood')showAdd();if(button.id==='recipes')showRecipes();if(button.id==='decorate'){if(decorating){decorating=false;selected=null;render();announce('소품 배치를 마쳤어요.');}else showDecor();}
    if(button.id==='propList')showDecor();
    if(button.dataset.selectProp){const item=items.find(r=>r.id===button.dataset.selectProp&&r.kind==='decor');if(item)showItem(item);}
    if(button.id==='closeTray'||button.hasAttribute('data-close'))closeTray();
    if(button.dataset.addFood){const id='added'+(++serial),name=button.dataset.addFood;items.push({id,kind:'food',name,quantity:'1개',expiry:date(3),zone:'freshLeft',x:.5,y:.63,z:++layer});doors.freshLeft=true;setCamera('fridge');selected=id;render();closeTray();announce(name+'을 시안 냉장고에 담았어요.');}
    if(button.dataset.addProp){const key=button.dataset.addProp;items.push({id:'decor'+(++serial),kind:'decor',art:key,name:props[key].name,zone:'counter',x:.56,y:.98,z:++layer});setCamera('counter');render();closeTray();announce(props[key].name+'을 놓았어요. 끌어 원하는 자리에 놓아보세요.');}
    if(button.dataset.layer)moveLayer(button.dataset.id,button.dataset.layer);if(button.dataset.remove){const index=items.findIndex(r=>r.id===button.dataset.remove&&r.kind==='decor');if(index>=0){items.splice(index,1);selected=null;render();closeTray();announce('소품을 치웠어요.');}}
    if(button.dataset.recipe){items.find(r=>r.kind==='meal').name=button.dataset.recipe;setCamera('counter');render();closeTray();announce('조리대에 '+button.dataset.recipe+'을 놓았어요.');window.dispatchEvent(new CustomEvent('mini-kitchen:recipe',{detail:{name:button.dataset.recipe}}));}
    if(button.id==='help')openTray('작은 부엌을 만져봐요',`<ul class="help-list"><li>냉장고 문을 누르면 열리고, 열린 문을 다시 누르면 닫혀요.</li><li>재료·양념병은 누르면 수량·기한을 살펴보고, 끌어서 옮길 수 있어요.</li><li>다른 칸으로 옮길 때는 그 문을 먼저 열어주세요.</li><li>‘꾸미기’에서 소품을 놓고 끌어 배치해요.</li><li>재료와 소품은 겹쳐 놓을 수 있고, 방향키로도 움직여요.</li><li>작은 화면은 냉장고·양념 선반·조리대를 골라 크게 봐요.</li></ul><p class="tray-note">기존 앱과 분리된 시안이에요. 저장 가능한 브라우저에서는 재료·식사·꾸밈 기록을 보관해요. 임시 세션에서는 식사·영양과 도감의 백업 탭을 이용해 주세요. 영양은 직접 입력한 값으로 계산하며 사진 인식·자동 영양 추정·기존 앱 동기화는 연결 전이에요.</p>`);
  });
  $('#tray').addEventListener('click',event=>{if(event.target!==$('#tray'))return;const r=$('#tray').getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)closeTray();});
  for(const node of document.querySelectorAll('[data-icon]'))node.innerHTML=A.icon(node.dataset.icon);
  document.title='한끼의 부엌 · '+(mode==='widget'?'위젯':'앱')+' 미니어처 시안';syncLayout();render();
  window.MiniKitchen=Object.freeze({
    isDoorClosing:key=>closing.has(key),
    getSnapshot:()=>JSON.parse(JSON.stringify({mode,doors,items,decorating,camera:document.body.dataset.camera})),
    exportWorld:()=>JSON.parse(JSON.stringify({items,doors,serial,layer})),
    restoreWorld(world){cleanup();items.splice(0,items.length,...JSON.parse(JSON.stringify(world.items)));for(const key of Object.keys(panels))doors[key]=world.doors[key];serial=world.serial;layer=world.layer;selected=null;decorating=false;render();},
    showTray:openTray,closeTray,refreshDisplays:renderDisplays,
    chooseRecipe(name){if(!window.KitchenCatalog.some(r=>r.name===name))return;items.find(r=>r.kind==='meal').name=name;setCamera('counter');render();closeTray();window.dispatchEvent(new CustomEvent('mini-kitchen:recipe',{detail:{name}}));}
  });
})();
