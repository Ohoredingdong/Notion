const test = require('node:test');
const assert = require('node:assert/strict');
const { KEY, ZONES, blank, createKitchenState } = require('../use-me-first-kitchen-state.js');
const nativeLocks = globalThis.navigator?.locks || require('node:worker_threads').locks;
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
function memory(entries = {}) {
  const values = new Map(Object.entries(entries));
  return {
    values, fail: false,
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { if (this.fail) throw new Error('QuotaExceededError'); values.set(key, String(value)); },
    removeItem(key) { values.delete(key); }
  };
}
class Events extends EventTarget {
  CustomEvent = class extends Event { constructor(type, options) { super(type); this.detail = options.detail; } };
  storage(key, newValue = null) { const event = new Event('storage'); event.key = key; event.newValue = newValue; this.dispatchEvent(event); }
}

test('defaults close both doors and never infer freezing from a food name', async () => {
  const storage = memory(), state = createKitchenState({ storage });
  assert.equal(await state.ready, true); assert.deepEqual(state.getState(), blank());
  assert.equal(state.zoneFor({ id: 'one', name: '냉동 만두' }), 'middle'); assert.equal(state.zoneFor({ id: 'two', name: '아이스크림' }), 'middle');
  assert.equal(storage.getItem(KEY), null, 'opening a screen alone does not write preferences');
  const clone = state.getState(); clone.doors.fridge = true; assert.equal(state.getState().doors.fridge, false);
});

test('freezer and fridge doors persist independently, including partial setDoors', async () => {
  const storage = memory(), state = createKitchenState({ storage });
  assert.equal(await state.toggleDoor('freezer'), true); assert.deepEqual(state.getState().doors, { freezer: true, fridge: false });
  assert.equal(await state.toggleDoor('fridge'), true); assert.deepEqual(state.getState().doors, { freezer: true, fridge: true });
  assert.equal(await state.setDoors({ freezer: false }), true); assert.deepEqual(state.getState().doors, { freezer: false, fridge: true });
  const reopened = createKitchenState({ storage }); assert.deepEqual(reopened.getState(), state.getState());
});

test('same-name ingredients use independent IDs and support every explicit zone', async () => {
  const storage = memory(), state = createKitchenState({ storage });
  const first = { id: 'lot-a', name: '두부' }, second = { id: 'lot-b', name: '두부' };
  await state.setZone(first.id, 'top'); await state.setZone(second.id, 'freezer-bottom');
  assert.equal(state.zoneFor(first), 'top'); assert.equal(state.zoneFor(second), 'freezer-bottom');
  const reopened = createKitchenState({ storage }); assert.equal(reopened.zoneFor(second), 'freezer-bottom');
  for (const zone of ZONES) { assert.equal(await state.setZone('zone-check', zone), true); assert.equal(state.zoneFor('zone-check'), zone); }
  await state.setZone('__proto__', 'pantry'); assert.equal(state.zoneFor('__proto__'), 'pantry'); assert.equal(state.zoneFor('constructor'), 'middle');
});

test('invalid setters and mutation payloads leave the successful record unchanged', async () => {
  const storage = memory(), state = createKitchenState({ storage }); await state.toggleDoor('fridge');
  const before = storage.getItem(KEY);
  for (const result of [state.setZone('', 'top'), state.setZone('lot', 'unknown'), state.toggleDoor('pantry'), state.setDoors({ fridge: 1 }), state.setDoors({ extra: true })]) assert.equal(await result, false);
  assert.equal(await state.updateAsync(draft => { draft.placements.lot = 'unknown'; }), false);
  assert.equal(await state.updateAsync(async draft => { draft.doors.fridge = false; }), false);
  assert.equal(storage.getItem(KEY), before); assert.ok(state.error);
});

test('malformed and future-version records are preserved byte for byte and block writes', async () => {
  for (const raw of ['{broken', JSON.stringify({ ...blank(), version: 2 }), JSON.stringify({ ...blank(), doors: { fridge: true } }), JSON.stringify({ ...blank(), placements: { one: 'unknown' } }), JSON.stringify({ ...blank(), extra: true })]) {
    const storage = memory({ [KEY]: raw }), state = createKitchenState({ storage });
    assert.equal(await state.ready, false); assert.doesNotThrow(() => state.getState());
    assert.equal(await state.toggleDoor('fridge'), false); assert.equal(storage.getItem(KEY), raw); assert.equal(state.blocked, true);
  }
});

test('storage failures retain the last successful state and emit a visible error event', async () => {
  const storage = memory(), events = new Events(), state = createKitchenState({ storage, eventTarget: events });
  const failures = []; events.addEventListener('umf:kitchenerror', event => failures.push(event.detail.message));
  await state.setZone('lot', 'top'); const before = storage.getItem(KEY); storage.fail = true;
  assert.equal(await state.setZone('lot', 'bottom'), false); assert.equal(storage.getItem(KEY), before); assert.equal(state.zoneFor('lot'), 'top');
  assert.ok(state.error); assert.ok(failures.length);
  const unavailable = createKitchenState({ storage: null }); assert.equal(await unavailable.ready, false); assert.equal(await unavailable.toggleDoor('fridge'), false); assert.deepEqual(unavailable.getState(), blank());
});

test('cross-tab events use durable state, preserve good memory after corruption, and support unsubscribe', async () => {
  const storage = memory(), events = new Events(), first = createKitchenState({ storage }), second = createKitchenState({ storage, eventTarget: events });
  const updates = [], unsubscribe = second.subscribe((state, info) => updates.push({ state, origin: info.origin }));
  await first.setDoors({ fridge: true }); events.storage(KEY, 'stale-event-body');
  assert.equal(updates.length, 1); assert.equal(updates[0].origin, 'external'); assert.equal(updates[0].state.doors.fridge, true);
  storage.setItem(KEY, '{broken'); events.storage(KEY); assert.equal(second.getState().doors.fridge, true); assert.equal(second.blocked, true);
  storage.removeItem(KEY); events.storage(KEY); assert.deepEqual(second.getState(), blank()); assert.equal(second.error, '');
  unsubscribe(); await first.toggleDoor('freezer'); events.storage(KEY); assert.equal(updates.length, 2); second.destroy();
});

test('updates read the latest durable preferences without relying on a storage event', async () => {
  const storage = memory(), first = createKitchenState({ storage }), second = createKitchenState({ storage });
  await first.toggleDoor('freezer'); await second.setZone('lot', 'bottom');
  assert.deepEqual(second.getState(), { version: 1, doors: { freezer: true, fridge: false }, placements: { lot: 'bottom' } });
});

test('native Web Locks serialize concurrent kitchen edits and capture queued door inputs', { skip: !nativeLocks }, async () => {
  const storage = memory(), first = createKitchenState({ storage, locks: nativeLocks }), second = createKitchenState({ storage, locks: nativeLocks });
  const entered = deferred(), release = deferred(), held = nativeLocks.request(KEY + ':transaction', () => { entered.resolve(); return release.promise; });
  await entered.promise;
  const changes = { fridge: true }, a = first.setDoors(changes), b = second.setZone('lot', 'freezer-top'), c = second.toggleDoor('freezer'); changes.fridge = false;
  await new Promise(r => setImmediate(r)); assert.equal(storage.getItem(KEY), null);
  release.resolve(); assert.deepEqual(await Promise.all([a, b, c]), [true, true, true]); await held;
  assert.deepEqual(first.getState(), { version: 1, doors: { freezer: true, fridge: true }, placements: { lot: 'freezer-top' } });
});

test('a rejected lock does not write without coordination or touch inventory and sync keys', async () => {
  const original = { 'use-me-first-state-v5': '{inventory-source}', 'use-me-first-sync-code-v1': 'existing-sync-code' };
  const storage = memory(original), state = createKitchenState({ storage, locks: { request: async () => { throw new Error('SecurityError'); } } });
  assert.equal(await state.toggleDoor('fridge'), false); assert.equal(storage.getItem(KEY), null); assert.ok(state.error);
  assert.deepEqual(Object.fromEntries(storage.values), original);
  const writable = createKitchenState({ storage }); await writable.toggleDoor('fridge');
  for (const [key, raw] of Object.entries(original)) assert.equal(storage.getItem(key), raw);
});
