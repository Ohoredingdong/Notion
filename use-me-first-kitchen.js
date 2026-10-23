/* Original Han-kki Kitchen scene, connected to the existing inventory and recipe stores. */
(() => {
  'use strict';
  const S = window.UMFStore, D = window.UMFDomain, R = window.UMFRecipes;
  const K = window.UMFKitchenState, A = window.UMFKitchenArt;
  const scene = document.querySelector('#umfKitchenScene');
  const hero = document.querySelector('#umfKitchenHero');
  if (!S || !D || !R || !K || !A || !scene) return;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const objectPhrase = name => { const word = String(name), last = word.charCodeAt(word.length - 1); return word + (last >= 0xac00 && last <= 0xd7a3 && (last - 0xac00) % 28 ? '을' : '를'); };
  const zones = Object.freeze({
    top: '냉장실 왼쪽 · 윗칸', middle: '냉장실 왼쪽 · 채소칸', bottom: '냉장실 왼쪽 · 밀폐 보관칸',
    'fridge-right-top': '냉장실 오른쪽 · 윗칸', 'fridge-right-middle': '냉장실 오른쪽 · 가운데 칸', 'fridge-right-bottom': '냉장실 오른쪽 · 아랫칸',
    'freezer-top': '냉동실 왼쪽 · 윗칸', 'freezer-middle': '냉동실 왼쪽 · 가운데 칸', 'freezer-bottom': '냉동실 왼쪽 · 아랫칸',
    'freezer-right-top': '냉동실 오른쪽 · 윗칸', 'freezer-right-middle': '냉동실 오른쪽 · 가운데 칸', 'freezer-right-bottom': '냉동실 오른쪽 · 아랫칸', pantry: '실온 · 양념 선반'
  });
  const compartments = {
    fridge: { label: '위 왼쪽 냉장실', shortLabel: '냉장 왼쪽', icon: 'leaf', side: 'left', type: 'fresh', zones: ['top', 'middle', 'bottom'] },
    'fridge-right': { label: '위 오른쪽 냉장실', shortLabel: '냉장 오른쪽', icon: 'leaf', side: 'right', type: 'fresh', zones: ['fridge-right-top', 'fridge-right-middle', 'fridge-right-bottom'] },
    freezer: { label: '아래 왼쪽 냉동실', shortLabel: '냉동 왼쪽', icon: 'snowflake', side: 'left', type: 'frozen', zones: ['freezer-top', 'freezer-middle', 'freezer-bottom'] },
    'freezer-right': { label: '아래 오른쪽 냉동실', shortLabel: '냉동 오른쪽', icon: 'snowflake', side: 'right', type: 'frozen', zones: ['freezer-right-top', 'freezer-right-middle', 'freezer-right-bottom'] }
  };
  const foods = Object.freeze({
    '계란': 'egg', '우유': 'milk', '두부': 'tofu', '닭가슴살': 'chicken', '닭고기': 'chicken', '양파': 'onion',
    '대파': 'scallion', '쪽파': 'scallion', '당근': 'carrot', '브로콜리': 'broccoli', '김치': 'kimchi',
    '밥/즉석밥': 'rice', '밥': 'rice', '쌀': 'rice', '토마토': 'tomato', '버섯': 'mushroom', '감자': 'potato',
    '애호박': 'zucchini', '식용유': 'oil', '올리브유': 'oil', '간장': 'soy', '참치캔': 'tuna', '참치': 'tuna',
    '마늘': 'garlic', '다진마늘': 'garlic', '소금': 'salt'
  });
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const foodIdFor = name => { const key = D.canonical(name); return A.foodIdForName?.(name) || (own(foods, key) ? foods[key] : 'ingredient'); };
  const seasoningFoodId = name => {
    const key = String(name || '').normalize('NFKC').trim();
    if (/간장/.test(key)) return 'soy';
    if (/식용유|올리브유|참기름|식초/.test(key)) return 'oil';
    if (/소금|설탕|후추/.test(key)) return 'salt';
    if (/다진마늘|마늘/.test(key)) return 'garlic';
    if (/고춧가루|고추장/.test(key)) return 'pepper';
    if (/케첩/.test(key)) return 'tomato';
    if (/된장/.test(key)) return 'soy';
    return A.foodIdForName?.(key) || 'ingredient';
  };
  const compartmentFor = zone => zone === 'pantry' ? 'pantry' : zone.startsWith('freezer-right-') ? 'freezer-right'
    : zone.startsWith('freezer-') ? 'freezer' : zone.startsWith('fridge-right-') ? 'fridge-right' : 'fridge';
  const zoneFor = item => { const value = K.zoneFor(item); return own(zones, value) ? value : 'middle'; };
  const text = (parent, selector, value) => { const node = parent?.querySelector(selector); if (node && node.textContent !== String(value)) node.textContent = value; };
  const itemButtons = new Map();
  const displayedPositions = new Map();
  const handledPointerMoves = new WeakSet();
  let initialized = false, organizing = false, movingId = null, draggedId = null, moveBusy = false, organizeBusy = false;
  let interaction = 0, destroyed = false, lastHeroName = null, localError = '';
  let pointerSession = null, htmlDrag = null, suppressClickUntil = 0, ghostSequence = 0;
  let seasoningPointerSession = null;
  const SEASONING_LAYOUT_KEY = 'umf-seasoning-layout-v3';
  const doorBusy = Object.fromEntries(Object.keys(compartments).map(key => [key, false]));
  const unit = value => Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  function readSeasoningLayout() {
    try {
      const parsed = JSON.parse(window.localStorage?.getItem(SEASONING_LAYOUT_KEY) || '{}');
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
      return Object.fromEntries(Object.entries(parsed).filter(([name, p]) =>
        typeof name === 'string' && p && Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.z)
      ).map(([name, p]) => [name, { x: clamp(p.x, .07, .93), y: clamp(p.y, .06, .94), z: p.z }]));
    } catch (_) { return {}; }
  }
  let seasoningLayout = readSeasoningLayout();
  function writeSeasoningLayout() {
    try { window.localStorage?.setItem(SEASONING_LAYOUT_KEY, JSON.stringify(seasoningLayout)); return true; }
    catch (_) { return false; }
  }
  function defaultSeasoningPosition(index) {
    const columns = 4, col = index % columns, row = Math.floor(index / columns);
    const rows = Math.max(1, Math.ceil(S.getState().season.length / columns));
    const x = .14 + (col / (columns - 1)) * .72;
    const y = clamp((row + .5) / rows, .06, .94);
    return { x: clamp(x, .08, .92), y, z: index + 1 };
  }
  function seasoningPosition(name, index) { return seasoningLayout[name] || defaultSeasoningPosition(index); }
  function placeSeasoning(button, position) {
    button.style.left = position.x * 100 + '%';
    button.style.top = position.y * 100 + '%';
    button.style.zIndex = String(Math.max(1, position.z || 1));
    button.dataset.x = String(position.x); button.dataset.y = String(position.y); button.dataset.z = String(position.z || 1);
  }
  function defaultPosition(id, index, count = 4) {
    if (document.body.dataset.kitchenMode === 'widget') {
      const columns = Math.min(2, Math.max(1, count)), rows = Math.max(1, Math.ceil(count / columns));
      return { x: columns > 1 ? (index % columns) / (columns - 1) : .5, y: rows > 1 ? Math.floor(index / columns) / (rows - 1) : .5, z: 0 };
    }
    const row = Math.floor(index % 9 / 3), column = index % 3;
    const seed = [...String(id)].reduce((value, letter) => (value * 31 + letter.charCodeAt(0)) >>> 0, 17);
    const offset = index < 9 ? 0 : ((seed % 11) - 5) * .006;
    return { x: unit((column + (row % 2) * .18) / 2.2 + offset), y: unit(.76 - row * .33 - offset), z: 0 };
  }
  function normalizedPoint(rect, size, point, anchor = { x: .5, y: .5 }) {
    const width = rect.width - size.width, height = rect.height - size.height;
    return { x: width > 0 ? unit((point.x - rect.left - size.width * anchor.x) / width) : 0, y: height > 0 ? unit((point.y - rect.top - size.height * anchor.y) / height) : 0 };
  }
  function positionFor(id) { return K.positionFor?.(id) || displayedPositions.get(id) || { x: .5, y: .5, z: 0 }; }
  function placementFingerprint(id) {
    const item = S.getState().items.find(value => value.id === id);
    return item ? JSON.stringify([item, zoneFor(item), K.positionFor?.(id) || null, D.daysLeft(item.expiry)]) : null;
  }
  function placeButton(button, position, layer) {
    button.dataset.x = String(position.x); button.dataset.y = String(position.y); button.dataset.z = String(position.z);
    button.style.setProperty('--food-x', String(position.x)); button.style.setProperty('--food-y', String(position.y)); button.style.setProperty('--food-z', String(layer));
    button.style.position = 'absolute'; button.style.left = position.x * 100 + '%'; button.style.top = position.y * 100 + '%';
    button.style.transform = 'translate(' + (-position.x * 100) + '%, ' + (-position.y * 100) + '%)'; button.style.zIndex = String(layer);
  }

  function shelfMarkup(zone) {
    const label = zones[zone].split(' · ')[1];
    return '<div class="shelf" data-zone="' + zone + '"><span class="shelf-name">' + label + '</span>' +
      '<button type="button" class="shelf-name shelf-target" data-action="move-zone" data-zone="' + zone + '" aria-label="' + zones[zone] + '으로 옮기기" hidden>' + label + ' <span aria-hidden="true">＋</span></button>' +
      '<button type="button" class="shelf-more" data-action="show-zone" data-zone="' + zone + '" hidden></button>' +
      '<div class="shelf-canvas" data-zone="' + zone + '" aria-label="' + zones[zone] + ' 재료 배치"><span class="shelf-empty">차곡차곡 담아주세요</span></div></div>';
  }
  function doorDisplayMarkup(key) {
    if (key === 'fridge') return '<section class="door-display door-display-expiry" aria-label="유통기한 임박 재료"><div class="door-display-head"><strong>먼저 먹어요</strong><small>3일 이내</small></div><div class="door-display-content" data-door-expiry></div><span class="display-footnote">우리 집 재료 메모</span></section>';
    if (key === 'fridge-right') return '<section class="door-display door-display-recipes" aria-label="추천 레시피"><div class="door-display-head"><strong>오늘의 메뉴</strong><small>우리 재료 기준</small></div><div class="door-display-content" data-door-recipes></div><span class="display-footnote">작은 부엌의 한 끼</span></section>';
    return '';
  }
  function renderDoorDisplays() {
    const state = S.getState();
    const expiryNode = scene.querySelector('[data-door-expiry]');
    if (expiryNode) {
      const upcoming = state.items.map(item => ({ item, status: itemStatus(item) })).concat(D.seasoningStock(state).map(item => ({ item, status: itemStatus(item), seasoning: true })))
        .filter(entry => !entry.status.empty && entry.status.d !== null && entry.status.d >= 0 && entry.status.d <= 3)
        .sort((a, b) => a.status.d - b.status.d || a.item.name.localeCompare(b.item.name, 'ko'))
        .slice(0, 3);
      expiryNode.innerHTML = upcoming.length ? upcoming.map(({ item, status, seasoning }) => {
        const badge = status.d === 0 ? '오늘' : status.d === 1 ? '내일' : status.d + '일';
        return '<div class="display-row display-food-row"><span class="display-food-art">' + (seasoning ? A.seasoningArt(item.name) : A.foodArt(foodIdFor(item.name))) + '</span><span class="display-row-copy"><b>' + esc(item.name) + '</b><small>' + esc(seasoning ? '양념' : status.quantity) + '</small></span><em class="display-badge d' + status.d + '">' + badge + '</em></div>';
      }).join('') : '<div class="display-empty">3일 안에 임박한 재료가 없어요.</div>';
    }
    const recipeNode = scene.querySelector('[data-door-recipes]');
    if (recipeNode) {
      const ranked = R.getRanked().slice(0, 2);
      recipeNode.innerHTML = ranked.length ? ranked.map(entry => {
        const recipe = entry.recipe, missing = entry.missing?.length || 0;
        const status = entry.available ? '바로 가능' : '재료 ' + missing + '개 부족';
        return '<div class="display-row display-recipe-row"><span class="display-recipe-art">' + A.dishArt({ id: recipe.name }) + '</span><span class="display-row-copy"><b>' + esc(recipe.name) + '</b><small>' + esc(status) + '</small><span class="display-meta">' + esc(recipe.time) + ' · 영양·원가 미연결</span></span></div>';
      }).join('') : '<div class="display-empty">추천할 메뉴를 준비 중이에요.</div>';
    }
  }
  function mountScene() {
    const inside = Object.entries(compartments).map(([key, c]) =>
      '<section class="fridge-inside compartment-' + key + ' panel-' + c.type + ' panel-' + c.side + '" id="inside-' + key + '" data-compartment="' + key + '" aria-label="' + c.label + ' 안쪽" aria-hidden="true" tabindex="-1" inert>' +
      '<i class="fridge-light" aria-hidden="true"></i><div class="compartment-head">' + A.icon(c.icon) + '<strong>' + c.label + '</strong><small>0개</small></div>' + c.zones.map(shelfMarkup).join('') + '</section>'
    ).join('');
    const doors = Object.entries(compartments).map(([key, c]) =>
      '<div class="fridge-door door-' + key + ' panel-' + c.type + ' panel-' + c.side + '" role="button" tabindex="0" aria-label="' + c.label + ' 문 열기" aria-expanded="false" aria-controls="inside-' + key + '" data-action="toggle-fridge" data-compartment="' + key + '">' +
      '<div class="door-front">' + doorDisplayMarkup(key) + '<i class="door-handle" aria-hidden="true"></i><span class="door-type">' + A.icon(c.icon) + (c.type === 'fresh' ? '냉장' : '냉동') + '</span><span class="fridge-brand">little kitchen</span></div>' +
      '<div class="door-back" aria-hidden="true"><span></span><span></span><span></span></div></div>'
    ).join('');
    const controls = Object.entries(compartments).map(([key, c]) =>
      '<button type="button" class="compartment-toggle toggle-' + key + '" data-action="toggle-fridge" data-compartment="' + key + '" aria-expanded="false" aria-controls="inside-' + key + '" aria-label="' + c.label + ' 문 열기">' + A.icon(c.icon) + '<span class="toggle-label">' + c.shortLabel + ' 열기</span><small>0</small></button>'
    ).join('');
    scene.innerHTML = '<div class="kitchen-scene"><div class="scene-top"><div class="scene-label">' + A.icon('fridge') + '<strong>나의 냉장고</strong><small class="muted" data-kitchen-count>0개</small></div>' +
      '<button type="button" class="btn btn-small btn-line" data-action="organize" aria-pressed="false"><span class="organize-icon">' + A.icon('sparkles') + '</span><span class="organize-label">자리 정리</span></button></div>' +
      '<div class="organize-banner" hidden><span>재료를 누른 뒤, 옮길 칸을 눌러주세요.</span></div>' +
      '<div class="fridge-stage four-door"><div class="fridge-body">' + inside + '</div><div class="fridge-feet" aria-hidden="true"></div>' + doors + '</div>' +
      '<div class="fridge-controls" aria-label="냉장고 문 열고 닫기">' + controls + '</div><div class="scene-footer"><span class="scene-hint"></span></div></div>' +
      '<section class="kitchen-arrange-tools panel" aria-label="재료 자리 정리" hidden><p class="kitchen-selected-material"></p><div class="kitchen-layer-controls"><span>겹친 재료의 앞뒤</span><button type="button" class="btn btn-line" data-action="layer-front">맨 앞으로</button><button type="button" class="btn btn-line" data-action="layer-back">맨 뒤로</button></div><details><summary>칸을 골라 옮기기</summary><div class="kitchen-zone-controls">' + Object.entries(zones).map(([zone, label]) => '<button type="button" class="btn btn-line" data-action="move-zone" data-zone="' + zone + '">' + esc(label) + '</button>').join('') + '</div></details></section>' +
      '<section class="seasoning-rack" aria-label="양념 선반"><div class="seasoning-rack-head"><div><strong>우리 집 양념장</strong><small>양념을 눌러 기한을 관리해요</small></div><button type="button" class="btn btn-small btn-line" data-action="add-seasoning">양념 추가</button></div><div class="seasoning-rack-board"><div class="seasoning-rack-items"></div></div><p class="seasoning-rack-note">끌어서 자리를 옮기고, 눌러 유통·소비기한을 설정해요.</p></section>' +
      '<details class="kitchen-pantry"><summary>실온 보관 재료</summary>' + shelfMarkup('pantry') + '</details>' +
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
  function openZone(zone, doors = K.getDoorPanels()) { const compartment = compartmentFor(zone); return compartment === 'pantry' || !!doors[compartment]; }
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
        '';
      for (const image of button.querySelectorAll('img')) image.draggable = false;
    }
    const label = item.name + ', ' + status.quantity + ', ' + zones[zone] + ', ' + status.label;
    button.setAttribute('aria-label', label + (organizing ? ', 옮길 재료 선택' : ', 재료 수정'));
    button.title = label; button.classList.toggle('expired', status.d !== null && status.d < 0);
    button.style.opacity = status.d !== null && status.d < 0 ? '0.45' : '1';
    button.classList.toggle('exhausted', status.empty); button.classList.toggle('selected', movingId === item.id);
    button.disabled = !initialized || moveBusy || !openZone(zone, doors);
    button.draggable = !button.disabled && (!organizing || htmlDrag?.id === item.id);
    if (organizing) button.setAttribute('aria-pressed', String(movingId === item.id));
    else button.removeAttribute('aria-pressed');
    button.removeAttribute('aria-describedby');
    return button;
  }
  function renderSeasoningShelf() {
    const rack = scene.querySelector('.seasoning-rack-items');
    if (!rack || seasoningPointerSession?.dragging) return;
    const state = S.getState();
    const names = [...new Set((state.season || []).map(name => String(name).trim()).filter(Boolean))];
    const active = new Set(names);
    let changed = false;
    for (const saved of Object.keys(seasoningLayout)) if (!active.has(saved)) { delete seasoningLayout[saved]; changed = true; }
    if (changed) writeSeasoningLayout();
    rack.closest('.seasoning-rack-board').style.setProperty('--seasoning-rows', Math.max(1, Math.ceil(names.length / 4)));
    rack.innerHTML = names.length ? names.map(name => {
      const expiry = own(state.seasoningExpiry || {}, name) ? state.seasoningExpiry[name] : '', days = D.daysLeft(expiry);
      const label = days === null ? '기한 설정' : days < 0 ? '기한 경과' : days === 0 ? '오늘까지' : days === 1 ? '내일까지' : days + '일 남음';
      const kind = days === null ? 'unknown' : days < 0 ? 'expired' : days <= 3 ? 'soon' : 'safe';
      return '<button type="button" class="seasoning-mini" data-action="manage-seasonings" data-seasoning-name="' + esc(name) + '" data-expiry-status="' + kind + '" title="' + esc(name + ' · ' + (expiry || '기한 미입력')) + '" aria-label="' + esc(name + ' 양념, ' + label) + '. 누르면 유통·소비기한 수정, 끌어서 위치 이동">' +
        (A.seasoningArt?.(name, 'food-art') || A.foodArt(seasoningFoodId(name))) + '<span class="seasoning-name">' + esc(name) + '</span><small class="seasoning-expiry">' + esc(label) + '</small></button>';
    }).join('') : '<button type="button" class="seasoning-empty" data-action="add-seasoning">양념을 추가해 주세요 <span aria-hidden="true">＋</span></button>';
    names.forEach((name, index) => {
      const button = [...rack.querySelectorAll('.seasoning-mini')].find(node => node.dataset.seasoningName === name);
      if (button) placeSeasoning(button, seasoningPosition(name, index));
    });
  }
  function renderScene() {
    const items = S.getState().items, state = K.getState(), doors = K.getDoorPanels(), focused = document.activeElement;
    const focusedInside = scene.contains(focused) ? focused.closest('.fridge-inside') : null;
    const placements = new Map(items.map(item => [item.id, own(state.placements, item.id) ? state.placements[item.id] : 'middle']));
    const widgetRows = Math.max(1, ...Object.keys(zones).filter(zone => zone !== 'pantry').map(zone => Math.ceil(items.filter(item => placements.get(item.id) === zone).length / 2)));
    scene.style.setProperty('--widget-fridge-rows', String(widgetRows));
    if (pointerSession && (!items.some(item => item.id === pointerSession.id) || !openZone(pointerSession.sourceZone, doors) || placementFingerprint(pointerSession.id) !== pointerSession.fingerprint)) {
      cleanupPointer(); interaction++; announce('재료 상태가 바뀌어 이동을 취소했어요. 다시 골라주세요.');
    }
    if (movingId && (!placements.has(movingId) || !openZone(placements.get(movingId), doors))) { movingId = null; interaction++; }
    const anyOpen = Object.values(doors).some(Boolean);
    const stage = scene.querySelector('.fridge-stage');
    stage.classList.toggle('open', anyOpen);
    for (const key of Object.keys(compartments)) stage.classList.toggle(key + '-open', doors[key]);
    text(scene, '[data-kitchen-count]', items.filter(item => placements.get(item.id) !== 'pantry').length + '개');
    for (const [key, compartment] of Object.entries(compartments)) {
      const inside = scene.querySelector('#inside-' + key), count = items.filter(item => compartmentFor(placements.get(item.id)) === key).length;
      inside.toggleAttribute('inert', !doors[key]); inside.setAttribute('aria-hidden', String(!doors[key]));
      text(inside, '.compartment-head small', count + '개');
      for (const control of scene.querySelectorAll('[data-action="toggle-fridge"][data-compartment="' + key + '"]')) {
        control.classList.toggle('is-open', !!doors[key]);
        control.setAttribute('aria-expanded', String(!!doors[key])); control.setAttribute('aria-label', compartment.label + ' 문 ' + (doors[key] ? '닫기' : '열기'));
        const busy = !initialized || doorBusy[key] || organizeBusy || moveBusy;
        control.setAttribute('aria-disabled', String(busy));
        if (control.classList.contains('fridge-door')) control.tabIndex = doors[key] || busy ? -1 : 0;
        else { control.disabled = busy; text(control, '.toggle-label', compartment.shortLabel + ' ' + (doors[key] ? '닫기' : '열기')); text(control, 'small', count); }
      }
    }
    displayedPositions.clear();
    for (const zone of Object.keys(zones)) {
      const shelf = scene.querySelector('.shelf[data-zone="' + zone + '"]'), lots = items.filter(item => placements.get(item.id) === zone);
      if (!shelf) continue;
      const more = shelf.querySelector('.shelf-more'), label = shelf.querySelector('span.shelf-name'), target = shelf.querySelector('.shelf-target');
      const canvas = shelf.querySelector('.shelf-canvas');
      const layout = lots.map((item, index) => ({ item, index, position: own(state.positions || {}, item.id) ? state.positions[item.id] : defaultPosition(item.id, index, lots.length) }));
      const layers = new Map([...layout].sort((a, b) => a.position.z - b.position.z || a.index - b.index).map((entry, index) => [entry.item.id, index + 1]));
      const wanted = layout.map(({ item, position }) => { const button = foodButton(item, zone, doors); displayedPositions.set(item.id, { ...position }); placeButton(button, position, layers.get(item.id)); return button; });
      for (const button of canvas.querySelectorAll('.fridge-food')) if (!wanted.includes(button)) button.remove();
      let anchor = canvas.querySelector('.shelf-empty');
      for (let n = wanted.length - 1; n >= 0; n--) { if (wanted[n].nextElementSibling !== anchor) canvas.insertBefore(wanted[n], anchor); anchor = wanted[n]; }
      label.hidden = organizing; target.hidden = !organizing; target.disabled = !initialized || !movingId || moveBusy || !openZone(zone, doors);
      canvas.classList.toggle('is-organizing', organizing); canvas.setAttribute('aria-disabled', String(!initialized || !openZone(zone, doors)));
      shelf.classList.toggle('drop-mode', organizing); more.hidden = lots.length <= 2; more.textContent = '전체 ' + lots.length + '개';
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
    scene.querySelector('.kitchen-arrange-tools').hidden = !organizing;
    text(scene, '.kitchen-selected-material', moving ? moving.name + ' · 원하는 자리에 놓아주세요' : '옮길 재료를 먼저 골라주세요');
    for (const button of scene.querySelectorAll('.kitchen-layer-controls button')) button.disabled = !moving || moveBusy;
    scene.querySelector('.organize-banner').hidden = !organizing;
    text(scene, '.organize-banner span', moving ? moving.name + ' · 원하는 자리에 겹쳐 놓아보세요' : '재료를 끌어 겹쳐 놓거나, 놓을 자리를 눌러주세요');
    renderSeasoningShelf();
    for (const button of scene.querySelectorAll('.kitchen-zone-controls [data-zone]')) {
      button.disabled = !initialized || !movingId || moveBusy || !openZone(button.dataset.zone, doors);
      button.setAttribute('aria-label', (moving ? objectPhrase(moving.name) + ' ' : '') + zones[button.dataset.zone] + '으로 옮기기');
    }
    const hint = organizing ? '끌어서 옮기거나, 재료를 고른 뒤 원하는 자리를 눌러주세요' : anyOpen ? '재료를 누르면 수량과 기한을 볼 수 있어요' : '위 두 칸은 냉장 · 아래 두 칸은 냉동';
    const hintNode = scene.querySelector('.scene-hint');
    if (hintNode.dataset.message !== hint) { hintNode.dataset.message = hint; hintNode.innerHTML = A.icon(anyOpen ? 'leaf' : 'heart') + esc(hint); }
    renderDoorDisplays();
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
      if (await K.togglePanel(key)) { localError = ''; announce(compartments[key].label + ' 문을 ' + (K.getDoorPanels()[key] ? '열었어요.' : '닫았어요.')); }
      else localError = K.error || '문 상태를 저장하지 못했어요. 다시 시도해 주세요.';
    } catch (_) { localError = '문 상태를 저장하지 못했어요. 다시 시도해 주세요.'; }
    finally { doorBusy[key] = false; render(); }
  }
  async function toggleOrganize() {
    if (!initialized || moveBusy || organizeBusy) return;
    const token = ++interaction;
    if (organizing) { cleanupPointer(); organizing = false; movingId = null; draggedId = null; renderScene(); announce('자리 정리를 마쳤어요.'); return; }
    organizeBusy = true; renderScene();
    try {
      if (await K.setDoors({ freezer: true, fridge: true })) { localError = ''; if (token === interaction) { organizing = true; movingId = null; announce('옮길 재료를 누른 뒤, 옮길 칸을 골라주세요.'); } }
      else localError = K.error || '문 상태를 저장하지 못해 정리를 시작하지 못했어요.';
    } catch (_) { localError = '자리 정리를 시작하지 못했어요. 다시 시도해 주세요.'; }
    finally {
      organizeBusy = false; render();
      // Keep both lower compartments above the fixed mobile navigation while
      // arranging; otherwise a valid touch drop can hit the navigation instead.
      if (organizing && token === interaction) scene.querySelector('.fridge-stage')?.scrollIntoView?.({ block: 'center', inline: 'nearest', behavior: 'instant' });
    }
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
        scene.querySelector('.fridge-stage')?.scrollIntoView?.({ block: 'center', inline: 'nearest', behavior: 'instant' });
        itemButtons.get(id)?.focus({ preventScroll: true });
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
  function restoreItemFocus(id, focused, token) {
    if (token !== interaction || !(document.activeElement === focused || document.activeElement === document.body)) return;
    const moved = itemButtons.get(id);
    if (moved?.isConnected && !moved.disabled) moved.focus();
  }
  async function moveItem(id, zone, requestedPosition) {
    if (!initialized || moveBusy || !own(zones, zone) || !openZone(zone)) return;
    const item = S.getState().items.find(value => value.id === id);
    if (!item) { movingId = null; announce('먼저 옮길 재료를 골라주세요.'); renderScene(); return; }
    const token = interaction, focused = document.activeElement, ownedFocus = scene.contains(document.activeElement);
    const fingerprint = placementFingerprint(id);
    const previousZone = zoneFor(item), peers = S.getState().items.filter(value => zoneFor(value) === zone).length;
    const fallback = previousZone === zone ? positionFor(id) : defaultPosition(id, peers, peers + 1);
    const position = requestedPosition || fallback;
    const guard = () => !destroyed && token === interaction && openZone(previousZone) && openZone(zone) && placementFingerprint(id) === fingerprint;
    moveBusy = true; renderScene();
    try {
      if (await K.setPosition(id, zone, { x: unit(position.x), y: unit(position.y) }, guard)) {
        localError = '';
        if (token === interaction) { movingId = id; announce(objectPhrase(item.name) + ' ' + zones[zone] + '의 원하는 자리에 놓았어요.'); }
      } else if (!guard()) announce('재료나 선택이 바뀌어 이동을 취소했어요.');
      else localError = K.error || '재료 위치를 저장하지 못했어요. 다시 시도해 주세요.';
    } catch (_) { localError = '재료 위치를 저장하지 못했어요. 다시 시도해 주세요.'; }
    finally {
      moveBusy = false; draggedId = null; render();
      if (ownedFocus) restoreItemFocus(id, focused, token);
    }
  }
  async function changeLayer(direction) {
    const id = movingId, item = S.getState().items.find(value => value.id === id);
    if (!organizing || !item || moveBusy || pointerSession || !openZone(zoneFor(item))) return;
    const zone = zoneFor(item), token = interaction, focused = document.activeElement;
    const guard = () => !destroyed && token === interaction && S.getState().items.some(value => value.id === id) && zoneFor(id) === zone && openZone(zone);
    moveBusy = true; renderScene();
    try {
      // Materialize the visible defaults together so sending a saved tile behind
      // an unsaved tile has the same meaning after reload. No inventory is changed.
      const seeded = await K.updateAsync(draft => {
        const lots = S.getState().items.filter(value => (own(draft.placements, value.id) ? draft.placements[value.id] : 'middle') === zone);
        const missing = lots.filter(value => !own(draft.positions, value.id));
        if (!missing.length) return;
        lots.forEach((value, index) => {
          if (own(draft.positions, value.id)) return;
          const position = defaultPosition(value.id, index, lots.length);
          Object.defineProperty(draft.positions, value.id, { value: { x: position.x, y: position.y, z: 0 }, writable: true, enumerable: true, configurable: true });
        });
        // Defaults were behind saved positions. Preserve that whole order while
        // assigning positive stored layers, then move only the selected tile.
        const order = new Map(S.getState().items.map((value, index) => [value.id, index]));
        Object.entries(draft.positions).sort((a, b) => a[1].z - b[1].z || (order.get(a[0]) ?? Infinity) - (order.get(b[0]) ?? Infinity)).forEach(([, position], index) => { position.z = index + 1; });
      }, guard);
      if (seeded && await K.changeLayer(id, direction, guard)) {
        localError = ''; announce(objectPhrase(item.name) + ' ' + (direction === 'front' ? '앞에' : '뒤에') + ' 놓았어요.');
      } else if (!guard()) announce('재료나 선택이 바뀌어 순서 변경을 취소했어요.');
      else localError = K.error || '재료의 앞뒤 순서를 저장하지 못했어요.';
    } catch (_) { localError = '재료의 앞뒤 순서를 저장하지 못했어요.'; }
    finally { moveBusy = false; render(); restoreItemFocus(id, focused, token); }
  }
  function onSceneClick(event) {
    if (suppressClickUntil && Date.now() <= suppressClickUntil) { suppressClickUntil = 0; event.preventDefault(); event.stopPropagation(); return; }
    const canvas = event.target.closest('.shelf-canvas');
    if (organizing && movingId && canvas && !event.target.closest('.fridge-food')) {
      const position = pointOnCanvas(canvas, itemButtons.get(movingId), event);
      if (position && openZone(canvas.dataset.zone)) moveItem(movingId, canvas.dataset.zone, position);
      return;
    }
    const target = event.target.closest('[data-action]');
    if (!target || !scene.contains(target) || target.disabled || target.getAttribute('aria-disabled') === 'true') return;
    if (target.dataset.action === 'toggle-fridge') toggleDoor(target.dataset.compartment);
    else if (target.dataset.action === 'organize') toggleOrganize();
    else if (target.dataset.action === 'fridge-food') selectItem(target.dataset.lot);
    else if (target.dataset.action === 'add-seasoning') document.querySelector('#addSeason')?.click();
    else if (target.dataset.action === 'manage-seasonings') {
      window.UMFCore?.openSeasoning(target.dataset.seasoningName);
    }
    else if (target.dataset.action === 'move-zone' && organizing) moveItem(movingId, target.dataset.zone);
    else if (target.dataset.action === 'layer-front') changeLayer('front');
    else if (target.dataset.action === 'layer-back') changeLayer('back');
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
    if (event.key !== 'Escape') suppressClickUntil = 0;
    if (event.key === 'Escape' && (pointerSession || organizing)) {
      event.preventDefault(); event.stopPropagation(); cleanupPointer(); clearDrag(); interaction++; movingId = null; renderScene(); announce('옮길 재료 선택을 취소했어요.'); return;
    }
    const arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    if (organizing && movingId && own(arrows, event.key) && event.target.closest('.fridge-food,.kitchen-arrange-tools')) {
      event.preventDefault(); suppressClickUntil = 0;
      if (moveBusy || pointerSession) return;
      const step = event.shiftKey ? .1 : .02, current = positionFor(movingId), vector = arrows[event.key];
      const next = { x: unit(current.x + vector[0] * step), y: unit(current.y + vector[1] * step) };
      if (next.x !== current.x || next.y !== current.y) moveItem(movingId, zoneFor(movingId), next);
      return;
    }
    const target = event.target.closest('.fridge-door[role="button"]');
    if (target && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); if (!event.repeat) target.click(); }
  }
  function onPresentationChange() { abortGesture(); render(); }
  function onNavigation(event) {
    interaction++; cleanupPointer(); clearDrag();
    if (event.detail?.page !== 'home') { organizing = false; movingId = null; draggedId = null; renderScene(); }
  }
  function sizeOf(button) {
    const rect = button?.getBoundingClientRect?.();
    return { width: rect?.width || button?.offsetWidth || 0, height: rect?.height || button?.offsetHeight || 0 };
  }
  function pointOnCanvas(canvas, button, event, anchor) {
    const rect = canvas?.getBoundingClientRect?.();
    if (!rect || rect.width <= 0 || rect.height <= 0 || !Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)) return null;
    if (event.clientX < rect.left || event.clientX > rect.left + rect.width || event.clientY < rect.top || event.clientY > rect.top + rect.height) return null;
    return normalizedPoint(rect, sizeOf(button), { x: event.clientX, y: event.clientY }, anchor);
  }
  function canvasAtPoint(event) {
    if (!Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)) return null;
    // Pointer capture keeps event.target on the source. Hit-testing is essential
    // both for another shelf and for rejecting an outside release.
    let hit;
    if (typeof document.elementFromPoint === 'function') hit = document.elementFromPoint(event.clientX, event.clientY);
    else hit = event.target;
    const canvas = hit?.closest?.('.shelf-canvas');
    if (!canvas || !scene.contains(canvas) || !openZone(canvas.dataset.zone) || canvas.closest('[inert]')) return null;
    const rect = canvas.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && event.clientX >= rect.left && event.clientX <= rect.left + rect.width && event.clientY >= rect.top && event.clientY <= rect.top + rect.height ? canvas : null;
  }
  function clearHighlights() { for (const target of scene.querySelectorAll('.is-over')) target.classList.remove('is-over'); }
  function makeGhost(button) {
    const ghost = button.cloneNode(true), rect = button.getBoundingClientRect(), prefix = 'umf-drag-' + (++ghostSequence) + '-';
    ghost.removeAttribute('id'); ghost.removeAttribute('data-action'); ghost.removeAttribute('data-lot');
    ghost.classList.remove('selected', 'is-drag-source'); ghost.classList.add('kitchen-drag-ghost');
    ghost.disabled = true; ghost.draggable = false; ghost.tabIndex = -1; ghost.setAttribute('aria-hidden', 'true');
    const renamed = new Map();
    for (const node of ghost.querySelectorAll('[id]')) { renamed.set(node.id, prefix + node.id); node.id = prefix + node.id; }
    for (const node of ghost.querySelectorAll('*')) for (const attribute of [...node.attributes]) {
      let value = attribute.value;
      for (const [before, after] of renamed) value = value.replaceAll('url(#' + before + ')', 'url(#' + after + ')').replace(/^#(.+)$/, (match, id) => id === before ? '#' + after : match);
      if (value !== attribute.value) node.setAttribute(attribute.name, value);
    }
    Object.assign(ghost.style, { position: 'fixed', width: rect.width + 'px', height: rect.height + 'px', maxWidth: 'none', minWidth: '0', transform: 'none', margin: '0', pointerEvents: 'none', zIndex: '2147483647', transition: 'none', opacity: '1' });
    document.body.appendChild(ghost); return ghost;
  }
  let edgeFrame = null, edgePoint = null;
  function edgeScroll() {
    edgeFrame = null;
    if (!pointerSession?.dragging || !edgePoint) return;
    const height = window.innerHeight, rect = scene.getBoundingClientRect();
    const amount = edgePoint.clientY > height - 64 && rect.bottom > height - 70 ? 14 : edgePoint.clientY < 100 && rect.top < 70 ? -14 : 0;
    if (!amount || edgePoint.clientX < 0 || edgePoint.clientX > window.innerWidth || edgePoint.clientY < 0 || edgePoint.clientY > height) return;
    const previous = window.scrollY;
    window.scrollBy({top:amount,behavior:'instant'});
    clearHighlights();canvasAtPoint(edgePoint)?.classList.add('is-over');
    if (window.scrollY !== previous) edgeFrame = window.requestAnimationFrame(edgeScroll);
  }
  function trackEdgeScroll(event) {
    edgePoint = {clientX:event.clientX,clientY:event.clientY};
    if (edgeFrame === null && typeof window.requestAnimationFrame === 'function' && typeof window.scrollBy === 'function') edgeFrame = window.requestAnimationFrame(edgeScroll);
  }
  function cleanupPointer(suppress = true) {
    if (edgeFrame !== null) window.cancelAnimationFrame?.(edgeFrame);
    edgeFrame = null; edgePoint = null;
    const active = pointerSession; if (!active) return;
    pointerSession = null;
    active.ghost?.remove(); active.button.classList.remove('is-drag-source'); clearHighlights();
    if (suppress) suppressClickUntil = Date.now() + 500;
    try { if (active.button.hasPointerCapture?.(active.pointerId)) active.button.releasePointerCapture(active.pointerId); } catch (_) { /* The browser may already have released it. */ }
  }
  function onSeasoningPointerDown(event) {
    const button = event.target.closest('.seasoning-mini');
    if (!button || button.disabled || seasoningPointerSession || event.isPrimary === false || (event.button ?? 0) !== 0) return false;
    const rack = button.closest('.seasoning-rack-items'), name = button.dataset.seasoningName;
    if (!rack || !name) return false;
    const rect = button.getBoundingClientRect();
    seasoningPointerSession = {
      name, button, rack, pointerId: event.pointerId ?? 1,
      startX: event.clientX, startY: event.clientY, dragging: false,
      start: { ...seasoningPosition(name, [...rack.querySelectorAll('.seasoning-mini')].indexOf(button)) },
      anchor: { x: rect.width ? (event.clientX - rect.left) / rect.width : .5, y: rect.height ? (event.clientY - rect.top) / rect.height : .5 }
    };
    try { button.setPointerCapture?.(seasoningPointerSession.pointerId); } catch (_) {}
    return true;
  }
  function seasoningPoint(active, event) {
    const rect = active.rack.getBoundingClientRect(), size = active.button.getBoundingClientRect();
    const rawX = rect.width ? (event.clientX - rect.left) / rect.width : .5;
    const rawY = rect.height ? (event.clientY - rect.top) / rect.height : .5;
    return { x: clamp(rawX, .07, .93), y: clamp(rawY, .06, .94), z: Math.max(1, ...Object.values(seasoningLayout).map(p => Number(p.z) || 0)) + 1 };
  }
  function finishSeasoningPointer(event, cancel = false) {
    const active = seasoningPointerSession;
    if (!active || (event && (event.pointerId ?? 1) !== active.pointerId)) return false;
    seasoningPointerSession = null;
    active.button.classList.remove('is-dragging');
    if (cancel) placeSeasoning(active.button, active.start);
    else if (active.dragging) {
      const next = seasoningPoint(active, event);
      seasoningLayout[active.name] = next; writeSeasoningLayout(); placeSeasoning(active.button, next);
      suppressClickUntil = Date.now() + 450;
      announce(active.name + ' 양념 위치를 옮겼어요.');
    }
    try { if (active.button.hasPointerCapture?.(active.pointerId)) active.button.releasePointerCapture(active.pointerId); } catch (_) {}
    return true;
  }
  function onPointerDown(event) {
    suppressClickUntil = 0;
    if (onSeasoningPointerDown(event)) return;
    const button = event.target.closest('.fridge-food');
    if (!button || !organizing || !initialized || moveBusy || pointerSession || button.disabled || event.isPrimary === false || (event.button ?? 0) !== 0) return;
    const item = S.getState().items.find(value => value.id === button.dataset.lot);
    if (!item || !openZone(zoneFor(item))) return;
    const rect = button.getBoundingClientRect(); interaction++;
    pointerSession = {
      id: item.id, pointerId: event.pointerId ?? 1, button, sourceZone: zoneFor(item), fingerprint: placementFingerprint(item.id),
      startX: event.clientX, startY: event.clientY, dragging: false, ghost: null,
      anchor: { x: rect.width ? unit((event.clientX - rect.left) / rect.width) : .5, y: rect.height ? unit((event.clientY - rect.top) / rect.height) : .5 }
    };
    event.preventDefault(); button.focus();
    try { button.setPointerCapture?.(pointerSession.pointerId); } catch (_) { /* Window listeners provide an uncaptured fallback. */ }
  }
  function onPointerMove(event) {
    if (seasoningPointerSession) {
      const active = seasoningPointerSession;
      if ((event.pointerId ?? 1) !== active.pointerId) return;
      if (!active.dragging && Math.hypot(event.clientX - active.startX, event.clientY - active.startY) < 5) return;
      event.preventDefault();
      active.dragging = true; active.button.classList.add('is-dragging');
      const next = seasoningPoint(active, event); placeSeasoning(active.button, next);
      return;
    }
    const active = pointerSession; if (!active || (event.pointerId ?? 1) !== active.pointerId) return;
    if (handledPointerMoves.has(event)) return; handledPointerMoves.add(event);
    if (placementFingerprint(active.id) !== active.fingerprint || !openZone(active.sourceZone)) { cleanupPointer(); interaction++; renderScene(); return; }
    if (!active.dragging && Math.hypot(event.clientX - active.startX, event.clientY - active.startY) < 5) return;
    event.preventDefault();
    if (!active.dragging) {
      active.dragging = true; movingId = active.id; active.ghost = makeGhost(active.button); active.button.classList.add('is-drag-source');
      renderScene(); announce(S.getState().items.find(item => item.id === active.id)?.name + ' 이동 중. 원하는 선반 안에 놓아주세요.');
    }
    if (pointerSession !== active) return;
    const size = sizeOf(active.button), canvas = canvasAtPoint(event);
    active.ghost.style.left = event.clientX - size.width * active.anchor.x + 'px'; active.ghost.style.top = event.clientY - size.height * active.anchor.y + 'px';
    active.ghost.classList.toggle('is-outside', !canvas); clearHighlights(); canvas?.classList.add('is-over');
    trackEdgeScroll(event);
  }
  function onPointerUp(event) {
    if (seasoningPointerSession) { finishSeasoningPointer(event, false); return; }
    const active = pointerSession; if (!active || (event.pointerId ?? 1) !== active.pointerId) return;
    event.preventDefault();
    const canvas = active.dragging ? canvasAtPoint(event) : null;
    const position = canvas ? pointOnCanvas(canvas, active.button, event, active.anchor) : null;
    const current = placementFingerprint(active.id) === active.fingerprint;
    cleanupPointer();
    if (!current) { interaction++; renderScene(); announce('재료가 바뀌어 이동을 취소했어요.'); }
    else if (!active.dragging) selectItem(active.id);
    else if (canvas && position) moveItem(active.id, canvas.dataset.zone, position);
    else { renderScene(); announce('선반 밖에 놓아 이동을 취소했어요.'); }
  }
  function onPointerCancel(event) {
    if (seasoningPointerSession) { finishSeasoningPointer(event, true); return; }
    if (!pointerSession || (event.pointerId ?? 1) !== pointerSession.pointerId) return;
    cleanupPointer(); interaction++; renderScene(); announce('재료 이동을 취소했어요.');
  }
  function onWindowKeyDown(event) {
    if (event.key === 'Escape' && seasoningPointerSession) { finishSeasoningPointer(null, true); announce('양념 이동을 취소했어요.'); event.preventDefault(); return; }
    if (event.key === 'Escape' && (pointerSession || (moveBusy && organizing))) { cleanupPointer(); clearDrag(); interaction++; movingId = null; renderScene(); announce('재료 이동을 취소했어요.'); event.preventDefault(); }
  }
  function abortGesture() {
    if (seasoningPointerSession) finishSeasoningPointer(null, true);
    if (pointerSession || draggedId) { cleanupPointer(); clearDrag(); interaction++; renderScene(); announce('재료 이동을 취소했어요.'); }
  }
  function onVisibilityChange() { if (document.hidden) abortGesture(); }
  function dragTarget(event) { const target = event.target.closest('.shelf-canvas[data-zone],.shelf[data-zone],.kitchen-zone-controls [data-zone]'); return target && scene.contains(target) ? target : null; }
  function onDragStart(event) {
    const button = event.target.closest('.fridge-food');
    if (!button || button.disabled || moveBusy || !initialized || pointerSession) { event.preventDefault(); return; }
    const item = S.getState().items.find(value => value.id === button.dataset.lot);
    if (!item || !openZone(zoneFor(item))) { event.preventDefault(); return; }
    interaction++; organizing = true; movingId = draggedId = item.id;
    htmlDrag = { id: item.id, fingerprint: placementFingerprint(item.id) };
    if (event.dataTransfer) { event.dataTransfer.setData('text/plain', item.id); event.dataTransfer.effectAllowed = 'move'; }
    renderScene();
  }
  function onDragOver(event) { const target = dragTarget(event); if (target && draggedId && !moveBusy && openZone(target.dataset.zone)) { event.preventDefault(); if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'; target.classList.add('is-over'); } }
  function onDragLeave(event) { const target = dragTarget(event); if (target && !target.contains(event.relatedTarget)) target.classList.remove('is-over'); }
  function clearDrag() { if (draggedId) suppressClickUntil = Date.now() + 500; clearHighlights(); draggedId = null; htmlDrag = null; }
  function onDrop(event) {
    const target = dragTarget(event); if (!target) return;
    event.preventDefault(); target.classList.remove('is-over');
    const id = event.dataTransfer?.getData('text/plain') || draggedId;
    if (id && id === draggedId && openZone(target.dataset.zone) && (!htmlDrag || htmlDrag.fingerprint === placementFingerprint(id))) {
      const canvas = target.classList.contains('shelf-canvas') ? target : target.querySelector('.shelf-canvas');
      const position = canvas ? pointOnCanvas(canvas, itemButtons.get(id), event) : null;
      suppressClickUntil = Date.now() + 500; moveItem(id, target.dataset.zone, position || undefined);
    }
  }

  mountScene(); mountHero();
  const handlers = { click: onSceneClick, keydown: onKeyDown, pointerdown: onPointerDown, pointermove: onPointerMove, pointerup: onPointerUp, pointercancel: onPointerCancel, lostpointercapture: onPointerCancel, dragstart: onDragStart, dragover: onDragOver, dragleave: onDragLeave, dragend: clearDrag, drop: onDrop };
  for (const [event, handler] of Object.entries(handlers)) scene.addEventListener(event, handler);
  hero?.addEventListener('click', onHeroClick);
  const offStore = S.subscribe(render), offKitchen = K.subscribe(render);
  window.addEventListener('umf:selectionchange', renderHero); window.addEventListener('umf:daychange', render); window.addEventListener('umf:kitchenerror', renderError);
  window.addEventListener('umf:navigation', onNavigation);
  window.addEventListener('pointermove', onPointerMove); window.addEventListener('pointerup', onPointerUp); window.addEventListener('pointercancel', onPointerCancel); window.addEventListener('keydown', onWindowKeyDown);
  window.addEventListener('blur', abortGesture); window.addEventListener('resize', abortGesture); window.addEventListener('umf:presentationchange', onPresentationChange); document.addEventListener('visibilitychange', onVisibilityChange);
  // Presentation changes must never rewrite inventory dates or quantities.
  const ready = Promise.all([S.ready, K.ready]).then(() => { initialized = true; render(); return true; }).catch(() => { localError = '부엌의 저장 상태를 읽지 못했어요.'; renderError(); return false; });
  window.UMFKitchen = {
    ready, render, navigate, arrangeItem, foodIdFor, itemStatus, zones, positionFor,
    geometry: Object.freeze({ normalizedPoint, defaultPosition }),
    getOrganizing: () => organizing, getMovingId: () => movingId,
    destroy() { destroyed = true; cleanupPointer(false); clearDrag(); offStore?.(); offKitchen?.(); for (const [event, handler] of Object.entries(handlers)) scene.removeEventListener(event, handler); hero?.removeEventListener('click', onHeroClick); window.removeEventListener('umf:selectionchange', renderHero); window.removeEventListener('umf:daychange', render); window.removeEventListener('umf:kitchenerror', renderError); window.removeEventListener('umf:navigation', onNavigation); window.removeEventListener('pointermove', onPointerMove); window.removeEventListener('pointerup', onPointerUp); window.removeEventListener('pointercancel', onPointerCancel); window.removeEventListener('keydown', onWindowKeyDown); window.removeEventListener('blur', abortGesture); window.removeEventListener('resize', abortGesture); window.removeEventListener('umf:presentationchange', onPresentationChange); document.removeEventListener('visibilitychange', onVisibilityChange); }
  };
  render();
})();
