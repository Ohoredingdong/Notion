/* Recipe views share the same inventory model as the fridge and shopping list. */
(() => {
  'use strict';
  const D = window.UMFDomain;
  const Store = window.UMFStore;
  if (!D || !Store) return;
  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const C = [
    {
      name: '계란 볶음밥', f: ['계란', '양파'], s: ['식용유', '간장'], p: ['밥/즉석밥'],
      time: '약 20분', level: '쉬움', tone: 'egg', desc: '양파와 계란을 볶아 밥 한 공기로 만드는 한 끼',
      amounts: { '계란': '1개', '양파': '1/4개', '식용유': '1작은술', '간장': '1작은술', '밥/즉석밥': '1공기' },
      steps: ['양파를 잘게 썰고 계란을 풀어 준비해 주세요.', '팬에 식용유를 두르고 양파가 부드러워질 때까지 볶아 주세요.', '계란을 넣고 익힌 뒤 밥과 간장을 넣어 고르게 볶아 주세요.']
    },
    {
      name: '두부 된장국', f: ['두부', '애호박', '양파'], s: ['된장', '다진마늘'], p: [],
      time: '약 25분', level: '쉬움', tone: 'tofu', desc: '두부와 채소를 넣고 구수하게 끓이는 국',
      amounts: { '두부': '150g', '애호박': '1/4개', '양파': '1/4개', '된장': '1/2큰술', '다진마늘': '1/2작은술' },
      water: '물 350mL',
      steps: ['두부는 깍둑썰고 애호박과 양파는 먹기 좋은 크기로 썰어 주세요.', '냄비에 물과 된장을 넣고 된장을 풀어 끓여 주세요.', '애호박, 양파, 다진마늘을 넣고 익힌 뒤 두부를 넣어 한 번 더 끓여 주세요. 간이 진하면 물을 더 넣어 주세요.']
    },
    {
      name: '닭가슴살 샐러드', f: ['닭가슴살', '토마토'], s: ['소금', '후추'], p: [],
      time: '약 25분', level: '쉬움', tone: 'tomato', desc: '익힌 닭가슴살과 토마토를 함께 담는 간단한 한 접시',
      amounts: { '닭가슴살': '120g', '토마토': '1개', '소금': '조금', '후추': '조금' },
      water: '닭가슴살을 삶을 물',
      steps: ['토마토를 씻어 썰어 주세요. 생닭을 다룬 도구는 세척해서 사용해 주세요.', '닭가슴살을 물에 삶아 중심까지 충분히 익힌 뒤, 먹기 좋은 크기로 찢어 주세요. 이미 익힌 제품은 포장지 조리법을 따라 주세요.', '닭가슴살과 토마토를 접시에 담고 소금과 후추로 가볍게 간해 주세요.']
    },
    {
      name: '애호박 계란전', f: ['애호박', '계란'], s: ['소금', '식용유'], p: [],
      time: '약 15분', level: '쉬움', tone: 'zucchini', desc: '가늘게 썬 애호박에 계란을 섞어 부치는 작은 전',
      amounts: { '애호박': '1/3개', '계란': '1개', '소금': '조금', '식용유': '1작은술' },
      steps: ['애호박을 가늘게 채 썰어 주세요.', '계란을 풀고 애호박과 소금을 넣어 섞어 주세요.', '기름을 두른 팬에 한 숟갈씩 올려 약한 불에서 앞뒤로 충분히 익혀 주세요. 작게 부치면 뒤집기 편해요.']
    },
    {
      name: '요거트 계란 샐러드', f: ['요거트', '계란'], s: ['소금', '후추'], p: [],
      time: '약 20분', level: '쉬움', tone: 'yogurt', desc: '삶은 계란을 플레인 요거트로 부드럽게 버무린 샐러드',
      amounts: { '요거트': '플레인 2큰술', '계란': '2개', '소금': '조금', '후추': '조금' },
      water: '계란을 삶을 물',
      steps: ['계란을 물에 완숙으로 삶아 식힌 뒤 껍질을 벗겨 주세요.', '계란을 먹기 좋게 으깨고 플레인 요거트를 넣어 섞어 주세요.', '소금과 후추를 조금씩 넣어 간을 맞춰 주세요. 요거트는 단맛이 없는 제품을 확인해 주세요.']
    },
    {
      name: '두부 스테이크', f: ['두부', '양파'], s: ['간장', '식용유'], p: [],
      time: '약 20분', level: '쉬움', tone: 'tofu', desc: '노릇한 두부에 양파 간장소스를 곁들이는 한 접시',
      amounts: { '두부': '150g', '양파': '1/4개', '간장': '1작은술', '식용유': '1작은술' },
      water: '소스에 넣을 물 1큰술',
      steps: ['두부의 물기를 닦아 도톰하게 썰고 양파는 얇게 썰어 주세요.', '식용유를 두른 팬에 두부를 앞뒤로 노릇하게 구워 접시에 옮겨 주세요.', '같은 팬에 양파를 볶고 간장과 물 1큰술을 넣어 살짝 끓인 뒤 두부 위에 올려 주세요.']
    },
    {
      name: '버섯 두부볶음', f: ['두부', '버섯', '양파'], s: ['간장', '식용유'], p: [],
      time: '약 20분', level: '쉬움', tone: 'mushroom', desc: '버섯과 양파, 두부를 함께 볶는 담백한 반찬',
      amounts: { '두부': '150g', '버섯': '70g', '양파': '1/4개', '간장': '1작은술', '식용유': '1작은술' },
      steps: ['두부는 물기를 닦아 한입 크기로 썰고, 양파와 버섯도 썰어 주세요.', '식용유를 두른 팬에 두부를 먼저 노릇하게 익혀 주세요.', '양파와 버섯을 넣어 익힌 뒤 간장을 넣고 고르게 볶아 주세요.']
    },
    {
      name: '토마토 치즈 오믈렛', f: ['계란', '토마토', '치즈'], s: ['소금', '식용유'], p: [],
      time: '약 15분', level: '쉬움', tone: 'cheese', desc: '토마토와 치즈를 넣고 계란을 부드럽게 접은 오믈렛',
      amounts: { '계란': '2개', '토마토': '1/2개', '치즈': '1장 또는 20g', '소금': '조금', '식용유': '1작은술' },
      steps: ['계란을 풀어 소금을 조금 넣고, 토마토는 작게 썰어 주세요.', '식용유를 두른 팬에서 토마토를 살짝 익힌 뒤 계란물을 부어 주세요.', '약한 불에서 익히다가 치즈를 올리고 반으로 접어, 안쪽 계란까지 익혀 주세요.']
    }
  ];
  const ingredientParts = {
    '계란': '<path d="M12 3.8c3.3 0 6 5.1 6 9.1a6 6 0 1 1-12 0c0-4 2.7-9.1 6-9.1Z" fill="#fff0c6" stroke="#c39c59"/>',
    '양파': '<path d="M12 5c1.8 1.8 6 4.9 6 9a6 6 0 1 1-12 0c0-4.1 4.2-7.2 6-9Z" fill="#eed7bd" stroke="#b78961"/><path d="M12 6v14M10 3l2 2 2-2" stroke="#b78961"/>',
    '두부': '<path d="m4 8 8-4 8 4v9l-8 4-8-4Z" fill="#fff4d9" stroke="#bea267"/><path d="m4 8 8 4 8-4M12 12v9" stroke="#bea267"/>',
    '애호박': '<path d="M4 15C7 8 14 6 21 8c-3 7-10 10-17 7Z" fill="#bbd997" stroke="#699b58"/><path d="m6 14 12-5" stroke="#699b58"/>',
    '닭가슴살': '<path d="M6 9c3-4 8-5 12-1 5 5 1 11-5 12-6 1-10-6-7-11Z" fill="#f4c4b3" stroke="#ba7c62"/><path d="m9 10 6 6m-4-8 6 6" stroke="#ba7c62"/>',
    '토마토': '<path d="M5 10c2-3 5-3 7-1 2-2 5-2 7 1 4 6-1 11-7 11S1 16 5 10Z" fill="#efac96" stroke="#bb7463"/><path d="m12 5-1 5-4-1m5 0 4-2m-4 1 3 3" stroke="#67916b"/>',
    '요거트': '<path d="M6 8h12l-2 13H8L6 8Z" fill="#fafbff" stroke="#9ba9c8"/><path d="M5 5h14v3H5ZM9 13h6" fill="#d5e2f5" stroke="#9ba9c8"/>',
    '버섯': '<path d="M10 13h4l1 8H9l1-8Z" fill="#f4e8d4" stroke="#aa9479"/><path d="M3 13C3 1 21 1 21 13H3Z" fill="#ceb6a0" stroke="#9b8067"/><path d="M7 9h.1M13 6h.1M17 10h.1" stroke="#fff4df" stroke-width="2.5"/>',
    '치즈': '<path d="m4 10 12-6 5 6v10H4V10Z" fill="#f8da83" stroke="#c39e4a"/><path d="M4 10h17" stroke="#c39e4a"/><circle cx="9" cy="15" r="1.3" fill="#dcb65c"/><circle cx="16" cy="16" r="1.8" fill="#dcb65c"/>'
  };
  const artIcon = (name) => ingredientParts[name]
    ? `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round">${ingredientParts[name]}</svg>`
    : (window.UMFCore?.icon(name) || '<svg viewBox="0 0 24 24" fill="none"><path d="M4 11h16l-2 9H6L4 11Z" stroke="currentColor"/></svg>');
  const heart = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z"/></svg>';
  const reasonLabel = { missing: '없음', expired: '소비기한 경과', empty: '소진' };
  const kindLabel = { fridge: '냉장고', season: '기본 양념', pantry: '상비 재료' };
  let selectedName = null;
  let visibleNames = [];
  let detailOpen = false;

  function ranked() {
    return D.rankRecipes(C, Store.getState());
  }
  function selected() {
    if (!selectedName || !visibleNames.includes(selectedName)) return null;
    const recipe = C.find((r) => r.name === selectedName);
    return recipe ? { recipe, ...D.evaluate(recipe, Store.getState()) } : null;
  }
  function notifySelection() {
    window.dispatchEvent(new CustomEvent('umf:selectionchange', { detail: { name: selectedName } }));
  }
  function setDetailVisibility() {
    const detail = $('#umfRecipeDetail');
    if (detail) detail.classList.toggle('on', detailOpen && !!selected());
    const button = $('#umfRecipeBtn');
    if (button) {
      button.setAttribute('aria-expanded', String(detailOpen && !!selected()));
      button.setAttribute('aria-controls', 'umfRecipeDetail');
      button.textContent = detailOpen && selected() ? '레시피 접기' : '레시피 보기';
    }
  }
  function renderSelection() {
    const current = selected();
    const name = $('#umfSelectedName');
    const status = $('#umfSelectionStatus');
    const chips = $('#umfSelectionChips');
    const detail = $('#umfRecipeDetail');
    document.querySelectorAll('#umfRecipeGrid .umf-menu-card').forEach((card) => {
      const active = card.dataset.name === current?.recipe.name;
      card.classList.toggle('selected', active);
      card.querySelector('.umf-menu-select')?.setAttribute('aria-pressed', String(active));
    });
    const log = $('#umfLogBtn');
    if (log) {
      log.disabled = !current?.available || log.dataset.busy === 'true';
      log.title = current?.available ? '재고 차감 없이 식사를 기록합니다' : '부족하거나 기한이 지난 재료를 먼저 확인해 주세요';
    }
    if ($('#umfRecipeBtn')) $('#umfRecipeBtn').disabled = !current;
    if ($('#umfShuffleBtn')) $('#umfShuffleBtn').disabled = visibleNames.length < 2;
    if (!current) {
      if (name) name.textContent = '선택할 메뉴가 없어요';
      if (status) status.textContent = '검색어를 지우거나 다른 필터를 선택해 주세요.';
      if (chips) chips.replaceChildren();
      if (detail) detail.replaceChildren();
      detailOpen = false;
      setDetailVisibility();
      notifySelection();
      return;
    }
    const r = current.recipe;
    if (name) name.textContent = r.name;
    if (status) {
      const missingNames = current.missing.map((m) => `${m.name} (${reasonLabel[m.reason] || '확인'})`).join(' · ');
      status.textContent = current.available
        ? '필요한 재료가 등록되어 있어요. 조리 전에 실제 분량과 재료 상태를 확인해 주세요.'
        : `확인할 재료 ${current.missing.length}개 · ${missingNames}`;
      status.classList.toggle('needs-check', !current.available);
    }
    if (chips) {
      const st = Store.getState();
      const ingredients = [...r.f, ...r.s, ...r.p];
      const checked = [...new Set([...st.season, ...st.pantry])].filter((n) => ingredients.some((required) => D.canonical(required) === D.canonical(n)));
      const owned = current.usedItems.map((item) => {
        const d = D.daysLeft(item.expiry);
        const quantity = item.quantity ? ` · ${item.quantity}` : ' · 수량 미입력';
        const expiry = d === 0 ? ' · 오늘까지' : d != null && d <= 2 ? ` · D-${d}` : d == null ? ' · 기한 미입력' : '';
        return `<span class="umf-selection-chip${d != null && d <= 2 ? ' urgent' : ''}">${esc(item.name)}${esc(quantity + expiry)}</span>`;
      });
      const usedCanon = new Set(current.usedItems.map((item) => D.canonical(item.name)));
      checked.forEach((n) => { if (!usedCanon.has(D.canonical(n))) owned.push(`<span class="umf-selection-chip checked">${esc(n)} · 보유 체크</span>`); });
      chips.innerHTML = owned.length ? owned.join('') : '<span class="umf-selection-chip">등록된 재료가 아직 없어요</span>';
    }
    if (detail) {
      const amountRows = [...r.f, ...r.s, ...r.p].map((ingredient) => `<li><span>${esc(ingredient)}</span><b>${esc(r.amounts[ingredient] || '적당량')}</b></li>`).join('');
      const shortages = current.missing.length
        ? `<div class="umf-detail-missing"><b>먼저 확인할 재료</b><ul>${current.missing.map((m) => `<li>${esc(m.name)} · ${esc(kindLabel[m.kind] || '재료')} · ${esc(reasonLabel[m.reason] || '확인 필요')}</li>`).join('')}</ul></div>` : '';
      detail.innerHTML = `<h3>${esc(r.name)}</h3><p class="umf-portion-note">1인분 조리 예시예요. 보유 여부는 재료 종류를 기준으로 확인하며, 아래 분량만큼 충분한지는 직접 확인해 주세요.</p><ul class="umf-detail-amounts">${amountRows}</ul>${r.water ? `<p class="umf-water-note">별도 준비: ${esc(r.water)}</p>` : ''}${shortages}<h4>만드는 순서</h4><ol class="umf-cooking-steps">${r.steps.map((step) => `<li>${esc(step)}</li>`).join('')}</ol>`;
    }
    setDetailVisibility();
    notifySelection();
  }
  function select(name, options = {}) {
    if (!visibleNames.includes(name)) return false;
    const changed = selectedName !== name;
    selectedName = name;
    if (changed || options.openDetail) detailOpen = true;
    renderSelection();
    return true;
  }
  async function favorite(name, button) {
    const focusWasOnButton = document.activeElement === button;
    let focusAtCommit = false;
    const saved = await Store.updateAsync((st) => {
      focusAtCommit = document.activeElement === button;
      st.favorites = st.favorites.includes(name) ? st.favorites.filter((item) => item !== name) : [...st.favorites, name];
    });
    if (!saved || !focusWasOnButton || !focusAtCommit) return;
    if (document.activeElement !== button && document.activeElement !== document.body) return;
    const replacement = [...document.querySelectorAll('#umfRecipeGrid .umf-menu-card')].find((card) => card.dataset.name === name)?.querySelector('.umf-fav');
    if (replacement) replacement.focus();
    else $('#umfRecipeFilter')?.focus();
  }
  function renderCard(entry, favoriteNames) {
    const r = entry.recipe;
    const card = document.createElement('article');
    card.className = `umf-menu-card${entry.available ? '' : ' missing'}${entry.urgentCount ? ' uses-soon' : ''}`;
    card.dataset.name = r.name;
    card.dataset.missing = JSON.stringify(entry.missing.map((m) => m.name));
    card.dataset.available = String(entry.available);
    card.dataset.urgentCount = String(entry.urgentCount);
    const isFavorite = favoriteNames.has(r.name);
    const needs = entry.missing.map((m) => m.name);
    const statusText = entry.available ? '재료 있음 · 분량 확인' : `필요 · ${needs.slice(0, 2).join(' · ')}${needs.length > 2 ? ` 외 ${needs.length - 2}개` : ''}`;
    card.innerHTML = `<div class="umf-menu-photo umf-ingredient-art tone-${esc(r.tone)}"><div class="umf-ingredient-scene" aria-hidden="true">${r.f.slice(0, 3).map((ingredient) => `<span class="umf-art-ingredient">${artIcon(ingredient)}<span class="umf-art-label">${esc(ingredient)}</span></span>`).join('')}</div><span class="umf-art-caption">재료 구성</span></div><div class="umf-menu-body"><div class="umf-menu-name">${esc(r.name)}</div><div class="umf-menu-desc">${esc(r.desc)}</div><div class="umf-menu-meta"><span>${esc(r.time)}</span><span>${esc(r.level)}</span></div>${entry.urgentCount ? `<div class="umf-menu-priority">먼저 쓸 재료 ${entry.urgentCount}개</div>` : ''}</div><div class="${entry.available ? 'umf-menu-status' : 'umf-menu-missing'}" title="${esc(entry.available ? '재료 종류만 확인한 결과입니다' : needs.join(' · '))}">${esc(statusText)}</div><button type="button" class="umf-menu-select" aria-label="${esc(r.name)} 레시피 선택" aria-pressed="false"><span class="umf-sr-only">${esc(r.name)} 레시피 선택</span></button><button type="button" class="umf-fav${isFavorite ? ' on' : ''}" aria-label="${esc(r.name)} 즐겨찾기${isFavorite ? ' 해제' : ''}" aria-pressed="${isFavorite}">${heart}</button>`;
    card.querySelector('.umf-menu-select').addEventListener('click', () => select(r.name, { openDetail: true }));
    const fav = card.querySelector('.umf-fav');
    fav.addEventListener('click', () => favorite(r.name, fav));
    return card;
  }
  function render() {
    const grid = $('#umfRecipeGrid');
    if (!grid) return;
    const st = Store.getState();
    const all = D.rankRecipes(C, st);
    const filter = $('#umfRecipeFilter')?.value || 'all';
    const search = D.normalizeName($('#umfRecipeSearch')?.value || '').toLocaleLowerCase('ko-KR');
    const favorites = new Set(st.favorites);
    const visible = all.filter((entry) => {
      if (filter === 'available' && !entry.available) return false;
      if (filter === 'favorites' && !favorites.has(entry.recipe.name)) return false;
      const recipe = entry.recipe;
      const pool = [recipe.name, ...recipe.f, ...recipe.s, ...recipe.p].map((s) => D.normalizeName(s).toLocaleLowerCase('ko-KR')).join(' ');
      return !search || pool.includes(search) || [...recipe.f, ...recipe.s, ...recipe.p].some((n) => D.canonical(n) === D.canonical(search));
    });
    visibleNames = visible.map((entry) => entry.recipe.name);
    const previous = selectedName;
    if (!visibleNames.includes(selectedName)) selectedName = visibleNames[0] || null;
    if (previous !== selectedName) detailOpen = false;
    const count = $('#umfAvailableCount');
    if (count) count.textContent = `재료 갖춘 메뉴 ${all.filter((entry) => entry.available).length} / 전체 ${all.length}`;
    const empty = $('#umfRecipeEmpty');
    if (empty) {
      empty.hidden = visible.length > 0;
      empty.textContent = filter === 'favorites'
        ? '이 조건에 맞는 즐겨찾기가 없어요. 메뉴의 하트를 눌러 저장해 보세요.'
        : filter === 'available'
          ? '필요한 재료를 모두 갖춘 메뉴가 아직 없어요. 전체 메뉴에서 부족한 재료를 확인해 주세요.'
          : '검색 결과가 없어요. 메뉴명이나 재료명을 짧게 입력해 주세요.';
    }
    const scrollTop = grid.scrollTop;
    grid.replaceChildren(...visible.map((entry) => renderCard(entry, favorites)));
    grid.scrollTop = scrollTop;
    renderSelection();
  }

  window.UMFRecipes = { catalog: C, getSelected: selected, getRanked: ranked, select, render };
  $('#umfRecipeFilter')?.addEventListener('change', render);
  $('#umfRecipeSearch')?.addEventListener('input', render);
  $('#umfRecipeBtn')?.addEventListener('click', () => {
    if (!selected()) return;
    detailOpen = !detailOpen;
    setDetailVisibility();
  });
  $('#umfShuffleBtn')?.addEventListener('click', () => {
    if (!visibleNames.length) return;
    const index = visibleNames.indexOf(selectedName);
    select(visibleNames[(index + 1) % visibleNames.length], { openDetail: true });
  });
  Store.subscribe(render);
  window.addEventListener('umf:daychange', render);
  render();
})();
