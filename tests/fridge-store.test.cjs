const test = require('node:test');
const assert = require('node:assert/strict');
const { webcrypto } = require('node:crypto');
const { createStore, createSyncEngine, keys, blank, remoteState } = require('../use-me-first-store.js');

function memory(entries = {}) {
  const values = new Map(Object.entries(entries));
  return {
    values, fail: false,
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { if (this.fail) throw new Error('QuotaExceededError'); values.set(key, String(value)); },
    removeItem(key) { if (this.fail) throw new Error('SecurityError'); values.delete(key); }
  };
}
const item = (name, quantity = '1개', id = name) => ({ id, name, expiry: '2030-01-01', quantity });
const payload = state => ({ version: 2, ...state });
const copy = x => JSON.parse(JSON.stringify(x));
const code = 'UMF-012345678901234567890123456789012345';
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
function server(initial) {
  const api = { remote: copy(initial), writes: [], successfulWrites: [], expected: [], codes: new Set([code]), updatedAt: '2026-10-20T00:00:00.000Z', getGate: null, putGate: null, gotGet: deferred(), gotPut: deferred(), fail: false };
  api.fetch = async (_, options) => {
    if (api.fail) return { ok: false, status: 503 };
    if (options.method === 'PUT') {
      const { payload: data, expected_updated_at: expected } = JSON.parse(options.body), syncCode = options.headers['x-sync-code'];
      api.writes.push(copy(data)); api.expected.push(expected); api.gotPut.resolve();
      const gate = api.putGate; api.putGate = null; if (gate) await gate.promise;
      if (expected === null ? api.codes.has(syncCode) : !api.codes.has(syncCode) || expected !== api.updatedAt) return { ok: false, status: 409 };
      api.codes.add(syncCode); api.remote = copy(data); api.updatedAt = new Date(Date.parse(api.updatedAt) + 1).toISOString(); api.successfulWrites.push(copy(data));
      const updated_at = api.updatedAt;
      return { ok: true, status: 200, json: async () => ({ ok: true, updated_at, concurrency: 'updated_at-v1' }) };
    }
    const remote = copy(api.remote), updated_at = api.updatedAt; api.gotGet.resolve();
    const gate = api.getGate; api.getGate = null; if (gate) await gate.promise;
    return { ok: true, status: 200, json: async () => ({ payload: remote, updated_at, concurrency: 'updated_at-v1' }) };
  };
  return api;
}
function engine(store, api, options = {}) {
  return createSyncEngine({ store, fetch: api.fetch, url: 'https://unit.invalid/sync', crypto: webcrypto, confirm: () => true, delay: 1, timeout: 500, ...options });
}
const nativeLocks = globalThis.navigator?.locks || require('node:worker_threads').locks;
async function holdStateLock() {
  const entered = deferred(), release = deferred();
  const done = nativeLocks.request(keys.STATE + ':transaction', { mode: 'exclusive' }, () => { entered.resolve(); return release.promise; });
  await entered.promise; return { release: () => release.resolve(), done };
}

test('native Web Locks serialize two stores and their first migration without losing either edit', { skip: !nativeLocks }, async () => {
  const storage = memory({ [keys.ITEMS]: JSON.stringify([{ name: '계란', expiry: '' }]) }), held = await holdStateLock();
  const first = createStore({ storage, locks: nativeLocks }), second = createStore({ storage, locks: nativeLocks });
  const entered = [], a = first.updateAsync(s => { entered.push('a'); s.items.push(item('양파')); }), b = second.updateAsync(s => { entered.push('b'); s.items.push(item('두부')); });
  await new Promise(r => setImmediate(r));
  assert.deepEqual(entered, []); assert.equal(storage.getItem(keys.STATE), null, 'migration also waits for the shared lock');
  held.release(); assert.deepEqual(await Promise.all([a, b]), [true, true]); await held.done;
  assert.deepEqual(first.getState().items.map(x => x.name), ['계란', '양파', '두부']); assert.equal(first.concurrency, 'web-locks'); assert.ok(storage.getItem(keys.ITEMS));
});

test('a migration waiting for its lock rechecks durable state before writing legacy contents', { skip: !nativeLocks }, async () => {
  const storage = memory({ [keys.ITEMS]: '[{"name":"계란"}]' }), held = await holdStateLock(), store = createStore({ storage, locks: nativeLocks });
  const latest = { version: 5, revision: 4, ...blank(), items: [item('두부')] };
  storage.setItem(keys.STATE, JSON.stringify(latest)); held.release(); assert.equal(await store.ready, true); await held.done;
  assert.deepEqual(store.getState().items, latest.items); assert.equal(JSON.parse(storage.getItem(keys.STATE)).revision, 4);
});

test('a rejected Web Lock never falls back to an unlocked write', async () => {
  const storage = memory(), original = createStore({ storage }); original.update(s => s.items.push(item('계란')));
  const before = storage.getItem(keys.STATE), store = createStore({ storage, locks: { request: async () => { throw new Error('SecurityError'); } } });
  assert.equal(await store.updateAsync(s => s.items.push(item('두부'))), false); assert.equal(storage.getItem(keys.STATE), before); assert.match(store.error, /저장 순서/);
});

test('sync rechecks the local snapshot after acquiring a delayed native lock', { skip: !nativeLocks }, async () => {
  const storage = memory({ [keys.SYNC]: code }); createStore({ storage });
  const store = createStore({ storage, locks: nativeLocks }), held = await holdStateLock();
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote)), sync = engine(store, api), loading = sync.reload();
  await api.gotGet.promise; await new Promise(r => setImmediate(r));
  store.update(s => s.items.push(item('계란'))); // This test writer already owns the lock above.
  held.release(); assert.equal(await loading, false); await held.done;
  assert.equal(sync.status.state, 'conflict'); assert.deepEqual(store.getState().items.map(x => x.name), ['계란']); assert.equal(storage.getItem(keys.RECOVERY), null); sync.destroy();
});

test('sync rechecks a disconnected code after waiting for the native commit lock', { skip: !nativeLocks }, async () => {
  const storage = memory({ [keys.SYNC]: code }); createStore({ storage });
  const store = createStore({ storage, locks: nativeLocks }), held = await holdStateLock();
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote)), sync = engine(store, api), loading = sync.reload();
  await api.gotGet.promise; await new Promise(r => setImmediate(r)); storage.removeItem(keys.SYNC);
  held.release(); assert.equal(await loading, false); await held.done;
  assert.equal(storage.getItem(keys.SYNC), null); assert.deepEqual(store.getState(), blank()); sync.destroy();
});

test('a recovery waiting for a native lock cannot replace a newer local edit', { skip: !nativeLocks }, async () => {
  const storage = memory(), original = createStore({ storage }); original.update(s => s.items.push(item('계란'))); original.backup();
  const store = createStore({ storage, locks: nativeLocks }), held = await holdStateLock(), api = server(payload(blank())), sync = engine(store, api), restoring = sync.restore();
  await new Promise(r => setImmediate(r)); store.update(s => s.items.push(item('두부')));
  held.release(); assert.equal(await restoring, false); await held.done;
  assert.deepEqual(store.getState().items.map(x => x.name), ['계란', '두부']); assert.equal(api.writes.length, 0); sync.destroy();
});

test('a queued disconnect cannot remove a newer connection selected by another tab', { skip: !nativeLocks }, async () => {
  const storage = memory({ [keys.SYNC]: code }); createStore({ storage });
  const store = createStore({ storage, locks: nativeLocks }), held = await holdStateLock(), api = server(null), sync = engine(store, api);
  const disconnecting = sync.disconnect(); await new Promise(r => setImmediate(r));
  const newer = 'UMF-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'; storage.setItem(keys.SYNC, newer);
  held.release(); assert.equal(await disconnecting, false); await held.done;
  assert.equal(storage.getItem(keys.SYNC), newer); sync.destroy();
});

test('legacy migration keeps original keys and gives quantities to one duplicate lot only', () => {
  const original = JSON.stringify([{ name: '계란', expiry: '2026-10-21' }, { name: '계란', expiry: '2026-10-25' }]);
  const storage = memory({ [keys.ITEMS]: original, [keys.QUANTITIES]: JSON.stringify({ 계란: '10개' }), [keys.MEALS]: JSON.stringify([{ name: '계란 볶음밥', ts: 1700000000000, day: '2023-11-14' }]), [keys.FAVORITES]: '["계란 볶음밥"]' });
  const store = createStore({ storage }), state = store.getState();
  assert.equal(state.items.length, 2); assert.equal(state.items[0].quantity, '10개'); assert.equal(state.items[1].quantity, '');
  assert.notEqual(state.items[0].id, state.items[1].id); assert.equal(state.meals.length, 1); assert.deepEqual(state.favorites, ['계란 볶음밥']);
  assert.equal(storage.getItem(keys.ITEMS), original); assert.ok(storage.getItem(keys.QUANTITIES));
  const reopened = createStore({ storage }); assert.deepEqual(reopened.getState(), state);
});

test('same-name lots edit and delete independently', () => {
  const store = createStore({ storage: memory() });
  store.update(s => s.items.push(item('계란', '10개', 'one'), item('계란', '2개', 'two')));
  store.update(s => { s.items.find(x => x.id === 'two').quantity = '0개'; });
  assert.deepEqual(store.getState().items.map(x => x.quantity), ['10개', '0개']);
  store.update(s => { s.items = s.items.filter(x => x.id !== 'one'); });
  assert.deepEqual(store.getState().items, [item('계란', '0개', 'two')]);
});

test('each tab commits against the latest durable state, even before a storage event', () => {
  const storage = memory(), first = createStore({ storage }), second = createStore({ storage });
  first.update(s => s.items.push(item('계란')));
  second.update(s => s.items.push(item('양파')));
  assert.deepEqual(first.getState().items.map(x => x.name), ['계란', '양파']);
});

test('snapshot guard prevents a late import from replacing a new local edit', () => {
  const store = createStore({ storage: memory() }), before = store.snapshot();
  store.update(s => s.items.push(item('계란')));
  assert.equal(store.replace(blank(), { expected: before, origin: 'sync' }), false);
  assert.equal(store.getState().items[0].name, '계란');
});

test('quota error preserves the successful previous record and reports failure', () => {
  const storage = memory(), store = createStore({ storage });
  store.update(s => s.items.push(item('계란'))); const raw = storage.getItem(keys.STATE); storage.fail = true;
  assert.equal(store.update(s => s.items.push(item('양파'))), false);
  assert.equal(storage.getItem(keys.STATE), raw); assert.equal(store.getState().items.length, 1); assert.match(store.error, /저장하지 못/);
});

test('unavailable storage does not crash or falsely acknowledge a save', () => {
  const store = createStore({ storage: null });
  assert.deepEqual(store.getState(), blank()); assert.equal(store.update(s => s.items.push(item('계란'))), false); assert.ok(store.error);
});

test('invalid or future v5 data is retained byte for byte without overwrite', () => {
  for (const original of ['{bad-json', JSON.stringify({ version: 6, items: [] }), JSON.stringify({ version: 5, items: [null] })]) {
    const storage = memory({ [keys.STATE]: original }), store = createStore({ storage });
    assert.doesNotThrow(() => store.getState()); assert.equal(store.update(s => s.items.push(item('계란'))), false);
    assert.equal(storage.getItem(keys.STATE), original); assert.ok(store.blocked);
  }
});

test('a storage clear is not resurrected by a stale tab', () => {
  const storage = memory(), first = createStore({ storage }), second = createStore({ storage });
  first.update(s => s.items.push(item('계란'))); storage.removeItem(keys.STATE);
  second.update(s => s.items.push(item('양파')));
  assert.deepEqual(second.getState().items.map(x => x.name), ['양파']);
});

test('remote v1 preserves local-only history and known quantities without copying to all lots', () => {
  const local = blank(); local.items = [item('계란', '8개', 'one'), item('계란', '2개', 'two')];
  local.meals = [{ id: 'm', name: '계란볶음밥', ts: 1700000000000, day: '2023-11-14' }]; local.favorites = ['계란볶음밥'];
  const old = { version: 1, items: [{ name: '계란', expiry: '2030-01-01' }, { name: '계란', expiry: '2030-01-01' }], season: [], pantry: [], customSeason: [], customPantry: [] };
  const remote = remoteState(old, local);
  assert.deepEqual(remote.items.map(x => x.quantity), ['8개', '2개']); assert.deepEqual(remote.meals, local.meals); assert.deepEqual(remote.favorites, local.favorites);
});

test('invalid remote payload cannot clear local fields', () => {
  assert.throws(() => remoteState({ version: 2, items: [] }));
  assert.throws(() => remoteState({ version: 2, ...blank(), items: [null] }));
});

test('failed new-code request leaves current code and records unchanged', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage });
  store.update(s => s.items.push(item('계란')));
  const api = server(payload(blank())); api.fail = true; const sync = engine(store, api);
  assert.equal(await sync.create(), false); assert.equal(storage.getItem(keys.SYNC), code); assert.equal(store.getState().items.length, 1); assert.equal(sync.status.state, 'error'); sync.destroy();
});

test('changes made during a PUT are sent in a following request, not lost', async () => {
  const store = createStore({ storage: memory() }), api = server(payload(blank())); api.putGate = deferred(); const release = api.putGate;
  store.update(s => s.items.push(item('계란'))); const sync = engine(store, api), creating = sync.create();
  await api.gotPut.promise; store.update(s => s.items.push(item('양파'))); release.resolve();
  assert.equal(await creating, true); assert.equal(api.writes.length, 2);
  assert.deepEqual(api.remote.items.map(x => x.name), ['계란', '양파']); assert.deepEqual(store.getState().items.map(x => x.name), ['계란', '양파']); assert.equal(sync.status.state, 'ready'); sync.destroy();
});

test('changes while a remote GET is pending prevent the stale pull from applying', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage });
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote)); api.getGate = deferred(); const release = api.getGate;
  const sync = engine(store, api), connecting = sync.connect(code);
  await api.gotGet.promise; store.update(s => s.items.push(item('계란'))); release.resolve();
  assert.equal(await connecting, false); assert.deepEqual(store.getState().items.map(x => x.name), ['계란']); assert.equal(sync.status.state, 'conflict'); assert.equal(api.writes.length, 0); sync.destroy();
});

test('offline edits plus changed server data show conflict without replacing either copy', async () => {
  const storage = memory(), store = createStore({ storage }), api = server(payload(blank())), first = engine(store, api);
  store.update(s => s.items.push(item('계란'))); await first.create(); first.destroy();
  store.update(s => s.items.push(item('양파'))); api.remote.items.push(item('두부'));
  const second = engine(store, api); assert.equal(await second.initialize(), false);
  assert.deepEqual(store.getState().items.map(x => x.name), ['계란', '양파']); assert.deepEqual(api.remote.items.map(x => x.name), ['계란', '두부']); assert.equal(second.status.state, 'conflict'); second.destroy();
});

test('an explicitly accepted import has a usable local recovery snapshot', async () => {
  const storage = memory(), store = createStore({ storage }); store.update(s => s.items.push(item('계란')));
  const remote = blank(); remote.items = [item('두부')]; remote.favorites = ['두부 스테이크'];
  const api = server(payload(remote)), sync = engine(store, api); assert.equal(await sync.connect(code), true);
  assert.equal(store.getState().items[0].name, '두부'); assert.equal(store.recovery().items[0].name, '계란');
  assert.equal(await sync.restore(), true); assert.equal(store.getState().items[0].name, '계란'); assert.equal(api.writes.length, 0); sync.destroy();
});

test('declining a remote replacement leaves the current local state and code', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage }); store.update(s => s.items.push(item('계란')));
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote));
  const sync = engine(store, api, { confirm: () => false }); assert.equal(await sync.connect('UMF-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'), false);
  assert.equal(store.getState().items[0].name, '계란'); assert.equal(storage.getItem(keys.SYNC), code); sync.destroy();
});

test('successful payload carries quantities, meal history, favorites and pantry together', async () => {
  const store = createStore({ storage: memory() });
  store.update(s => { s.items.push(item('계란', '3개')); s.season = ['간장']; s.pantry = ['밥/즉석밥']; s.favorites = ['계란 볶음밥']; s.meals.push({ id: 'meal', name: '계란 볶음밥', ts: 1700000000000, day: '2023-11-14' }); });
  const api = server(payload(blank())), sync = engine(store, api); await sync.create();
  assert.deepEqual(remoteState(api.remote), store.getState()); assert.equal(api.remote.version, 2); sync.destroy();
});

test('a refused overwrite does not send PUT or replace the current remote data', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage }); store.update(s => s.items.push(item('계란')));
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote));
  const sync = engine(store, api, { confirm: () => false }); assert.equal(await sync.upload(), false);
  assert.equal(api.writes.length, 0); assert.deepEqual(api.remote, payload(remote)); assert.equal(store.getState().items[0].name, '계란'); sync.destroy();
});

test('timeout ends the busy state and keeps the local state and code', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage }); store.update(s => s.items.push(item('계란')));
  const sync = createSyncEngine({ store, fetch: () => new Promise(() => {}), url: 'https://unit.invalid/sync', timeout: 5 });
  assert.equal(await sync.reload(), false); assert.equal(sync.status.busy, false); assert.equal(sync.status.state, 'error');
  assert.equal(store.getState().items[0].name, '계란'); assert.equal(storage.getItem(keys.SYNC), code); sync.destroy();
});

test('failed backup storage prevents remote import before it can replace local data', async () => {
  const storage = memory(), store = createStore({ storage }); store.update(s => s.items.push(item('계란')));
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote)), sync = engine(store, api); storage.fail = true;
  assert.equal(await sync.connect(code), false); assert.equal(store.getState().items[0].name, '계란'); assert.equal(storage.getItem(keys.SYNC), null); sync.destroy();
});

test('corrupt local storage cannot be uploaded or create a new sync code', async () => {
  for (const prepare of ['corrupt-at-start', 'corrupt-after-read']) {
    const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage });
    if (prepare === 'corrupt-after-read') store.update(s => s.items.push(item('계란')));
    const original = '{malformed-private-record'; storage.setItem(keys.STATE, original);
    const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote)); const sync = engine(store, api);
    assert.equal(await sync.upload(), false); assert.equal(await sync.create(), false);
    assert.equal(api.writes.length, 0); assert.deepEqual(api.remote, payload(remote));
    assert.equal(storage.getItem(keys.SYNC), code); assert.equal(storage.getItem(keys.STATE), original);
    assert.equal(sync.status.state, 'error'); assert.ok(store.blocked); sync.destroy();
  }
});

test('corruption during the remote preflight is checked again before PUT', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage }); store.update(s => s.items.push(item('계란')));
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote)); api.getGate = deferred(); const release = api.getGate;
  const sync = engine(store, api), uploading = sync.upload(); await api.gotGet.promise;
  storage.setItem(keys.STATE, '{broken-after-preflight'); release.resolve();
  assert.equal(await uploading, false); assert.equal(api.writes.length, 0); assert.deepEqual(api.remote, payload(remote)); sync.destroy();
});

test('corruption during overwrite confirmation is checked before any PUT', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage }); store.update(s => s.items.push(item('계란')));
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote));
  const sync = engine(store, api, { confirm: () => { storage.setItem(keys.STATE, '{broken-during-confirm'); return true; } });
  assert.equal(await sync.upload(), false); assert.equal(api.writes.length, 0); assert.deepEqual(api.remote, payload(remote)); sync.destroy();
});

test('backup refuses unreadable state and retains the earlier valid recovery snapshot', () => {
  const storage = memory(), store = createStore({ storage }); store.update(s => s.items.push(item('계란'))); assert.equal(store.backup(), true);
  const recovery = storage.getItem(keys.RECOVERY); storage.setItem(keys.STATE, '{broken');
  assert.equal(store.backup(), false); assert.equal(storage.getItem(keys.RECOVERY), recovery); assert.equal(storage.getItem(keys.STATE), '{broken');
});

test('explicit recovery restores a blocked store while preserving the unreadable original', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage }); store.update(s => s.items.push(item('계란', '3개'))); store.backup();
  const original = '{broken-original-한글'; storage.setItem(keys.STATE, original); store.getState(); assert.equal(store.blocked, true);
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote)), sync = engine(store, api);
  assert.equal(await sync.restore(), true); assert.equal(store.blocked, false); assert.equal(store.getState().items[0].quantity, '3개');
  assert.ok(JSON.parse(storage.getItem(keys.RECOVERY_ARCHIVE)).some(x => x.raw === original)); assert.equal(api.writes.length, 0);
  assert.deepEqual(api.remote, payload(remote)); assert.equal(sync.status.state, 'conflict'); sync.destroy();
});

test('recovery aborts if the raw original cannot be archived', async () => {
  const storage = memory(), store = createStore({ storage }); store.update(s => s.items.push(item('계란'))); store.backup();
  storage.setItem(keys.STATE, '{broken-original'); storage.fail = true;
  const api = server(payload(blank())), sync = engine(store, api); assert.equal(await sync.restore(), false);
  assert.equal(storage.getItem(keys.STATE), '{broken-original'); assert.equal(api.writes.length, 0); sync.destroy();
});

test('malformed raw v2 server data is rejected without normalizing it into empty records', async () => {
  const badPayloads = [
    { version: 2, ...blank(), items: [null] },
    { version: 2, ...blank(), items: [{ name: '계란' }] },
    { version: 2, ...blank(), items: [{ ...item('계란'), quantity: {} }] },
    { version: 2, ...blank(), meals: [null] },
    { version: 2, ...blank(), meals: [{ id: 'm', name: '계란 볶음밥', ts: 1e100, day: '2026-10-20' }] },
    { version: 2, ...blank(), favorites: [null] },
    { version: 2, ...blank(), season: [3] }
  ];
  for (const bad of badPayloads) {
    assert.throws(() => remoteState(bad));
    const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage }); store.update(s => s.items.push(item('양파')));
    const before = storage.getItem(keys.STATE), api = server(bad), sync = engine(store, api);
    assert.equal(await sync.reload(), false); assert.equal(storage.getItem(keys.STATE), before); assert.equal(api.writes.length, 0); sync.destroy();
  }
});

test('an invalid recovery snapshot is never used to replace unreadable data', async () => {
  const storage = memory({ [keys.STATE]: '{original', [keys.RECOVERY]: '{also-broken', [keys.SYNC]: code });
  const store = createStore({ storage }), api = server(payload(blank())), sync = engine(store, api);
  assert.equal(await sync.restore(), false); assert.equal(storage.getItem(keys.STATE), '{original'); assert.equal(storage.getItem(keys.RECOVERY), '{also-broken'); assert.equal(api.writes.length, 0); sync.destroy();
});

test('a delayed response for connection A cannot revert a different tabs connection B', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage }), secondCode = 'UMF-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';
  const a = blank(); a.items = [item('계란')]; const b = blank(); b.items = [item('두부')];
  const gate = deferred(), started = deferred(), ready = deferred(); const sent = [];
  const sync = createSyncEngine({ store, url: 'https://unit.invalid/sync', timeout: 500, confirm: () => true, onStatus: s => { if (s.state === 'ready' && storage.getItem(keys.SYNC) === secondCode) ready.resolve(); }, fetch: async (_, options) => {
    sent.push(options.method);
    if (options.headers['x-sync-code'] === code) { started.resolve(); await gate.promise; return { ok: true, status: 200, json: async () => ({ payload: payload(a) }) }; }
    return { ok: true, status: 200, json: async () => ({ payload: payload(b) }) };
  } });
  const loading = sync.reload(); await started.promise;
  store.replace(b, { origin: 'external' }); storage.setItem(keys.SYNC, secondCode); gate.resolve();
  assert.equal(await loading, false); await ready.promise;
  assert.equal(storage.getItem(keys.SYNC), secondCode); assert.deepEqual(store.getState(), b); assert.ok(sent.every(x => x === 'GET')); sync.destroy();
});

test('disconnecting in another tab while a pull is pending prevents reconnection by the late result', async () => {
  const storage = memory({ [keys.SYNC]: code }), store = createStore({ storage }); store.update(s => s.items.push(item('계란')));
  const remote = blank(); remote.items = [item('두부')]; const api = server(payload(remote)); api.getGate = deferred(); const release = api.getGate;
  const sync = engine(store, api), loading = sync.reload(); await api.gotGet.promise; storage.removeItem(keys.SYNC); release.resolve();
  assert.equal(await loading, false); assert.equal(storage.getItem(keys.SYNC), null); assert.equal(store.getState().items[0].name, '계란'); assert.equal(api.writes.length, 0); sync.destroy();
});

// Execute the production modal-save function with real stores and explicit form inputs.
async function saveOpenEditor(store, original, changes) {
  const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
  const source = fs.readFileSync(path.join(__dirname, '../use-me-first-core-final.js'), 'utf8');
  const body = source.slice(source.indexOf('  async function saveItem(){'), source.indexOf('  function openCustom('));
  const form = { '#name': { value: changes.name || original.name }, '#expiry': { value: original.expiry }, '#umfQty': { value: changes.quantity ?? original.quantity } };
  let error = '', closed = false;
  await vm.runInNewContext(body + '\nsaveItem();', { store, $: selector => form[selector], domain: { daysLeft: () => 1 }, editingId: original.id, editingOriginal: JSON.stringify(original), savingItem: false, modalVersion: 0, formError: message => { error = message; }, closeModal: () => { closed = true; } });
  return { error, closed };
}

test('saving an old edit form cannot overwrite a newer edit of the same lot', async () => {
  const storage = memory(), first = createStore({ storage }), second = createStore({ storage });
  first.update(s => s.items.push(item('계란', '10개', 'lot'))); const opened = first.getState().items[0];
  second.update(s => { s.items[0].quantity = '4개'; });
  const result = await saveOpenEditor(first, opened, { quantity: '9개' });
  assert.match(result.error, /다른 화면에서 수정/); assert.equal(result.closed, false); assert.equal(first.getState().items[0].quantity, '4개');
});

test('an open item editor still saves after an unrelated lot changes in another tab', async () => {
  const storage = memory(), first = createStore({ storage }), second = createStore({ storage });
  first.update(s => s.items.push(item('계란', '10개', 'lot'))); const opened = first.getState().items[0]; second.update(s => s.items.push(item('두부')));
  const result = await saveOpenEditor(first, opened, { quantity: '9개' });
  assert.equal(result.error, ''); assert.equal(result.closed, true); assert.deepEqual(first.getState().items.map(x => x.quantity), ['9개', '1개']);
});

test('an old edit form cannot recreate a lot deleted in another tab', async () => {
  const storage = memory(), first = createStore({ storage }), second = createStore({ storage });
  first.update(s => s.items.push(item('계란', '10개', 'lot'))); const opened = first.getState().items[0]; second.update(s => { s.items = []; });
  const result = await saveOpenEditor(first, opened, { quantity: '9개' });
  assert.match(result.error, /다른 화면에서 삭제/); assert.equal(result.closed, false); assert.deepEqual(first.getState().items, []);
});

test('two clients with the same server timestamp cannot both overwrite the record', async () => {
  const first = createStore({ storage: memory({ [keys.SYNC]: code }) }), second = createStore({ storage: memory({ [keys.SYNC]: code }) });
  first.update(s => s.items.push(item('계란'))); second.update(s => s.items.push(item('두부')));
  const api = server(payload(blank())); api.putGate = deferred(); const release = api.putGate;
  const a = engine(first, api), b = engine(second, api), firstUpload = a.upload();
  await api.gotPut.promise; assert.equal(await b.upload(), true); release.resolve();
  assert.equal(await firstUpload, false); assert.equal(a.status.state, 'conflict');
  assert.deepEqual(api.remote.items.map(x => x.name), ['두부']); assert.deepEqual(first.getState().items.map(x => x.name), ['계란']);
  assert.equal(api.expected[0], api.expected[1]); assert.equal(api.successfulWrites.length, 1);
  first.update(s => s.items.push(item('양파'))); await new Promise(r => setTimeout(r, 5));
  assert.equal(api.writes.length, 2, 'a conflict stays pending until the user chooses a resolution'); a.destroy(); b.destroy();
});

test('an old server without CAS metadata cannot receive an existing-code PUT', async () => {
  const store = createStore({ storage: memory({ [keys.SYNC]: code }) }); store.update(s => s.items.push(item('계란')));
  const methods = [], sync = createSyncEngine({ store, url: 'https://unit.invalid/sync', confirm: () => true, fetch: async (_, options) => {
    methods.push(options.method); return { ok: true, status: 200, json: async () => ({ payload: payload(blank()) }) };
  } });
  assert.equal(await sync.upload(), false); assert.deepEqual(methods, ['GET']); assert.equal(sync.status.state, 'error'); assert.match(sync.status.text, /버전/); sync.destroy();
});

test('a missing remote record has a specific not-found message and preserves local data', async () => {
  const store = createStore({ storage: memory({ [keys.SYNC]: code }) }); store.update(s => s.items.push(item('계란')));
  const api = server(null), sync = engine(store, api); assert.equal(await sync.reload(), false);
  assert.match(sync.status.text, /찾지 못/); assert.equal(store.getState().items[0].name, '계란'); assert.equal(api.writes.length, 0); sync.destroy();
});

// Run the actual Edge Function handler. Only the database transport is replaced;
// its conditional predicates execute against a shared record map atomically.
function edgeFunction() {
  const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
  const { stripTypeScriptTypes } = require('node:module');
  const source = fs.readFileSync(path.join(__dirname, '../supabase/functions/use-me-first-sync/index.ts'), 'utf8').replace(/^import .*;\n/gm, '');
  const records = new Map(); let handler;
  class FixedDate extends Date {
    constructor(...args) { super(...(args.length ? args : ['2026-10-20T00:00:00.000Z'])); }
    static now() { return Date.parse('2026-10-20T00:00:00.000Z'); }
  }
  const createClient = () => ({ from(table) {
    assert.equal(table, 'use_me_first_sync'); let operation = 'select', value; const filters = {};
    return {
      select() { return this; }, eq(key, v) { filters[key] = v; return this; },
      insert(v) { operation = 'insert'; value = v; return this; }, update(v) { operation = 'update'; value = v; return this; },
      async maybeSingle() {
        const hash = filters.sync_hash || value?.sync_hash, current = records.get(hash);
        if (operation === 'insert') {
          if (current) return { data: null, error: { code: '23505' } };
          records.set(hash, copy(value)); return { data: { updated_at: value.updated_at }, error: null };
        }
        if (operation === 'update') {
          assert.equal(typeof filters.updated_at, 'string', 'an update must have the expected timestamp predicate');
          if (!current || Date.parse(current.updated_at) !== Date.parse(filters.updated_at)) return { data: null, error: null };
          records.set(hash, { ...current, ...copy(value) }); return { data: { updated_at: value.updated_at }, error: null };
        }
        return { data: current ? copy(current) : null, error: null };
      }
    };
  } });
  vm.runInNewContext(stripTypeScriptTypes(source), {
    Deno: { serve: fn => { handler = fn; }, env: { get: name => name === 'SUPABASE_URL' ? 'https://unit.invalid' : 'test-only-key' } },
    createClient, crypto: webcrypto, TextEncoder, Response, Date: FixedDate
  });
  return {
    records,
    request(method = 'GET', body, syncCode = code) {
      return handler(new Request('https://unit.invalid/sync', { method, headers: { 'x-sync-code': syncCode, 'content-type': 'application/json' }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) }));
    }
  };
}

test('the Edge Function advertises CAS, creates with null expectation and returns not-found as null', async () => {
  const edge = edgeFunction(), missing = await edge.request(), empty = await missing.json();
  assert.deepEqual(empty, { payload: null, updated_at: null, concurrency: 'updated_at-v1' });
  const created = await edge.request('PUT', { payload: payload(blank()), expected_updated_at: null }), result = await created.json();
  assert.equal(created.status, 200); assert.equal(result.ok, true); assert.equal(result.concurrency, 'updated_at-v1');
  assert.deepEqual((await (await edge.request()).json()).payload, payload(blank()));
  const duplicate = await edge.request('PUT', { payload: payload(blank()), expected_updated_at: null });
  assert.equal(duplicate.status, 409); assert.equal(duplicate.headers.get('access-control-allow-origin'), '*');
});

test('the actual Edge Function allows one CAS winner and advances timestamps within the same millisecond', async () => {
  const edge = edgeFunction(), created = await (await edge.request('PUT', { payload: payload(blank()), expected_updated_at: null })).json();
  const a = blank(); a.items = [item('계란')]; const b = blank(); b.items = [item('두부')];
  const results = await Promise.all([a, b].map(value => edge.request('PUT', { payload: payload(value), expected_updated_at: created.updated_at })));
  assert.deepEqual(results.map(x => x.status).sort(), [200, 409]);
  const winner = await results.find(x => x.status === 200).json(); assert.ok(Date.parse(winner.updated_at) > Date.parse(created.updated_at));
  const next = await edge.request('PUT', { payload: payload(a), expected_updated_at: winner.updated_at });
  assert.equal(next.status, 200); assert.ok(Date.parse((await next.json()).updated_at) > Date.parse(winner.updated_at));
  assert.equal(results.find(x => x.status === 409).headers.get('access-control-allow-origin'), '*');
});

test('legacy clients may create but receive 428 before overwriting an existing Edge Function record', async () => {
  const edge = edgeFunction(), a = blank(); a.items = [item('계란')];
  assert.equal((await edge.request('PUT', { payload: payload(a) })).status, 200);
  const oldUpdate = await edge.request('PUT', { payload: payload(blank()) });
  assert.equal(oldUpdate.status, 428); assert.equal(oldUpdate.headers.get('access-control-allow-origin'), '*');
  assert.equal((await oldUpdate.json()).error, 'reload_required'); assert.deepEqual((await (await edge.request()).json()).payload, payload(a));
});

test('the Edge Function rejects malformed v2 payloads and timestamp types before writing', async () => {
  const edge = edgeFunction();
  for (const bad of [{ ...payload(blank()), items: [null] }, { ...payload(blank()), items: [{ ...item('계란'), quantity: {} }] }, { ...payload(blank()), favorites: [false] }, { ...payload(blank()), meals: [null] }]) {
    assert.equal((await edge.request('PUT', { payload: bad, expected_updated_at: null })).status, 400);
  }
  for (const expected_updated_at of [42, {}, 'not-a-date']) assert.equal((await edge.request('PUT', { payload: payload(blank()), expected_updated_at })).status, 400);
  assert.equal(edge.records.size, 0);
});
