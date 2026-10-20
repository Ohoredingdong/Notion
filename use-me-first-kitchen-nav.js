/* App navigation keeps the original inventory, recipe and diary DOM alive. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const views = ['home', 'recipes', 'diary', 'shopping'];
  const titles = {home:'umfHomeTitle',recipes:'umfRecipesTitle',diary:'umfDiaryTitle',shopping:'umfShoppingTitle'};
  const zones = {top:'냉장실 · 윗칸',middle:'냉장실 · 채소칸',bottom:'냉장실 · 밀폐 보관칸','freezer-top':'냉동실 · 윗칸','freezer-middle':'냉동실 · 가운데 칸','freezer-bottom':'냉동실 · 아랫칸',pantry:'실온 · 양념 선반'};
  let current = 'home';
  function focusTarget(element, scroll) {
    if (!element) return;
    if (scroll && typeof element.scrollIntoView === 'function') element.scrollIntoView({block:'start',behavior:'auto'});
    element.focus?.({preventScroll:true});
  }
  function go(requested, options = {}) {
    const inventory = requested === 'inventory';
    const next = inventory ? 'home' : views.includes(requested) ? requested : 'home';
    current = next;
    for (const page of document.querySelectorAll('[data-kitchen-view]')) page.hidden = page.dataset.kitchenView !== next;
    for (const button of document.querySelectorAll('.nav-btn[data-kitchen-page]')) {
      const active = button.dataset.kitchenPage === next;
      button.classList.toggle('active',active);
      if (active) button.setAttribute('aria-current','page');
      else button.removeAttribute('aria-current');
    }
    document.body.dataset.kitchenActivePage = next;
    if (options.history !== false && window.history?.replaceState) {
      try { window.history.replaceState(null,'','#' + (inventory ? 'inventory' : next)); } catch (_) {}
    }
    if (inventory) {
      $('#fridgeTab')?.click();
      const expand = $('#all');
      if (expand && !expand.hidden && expand.getAttribute('aria-expanded') === 'false') expand.click();
    }
    if (options.focus !== false) {
      if (inventory) focusTarget($('#inventoryTitle'),true);
      else { window.scrollTo?.({top:0,behavior:'auto'}); focusTarget(document.getElementById(titles[next]),false); }
    }
    window.dispatchEvent(new CustomEvent('umf:navigation',{detail:{page:next,inventory}}));
    return next;
  }
  for (const placeholder of document.querySelectorAll('[data-kitchen-icon]')) {
    if (window.UMFKitchenArt) placeholder.innerHTML = window.UMFKitchenArt.icon(placeholder.dataset.kitchenIcon);
  }
  const rail = $('.widget-control-rail'), target = $('#umfKitchenTools');
  if (rail && target) target.appendChild(rail);
  function placementLabels() {
    const K = window.UMFKitchenState;
    if (!K) return;
    for (const row of document.querySelectorAll('#list .row[data-id]')) {
      const parent = row.querySelector('.ex');
      if (!parent) continue;
      let label = parent.querySelector('.kitchen-location');
      if (!label) { label = document.createElement('button'); label.type = 'button'; label.className = 'kitchen-location'; parent.appendChild(label); }
      label.dataset.kitchenArrange = row.dataset.id;
      label.textContent = (zones[K.zoneFor(row.dataset.id)] || zones.middle) + ' ↗';
      label.setAttribute('aria-label',(row.querySelector('.nm')?.textContent || '재료') + ' 보관 위치 바꾸기');
    }
  }
  function showError() {
    const box = $('#umfKitchenError');
    if (!box) return;
    box.textContent = window.UMFKitchenState?.error || '';
    box.hidden = !box.textContent;
  }
  document.addEventListener('click', event => {
    const button = event.target.closest?.('button[data-kitchen-page],a[data-kitchen-page]');
    if (button) { event.preventDefault(); go(button.dataset.kitchenPage); }
    const arranging = event.target.closest?.('[data-kitchen-arrange]');
    if (arranging) { event.preventDefault(); window.UMFKitchen?.arrangeItem(arranging.dataset.kitchenArrange); }
    const help = event.target.closest?.('[data-kitchen-help]');
    if (help) { const panel = $('#umfKitchenHelp'); if (panel) { panel.open = true; focusTarget(panel.querySelector('summary'),true); } }
    if (!event.target.closest?.('.kitchen-settings')) $('#umfKitchenSettings')?.removeAttribute('open');
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !$('#umfKitchenSettings')?.open) return;
    $('#umfKitchenSettings').open = false;
    focusTarget($('#umfKitchenSettings summary'),false);
  });
  window.addEventListener('hashchange', () => go((window.location?.hash || '').slice(1),{history:false}));
  window.addEventListener('umf:kitchenerror',showError);
  window.addEventListener('umf:kitchenchange',() => { placementLabels();showError(); });
  window.UMFStore?.subscribe(placementLabels);
  // Inventory expands independently of store changes.
  $('#all')?.addEventListener('click',placementLabels);
  window.UMFKitchenNav = {go,getPage:() => current,refresh:placementLabels};
  go((window.location?.hash || '').slice(1),{focus:false,history:false});
  Promise.all([window.UMFStore?.ready,window.UMFKitchenState?.ready]).then(() => {placementLabels();showError();});
})();
