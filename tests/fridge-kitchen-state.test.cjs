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
  for (const raw of ['{broken', JSON.stringify({ ...blank(), version: 3 }), JSON.stringify({ ...blank(), doors: { fridge: true } }), JSON.stringify({ ...blank(), placements: { one: 'unknown' } }), JSON.stringify({ ...blank(), extra: true })]) {
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
  assert.deepEqual(second.getState(), { version: 2, doors: { freezer: true, fridge: false }, placements: { lot: 'bottom' }, positions: {} });
});

test('native Web Locks serialize concurrent kitchen edits and capture queued door inputs', { skip: !nativeLocks }, async () => {
  const storage = memory(), first = createKitchenState({ storage, locks: nativeLocks }), second = createKitchenState({ storage, locks: nativeLocks });
  const entered = deferred(), release = deferred(), held = nativeLocks.request(KEY + ':transaction', () => { entered.resolve(); return release.promise; });
  await entered.promise;
  const changes = { fridge: true }, a = first.setDoors(changes), b = second.setZone('lot', 'freezer-top'), c = second.toggleDoor('freezer'); changes.fridge = false;
  await new Promise(r => setImmediate(r)); assert.equal(storage.getItem(KEY), null);
  release.resolve(); assert.deepEqual(await Promise.all([a, b, c]), [true, true, true]); await held;
  assert.deepEqual(first.getState(), { version: 2, doors: { freezer: true, fridge: true }, placements: { lot: 'freezer-top' }, positions: {} });
});

test('a rejected lock does not write without coordination or touch inventory and sync keys', async () => {
  const original = { 'use-me-first-state-v5': '{inventory-source}', 'use-me-first-sync-code-v1': 'existing-sync-code' };
  const storage = memory(original), state = createKitchenState({ storage, locks: { request: async () => { throw new Error('SecurityError'); } } });
  assert.equal(await state.toggleDoor('fridge'), false); assert.equal(storage.getItem(KEY), null); assert.ok(state.error);
  assert.deepEqual(Object.fromEntries(storage.values), original);
  const writable = createKitchenState({ storage }); await writable.toggleDoor('fridge');
  for (const [key, raw] of Object.entries(original)) assert.equal(storage.getItem(key), raw);
});

test('v1 preferences migrate in memory and retain their exact bytes until an actual change', async () => {
  const legacy = { version: 1, doors: { freezer: true, fridge: false }, placements: { lot: 'freezer-middle' } };
  const raw = '  ' + JSON.stringify(legacy) + '\n', storage = memory({ [KEY]: raw }), state = createKitchenState({ storage });
  assert.equal(await state.ready, true);
  assert.deepEqual(state.getState(), { ...legacy, version: 2, positions: {} }); assert.equal(state.positionFor('lot'), null);
  assert.equal(state.zoneFor('lot'), 'freezer-middle'); assert.equal(storage.getItem(KEY), raw);
  assert.equal(await state.setDoors({ freezer: true }), true); assert.equal(storage.getItem(KEY), raw, 'a no-op also keeps the v1 original');
  assert.equal(await state.setPosition('lot', 'freezer-middle', { x: 0.2, y: 0.75 }), true);
  assert.deepEqual(JSON.parse(storage.getItem(KEY)), { ...legacy, version: 2, positions: { lot: { x: 0.2, y: 0.75, z: 1 } } });
});

test('moving a lot commits its zone, coordinates and front layer together once', async () => {
  const storage = memory(), state = createKitchenState({ storage }); await state.setPosition('lot', 'top', { x: 0.1, y: 0.2 });
  const writes = [], updates = [], write = storage.setItem.bind(storage);
  storage.setItem = (key, raw) => { writes.push({ key, value: JSON.parse(raw) }); write(key, raw); };
  state.subscribe(value => updates.push(value));
  assert.equal(await state.setPosition('lot', 'freezer-bottom', { x: 1, y: 0 }), true);
  assert.equal(writes.length, 1); assert.equal(writes[0].key, KEY); assert.equal(updates.length, 1);
  assert.equal(writes[0].value.placements.lot, 'freezer-bottom'); assert.deepEqual(writes[0].value.positions.lot, { x: 1, y: 0, z: 2 });
  assert.deepEqual(updates[0], writes[0].value);
});

test('positions persist independently by ID and returned coordinates cannot mutate stored state', async () => {
  const storage = memory(), state = createKitchenState({ storage });
  const first = { id: 'one', name: '계란' }, second = { id: 'two', name: '계란' };
  await state.setPosition(first.id, 'middle', { x: 0.25, y: 0.5 }); await state.setPosition(second.id, 'middle', { x: 0.25, y: 0.5 });
  assert.deepEqual(state.positionFor(first), { x: 0.25, y: 0.5, z: 1 }); assert.deepEqual(state.positionFor(second), { x: 0.25, y: 0.5, z: 2 });
  const copy = state.positionFor(first); copy.x = 0.9; copy.z = 99;
  const reopened = createKitchenState({ storage }); assert.deepEqual(reopened.positionFor(first), { x: 0.25, y: 0.5, z: 1 });
  assert.equal(reopened.positionFor('missing'), null);
});

test('coordinate validation rejects nonfinite, out-of-range and wrong-typed values without writing', async () => {
  const storage = memory(), state = createKitchenState({ storage }); await state.setPosition('lot', 'top', { x: 0, y: 1 });
  const before = storage.getItem(KEY);
  for (const bad of [null, [], {}, { x: -0.01, y: 0 }, { x: 0, y: 1.01 }, { x: NaN, y: 0 }, { x: 0, y: Infinity }, { x: '0.5', y: 0 }, { x: true, y: 0 }]) {
    assert.equal(await state.setPosition('lot', 'bottom', bad), false); assert.equal(storage.getItem(KEY), before);
  }
  assert.equal(await state.setPosition('lot', 'unknown', { x: 0.5, y: 0.5 }), false);
  assert.equal(await state.setPosition('', 'middle', { x: 0.5, y: 0.5 }), false);
  assert.equal(storage.getItem(KEY), before);
  assert.equal(await state.setPosition('lot', 'middle', { x: 1, y: 0, z: -10 }), true);
  assert.deepEqual(state.positionFor('lot'), { x: 1, y: 0, z: 2 }, 'the setter assigns its own safe front layer');
});

test('zone changes reset coordinates while selecting the same effective zone preserves them', async () => {
  const state = createKitchenState({ storage: memory() }); await state.setPosition('lot', 'top', { x: 0.4, y: 0.6 });
  const saved = state.positionFor('lot'); await state.setZone('lot', 'top'); assert.deepEqual(state.positionFor('lot'), saved);
  await state.setZone('lot', 'middle'); assert.equal(state.positionFor('lot'), null); assert.equal(state.zoneFor('lot'), 'middle');
  await state.updateAsync(draft => { draft.positions.implicit = { x: 0.3, y: 0.7, z: 1 }; });
  await state.setZone('implicit', 'middle'); assert.deepEqual(state.positionFor('implicit'), { x: 0.3, y: 0.7, z: 1 });
  await state.setZone('implicit', 'pantry'); assert.equal(state.positionFor('implicit'), null);
});

test('front and back actions preserve coordinates and other lots relative order', async () => {
  const state = createKitchenState({ storage: memory() });
  await state.setPosition('a', 'top', { x: 0.1, y: 0.2 }); await state.setPosition('b', 'top', { x: 0.3, y: 0.4 }); await state.setPosition('c', 'bottom', { x: 0.5, y: 0.6 });
  assert.equal(await state.changeLayer('a'), true); assert.ok(state.positionFor('a').z > state.positionFor('c').z);
  assert.equal(await state.changeLayer('c', 'back'), true);
  const after = state.getState(); assert.ok(after.positions.c.z < after.positions.b.z); assert.ok(after.positions.b.z < after.positions.a.z);
  assert.deepEqual({ ...after.positions.a, z: 0 }, { x: 0.1, y: 0.2, z: 0 });
  assert.deepEqual({ ...after.positions.b, z: 0 }, { x: 0.3, y: 0.4, z: 0 });
  assert.deepEqual({ ...after.positions.c, z: 0 }, { x: 0.5, y: 0.6, z: 0 });
  assert.deepEqual(after.placements, { a: 'top', b: 'top', c: 'bottom' });
});

test('layer changes never invent coordinates for an unpositioned lot', async () => {
  const storage = memory(), state = createKitchenState({ storage }); await state.setZone('lot', 'bottom'); const before = storage.getItem(KEY);
  assert.equal(await state.changeLayer('lot', 'back'), false); assert.equal(state.positionFor('lot'), null); assert.equal(storage.getItem(KEY), before);
  assert.equal(await state.changeLayer('lot', 'above'), false); assert.equal(storage.getItem(KEY), before);
});

test('front layer overflow renumbers atomically while keeping relative order and coordinates', async () => {
  const seeded = { ...blank(), placements: { a: 'top', b: 'top' }, positions: { a: { x: 0.1, y: 0.2, z: Number.MAX_SAFE_INTEGER }, b: { x: 0.3, y: 0.4, z: Number.MAX_SAFE_INTEGER - 1 } } };
  const storage = memory({ [KEY]: JSON.stringify(seeded) }), state = createKitchenState({ storage });
  assert.equal(await state.setPosition('c', 'top', { x: 0.5, y: 0.6 }), true);
  assert.deepEqual(state.getState().positions, { a: { x: 0.1, y: 0.2, z: 2 }, b: { x: 0.3, y: 0.4, z: 1 }, c: { x: 0.5, y: 0.6, z: 3 } });
  storage.setItem(KEY, JSON.stringify(seeded)); assert.equal(await state.changeLayer('b', 'front'), true);
  assert.deepEqual(state.positionFor('a'), { x: 0.1, y: 0.2, z: 2 }); assert.deepEqual(state.positionFor('b'), { x: 0.3, y: 0.4, z: 3 });
});

test('malformed v2 positions block saves and preserve the original record', async () => {
  const invalid = [null, [], { lot: null }, { lot: { x: 0, y: 0 } }, { lot: { x: -1, y: 0, z: 1 } }, { lot: { x: 0, y: 2, z: 1 } }, { lot: { x: 0, y: 0, z: 0 } }, { lot: { x: 0, y: 0, z: -1 } }, { lot: { x: 0, y: 0, z: 0.5 } }, { lot: { x: 0, y: 0, z: Number.MAX_SAFE_INTEGER + 1 } }, { lot: { x: 0, y: 0, z: 1, other: true } }];
  for (const positions of invalid) {
    const raw = JSON.stringify({ ...blank(), positions }), storage = memory({ [KEY]: raw }), state = createKitchenState({ storage });
    assert.equal(await state.ready, false); assert.equal(await state.setPosition('lot', 'middle', { x: 0.5, y: 0.5 }), false);
    assert.equal(storage.getItem(KEY), raw); assert.equal(state.blocked, true);
  }
});

test('four-door preferences preserve legacy bytes and placements until a panel is actually toggled', async () => {
  for (const version of [1, 2]) {
    const original = { version, doors: { freezer: true, fridge: false }, placements: { oldLot: 'freezer-middle' },
      ...(version === 2 ? { positions: { oldLot: { x: .2, y: .8, z: 3 } } } : {}) };
    const raw = '  ' + JSON.stringify(original) + '\n';
    const storage = memory({ [KEY]: raw }), kitchen = createKitchenState({ storage });
    assert.equal(await kitchen.ready, true);
    assert.deepEqual(kitchen.getDoorPanels(), { fridge: false, 'fridge-right': false, freezer: true, 'freezer-right': true });
    assert.equal(storage.getItem(KEY), raw);
    assert.equal(await kitchen.togglePanel('fridge-right'), true);
    assert.deepEqual(kitchen.getDoorPanels(), { fridge: false, 'fridge-right': true, freezer: true, 'freezer-right': true });
    assert.deepEqual(kitchen.getState().placements, original.placements);
    assert.deepEqual(kitchen.getState().positions, original.positions || {});
    assert.deepEqual(createKitchenState({ storage }).getState(), kitchen.getState());
  }
});

test('four physical panels persist independently and legacy group controls still operate both panels', async () => {
  const storage = memory(), kitchen = createKitchenState({ storage });
  for (const panel of ['fridge', 'fridge-right', 'freezer', 'freezer-right']) {
    assert.equal(await kitchen.togglePanel(panel), true);
    assert.equal(kitchen.getDoorPanels()[panel], true);
  }
  await kitchen.togglePanel('fridge');
  assert.equal(kitchen.getDoorPanels().fridge, false);
  assert.equal(kitchen.getDoorPanels()['fridge-right'], true);
  const returned = kitchen.getDoorPanels(); returned['freezer-right'] = false;
  assert.equal(kitchen.getDoorPanels()['freezer-right'], true);
  await kitchen.setDoors({ fridge: false });
  assert.deepEqual(kitchen.getDoorPanels(), { fridge: false, 'fridge-right': false, freezer: true, 'freezer-right': true });
  await kitchen.toggleDoor('fridge');
  assert.deepEqual(kitchen.getDoorPanels(), { fridge: true, 'fridge-right': true, freezer: true, 'freezer-right': true });
  const before = storage.getItem(KEY);
  assert.equal(await kitchen.togglePanel('unknown'), false);
  assert.equal(storage.getItem(KEY), before);
});

test('invalid four-panel extensions block saves without overwriting the original view record', async () => {
  for (const panels of [null, [], {}, { fridge: true }, { fridge: true, 'fridge-right': true, freezer: false, 'freezer-right': 1 },
    { fridge: false, 'fridge-right': false, freezer: false, 'freezer-right': false, extra: true }]) {
    const raw = JSON.stringify({ ...blank(), panels }), storage = memory({ [KEY]: raw }), kitchen = createKitchenState({ storage });
    assert.equal(await kitchen.ready, false);
    assert.equal(await kitchen.togglePanel('fridge-right'), false);
    assert.equal(storage.getItem(KEY), raw);
  }
});

test('concurrent panel and right-freezer position changes retain both edits under Web Locks', { skip: !nativeLocks }, async () => {
  const storage = memory(), a = createKitchenState({ storage, locks: nativeLocks }), b = createKitchenState({ storage, locks: nativeLocks });
  assert.deepEqual(await Promise.all([a.togglePanel('fridge-right'), b.togglePanel('freezer-right'), a.setPosition('lot', 'freezer-right-bottom', { x: .75, y: .4 })]), [true, true, true]);
  const reopened = createKitchenState({ storage });
  assert.deepEqual(reopened.getDoorPanels(), { fridge: false, 'fridge-right': true, freezer: false, 'freezer-right': true });
  assert.equal(reopened.zoneFor('lot'), 'freezer-right-bottom');
  assert.deepEqual(reopened.positionFor('lot'), { x: .75, y: .4, z: 1 });
});

test('failed position storage never commits half a move or emits a successful change', async () => {
  const storage = memory(), state = createKitchenState({ storage }); await state.setPosition('lot', 'top', { x: 0.2, y: 0.3 });
  const before = storage.getItem(KEY), updates = []; state.subscribe(value => updates.push(value)); storage.fail = true;
  assert.equal(await state.setPosition('lot', 'freezer-bottom', { x: 0.8, y: 0.9 }), false);
  assert.equal(storage.getItem(KEY), before); assert.equal(state.zoneFor('lot'), 'top'); assert.deepEqual(state.positionFor('lot'), { x: 0.2, y: 0.3, z: 1 });
  assert.equal(updates.length, 0);
});

test('hostile IDs remain own position properties through moves, layers and zone resets', async () => {
  const state = createKitchenState({ storage: memory() });
  await state.setPosition('__proto__', 'top', { x: 0.1, y: 0.2 }); await state.setPosition('constructor', 'top', { x: 0.3, y: 0.4 });
  assert.equal(await state.changeLayer('__proto__', 'front'), true); assert.equal(await state.changeLayer('constructor', 'back'), true);
  assert.ok(Object.prototype.hasOwnProperty.call(state.getState().positions, '__proto__'));
  assert.ok(state.positionFor('__proto__').z > state.positionFor('constructor').z);
  await state.setZone('__proto__', 'middle'); assert.equal(state.positionFor('__proto__'), null); assert.equal(state.zoneFor('__proto__'), 'middle');
  assert.deepEqual(state.positionFor('constructor'), { x: 0.3, y: 0.4, z: 1 });
});

test('native locks preserve concurrent coordinates, layers and captured pointer values', { skip: !nativeLocks }, async () => {
  const storage = memory(), first = createKitchenState({ storage, locks: nativeLocks }), second = createKitchenState({ storage, locks: nativeLocks });
  const entered = deferred(), release = deferred(), held = nativeLocks.request(KEY + ':transaction', () => { entered.resolve(); return release.promise; });
  await entered.promise;
  const pointer = { x: 0.1, y: 0.2 }, a = first.setPosition('a', 'middle', pointer), b = second.setPosition('b', 'middle', { x: 0.6, y: 0.7 }); pointer.x = 0.9;
  await new Promise(r => setImmediate(r)); assert.equal(storage.getItem(KEY), null);
  release.resolve(); assert.deepEqual(await Promise.all([a, b]), [true, true]); await held;
  assert.deepEqual(first.getState().positions, { a: { x: 0.1, y: 0.2, z: 1 }, b: { x: 0.6, y: 0.7, z: 2 } });
  assert.deepEqual(await Promise.all([first.changeLayer('a', 'front'), second.changeLayer('b', 'front')]), [true, true]);
  assert.deepEqual(first.positionFor('a'), { x: 0.1, y: 0.2, z: 3 }); assert.deepEqual(first.positionFor('b'), { x: 0.6, y: 0.7, z: 4 });
});

test('commit guards cancel queued moves and layer changes after a lot disappears', { skip: !nativeLocks }, async () => {
  const storage = memory(), state = createKitchenState({ storage, locks: nativeLocks });
  await state.setPosition('lot', 'top', { x: 0.2, y: 0.3 }); const before = storage.getItem(KEY), updates = [];
  state.subscribe(value => updates.push(value));
  const entered = deferred(), release = deferred(), held = nativeLocks.request(KEY + ':transaction', () => { entered.resolve(); return release.promise; });
  await entered.promise;
  let exists = true, calls = 0; const guard = () => { calls++; return exists; };
  const moving = state.setPosition('lot', 'bottom', { x: 0.8, y: 0.9 }, guard), layering = state.changeLayer('lot', 'back', guard);
  await new Promise(r => setImmediate(r)); assert.equal(calls, 0, 'guards run after acquiring the transaction lock'); exists = false;
  release.resolve(); assert.deepEqual(await Promise.all([moving, layering]), [false, false]); await held;
  assert.equal(calls, 2); assert.equal(storage.getItem(KEY), before); assert.equal(updates.length, 0);
  assert.equal(await state.updateAsync(draft => { draft.doors.fridge = true; }, () => false), false); assert.equal(storage.getItem(KEY), before);
});

test('guards must return a synchronous boolean and successful guards allow the commit', async () => {
  const storage = memory(), state = createKitchenState({ storage });
  for (const guard of [() => { throw new Error('No longer valid'); }, () => 1, async () => true, async () => { throw new Error('Rejected async guard'); }, null]) {
    assert.equal(await state.setPosition('lot', 'top', { x: 0.2, y: 0.3 }, guard), false); assert.equal(storage.getItem(KEY), null);
  }
  assert.equal(await state.setPosition('lot', 'top', { x: 0.2, y: 0.3 }, () => true), true);
  assert.deepEqual(state.positionFor('lot'), { x: 0.2, y: 0.3, z: 1 });
});
