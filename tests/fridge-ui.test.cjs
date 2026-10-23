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
  class TestPointerEvent extends dom.Event {
    constructor(type, options = {}) {
      super(type, { bubbles: true, cancelable: true, ...options });
      for (const [key, value] of Object.entries({
        pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0,
        buttons: type === 'pointerup' || type === 'pointercancel' ? 0 : 1,
        clientX: 0, clientY: 0, ...options
      })) if (!['bubbles', 'cancelable', 'composed'].includes(key)) this[key] = value;
    }
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
    navigator, document, localStorage: storage, crypto: webcrypto, CustomEvent: dom.CustomEvent, PointerEvent: TestPointerEvent,
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
    CustomEvent: dom.CustomEvent, Event: dom.Event, PointerEvent: TestPointerEvent, Node: dom.Node,
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

test('seasoning shelf edits dates, cancels safely, retains old stock and reopens after reload', async t => {
  const app = await boot(); t.after(() => app.close());
  await app.toggle('#sg', '간장');
  const original = app.memory.get(STATE), old = JSON.parse(original);
  await app.click('.seasoning-mini[data-seasoning-name="간장"]');
  assert.equal(app.$('#customName').readOnly, true);
  assert.equal(app.$('#customExpiryField').hidden, false);
  app.fill('#customExpiry', '2026-10-22'); await app.click('#customCancel');
  assert.equal(app.memory.get(STATE), original);
  await app.click('.seasoning-mini[data-seasoning-name="간장"]');
  app.fill('#customExpiry', '2026-10-22'); await app.click('#customSave');
  assert.equal(app.memory.get('use-me-first-before-seasoning-expiry-v1'), original);
  assert.equal(app.w.UMFStore.getState().seasoningExpiry.간장, '2026-10-22');
  for (const field of ['items', 'season', 'pantry', 'customSeason', 'customPantry', 'meals', 'favorites']) assert.deepEqual(JSON.parse(app.memory.get(STATE))[field], old[field]);
  const reopened = await boot({ memory: app.memory }); t.after(() => reopened.close());
  await reopened.click('.seasoning-mini[data-seasoning-name="간장"]');
  assert.equal(reopened.$('#customExpiry').value, '2026-10-22');
  await reopened.click('#customCancel');
  assert.match(reopened.$('.seasoning-mini[data-seasoning-name="간장"]').textContent, /2일 남음/);
});

test('expired seasoning changes recipe and shopping status and clearing its date keeps ownership', async t => {
  const app = await readyRice(t);
  await app.click('.nav-btn[data-kitchen-page="home"]');
  await app.click('.seasoning-mini[data-seasoning-name="간장"]');
  app.fill('#customExpiry', '2026-10-19'); await app.click('#customSave');
  assert.equal(app.$('.seasoning-mini[data-seasoning-name="간장"]').dataset.expiryStatus, 'expired');
  const rice = app.w.UMFRecipes.getRanked().find(x => x.recipe.name === '계란 볶음밥');
  assert.equal(rice.available, false); assert.equal(rice.missing.find(x => x.name === '간장').reason, 'expired');
  assert.match(app.$('#umfSelectionChips').textContent, /간장 · 기한 경과/);
  await app.click('.seasoning-mini[data-seasoning-name="간장"]');
  app.fill('#customExpiry', ''); await app.click('#customSave');
  assert.ok(app.w.UMFStore.getState().season.includes('간장'));
  assert.equal(Object.hasOwn(app.w.UMFStore.getState().seasoningExpiry, '간장'), false);
  assert.equal(app.w.UMFRecipes.getRanked().find(x => x.recipe.name === '계란 볶음밥').available, true);
});

test('seasoning additions accept dates while toggles and pantry additions preserve their existing meaning', async t => {
  const app = await boot(); t.after(() => app.close());
  await app.click('#addSeason'); app.fill('#customName', '유자청'); app.fill('#customExpiry', '2026-11-01'); await app.click('#customSave');
  assert.ok(app.w.UMFStore.getState().customSeason.includes('유자청'));
  await app.toggle('#sg', '유자청'); await app.toggle('#sg', '유자청');
  assert.equal(app.w.UMFStore.getState().seasoningExpiry.유자청, '2026-11-01');
  await app.click('#addPantry'); assert.equal(app.$('#customExpiryField').hidden, true);
  assert.equal(app.$('#customName').readOnly, false); app.fill('#customName', '오트밀'); await app.click('#customSave');
  assert.ok(app.w.UMFStore.getState().pantry.includes('오트밀'));
  assert.equal(Object.hasOwn(app.w.UMFStore.getState().seasoningExpiry, '오트밀'), false);
  assert.ok(app.$('.seasoning-mini[data-seasoning-name="유자청"] [data-seasoning-art="jar"]'));
});

test('seasoning date dialogs reject malformed dates and concurrent changes without overwriting either record', async t => {
  const app = await boot(); t.after(() => app.close()); await app.toggle('#sg', '간장');
  await app.click('.seasoning-mini[data-seasoning-name="간장"]'); app.fill('#customExpiry', '2026-02-30');
  const original = app.memory.get(STATE); await app.click('#customSave');
  assert.equal(app.memory.get(STATE), original); assert.equal(app.$('#umfCustomError').hidden, false);
  app.fill('#customExpiry', '2026-11-01');
  await app.w.UMFStore.updateAsync(s => { s.seasoningExpiry = { 간장: '2026-12-01' }; });
  await app.click('#customSave'); assert.match(app.$('#umfCustomError').textContent, /다른 화면/);
  assert.equal(app.w.UMFStore.getState().seasoningExpiry.간장, '2026-12-01');
  await app.click('#customCancel');
});
async function whileStoreLocked(action, key = STATE) {
  let release, acquired;
  const gate = new Promise(resolve => { release = resolve; });
  const entered = new Promise(resolve => { acquired = resolve; });
  const holding = nodeLocks.request(key + ':transaction', { mode: 'exclusive' }, async () => {
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
  const before = (dependency, consumer) => {
    const first = sources.findIndex(src => src.split('?')[0] === dependency);
    const second = sources.findIndex(src => src.split('?')[0] === consumer);
    assert.ok(first >= 0 && second > first, dependency + ' must load before ' + consumer);
  };
  before('use-me-first-domain.js', 'use-me-first-core-final.js');
  before('use-me-first-store.js', 'use-me-first-core-final.js');
  before('use-me-first-core-final.js', 'use-me-first-recipe-grid-final.js');
  before('use-me-first-recipe-grid-final.js', 'use-me-first-ui-final.js');
  before('use-me-first-kitchen-state.js', 'use-me-first-kitchen.js');
  before('use-me-first-kitchen-art.js', 'use-me-first-kitchen.js');
  before('use-me-first-kitchen-nav.js', 'use-me-first-kitchen.js');
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
  for (const image of app.document.querySelectorAll('#umfRecipeGrid img')) {
    assert.doesNotMatch(image.getAttribute('src') || '', /^https?:\/\//, 'Recipe art is a bundled asset, not an unrelated external photograph');
  }
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
  assert.equal(app.document.querySelector('#list img[onerror],#list img[src="x"]'), null);
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
  await app.click('#addSeason'); app.fill('#customName', '유자청'); await app.click('#customSave');
  await app.click('#addPantry'); app.fill('#customName', '오트밀'); await app.click('#customSave');
  const st = app.w.UMFStore.getState(); assert.equal(st.customSeason.includes('유자청'), true); assert.equal(st.customPantry.includes('오트밀'), true);
  assert.equal(st.season.includes('유자청'), true); assert.equal(st.pantry.includes('오트밀'), true); assert.equal(st.items.length, 0);
  const remove = [...app.document.querySelectorAll('#sg .umf-custom-remove')].find(x => x.getAttribute('aria-label') === '유자청 항목 삭제'); await app.click(remove);
  assert.equal(app.w.UMFStore.getState().season.includes('유자청'), false);
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
function kitchenGeometry(app) {
  // Deterministic hit testing validates event/coordinate logic, not CSS layout.
  const rectangles = new Map(), captures = new Map();
  const rectangle = (left, top, width, height) => ({ left, top, width, height, x: left, y: top, right: left + width, bottom: top + height });
  for (const [index, canvas] of [...app.document.querySelectorAll('#umfKitchenScene .shelf-canvas')].entries()) {
    const rect = rectangle(40 + index % 2 * 300, 50 + Math.floor(index / 2) * 220, 240, 160);
    rectangles.set(canvas, rect); canvas.getBoundingClientRect = () => rect;
    Object.defineProperties(canvas, { clientWidth: { configurable: true, value: rect.width }, clientHeight: { configurable: true, value: rect.height } });
  }
  for (const button of app.document.querySelectorAll('#umfKitchenScene .fridge-food')) {
    button.getBoundingClientRect = () => {
      const rect = rectangles.get(button.closest('.shelf-canvas'));
      return rectangle(rect.left + Number(button.dataset.x) * 200, rect.top + Number(button.dataset.y) * 120, 40, 40);
    };
    Object.defineProperties(button, { offsetWidth: { configurable: true, value: 40 }, offsetHeight: { configurable: true, value: 40 } });
    button.setPointerCapture = id => captures.set(id, button);
    button.hasPointerCapture = id => captures.get(id) === button;
    button.releasePointerCapture = id => { if (captures.get(id) === button) captures.delete(id); };
  }
  app.document.elementFromPoint = (x, y) => [...rectangles].find(([, rect]) => x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom)?.[0] || null;
  return {
    captures,
    canvas(zone) { return app.$('#umfKitchenScene .shelf-canvas[data-zone="' + zone + '"]'); },
    point(zone, x, y) {
      const rect = rectangles.get(this.canvas(zone));
      return { clientX: rect.left + x * 200 + 20, clientY: rect.top + y * 120 + 20 };
    },
    itemPoint(id) { const rect = shelfItem(app, id).getBoundingClientRect(); return { clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 }; },
    pointer(target, type, point, properties = {}) {
      const event = new app.w.PointerEvent(type, { ...point, ...properties });
      target.dispatchEvent(event); return event;
    },
    click(target, point) {
      const event = new app.w.CustomEvent('click', { bubbles: true, cancelable: true });
      Object.assign(event, { button: 0, detail: 1, ...point }); target.dispatchEvent(event); return event;
    }
  };
}
function assertKitchenPosition(app, id, zone, x, y) {
  const saved = app.w.UMFKitchenState.positionFor(id), button = shelfItem(app, id);
  assert.ok(saved, 'An arranged lot has a saved position');
  assert.equal(app.w.UMFKitchenState.zoneFor(id), zone);
  assert.equal(button.closest('.shelf-canvas').dataset.zone, zone);
  for (const [key, expected] of [['x', x], ['y', y]]) {
    assert.ok(Math.abs(saved[key] - expected) < 1e-10, key + ' expected ' + expected + ', got ' + saved[key]);
    assert.ok(Math.abs(Number(button.dataset[key]) - expected) < 1e-10, 'Rendered ' + key + ' matches the saved position');
  }
  assert.equal(Number(button.dataset.z), saved.z);
  assert.ok(Number.isSafeInteger(saved.z) && saved.z > 0);
  return saved;
}
async function kitchenKey(app, target, key, options = {}) {
  const event = new app.w.CustomEvent('keydown', { bubbles: true, cancelable: true });
  Object.assign(event, { key, shiftKey: false, repeat: false, ...options });
  target.dispatchEvent(event); await app.flush(); return event;
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

test('kitchen renders every overlapping lot and inventory can select a buried lot to change its layer', async t => {
  const items = Array.from({ length: 8 }, (_, index) => kitchenItem('overlap-' + index, '계란', (index + 1) + '개'));
  const view = {
    version: 2, doors: { freezer: false, fridge: true }, placements: {},
    positions: Object.fromEntries(items.map((item, index) => [item.id, { x: .4, y: .6, z: index + 1 }]))
  };
  const memory = new Map([[STATE, JSON.stringify(existingFridge(items))], [KITCHEN_VIEW, JSON.stringify(view)]]);
  const app = await boot({ memory }); t.after(() => app.close());
  const before = memory.get(STATE), buriedId = items[0].id;
  const rendered = [...app.document.querySelectorAll('#umfKitchenScene .shelf-canvas[data-zone="middle"] .fridge-food')];
  assert.equal(rendered.length, items.length, 'No inventory lot is replaced by a hidden-count placeholder');
  assert.deepEqual(rendered.map(node => node.dataset.lot), items.map(item => item.id));
  for (const [index, button] of rendered.entries()) {
    assert.equal(button.hidden, false); assert.equal(button.disabled, false);
    assert.equal(button.querySelector('.quantity-mini').textContent, (index + 1) + '개');
    assertKitchenPosition(app, items[index].id, 'middle', .4, .6);
    assert.equal(button.style.left, '40%'); assert.equal(button.style.top, '60%');
    assert.equal(Number(button.style.zIndex), index + 1);
  }
  assert.equal(new Set(rendered.map(button => button.style.transform)).size, 1, 'Equal coordinates deliberately overlap');
  assert.doesNotMatch(app.$('#umfKitchenScene').textContent, /\+\s*[1-9]\d*\s*(?:개)?/);
  await app.click('#all');
  assert.equal(app.document.querySelectorAll('#list .row').length, 6);
  await app.click('#umfKitchenScene [data-action="navigate"][data-page="inventory"]');
  assertKitchenPage(app, 'home');
  assert.equal(app.document.querySelectorAll('#list .row').length, items.length);
  assert.equal(app.document.activeElement, app.$('#inventoryTitle'));
  const row = [...app.document.querySelectorAll('#list .row')].find(node => node.dataset.id === buriedId);
  assert.ok(row);
  const arrange = row.querySelector('[data-kitchen-arrange]');
  assert.ok(arrange, 'An overlapped lot remains reachable through its inventory row');
  await app.click(arrange);
  assert.equal(app.w.UMFKitchen.getOrganizing(), true);
  assert.equal(app.w.UMFKitchen.getMovingId(), buriedId);
  await app.click('#umfKitchenScene [data-action="layer-front"]');
  const front = assertKitchenPosition(app, buriedId, 'middle', .4, .6);
  assert.ok(items.slice(1).every(item => app.w.UMFKitchenState.positionFor(item.id).z < front.z));
  assert.equal(Number(shelfItem(app, buriedId).style.zIndex), items.length);
  await app.click('#umfKitchenScene [data-action="layer-back"]');
  const back = assertKitchenPosition(app, buriedId, 'middle', .4, .6);
  assert.ok(items.slice(1).every(item => app.w.UMFKitchenState.positionFor(item.id).z > back.z));
  assert.equal(Number(shelfItem(app, buriedId).style.zIndex), 1);
  assert.equal(memory.get(STATE), before);
  const arranged = memory.get(KITCHEN_VIEW);
  app.close();
  const reloaded = await boot({ memory }); t.after(() => reloaded.close());
  assert.equal(reloaded.document.querySelectorAll('#umfKitchenScene .fridge-food').length, items.length);
  for (const item of items) assertKitchenPosition(reloaded, item.id, 'middle', .4, .6);
  assert.equal(Number(shelfItem(reloaded, buriedId).style.zIndex), 1);
  assert.equal(memory.get(KITCHEN_VIEW), arranged);
  assert.equal(memory.get(STATE), before);
});

test('kitchen layer changes preserve the relative order and coordinates of unselected saved and default lots', async t => {
  const items = [kitchenItem('saved-onion', '양파'), kitchenItem('default-egg', '계란'), kitchenItem('selected-tofu', '두부')];
  const app = await boot({ seed: {
    [STATE]: existingFridge(items),
    [KITCHEN_VIEW]: { version: 2, doors: { freezer: false, fridge: true }, placements: {}, positions: { 'saved-onion': { x: .4, y: .5, z: 1 } } }
  } }); t.after(() => app.close());
  const before = app.memory.get(STATE);
  const positions = new Map(items.map(item => [item.id, { x: Number(shelfItem(app, item.id).dataset.x), y: Number(shelfItem(app, item.id).dataset.y) }]));
  assert.ok(Number(shelfItem(app, 'default-egg').style.zIndex) < Number(shelfItem(app, 'saved-onion').style.zIndex));
  await app.click('#umfKitchenScene [data-action="organize"]');
  await app.click(shelfItem(app, 'selected-tofu'));
  await app.click('#umfKitchenScene [data-action="layer-front"]');
  for (const item of items) {
    const position = positions.get(item.id);
    assertKitchenPosition(app, item.id, 'middle', position.x, position.y);
  }
  assert.ok(app.w.UMFKitchenState.positionFor('default-egg').z < app.w.UMFKitchenState.positionFor('saved-onion').z, 'Sending C to the front must not move an unrelated default B in front of saved A');
  assert.ok(app.w.UMFKitchenState.positionFor('saved-onion').z < app.w.UMFKitchenState.positionFor('selected-tofu').z);
  assert.equal(app.memory.get(STATE), before);
});

test('kitchen mouse placement uses captured-pointer destination coordinates and keeps repaired duplicate lots independent', async t => {
  const app = await boot({ seed: { [STATE]: existingFridge([kitchenItem('duplicate-lot', '계란', '2개'), kitchenItem('duplicate-lot', '계란', '7개')]) } });
  t.after(() => app.close());
  const items = app.w.UMFStore.getState().items;
  assert.equal(items.length, 2); assert.notEqual(items[0].id, items[1].id, 'Restored duplicate IDs are repaired before the scene maps lots');
  const movedId = items[1].id, untouchedId = items[0].id, stock = app.memory.get(STATE);
  assert.equal(app.document.querySelectorAll('#umfKitchenScene .fridge-food').length, 2);
  await app.click('#umfKitchenScene [data-action="organize"]');
  const geometry = kitchenGeometry(app), food = shelfItem(app, movedId);
  const start = geometry.itemPoint(movedId), destination = geometry.point('freezer-top', .7, .3);
  // Grab at 75% across and 25% down: preserving the grab anchor prevents a jump
  // when the pointer is not at the center of the food.
  start.clientX += 10; start.clientY -= 10;
  destination.clientX += 10; destination.clientY -= 10;
  const viewBefore = app.memory.get(KITCHEN_VIEW);
  geometry.pointer(food, 'pointerdown', start);
  assert.equal(geometry.captures.get(1), food);
  geometry.pointer(food, 'pointermove', destination);
  assert.equal(app.memory.get(KITCHEN_VIEW), viewBefore, 'A drag preview must not write a position before release');
  assert.ok(app.document.querySelector('.kitchen-drag-ghost'));
  // The original source receives pointerup under capture; its event.target is
  // deliberately not the destination canvas returned by elementFromPoint.
  geometry.pointer(food, 'pointerup', destination); await app.flush();
  assertKitchenPosition(app, movedId, 'freezer-top', .7, .3);
  assert.equal(app.w.UMFKitchenState.positionFor(untouchedId), null);
  assert.equal(app.w.UMFKitchenState.zoneFor(untouchedId), 'middle');
  assert.equal(shelfItem(app, movedId).querySelector('.quantity-mini').textContent, '7개');
  assert.equal(shelfItem(app, untouchedId).querySelector('.quantity-mini').textContent, '2개');
  assert.equal(app.document.querySelector('.kitchen-drag-ghost'), null);
  assert.equal(geometry.captures.size, 0);
  assert.equal(geometry.click(food, destination).defaultPrevented, true, 'The synthetic click following pointerup is consumed');
  await app.flush();
  assert.equal(app.w.UMFKitchen.getMovingId(), movedId);
  assert.equal(app.$('#mb').classList.contains('on'), false);
  app.advance(501);
  await app.click('#umfKitchenScene [data-action="organize"]');
  await app.click(food);
  assert.equal(app.$('#mb').classList.contains('on'), true, 'A later intentional click still opens the editor');
  assert.equal(app.$('#umfQty').value, '7개');
  assert.equal(app.memory.get(STATE), stock);
});

test('kitchen touch placement, canvas taps and arrow nudges preserve v1 preferences while upgrading the same key', async t => {
  const items = [kitchenItem('touch-egg', '계란', '2개'), kitchenItem('pantry-onion', '양파')];
  const legacy = { version: 1, doors: { freezer: true, fridge: false }, placements: { 'touch-egg': 'freezer-top', 'pantry-onion': 'pantry' } };
  const rawLegacy = JSON.stringify(legacy), rawStock = JSON.stringify(existingFridge(items));
  const memory = new Map([[STATE, rawStock], [KITCHEN_VIEW, rawLegacy]]);
  const app = await boot({ memory }); t.after(() => app.close());
  assert.equal(memory.get(KITCHEN_VIEW), rawLegacy, 'Reading a valid v1 preference does not rewrite it');
  assert.equal(app.w.UMFKitchenState.getState().version, 2);
  assert.equal(app.w.UMFKitchenState.positionFor('touch-egg'), null);
  assert.equal(app.w.UMFKitchenState.getState().doors.fridge, false);
  await app.click('#umfKitchenScene [data-action="organize"]');
  const geometry = kitchenGeometry(app), food = shelfItem(app, 'touch-egg');
  const touch = { pointerId: 31, pointerType: 'touch' }, destination = geometry.point('freezer-top', .6, .4);
  geometry.pointer(food, 'pointerdown', geometry.itemPoint('touch-egg'), touch);
  geometry.pointer(food, 'pointermove', destination, touch);
  geometry.pointer(food, 'pointerup', destination, touch); await app.flush();
  assertKitchenPosition(app, 'touch-egg', 'freezer-top', .6, .4);
  geometry.click(food, destination); await app.flush();
  assert.equal(app.w.UMFKitchen.getMovingId(), 'touch-egg');
  const canvas = geometry.canvas('middle'), tap = geometry.point('middle', .25, .75);
  geometry.pointer(canvas, 'pointerdown', tap, touch);
  geometry.pointer(canvas, 'pointerup', tap, touch);
  geometry.click(canvas, tap); await app.flush();
  assertKitchenPosition(app, 'touch-egg', 'middle', .25, .75);
  assert.equal((await kitchenKey(app, food, 'ArrowRight')).defaultPrevented, true);
  assertKitchenPosition(app, 'touch-egg', 'middle', .27, .75);
  await kitchenKey(app, food, 'ArrowDown', { shiftKey: true });
  assertKitchenPosition(app, 'touch-egg', 'middle', .27, .85);
  await kitchenKey(app, food, 'ArrowDown', { shiftKey: true });
  await kitchenKey(app, food, 'ArrowDown', { shiftKey: true });
  assertKitchenPosition(app, 'touch-egg', 'middle', .27, 1);
  const atEdge = memory.get(KITCHEN_VIEW);
  await kitchenKey(app, food, 'ArrowDown');
  assert.equal(memory.get(KITCHEN_VIEW), atEdge, 'A nudge beyond the edge causes no extra write or layer change');
  const upgraded = JSON.parse(memory.get(KITCHEN_VIEW));
  assert.equal(upgraded.version, 2);
  assert.equal(upgraded.placements['pantry-onion'], 'pantry');
  assert.equal(upgraded.positions['pantry-onion'], undefined);
  assert.equal(memory.get(STATE), rawStock);
  assert.equal([...memory.keys()].filter(key => /^use-me-first-kitchen-view/.test(key)).length, 1);
  app.close();
  const reloaded = await boot({ memory }); t.after(() => reloaded.close());
  assertKitchenPosition(reloaded, 'touch-egg', 'middle', .27, 1);
  assert.equal(reloaded.w.UMFKitchenState.zoneFor('pantry-onion'), 'pantry');
  assert.equal(memory.get(STATE), rawStock);
});

test('kitchen pointer cancellation, Escape and an outside release discard the preview and late pointerup', async t => {
  const app = await boot({ seed: {
    [STATE]: existingFridge([kitchenItem('cancel-egg', '계란')]),
    [KITCHEN_VIEW]: { version: 2, doors: { freezer: true, fridge: true }, placements: {}, positions: { 'cancel-egg': { x: .2, y: .3, z: 1 } } }
  } }); t.after(() => app.close());
  await app.click('#umfKitchenScene [data-action="organize"]');
  const geometry = kitchenGeometry(app), food = shelfItem(app, 'cancel-egg');
  const before = app.memory.get(KITCHEN_VIEW), stock = app.memory.get(STATE), destination = geometry.point('top', .8, .6);
  for (const cancellation of ['pointercancel', 'Escape', 'outside']) {
    app.advance(501);
    geometry.pointer(food, 'pointerdown', geometry.itemPoint('cancel-egg'));
    geometry.pointer(food, 'pointermove', destination);
    assert.ok(app.document.querySelector('.kitchen-drag-ghost'), cancellation + ' starts from a real drag preview');
    if (cancellation === 'Escape') await kitchenKey(app, food, 'Escape');
    else if (cancellation === 'pointercancel') geometry.pointer(food, 'pointercancel', destination);
    else geometry.pointer(food, 'pointerup', { clientX: -100, clientY: -100 });
    geometry.pointer(food, 'pointerup', destination); await app.flush();
    assert.equal(app.memory.get(KITCHEN_VIEW), before, cancellation + ' must not save any coordinate, zone or layer');
    assertKitchenPosition(app, 'cancel-egg', 'middle', .2, .3);
    assert.equal(app.document.querySelector('.kitchen-drag-ghost,.is-drag-source,.shelf-canvas.is-over'), null);
    assert.equal(geometry.captures.size, 0);
    assert.equal(app.$('#mb').classList.contains('on'), false);
  }
  assert.equal(app.memory.get(STATE), stock);
});

test('kitchen closed doors reject a drag source, a drop target and a gesture interrupted by door closing', async t => {
  const items = [kitchenItem('closed-frozen', '계란'), kitchenItem('open-fresh', '양파')];
  const app = await boot({ seed: {
    [STATE]: existingFridge(items),
    [KITCHEN_VIEW]: { version: 2, doors: { freezer: true, fridge: true }, placements: { 'closed-frozen': 'freezer-top' }, positions: { 'closed-frozen': { x: .2, y: .3, z: 1 }, 'open-fresh': { x: .4, y: .5, z: 2 } } }
  } }); t.after(() => app.close());
  const stock = app.memory.get(STATE);
  await app.click('#umfKitchenScene [data-action="organize"]');
  await app.click('#umfKitchenScene .compartment-toggle[data-compartment="freezer"]');
  const geometry = kitchenGeometry(app), frozen = shelfItem(app, 'closed-frozen'), fresh = shelfItem(app, 'open-fresh');
  const before = app.memory.get(KITCHEN_VIEW), openPoint = geometry.point('top', .6, .7), closedPoint = geometry.point('freezer-top', .6, .7);
  assert.equal(frozen.disabled, true);
  geometry.pointer(frozen, 'pointerdown', geometry.itemPoint('closed-frozen'));
  geometry.pointer(frozen, 'pointermove', openPoint);
  geometry.pointer(frozen, 'pointerup', openPoint); await app.flush();
  assert.equal(app.memory.get(KITCHEN_VIEW), before, 'Inert stock cannot begin a gesture');
  geometry.pointer(fresh, 'pointerdown', geometry.itemPoint('open-fresh'));
  geometry.pointer(fresh, 'pointermove', closedPoint);
  geometry.pointer(fresh, 'pointerup', closedPoint); await app.flush();
  assert.equal(app.memory.get(KITCHEN_VIEW), before, 'A closed destination cannot receive an item');
  app.advance(501);
  geometry.pointer(fresh, 'pointerdown', geometry.itemPoint('open-fresh'));
  geometry.pointer(fresh, 'pointermove', openPoint);
  await app.w.UMFKitchenState.toggleDoor('fridge'); await app.flush();
  const afterClosing = app.memory.get(KITCHEN_VIEW);
  geometry.pointer(fresh, 'pointerup', openPoint); await app.flush();
  assert.equal(app.memory.get(KITCHEN_VIEW), afterClosing, 'A late pointerup cannot revive a gesture canceled by closing the source');
  assertKitchenPosition(app, 'closed-frozen', 'freezer-top', .2, .3);
  assertKitchenPosition(app, 'open-fresh', 'middle', .4, .5);
  assert.equal(app.$('#inside-fridge').hasAttribute('inert'), true);
  assert.equal(app.document.querySelector('.kitchen-drag-ghost'), null);
  assert.equal(geometry.captures.size, 0);
  assert.equal(app.memory.get(STATE), stock);
});

test('kitchen a queued pointer placement cannot commit after navigation, global Escape or a changed inventory lot', async t => {
  for (const cancellation of ['navigation', 'Escape', 'inventory change']) {
    const app = await boot({ seed: {
      [STATE]: existingFridge([kitchenItem('queued-egg', '계란', '2개')]),
      [KITCHEN_VIEW]: { version: 2, doors: { freezer: true, fridge: true }, placements: {}, positions: { 'queued-egg': { x: .2, y: .3, z: 1 } } }
    } }); t.after(() => app.close());
    await app.click('#umfKitchenScene [data-action="organize"]');
    const geometry = kitchenGeometry(app), food = shelfItem(app, 'queued-egg');
    const before = app.memory.get(KITCHEN_VIEW), destination = geometry.point('freezer-bottom', .6, .8);
    await whileStoreLocked(async () => {
      geometry.pointer(food, 'pointerdown', geometry.itemPoint('queued-egg'));
      geometry.pointer(food, 'pointermove', destination);
      geometry.pointer(food, 'pointerup', destination);
      assert.equal(food.disabled, true, 'The position save is waiting for the real Web Lock');
      assert.equal(app.memory.get(KITCHEN_VIEW), before);
      if (cancellation === 'navigation') app.w.UMFKitchenNav.go('recipes');
      else if (cancellation === 'Escape') {
        const event = new app.w.CustomEvent('keydown', { bubbles: true, cancelable: true });
        event.key = 'Escape'; app.document.body.dispatchEvent(event);
      } else await app.w.UMFStore.updateAsync(state => { state.items[0].quantity = '7개'; });
      // Do not flush while holding the lock: the UI action is intentionally
      // still queued, and must validate its captured context after release.
    }, KITCHEN_VIEW);
    await app.flush();
    assert.equal(app.memory.get(KITCHEN_VIEW), before, cancellation + ' cancels the delayed position write');
    assertKitchenPosition(app, 'queued-egg', 'middle', .2, .3);
    assert.equal(app.document.querySelector('.kitchen-drag-ghost'), null);
    assert.equal(app.$('#mb').classList.contains('on'), false);
    if (cancellation === 'navigation') assertKitchenPage(app, 'recipes');
    if (cancellation === 'inventory change') assert.equal(shelfItem(app, 'queued-egg').querySelector('.quantity-mini').textContent, '7개');
    app.close();
  }
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

test('four physical doors open independently and closed upper and lower panels remain inert', async t => {
  const app = await boot(); t.after(() => app.close());
  const panels = ['fridge', 'fridge-right', 'freezer', 'freezer-right'];
  assert.equal(app.document.querySelectorAll('#umfKitchenScene .fridge-door').length, 4);
  assert.equal(app.document.querySelectorAll('#umfKitchenScene .door-display').length, 2);
  for (const selected of panels) {
    await app.click('.fridge-door[data-compartment="' + selected + '"]');
    for (const key of panels) {
      assert.equal(app.$('#inside-' + key).hasAttribute('inert'), key !== selected);
      assert.equal(app.$('.compartment-toggle[data-compartment="' + key + '"]').getAttribute('aria-expanded'), String(key === selected));
    }
    await app.click('.compartment-toggle[data-compartment="' + selected + '"]');
    assert.ok(panels.every(key => app.$('#inside-' + key).hasAttribute('inert')));
  }
});

test('right-hand refrigerated and frozen placements retain exact inventory and reopen after reload', async t => {
  const id = 'four-door-lot';
  const memory = new Map([[STATE, JSON.stringify(existingFridge([kitchenItem(id, '두부', '150g')]))]]);
  const app = await boot({ memory }); t.after(() => app.close());
  const original = memory.get(STATE);
  await app.click('[data-action="organize"]');
  await app.click(shelfItem(app, id));
  for (const zone of ['fridge-right-middle', 'freezer-bottom', 'freezer-right-bottom']) {
    await app.click('.kitchen-zone-controls [data-zone="' + zone + '"]');
    assert.equal(app.w.UMFKitchenState.zoneFor(id), zone);
    assert.equal(shelfItem(app, id).closest('.shelf').dataset.zone, zone);
  }
  await app.click('.compartment-toggle[data-compartment="freezer"]');
  assert.equal(shelfItem(app, id).disabled, false, 'Closing the left freezer must not disable a right-freezer lot');
  assert.equal(memory.get(STATE), original);
  app.close();
  const reopened = await boot({ memory }); t.after(() => reopened.close());
  assert.equal(reopened.w.UMFKitchenState.zoneFor(id), 'freezer-right-bottom');
  assert.equal(reopened.$('#inside-freezer-right').hasAttribute('inert'), false);
  assert.equal(reopened.$('#inside-freezer').hasAttribute('inert'), true);
  assert.equal(shelfItem(reopened, id).querySelector('.quantity-mini').textContent, '150g');
  assert.equal(memory.get(STATE), original);
});

test('redesigned kitchen never refreshes expired inventory even when names and quantities match an old demo', async t => {
  const items = [['애호박', '1개'], ['우유', '900ml'], ['두부', '300g'], ['계란', '10개'], ['양파', '3개'], ['요거트', '1개']]
    .map(([name, quantity], i) => kitchenItem('real-lot-' + i, name, quantity, '2020-01-01'));
  const original = JSON.stringify(existingFridge(items));
  const memory = new Map([[STATE, original]]);
  const app = await boot({ memory }); t.after(() => app.close());
  assert.equal(memory.get(STATE), original);
  assert.equal(memory.has('umf-demo-expiry-balance-v1'), false);
  await app.click('.compartment-toggle[data-compartment="freezer-right"]');
  await app.click('[data-action="organize"]');
  assert.equal(memory.get(STATE), original);
  app.close();
  const reloaded = await boot({ memory }); t.after(() => reloaded.close());
  assert.equal(memory.get(STATE), original);
  assert.ok(reloaded.w.UMFStore.getState().items.every(item => item.expiry === '2020-01-01'));
});

test('cozy recipe worktops render every miniature meal and retain recipe selection and favorite actions', async t => {
  const app = await boot(); t.after(() => app.close());
  for (const recipe of app.w.UMFRecipes.catalog) {
    const card = app.card(recipe.name), dish = card.querySelector('.umf-recipe-board [data-miniature]');
    assert.ok(dish, recipe.name + ' has a miniature meal');
    assert.notEqual(dish.dataset.miniature, 'ingredient', recipe.name + ' must not use a generic fallback');
  }
  await app.click('.nav-btn[data-kitchen-page="recipes"]');
  await app.selectRecipe('두부 스테이크');
  assert.equal(app.w.UMFRecipes.getSelected().recipe.name, '두부 스테이크');
  await app.click(app.card('두부 스테이크').querySelector('.umf-fav'));
  assert.ok(app.w.UMFStore.getState().favorites.includes('두부 스테이크'));
});
