/* Miniature scene; the journal adapter persists only its separate preview key. */
(() => {
  'use strict';
  const FRIDGE = './designs/miniature-kitchen/assets/refresh-20261109/closed-front-v1.png';
  const KITCHEN_SCENE = './designs/miniature-kitchen/assets/refresh-20261109/kitchen-open.png';
  const KITCHEN_REVEAL = './designs/miniature-kitchen/assets/refresh-20261109/kitchen-reveal.png';
  const ROOM_SCENE = './designs/miniature-kitchen/assets/refresh-20261109/kitchen-room.png';
  const FOOD_SCENE = './designs/miniature-kitchen/assets/refresh-20261109/food-atlas-v1.png';
  const DECOR = './designs/miniature-kitchen/assets/decor-atlas.png';
  const ROOM_PROPS = './designs/miniature-kitchen/assets/room-props-fullflow-v1.png';
  const A=window.UMFKitchenArt, $=s=>document.querySelector(s), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
  const mode=document.body.dataset.mode==='widget'?'widget':'app';
  const date=(offset=0)=>{const d=new Date();d.setDate(d.getDate()+offset);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');};
  // Geometry is measured from the approved empty artwork, never from saved data.
  const P=window.KitchenSceneProjection,STAGE_HEIGHT=P.stage[3];
  const panels=Object.fromEntries(Object.entries(P.panels).map(([key,photo])=>{
    const [bx,by,bw,bh]=P.stage,[x,y,w,h]=photo.body,[zx,zy,zw,zh]=photo.interior,[ox,oy,ow,oh]=photo.open;
    return [key,{name:(key.startsWith('fresh')?'냉장':'냉동')+' '+(key.endsWith('Left')?'왼쪽':'오른쪽'),kind:key.startsWith('fresh')?'냉장':'냉동',x:(x-bx)/bw,y:(y-by)/bh,w:w/bw,h:h/bh,zx:(zx-bx)/bw,zy:(zy-by)/bh,zw:zw/bw,zh:zh/bh,open:[ox-bx,oy-by,ow,oh]}];
  }));
  const props={utensils:{name:'도자기 도구통',crop:[48,15,550,648]},flowers:{name:'데이지 유리병',crop:[735,25,510,640]},cup:{name:'우드 트레이와 찻잔',crop:[24,685,694,495]},cookies:{name:'쿠키 유리병',crop:[773,675,445,504]},frame:{name:'우드 액자',crop:[48,15,550,648]},basket:{name:'바구니',crop:[773,675,445,504]}};
  let serial=20, layer=20, cropSerial=0, decorating=false, selected=null, active=null, previousFocus=null, decorEdit=null, announcementTimer=0, highlightedItem=null, highlightUntil=0;
  const closing=new Set(),closingTimers=new Map();
  const movingDisplays=new Map();
  let movingDisplayCSS;
  let lastSceneGeometry;
  const sideCounters=document.createElement('div');sideCounters.className='fitted-side-counters';sideCounters.setAttribute('aria-hidden','true');sideCounters.innerHTML='<i></i><i></i>';$('.shell').appendChild(sideCounters);
  const doors={freshLeft:true,freshRight:true,frozenLeft:true,frozenRight:true};
  const doorForZone=z=>z.startsWith('door')?z.slice(4,5).toLowerCase()+z.slice(5):z;
  const isAvailable=z=>!panels[doorForZone(z)]||doors[doorForZone(z)];
  const items=[
    {id:'egg',kind:'food',name:'계란',quantity:'6개',expiry:date(),zone:'freshLeft',x:.75,y:.15,z:1},
    {id:'milk',kind:'food',name:'우유',quantity:'500ml',expiry:date(1),zone:'freshRight',x:.5,y:.6,z:2},
    {id:'tofu',kind:'food',name:'두부',quantity:'1모',expiry:date(3),zone:'freshLeft',x:.75,y:.6,z:3},
    {id:'broccoli',kind:'food',name:'브로콜리',quantity:'1개',expiry:date(2),zone:'freshRight',x:.5,y:.15,z:4},
    {id:'tomato',kind:'food',name:'토마토',quantity:'3개',expiry:date(1),zone:'freshLeft',x:.25,y:.15,z:5},
    {id:'fish',kind:'food',name:'생선',quantity:'2조각',expiry:date(14),zone:'frozenLeft',x:.5,y:.907,z:6},
    ...['간장','고추장','된장','소금'].map((name,index)=>({id:'spice'+index,kind:'seasoning',name,quantity:index===0?'150ml':'',expiry:date(30+index*10),zone:index===0||index===3?'doorFreshLeft':'doorFreshRight',x:index%2?.3:.7,y:index<2?.45:.86,z:7+index})),
    {id:'scallion',kind:'food',name:'대파',quantity:'1개',expiry:date(5),zone:'freshRight',x:.5,y:.95,z:11},
    {id:'mushroom',kind:'food',name:'양송이버섯',quantity:'100g',expiry:date(5),zone:'freshLeft',x:.5,y:.95,z:12},
    {id:'kimchi',kind:'food',name:'김치',quantity:'200g',expiry:date(12),zone:'freshLeft',x:.25,y:.6,z:13},
    {id:'beef',kind:'food',name:'소고기',quantity:'300g',expiry:date(12),zone:'frozenLeft',x:.5,y:.472,z:14},
    {id:'shrimp',kind:'food',name:'새우',quantity:'200g',expiry:date(30),zone:'frozenRight',x:.5,y:.297,z:15},
    {id:'dumplings',kind:'food',name:'만두',quantity:'1팩',expiry:date(18),zone:'frozenRight',x:.25,y:1,z:16},
    {id:'mixveg',kind:'food',name:'냉동 채소',quantity:'200g',expiry:date(25),zone:'frozenRight',x:.75,y:1,z:17},
    {id:'meal',kind:'meal',name:'계란 볶음밥',zone:'counter',x:.46,y:.96,z:18},
    {id:'cup',kind:'decor',art:'cup',name:props.cup.name,zone:'counter',x:.075,y:.98,z:20}
  ];
  const clone=value=>JSON.parse(JSON.stringify(value));
  const sceneItems=()=>{if(!decorEdit)return items;const pending=new Map(decorEdit.items.map(i=>[i.id,i])),visible=[];for(const item of items){if(item.kind!=='decor')visible.push(item);else if(pending.has(item.id)){visible.push(pending.get(item.id));pending.delete(item.id);}}return [...visible,...pending.values()];};
  const differs=(a,b)=>JSON.stringify(a)!==JSON.stringify(b);
  const decorDirty=()=>Boolean(decorEdit&&(differs(decorEdit.items,decorEdit.base)||differs(decorEdit.theme,decorEdit.baseTheme)||differs(decorEdit.equipped,decorEdit.baseEquipped)||pendingDecorRewards(decorEdit).length));
  function notifyChange(preview=false){window.dispatchEvent(new CustomEvent('mini-kitchen:change',{detail:{preview}}));}
  function beginDecorEdit(options={}){
    if(!decorEdit){const base=clone(items.filter(i=>i.kind==='decor')),theme=window.KitchenJournal?.getWorkflow().theme||null,equipped=window.KitchenJournal?.getSnapshot().equipped||null;decorEdit={base,items:clone(base),baseTheme:clone(theme),theme:clone(theme),baseEquipped:clone(equipped),equipped:clone(equipped),serial,layer,selectedBefore:selected,pendingRewards:[],returnTo:options.returnTo||'growth'};}
    if(options.returnTo)decorEdit.returnTo=options.returnTo;
    decorating=true;return getDecorDraftState();
  }
  function pendingDecorRewards(edit=decorEdit){return edit?[...new Set(edit.pendingRewards||[])].filter(id=>{const r=window.KitchenPlayModel?.REWARDS[id];return r?.kind==='room'?edit.items.some(i=>i.art===r.art):Object.values(edit.equipped||{}).includes(id);}):[];}
  function decorRewardCost(edit=decorEdit){const M=window.KitchenPlayModel,s=window.KitchenJournal?.getSnapshot();if(!edit||!M||!s)return 0;return pendingDecorRewards(edit).reduce((cost,id)=>{const r=M.REWARDS[id],owned=r.kind==='room'?M.ownsRoomReward(s,{items:edit.base},id):s.owned.includes(id);return cost+(owned?0:r.cost);},0);}
  function getDecorDraftState(){return {active:Boolean(decorEdit),dirty:decorDirty(),pendingRewards:pendingDecorRewards(),cost:decorRewardCost(),returnTo:decorEdit?.returnTo||'growth'};}
  function queueDecorReward(id){
    const M=window.KitchenPlayModel,J=window.KitchenJournal,r=M?.REWARDS[id];if(!r||!J)throw new Error('소품 기록을 불러온 뒤 다시 골라 주세요.');
    const s=J.getSnapshot(),owned=r.kind==='room'?M.ownsRoomReward(s,{items:decorEdit?.base||items},id):s.owned.includes(id),already=pendingDecorRewards().includes(id),cost=decorRewardCost()+(owned||already?0:r.cost);
    if(J.summary().tickets<cost)throw new Error('꾸밈권이 더 필요해요. 적용 전에 다른 소품을 골라 주세요.');
    beginDecorEdit({returnTo:'rewards'});if(!owned&&!decorEdit.pendingRewards.includes(id))decorEdit.pendingRewards.push(id);return r;
  }
  function previewDecorReward(id,options={}){
    const r=queueDecorReward(id);
    if(r.kind!=='room'){setDecorEquippedDraft(options.slot||'frozenLeft',id);setCamera('counter');render(true);closeTray();return;}
    const existing=decorEdit.items.find(i=>i.art===r.art);if(existing)selected=existing.id;
    else{if(items.filter(i=>i.kind!=='decor').length+decorEdit.items.length>=2000)throw new Error('소품을 더 놓기 전에 기존 소품을 정리해 주세요.');let itemId;do{itemId='decor'+(++decorEdit.serial);}while(items.some(i=>i.id===itemId)||decorEdit.items.some(i=>i.id===itemId));const item={id:itemId,kind:'decor',art:r.art,name:r.name,zone:'counter',x:r.art==='cup'?.12:.87,y:.98,z:nextItemLayer({kind:'decor'})};decorEdit.items.push(item);selected=item.id;}
    setCamera('counter');render(true);closeTray();announce('배치 미리보기예요. 적용하면 저장해요.',false);
  }
  function setDecorThemeDraft(theme){
    if(!theme||!['linen','stone'].includes(theme.background)||!['standard','minimal'].includes(theme.labels)||typeof theme.organizer!=='boolean')throw new Error('부엌 분위기 설정을 확인해 주세요.');
    beginDecorEdit();decorEdit.theme={...decorEdit.theme,background:theme.background,labels:theme.labels,organizer:theme.organizer};notifyChange(true);
  }
  function setDecorEquippedDraft(slot,id){
    if(!['frozenLeft','frozenRight'].includes(slot)||id!==null&&(!window.KitchenPlayModel?.REWARDS[id]||window.KitchenPlayModel.REWARDS[id].kind==='room'))throw new Error('문에 붙일 소품을 골라 주세요.');
    if(id)queueDecorReward(id);
    beginDecorEdit();if(!decorEdit.equipped)throw new Error('소품 기록을 불러온 뒤 다시 골라 주세요.');
    if(id)for(const key of Object.keys(decorEdit.equipped))if(decorEdit.equipped[key]===id)decorEdit.equipped[key]=null;
    decorEdit.equipped[slot]=id;notifyChange(true);
  }
  function nextItemLayer(item){if(item.kind==='decor'&&decorEdit)return decorEdit.layer=Math.max(layer,decorEdit.layer)+1;return ++layer;}
  function cancelDecorEdit(){
    if(!decorEdit)return false;
    const prior=decorEdit.selectedBefore;decorEdit=null;decorating=false;selected=items.some(i=>i.id===prior&&i.kind!=='decor')?prior:null;
    render(true);return true;
  }
  // Navigation can discard a preview without selecting a different page or
  // camera. The caller owns its destination; nothing is applied implicitly.
  function leaveDecor(){return cancelDecorEdit();}
  function applyDecorEdit(){
    if(!decorEdit)return false;
    const edit=decorEdit,changed=decorDirty()||Object.values(doors).some(Boolean);
    if(changed){
      const merge=({world,flow,play})=>{
        if(differs(world.items.filter(i=>i.kind==='decor'),edit.base))throw new Error('소품 기록이 바뀌었어요. 취소한 뒤 현재 배치에서 다시 꾸며 주세요.');
        if(play)for(const id of pendingDecorRewards(edit)){const M=window.KitchenPlayModel,r=M.REWARDS[id],s=play.state(),owned=r.kind==='room'?M.ownsRoomReward(s,{items:edit.base},id):s.owned.includes(id);if(!owned)play.buy(id);}
        if(differs(edit.items,edit.base)){
          if(differs(world.items.filter(i=>i.kind==='decor'),edit.base))throw new Error('소품 기록이 바뀌었어요. 취소한 뒤 현재 배치에서 다시 꾸며 주세요.');
          const pending=new Map(edit.items.map(i=>[i.id,clone(i)])),next=[];
          for(const item of world.items){if(item.kind!=='decor')next.push(item);else if(pending.has(item.id)){next.push(pending.get(item.id));pending.delete(item.id);}}
          world.items=[...next,...pending.values()];world.serial=Math.max(world.serial,edit.serial);world.layer=Math.max(world.layer,edit.layer);
        }
        if(flow&&differs(edit.theme,edit.baseTheme)){if(differs(flow.theme,edit.baseTheme))throw new Error('부엌 설정이 바뀌었어요. 현재 설정에서 다시 꾸며 주세요.');flow.theme=clone(edit.theme);}
        if(play&&differs(edit.equipped,edit.baseEquipped)){
          if(differs(play.state().equipped,edit.baseEquipped))throw new Error('문의 소품 배치가 바뀌었어요. 현재 배치에서 다시 골라 주세요.');
          for(const key of Object.keys(edit.equipped))play.equip(key,null);
          for(const [key,id] of Object.entries(edit.equipped))if(id)play.equip(key,id);
        }
        for(const key of Object.keys(world.doors))world.doors[key]=false;
      };
      if(window.KitchenJournal)window.KitchenJournal.transact(merge);
      else{const world={items:clone(items),doors:clone(doors),serial,layer};merge({world});items.splice(0,items.length,...world.items);serial=world.serial;layer=world.layer;}
    }
    const prior=edit.selectedBefore;decorEdit=null;decorating=false;selected=items.some(i=>i.id===prior&&i.kind!=='decor')?prior:null;
    render(Boolean(window.KitchenJournal)||!changed);return changed;
  }
  function crop(asset,box,total,cls='',fit='none') {
    const id='mini-crop-'+(++cropSerial),[x,y,w,h]=box;
    return `<svg class="${cls}" viewBox="${box.join(' ')}" preserveAspectRatio="${fit}" aria-hidden="true" focusable="false"><defs><clipPath id="${id}"><rect x="${x}" y="${y}" width="${w}" height="${h}"/></clipPath></defs><image href="${asset}" x="0" y="0" width="${total[0]}" height="${total[1]}" clip-path="url(#${id})"/></svg>`;
  }
  const frontBoxes=P.closed.faces;
  const closedBox=key=>{const [x,y,w,h]=frontBoxes[key],c=P.closed;return [P.stage[2]/2+(x-c.center)*c.scale,c.top+(y-c.sourceTop)*c.scale,w*c.scale,h*c.scale];};
  const frontArt=key=>crop(FRIDGE,frontBoxes[key],P.closed.size,'closed-door-face','xMidYMid meet');
  const openPhotos=Object.fromEntries(Object.entries(P.panels).map(([key,p])=>[key,{box:p.open,points:p.polygon.map(v=>v.join(',')).join(' ')}]));
  function openDoorArt(key){const {box,points}=openPhotos[key],id='native-door-'+(++cropSerial);return `<svg class="original-open-door" viewBox="${box.join(' ')}" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false" style="--door-paint-width:${box[2]}px;--door-paint-height:${box[3]}px"><defs><clipPath id="${id}"><polygon points="${points}"/></clipPath></defs><image href="${KITCHEN_SCENE}" width="${P.world[0]}" height="${P.world[1]}" clip-path="url(#${id})"/></svg>`;}
  function photoSample(box,cls='',attributes=''){
    const id='scene-sample-'+(++cropSerial),[x,y,w,h]=box;
    return `<defs><clipPath id="${id}"><rect x="${x}" y="${y}" width="${w}" height="${h}"/></clipPath></defs><image class="${cls}" ${attributes} href="${KITCHEN_SCENE}" width="${P.world[0]}" height="${P.world[1]}" clip-path="url(#${id})"/>`;
  }
  function roomFridgeArt(cls=''){
    const faces=Object.keys(frontBoxes).map(key=>{const [x,y,w,h]=closedBox(key);return crop(FRIDGE,frontBoxes[key],P.closed.size,'shared-front-face','xMidYMid meet').replace('<svg ',`<svg x="${P.stage[0]+x}" y="${P.stage[1]+y}" width="${w}" height="${h}" `);}).join('');
    return `<svg class="${cls}" viewBox="${P.stage.join(' ')}" preserveAspectRatio="xMidYMax meet" aria-hidden="true">${photoSample(P.base)}${faces}</svg>`;
  }
  function scenePhoto(){
    const photo=document.createElement('img');photo.className='original-kitchen-photo';photo.src=KITCHEN_REVEAL;photo.alt='';photo.draggable=false;$('.scene-world').prepend(photo);
    const body=document.createElement('div');body.className='original-fridge-body';body.setAttribute('aria-hidden','true');
    const quarters=Object.entries(P.panels).map(([key,p])=>photoSample(p.body,'native-quarter',`data-native-quarter="${key}"`)).join('');
    const hinges=Object.entries(P.hinges).map(([key,h])=>photoSample(h.box,'native-hinge',`data-native-hinge="${key}"`)).join('');
    body.innerHTML=`<svg viewBox="0 0 ${P.world.join(' ')}" preserveAspectRatio="xMidYMid meet">${photoSample(P.base)}${quarters}${hinges}</svg>`;$('.scene-world').appendChild(body);
  }
  const roomCamera=()=>document.body.dataset.camera==='counter'||$('#panel-fridge').dataset.screenId==='D6';
  const roomPropBoxes={"flowers":[78,44,492,567],"cup":[656,159,514,439],"frame":[96,701,412,464],"basket":[647,699,540,469]};
  const decorArt=key=>roomPropBoxes[key]?crop(ROOM_PROPS,roomPropBoxes[key],[1254,1254],'decor-art','xMidYMax meet'):crop(DECOR,props[key].crop,[1286,1223],'decor-art','xMidYMax meet');
  const stockNameById={egg:'계란',milk:'우유',tofu:'두부',broccoli:'브로콜리',tomato:'토마토',fish:'생선',scallion:'대파',kimchi:'김치',mushroom:'양송이버섯'};
  const retainedFoodIds=new Set(['chicken','onion','carrot','rice','potato','zucchini','oil','cheese','yogurt','lettuce','garlic','pepper','ingredient']);
  function art(item) {
    if(item.photo&&item.photoAsIcon!==false)return `<img class="food-art product-photo" alt="" src="${esc(item.photo)}">`;
    const foodBoxes=P.foodBoxes;
    const spice=item.kind==='seasoning'?(/고추장|쌈장/.test(item.name)?'고추장':/된장/.test(item.name)?'된장':/소금/.test(item.name)?'소금':/간장|액젓|참치액/.test(item.name)?'간장':null):null;
    const pictured=foodBoxes[item.name]?item.name:spice||stockNameById[A.foodIdForName(item.name)];
    if(['food','seasoning'].includes(item.kind)&&pictured&&foodBoxes[pictured])return crop(FOOD_SCENE,foodBoxes[pictured],P.foodSize,'food-art','xMidYMax meet');
    if(item.kind==='decor')return decorArt(item.art);
    if(item.kind==='meal')return window.KitchenStoryboardArt.dish({id:item.name});
    if(item.kind==='seasoning')return A.seasoningArt('기타 양념','food-art');
    const id=A.foodIdForName(item.name);return A.foodArt(retainedFoodIds.has(id)?id:'ingredient');
  }
  function announce(message,visual=true){
    clearTimeout(announcementTimer);const output=$('#liveMessage'),text=String(message??'');output.textContent=text;
    output.dataset.visual=String(visual);
    if(text)announcementTimer=setTimeout(()=>{if(output.textContent===text)output.textContent='';},3500);
  }
  function compact(){return mode==='widget'||$('.shell').clientWidth<960;}
  function positionBackground(){
    if(!roomCamera())return;
    const room=$('.room'),shell=$('.shell'),scale=room.clientWidth/P.room.size[0],host=$(document.body.dataset.camera==='counter'?'#decorStage':'#fridgeSceneHost');
    const visible=host.getBoundingClientRect(),box=room.getBoundingClientRect(),left=Math.max(P.room.counter[0],(visible.left-box.left)/scale),right=Math.min(P.room.counter[0]+P.room.counter[2],(visible.right-box.left)/scale);
    const zone=$('.counter-zone');Object.assign(zone.style,{left:left+'px',top:P.room.counter[1]+'px',width:Math.max(1,right-left)+'px',height:P.room.counter[3]+'px'});
    shell.style.setProperty('--counter-surface-y-room',(P.room.counter[1]+P.room.counter[3])*scale+'px');shell.style.setProperty('--counter-world-y',(P.room.counter[1]+P.room.counter[3])+'px');
    shell.style.setProperty('--kitchen-floor-y',P.room.floor*scale+'px');
  }
  function syncLayout(){
    window.KitchenRefreshLayout.fit();
    const room=$('.room'),shell=$('.shell');if(!room.getClientRects().length)return;
    const inRoom=roomCamera(),native=inRoom?P.room.size:P.world,host=$(document.body.dataset.camera==='counter'?'#decorStage':'#fridgeSceneHost');
    let width=host?.clientWidth||shell.clientWidth;
    if(inRoom){const height=Math.max(1,host?.clientHeight||innerHeight);width=document.body.dataset.camera==='counter'?Math.min(width,height*native[0]/native[1]):Math.max(width,height*native[0]/native[1]);}
    const scale=width/native[0];room.style.setProperty('--room-fit-width',width+'px');
    for(const [name,value]of Object.entries({'--scene-scale':String(scale),'--scene-height':scale*native[1]+'px','--scene-world-width':native[0]+'px','--scene-world-height':native[1]+'px','--scene-logical-height':native[1]+'px','--scene-x':'0px','--scene-y':'0px','--object':Math.max(118,42/scale)+'px','--seasoning':Math.max(110,40/scale)+'px'}))shell.style.setProperty(name,value);
    const photo=$('.original-kitchen-photo'),asset=inRoom?ROOM_SCENE:KITCHEN_REVEAL;if(photo.getAttribute('src')!==asset)photo.src=asset;
    const backdrop=$('.decor-fridge-backdrop');Object.assign(backdrop.style,{left:P.room.fridge[0]+'px',top:P.room.fridge[1]+'px',bottom:'auto',width:P.room.fridge[2]+'px',height:P.room.fridge[3]+'px'});
    $('.kitchen-view').classList.toggle('is-compact',compact());positionBackground();renderDisplays();
  }
  function setCamera(camera) {
    cleanup();camera=camera==='counter'?'counter':'fridge';document.body.dataset.camera=camera;
    decorating=camera==='counter';if(decorating)beginDecorEdit();document.body.classList.toggle('is-decorating',decorating);if($('#decorationTools'))$('#decorationTools').hidden=!decorating;
    window.KitchenHome?.showScene(camera);
    for(const b of document.querySelectorAll('.camera-tabs button'))b.setAttribute('aria-pressed',String(b.dataset.camera===camera));
    const message=$('#roomMessage'),note=$('#sceneNote');
    if(message)message.textContent=camera==='counter'?'소품을 옮겨 나만의 부엌을 꾸며요.':'냉장고 문을 열어, 우리 집 재료를 살펴봐요.';
    if(note){note.textContent=decorating?'소품을 끌어 놓고, 누르면 앞뒤 순서도 바꿀 수 있어요.':'음식과 소품을 눌러 살펴봐요.';note.hidden=true;}
    syncLayout();constrainItems();
  }
  function renderDisplays(expanded=false) {
    const root=$('#fridgeDisplays');if(!root)return;
    const liveStage=$('.fridge-stage').getBoundingClientRect(),liveRoom=$('.room').getBoundingClientRect(),hasGeometry=liveStage.width>0&&liveRoom.width>0;
    if(hasGeometry)lastSceneGeometry={stage:liveStage,room:liveRoom};
    if(!lastSceneGeometry)return '';
    const {stage,room}=lastSceneGeometry;
    root.hidden=document.body.dataset.camera!=='fridge';
    // Calendar-day comparison avoids DST and midnight timezone rounding.
    const dayNumber=value=>{const [y,m,d]=value.split('-').map(Number);return Date.UTC(y,m-1,d)/86400000;};
    const today=dayNumber(date());
    const near=items.filter(r=>(r.kind==='food'||r.kind==='seasoning')&&!r.depleted&&window.KitchenWorkflowModel?.parseQuantity(r.quantity)?.baseAmount!==0&&r.expiry&&dayNumber(r.expiry)-today<=3).sort((a,b)=>a.expiry.localeCompare(b.expiry));
    const counts={overdue:0,today:0,tomorrow:0,soon:0};
    for(const item of near){const days=dayNumber(item.expiry)-today;counts[days<0?'overdue':days===0?'today':days===1?'tomorrow':'soon']++;}
    const distribution=Object.entries(counts).filter(([,count])=>count).map(([tone,count])=>`<i data-expiry-tone="${tone}" style="flex:${count}"></i>`).join('');
    const distributionLabel=`기한 경과 ${counts.overdue}건, 오늘 ${counts.today}건, 내일 ${counts.tomorrow}건, 2~3일 이내 ${counts.soon}건`;
    const cleanName=name=>String(name).normalize('NFKC').replace(/\s+/g,'').toLowerCase();
    const names=new Set(items.filter(r=>(r.kind==='food'||r.kind==='seasoning')&&!r.depleted&&window.KitchenWorkflowModel?.parseQuantity(r.quantity)?.baseAmount!==0&&(!r.expiry||dayNumber(r.expiry)>=today)).map(r=>cleanName(r.name)));
    const markup=['freshLeft','freshRight'].map(key=>{
      const candidate=window.KitchenHome?.recommendation(),p=panels[key],left=key==='freshLeft',meal=items.find(r=>r.kind==='meal'),hidden=!expanded&&(doors[key]||closing.has(key));
      // Fit inside the door's flat surface, leaving the curved edge and handle
      // clear. Keep text at native size rather than scaling a tall dashboard.
      const width=panels.freshRight.w*.70*stage.width,doorHeight=p.h*stage.height;
      // Match the approved tall-glass concept. The room, appliance, handles and
      // hit targets keep their existing coordinates; only the live inset grows.
      const height=doorHeight*.72;
      const layout=expanded?'standard':height<128||width<62?'summary':width<96||height<195?'compact':'standard';
      const x=stage.x-room.x+(p.x+p.w*(left?.10:.20))*stage.width;
      // The original atlas already has recessed screens at y188..394. Center
      // the live screen over that recess so it never peeks out below the UI.
      const center=.48;
      const y=stage.y-room.y+p.y*stage.height+doorHeight*center-height/2;
      const visible=near.slice(0,layout==='standard'?3:layout==='compact'&&height>=150?2:1),overdue=counts.overdue>0;
      const recipe=window.KitchenHome?candidate?.recipe:window.KitchenCatalog.find(r=>r.name===meal.name),menuName=recipe?.name||'조건 확인',facts=candidate?.nutrients||{},cost=candidate?.cost??null;
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
      const stock=candidate?`<div class="lcd-stock lcd-availability" data-lcd-stock-status="${candidate.availability.status}"><span>재료 상태</span><b>${candidate.availability.ready?'수량 충족':candidate.availability.status==='shortage'?'부족 '+candidate.availability.missing.length+'종':'수량 확인'}</b></div>`:recipe?`<div class="lcd-stock" style="--lcd-coverage:${ratio}%" title="기록된 재료 이름 중 일치하는 종류 수 · 기한 경과 항목 제외 · 수량 미검증"><div class="lcd-stock-label"><span>재료<span class="lcd-stock-word"> 기록</span></span><b>${registered}/${required.length}</b></div><div class="lcd-stock-track" role="meter" aria-label="기록된 재료 종류 · 이름 기준, 수량 미검증" aria-valuemin="0" aria-valuemax="${required.length||1}" aria-valuenow="${registered}"><i style="width:${ratio}%"></i></div></div>`:'<div class="lcd-stock"><span>재료 미입력</span></div>';
      const missingNote=candidate?'':recipe?`<p class="lcd-missing" title="${esc(missing.join(' · '))}"><span>${missing.length?'미등록 재료':'이름 기록됨'}</span>${missing.length?`<b>${esc(missing.slice(0,2).join(' · '))}${missing.length>2?' 외 '+(missing.length-2):''}</b>`:'<b>수량 확인 필요</b>'}</p>`:'';
      const lcdFacts=`<div class="lcd-nutrition-cost" aria-label="입력한 1회분 영양과 원가"><span>${typeof facts.kcal==='number'?Math.round(facts.kcal)+' kcal':'열량 미입력'}</span><span>${cost===null?'원가 미입력':Math.round(cost).toLocaleString('ko-KR')+'원'}</span></div>`;
      const content=left?`${counters}<div class="lcd-list" style="--lcd-rows:${visible.length||1}">${rows||'<p class="lcd-empty">'+empty+'</p>'}</div><div class="lcd-footer lcd-expiry-footer"><span>${overdue?'경과 '+counts.overdue+'건':near.length?'임박 '+near.length+'건':'보관 '+items.filter(r=>r.kind==='food'||r.kind==='seasoning').length+'건'}</span><div class="lcd-expiry-track" role="img" aria-label="${distributionLabel}">${distribution}</div></div>`:`<div class="lcd-menu"><div class="lcd-dish">${recipe?window.KitchenStoryboardArt.dish({id:menuName}):'<span>추천 조건을<br>확인해 주세요</span>'}</div><b class="lcd-recipe">${esc(menuName)}</b></div>${lcdFacts}<div class="lcd-footer lcd-recipe-facts"><span>${esc(recipe?.time||'시간 미입력')}</span><span class="lcd-level">${esc(recipe?.level||'')}</span></div><div class="lcd-recipe-detail">${stock}${missingNote}</div>`;
      return `<section class="fridge-lcd ${hidden?'':'is-on'}" data-lcd="${key}" ${!left?`data-recommended-recipe="${esc(recipe?.id||'')}"`:''} data-lcd-layout="${layout}" data-lcd-height="${expanded?'tall':height<150?'short':height<220?'medium':'tall'}" aria-label="${title} 디스플레이" style="left:${Math.round(x)}px;top:${Math.round(y)}px;width:${Math.round(width)}px;height:${Math.round(height)}px" ${hidden?'hidden':''}><div class="lcd-screen"><div class="lcd-header"><strong class="lcd-title">${title}</strong>${totalBadge}</div>${content}</div></section>`;
    }).join('');
    if(expanded)return markup;
    root.innerHTML=markup;if(hasGeometry)syncMovingDisplays(stage,room);window.dispatchEvent(new Event('mini-kitchen:layout'));
  }
  function syncMovingDisplays(stage,room) {
    // Keep a front-face copy on a moving door. The stationary, native-pixel LCD
    // returns after closing; an unfinished transition must never expose the
    // old blank recess. A closed shadow tree scopes SVG clip IDs and keeps the
    // decorative copy out of the UI's selectors and accessibility tree.
    const inverse=$('.fridge-stage').offsetWidth/stage.width;
    for(const key of ['freshLeft','freshRight']) {
      const door=$('[data-door="'+key+'"]'),active=doors[key]||closing.has(key);
      if(!door)continue;
      if(!active){movingDisplays.get(key)?.host.remove();movingDisplays.delete(key);continue;}
      if(movingDisplayCSS===undefined){
        const relevant=/\.(?:fridge-lcd|lcd-[\w-]+|food-art|dish-art)\b|^\*$/;
        const select=rule=>{
          if(rule.selectorText)return relevant.test(rule.selectorText)?rule.cssText:'';
          if(!rule.cssRules)return '';
          const children=[...rule.cssRules].map(select).join('\n');
          return children?rule.cssText.slice(0,rule.cssText.indexOf('{')+1)+children+'}':'';
        };
        movingDisplayCSS=[...document.styleSheets].map(sheet=>{try{return [...sheet.cssRules].map(select).join('\n');}catch(_){return '';}}).join('\n');
      }
      let copy=movingDisplays.get(key);
      if(!copy?.host.isConnected){
        const host=document.createElement('span');host.className='door-live-display';host.setAttribute('aria-hidden','true');host.inert=true;
        copy={host,root:host.attachShadow({mode:'closed'})};movingDisplays.set(key,copy);door.appendChild(host);
      }
      const panel=$('#fridgeDisplays [data-lcd="'+key+'"]'),p=panels[key];
      const clone=panel.cloneNode(true),style=document.createElement('style');
      clone.hidden=false;clone.classList.add('is-on');
      Object.assign(clone.style,{position:'relative',left:'0px',top:'0px'});
      // A moving face uses an opaque backing; it does not need to sample the
      // animated 3D scene with backdrop-filter. The normal LCD is unchanged.
      style.textContent=movingDisplayCSS+'\n.fridge-lcd{background-color:#faf8f2;-webkit-backdrop-filter:none;backdrop-filter:none}';
      copy.root.replaceChildren(style,clone);
      Object.assign(copy.host.style,{
        left:(room.x+$('.room').clientLeft+parseFloat(panel.style.left)-stage.x-p.x*stage.width)*inverse+'px',
        top:(room.y+$('.room').clientTop+parseFloat(panel.style.top)-stage.y-p.y*stage.height)*inverse+'px',
        width:panel.style.width,height:panel.style.height,transform:'scale('+inverse+')'
      });
    }
  }
  $('#cabinet').replaceChildren();scenePhoto();
  const decorFridge=document.createElement('div');decorFridge.className='decor-fridge-backdrop';decorFridge.setAttribute('aria-hidden','true');decorFridge.inert=true;decorFridge.style.pointerEvents='none';decorFridge.innerHTML=roomFridgeArt('decor-fridge-art');$('.scene-world').appendChild(decorFridge);
  for(const [key,p] of Object.entries(panels)) {
    const zone=document.createElement('div');zone.className='drop-zone';zone.dataset.zone=key;zone.setAttribute('aria-label',p.name+' 재료');Object.assign(zone.style,{left:p.zx*100+'%',top:p.zy*100+'%',width:p.zw*100+'%',height:p.zh*100+'%'});$('#fridgeInteriors').appendChild(zone);
    const door=document.createElement('button');door.type='button';door.className='door'+(key.endsWith('Right')?' right':'')+(key.startsWith('frozen')?' frozen':'');door.dataset.door=key;Object.assign(door.style,{left:p.x*100+'%',top:p.y*100+'%',width:p.w*100+'%',height:p.h*100+'%'});$('#fridgeDoors').appendChild(door);door.addEventListener('transitionend',event=>{if(event.target===door&&event.propertyName==='transform')finishClosing(key);});
    const cargo=document.createElement('div');cargo.className='door-cargo'+(key.endsWith('Right')?' right':'');cargo.dataset.cargo=key;Object.assign(cargo.style,{left:p.x*100+'%',top:p.y*100+'%',width:p.w*100+'%',height:p.h*100+'%'});const inner=document.createElement('div');inner.className='door-storage drop-zone';inner.dataset.zone='door'+key[0].toUpperCase()+key.slice(1);inner.setAttribute('aria-label',p.name+' 문 선반');cargo.appendChild(inner);$('.fridge-stage').appendChild(cargo);
  }
  // Old v1 seasoning shelves now paint on the door racks. Their stored zone
  // and coordinates stay exact until the user deliberately moves the item.
  const displayZone=item=>item.zone==='seasoning'&&['food','seasoning'].includes(item.kind)?(item.x<.5?'doorFreshLeft':'doorFreshRight'):item.zone;
  function cargoFloors(key){
    const p=P.panels[key],scale=parseFloat(getComputedStyle($('.shell')).getPropertyValue('--scene-scale'))||1;
    // Keep a full finger target below the rack on a narrow opened door.
    return p.cargoFloors.map(y=>Math.min(y,p.open[1]+p.open[3]-46/scale));
  }
  function place(button,item){
    let {x,y}=item;
    if(displayZone(item)!==item.zone){const key=doorForZone(displayZone(item)),p=P.panels[key];x=.5;y=(cargoFloors(key)[item.x%.5<.25?0:1]-p.cargo[1])/p.cargo[3];}
    button.style.left=x*100+'%';button.style.top=y*100+'%';button.style.zIndex=String(item.z);
  }
  function syncShelfLabels(){
    // Keep annotations above neighboring food art without changing stored positions or food layers.
    for(const button of document.querySelectorAll('.fridge-interiors .drop-zone>.item')){
      const zone=button.parentElement,item=items.find(i=>i.id===button.dataset.item);if(!item)continue;
      let label=button.querySelector('.item-label')||zone.querySelector('[data-for-item="'+CSS.escape(item.id)+'"]');if(!label)continue;
      label.classList.add('shelf-label');label.classList.toggle('is-selected',selected===item.id);label.dataset.forItem=item.id;label.setAttribute('aria-hidden','true');
      label.dataset.foodName=item.name;
      const style=getComputedStyle(button),scale=parseFloat(getComputedStyle($('.shell')).getPropertyValue('--scene-scale'))||1,paintHeight=parseFloat(style.getPropertyValue('--profile-height'))*(parseFloat(style.getPropertyValue('--food-fit'))||1),anchor=parseFloat(button.style.top)/100*zone.clientHeight;label.style.left=button.style.left;label.style.top=Math.max(18/scale,anchor-(paintHeight||button.offsetHeight)-4/scale)+'px';
      label.style.zIndex=String(selected===item.id?20000002:20000001);zone.appendChild(label);
    }
  }
  function constrainItems(){
    const shelves=Object.fromEntries(Object.entries(P.panels).map(([key,p])=>[key,p.shelves.map(y=>y-P.stage[1])])),groups=new Map();
    for(const button of document.querySelectorAll('.drop-zone>.item')){
      const item=sceneItems().find(r=>r.id===button.dataset.item),zone=button.parentElement,width=zone.clientWidth,height=zone.clientHeight;
      if(!item||!width||getComputedStyle(button).visibility!=='visible')continue;
      place(button,item);
      if(button.dataset.foodProfile&&button.closest('.fridge-interiors')){
        const css=getComputedStyle(button),w=parseFloat(css.getPropertyValue('--profile-width')),h=parseFloat(css.getPropertyValue('--profile-height'));
        const capacity=P.panels[item.zone]?.capacity||height;
        const fit=Math.min(1,width/w,height/h,capacity/h),visualWidth=w*fit,visualHeight=h*fit;
        button.style.setProperty('--food-fit',String(fit));
        const panel=panels[item.zone],floors=shelves[item.zone]||[],ceiling=P.panels[item.zone].interior[1]-P.stage[1];
        const valid=floors.map((y,index)=>({index,anchor:(y/STAGE_HEIGHT-panel.zy)/panel.zh,clearance:y-(index?floors[index-1]:ceiling)})).filter(f=>f.clearance>=visualHeight-.5);
        const preferred=valid.reduce((best,f)=>!best||Math.abs(f.anchor-item.y)<Math.abs(best.anchor-item.y)?f:best,null)?.index||0;
        const group=zone,offset=0,packWidth=width,preferredX=item.x;
        if(!groups.has(group))groups.set(group,[]);
        groups.get(group).push({button,item,width:packWidth,zoneWidth:width,offset,preferredX,height,visualWidth,visualHeight,valid,preferred});
      }else{
        const half=Math.min(.5,button.offsetWidth/2/width);button.style.left=clamp(item.x,half,1-half)*100+'%';
        if(item.kind==='seasoning'&&item.zone.startsWith('door')){const key=doorForZone(item.zone),photo=P.panels[key];if(photo){const floors=cargoFloors(key).map(y=>(y-photo.cargo[1])/photo.cargo[3]);const nearest=floors.reduce((best,y)=>Math.abs(y-item.y)<Math.abs(best-item.y)?y:best,floors[0]);button.style.top=nearest*100+'%';}}
      }
    }
    // Project saved normalized coordinates onto the new shelves. Only DOM
    // positions change: existing v1 records and deliberate drag coordinates
    // remain intact, while two old rows can no longer obscure each other.
    for(const entries of groups.values()){
      const gap=2,width=entries[0].width,priority=entries.reduce((best,e)=>!best||e.item.z>best.item.z?e:best,null);
      const zoneRect=entries[0].button.parentElement.getBoundingClientRect(),action=$('#addFood').getBoundingClientRect(),scale=zoneRect.width/width;
      const actionX=(action.left-zoneRect.left)/scale,actionRight=(action.right-zoneRect.left)/scale,actionY=(action.top-zoneRect.top)/scale,actionBottom=(action.bottom-zoneRect.top)/scale;
      const rowEnd=row=>{
        const candidates=entries.filter(e=>e.valid.some(f=>f.index===row)),support=candidates[0]?.valid.find(f=>f.index===row);
        if(!support||!action.width||!action.height||actionX>=width||actionRight<=0)return width;
        const bottom=support.anchor*candidates[0].height,top=bottom-Math.max(...candidates.map(e=>e.visualHeight));
        return bottom>actionY&&top<actionBottom?clamp(actionX-gap,0,width):width;
      };
      const pack=pinned=>{
        const bins=[],floors=[...new Set(entries.flatMap(e=>e.valid.map(f=>f.index)))].sort((a,b)=>a-b);
        const priorityRow=priority.valid.filter(f=>rowEnd(f.index)>=priority.visualWidth).sort((a,b)=>Math.abs(a.index-priority.preferred)-Math.abs(b.index-priority.preferred))[0]?.index;
        if(pinned&&priorityRow===undefined)return null;
        const center=clamp(priority.preferredX*width,priority.visualWidth/2,rowEnd(priorityRow??priority.preferred)-priority.visualWidth/2);
        for(const row of floors){
          const end=rowEnd(row),ranges=pinned&&row===priorityRow?[[0,center-priority.visualWidth/2-gap],[center+priority.visualWidth/2+gap,end]]:[[0,end]];
          for(const [start,end] of ranges)if(end>start)bins.push({row,start,end,remaining:end-start+gap,items:[]});
        }
        const pending=entries.filter(e=>!pinned||e!==priority).sort((a,b)=>b.visualWidth-a.visualWidth||a.item.y-b.item.y||b.item.z-a.item.z||a.item.id.localeCompare(b.item.id)),failed=new Set();let visits=0;
        const search=index=>{
          if(index===pending.length)return true;
          if(++visits>50000)return false;
          const key=index+':'+bins.map(bin=>bin.remaining.toFixed(3)).join(',');if(failed.has(key))return false;
          const entry=pending[index],needed=entry.visualWidth+gap;
          const options=bins.filter(bin=>bin.remaining+.001>=needed&&entry.valid.some(f=>f.index===bin.row)).sort((a,b)=>{
            const score=bin=>Math.abs(bin.row-entry.preferred)*width+Math.abs(clamp(entry.preferredX*width,bin.start+entry.visualWidth/2,bin.end-entry.visualWidth/2)-entry.preferredX*width)+(bin.remaining-needed)*.001;
            return score(a)-score(b);
          });
          for(const bin of options){bin.items.push(entry);bin.remaining-=needed;if(search(index+1))return true;bin.remaining+=needed;bin.items.pop();}
          failed.add(key);return false;
        };
        if(!search(0))return null;
        return {bins,pinned,center,priorityRow};
      };
      const layout=pack(true)||pack(false);
      if(!layout){
        // An arbitrarily full compartment still keeps every record and its
        // inventory-list access; never erase data to make the picture fit.
        for(const entry of entries){const support=entry.valid.find(f=>f.index===entry.preferred)||entry.valid[0];if(!support)continue;entry.button.style.left=(clamp(entry.preferredX*width,entry.visualWidth/2,width-entry.visualWidth/2)-entry.offset)/entry.zoneWidth*100+'%';entry.button.style.top=support.anchor*100+'%';}
        continue;
      }
      const placeEntry=(entry,center,row)=>{entry.button.style.left=(center-entry.offset)/entry.zoneWidth*100+'%';entry.button.style.top=entry.valid.find(f=>f.index===row).anchor*100+'%';};
      if(layout.pinned)placeEntry(priority,layout.center,layout.priorityRow);
      for(const bin of layout.bins){
        bin.items.sort((a,b)=>a.preferredX-b.preferredX||b.item.z-a.item.z||a.item.id.localeCompare(b.item.id));
        let edge=bin.start;
        for(const entry of bin.items){const half=entry.visualWidth/2;entry.center=Math.max(clamp(entry.preferredX*width,bin.start+half,bin.end-half),edge+half);edge=entry.center+half+gap;}
        edge=bin.end;
        for(const entry of [...bin.items].reverse()){const half=entry.visualWidth/2;entry.center=Math.min(entry.center,edge-half);edge=entry.center-half-gap;}
        for(const entry of bin.items)placeEntry(entry,entry.center,bin.row);
      }
    }

    syncShelfLabels();
  }

  function itemButton(item) {
    const b=document.createElement('button');b.type='button';b.className='item '+item.kind;b.dataset.item=item.id;if(item.art)b.dataset.art=item.art;
    if(item.kind==='food')b.dataset.foodName=item.name;
    // A food's appearance is its type, never its mutable shelf coordinates.
    if(item.kind==='food')b.dataset.foodProfile=({'계란':'eggs','달걀':'eggs','토마토':'tomatoes','방울토마토':'tomatoes','김치':'kimchi','양송이버섯':'mushrooms','두부':'tofu','브로콜리':'broccoli','우유':'milk','대파':'scallion','생선':'tray','소고기':'tray','새우':'frozen-small','만두':'frozen-small','냉동 채소':'frozen-small','냉동채소':'frozen-small'})[item.name]||'generic';
    const spice=item.kind==='seasoning'?(/고추장|쌈장/.test(item.name)?'고추장':/된장/.test(item.name)?'된장':/소금/.test(item.name)?'소금':/간장|액젓|참치액/.test(item.name)?'간장':null):null;
    const food=P.foodBoxes[item.name]||P.foodBoxes[spice]||P.foodBoxes[stockNameById[A.foodIdForName(item.name)]]||(['food','seasoning'].includes(item.kind)?[0,0,100,100]:null);
    if(['food','seasoning'].includes(item.kind)&&food){
      const limits={'계란':[142,94],'토마토':[100,86],'두부':[150,78],'브로콜리':[125,96],'우유':[104,144],'대파':[178,78],'양송이버섯':[125,84],'김치':[105,98],'소고기':[240,92],'생선':[240,92],'새우':[230,92],'만두':[132,88],'냉동 채소':[132,88]},[mw,mh]=limits[item.name]||(item.kind==='seasoning'?[65,138]:[140,94]),fit=Math.min(mw/food[2],mh/food[3]);
      b.style.setProperty('--profile-width',food[2]*fit+'px');b.style.setProperty('--profile-height',food[3]*fit+'px');if(item.kind==='seasoning')b.dataset.foodProfile='seasoning';
    }
    if(item.kind==='decor'){const sizes={flowers:[120,160],cup:[105,95],frame:[110,135],basket:[145,105],utensils:[100,150],cookies:[100,130]},[w,h]=sizes[item.art]||[110,135];b.style.setProperty('--decor-width',w+'px');b.style.setProperty('--decor-height',h+'px');}
    if(item.id===highlightedItem&&Date.now()<highlightUntil)b.classList.add('is-new');
    // A sauce is one miniature with one annotation. The previous three
    // overlapping name/quantity badges made the small jars look like forms.
    b.innerHTML=art(item)+(item.kind==='seasoning'?'':(item.quantity?`<span class="quantity">${esc(item.quantity)}</span>`:'')+`<span class="item-name">${esc(item.name)}</span>`);
    if(['food','seasoning'].includes(item.kind)){
      const delta=item.expiry?Math.round((Date.parse(item.expiry+'T12:00:00')-Date.parse(date()+'T12:00:00'))/86400000):null;
      const tone=delta===null?'unknown':delta<0?'overdue':delta===0?'today':delta===1?'tomorrow':'later',label=delta===null?'기한 확인':delta<0?'기한 경과':delta===0?'오늘까지':delta===1?'내일':delta+'일';
      b.innerHTML+=`<span class="item-label${item.kind==='seasoning'?' sauce-label':''}" data-tone="${tone}"><b>${esc(item.name==='양송이버섯'?'양송이':item.name.replace('냉동 채소','냉동채소'))}</b><small><span class="label-qty">${esc(item.quantity||'수량 확인')}</span>${delta!==null&&delta<=1?`<span class="label-deadline"> · ${delta<0?'경과':delta===0?'오늘':'내일'}</span>`:''}</small></span>`;
    }
    b.setAttribute('aria-label',item.name+(item.quantity?' '+item.quantity:'')+(item.expiry?' · '+item.expiry:'')+(item.kind==='decor'?' · 소품 위치 바꾸기':' · 누르면 살펴보기, 끌어서 이동'));b.classList.toggle('is-selected',selected===item.id);place(b,item);return b;
  }
  function syncDecorShelf(){
    const shelf=$('#decorPropShelf');if(!shelf)return;
    const visible=sceneItems().filter(i=>i.kind==='decor'&&!i.depleted),M=window.KitchenPlayModel,J=window.KitchenJournal,play=J?.getSnapshot(),base={items:decorEdit?.base||items};
    const cards=visible.map(item=>({name:item.name,art:item.art,action:'data-decor-select="'+esc(item.id)+'"',selected:selected===item.id,note:'놓여 있는 소품'}));
    if(M&&play)for(const id of M.roomRewards){const reward=M.REWARDS[id];if(visible.some(i=>i.art===reward.art))continue;const owned=M.ownsRoomReward(play,base,id);cards.push({name:reward.name,art:reward.art,action:'data-decor-reward="'+esc(id)+'"',selected:false,note:owned?'보유 소품 · 무료 배치':'꾸밈권 '+reward.cost+' · 적용 시 사용'});}
    for(const [key,p]of Object.entries(props)){if(visible.some(i=>i.art===key)||Object.values(M?.REWARDS||{}).some(r=>r.kind==='room'&&r.art===key))continue;cards.push({name:p.name,art:key,action:'data-add-prop="'+esc(key)+'"',selected:false,note:'기본 소품 · 무료 배치'});}
    const preferred=['flowers','cup','frame','basket'];cards.sort((a,b)=>{const rank=x=>preferred.includes(x.art)?preferred.indexOf(x.art):preferred.length;return rank(a)-rank(b);});
    const left=shelf.scrollLeft,focused=shelf.contains(document.activeElement)?document.activeElement?.closest('button')?.getAttribute('data-decor-select')||null:null;
    shelf.innerHTML=cards.map(card=>'<button type="button" class="studio-prop-card" '+card.action+' aria-pressed="'+card.selected+'" aria-label="'+esc(card.name)+' · '+card.note+'" title="'+esc(card.name)+'"><span class="studio-prop-art" aria-hidden="true">'+decorArt(card.art)+'</span><span class="studio-prop-copy"><strong>'+esc(card.name)+'</strong><small>'+card.note+'</small></span></button>').join('');
    shelf.scrollLeft=left;
    if(focused)shelf.querySelector('[data-decor-select="'+CSS.escape(focused)+'"]')?.focus({preventScroll:true});
  }
  function syncDecorToolbar(){
    const item=sceneItems().find(i=>i.id===selected&&i.kind==='decor'),enabled=Boolean(decorating&&decorEdit&&item);
    for(const button of document.querySelectorAll('[data-decor-tool]')){button.disabled=!enabled;button.setAttribute('aria-label',(enabled?item.name:'선택한 소품')+' '+({back:'뒤로 보내기',front:'앞으로 가져오기',remove:'치우기'}[button.dataset.decorTool]||'편집'));}
    const label=$('#decorSelectionName');if(label){label.textContent=enabled?item.name:'소품을 골라 배치해 보세요';label.title=enabled?item.name:'';}
    for(const handles of document.querySelectorAll('.decor-selection-handles'))handles.remove();
    if(enabled)document.querySelector('.room [data-item="'+CSS.escape(item.id)+'"]')?.insertAdjacentHTML('beforeend','<span class="decor-selection-handles" aria-hidden="true"><i></i><i></i><i></i><i></i></span>');
    const editor=$('#homeDecor');if(editor)editor.dataset.screenId='D5';
    const title=$('#homeDecor .decor-heading h2');if(title)title.textContent='배치 미리보기';
    const note=$('#decorationTools');if(note){note.hidden=!(decorating&&decorEdit);const cost=decorRewardCost();note.textContent=cost?'꾸밈권 '+cost+' · 적용 시 사용':decorDirty()?'저장 전 미리보기':'아직 변경 없음';}
    syncDecorShelf();
  }
  function selectCanvasItem(item){
    if(item.kind==='decor'&&decorating&&document.body.dataset.homePage==='decor'){
      beginDecorEdit();selected=item.id;render(true);document.querySelector('.room [data-item="'+CSS.escape(item.id)+'"]')?.focus({preventScroll:true});return;
    }
    showItem(item);
  }
  function removeDecor(id,{close=true}={}){
    beginDecorEdit();const index=decorEdit.items.findIndex(i=>i.id===id&&i.kind==='decor');if(index<0)return;
    decorEdit.items.splice(index,1);selected=null;render(true);if(close&&$('#tray').open)closeTray();announce('미리보기에서 소품을 치웠어요.');
  }
  function render(preview=false) {
    document.body.classList.toggle('is-decorating',decorating);if($('#decorationTools'))$('#decorationTools').hidden=!decorating;$('#decorate')?.setAttribute('aria-pressed',String(decorating));const decorateLabel=$('#decorate>span:last-child');if(decorateLabel)decorateLabel.textContent=decorating?'꾸미기 완료':'꾸미기';
    for(const quarter of document.querySelectorAll('[data-native-quarter]'))quarter.style.display=doors[quarter.dataset.nativeQuarter]?'':'none';
    for(const hinge of document.querySelectorAll('[data-native-hinge]'))hinge.style.display=(hinge.dataset.nativeHinge==='center'?(doors.freshLeft||doors.freshRight):doors[hinge.dataset.nativeHinge])?'':'none';
    for(const [key,p] of Object.entries(panels)) {
      const door=$('[data-door="'+key+'"]'),open=doors[key];door.innerHTML=open?openDoorArt(key):frontArt(key);const [ox,oy,ow,oh]=p.open,[cx,cy,cw,ch]=closedBox(key);Object.assign(door.style,open?{left:ox+'px',top:oy+'px',width:ow+'px',height:oh+'px'}:{left:cx+'px',top:cy+'px',width:cw+'px',height:ch+'px'});door.classList.toggle('is-open',open);door.setAttribute('aria-expanded',String(open));door.setAttribute('aria-label',p.name+' 문 '+(open?'닫기':'열기'));door.tabIndex=0;
      const zone=$('[data-zone="'+key+'"]');zone.hidden=!open;zone.inert=!open;
      const cargo=$('[data-cargo="'+key+'"]'),[qx,qy,qw,qh]=P.panels[key].cargo;Object.assign(cargo.style,{left:(qx-P.stage[0])+'px',top:(qy-P.stage[1])+'px',width:qw+'px',height:qh+'px'});cargo.hidden=!open;cargo.classList.toggle('is-open',open);cargo.classList.toggle('is-closing',closing.has(key));cargo.inert=!open;
    }
    for(const zone of document.querySelectorAll('.drop-zone')){for(const child of zone.querySelectorAll('.item,.shelf-label'))child.remove();for(const item of sceneItems().filter(r=>displayZone(r)===zone.dataset.zone&&!r.depleted&&window.KitchenWorkflowModel?.parseQuantity(r.quantity)?.baseAmount!==0))zone.appendChild(itemButton(item));}constrainItems();renderDisplays();syncDecorToolbar();notifyChange(preview);
  }
  function finishClosing(key){clearTimeout(closingTimers.get(key));closingTimers.delete(key);if(closing.delete(key))renderDisplays();}
  function toggle(key){cleanup();finishClosing(key);const willClose=doors[key];if(willClose&&!matchMedia('(prefers-reduced-motion: reduce)').matches){closing.add(key);closingTimers.set(key,setTimeout(()=>finishClosing(key),650));}doors[key]=!doors[key];if(doors[key]){delete document.body.dataset.fridgeState;$('#panel-fridge').dataset.screenId='A1';}render();announce(panels[key].name+' 문을 '+(doors[key]?'열었어요.':'닫았어요.'),false);}
  function openTray(title,content,eyebrow='MY LITTLE KITCHEN') {
    delete $('#tray').dataset.workflowRoute;
    if(!$('#tray').open)previousFocus=document.activeElement===document.body?document.querySelector('.item.is-selected')||document.activeElement:document.activeElement;$('#trayTitle').textContent=title;$('#trayEyebrow').textContent=eyebrow;$('#trayContent').innerHTML=content;if(!$('#tray').open)$('#tray').showModal();$('#tray').scrollTop=0;$('#trayTitle').tabIndex=-1;$('#trayTitle').focus({preventScroll:true});
  }
  function restoreTrayFocus(){const target=previousFocus?.isConnected?previousFocus:previousFocus?.dataset.item?document.querySelector('[data-item="'+CSS.escape(previousFocus.dataset.item)+'"]'):previousFocus?.id?document.getElementById(previousFocus.id):null;(target!==document.body&&target?.getClientRects().length?target:document.querySelector('.home-shortcuts [aria-selected="true"]'))?.focus({preventScroll:true});}
  function closeTray(){$('#tray').close();restoreTrayFocus();}
  function showAdd(){if(window.KitchenWorkflows)return window.KitchenWorkflows.add();openTray('부엌에 재료를 담아봐요',`<p class="tray-note">시안용 재료예요. 고른 재료는 열린 냉장칸에 놓이고, 눌러서 수량과 기한을 바꿀 수 있어요.</p><div class="palette">${['계란','우유','두부','브로콜리','토마토','대파','당근','생선'].map(name=>`<button type="button" data-add-food="${esc(name)}">${art({kind:'food',name})}<strong>${esc(name)}</strong><small>부엌에 담기</small></button>`).join('')}</div>`);}
  function showDecor() {
    beginDecorEdit();setCamera('counter');render(true);openTray('마음에 드는 소품을 놓아봐요',`<p class="tray-note">소품을 골라 조리대에 놓고 자유롭게 옮겨요. 소품을 누르면 앞뒤 순서와 배치를 바꿀 수 있어요.</p><div class="palette">${Object.entries(props).map(([key,p])=>`<button type="button" data-add-prop="${key}">${decorArt(key)}<strong>${p.name}</strong><small>${sceneItems().some(r=>r.art===key)?'이미 놓았어요 · 하나 더 놓기':'조리대에 놓기'}</small></button>`).join('')}</div><h3 class="placed-title">놓아둔 소품</h3><p class="tray-note">뒤에 가려진 소품도 여기서 고를 수 있어요.</p><div class="placed-props">${sceneItems().filter(r=>r.kind==='decor').map(r=>`<button type="button" data-select-prop="${esc(r.id)}">${art(r)}<span>${esc(r.name)}<br>선택해서 배치 바꾸기</span></button>`).join('')}</div><div class="tray-actions"><button type="button" class="small-action primary" data-close>부엌에서 옮겨보기</button></div>`);
  }
  function showRecipes(){if(window.KitchenWorkflows)return window.KitchenWorkflows.recipes();openTray('오늘은 어떤 한 끼가 좋을까요?',`<p class="tray-note">조리대에 놓을 요리 카드를 골라봐요. 기존 요리 8종을 살펴봐요. 영양은 식사 기록에 직접 입력한 값으로 계산해요.</p><div class="recipe-sheet">${window.KitchenCatalog.map(({name,f})=>`<button type="button" class="recipe-option" data-recipe="${name}" aria-pressed="${items.find(r=>r.kind==='meal').name===name}">${window.KitchenStoryboardArt.dish({id:name})}<strong>${name}</strong><small>${f.join(' · ')}</small></button>`).join('')}</div>`,'TODAY’S LITTLE MEAL');}
  function showItem(item) {
    if(item.kind==='decor'){beginDecorEdit();item=decorEdit.items.find(i=>i.id===item.id)||item;}
    selected=item.id;render(true);if(window.KitchenWorkflows&&['food','seasoning'].includes(item.kind))return window.KitchenWorkflows.item(item.id);if(item.kind==='meal'){showRecipes();return;}
    if(item.kind==='decor') {
      decorating=true;render(true);openTray(item.name,`<div class="ingredient-preview">${art(item)}</div><p class="tray-note">창을 닫고 소품을 끌어 위치를 바꿔보세요. 겹쳐 놓고 앞뒤 순서도 고를 수 있어요.</p><div class="tray-actions"><button type="button" class="small-action" data-layer="back" data-id="${esc(item.id)}">뒤로 보내기</button><button type="button" class="small-action" data-layer="front" data-id="${esc(item.id)}">앞으로 가져오기</button><button type="button" class="small-action" data-remove="${esc(item.id)}">소품 치우기</button><button type="button" class="small-action primary" data-close>옮기기</button></div>`);return;
    }
    const zones={...Object.fromEntries(Object.entries(panels).map(([key,p])=>[key,p.name])),seasoning:'양념 선반',counter:'조리대'};
    openTray(item.name,`<form id="ingredientForm"><div class="ingredient-form"><div class="ingredient-preview">${art(item)}</div><div class="form-fields"><label>수량<input name="quantity" value="${esc(item.quantity)}" maxlength="40" placeholder="예: 2개"></label><label>유통·소비기한<input name="expiry" type="date" min="1900-01-01" max="9999-12-31" value="${esc(item.expiry)}"></label><label>놓을 곳<select name="zone">${Object.entries(zones).map(([key,name])=>`<option value="${key}" ${item.zone===key?'selected':''}>${name}</option>`).join('')}</select></label><span class="hint">이 시안의 예시 값만 바뀌어요.</span></div></div><div class="tray-actions"><button type="button" class="small-action" data-close>닫기</button><button type="submit" class="small-action primary">시안에 적용</button></div></form>`,'OUR INGREDIENTS');
    $('#ingredientForm').addEventListener('submit',event=>{event.preventDefault();const f=new FormData(event.currentTarget),next=f.get('zone');item.quantity=f.get('quantity').trim();item.expiry=f.get('expiry');if(item.zone!==next){item.zone=next;item.x=.5;item.y=.63;item.z=++layer;}if(panels[next])doors[next]=true;if(compact())setCamera(panels[next]?'fridge':next==='seasoning'?'seasoning':'counter');render();closeTray();announce(item.name+'의 시안 값을 바꿨어요.');});
  }
  function moveLayer(id,direction,{close=true}={}){const item=sceneItems().find(r=>r.id===id);if(!item)return;const preview=item.kind==='decor'&&Boolean(decorEdit),pool=preview?decorEdit.items:items;const order=pool.filter(r=>r.zone===item.zone&&r!==item).sort((a,b)=>a.z-b.z);if(direction==='front')order.push(item);else order.unshift(item);order.forEach((r,i)=>{r.z=i+1;});render(preview);if(close&&$('#tray').open)closeTray();announce(item.name+'을 '+(direction==='front'?'앞에':'뒤에')+' 놓았어요.');}
  let ghost=null, scrollFrame=0, pointer=null, completedItemPointer=null;
  function rememberItemPointer(event){completedItemPointer={x:event.clientX,y:event.clientY,id:event.pointerId,at:performance.now()};}
  // An item tap replaces the canvas DOM and opens a sheet on pointerup. Consume
  // only that gesture's following compatibility click, which can otherwise hit
  // a newly positioned sheet button. The next physical pointerdown is independent.
  document.addEventListener('pointerdown',()=>{completedItemPointer=null;},true);
  document.addEventListener('click',event=>{
    const p=completedItemPointer;if(!p||!event.isTrusted||event.detail===0)return;
    completedItemPointer=null;
    const samePointer=!('pointerId' in event)||event.pointerId===p.id||event.pointerId===-1;
    if(samePointer&&performance.now()-p.at<650&&Math.hypot(event.clientX-p.x,event.clientY-p.y)<8){event.preventDefault();event.stopImmediatePropagation();}
  },true);
  function cleanup(){cancelAnimationFrame(scrollFrame);scrollFrame=0;pointer=null;if(active){active.button.classList.remove('is-dragging');try{active.button.releasePointerCapture(active.pointer);}catch(_){}active=null;}ghost?.remove();ghost=null;for(const zone of document.querySelectorAll('.is-over'))zone.classList.remove('is-over');}
  function dropAt(x,y){const hit=document.elementFromPoint(x,y);if(hit?.closest('.home-shortcuts,#homeWorktop,.fridge-add,#addFood,.decor-footer,.decor-toolbar,.worktop-actions,.kitchen-milestone,.kitchen-progress,.scene-tools,.room-caption,.tray'))return null;const direct=hit?.closest('.drop-zone');if(direct&&isAvailable(direct.dataset.zone)){const r=direct.getBoundingClientRect();if(x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom)return direct;}return [...document.querySelectorAll('.drop-zone')].reverse().find(z=>{if(!isAvailable(z.dataset.zone)||z.hidden||getComputedStyle(z).visibility!=='visible')return false;const r=z.getBoundingClientRect();return r.width>0&&r.height>0&&x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom;})||null;}
  function highlightDrop(x,y){for(const z of document.querySelectorAll('.is-over'))z.classList.remove('is-over');const target=dropAt(x,y);if(active&&target&&isAvailable(target.dataset.zone)&&(active.item.kind!=='decor'||target.dataset.zone==='counter'))target.classList.add('is-over');}
  function scrollDrag(){
    scrollFrame=0;if(!active?.moved||!pointer)return;
    const edge=72,y=pointer.y,delta=y<edge?-Math.ceil(18*Math.min(1,(edge-y)/edge)):y>innerHeight-edge?Math.ceil(18*Math.min(1,(y-innerHeight+edge)/edge)):0;
    if(!delta)return;
    const before=window.scrollY;window.scrollBy(0,delta);
    if(window.scrollY!==before){highlightDrop(pointer.x,pointer.y);scrollFrame=requestAnimationFrame(scrollDrag);}
  }
  function paintedFoodTarget(button,event){
    if(!button.closest('.fridge-interiors'))return button;
    const contains=rect=>rect&&rect.width>0&&rect.height>0&&event.clientX>=rect.left&&event.clientX<=rect.right&&event.clientY>=rect.top&&event.clientY<=rect.bottom;
    if(contains(button.querySelector('.food-art')?.getBoundingClientRect()))return button;
    const painted=[...document.querySelectorAll('.fridge-interiors .drop-zone:not([hidden])>.item')].filter(node=>contains(node.querySelector('.food-art')?.getBoundingClientRect()));
    return painted.sort((a,b)=>Number(b.style.zIndex)-Number(a.style.zIndex))[0]||button;
  }
  document.addEventListener('pointerdown',event=>{
    let button=event.target.closest('.room .item');if(!button||active||event.isPrimary===false||event.button!==0)return;button=paintedFoodTarget(button,event);const item=sceneItems().find(r=>r.id===button.dataset.item);if(!item)return;if(item.kind==='decor'&&!decorating)return;
    const rect=button.getBoundingClientRect();active={item,button,pointer:event.pointerId,startX:event.clientX,startY:event.clientY,moved:false,w:rect.width,h:rect.height,ax:(event.clientX-rect.left)/rect.width,ay:(event.clientY-rect.top)/rect.height};button.focus({preventScroll:true});button.setPointerCapture?.(event.pointerId);event.preventDefault();
  });
  window.addEventListener('pointermove',event=>{
    const drag=active;if(!drag||event.pointerId!==drag.pointer)return;if(!drag.moved&&Math.hypot(event.clientX-drag.startX,event.clientY-drag.startY)<6)return;event.preventDefault();
    if(!drag.moved){drag.moved=true;drag.button.classList.add('is-dragging');ghost=itemButton(drag.item);ghost.classList.add('ghost');ghost.removeAttribute('data-item');ghost.setAttribute('aria-hidden','true');ghost.tabIndex=-1;ghost.disabled=true;Object.assign(ghost.style,{width:drag.w+'px',height:drag.h+'px'});document.body.appendChild(ghost);
      const sourceArt=drag.button.querySelector('.food-art'),copyArt=ghost.querySelector('.food-art');
      if(sourceArt&&copyArt){const r=sourceArt.getBoundingClientRect(),b=drag.button.getBoundingClientRect();Object.assign(copyArt.style,{position:'absolute',left:(r.left-b.left)+'px',top:(r.top-b.top)+'px',right:'auto',bottom:'auto',width:r.width+'px',height:r.height+'px',maxHeight:'none',transform:'none'});}
    }
    ghost.style.left=event.clientX-drag.w*drag.ax+'px';ghost.style.top=event.clientY-drag.h*drag.ay+'px';pointer={x:event.clientX,y:event.clientY};highlightDrop(pointer.x,pointer.y);if(!scrollFrame)scrollFrame=requestAnimationFrame(scrollDrag);
  },{passive:false});
  window.addEventListener('pointerup',event=>{
    const drag=active;if(!drag||event.pointerId!==drag.pointer)return;event.preventDefault();const target=dropAt(event.clientX,event.clientY),wasMoved=drag.moved;rememberItemPointer(event);cleanup();if(!wasMoved){selectCanvasItem(drag.item);return;}
    const zone=target?.dataset.zone;if(!zone||!isAvailable(zone)||((drag.item.kind==='decor'||drag.item.kind==='meal')&&zone!=='counter')){announce('놓을 수 있는 선반이나 조리대에 옮겨주세요.');return;}
    const rect=target.getBoundingClientRect(),art=drag.button.querySelector('.food-art'),half=Math.min(.5,(art?.getBoundingClientRect().width||drag.w)/2/rect.width);drag.item.zone=zone;drag.item.x=clamp((event.clientX-drag.w*drag.ax+drag.w/2-rect.left)/rect.width,half,1-half);drag.item.y=clamp((event.clientY+drag.h*(1-drag.ay)-rect.top)/rect.height,Math.min(1,drag.h/rect.height),1);drag.item.z=nextItemLayer(drag.item);selected=drag.item.id;render(drag.item.kind==='decor'&&Boolean(decorEdit));announce(drag.item.name+'을 원하는 자리에 놓았어요.',false);
  });
  const layoutObserver=new ResizeObserver(()=>{syncLayout();constrainItems();});
  for(const node of [$('#dailyBalance'),$('#kitchenMilestone'),$('#homeStorageNotice'),$('#kitchenProgress'),$('#fridgeSceneHost'),$('#decorStage'),$('#homeWorktop'),$('.home-shortcuts'),$('.decor-heading'),$('.decor-actions'),$('.decor-toolbar'),$('.decor-footer')])if(node)layoutObserver.observe(node);
  window.addEventListener('pointercancel',event=>{if(active&&event.pointerId===active.pointer)rememberItemPointer(event);cleanup();});window.addEventListener('blur',cleanup);window.addEventListener('resize',()=>{cleanup();syncLayout();constrainItems();});
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&active){event.preventDefault();cleanup();announce('이동을 취소했어요.',false);return;}const button=event.target.closest('.room .item');if(!button)return;const item=sceneItems().find(r=>r.id===button.dataset.item);if(!item)return;
    if(event.key==='Enter'||event.key===' '){event.preventDefault();selectCanvasItem(item);return;}
    const vector={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];if(vector&&(item.kind!=='decor'||decorating)){event.preventDefault();const step=event.shiftKey ? .1 : .025;item.x=clamp(item.x+vector[0]*step,.15,.85);item.y=clamp(item.y+vector[1]*step,.2,1);item.z=nextItemLayer(item);constrainItems();if(item.kind==='decor')syncDecorToolbar();notifyChange(item.kind==='decor'&&Boolean(decorEdit));announce(item.name+' 위치를 바꿨어요.',false);}
  });
  document.addEventListener('click',event=>{
    const button=event.target.closest('button');if(!button)return;if(button.dataset.door)toggle(button.dataset.door);if(button.dataset.camera)setCamera(button.dataset.camera);
    if(button.id==='addFood')showAdd();if(button.id==='recipes')showRecipes();if(button.id==='decorate'){if(window.KitchenWorkflows){window.KitchenWorkflows.decor();return;}if(decorating){decorating=false;selected=null;render();announce('소품 배치를 마쳤어요.');}else showDecor();}
    if(button.hasAttribute('data-decor-apply')){try{const changed=applyDecorEdit();for(const key of Object.keys(doors))doors[key]=false;selected=null;setCamera('fridge');render(true);$('#panel-fridge').dataset.screenId='D6';syncLayout();window.dispatchEvent(new CustomEvent('mini-kitchen:decor-applied'));announce(changed?'나의 부엌에 적용했어요.':'현재 배치를 확인했어요.');}catch(error){announce(error.message);}return;}
    if(button.hasAttribute('data-decor-cancel')){const returnTo=decorEdit?.returnTo||'growth';cancelDecorEdit();setCamera('fridge');if(window.KitchenHome)window.KitchenHome.selectSubtab('growth',{focus:returnTo!=='rewards'});if(returnTo==='rewards')window.KitchenJournal?.show('rewards');announce('편집 전 배치와 꾸밈권을 유지했어요.',false);return;}
    if(button.id==='propList'){if(window.KitchenJournal)window.KitchenJournal.show('rewards');else showDecor();}
    if(button.dataset.decorSelect){const item=sceneItems().find(i=>i.id===button.dataset.decorSelect&&i.kind==='decor');if(item){beginDecorEdit();selected=item.id;render(true);document.querySelector('.room [data-item="'+CSS.escape(item.id)+'"]')?.focus({preventScroll:true});}return;}
    if(button.dataset.decorReward){try{previewDecorReward(button.dataset.decorReward);}catch(error){announce(error.message);}return;}
    if(button.dataset.decorTool){const item=sceneItems().find(i=>i.id===selected&&i.kind==='decor');if(!item||!decorating||!decorEdit)return;const tool=button.dataset.decorTool;if(tool==='remove')removeDecor(item.id,{close:false});else if(tool==='front'||tool==='back')moveLayer(item.id,tool,{close:false});return;}
    if(button.id==='expandDisplays')openTray('냉장고 디스플레이',`<div class="display-inspector">${renderDisplays(true)}</div><p class="tray-note">현재 기록의 확대 화면이에요. 기한별 숫자는 재료·양념 기록 건수이며, 재료 기록률은 이름 기준으로 수량의 충분함을 확인한 값은 아니에요.</p>`,'OUR KITCHEN');
    if(button.dataset.selectProp){const item=sceneItems().find(r=>r.id===button.dataset.selectProp&&r.kind==='decor');if(item)showItem(item);}
    if(button.id==='closeTray'||button.hasAttribute('data-close'))closeTray();
    if(button.dataset.addFood){const id='added'+(++serial),name=button.dataset.addFood;items.push({id,kind:'food',name,quantity:'1개',expiry:date(3),zone:'freshLeft',x:.5,y:.63,z:++layer});doors.freshLeft=true;setCamera('fridge');selected=id;render();closeTray();announce(name+'을 시안 냉장고에 담았어요.');}
    if(button.dataset.addProp){const key=button.dataset.addProp;if(!Object.hasOwn(props,key))return;const reward=Object.entries(window.KitchenPlayModel?.REWARDS||{}).find(([,r])=>r.kind==='room'&&r.art===key);if(reward){try{previewDecorReward(reward[0]);}catch(error){announce(error.message);}return;}beginDecorEdit();if(items.filter(i=>i.kind!=='decor').length+decorEdit.items.length>=2000){announce('소품을 더 놓기 전에 기존 소품을 정리해 주세요.');return;}let id;decorEdit.serial=Math.max(serial,decorEdit.serial);do{id='decor'+(++decorEdit.serial);}while(items.some(i=>i.id===id)||decorEdit.items.some(i=>i.id===id));decorEdit.items.push({id,kind:'decor',art:key,name:props[key].name,zone:'counter',x:.84,y:.98,z:nextItemLayer({kind:'decor'})});selected=id;setCamera('counter');render(true);closeTray();announce(props[key].name+'을 미리 놓았어요. 적용을 누르면 저장해요.');}
    if(button.dataset.layer)moveLayer(button.dataset.id,button.dataset.layer);if(button.dataset.remove)removeDecor(button.dataset.remove);
    if(button.dataset.recipe){items.find(r=>r.kind==='meal').name=button.dataset.recipe;setCamera('counter');render();closeTray();announce('조리대에 '+button.dataset.recipe+'을 놓았어요.');window.dispatchEvent(new CustomEvent('mini-kitchen:recipe',{detail:{name:button.dataset.recipe}}));}
    if(button.id==='help')openTray('작은 부엌을 만져봐요',`<ul class="help-list"><li>냉장고 문을 누르면 열리고, 열린 문을 다시 누르면 닫혀요.</li><li>재료·양념병은 누르면 수량·기한을 살펴보고, 끌어서 옮길 수 있어요.</li><li>다른 칸으로 옮길 때는 그 문을 먼저 열어주세요.</li><li>‘꾸미기’에서 소품을 놓고 끌어 배치해요.</li><li>재료와 소품은 겹쳐 놓을 수 있고, 방향키로도 움직여요.</li><li>양념은 재료 목록의 양념 보기에서, 소품 배치는 내 부엌의 꾸미기에서 관리해요.</li></ul><p class="tray-note">기존 앱과 분리된 시안이에요. 저장 가능한 브라우저에서는 재료·식사·꾸밈 기록을 보관해요. 임시 세션에서는 메뉴의 설정·백업에서 기록을 보관해 주세요. 영양은 직접 입력한 값으로 계산하며 제품·기한 사진은 글자를 읽고 직접 검수해요. 전체 사진 재료 판별·자동 영양 추정·기존 앱 동기화는 연결 전이에요.</p>`);
  });
  $('#tray').addEventListener('click',event=>{if(event.target!==$('#tray'))return;const r=$('#tray').getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)closeTray();});
  $('#tray').addEventListener('close',()=>{if(!$('#tray').open){if($('#trayContent .display-inspector'))$('#trayContent').replaceChildren();restoreTrayFocus();}});
  for(const node of document.querySelectorAll('[data-icon]'))node.innerHTML=A.icon(node.dataset.icon);
  document.title='한끼의 부엌 · '+(mode==='widget'?'위젯':'앱')+' 미니어처 시안';syncLayout();render();
  window.MiniKitchen=Object.freeze({
    isDoorClosing:key=>closing.has(key),
    getSnapshot:()=>JSON.parse(JSON.stringify({mode,doors,items:sceneItems(),decorating,selected,camera:document.body.dataset.camera,decorEdit:getDecorDraftState()})),
    exportWorld:()=>JSON.parse(JSON.stringify({items,doors,serial,layer})),
    restoreWorld(world,preserveSelection=false){cleanup();if(!preserveSelection)decorEdit=null;items.splice(0,items.length,...JSON.parse(JSON.stringify(world.items)));for(const key of Object.keys(panels))doors[key]=world.doors[key];serial=world.serial;layer=world.layer;if(!preserveSelection)selected=null;decorating=Boolean(decorEdit)&&document.body.dataset.camera==='counter';render();},
    showTray:openTray,closeTray,refreshDisplays:renderDisplays,refreshLayout:()=>{syncLayout();constrainItems();},showItem:id=>{const item=sceneItems().find(r=>r.id===id);if(item)showItem(item);},setCamera,decorate:showDecor,render,announce,
    getArt:art,getFridgeArt:()=>roomFridgeArt('home-fridge-art'),beginDecorEdit,applyDecorEdit,cancelDecorEdit,leaveDecor,previewDecorReward,hasDecorDraft:()=>Boolean(decorEdit),getDecorDraftState,setDecorThemeDraft,getDecorThemeDraft:()=>decorEdit?clone(decorEdit.theme):null,setDecorEquippedDraft,getDecorEquippedDraft:()=>decorEdit?clone(decorEdit.equipped):null,
    highlightItem(id){const item=items.find(r=>r.id===id);if(!item)return;document.body.dataset.fridgeState='saved';$('#panel-fridge').dataset.screenId='A5';const key=doorForZone(displayZone(item));if(panels[key])doors[key]=true;selected=id;highlightedItem=id;highlightUntil=Date.now()+3500;render(true);setTimeout(()=>{for(const button of document.querySelectorAll('.item.is-new'))button.classList.remove('is-new');highlightedItem=null;},3500);},
    chooseRecipe(name){if(!window.KitchenCatalog.some(r=>r.name===name))return;items.find(r=>r.kind==='meal').name=name;setCamera('counter');render();closeTray();window.dispatchEvent(new CustomEvent('mini-kitchen:recipe',{detail:{name}}));}
  });
  window.KitchenSceneArt=Object.freeze({...A,foodArt(id,cls=''){const name=stockNameById[id];return name?art({kind:'food',name}):A.foodArt(retainedFoodIds.has(id)?id:'ingredient',cls);},seasoningArt(name){return art({kind:'seasoning',name});}});
})();
