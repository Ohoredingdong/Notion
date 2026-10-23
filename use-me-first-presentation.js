/* Two presentations of the same kitchen; no separate data or feature model. */
(() => {
  'use strict';
  const body = document.body, $ = selector => document.querySelector(selector);
  const modes = ['app', 'widget'], sections = ['fridge', 'seasoning', 'inventory'];
  let mode = body.dataset.kitchenMode === 'widget' ? 'widget' : 'app', section = 'fridge';
  try {
    const requested = new URLSearchParams(window.location?.search || '').get('view');
    if (modes.includes(requested)) mode = requested;
  } catch (_) { /* The entry's default also works in detached previews. */ }
  function render() {
    body.dataset.kitchenMode = document.documentElement.dataset.kitchenMode = mode;
    body.dataset.kitchenWidgetSection = section;
    const switcher = $('[data-kitchen-mode-switch]');
    if (switcher) {
      switcher.textContent = mode === 'widget' ? '앱 보기' : '위젯 보기';
      switcher.setAttribute('aria-label', mode === 'widget' ? '같은 부엌을 앱 화면으로 보기' : '같은 부엌을 작은 위젯 화면으로 보기');
    }
    for (const button of document.querySelectorAll('[data-kitchen-widget-section]')) {
      button.setAttribute('aria-pressed', String(button.dataset.kitchenWidgetSection === section));
    }
  }
  function setMode(value) {
    if (!modes.includes(value)) return false;
    mode = value; render();
    try {
      const url = new URL(window.location.href); url.searchParams.set('view', mode);
      window.history.replaceState(null, '', url.href);
    } catch (_) { /* Storage-restricted and srcdoc hosts can still switch views. */ }
    window.dispatchEvent(new CustomEvent('umf:presentationchange', { detail: { mode, section } }));
    return true;
  }
  function showSection(value) {
    if (!sections.includes(value)) return false;
    window.UMFKitchenNav?.go(value === 'inventory' ? 'inventory' : 'home', { focus: false });
    section = value; render();
    window.scrollTo?.({ top: 0, behavior: 'instant' });
    window.dispatchEvent(new CustomEvent('umf:presentationchange', { detail: { mode, section } }));
    return true;
  }
  $('[data-kitchen-mode-switch]')?.addEventListener('click', () => setMode(mode === 'widget' ? 'app' : 'widget'));
  $('[data-kitchen-widget-add]')?.addEventListener('click', () => window.UMFCore?.openAdd());
  for (const button of document.querySelectorAll('[data-kitchen-widget-section]')) {
    button.addEventListener('click', () => showSection(button.dataset.kitchenWidgetSection));
  }
  window.addEventListener('umf:navigation', event => {
    if (event.detail?.page === 'home') section = event.detail.inventory ? 'inventory' : 'fridge';
    render();
  });
  window.UMFKitchenPresentation = { setMode, showSection, getMode: () => mode, getSection: () => section };
  render();
  window.UMFKitchen?.render();
})();
