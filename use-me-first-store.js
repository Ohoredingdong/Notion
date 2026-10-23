/* A single durable state for every panel. Legacy storage is retained for recovery. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else {
    let storage, locks;
    try { storage = root.localStorage; } catch (_) { storage = null; }
    try { locks = root.navigator?.locks; } catch (_) { locks = null; }
    root.UMFStore = api.createStore({ storage, eventTarget: root, crypto: root.crypto, locks });
    root.UMFStore.createSyncEngine = api.createSyncEngine;
  }
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const keys = Object.freeze({
    STATE: 'use-me-first-state-v5', ITEMS: 'use-me-first-v4',
    SEASON: 'use-me-first-seasonings-v1', PANTRY: 'use-me-first-pantry-v1',
    CUSTOM_SEASON: 'use-me-first-custom-seasonings-v1', CUSTOM_PANTRY: 'use-me-first-custom-pantry-v1',
    QUANTITIES: 'use-me-first-quantities-v1', MEALS: 'use-me-first-meal-log-v1',
    FAVORITES: 'use-me-first-favorites-v1', SYNC: 'use-me-first-sync-code-v1',
    SYNC_META: 'use-me-first-sync-meta-v2', RECOVERY: 'use-me-first-before-sync-v5',
    RECOVERY_ARCHIVE: 'use-me-first-preserved-before-recovery-v5',
    SEASONING_RECOVERY: 'use-me-first-before-seasoning-expiry-v1'
  });
  const fields = ['items', 'season', 'pantry', 'customSeason', 'customPantry', 'meals', 'favorites'];
  const blank = () => ({ items: [], season: [], pantry: [], customSeason: [], customPantry: [], meals: [], favorites: [] });
  const clone = value => JSON.parse(JSON.stringify(value));
  const clean = (value, limit = 120) => typeof value === 'string' ? value.normalize('NFKC').trim().slice(0, limit) : '';
  const strings = value => [...new Set((Array.isArray(value) ? value : []).filter(x => typeof x === 'string').map(x => clean(x)).filter(Boolean))];
  const dayOf = ts => { const d = new Date(ts); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  const stableId = value => { let h = 2166136261; for (let i = 0; i < value.length; i++) h = Math.imul(h ^ value.charCodeAt(i), 16777619); return 'legacy-' + (h >>> 0).toString(36); };
  const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
  const validExpiry = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && value >= '0001-01-01' &&
    Number.isFinite(Date.parse(value + 'T00:00:00Z')) && new Date(value + 'T00:00:00Z').toISOString().slice(0, 10) === value;
  const validSeasoningExpiry = value => !own(value, 'seasoningExpiry') || (value.seasoningExpiry && typeof value.seasoningExpiry === 'object' &&
    !Array.isArray(value.seasoningExpiry) && Object.entries(value.seasoningExpiry).every(([name, expiry]) => name === clean(name) && name && validExpiry(expiry)));
  // Preserve old snapshot tokens exactly until the optional field actually exists.
  const signature = state => JSON.stringify(fields.map(key => state[key]).concat(own(state, 'seasoningExpiry') ? [state.seasoningExpiry] : []));

  function normalizeState(source) {
    const state = blank(), used = new Set();
    if (!source || typeof source !== 'object') return state;
    for (const key of ['season', 'pantry', 'customSeason', 'customPantry', 'favorites']) state[key] = strings(source[key]);
    if (own(source, 'seasoningExpiry') && validSeasoningExpiry(source)) state.seasoningExpiry = { ...source.seasoningExpiry };
    state.items = (Array.isArray(source.items) ? source.items : []).filter(x => x && typeof x === 'object' && clean(x.name)).map((x, i) => {
      let id = clean(x.id) || stableId(`${x.name}|${x.expiry || ''}|${i}`);
      while (used.has(id)) id += '-duplicate';
      used.add(id);
      return { id, name: clean(x.name), expiry: clean(x.expiry, 20), quantity: typeof x.quantity === 'number' && Number.isFinite(x.quantity) ? String(x.quantity) : clean(x.quantity, 80) };
    });
    used.clear();
    state.meals = (Array.isArray(source.meals) ? source.meals : []).filter(x => x && typeof x === 'object' && clean(x.name) && Number.isFinite(Number(x.ts)) && Number(x.ts) > 0 && !Number.isNaN(new Date(Number(x.ts)).getTime())).map((x, i) => {
      let id = clean(x.id) || stableId(`meal|${x.name}|${x.ts}|${i}`);
      while (used.has(id)) id += '-duplicate';
      used.add(id);
      return { id, name: clean(x.name), ts: Number(x.ts), day: /^\d{4}-\d{2}-\d{2}$/.test(x.day || '') ? x.day : dayOf(Number(x.ts)) };
    });
    return state;
  }

  function isEnvelope(value) {
    return value && typeof value === 'object' && value.version === 5 && fields.every(k => Array.isArray(value[k])) && validSeasoningExpiry(value) &&
      value.items.every(x => x && typeof x === 'object' && typeof x.id === 'string' && x.id && typeof x.name === 'string' && x.name.trim() && typeof x.expiry === 'string' && typeof x.quantity === 'string') &&
      ['season', 'pantry', 'customSeason', 'customPantry', 'favorites'].every(k => value[k].every(x => typeof x === 'string')) &&
      value.meals.every(x => x && typeof x.id === 'string' && x.id && typeof x.name === 'string' && x.name.trim() && typeof x.ts === 'number' && Number.isFinite(x.ts) && x.ts > 0 && !Number.isNaN(new Date(x.ts).getTime()) && typeof x.day === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x.day));
  }

  function migrateLegacy(read) {
    const state = blank(), quantities = read(keys.QUANTITIES, {}), claimed = new Set();
    state.items = (Array.isArray(read(keys.ITEMS, [])) ? read(keys.ITEMS, []) : []).filter(x => x && typeof x === 'object').map(x => {
      const name = clean(x.name), qty = x.quantity != null ? x.quantity : (!claimed.has(name) && quantities && typeof quantities === 'object' ? quantities[name] : '');
      claimed.add(name);
      return { ...x, quantity: qty == null ? '' : String(qty) };
    });
    for (const [field, key] of [['season', keys.SEASON], ['pantry', keys.PANTRY], ['customSeason', keys.CUSTOM_SEASON], ['customPantry', keys.CUSTOM_PANTRY], ['meals', keys.MEALS], ['favorites', keys.FAVORITES]]) state[field] = read(key, []);
    return normalizeState(state);
  }

  function createStore(options = {}) {
    const storage = options.storage, target = options.eventTarget, listeners = new Set();
    const locks = options.locks?.request ? options.locks : null, lockName = keys.STATE + ':transaction';
    let state = blank(), revision = 0, error = '', blocked = false, seq = 0, seenPersisted = false;
    const newId = () => options.crypto?.randomUUID ? options.crypto.randomUUID() : `umf-${Date.now().toString(36)}-${(++seq).toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
    function dispatch(name, detail) {
      if (!target?.dispatchEvent) return;
      try { const C = target.CustomEvent || (typeof CustomEvent !== 'undefined' && CustomEvent); if (C) target.dispatchEvent(new C(name, { detail })); } catch (_) { /* Optional event surface. */ }
    }
    function fail(message) { error = message; dispatch('umf:storageerror', { message }); return false; }
    async function locked(action) {
      // Every production writer uses the same origin-scoped Web Lock. An unavailable
      // API falls back to latest-read writes; a rejected lock never writes unlocked.
      const commit = () => {
        const result = action();
        if (result && typeof result.then === 'function') throw new Error('A storage transaction must be synchronous');
        return result;
      };
      try { return locks ? await locks.request(lockName, { mode: 'exclusive' }, commit) : commit(); }
      catch (_) { return fail('다른 화면과 저장 순서를 확인하지 못했어요. 새로고침 후 다시 저장해 주세요.'); }
    }
    async function exclusive(action) { await ready; return locked(action); }
    function updateAsync(mutator, opts = {}) { return exclusive(() => update(mutator, opts)); }
    function replaceAsync(next, opts = {}) { const captured = clone(next); return exclusive(() => replace(captured, opts)); }
    function restoreRecoveryAsync(opts = {}) { return exclusive(() => restoreRecovery(opts)); }
    function rawRead(key) { if (!storage) throw new Error('Storage unavailable'); return storage.getItem(key); }
    function readAux(key, fallback = null) { try { const v = rawRead(key); return v === null ? fallback : v; } catch (_) { fail('이 환경에서 저장 공간을 사용할 수 없어요. 저장 설정을 확인해 주세요.'); return fallback; } }
    function writeAux(key, value) { try { if (!storage) throw new Error(); storage.setItem(key, String(value)); return true; } catch (_) { return fail('저장하지 못했어요. 기존 기록은 유지됩니다. 저장 공간과 브라우저 설정을 확인해 주세요.'); } }
    function removeAux(key) { try { if (!storage) throw new Error(); storage.removeItem(key); return true; } catch (_) { return fail('저장 설정을 변경하지 못했어요. 브라우저 저장 권한을 확인해 주세요.'); } }
    function parsed(key, fallback) { try { const text = rawRead(key); return text === null ? fallback : JSON.parse(text); } catch (_) { return fallback; } }
    function notify(origin) {
      const info = { origin, revision };
      for (const listener of listeners) { try { listener(clone(state), info); } catch (e) { if (typeof console !== 'undefined') console.error('냉장고 화면 갱신 실패', e); } }
      dispatch('umf:statechange', info);
    }
    function readCurrent() {
      let text;
      try { text = rawRead(keys.STATE); } catch (_) { blocked = true; fail('이 환경에서 기록을 저장할 수 없어요. 브라우저 저장 권한을 확인해 주세요.'); return false; }
      if (text === null) { if (seenPersisted) { state = blank(); revision = 0; blocked = false; error = ''; } return true; }
      try {
        const value = JSON.parse(text);
        if (!isEnvelope(value)) throw new Error('Invalid state');
        state = normalizeState(value); revision = Number.isFinite(value.revision) ? value.revision : 0; blocked = false; seenPersisted = true;
        return true;
      } catch (_) { blocked = true; fail('저장된 기록의 형식을 읽지 못했어요. 원본은 덮어쓰지 않았습니다.'); return false; }
    }
    function update(mutator, opts = {}) {
      if (!readCurrent() || blocked) return false;
      const before = signature(state);
      if (opts.expected != null && opts.expected !== before) return fail('다른 변경이 먼저 저장됐어요. 최신 내용을 확인한 뒤 다시 시도해 주세요.');
      const candidate = clone(state);
      try { const result = mutator(candidate); if (result && typeof result.then === 'function') throw new Error('Async mutator'); } catch (_) { return fail('변경을 적용하지 못했어요. 입력 내용을 확인해 주세요.'); }
      if (!validSeasoningExpiry(candidate)) return fail('양념 기한을 올바른 날짜로 입력해 주세요. 기존 기록은 유지됩니다.');
      const next = normalizeState(candidate);
      if (signature(next) === before) return true;
      const envelope = { version: 5, revision: revision + 1, updatedAt: Date.now(), ...next };
      if (own(next, 'seasoningExpiry') && !own(state, 'seasoningExpiry')) {
        try {
          if (rawRead(keys.SEASONING_RECOVERY) === null) {
            const original = rawRead(keys.STATE);
            if (original !== null && !writeAux(keys.SEASONING_RECOVERY, original)) return false;
          }
        } catch (_) { return fail('기존 양념 기록을 보관하지 못해 저장을 중단했어요. 저장 권한을 확인해 주세요.'); }
      }
      if (!writeAux(keys.STATE, JSON.stringify(envelope))) return false;
      state = next; revision++; error = ''; seenPersisted = true; notify(opts.origin || 'local'); return true;
    }
    function replace(next, opts = {}) { return update(draft => {
      if (!validSeasoningExpiry(next)) throw new Error('Invalid seasoning expiry');
      const value = normalizeState(next); for (const field of fields) draft[field] = value[field];
      if (own(value, 'seasoningExpiry')) draft.seasoningExpiry = value.seasoningExpiry;
      else delete draft.seasoningExpiry;
    }, opts); }
    function getState() { readCurrent(); return clone(state); }
    function snapshot() { return signature(getState()); }
    function validatedState() {
      if (!readCurrent() || blocked) return null;
      try { if (rawRead(keys.STATE) === null) { fail('저장된 기록을 확인하지 못했어요. 먼저 이 기기에 기록을 저장해 주세요.'); return null; } }
      catch (_) { fail('저장된 기록을 확인하지 못해 동기화를 중단했어요.'); return null; }
      return clone(state);
    }
    function backup() { const current = validatedState(); return current !== null && writeAux(keys.RECOVERY, JSON.stringify({ version: 5, revision, savedAt: Date.now(), ...current })); }
    function recovery() { const value = parsed(keys.RECOVERY, null); return isEnvelope(value) ? normalizeState(value) : null; }
    function restoreRecovery(opts = {}) {
      const value = recovery();
      if (!value) return fail('복구 가능한 백업을 읽지 못했어요. 현재 원본은 유지됩니다.');
      if (opts.expectedRecovery != null && signature(value) !== opts.expectedRecovery) return fail('백업이 변경됐어요. 복구할 내용을 다시 확인해 주세요.');
      let original, archive;
      try {
        original = rawRead(keys.STATE);
        if (Object.prototype.hasOwnProperty.call(opts, 'expectedCurrent') && original !== opts.expectedCurrent) return fail('다른 변경이 먼저 저장됐어요. 최신 내용을 확인한 뒤 다시 복구해 주세요.');
        const previous = rawRead(keys.RECOVERY_ARCHIVE); archive = previous === null ? [] : JSON.parse(previous);
        if (!Array.isArray(archive) || !archive.every(x => x && typeof x.raw === 'string' && typeof x.savedAt === 'number')) throw new Error();
      } catch (_) { return fail('현재 원본을 별도로 보관할 수 없어 복구를 중단했어요.'); }
      if (original !== null && !archive.some(x => x.raw === original)) archive.push({ raw: original, savedAt: Date.now() });
      // Keep unreadable source bytes before replacing the main record. Do not use update(),
      // whose normal corruption guard must continue to block all ordinary edits.
      if (!writeAux(keys.RECOVERY_ARCHIVE, JSON.stringify(archive))) return false;
      try { if (rawRead(keys.STATE) !== original) return fail('다른 변경이 먼저 저장됐어요. 최신 내용을 확인한 뒤 다시 복구해 주세요.'); }
      catch (_) { return fail('현재 원본을 다시 확인하지 못해 복구를 중단했어요.'); }
      if (!writeAux(keys.STATE, JSON.stringify({ version: 5, revision: revision + 1, updatedAt: Date.now(), ...value }))) return false;
      state = value; revision++; blocked = false; error = ''; seenPersisted = true; notify('restore'); return true;
    }
    function onStorage(event) {
      if (event.key !== keys.STATE && event.key !== null) return;
      const before = signature(state);
      if (event.key === null || event.newValue === null) { state = blank(); revision = 0; blocked = false; error = ''; notify('external'); return; }
      if (readCurrent() && signature(state) !== before) notify('external');
    }
    target?.addEventListener?.('storage', onStorage);
    let initial;
    try { initial = rawRead(keys.STATE); } catch (_) { initial = undefined; blocked = true; fail('이 환경에서 기록을 저장할 수 없어요. 브라우저 저장 권한을 확인해 주세요.'); }
    let ready;
    if (initial === null) {
      state = migrateLegacy(parsed);
      const migrate = () => {
        // Another tab may have finished migration or saved while this tab waited.
        let latest; try { latest = rawRead(keys.STATE); } catch (_) { return readCurrent(); }
        if (latest !== null) { const ok = readCurrent(); if (ok) notify('external'); return ok; }
        seenPersisted = writeAux(keys.STATE, JSON.stringify({ version: 5, revision: 0, updatedAt: Date.now(), ...state }));
        return seenPersisted;
      };
      ready = locks ? locked(migrate) : Promise.resolve(migrate());
    } else { if (initial !== undefined) readCurrent(); ready = Promise.resolve(initial !== undefined && !blocked); }
    return {
      keys, ready, getState, update, replace, updateAsync, replaceAsync, restoreRecoveryAsync, exclusive, newId, snapshot, validatedState, backup, recovery, restoreRecovery, readAux, writeAux, removeAux,
      get concurrency() { return locks ? 'web-locks' : 'best-effort'; },
      subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
      get error() { return error; }, get blocked() { return blocked; },
      destroy() { target?.removeEventListener?.('storage', onStorage); listeners.clear(); }
    };
  }

  function remoteState(payload, local = blank()) {
    if (!payload || typeof payload !== 'object' || !Array.isArray(payload.items) || ![undefined, 1, 2].includes(payload.version)) throw new Error('Invalid remote payload');
    if (!validSeasoningExpiry(payload)) throw new Error('Invalid remote seasoning expiry');
    for (const field of ['season', 'pantry', 'customSeason', 'customPantry']) if (!Array.isArray(payload[field]) || !payload[field].every(x => typeof x === 'string' && x.trim())) throw new Error('Invalid remote fields');
    if (!payload.items.every(x => x && typeof x === 'object' && typeof x.name === 'string' && x.name.trim())) throw new Error('Invalid remote item');
    if (payload.version === 2 && !isEnvelope({ ...payload, version: 5 })) throw new Error('Invalid remote v2 data');
    const old = payload.version !== 2, claimed = new Set();
    const items = payload.items.map(x => {
      if (x.quantity != null) return x;
      // v1 never contained quantities: retain the matching local lot's known quantity once.
      const match = local.items.find(i => !claimed.has(i.id) && (x.id ? i.id === x.id : i.name === x.name && i.expiry === (x.expiry || '')));
      if (match) claimed.add(match.id);
      return { ...x, id: x.id || match?.id, quantity: match?.quantity || '' };
    });
    const next = { ...payload, items, meals: old ? local.meals : payload.meals, favorites: old ? local.favorites : payload.favorites };
    // An older client cannot express a date deletion. Only an explicit map from
    // a supporting client (including {}) replaces known local seasoning dates.
    if (!own(payload, 'seasoningExpiry') && own(local, 'seasoningExpiry')) next.seasoningExpiry = local.seasoningExpiry;
    return normalizeState(next);
  }
  const pack = state => ({ version: 2, ...clone(state) });
  const remoteSignature = payload => signature(remoteState(payload));

  /* Transport is injectable so slow requests and offline edits can be tested without live writes. */
  function createSyncEngine(options) {
    const store = options.store, request = options.fetch, url = options.url;
    const confirmAction = options.confirm || (() => false), onStatus = options.onStatus || (() => {});
    let busy = false, pending = false, allowed = false, suspended = false, timer = null, generation = 0, applying = false, reconnectPending = false;
    let status = { text: '', state: 'local', busy: false };
    const code = () => store.readAux(keys.SYNC, '') || '';
    const metadata = () => { try { const v = JSON.parse(store.readAux(keys.SYNC_META, '{}')); return v && v.code === code() ? v : {}; } catch (_) { return {}; } };
    const tell = (text, state) => { status = { text, state, busy }; onStatus({ ...status }); };
    const setBusy = value => { busy = value; onStatus({ ...status, busy }); };
    const same = (a, b) => signature(a) === signature(b);
    const populated = s => fields.some(k => s[k].length > 0) || Object.keys(s.seasoningExpiry || {}).length > 0;
    const note = () => tell('기기에 새 변경이 있어요 · 동기화에서 보관할 내용을 선택해 주세요', 'conflict');
    function checkedState() { const local = store.validatedState(); if (!local || store.blocked) throw new Error('storage-blocked'); return local; }
    function connectionChanged() {
      generation++; allowed = false; suspended = true; pending = false; clearTimeout(timer);
      const current = code();
      tell(current ? '다른 화면에서 동기화 설정이 바뀌었어요 · 새 연결 확인 중' : '이 기기는 로컬 저장만 사용 중', current ? 'configured' : 'local');
      if (busy) { reconnectPending = true; return; }
      if (current) return load(current, 'auto');
    }
    function finishBusy() {
      setBusy(false);
      if (reconnectPending) { reconnectPending = false; if (code()) Promise.resolve().then(() => load(code(), 'auto')); }
    }
    function saveMeta(syncCode, local, remote, updatedAt) { return store.writeAux(keys.SYNC_META, JSON.stringify({ code: syncCode, local: signature(local), remote, updated_at: updatedAt, at: Date.now() })); }
    const supportsCAS = response => response.concurrency === 'updated_at-v1' && typeof response.updated_at === 'string' && Number.isFinite(Date.parse(response.updated_at));
    async function network(syncCode, method = 'GET', payload, expectedUpdatedAt) {
      // Revalidate at the last synchronous point before an outbound write, including
      // after a slow preflight or an asynchronous overwrite confirmation.
      if (method === 'PUT') { checkedState(); if (expectedUpdatedAt !== null && typeof expectedUpdatedAt !== 'string') throw new Error('cas-required'); }
      const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
      let timeout;
      try {
        const response = await Promise.race([
          request(url, { method, headers: { 'x-sync-code': syncCode, ...(method === 'PUT' ? { 'Content-Type': 'application/json' } : {}) }, ...(payload ? { body: JSON.stringify({ payload, expected_updated_at: expectedUpdatedAt }) } : {}), ...(controller ? { signal: controller.signal } : {}) }),
          new Promise((_, reject) => { timeout = setTimeout(() => { controller?.abort(); reject(new Error('timeout')); }, options.timeout || 12000); })
        ]);
        if (response.status === 404) throw new Error('not-found');
        if (response.status === 409) throw new Error('cas-conflict');
        if (response.status === 428) throw new Error('cas-required');
        if (!response.ok) throw new Error('http-error');
        const result = await response.json();
        if (method === 'PUT') { if (!supportsCAS(result) || result.ok !== true) throw new Error('cas-required'); return result; }
        if (result.payload === null) throw new Error('not-found');
        remoteState(result.payload); return result;
      } finally { clearTimeout(timeout); }
    }
    const errorStatus = e => {
      if (e?.message === 'cas-conflict') { suspended = true; tell('다른 기기가 먼저 저장했어요 · 이 기기의 기록을 유지했습니다. 서버 기록을 확인해 주세요.', 'conflict'); return; }
      tell(e?.message === 'not-found' ? '저장된 냉장고를 찾지 못했어요 · 코드를 확인해 주세요' : e?.message === 'storage-blocked' ? '저장된 기록을 읽지 못해 동기화를 중단했어요 · 백업 복구를 확인해 주세요' : e?.message === 'cas-required' ? '동기화 버전 확인이 필요해요 · 새로고침한 뒤 다시 시도해 주세요' : '동기화 실패 · 이 기기의 기록은 유지됩니다', 'error');
    };
    function schedule() { clearTimeout(timer); timer = setTimeout(() => drain(), options.delay ?? 400); }
    const unsubscribe = store.subscribe((_, info) => {
      if (applying || info.origin === 'sync' || info.origin === 'external') return;
      pending = true;
      if (!code()) return;
      if (allowed && !suspended) { if (!busy) schedule(); }
      else if (!busy) note();
    });

    async function drain(force = false, newCode = '') {
      if (busy) { pending = true; return false; }
      const syncCode = newCode || code(); if (!syncCode) return false;
      let configuredAtStart = code();
      const run = generation; setBusy(true); tell('동기화 중…', 'busy');
      let ok = false;
      try {
        await store.ready;
        do {
          pending = false;
          const local = checkedState(), localSig = signature(local), payload = pack(local), meta = metadata();
          let expectedUpdatedAt = null;
          if (!newCode) {
            const remote = await network(syncCode), token = remoteSignature(remote.payload);
            if (run !== generation) return false;
            if (code() !== configuredAtStart) { connectionChanged(); return false; }
            if (!supportsCAS(remote)) throw new Error('cas-required');
            expectedUpdatedAt = remote.updated_at;
            if (token !== meta.remote && !same(remoteState(remote.payload, local), local)) {
              if (!force || !(await confirmAction('서버의 기록을 이 기기의 현재 기록으로 바꿀까요? 다른 기기에서 수정한 내용이 있다면 덮어씁니다.'))) { suspended = true; allowed = false; pending = true; note(); return false; }
            }
          }
          if (code() !== configuredAtStart) { connectionChanged(); return false; }
          const written = await network(syncCode, 'PUT', payload, expectedUpdatedAt);
          if (run !== generation) return false;
          if (code() !== configuredAtStart) { connectionChanged(); return false; }
          const committed = await store.exclusive(() => {
            if (run !== generation) return false;
            if (code() !== configuredAtStart) { connectionChanged(); return false; }
            checkedState();
            return saveMeta(syncCode, local, remoteSignature(payload), written.updated_at) && (!newCode || store.writeAux(keys.SYNC, syncCode));
          });
          if (!committed) { if (run !== generation) return false; throw new Error('storage'); }
          configuredAtStart = syncCode;
          if (code() !== syncCode) return false;
          allowed = true; suspended = false; ok = true;
          pending = pending || store.snapshot() !== localSig;
          newCode = ''; force = false;
        } while (pending);
        tell('동기화 완료 · 재료·수량·기록·즐겨찾기', 'ready');
        return true;
      } catch (e) { pending = true; allowed = false; errorStatus(e); return false; }
      finally { finishBusy(); if (!ok && status.state === 'busy') note(); }
    }

    async function load(syncCode, mode = 'auto') {
      if (busy || !syncCode) return false;
      const run = generation, configuredAtStart = code();
      setBusy(true); tell('저장된 냉장고 확인 중…', 'busy');
      try {
        await store.ready;
        const local = checkedState(), before = signature(local), meta = metadata();
        const remote = await network(syncCode), next = remoteState(remote.payload, local), token = remoteSignature(remote.payload);
        if (run !== generation) return false;
        if (code() !== configuredAtStart) { connectionChanged(); return false; }
        if (signature(checkedState()) !== before) { suspended = true; allowed = false; pending = true; note(); return false; }
        const changed = !same(next, local), cleanLocal = meta.local === before;
        if (mode === 'auto' && changed && populated(local) && !cleanLocal) {
          if (meta.remote === token) { allowed = true; suspended = false; pending = true; tell('기기의 변경을 동기화할 준비가 됐어요', 'configured'); return true; }
          suspended = true; allowed = false; pending = true; note(); return false;
        }
        if (mode !== 'auto' && changed && populated(local) && !(await confirmAction('서버의 냉장고를 불러올까요? 현재 기기의 기록은 가져오기 전 백업으로 보관하며, 동기화 설정에서 복구할 수 있습니다.'))) { note(); return false; }
        if (run !== generation) return false;
        if (code() !== configuredAtStart) { connectionChanged(); return false; }
        if (signature(checkedState()) !== before) { note(); return false; }
        const committed = await store.exclusive(() => {
          // A tab may edit or switch connections while this request waits for its lock.
          if (run !== generation) return false;
          if (code() !== configuredAtStart) { connectionChanged(); return false; }
          if (signature(checkedState()) !== before) { suspended = true; allowed = false; pending = true; note(); return false; }
          if (changed) {
            if (!store.backup()) return false;
            applying = true;
            try { if (!store.replace(next, { origin: 'sync', expected: before })) return false; } finally { applying = false; }
          }
          return saveMeta(syncCode, next, token, remote.updated_at) && store.writeAux(keys.SYNC, syncCode);
        });
        if (!committed) { if (run !== generation || status.state === 'conflict') return false; throw new Error('storage'); }
        allowed = true; suspended = false; pending = false;
        tell('동기화 완료 · 재료·수량·기록·즐겨찾기', 'ready'); return true;
      } catch (e) { allowed = false; errorStatus(e); return false; }
      finally { finishBusy(); if (pending && allowed && !suspended) schedule(); }
    }

    function randomCode() {
      const crypto = options.crypto || (typeof globalThis.crypto !== 'undefined' && globalThis.crypto);
      if (!crypto?.getRandomValues) throw new Error('secure-random-unavailable');
      const bytes = new Uint8Array(18); crypto.getRandomValues(bytes);
      return 'UMF-' + [...bytes].map(x => x.toString(16).padStart(2, '0')).join('');
    }
    async function disconnect() {
      if (busy) return false;
      const configuredAtStart = code(), run = generation; let stale = false;
      setBusy(true);
      try {
        const disconnected = await store.exclusive(() => {
          if (run !== generation) { stale = true; return false; }
          if (code() !== configuredAtStart) { stale = true; connectionChanged(); return false; }
          clearTimeout(timer); generation++; allowed = false; suspended = true; pending = false;
          return store.removeAux(keys.SYNC) && store.removeAux(keys.SYNC_META);
        });
        if (!disconnected) { if (!stale) errorStatus(new Error('storage')); return false; }
        tell('이 기기는 로컬 저장만 사용 중', 'local'); return true;
      } finally { finishBusy(); }
    }
    async function restore() {
      if (busy) return false;
      setBusy(true);
      try {
        await store.ready;
        const value = store.recovery(), original = store.readAux(keys.STATE, null);
        if (!value) { tell('가져오기 전 백업이 없어요', 'configured'); return false; }
        if (!(await confirmAction('서버에서 가져오기 전의 이 기기 기록으로 복구할까요? 복구한 내용은 자동으로 서버에 올리지 않습니다.'))) return false;
        allowed = false; suspended = true; pending = true;
        if (!(await store.restoreRecoveryAsync({ expectedCurrent: original, expectedRecovery: signature(value) }))) { errorStatus(new Error('storage')); return false; }
        tell('이전 기록을 복구했어요 · 동기화할 내용을 선택해 주세요', 'conflict'); return true;
      } finally { finishBusy(); }
    }
    return {
      get code() { return code(); }, get status() { return { ...status, busy }; },
      initialize() { if (code()) return load(code(), 'auto'); tell('이 기기는 로컬 저장만 사용 중', 'local'); return Promise.resolve(true); },
      async create() { if (busy) return false; try { return await drain(true, randomCode()); } catch (e) { errorStatus(e); return false; } },
      connect(value) { const c = String(value || '').trim(); if (!/^UMF-[A-Za-z0-9-]{20,120}$/.test(c)) { tell('동기화 코드 형식을 확인해 주세요', 'error'); return Promise.resolve(false); } return load(c, 'connect'); },
      upload() { return drain(true); }, reload() { return load(code(), 'manual'); }, disconnect, restore, connectionChanged,
      retry() { return code() && !busy ? load(code(), 'auto') : Promise.resolve(false); },
      destroy() { generation++; clearTimeout(timer); unsubscribe(); }
    };
  }
  return { keys, blank, normalizeState, migrateLegacy, signature, createStore, remoteState, createSyncEngine };
});
