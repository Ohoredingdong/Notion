'use strict';
// DOM integration only: executes the published scripts and user events, without
// claiming browser layout, CSS, network or cross-device end-to-end verification.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const { locks: nodeLocks } = require('node:worker_threads');
const { parseHTML } = require(process.env.FRIDGE_TEST_DOM || 'linkedom');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'use-me-first.html'), 'utf8');
const STATE = 'use-me-first-state-v5';
const nativeDate = Date;
const seedTime = nativeDate.parse('2026-10-20T12:00:00Z');

async function boot(options = {}) {
  const { window: dom } = parseHTML(html);
  const document = dom.document;
  const memory = options.memory || new Map();
  for (const [key, value] of Object.entries(options.seed || {})) memory.set(key, JSON.stringify(value));
  const errors = [], requests = [], observers = [], timers = new Map();
  let sequence = 0, currentTime = seedTime, focused = null;
  class TestDate extends nativeDate {
    constructor(...args) { super(...(args.length ? args : [currentTime])); }
    static now() { return currentTime; }
  }
  const storage = {
    getItem(key) { if (options.storageDenied) throw new Error('Test storage denied'); return memory.get(key) ?? null; },
    setItem(key, value) { if (options.storageDenied) throw new Error('Test storage denied'); memory.set(key, String(value)); },
    removeItem(key) { if (options.storageDenied) throw new Error('Test storage denied'); memory.delete(key); }
  };
  const pendingLocks = new Set();
  const navigator = { clipboard: { async writeText() {} }, locks: options.locks === false ? undefined : {
    request(...args) {
      const pending = (options.locks || nodeLocks).request(...args);
      pendingLocks.add(pending);
      pending.then(() => pendingLocks.delete(pending), () => pendingLocks.delete(pending));
      return pending;
    }
  } };
  const w = {
    navigator, document, localStorage: storage, crypto: webcrypto, CustomEvent: dom.CustomEvent,
    confirm: () => true,
    addEventListener: dom.addEventListener.bind(dom),
    removeEventListener: dom.removeEventListener.bind(dom),
    dispatchEvent: dom.dispatchEvent.bind(dom)
  };
  // Linkedom does not model the browser's default selected option or focus.
  const selectPrototype = Object.getPrototypeOf(document.querySelector('select'));
  const ownValue = Object.getOwnPropertyDescriptor(selectPrototype, 'value');
  if (!ownValue?.set) Object.defineProperty(selectPrototype, 'value', {
    configurable: true,
    get() { return (this.querySelector('option[selected]') || this.querySelector('option'))?.value || ''; },
    set(value) {
      for (const option of this.querySelectorAll('option')) option.removeAttribute('selected');
      const selected = [...this.querySelectorAll('option')].find(option => option.value === String(value));
      if (selected) selected.setAttribute('selected', '');
    }
  });
  Object.defineProperty(document, 'activeElement', { configurable: true, get: () => focused || document.body });
  for (const element of document.querySelectorAll('button,input,select,textarea,[tabindex],summary,a[href]')) element.focus = () => { focused = element; };
  class TestMutationObserver {
    constructor(callback) { this.observer = new dom.MutationObserver(callback); observers.push(this); }
    observe(...args) { this.observer.observe(...args); }
    disconnect() { this.observer.disconnect(); }
  }
  const sandbox = {
    window: w, document, localStorage: storage, crypto: webcrypto, Date: TestDate,
    console: { log() {}, warn() {}, error(...args) { errors.push(args.map(String).join(' ')); } },
    location: { pathname: '/use-me-first.html' },
    navigator,
    matchMedia: () => ({ matches: false }),
    ResizeObserver: class { observe() {} disconnect() {} },
    MutationObserver: TestMutationObserver,
    CustomEvent: dom.CustomEvent, Event: dom.Event, Node: dom.Node,
    setTimeout(callback, ms) { timers.set(++sequence, { callback, ms }); return sequence; },
    clearTimeout(id) { timers.delete(id); },
    AbortController, TextEncoder, TextDecoder,
    async fetch(url, init = {}) { requests.push({ url, method: init.method || 'GET' }); throw new Error('Test network disabled'); }
  };
  const context = vm.createContext(sandbox);
  for (const script of document.querySelectorAll('script[src]')) {
    const filename = script.getAttribute('src').split('?')[0];
    vm.runInContext(fs.readFileSync(path.join(root, filename), 'utf8'), context, { filename });
  }
  const api = {
    w, document, memory, errors, requests,
    $(selector) { const el = document.querySelector(selector); assert.ok(el, 'Missing DOM element: ' + selector); return el; },
    async click(selector) { const element = typeof selector === 'string' ? api.$(selector) : selector; assert.ok(element); assert.notEqual(element.disabled, true, 'Attempt to click disabled button'); element.click(); await api.flush(); },
    fill(selector, value, event = 'input') { const element = api.$(selector); element.value = value; element.dispatchEvent(new dom.Event(event, { bubbles: true })); },
    choose(selector, value) { api.fill(selector, value, 'change'); },
    async selectRecipe(name) { const card = [...document.querySelectorAll('.umf-menu-card')].find(x => x.dataset.name === name); assert.ok(card, name + ' should be visible'); await api.click(card.querySelector('.umf-menu-select')); },
    card(name) { return [...document.querySelectorAll('.umf-menu-card')].find(x => x.dataset.name === name); },
    async add(name, quantity = '', expiry = '') { await api.click('#umfTopAdd'); api.fill('#name', name); api.fill('#umfQty', quantity); api.fill('#expiry', expiry); await api.click('#save'); },
    async toggle(selector, name) { const button = [...document.querySelectorAll(selector + ' .tog')].find(x => x.textContent.replace(/^✓ /, '') === name); assert.ok(button, 'Missing stock button: ' + name); await api.click(button); },
    async menu(id, action) { const row = [...document.querySelectorAll('#list .row')].find(x => x.dataset.id === id); assert.ok(row); await api.click(row.querySelector('.rm')); await api.click(row.querySelector('[data-action="' + action + '"]')); },
    advance(ms) { currentTime += ms; },
    storageEvent() { const event = new dom.Event('storage'); event.key = STATE; event.newValue = memory.get(STATE) || null; w.dispatchEvent(event); },
    async flush() {
      for (let i = 0; i < 3; i++) {
        await new Promise(setImmediate);
        await Promise.allSettled([...pendingLocks]);
      }
    },
    close() { w.UMFKitchen?.destroy(); w.UMFKitchenState?.destroy(); w.UMFCore?.sync.destroy(); w.UMFStore?.destroy(); observers.forEach(x => x.disconnect()); timers.clear(); assert.deepEqual(errors, [], 'No application exceptions should be logged'); }
  };
  await Promise.all([w.UMFStore.ready, w.UMFKitchenState?.ready, w.UMFKitchen?.ready]);
  await api.flush();
  return api;
}
async function readyRice(t, options) {
  const app = await boot(options); t.after(() => app.close());
  await app.add('달걀', '2개', '2099-01-01'); await app.add('양파', '1개', '2099-01-01');
  await app.toggle('#sg', '식용유'); await app.toggle('#sg', '간장'); await app.toggle('#pg', '밥/즉석밥');
  await app.selectRecipe('계란 볶음밥'); return app;
}
async function whileStoreLocked(action) {
  let release, acquired;
  const gate = new Promise(resolve => { release = resolve; });
  const entered = new Promise(resolve => { acquired = resolve; });
  const holding = nodeLocks.request(STATE + ':transaction', { mode: 'exclusive' }, async () => {
    acquired(); await gate;
  });
  await entered;
  try { await action(); } finally { release(); await holding; }
}

test('HTML identifiers are unique and all local script dependencies are ordered and versioned', () => {
  const { document } = parseHTML(html);
  const ids = [...document.querySelectorAll('[id]')].map(x => x.id);
  assert.equal(new Set(ids).size, ids.length);
  const sources = [...document.querySelectorAll('script[src]')].map(x => x.getAttribute('src'));
  assert.match(sources[0], /^use-me-first-domain\.js\?v=/);
  assert.match(sources[1], /^use-me-first-store\.js\?v=/);
  for (const src of sources) { assert.match(src, /\?v=.+/); assert.ok(fs.existsSync(path.join(root, src.split('?')[0]))); }
});

test('all scripts boot together with empty stock and no fabricated food or nutrition counts', async t => {
  const app = await boot(); t.after(() => app.close());
  assert.equal(app.w.UMFStore.concurrency, 'web-locks');
  assert.equal(app.w.UMFStore.getState().items.length, 0);
  assert.equal(app.$('#fc').textContent, '0');
  assert.equal(app.$('#umfPossibleCount').textContent, '0개');
  assert.equal(app.$('#umfSoonCount').textContent, '0개');
  for (const el of app.document.querySelectorAll('[data-balance-pct]')) assert.equal(el.textContent, '0종');
  assert.equal(app.document.querySelectorAll('.umf-menu-card').length, 8);
  assert.equal(app.$('#umfLogBtn').disabled, true);
  assert.equal(app.document.querySelectorAll('#umfRecipeGrid img').length, 0);
  assert.equal(app.requests.length, 0);
});

test('same-name stock keeps independent quantities, optional dates, editing and deletion by ID', async t => {
  const app = await boot(); t.after(() => app.close());
  await app.add('계란', '2개'); await app.add('계란', '7개', '2099-01-02');
  let items = app.w.UMFStore.getState().items;
  assert.equal(items.length, 2); assert.notEqual(items[0].id, items[1].id);
  assert.equal(items[0].expiry, ''); assert.equal(items[0].quantity, '2개'); assert.equal(items[1].quantity, '7개');
  const firstId = items[0].id, secondId = items[1].id;
  await app.menu(firstId, 'edit'); app.fill('#umfQty', '3개'); await app.click('#save');
  items = app.w.UMFStore.getState().items;
  assert.equal(items.find(x => x.id === firstId).quantity, '3개'); assert.equal(items.find(x => x.id === secondId).quantity, '7개');
  await app.menu(secondId, 'remove');
  assert.equal(app.w.UMFStore.getState().items.length, 1);
  assert.match(app.$('#list').textContent, /3개/); assert.doesNotMatch(app.$('#list').textContent, /7개/);
});

test('invalid inputs preserve stored stock and special characters cannot insert markup', async t => {
  const app = await boot(); t.after(() => app.close());
  await app.click('#openAdd'); await app.click('#save');
  assert.match(app.$('#umfFormError').textContent, /재료명/); assert.equal(app.w.UMFStore.getState().items.length, 0);
  app.fill('#name', '계란'); app.fill('#umfQty', '-2개'); await app.click('#save');
  assert.match(app.$('#umfFormError').textContent, /0 이상/); assert.equal(app.w.UMFStore.getState().items.length, 0);
  app.fill('#umfQty', '2개'); app.fill('#expiry', '2026-02-30'); await app.click('#save');
  assert.match(app.$('#umfFormError').textContent, /올바른 날짜/); assert.equal(app.w.UMFStore.getState().items.length, 0);
  app.fill('#name', '<img src=x onerror=alert(1)>'); app.fill('#expiry', ''); await app.click('#save');
  assert.equal(app.document.querySelectorAll('#list img').length, 0);
  assert.equal(app.$('#list .nm').textContent, '<img src=x onerror=alert(1)>');
});

test('Korean IME confirmation does not submit stock or custom ingredients before composition ends', async t => {
  const app = await boot(); t.after(() => app.close());
  async function enter(selector, properties = {}) {
    const event = new app.w.CustomEvent('keydown', { bubbles: true, cancelable: true });
    Object.assign(event, { key: 'Enter', keyCode: 13, isComposing: false }, properties);
    app.$(selector).dispatchEvent(event);
    await app.flush();
  }
  await app.click('#openAdd'); app.fill('#name', '달걀'); app.fill('#umfQty', '2개');
  await enter('#name', { isComposing: true });
  await enter('#umfQty', { keyCode: 229 });
  assert.equal(app.w.UMFStore.getState().items.length, 0);
  assert.equal(app.$('#mb').classList.contains('on'), true);
  await enter('#name');
  assert.equal(app.w.UMFStore.getState().items.length, 1);
  assert.equal(app.w.UMFStore.getState().items[0].name, '달걀');
  assert.equal(app.$('#mb').classList.contains('on'), false);
  await app.click('#seasonTab'); await app.click('#addSeason'); app.fill('#customName', '굴소스');
  await enter('#customName', { isComposing: true });
  await enter('#customName', { keyCode: 229 });
  assert.equal(app.w.UMFStore.getState().season.includes('굴소스'), false);
  assert.equal(app.$('#customModal').classList.contains('on'), true);
  await enter('#customName');
  assert.equal(app.w.UMFStore.getState().season.includes('굴소스'), true);
  assert.equal(app.$('#customModal').classList.contains('on'), false);
});

test('recipe availability, shortage list and meal button agree for expired and zero stock', async t => {
  const app = await readyRice(t); const id = app.w.UMFStore.getState().items.find(x => x.name === '달걀').id;
  assert.equal(app.card('계란 볶음밥').dataset.available, 'true');
  await app.menu(id, 'edit'); app.fill('#expiry', '2000-01-01'); await app.click('#save');
  assert.equal(app.card('계란 볶음밥').dataset.available, 'false'); assert.equal(app.$('#umfLogBtn').disabled, true);
  assert.match(app.$('#umfMissingList').textContent, /소비기한 경과/);
  await app.menu(id, 'edit'); app.fill('#expiry', '2099-01-01'); app.fill('#umfQty', '0개'); await app.click('#save');
  assert.equal(app.card('계란 볶음밥').dataset.available, 'false'); assert.match(app.$('#umfMissingList').textContent, /소진/);
  await app.menu(id, 'edit'); app.fill('#umfQty', '2개'); await app.click('#save');
  assert.equal(app.card('계란 볶음밥').dataset.available, 'true'); assert.equal(app.$('#umfLogBtn').disabled, false);
  assert.equal(app.$('#umfMissingCount').textContent, '0개');
});

test('the UI accepts egg aliases but rejects ingredient names embedded in another product', async t => {
  const app = await readyRice(t); const id = app.w.UMFStore.getState().items.find(x => x.name === '달걀').id;
  assert.equal(app.card('계란 볶음밥').dataset.available, 'true');
  await app.menu(id, 'edit'); app.fill('#name', '무계란빵'); await app.click('#save');
  assert.equal(app.card('계란 볶음밥').dataset.available, 'false'); assert.match(app.$('#umfMissingList').textContent, /계란/);
  await app.menu(id, 'edit'); app.fill('#name', '계란'); await app.click('#save'); assert.equal(app.card('계란 볶음밥').dataset.available, 'true');
});

test('shortage plus routes seasonings and pantry into the correct confirmation dialog', async t => {
  const app = await boot(); t.after(() => app.close()); await app.add('달걀', '2개'); await app.add('양파', '1개'); await app.toggle('#sg', '식용유'); await app.selectRecipe('계란 볶음밥');
  await app.click('#umfMissingList [data-name="간장"]'); assert.equal(app.$('#customType').value, 'season'); assert.equal(app.$('#customName').value, '간장');
  assert.equal(app.w.UMFStore.getState().season.includes('간장'), false); await app.click('#customSave');
  assert.equal(app.w.UMFStore.getState().season.includes('간장'), true); assert.equal(app.w.UMFStore.getState().items.length, 2);
  await app.click('#umfMissingList [data-kind="pantry"]'); assert.equal(app.$('#customType').value, 'pantry'); await app.click('#customSave');
  assert.equal(app.w.UMFStore.getState().pantry.includes('밥/즉석밥'), true); assert.equal(app.card('계란 볶음밥').dataset.available, 'true');
});

test('custom seasoning and pantry controls work and quantities remain unrelated to those sets', async t => {
  const app = await boot(); t.after(() => app.close()); await app.click('#seasonTab');
  assert.equal(app.$('#seasonTab').getAttribute('aria-selected'), 'true'); assert.equal(app.$('#season').classList.contains('on'), true);
  await app.click('#addSeason'); app.fill('#customName', '굴소스'); await app.click('#customSave');
  await app.click('#addPantry'); app.fill('#customName', '오트밀'); await app.click('#customSave');
  const st = app.w.UMFStore.getState(); assert.equal(st.customSeason.includes('굴소스'), true); assert.equal(st.customPantry.includes('오트밀'), true);
  assert.equal(st.season.includes('굴소스'), true); assert.equal(st.pantry.includes('오트밀'), true); assert.equal(st.items.length, 0);
  const remove = [...app.document.querySelectorAll('#sg .umf-custom-remove')].find(x => x.getAttribute('aria-label') === '굴소스 항목 삭제'); await app.click(remove);
  assert.equal(app.w.UMFStore.getState().season.includes('굴소스'), false);
});

test('filters and search clear hidden selection and disable unavailable actions', async t => {
  const app = await readyRice(t);
  app.choose('#umfRecipeFilter', 'available'); assert.equal(app.document.querySelectorAll('.umf-menu-card').length, 1);
  app.fill('#umfRecipeSearch', '달걀'); assert.equal(app.document.querySelectorAll('.umf-menu-card').length, 1);
  app.fill('#umfRecipeSearch', '존재하지 않는 음식'); assert.equal(app.document.querySelectorAll('.umf-menu-card').length, 0);
  assert.equal(app.w.UMFRecipes.getSelected(), null); assert.equal(app.$('#umfRecipeEmpty').hidden, false);
  assert.equal(app.$('#umfRecipeBtn').disabled, true); assert.equal(app.$('#umfLogBtn').disabled, true); assert.equal(app.$('#umfMissingCount').textContent, '0개');
  app.fill('#umfRecipeSearch', ''); assert.equal(app.w.UMFRecipes.getSelected().recipe.name, '계란 볶음밥');
});

test('recipe details stay expanded when an unrelated stock or favorite changes', async t => {
  const app = await readyRice(t);
  assert.equal(app.$('#umfRecipeDetail').classList.contains('on'), true);
  assert.equal(app.$('#umfRecipeBtn').getAttribute('aria-expanded'), 'true');
  await app.add('오이', '1개'); assert.equal(app.$('#umfRecipeDetail').classList.contains('on'), true);
  await app.click(app.card('계란 볶음밥').querySelector('.umf-fav')); assert.equal(app.$('#umfRecipeDetail').classList.contains('on'), true);
  assert.match(app.$('#umfRecipeDetail').textContent, /1인분/); assert.match(app.$('#umfRecipeDetail').textContent, /실제|직접/);
  await app.click('#umfRecipeBtn'); assert.equal(app.$('#umfRecipeDetail').classList.contains('on'), false);
  await app.add('당근', '1개'); assert.equal(app.$('#umfRecipeDetail').classList.contains('on'), false);
});

test('favorites survive a reload and removing the filtered favorite clears selection', async t => {
  const memory = new Map(); const first = await boot({ memory });
  await first.selectRecipe('계란 볶음밥'); await first.click(first.card('계란 볶음밥').querySelector('.umf-fav')); first.close();
  const app = await boot({ memory }); t.after(() => app.close()); app.choose('#umfRecipeFilter', 'favorites');
  assert.equal(app.document.querySelectorAll('.umf-menu-card').length, 1); assert.equal(app.card('계란 볶음밥').querySelector('.umf-fav').getAttribute('aria-pressed'), 'true');
  await app.click(app.card('계란 볶음밥').querySelector('.umf-fav'));
  assert.equal(app.document.querySelectorAll('.umf-menu-card').length, 0); assert.equal(app.w.UMFRecipes.getSelected(), null);
});

test('meal logging avoids double clicks, shows more than three entries, and supports cancel and undo', async t => {
  const app = await readyRice(t); await app.click('#umfLogBtn'); await app.click('#umfLogBtn');
  assert.equal(app.w.UMFStore.getState().meals.length, 1);
  for (let n = 0; n < 3; n++) { app.advance(1000); await app.click('#umfLogBtn'); }
  assert.equal(app.document.querySelectorAll('.meal-item').length, 4);
  assert.equal(app.w.UMFStore.getState().items.find(x => x.name === '달걀').quantity, '2개');
  await app.click('.meal-remove'); assert.equal(app.w.UMFStore.getState().meals.length, 3); assert.equal(app.$('#umfUndoMeal').hidden, false);
  await app.click('#umfUndoMeal'); assert.equal(app.w.UMFStore.getState().meals.length, 4); assert.equal(app.document.querySelectorAll('.meal-item').length, 4);
});

test('full history exposes old meals while clearing today preserves other dates', async t => {
  const oldTs = seedTime - 86400000;
  const app = await readyRice(t, { seed: { 'use-me-first-meal-log-v1': [{ name: '어제 메뉴', ts: oldTs, day: '2026-10-19' }] } });
  assert.equal(app.document.querySelectorAll('.meal-item').length, 0); await app.click('#umfLogBtn');
  app.choose('#umfMealScope', 'all'); assert.equal(app.document.querySelectorAll('.meal-item').length, 2);
  await app.click('#umfClearMeals'); assert.equal(app.w.UMFStore.getState().meals.length, 1); assert.match(app.$('#umfMealList').textContent, /어제 메뉴/);
  await app.click('#umfUndoMeal'); assert.equal(app.w.UMFStore.getState().meals.length, 2);
});

test('blocked storage boots without exceptions, refuses false saves, and leaves display controls usable', async t => {
  const app = await boot({ storageDenied: true }); t.after(() => app.close());
  assert.equal(app.$('#umfStorageStatus').hidden, false); assert.match(app.$('#umfStorageStatus').textContent, /저장/);
  await app.add('계란', '2개'); assert.equal(app.w.UMFStore.getState().items.length, 0); assert.equal(app.$('#mb').classList.contains('on'), true);
  assert.match(app.$('#umfFormError').textContent, /저장/);
  await app.click('#widgetThemeControl'); assert.equal(app.document.documentElement.dataset.widgetTheme, 'dark');
  await app.click('#widgetSizeControl'); assert.equal(app.document.documentElement.dataset.widgetSize, 'large');
  await app.click('#widgetResetControl'); assert.equal(app.document.documentElement.dataset.widgetSize, 'normal');
});

test('legacy quantities and favorites display after migration without deleting their originals', async t => {
  const app = await boot({ seed: { 'use-me-first-v4': [{name:'계란',expiry:'2099-01-01'},{name:'계란',expiry:'2099-02-01'}], 'use-me-first-quantities-v1': {'계란':'5개'}, 'use-me-first-favorites-v1':['계란 볶음밥'] } }); t.after(() => app.close());
  const st = app.w.UMFStore.getState(); assert.equal(st.items[0].quantity, '5개'); assert.equal(st.items[1].quantity, '');
  assert.ok(app.memory.has('use-me-first-v4')); assert.ok(app.memory.has('use-me-first-quantities-v1'));
  assert.match(app.$('#list').textContent, /5개/); assert.match(app.$('#list').textContent, /수량 미입력/);
  app.choose('#umfRecipeFilter','favorites'); assert.equal(app.document.querySelectorAll('.umf-menu-card').length,1);
});

test('two actual DOM sessions preserve both additions even before the second tab receives its storage event', async t => {
  const memory = new Map(), a = await boot({memory}), b = await boot({memory}); t.after(() => { a.close(); b.close(); });
  await a.add('달걀','2개'); await b.add('양파','1개'); a.storageEvent(); b.storageEvent();
  assert.equal(a.w.UMFStore.getState().items.length,2); assert.equal(b.w.UMFStore.getState().items.length,2);
  assert.match(a.$('#list').textContent,/달걀/); assert.match(a.$('#list').textContent,/양파/); assert.equal(b.document.querySelectorAll('#list .row').length,2);
});

test('local midnight refresh updates expiry, available menu count and the visible day', async t => {
  const app = await readyRice(t); const item = app.w.UMFStore.getState().items.find(x=>x.name==='달걀');
  await app.menu(item.id,'edit'); app.fill('#expiry','2026-10-20'); await app.click('#save');
  assert.equal(app.$('#umfSoonCount').textContent,'1개'); const dateBefore=app.$('#umfDateMain').textContent;
  app.advance(86400000); app.w.dispatchEvent(new app.w.CustomEvent('focus'));
  assert.notEqual(app.$('#umfDateMain').textContent,dateBefore); assert.match(app.$('#list').textContent,/기한 경과/);
  assert.equal(app.card('계란 볶음밥').dataset.available,'false'); assert.equal(app.$('#umfSoonCount').textContent,'0개');
});

test('a failed sync request shows failure without saving a new code or sending a real request', async t => {
  const app = await boot(); t.after(()=>app.close()); await app.click('#syncBtn'); await app.click('#syncCreate'); await app.flush();
  assert.match(app.$('#syncFeedback').textContent,/실패|연결/); assert.equal(app.memory.has('use-me-first-sync-code-v1'),false);
  assert.equal(app.$('#syncDot').classList.contains('bad'),true); assert.ok(app.requests.length>=1);
  assert.equal(app.$('#syncCreate').disabled,false);
});

test('held Web Locks preserve captured stock and custom input, reject double saves, and keep a newer dialog open', async t => {
  const app = await boot(); t.after(() => app.close());
  await app.click('#openAdd'); app.fill('#name', '달걀'); app.fill('#umfQty', '2개');
  await whileStoreLocked(async () => {
    app.$('#save').click(); app.$('#save').click();
    assert.equal(app.$('#save').disabled, true);
    assert.equal(app.w.UMFStore.getState().items.length, 0);
    app.$('#cancel').click(); app.$('#openAdd').click();
    app.fill('#name', '양파'); app.fill('#umfQty', '1개');
    await new Promise(setImmediate);
  });
  await app.flush();
  assert.equal(app.w.UMFStore.getState().items.length, 1);
  assert.equal(app.w.UMFStore.getState().items[0].name, '달걀');
  assert.equal(app.$('#mb').classList.contains('on'), true);
  assert.equal(app.$('#name').value, '양파');
  await app.click('#save'); assert.equal(app.w.UMFStore.getState().items.length, 2);
  await app.click('#seasonTab'); await app.click('#addSeason'); app.fill('#customName', '굴소스');
  await whileStoreLocked(async () => {
    app.$('#customSave').click(); app.$('#customSave').click();
    app.$('#customClose').click(); app.$('#addPantry').click(); app.fill('#customName', '오트밀');
    await new Promise(setImmediate);
  });
  await app.flush();
  assert.equal(app.w.UMFStore.getState().season.filter(x => x === '굴소스').length, 1);
  assert.equal(app.$('#customModal').classList.contains('on'), true);
  assert.equal(app.$('#customType').value, 'pantry'); assert.equal(app.$('#customName').value, '오트밀');
  await app.click('#customSave'); assert.equal(app.w.UMFStore.getState().pantry.includes('오트밀'), true);
});

test('queued meal and favorite actions use current transaction state and reject duplicate or newly unavailable meals', async t => {
  const app = await readyRice(t);
  await whileStoreLocked(async () => {
    app.$('#umfLogBtn').click(); app.$('#umfLogBtn').click();
    assert.equal(app.$('#umfLogBtn').disabled, true);
    assert.equal(app.w.UMFStore.getState().meals.length, 0);
    await new Promise(setImmediate);
  });
  await app.flush(); assert.equal(app.w.UMFStore.getState().meals.length, 1);
  app.advance(1000); let changed;
  await whileStoreLocked(async () => {
    changed = app.w.UMFStore.updateAsync(st => { st.items.find(x => x.name === '달걀').quantity = '0개'; });
    await new Promise(setImmediate);
    app.$('#umfLogBtn').click(); app.$('#umfLogBtn').click();
  });
  await changed; await app.flush();
  assert.equal(app.w.UMFStore.getState().meals.length, 1);
  assert.equal(app.card('계란 볶음밥').dataset.available, 'false');
  assert.match(app.$('#umfMealFeedback').textContent, /재료가 바뀌었어요/);
  await whileStoreLocked(async () => {
    const button = app.card('계란 볶음밥').querySelector('.umf-fav');
    button.click(); button.click(); await new Promise(setImmediate);
  });
  await app.flush();
  assert.equal(app.w.UMFStore.getState().favorites.includes('계란 볶음밥'), false);
});

const KITCHEN_VIEW = 'use-me-first-kitchen-view-v1';
const kitchenItem = (id, name, quantity = '1개', expiry = '2099-01-01') => ({ id, name, quantity, expiry });
function existingFridge(items, extras = {}) {
  return {
    version: 5, revision: 7, updatedAt: seedTime, items,
    season: [], pantry: [], customSeason: [], customPantry: [], meals: [], favorites: [],
    ...extras
  };
}
function assertKitchenPage(app, page) {
  const visible = [...app.document.querySelectorAll('[data-kitchen-view]')].filter(node => !node.hidden);
  assert.deepEqual(visible.map(node => node.dataset.kitchenView), [page], 'Exactly one application page is visible');
  assert.equal(app.w.UMFKitchenNav.getPage(), page);
  const active = [...app.document.querySelectorAll('.nav-btn[data-kitchen-page][aria-current="page"]')];
  assert.deepEqual(active.map(node => node.dataset.kitchenPage), [page], 'The active navigation item matches the visible page');
}
function shelfItem(app, id) {
  const button = [...app.document.querySelectorAll('#umfKitchenScene .fridge-food')].find(node => node.dataset.lot === id);
  assert.ok(button, 'The actual inventory lot is visible on a shelf: ' + id);
  return button;
}

test('kitchen navigation shows one of four pages and inventory opens the complete real stock list', async t => {
  const items = ['계란', '양파', '당근', '감자', '우유', '두부', '대파', '버섯'].map((name, index) => kitchenItem('route-' + index, name));
  const app = await boot({ seed: { [STATE]: existingFridge(items) } }); t.after(() => app.close());
  const ids = [...app.document.querySelectorAll('[id]')].map(node => node.id);
  assert.equal(new Set(ids).size, ids.length, 'Generated scene elements also have unique IDs');
  assert.equal(app.document.querySelectorAll('[data-kitchen-view]').length, 4);
  assertKitchenPage(app, 'home');
  for (const page of ['recipes', 'diary', 'shopping', 'home']) {
    await app.click('.nav-btn[data-kitchen-page="' + page + '"]');
    assertKitchenPage(app, page);
  }
  await app.click('#all');
  assert.equal(app.document.querySelectorAll('#list .row').length, 6);
  await app.click('#seasonTab');
  await app.click('.nav-btn[data-kitchen-page="shopping"]');
  app.w.UMFKitchenNav.go('inventory'); await app.flush();
  assertKitchenPage(app, 'home');
  assert.equal(app.$('#fridgeTab').getAttribute('aria-selected'), 'true');
  assert.equal(app.$('#fridge').classList.contains('on'), true);
  assert.equal(app.$('#all').getAttribute('aria-expanded'), 'true');
  assert.equal(app.document.querySelectorAll('#list .row').length, items.length);
  assert.equal(app.document.activeElement, app.$('#inventoryTitle'));
});

test('kitchen ordinary recipe and modal clicks do not navigate again or steal input focus', async t => {
  const app = await boot(); t.after(() => app.close());
  await app.click('.nav-btn[data-kitchen-page="recipes"]');
  const navigation = [];
  app.w.addEventListener('umf:navigation', event => navigation.push(event.detail));
  await app.selectRecipe('계란 볶음밥');
  assertKitchenPage(app, 'recipes');
  assert.equal(navigation.length, 0, 'Selecting a recipe is not an application navigation action');
  await app.click('.nav-btn[data-kitchen-page="home"]');
  navigation.length = 0;
  await app.click('#umfTopAdd');
  app.$('#name').focus(); await app.click('#name');
  assert.equal(app.$('#mb').classList.contains('on'), true);
  assert.equal(app.document.activeElement, app.$('#name'));
  assert.equal(navigation.length, 0, 'Opening a form or clicking its input must not route through the body element');
});

test('kitchen doors open independently and a closed compartment cannot open a stock editor', async t => {
  const items = [kitchenItem('frozen-egg', '계란', '2개'), kitchenItem('fresh-onion', '양파')];
  const app = await boot({ seed: {
    [STATE]: existingFridge(items),
    [KITCHEN_VIEW]: { version: 1, doors: { freezer: false, fridge: false }, placements: { 'frozen-egg': 'freezer-top' } }
  } }); t.after(() => app.close());
  const before = app.memory.get(STATE);
  assert.equal(app.$('#inside-freezer').hasAttribute('inert'), true);
  assert.equal(app.$('#inside-fridge').getAttribute('aria-hidden'), 'true');
  await app.click('#umfKitchenScene .fridge-door[data-compartment="freezer"]');
  assert.equal(app.$('#inside-freezer').hasAttribute('inert'), false);
  assert.equal(app.$('#inside-freezer').getAttribute('aria-hidden'), 'false');
  assert.equal(app.$('#inside-fridge').hasAttribute('inert'), true);
  assert.equal(app.w.UMFKitchenState.getState().doors.fridge, false);
  await app.click('#umfKitchenScene .compartment-toggle[data-compartment="fridge"]');
  await app.click('#umfKitchenScene .compartment-toggle[data-compartment="freezer"]');
  assert.equal(app.w.UMFKitchenState.getState().doors.freezer, false);
  assert.equal(app.w.UMFKitchenState.getState().doors.fridge, true);
  assert.equal(app.$('#inside-freezer').hasAttribute('inert'), true);
  assert.equal(app.$('#inside-fridge').hasAttribute('inert'), false);
  const frozen = shelfItem(app, 'frozen-egg');
  assert.equal(frozen.disabled, true);
  frozen.click(); await app.flush();
  assert.equal(app.$('#mb').classList.contains('on'), false, 'A synthetic click cannot bypass a closed door');
  await app.click(shelfItem(app, 'fresh-onion'));
  assert.equal(app.$('#mb').classList.contains('on'), true);
  assert.equal(app.$('#name').value, '양파');
  assert.equal(app.memory.get(STATE), before, 'Opening doors and inspecting stock never changes inventory');
});

test('kitchen tap and drag arranging preserve same-name lot IDs, quantities and saved shelf positions', async t => {
  const firstId = 'lot" data-injected="yes', secondId = 'other-egg';
  const saved = existingFridge([kitchenItem(firstId, '계란', '2개'), kitchenItem(secondId, '계란', '7개')]);
  const memory = new Map([[STATE, JSON.stringify(saved)]]);
  const app = await boot({ memory }); t.after(() => app.close());
  const before = memory.get(STATE);
  await app.click('#umfKitchenScene [data-action="organize"]');
  assert.equal(app.w.UMFKitchenState.getState().doors.freezer, true);
  assert.equal(app.w.UMFKitchenState.getState().doors.fridge, true);
  await app.click(shelfItem(app, firstId));
  assert.equal(app.w.UMFKitchen.getMovingId(), firstId);
  await app.click('#umfKitchenScene .kitchen-zone-controls [data-zone="freezer-bottom"]');
  assert.equal(app.w.UMFKitchenState.zoneFor(firstId), 'freezer-bottom');
  assert.equal(app.w.UMFKitchenState.zoneFor(secondId), 'middle');
  assert.equal(shelfItem(app, firstId).closest('.shelf').dataset.zone, 'freezer-bottom');
  assert.equal(shelfItem(app, firstId).querySelector('.quantity-mini').textContent, '2개');
  assert.equal(shelfItem(app, secondId).querySelector('.quantity-mini').textContent, '7개');
  assert.equal(app.document.querySelector('[data-injected]'), null, 'An unusual persisted ID is data, not an HTML attribute');
  const transfer = {
    values: new Map(),
    setData(type, value) { this.values.set(type, value); },
    getData(type) { return this.values.get(type) || ''; }
  };
  const dispatchDrag = (target, type) => {
    const event = new app.w.CustomEvent(type, { bubbles: true, cancelable: true });
    event.dataTransfer = transfer; target.dispatchEvent(event); return event;
  };
  const dragged = shelfItem(app, secondId), destination = app.$('#umfKitchenScene .shelf[data-zone="top"]');
  dispatchDrag(dragged, 'dragstart');
  assert.equal(transfer.getData('text/plain'), secondId);
  assert.equal(dispatchDrag(destination, 'dragover').defaultPrevented, true);
  dispatchDrag(destination, 'drop'); await app.flush(); dispatchDrag(dragged, 'dragend');
  assert.equal(app.w.UMFKitchenState.zoneFor(secondId), 'top');
  assert.equal(app.w.UMFKitchenState.zoneFor(firstId), 'freezer-bottom');
  assert.equal(shelfItem(app, secondId).closest('.shelf').dataset.zone, 'top');
  assert.equal(memory.get(STATE), before, 'Only the separate kitchen view record changes when arranging');
  assert.deepEqual(JSON.parse(memory.get(KITCHEN_VIEW)).placements, { [firstId]: 'freezer-bottom', [secondId]: 'top' });
  app.close();
  const reloaded = await boot({ memory }); t.after(() => reloaded.close());
  assert.equal(shelfItem(reloaded, firstId).closest('.shelf').dataset.zone, 'freezer-bottom');
  assert.equal(shelfItem(reloaded, secondId).closest('.shelf').dataset.zone, 'top');
  assert.equal(memory.get(STATE), before);
});

test('kitchen overflow opens all inventory and lets the user move a lot hidden behind plus N', async t => {
  const items = Array.from({ length: 8 }, (_, index) => kitchenItem('overflow-' + index, '계란', (index + 1) + '개'));
  const app = await boot({ seed: { [STATE]: existingFridge(items) } }); t.after(() => app.close());
  const before = app.memory.get(STATE), hiddenId = items[7].id;
  await app.click('#all');
  assert.equal(app.document.querySelectorAll('#list .row').length, 6);
  await app.click('#umfKitchenScene .compartment-toggle[data-compartment="fridge"]');
  const more = app.$('#umfKitchenScene .shelf[data-zone="middle"] .shelf-more');
  assert.equal(more.hidden, false); assert.equal(more.textContent, '+6');
  assert.equal(app.document.querySelectorAll('#umfKitchenScene .shelf[data-zone="middle"] .fridge-food').length, 2);
  await app.click(more);
  assertKitchenPage(app, 'home');
  assert.equal(app.document.querySelectorAll('#list .row').length, items.length);
  assert.equal(app.document.activeElement, app.$('#inventoryTitle'));
  const row = [...app.document.querySelectorAll('#list .row')].find(node => node.dataset.id === hiddenId);
  assert.ok(row);
  const arrange = row.querySelector('[data-kitchen-arrange]');
  assert.ok(arrange, 'Overflow stock has an actionable placement control in the real inventory list');
  await app.click(arrange);
  assert.equal(app.w.UMFKitchen.getOrganizing(), true);
  assert.equal(app.w.UMFKitchen.getMovingId(), hiddenId);
  await app.click('#umfKitchenScene .kitchen-zone-controls [data-zone="pantry"]');
  assert.equal(shelfItem(app, hiddenId).closest('.shelf').dataset.zone, 'pantry');
  assert.equal(shelfItem(app, hiddenId).querySelector('.quantity-mini').textContent, '8개');
  assert.equal(app.w.UMFKitchenState.zoneFor(items[0].id), 'middle');
  assert.equal(app.memory.get(STATE), before);
});

test('kitchen hero follows the selected recipe and opens its live detail instead of a separate recommendation', async t => {
  const app = await readyRice(t);
  await app.click('.nav-btn[data-kitchen-page="recipes"]');
  const other = app.w.UMFRecipes.catalog.find(recipe => recipe.name !== '계란 볶음밥');
  await app.selectRecipe(other.name);
  assertKitchenPage(app, 'recipes');
  assert.equal(app.$('#umfKitchenHero .recipe-title').textContent, other.name);
  assert.equal(app.$('#umfKitchenHero').dataset.recipe, other.name);
  assert.equal(app.$('#umfKitchenHero .today-dish').getAttribute('aria-label'), other.name + ' 재료를 표현한 일러스트');
  assert.equal(app.$('#umfSelectedName').textContent, other.name);
  await app.click('.nav-btn[data-kitchen-page="home"]');
  await app.click('#umfKitchenHero [data-action="recipe"]');
  assertKitchenPage(app, 'recipes');
  assert.equal(app.w.UMFRecipes.getSelected().recipe.name, other.name);
  assert.equal(app.$('#umfRecipeDetail').classList.contains('on'), true);
  assert.match(app.$('#umfRecipeDetail').textContent, new RegExp(other.name));
  await app.click('.nav-btn[data-kitchen-page="home"]');
  await app.click('#umfKitchenHero [data-action="shuffle"]');
  const shuffled = app.w.UMFRecipes.getSelected().recipe.name;
  assert.notEqual(shuffled, other.name);
  assert.equal(app.$('#umfKitchenHero .recipe-title').textContent, shuffled);
});

test('kitchen successful meal logging goes to the diary while an unavailable meal does not change pages', async t => {
  const app = await readyRice(t);
  const stock = JSON.stringify(app.w.UMFStore.getState().items);
  await app.click('.nav-btn[data-kitchen-page="recipes"]');
  await app.click('#umfLogBtn');
  assertKitchenPage(app, 'diary');
  assert.equal(app.w.UMFStore.getState().meals.length, 1);
  assert.match(app.$('#umfMealList').textContent, /계란 볶음밥/);
  assert.match(app.$('#umfMealFeedback').textContent, /기록했어요/);
  assert.equal(JSON.stringify(app.w.UMFStore.getState().items), stock);
  await app.click('.nav-btn[data-kitchen-page="recipes"]');
  await app.w.UMFStore.updateAsync(state => { state.items.find(item => item.name === '달걀').quantity = '0개'; });
  await app.flush(); app.advance(1000);
  await app.w.UMFInsights.logSelected(); await app.flush();
  assertKitchenPage(app, 'recipes');
  assert.equal(app.w.UMFStore.getState().meals.length, 1);
  assert.equal(app.$('#umfLogBtn').disabled, true);
});

test('kitchen preserves v5 records and sync settings without adding sample food, nutrition or prices', async t => {
  const original = existingFridge([
    kitchenItem('legacy-tofu', '두부', '1모', ''),
    kitchenItem('legacy-herbs', '허브', '조금', '')
  ], {
    season: ['식용유', '굴소스'], pantry: ['오트밀'],
    customSeason: ['굴소스'], customPantry: ['오트밀'],
    meals: [{ id: 'legacy-meal', name: '어제 메뉴', ts: seedTime - 86400000, day: '2026-10-19' }],
    favorites: ['계란 볶음밥']
  });
  const syncCode = 'UMF-012345678901234567890123456789012345';
  const metadata = JSON.stringify({ code: syncCode, local: 'preserved-local', remote: 'preserved-remote' });
  const raw = JSON.stringify(original);
  const memory = new Map([[STATE, raw], ['use-me-first-sync-code-v1', syncCode], ['use-me-first-sync-meta-v2', metadata]]);
  const app = await boot({ memory }); t.after(() => app.close());
  const requests = app.requests.length;
  assert.equal(memory.get(STATE), raw);
  assert.equal(app.w.UMFStore.getState().items.length, original.items.length);
  assert.equal(app.document.querySelectorAll('#umfKitchenScene .fridge-food').length, original.items.length);
  assert.match(app.$('#umfKitchenScene').textContent, /1모/);
  assert.match(app.$('#umfKitchenScene').textContent, /조금/);
  assert.doesNotMatch(app.$('#umfHomePage').textContent, /샘플 체험 중|샘플 냉장고|내 냉장고로 시작/);
  assert.doesNotMatch(app.$('#umfKitchenHero').textContent, /\d[\d,.]*\s*(?:kcal|원)/i);
  assert.equal(app.w.UMFStore.getState().favorites[0], '계란 볶음밥');
  await app.click('#umfKitchenScene .compartment-toggle[data-compartment="fridge"]');
  await app.click('#umfKitchenScene [data-action="organize"]');
  await app.click(shelfItem(app, 'legacy-tofu'));
  await app.click('#umfKitchenScene .kitchen-zone-controls [data-zone="freezer-top"]');
  assert.equal(memory.get(STATE), raw);
  assert.equal(memory.get('use-me-first-sync-code-v1'), syncCode);
  assert.equal(memory.get('use-me-first-sync-meta-v2'), metadata);
  assert.equal(app.requests.length, requests, 'Door and placement changes do not start inventory synchronization');
  assert.equal(app.w.UMFStore.getState().meals[0].day, '2026-10-19');
  assert.equal(app.w.UMFStore.getState().meals[0].name, '어제 메뉴');
  assert.equal(JSON.parse(memory.get(KITCHEN_VIEW)).placements['legacy-tofu'], 'freezer-top');
});
