/* Original Han-kki Kitchen scene, connected to the existing inventory and recipe stores. */
(() => {
  'use strict';
  const S = window.UMFStore, D = window.UMFDomain, R = window.UMFRecipes;
  const K = window.UMFKitchenState, A = window.UMFKitchenArt;
  const scene = document.querySelector('#umfKitchenScene');
  const hero = document.querySelector('#umfKitchenHero');
  if (!S || !D || !R || !K || !A || !scene) return;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const zones = Object.freeze({
    top: '냉장실 · 윗칸', middle: '냉장실 · 채소칸', bottom: '냉장실 · 밀폐 보관칸',
    'freezer-top': '냉동실 · 윗칸', 'freezer-middle': '냉동실 · 가운데 칸', 'freezer-bottom': '냉동실 · 아랫칸', pantry: '실온 · 양념 선반'
  });
  const compartments = {
    freezer: { label: '냉동실', icon: 'snowflake', english: 'FROZEN', zones: ['freezer-top', 'freezer-middle', 'freezer-bottom'] },
    fridge: { label: '냉장실', icon: 'leaf', english: 'FRESH', zones: ['top', 'middle', 'bottom'] }
  };
  const foods = Object.freeze({
    '계란': 'egg', '우유': 'milk', '두부': 'tofu', '닭가슴살': 'chicken', '닭고기': 'chicken', '양파': 'onion',
    '대파': 'scallion', '쪽파': 'scallion', '당근': 'carrot', '브로콜리': 'broccoli', '김치': 'kimchi',
    '밥/즉석밥': 'rice', '밥': 'rice', '쌀': 'rice', '토마토': 'tomato', '버섯': 'mushroom', '감자': 'potato',
    '애호박': 'zucchini', '식용유': 'oil', '올리브유': 'oil', '간장': 'soy', '참치캔': 'tuna', '참치': 'tuna',
    '마늘': 'garlic', '다진마늘': 'garlic', '소금': 'salt'
  });
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const foodIdFor = name => { const key = D.canonical(name); return own(foods, key) ? foods[key] : 'ingredient'; };
  const compartmentFor = zone => zone === 'pantry' ? 'pantry' : zone.startsWith('freezer-') ? 'freezer' : 'fridge';
  const zoneFor = item => { const value = K.zoneFor(item); return own(zones, value) ? value : 'middle'; };
  const text = (parent, selector, value) => { const node = parent?.querySelector(selector); if (node && node.textContent !== String(value)) node.textContent = value; };
  const itemButtons = new Map();
  let initialized = false, organizing = false, movingId = null, draggedId = null, moveBusy = false, organizeBusy = false;
  let interaction = 0, destroyed = false, lastHeroName = null, localError = '';
  const doorBusy = { freezer: false, fridge: false };

  function shelfMarkup(zone) {
    const label = zones[zone].split(' · ')[1];
    return '<div class="shelf" data-zone="' + zone + '"><span class="shelf-name">' + label + '</span>' +
      '<button type="button" class="shelf-name shelf-target" data-action="move-zone" data-zone="' + zone + '" aria-label="' + zones[zone] + '으로 옮기기" hidden>' + label + ' <span aria-hidden="true">＋</span></button>' +
      '<button type="button" class="shelf-more" data-action="show-zone" data-zone="' + zone + '" hidden></button>' +
      '<span class="shelf-empty">차곡차곡 담아주세요</span></div>';
  }
  function mountScene() {
    const inside = Object.entries(compartments).map(([key, c]) =>
      '<section class="fridge-inside compartment-' + key + '" id="inside-' + key + '" data-compartment="' + key + '" aria-label="' + c.label + ' 안쪽" aria-hidden="true" tabindex="-1" inert>' +
      '<i class="fridge-light" aria-hidden="true"></i><div class="compartment-head">' + A.icon(c.icon) + '<strong>' + c.label + '</strong><small>0개</small></div>' + c.zones.map(shelfMarkup).join('') + '</section>'
    ).join('');
    const doors = Object.entries(compartments).map(([key, c]) =>
      '<div class="fridge-door door-' + key + '" role="button" tabindex="0" aria-label="' + c.label + ' 문 열기" aria-expanded="false" aria-controls="inside-' + key + '" data-action="toggle-fridge" data-compartment="' + key + '">' +
      '<div class="door-front"><div class="door-compartment-label">' + A.icon(c.icon) + '<strong>' + c.label + '</strong><small>' + c.english + '</small></div><i class="door-handle" aria-hidden="true"></i>' +
      (key === 'freezer' ? '<div class="ice-magnet">' + A.icon('snowflake') + '</div><div class="freezer-scribble">시원하게<br>차곡차곡</div><span class="door-flower" aria-hidden="true">✿</span>' : '<div class="magnet-carrot">' + A.foodArt('carrot') + '</div><div class="door-note">잘 먹고,<br>잘 지내요.<small>A GOOD LITTLE DAY</small></div><span class="fridge-brand">little kitchen</span>') +
      '</div><div class="door-back" aria-hidden="true"><span></span><span></span><span></span></div></div>'
    ).join('');
    const controls = Object.entries(compartments).map(([key, c]) =>
      '<button type="button" class="compartment-toggle toggle-' + key + '" data-action="toggle-fridge" data-compartment="' + key + '" aria-expanded="false" aria-controls="inside-' + key + '" aria-label="' + c.label + ' 문 열기">' + A.icon(c.icon) + '<span class="toggle-label">' + c.label + ' 열기</span><small>0</small></button>'
    ).join('');
    scene.innerHTML = '<div class="kitchen-scene"><div class="scene-top"><div class="scene-label">' + A.icon('fridge') + '<strong>나의 냉장고</strong><small class="muted" data-kitchen-count>0개</small></div>' +
      '<button type="button" class="btn btn-small btn-line" data-action="organize" aria-pressed="false" aria-controls="umfKitchenArrangeHelp"><span class="organize-icon">' + A.icon('sparkles') + '</span><span class="organize-label">자리 정리</span></button></div>' +
      '<div class="organize-banner" hidden><span>재료를 누른 뒤, 옮길 칸을 눌러주세요.</span></div>' +
      '<div class="fridge-stage side-by-side"><div class="fridge-body side-by-side-body">' + inside + '</div><div class="fridge-feet" aria-hidden="true"></div>' + doors + '</div>' +
      '<div class="fridge-controls" aria-label="냉장고 문 열고 닫기">' + controls + '</div><div class="scene-footer"><span class="scene-hint"></span></div></div>' +
      '<div class="drag-note kitchen-arrange-tools" hidden><p id="umfKitchenArrangeHelp">끌어서 옮기거나, 재료 → 칸 순서로 눌러주세요.</p><div class="kitchen-zone-controls" role="group" aria-label="선택한 재료를 옮길 보관 위치">' +
      Object.entries(zones).map(([zone, label]) => '<button type="button" class="btn btn-small btn-line" data-action="move-zone" data-zone="' + zone + '">' + label + '</button>').join('') +
      '</div><p class="tiny">위치를 옮겨도 수량과 소비기한은 바뀌지 않아요.</p></div>' +
      '<section class="kitchen-pantry" aria-label="실온 양념 선반" hidden>' + shelfMarkup('pantry') + '</section>' +
      '<div class="kitchen-inventory-link"><button type="button" class="btn btn-ghost" data-action="navigate" data-page="inventory">전체 재고 보기 ' + A.icon('chevron') + '</button><button type="button" class="btn btn-ghost" data-action="add-food">' + A.icon('plus') + '재료 넣기</button></div>' +
      '<p class="tiny kitchen-live" id="umfKitchenLive" role="status" aria-live="polite" aria-atomic="true"></p>';
  }
  function announce(message) { text(scene, '#umfKitchenLive', message); }
  function renderError() {
    const node = document.querySelector('#umfKitchenError');
    if (node) { node.textContent = localError || K.error || ''; node.hidden = !node.textContent; }
  }
  function itemStatus(item) {
    const d = D.daysLeft(item.expiry), quantity = String(item.quantity || '').trim();
    const empty = D.parseQuantity(quantity).empty;
    const expiry = d === null ? '기한 미입력' : d < 0 ? '소비기한 ' + Math.abs(d) + '일 지남' : d === 0 ? '오늘까지' : d + '일 남음';
    return { d, empty, quantity: quantity || '수량 미입력', label: (empty ? '소진 · ' : '') + expiry };
  }
  function openZone(zone, doors = K.getState().doors) { const compartment = compartmentFor(zone); return compartment === 'pantry' || !!doors[compartment]; }
  function foodButton(item, zone, doors) {
    let button = itemButtons.get(item.id);
    if (!button) {
      button = document.createElement('button'); button.type = 'button'; button.className = 'fridge-food';
      button.dataset.action = 'fridge-food'; button.dataset.lot = item.id; itemButtons.set(item.id, button);
    }
    const status = itemStatus(item), signature = JSON.stringify([item.name, status.quantity, status.label, status.d, status.empty]);
    if (button.dataset.signature !== signature) {
      button.dataset.signature = signature;
      button.innerHTML = A.foodArt(foodIdFor(item.name)) + '<span class="quantity-mini">' + esc(status.quantity) + '</span><span class="food-label">' + esc(item.name) + '</span>' +
        (status.d !== null && status.d <= 2 ? '<i class="expiry-dot" aria-hidden="true"></i>' : '');
    }
    const label = item.name + ', ' + status.quantity + ', ' + zones[zone] + ', ' + status.label;
    button.setAttribute('aria-label', label + (organizing ? ', 옮길 재료 선택' : ', 재료 수정'));
    button.title = label; button.classList.toggle('expired', status.d !== null && status.d < 0);
    button.classList.toggle('exhausted', status.empty); button.classList.toggle('selected', movingId === item.id);
    button.disabled = !initialized || moveBusy || !openZone(zone, doors);
    button.draggable = !button.disabled;
    if (organizing) { button.setAttribute('aria-pressed', String(movingId === item.id)); button.setAttribute('aria-describedby', 'umfKitchenArrangeHelp'); }
    else { button.removeAttribute('aria-pressed'); button.removeAttribute('aria-describedby'); }
    return button;
  }
  function renderScene() {
    const items = S.getState().items, state = K.getState(), doors = state.doors, focused = document.activeElement;
    const focusedInside = scene.contains(focused) ? focused.closest('.fridge-inside') : null;
    const placements = new Map(items.map(item => [item.id, zoneFor(item)]));
    if (movingId && (!placements.has(movingId) || !openZone(placements.get(movingId), doors))) { movingId = null; interaction++; }
    const anyOpen = doors.freezer || doors.fridge;
    const stage = scene.querySelector('.fridge-stage');
    stage.classList.toggle('open', !!anyOpen); stage.classList.toggle('freezer-open', !!doors.freezer); stage.classList.toggle('fridge-open', !!doors.fridge);
    text(scene, '[data-kitchen-count]', items.filter(item => placements.get(item.id) !== 'pantry').length + '개');
    for (const [key, compartment] of Object.entries(compartments)) {
      const inside = scene.querySelector('#inside-' + key), count = items.filter(item => compartmentFor(placements.get(item.id)) === key).length;
      inside.toggleAttribute('inert', !doors[key]); inside.setAttribute('aria-hidden', String(!doors[key]));
      text(inside, '.compartment-head small', count + '개');
      for (const control of scene.querySelectorAll('[data-action="toggle-fridge"][data-compartment="' + key + '"]')) {
        control.setAttribute('aria-expanded', String(!!doors[key])); control.setAttribute('aria-label', compartment.label + ' 문 ' + (doors[key] ? '닫기' : '열기'));
        const busy = !initialized || doorBusy[key] || organizeBusy || moveBusy;
        control.setAttribute('aria-disabled', String(busy));
        if (control.classList.contains('fridge-door')) control.tabIndex = doors[key] || busy ? -1 : 0;
        else { control.disabled = busy; control.classList.toggle('is-open', !!doors[key]); text(control, '.toggle-label', compartment.label + ' ' + (doors[key] ? '닫기' : '열기')); text(control, 'small', count); }
      }
    }
    for (const zone of Object.keys(zones)) {
      const shelf = scene.querySelector('.shelf[data-zone="' + zone + '"]'), lots = items.filter(item => placements.get(item.id) === zone);
      const more = shelf.querySelector('.shelf-more'), label = shelf.querySelector('span.shelf-name'), target = shelf.querySelector('.shelf-target');
      const wanted = lots.slice(0, 2).map(item => foodButton(item, zone, doors));
      for (const button of shelf.querySelectorAll('.fridge-food')) if (!wanted.includes(button)) button.remove();
      let anchor = more;
      for (let n = wanted.length - 1; n >= 0; n--) { if (wanted[n].nextElementSibling !== anchor) shelf.insertBefore(wanted[n], anchor); anchor = wanted[n]; }
      label.hidden = organizing; target.hidden = !organizing; target.disabled = !initialized || !movingId || moveBusy || !openZone(zone, doors);
      shelf.classList.toggle('drop-mode', organizing); more.hidden = lots.length <= 2; more.textContent = '+' + Math.max(0, lots.length - 2);
      more.disabled = !openZone(zone, doors); more.setAttribute('aria-label', zones[zone] + ' 재료 ' + lots.length + '개 전체 재고에서 보기');
      shelf.querySelector('.shelf-empty').hidden = lots.length > 0;
    }
    for (const id of itemButtons.keys()) if (!placements.has(id)) itemButtons.delete(id);
    const organize = scene.querySelector('[data-action="organize"]');
    organize.disabled = !initialized || organizeBusy || moveBusy;
    organize.setAttribute('aria-pressed', String(organizing));
    text(organize, '.organize-label', organizing ? '정리 마치기' : '자리 정리');
    if (organize.dataset.mode !== String(organizing)) { organize.dataset.mode = String(organizing); organize.querySelector('.organize-icon').innerHTML = A.icon(organizing ? 'check' : 'sparkles'); }
    const moving = items.find(item => item.id === movingId);
    scene.querySelector('.organize-banner').hidden = !organizing;
    text(scene, '.organize-banner span', moving ? moving.name + ' · 옮길 칸을 눌러주세요' : '재료를 누른 뒤, 옮길 칸을 눌러주세요');
    scene.querySelector('.kitchen-arrange-tools').hidden = !organizing;
    scene.querySelector('.kitchen-pantry').hidden = !organizing && !items.some(item => placements.get(item.id) === 'pantry');
    for (const button of scene.querySelectorAll('.kitchen-zone-controls [data-zone]')) {
      button.disabled = !initialized || !movingId || moveBusy || !openZone(button.dataset.zone, doors);
      button.setAttribute('aria-label', (moving ? moving.name + '을 ' : '') + zones[button.dataset.zone] + '으로 옮기기');
    }
    const hint = organizing ? '재료를 누르고, 옮길 칸을 골라주세요' : anyOpen ? '재료를 누르면 수량과 기한을 볼 수 있어요' : '왼쪽은 냉동실, 오른쪽은 냉장실이에요';
    const hintNode = scene.querySelector('.scene-hint');
    if (hintNode.dataset.message !== hint) { hintNode.dataset.message = hint; hintNode.innerHTML = A.icon(anyOpen ? 'leaf' : 'heart') + esc(hint); }
    if (focusedInside && !doors[focusedInside.dataset.compartment] && (document.activeElement === focused || document.activeElement === document.body)) scene.querySelector('.toggle-' + focusedInside.dataset.compartment)?.focus();
    else if (focused?.classList?.contains('fridge-food') && !focused.isConnected && document.activeElement === document.body) scene.querySelector('[data-action="organize"]')?.focus();
    renderError();
  }
  function mountHero() {
    if (!hero) return;
    hero.classList.add('panel', 'today-panel'); hero.setAttribute('aria-label', '오늘의 추천 메뉴');
    hero.innerHTML = '<div class="panel-title"><div><span class="eyebrow">TODAY\'S LITTLE MEAL</span><h3>오늘의 한 끼</h3></div><button type="button" class="icon-btn" data-action="shuffle" aria-label="다른 추천 메뉴 보기">' + A.icon('shuffle') + '</button></div>' +
      '<div class="today-dish"></div><h2 class="recipe-title"></h2><p class="recipe-sub"></p><div class="row"><span class="pill kitchen-ready"></span><span class="tiny kitchen-recipe-time"></span></div>' +
      '<div class="meal-metrics"><div class="metric"><div class="metric-label">보유 재료</div><strong data-hero-owned>0<small> 가지</small></strong></div><div class="metric"><div class="metric-label">더 필요한 재료</div><strong data-hero-missing>0<small> 가지</small></strong></div><div class="metric"><div class="metric-label">먼저 쓸 재료</div><strong data-hero-urgent>0<small> 개</small></strong></div></div>' +
      '<p class="tiny kitchen-hero-owned"></p><p class="tiny kitchen-hero-note"></p><div class="primary-action"><button type="button" class="btn btn-primary full" data-action="recipe">선택한 레시피 보기 ' + A.icon('arrow') + '</button></div>' +
      '<button type="button" class="more-recipe" data-action="navigate" data-page="recipes">다른 메뉴도 둘러보기 ' + A.icon('chevron') + '</button>';
  }
  function renderHero() {
    if (!hero) return;
    const selected = R.getSelected(), recipe = selected?.recipe;
    const picture = hero.querySelector('.today-dish');
    if (lastHeroName !== (recipe?.name || '')) {
      lastHeroName = recipe?.name || '';
      picture.innerHTML = recipe ? A.dishArt({ id: recipe.name, ingredients: [...recipe.f, ...recipe.p, ...recipe.s].map(name => ({ foodId: foodIdFor(name) })), illustration: recipe.name.includes('샐러드') ? 'salad' : recipe.name.endsWith('국') ? 'soup' : 'meal' }) : A.icon('leaf');
      picture.setAttribute('aria-label', recipe ? recipe.name + ' 재료를 표현한 일러스트' : ''); picture.setAttribute('role', 'img');
    }
    text(hero, '.recipe-title', recipe?.name || '선택할 메뉴가 없어요');
    text(hero, '.recipe-sub', recipe?.desc || '검색어를 지우거나 다른 필터에서 메뉴를 골라주세요.');
    text(hero, '.kitchen-recipe-time', recipe ? recipe.time + ' · 1인분 조리 예시' : '');
    const readyLabel = hero.querySelector('.kitchen-ready');
    readyLabel.classList.toggle('green', !!selected?.available);
    const status = !recipe ? '메뉴 선택 필요' : selected.available ? '재료 있음 · 분량 확인' : '재료 ' + selected.missing.length + '가지 더';
    if (readyLabel.dataset.status !== status) { readyLabel.dataset.status = status; readyLabel.innerHTML = A.icon(selected?.available ? 'check' : 'basket') + esc(status); }
    for (const [key, count, unit] of [['owned', selected?.matchedCount, '가지'], ['missing', selected?.missing.length, '가지'], ['urgent', selected?.urgentCount, '개']]) {
      const node = hero.querySelector('[data-hero-' + key + ']'), value = recipe ? String(count || 0) : '—';
      if (node.dataset.count !== value) { node.dataset.count = value; node.innerHTML = value + '<small> ' + unit + '</small>'; }
    }
    const owned = recipe ? [...recipe.f, ...recipe.s, ...recipe.p].filter(name => !selected.missing.some(missing => D.canonical(missing.name) === D.canonical(name))) : [];
    text(hero, '.kitchen-hero-owned', recipe ? owned.length ? '보유 재료 · ' + owned.join(' · ') : '아직 이 메뉴에 필요한 재료가 등록되지 않았어요.' : '');
    text(hero, '.kitchen-hero-note', recipe ? (selected.urgentCount ? '기한이 가까운 재료 ' + selected.urgentCount + '개를 먼저 확인해 주세요. ' : '') + '조리 전 실제 분량과 재료 상태를 확인해 주세요.' : '');
    hero.querySelector('[data-action="recipe"]').disabled = !recipe;
    const shuffle = document.querySelector('#umfShuffleBtn');
    hero.querySelector('[data-action="shuffle"]').disabled = shuffle ? shuffle.disabled : R.catalog.length < 2;
    hero.dataset.recipe = recipe?.name || '';
  }
  function renderSummary() {
    const summary = document.querySelector('#umfKitchenSummary'); if (!summary) return;
    const items = S.getState().items, available = R.getRanked().filter(entry => entry.available).length;
    summary.textContent = '등록한 재료 ' + items.length + '개 · 재료를 갖춘 메뉴 ' + available + '개';
  }
  function render() { if (!destroyed) { renderScene(); renderHero(); renderSummary(); } }
  function navigate(view) { interaction++; window.UMFKitchenNav?.go(view); }
  async function toggleDoor(key) {
    if (!initialized || !own(compartments, key) || doorBusy[key] || organizeBusy || moveBusy) return;
    doorBusy[key] = true; renderScene();
    try {
      if (await K.toggleDoor(key)) { localError = ''; announce(compartments[key].label + ' 문을 ' + (K.getState().doors[key] ? '열었어요.' : '닫았어요.')); }
      else localError = K.error || '문 상태를 저장하지 못했어요. 다시 시도해 주세요.';
    } catch (_) { localError = '문 상태를 저장하지 못했어요. 다시 시도해 주세요.'; }
    finally { doorBusy[key] = false; render(); }
  }
  async function toggleOrganize() {
    if (!initialized || moveBusy || organizeBusy) return;
    const token = ++interaction;
    if (organizing) { organizing = false; movingId = null; draggedId = null; renderScene(); announce('자리 정리를 마쳤어요.'); return; }
    organizeBusy = true; renderScene();
    try {
      if (await K.setDoors({ freezer: true, fridge: true })) { localError = ''; if (token === interaction) { organizing = true; movingId = null; announce('옮길 재료를 누른 뒤, 옮길 칸을 골라주세요.'); } }
      else localError = K.error || '문 상태를 저장하지 못해 정리를 시작하지 못했어요.';
    } catch (_) { localError = '자리 정리를 시작하지 못했어요. 다시 시도해 주세요.'; }
    finally { organizeBusy = false; render(); }
  }
  async function arrangeItem(id) {
    if (!initialized || moveBusy || organizeBusy || !S.getState().items.some(item => item.id === id)) return false;
    const token = ++interaction; let selected = false;
    organizeBusy = true; renderScene();
    try {
      if (!(await K.setDoors({ freezer: true, fridge: true }))) { localError = K.error || '자리 정리를 시작하지 못했어요.'; return false; }
      const item = S.getState().items.find(value => value.id === id);
      if (!item || token !== interaction) return false;
      localError = ''; organizing = true; movingId = id; selected = true; navigate('home');
      announce(item.name + ' 선택. 옮길 칸을 골라주세요.'); return true;
    } catch (_) { localError = '자리 정리를 시작하지 못했어요. 다시 시도해 주세요.'; return false; }
    finally {
      organizeBusy = false; render();
      if (selected) {
        const target = scene.querySelector('.kitchen-zone-controls button:not(:disabled)');
        target?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' }); target?.focus();
      }
    }
  }
  function selectItem(id) {
    if (!initialized || moveBusy) return;
    const item = S.getState().items.find(value => value.id === id);
    if (!item || !openZone(zoneFor(item))) return;
    if (!organizing) { window.UMFCore?.openEdit(id); return; }
    interaction++; movingId = movingId === id ? null : id; renderScene();
    announce(movingId ? item.name + ' 선택. 옮길 칸을 골라주세요.' : '재료 선택을 취소했어요.');
  }
  async function moveItem(id, zone) {
    if (!initialized || moveBusy || !own(zones, zone) || !openZone(zone)) return;
    const item = S.getState().items.find(value => value.id === id);
    if (!item) { movingId = null; announce('먼저 옮길 재료를 골라주세요.'); renderScene(); return; }
    const token = interaction, focused = document.activeElement, ownedFocus = scene.contains(document.activeElement);
    moveBusy = true; renderScene();
    try {
      if (await K.setZone(id, zone)) {
        localError = '';
        if (token === interaction) { movingId = null; announce(item.name + '을 ' + zones[zone] + '으로 옮겼어요.'); }
      } else localError = K.error || '재료 위치를 저장하지 못했어요. 다시 시도해 주세요.';
    } catch (_) { localError = '재료 위치를 저장하지 못했어요. 다시 시도해 주세요.'; }
    finally {
      moveBusy = false; draggedId = null; render();
      if (token === interaction && ownedFocus && (document.activeElement === focused || document.activeElement === document.body)) {
        const moved = itemButtons.get(id), more = scene.querySelector('.shelf[data-zone="' + zone + '"] .shelf-more');
        if (moved?.isConnected && !moved.disabled) moved.focus();
        else if (more && !more.hidden && !more.disabled) more.focus();
        else scene.querySelector('[data-action="organize"]')?.focus();
      }
    }
  }
  function onSceneClick(event) {
    const target = event.target.closest('[data-action]');
    if (!target || !scene.contains(target) || target.disabled || target.getAttribute('aria-disabled') === 'true') return;
    if (target.dataset.action === 'toggle-fridge') toggleDoor(target.dataset.compartment);
    else if (target.dataset.action === 'organize') toggleOrganize();
    else if (target.dataset.action === 'fridge-food') selectItem(target.dataset.lot);
    else if (target.dataset.action === 'move-zone' && organizing) moveItem(movingId, target.dataset.zone);
    else if (target.dataset.action === 'show-zone') navigate('inventory');
    else if (target.dataset.action === 'navigate') navigate(target.dataset.page);
    else if (target.dataset.action === 'add-food') window.UMFCore?.openAdd();
  }
  function onHeroClick(event) {
    const target = event.target.closest('[data-action]'); if (!target || !hero.contains(target) || target.disabled) return;
    if (target.dataset.action === 'shuffle') {
      const shuffle = document.querySelector('#umfShuffleBtn');
      if (shuffle) shuffle.click();
      else { const entries = R.getRanked(), index = entries.findIndex(entry => entry.recipe.name === R.getSelected()?.recipe.name); for (let n = 1; n <= entries.length; n++) if (R.select(entries[(index + n) % entries.length].recipe.name)) break; }
    } else if (target.dataset.action === 'recipe') { const selected = R.getSelected(); if (selected) { navigate('recipes'); R.select(selected.recipe.name, { openDetail: true }); document.querySelector('#umfRecipeDetail')?.scrollIntoView?.({ block: 'start', behavior: 'smooth' }); } }
    else if (target.dataset.action === 'navigate') navigate('recipes');
  }
  function onKeyDown(event) {
    const target = event.target.closest('.fridge-door[role="button"]');
    if (target && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); if (!event.repeat) target.click(); }
    else if (event.key === 'Escape' && organizing) { interaction++; movingId = null; draggedId = null; renderScene(); announce('옮길 재료 선택을 취소했어요.'); }
  }
  function onNavigation(event) {
    interaction++;
    if (event.detail?.page !== 'home') { organizing = false; movingId = null; draggedId = null; renderScene(); }
  }
  function dragTarget(event) { const target = event.target.closest('.shelf[data-zone],.kitchen-zone-controls [data-zone]'); return target && scene.contains(target) ? target : null; }
  function onDragStart(event) {
    const button = event.target.closest('.fridge-food');
    if (!button || button.disabled || moveBusy || !initialized) { event.preventDefault(); return; }
    const item = S.getState().items.find(value => value.id === button.dataset.lot);
    if (!item || !openZone(zoneFor(item))) { event.preventDefault(); return; }
    interaction++; organizing = true; movingId = draggedId = item.id;
    if (event.dataTransfer) { event.dataTransfer.setData('text/plain', item.id); event.dataTransfer.effectAllowed = 'move'; }
    renderScene();
  }
  function onDragOver(event) { const target = dragTarget(event); if (target && draggedId && !moveBusy && openZone(target.dataset.zone)) { event.preventDefault(); if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'; target.classList.add('is-over'); } }
  function onDragLeave(event) { const target = dragTarget(event); if (target && !target.contains(event.relatedTarget)) target.classList.remove('is-over'); }
  function clearDrag() { for (const target of scene.querySelectorAll('.is-over')) target.classList.remove('is-over'); draggedId = null; }
  function onDrop(event) {
    const target = dragTarget(event); if (!target) return;
    event.preventDefault(); target.classList.remove('is-over');
    const id = event.dataTransfer?.getData('text/plain') || draggedId;
    if (id && id === draggedId && openZone(target.dataset.zone)) moveItem(id, target.dataset.zone);
  }
  mountScene(); mountHero();
  const handlers = { click: onSceneClick, keydown: onKeyDown, dragstart: onDragStart, dragover: onDragOver, dragleave: onDragLeave, dragend: clearDrag, drop: onDrop };
  for (const [event, handler] of Object.entries(handlers)) scene.addEventListener(event, handler);
  hero?.addEventListener('click', onHeroClick);
  const offStore = S.subscribe(render), offKitchen = K.subscribe(render);
  window.addEventListener('umf:selectionchange', renderHero); window.addEventListener('umf:daychange', render); window.addEventListener('umf:kitchenerror', renderError);
  window.addEventListener('umf:navigation', onNavigation);
  const ready = Promise.all([S.ready, K.ready]).then(() => { initialized = true; render(); return true; }).catch(() => { localError = '부엌의 저장 상태를 읽지 못했어요.'; renderError(); return false; });
  window.UMFKitchen = {
    ready, render, navigate, arrangeItem, foodIdFor, itemStatus, zones,
    getOrganizing: () => organizing, getMovingId: () => movingId,
    destroy() { destroyed = true; offStore?.(); offKitchen?.(); for (const [event, handler] of Object.entries(handlers)) scene.removeEventListener(event, handler); hero?.removeEventListener('click', onHeroClick); window.removeEventListener('umf:selectionchange', renderHero); window.removeEventListener('umf:daychange', render); window.removeEventListener('umf:kitchenerror', renderError); window.removeEventListener('umf:navigation', onNavigation); }
  };
  render();
})();
