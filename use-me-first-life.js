/* Shared app/widget life screens. Unconnected recognition never fabricates data. */
(() => {
  'use strict';
  const L=window.UMFLife, S=window.UMFLifeStore, I=window.UMFStore;
  if (!L || !S || !I) return;
  const $=s=>document.querySelector(s), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money=v=>new Intl.NumberFormat('ko-KR').format(v)+'원', uid=()=>window.crypto?.randomUUID?.() || 'life-'+Date.now()+'-'+Math.random().toString(36).slice(2);
  const field=(label,name,type='text',extra='')=>`<label>${label}<input name="${name}" type="${type}" ${extra}></label>`;
  const page=(name,title,sub,content)=>`<section class="kitchen-page life-page" data-kitchen-view="${name}" aria-labelledby="life-${name}-title" hidden><div class="life-page-heading"><div><span class="life-kicker">MY LITTLE KITCHEN</span><h1 id="life-${name}-title" tabindex="-1">${title}</h1><p>${sub}</p></div><button class="btn btn-line" data-kitchen-page="home">냉장고로</button></div><p class="life-local-note">생활 기록은 이 브라우저에 저장돼요. 다른 기기 동기화는 아직 지원하지 않아요.</p>${content}</section>`;
  const submit=text=>`<button type="submit" class="btn btn-sage">${text}</button>`;
  const dateField=()=>field('날짜','day','date','required min="1900-01-01" max="9999-12-31"');
  const numField=(label,name,required=false)=>field(label,name,'number',`min="0" max="100000000" step="any" inputmode="decimal" ${required?'required':''}`);
  const sourceNote='<p class="life-note">직접 입력한 영양정보만 집계해요. 빈칸은 미확인 값으로 남으며, 자동 계산·개인별 권장량은 아직 제공하지 않아요.</p>';
  const tabs=[['photos','사진 등록'],['garden','꾸미기·성장'],['budget','식비'],['nutrition','영양·영양제'],['monthly','월간 기록']];
  $('#main').insertAdjacentHTML('afterbegin','<nav class="life-tools" aria-label="부엌 생활 메뉴">'+tabs.map(([key,label])=>`<button data-kitchen-page="${key}">${label}</button>`).join('')+'</nav><div id="lifeStatus" class="life-status" role="status" aria-live="polite" hidden></div>');
  $('#umfHomeTitle').textContent='잘 먹는 하루, 자라는 부엌.';
  $('#umfHomePage > .intro .sub').textContent='재료를 돌보고, 한 끼를 기록하고, 내 취향으로 채워요.';
  $('#umfHomePage > .intro').insertAdjacentHTML('afterend','<div class="life-today" id="lifeToday"></div>');
  $('#main').insertAdjacentHTML('beforeend',
    page('garden','나와 함께 자라는 부엌','목표를 고르고, 하루 한 번의 작은 돌봄으로 꾸며요.',`
      <div class="life-columns"><section class="life-card garden-card"><div id="lifeGarden"></div></section><section class="life-card"><span class="life-kicker">MY CHOICE</span><h2>오늘의 작은 목표</h2><p class="life-note">어떤 목표든 하루 한 번, 10잎을 모아요. 놓친 날의 차감은 없어요.</p><form id="lifeGoalForm"><label>목표 선택<select name="goal"><option value="care">냉장고·기한 확인하기</option><option value="meal">한 끼 기록하기</option><option value="budget">오늘 식비 기록하기</option></select></label>${submit('이 목표로 정하기')}</form><div id="lifeClaim"></div><h2 class="life-section-title">부엌 분위기 고르기</h2><div id="lifeThemes" class="life-theme-choices"></div></section></div>`)+
    page('photos','사진에서 시작하는 재료 정리','두 장으로 등록하거나, 냉장고 전체를 보며 차근차근 정리해요.',`
      <div class="life-card"><div class="life-segment" role="group" aria-label="사진 등록 방식"><button type="button" data-photo-mode="product" aria-pressed="true">제품 + 기한 · 2장</button><button type="button" data-photo-mode="fridge" aria-pressed="false">냉장고 전체 · 1장</button></div><p class="life-connection">지금은 사진을 보며 직접 입력해요. 자동 인식과 사진 아이콘 생성은 아직 연결되지 않았어요.</p><div id="lifeProductPhotos" class="life-photo-grid">${photo('product','01','제품 사진')}${photo('expiry','02','유통·소비기한 사진')}</div><div id="lifeFridgePhoto" hidden>${photo('fridge','01','냉장고 전체 사진')}</div><p class="life-note">사진은 이 화면에서만 미리 보고, 저장하거나 전송하지 않아요. JPEG·PNG·WebP, 한 장당 12MB까지.</p><form id="lifePhotoForm" class="life-form"><label>사진에서 확인한 재료명<input name="name" required maxlength="80" placeholder="예: 두부"></label><label>등록할 곳<select name="kind"><option value="fridge">냉장고 재료</option><option value="season">기본 양념</option></select></label>${submit('직접 확인하고 등록하기')}</form><p class="life-note">다음 입력창에서 수량과 기한을 확인해 저장해요. 여러 재료는 하나씩 등록해 주세요. 아이콘은 기존 재료 그림을 사용해요.</p></div>`)+
    page('budget','맛있게 먹고, 알맞게 쓰고.','이번 달 예산과 실제 식비를 나란히 살펴봐요.',`
      <div id="lifeBudgetSummary" class="life-metrics"></div><div class="life-columns"><section class="life-card"><h2>한 달 식비 목표</h2><form id="lifeBudgetForm">${numField('월 예산 (원) · 비우면 미설정','budget')}${submit('예산 저장')}</form><p class="life-note">이 부엌에서 입력한 식비만 합산해요. 다른 가계부 기록은 자동으로 가져오지 않아요.</p></section><section class="life-card"><h2>쓴 돈 기록하기</h2><form id="lifeExpenseForm" class="life-form">${dateField()}${field('내용','name','text','required maxlength="100" placeholder="예: 주말 장보기"')}<label>분류<select name="category"><option value="groceries">장보기</option><option value="eatingout">외식·배달</option></select></label>${numField('금액 (원)','amount',true)}${submit('식비 기록')}</form></section></div><section class="life-card"><h2>이번 달 지출</h2><div id="lifeExpenses"></div></section>`)+
    page('nutrition','내 식사를 조금 더 알아가요.','영양표를 옮겨 적고, 챙긴 영양제도 기록해요.',`
      <div class="life-day-heading"><h2>오늘 입력한 영양</h2><span id="lifeNutritionDate"></span></div><div id="lifeNutrients" class="life-metrics"></div>${sourceNote}<div class="life-columns"><section class="life-card"><h2>식사 영양정보 기록</h2><form id="lifeNutritionForm" class="life-form">${dateField()}${field('음식 이름','name','text','required maxlength="100" placeholder="먹은 양 기준으로 입력"')}${numField('열량 (kcal)','kcal')}${numField('탄수화물 (g)','carb')}${numField('단백질 (g)','protein')}${numField('지방 (g)','fat')}${submit('영양 기록')}</form><p class="life-note">제품 영양표나 확인한 자료의 섭취 분량 값을 입력하세요. 레시피 재료량으로 영양을 계산하는 연결은 준비 중이에요.</p></section><section class="life-card"><h2>내가 정한 하루 목표</h2><form id="lifeTargetsForm" class="life-form">${numField('열량 (kcal)','kcal')}${numField('탄수화물 (g)','carb')}${numField('단백질 (g)','protein')}${numField('지방 (g)','fat')}${submit('목표 저장')}</form><p class="life-note">개인별 권장 섭취량을 계산한 값이 아니에요. 목표가 없으면 비워 두세요.</p></section></div><section class="life-card"><h2>영양제 챙기기</h2><form id="lifeSupplementForm" class="life-form">${field('제품명','name','text','required maxlength="100"')}${field('내 복용 메모','amount','text','maxlength="100" placeholder="제품 표시나 안내받은 내용"')}${submit('영양제 추가')}</form><p class="life-note">복용 여부와 메모를 기록해요. 제품의 함량·상호작용이나 권장 복용량을 계산하지 않아요.</p><div id="lifeSupplements"></div></section><section class="life-card"><h2>이번 달 영양 입력</h2><div id="lifeNutritionRows"></div></section>`)+
    page('monthly','한 달의 식탁을 한눈에.','식사 기록·실제 식비·입력한 영양 비율을 함께 살펴봐요.',`
      <div class="life-month-control"><label>살펴볼 달<input type="month" id="lifeMonth" min="1900-01" max="9999-12"></label><button class="btn btn-line" id="lifeExport">생활 기록 내려받기</button></div><div id="lifeMonthSummary" class="life-metrics"></div><div class="life-columns"><section class="life-card"><h2>탄수화물·단백질·지방</h2><div id="lifeRatio"></div><p class="life-note">세 항목을 모두 입력한 기록만 사용해요. 탄수화물·단백질 4kcal/g, 지방 9kcal/g으로 환산한 기록 내 에너지 비율이에요. 영양제는 합산하지 않아요.</p></section><section class="life-card"><h2>이번 달을 돌아보며</h2><div id="lifeMonthNotes"></div><p class="life-note">기록이 없는 날짜는 미기록이에요. 0원 지출·0 영양 섭취로 간주하지 않아요.</p></section></div>`)
  );
  function photo(key,index,label) {
    return `<label class="life-photo"><span class="life-photo-number">${index}</span><strong>${label}</strong><span class="life-note">사진 찍기 / 선택</span><input type="file" data-life-photo="${key}" accept="image/jpeg,image/png,image/webp" capture="environment"><img data-life-photo-preview="${key}" alt="${label} 미리보기" hidden></label>`;
  }
  function plant(points,large=false) {
    const stage=Math.min(2,Math.floor(points/30));
    return `<svg viewBox="0 0 180 180" class="life-plant ${large?'large':''}" aria-hidden="true"><defs><linearGradient id="pot-${large}" x2="1" y2="1"><stop stop-color="#fcf5e8"/><stop offset="1" stop-color="#d6b99b"/></linearGradient></defs><ellipse cx="90" cy="164" rx="47" ry="8" fill="#755438" opacity=".12"/><path d="M90 125 Q99 93 88 53" stroke="#648451" stroke-width="5" fill="none"/><path d="M91 91Q45 87 57 57Q95 53 91 91M92 73Q129 76 130 42Q95 39 92 73" fill="#8fa56e"/>${stage>0?'<path d="M94 113Q137 114 140 82Q99 79 94 113M90 63Q58 47 75 26Q101 36 90 63" fill="#6d8d56"/>':''}${stage>1?'<path d="M91 44Q120 34 109 10Q83 15 91 44M87 113Q49 113 42 88Q81 77 87 113" fill="#99af74"/>':''}<path d="M56 117H124L117 156Q90 170 63 156Z" fill="url(#pot-${large})" stroke="#c6ac91"/><ellipse cx="90" cy="117" rx="34" ry="9" fill="#e5cfb5" stroke="#c6ac91"/><ellipse cx="90" cy="116" rx="27" ry="5" fill="#8e7153"/><path d="M90 123L92 104" stroke="#708b54" stroke-width="5"/><path d="M69 132v18" stroke="#fffaf2" stroke-width="4" stroke-linecap="round" opacity=".8"/></svg>`;
  }
  const goals={care:'냉장고·기한 확인하기',meal:'한 끼 기록하기',budget:'오늘 식비 기록하기'};
  const themes={oat:'오트 크림',sage:'세이지 그린',rose:'로즈 밀크'};
  let busy=false, viewedMonth=L.today().slice(0,7), undo=null;
  function status(message,isError=false) {const box=$('#lifeStatus');box.hidden=false;box.classList.toggle('bad',isError);box.textContent=message;}
  function rows(target,values,kind,format) {
    $(target).innerHTML=values.length?values.slice().reverse().map(r=>`<div class="life-row"><div><strong>${esc(r.name)}</strong><small>${esc(r.day || r.amount || '메모 없음')}${kind==='supplements'?'': ' · '+esc(format(r))}</small></div>${kind==='supplements'?`<button class="btn btn-line" data-supplement="${esc(r.id)}" aria-pressed="${r.days.includes(L.today())}">${r.days.includes(L.today())?'오늘 챙김':'오늘 체크'}</button>`:''}<button class="life-delete" data-life-delete="${kind}" data-id="${esc(r.id)}" aria-label="${esc(r.name)} 기록 삭제">삭제</button></div>`).join(''):'<p class="life-empty">아직 기록이 없어요. 첫 기록부터 천천히 채워요.</p>';
  }
  function render() {
    const error=S.error, s=S.getState(), inventory=I.getState(), today=L.today(), month=today.slice(0,7), points=s.claims.length*10, done=s.claims.includes(today);
    document.body.dataset.lifeTheme=s.theme;
    const level=Math.floor(s.claims.length/3)+1, next=30-points%30;
    $('#lifeToday').innerHTML=`<div class="life-today-copy"><span class="life-kicker">MY KITCHEN · LEVEL ${level}</span><strong>작은 돌봄이 모여, 내 부엌이 자라요.</strong><span>오늘의 목표 · ${goals[s.goal]}</span><button class="life-text-button" data-kitchen-page="garden">${done?'오늘 목표 완료':'목표 확인하기'} <span aria-hidden="true">↗</span></button></div><div class="life-today-growth">${plant(points)}<div><strong>${points}잎</strong><small>다음 성장까지 ${next}잎</small><span class="life-progress"><i style="width:${points%30/30*100}%"></i></span></div></div>`;
    $('#lifeGarden').innerHTML=`<span class="life-kicker">YOUR LITTLE GARDEN</span><div class="life-garden-stage">${plant(points,true)}<div class="life-garden-shelf"></div></div><h2>레벨 ${level} · ${points<30?'처음 만난 새싹':points<60?'잎이 자라는 중':'싱그러운 나의 허브'}</h2><p class="life-note">${s.claims.length}일의 돌봄을 모았어요. 30잎마다 레벨이 올라요.</p><span class="life-reward-pill">${points}잎 모음</span>`;
    $('#lifeClaim').innerHTML=`<button type="button" class="btn btn-sage" id="lifeClaimButton" ${done?'disabled':''}>${done?'오늘의 10잎을 받았어요':s.goal==='care'?'오늘 재료·기한 확인 완료 · 10잎':'기록 확인하고 10잎 받기'}</button><p class="life-note">${s.goal==='care'?'재료의 보관 상태와 표시 기한을 직접 확인한 후 눌러 주세요.':'오늘의 해당 기록이 있을 때 받을 수 있어요.'}</p>`;
    $('#lifeThemes').innerHTML=Object.entries(themes).map(([key,name])=>`<button type="button" class="life-theme" data-life-theme="${key}" aria-pressed="${s.theme===key}" ${points<L.THEMES[key]?'disabled':''}><span class="life-swatch ${key}"></span><strong>${name}</strong><small>${L.THEMES[key]===0?'처음부터':points>=L.THEMES[key]?'선택 가능':L.THEMES[key]+'잎에 열려요'}</small></button>`).join('');
    const monthly=L.report(s,inventory,month), viewed=L.report(s,inventory,viewedMonth);
    $('#lifeBudgetSummary').innerHTML=metric('이번 달 지출',money(monthly.spending),'입력한 지출 기준')+metric('월 예산',s.budget===null?'미설정':money(s.budget),'직접 정한 목표')+metric('예산 잔액',s.budget===null?'—':money(s.budget-monthly.spending),'미입력 지출은 미반영');
    rows('#lifeExpenses',monthly.expenses,'expenses',r=>money(r.amount)+(r.category==='groceries'?' · 장보기':' · 외식·배달'));
    const daily=s.nutrition.filter(r=>r.day===today);
    $('#lifeNutritionDate').textContent=today;
    $('#lifeNutrients').innerHTML=Object.entries({kcal:['열량','kcal'],carb:['탄수화물','g'],protein:['단백질','g'],fat:['지방','g']}).map(([k,[label,unit]])=>{
      const known=daily.filter(r=>r[k]!==null), value=known.reduce((sum,r)=>sum+r[k],0), target=s.targets[k];
      return metric(label,known.length?Math.round(value*10)/10+' '+unit:'—',`입력 ${known.length}/${daily.length}건 · 목표 ${target===null?'미설정':target+unit}`);
    }).join('');
    rows('#lifeNutritionRows',monthly.rows,'nutrition',r=>r.kcal===null?'열량 미입력':r.kcal+' kcal · 직접 입력');
    rows('#lifeSupplements',s.supplements,'supplements',()=> '');
    $('#lifeMonthSummary').innerHTML=metric('식사 기록',viewed.meals+'끼','기존 식사 기록 포함')+metric('실제 식비',money(viewed.spending),viewed.expenses.length+'건 입력')+metric('영양 입력한 날',viewed.days+'일',viewed.rows.length+'건 · 직접 입력');
    $('#lifeRatio').innerHTML=viewed.ratio?Object.entries({carb:'탄수화물',protein:'단백질',fat:'지방'}).map(([k,label])=>`<div class="life-ratio-row"><span>${label}</span><div><i class="${k}" style="width:${viewed.ratio[k]}%"></i></div><strong>${Math.round(viewed.ratio[k])}%</strong></div>`).join(''):'<p class="life-empty">아직 비율을 계산할 수 없어요.<br>탄수화물·단백질·지방을 모두 입력한 식사부터 표시해요.</p>';
    $('#lifeMonthNotes').innerHTML=`<p>영양 ${viewed.rows.length}건 중 <strong>${viewed.complete}건</strong>에 세 영양소가 모두 있어요.</p><p>식비는 ${viewed.expenses.length}건, 식사는 ${viewed.meals}끼를 기록했어요.</p><p>서로 연결되지 않은 식사·영양 입력이 포함될 수 있어요. 한 달 전체 섭취량이나 건강 평가를 뜻하지 않아요.</p>`;
    if(error || S.error) status(error || S.error,true);
    if(busy) for(const button of document.querySelectorAll('#lifeClaimButton,[data-life-theme],[data-supplement],[data-life-delete]'))button.disabled=true;
  }
  function metric(label,value,note) {return `<div class="life-metric"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`;}
  function populate() {
    const s=S.getState(); $('#lifeGoalForm select').value=s.goal; $('#lifeBudgetForm input').value=s.budget??'';
    for(const [k,v] of Object.entries(s.targets)) $('#lifeTargetsForm [name="'+k+'"]').value=v??'';
    for(const input of document.querySelectorAll('.life-page input[type="date"]')) input.value=L.today();
    $('#lifeMonth').value=viewedMonth;
  }
  async function save(mutator,message,form) {
    if(busy) return false; busy=true;
    const controls=[...form?.querySelectorAll('input,select,button')||[]].map(control=>[control,control.disabled]);
    for(const [control] of controls)control.disabled=true;
    try {const ok=await S.update(mutator);if(ok)status(message);else status(S.error || '저장하지 못했어요.',true);return ok;}
    finally {busy=false;for(const [control,disabled] of controls)control.disabled=disabled;render();}
  }
  const numeric=(f,key)=>f.get(key)===''?null:Number(f.get(key));
  for(const id of ['Goal','Budget','Expense','Nutrition','Targets','Supplement']) {
    $('#life'+id+'Form').addEventListener('submit',async event=>{
      event.preventDefault();const form=event.currentTarget, f=new FormData(form);let mutate;
      if(id==='Goal') mutate=s=>{s.goal=f.get('goal');};
      if(id==='Budget') mutate=s=>{s.budget=numeric(f,'budget');};
      if(id==='Targets') mutate=s=>{for(const k of Object.keys(s.targets))s.targets[k]=numeric(f,k);};
      if(id==='Expense') mutate=s=>{s.expenses.push({id:uid(),day:f.get('day'),name:f.get('name').trim(),amount:numeric(f,'amount'),category:f.get('category')});};
      if(id==='Nutrition') mutate=s=>{s.nutrition.push({id:uid(),day:f.get('day'),name:f.get('name').trim(),...Object.fromEntries(['kcal','protein','carb','fat'].map(k=>[k,numeric(f,k)])),source:'manual'});};
      if(id==='Supplement') mutate=s=>{s.supplements.push({id:uid(),name:f.get('name').trim(),amount:f.get('amount').trim(),days:[]});};
      if(await save(mutate,'저장했어요.',form)) {
        if(['Expense','Nutrition','Supplement'].includes(id)) {form.reset(); const date=form.querySelector('[type="date"]');if(date)date.value=L.today();}
      }
    });
  }
  document.addEventListener('click',async event=>{
    const button=event.target.closest('button');if(!button)return;
    if(button.id==='lifeClaimButton') await save(s=>{
      const today=L.today(); if(s.claims.includes(today)) return;
      if(s.goal==='meal'&&!I.getState().meals.some(r=>r.day===today))throw new Error('먼저 오늘의 식사를 기록해 주세요.');
      if(s.goal==='budget'&&!s.expenses.some(r=>r.day===today))throw new Error('먼저 오늘의 식비를 기록해 주세요.');
      s.claims.push(today);
    },'오늘의 돌봄으로 10잎을 모았어요.');
    if(button.dataset.lifeTheme) await save(s=>{s.theme=button.dataset.lifeTheme;},'부엌 분위기를 바꿨어요.');
    if(button.dataset.supplement) await save(s=>{const r=s.supplements.find(r=>r.id===button.dataset.supplement),day=L.today();if(!r)throw new Error('기록을 다시 확인해 주세요.');r.days=r.days.includes(day)?r.days.filter(d=>d!==day):[...r.days,day];},'오늘 체크를 저장했어요.');
    if(button.dataset.lifeDelete && window.confirm('이 기록을 삭제할까요? 다른 기록은 유지돼요.')) {
      const key=button.dataset.lifeDelete,id=button.dataset.id;
      if(!['expenses','nutrition','supplements'].includes(key)) return;
      if(await save(s=>{undo={key,record:s[key].find(r=>r.id===id)};s[key]=s[key].filter(r=>r.id!==id);},'기록을 삭제했어요.')) {
        $('#lifeStatus').insertAdjacentHTML('beforeend',' <button type="button" id="lifeUndo">되돌리기</button>');
      }
    }
    if(button.id==='lifeUndo'&&undo) {const restoring=undo;if(await save(s=>{if(restoring.record&&!s[restoring.key].some(r=>r.id===restoring.record.id))s[restoring.key].push(restoring.record);},'기록을 복원했어요.'))undo=null;}
    if(button.dataset.photoMode) {
      const product=button.dataset.photoMode==='product'; $('#lifeProductPhotos').hidden=!product;$('#lifeFridgePhoto').hidden=product;
      for(const tab of document.querySelectorAll('[data-photo-mode]'))tab.setAttribute('aria-pressed',String(tab===button));
    }
    if(button.id==='lifeExport') {
      if(S.error) {status(S.error,true);return;}
      const url=URL.createObjectURL(new Blob([JSON.stringify(S.getState(),null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='kitchen-life-'+L.today()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
  });
  $('#lifeMonth').addEventListener('change',event=>{if(/^\d{4}-(0[1-9]|1[0-2])$/.test(event.target.value)){viewedMonth=event.target.value;render();}});
  $('#lifePhotoForm').addEventListener('submit',event=>{event.preventDefault();const f=new FormData(event.currentTarget);window.UMFCore.openAdd(f.get('name').trim(),f.get('kind'));});
  const photoURLs=new Map();
  for(const input of document.querySelectorAll('[data-life-photo]'))input.addEventListener('change',async()=>{
    const key=input.dataset.lifePhoto, file=input.files[0], image=$('[data-life-photo-preview="'+key+'"]');
    if(photoURLs.has(key))URL.revokeObjectURL(photoURLs.get(key));photoURLs.delete(key);image.hidden=true;image.removeAttribute('src');
    if(!file)return;
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>12*1024*1024){input.value='';status('12MB 이하의 JPEG·PNG·WebP 사진을 선택해 주세요.',true);return;}
    const url=URL.createObjectURL(file);photoURLs.set(key,url);image.src=url;
    try {await image.decode();if(photoURLs.get(key)===url){image.hidden=false;status('사진을 불러왔어요. 내용을 직접 확인해 입력해 주세요.');}}
    catch(_){if(photoURLs.get(key)===url){URL.revokeObjectURL(url);photoURLs.delete(key);input.value='';image.removeAttribute('src');status('사진을 열지 못했어요. 다른 사진을 선택해 주세요.',true);}}
  });
  window.addEventListener('pagehide',()=>{for(const url of photoURLs.values())URL.revokeObjectURL(url);});
  window.addEventListener('umf:navigation',event=>{
    for(const button of document.querySelectorAll('.life-tools button')) {const active=button.dataset.kitchenPage===event.detail.page;button.classList.toggle('active',active);if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');}
  });
  window.addEventListener('umf:daychange',render);window.addEventListener('focus',render);
  S.subscribe(render);I.subscribe(render);populate();render();I.ready?.then(render);
})();
