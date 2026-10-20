/* Local kitchen presentation preferences. Inventory and sync data live in UMFStore. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else {
    let storage, locks;
    try { storage = root.localStorage; } catch (_) { storage = null; }
    try { locks = root.navigator?.locks; } catch (_) { locks = null; }
    root.UMFKitchenState = api.createKitchenState({ storage, locks, eventTarget: root });
  }
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const KEY = 'use-me-first-kitchen-view-v1';
  const ZONES = Object.freeze(['top', 'middle', 'bottom', 'freezer-top', 'freezer-middle', 'freezer-bottom', 'pantry']);
  const compartments = ['freezer', 'fridge'];
  const blank = () => ({ version: 2, doors: { freezer: false, fridge: false }, placements: {}, positions: {} });
  const clone = value => JSON.parse(JSON.stringify(value));
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  const owns = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
  const validId = id => typeof id === 'string' && id.trim().length > 0;
  const unit = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
  const validPosition = value => object(value) && Object.keys(value).length === 3 && ['x', 'y', 'z'].every(key => owns(value, key)) &&
    unit(value.x) && unit(value.y) && Number.isSafeInteger(value.z) && value.z > 0;
  const setOwn = (value, key, content) => Object.defineProperty(value, key, { value: content, writable: true, enumerable: true, configurable: true });
  function valid(value, allowLegacy = true) {
    if (!object(value) || !['version', 'doors', 'placements'].every(key => owns(value, key)) ||
      !object(value.doors) || Object.keys(value.doors).length !== 2 || !compartments.every(key => owns(value.doors, key) && typeof value.doors[key] === 'boolean') ||
      !object(value.placements) || !Object.entries(value.placements).every(([id, zone]) => validId(id) && ZONES.includes(zone))) return false;
    if (allowLegacy && value.version === 1) return Object.keys(value).length === 3;
    return value.version === 2 && Object.keys(value).length === 4 && owns(value, 'positions') && object(value.positions) &&
      Object.entries(value.positions).every(([id, position]) => validId(id) && validPosition(position));
  }
  const canonical = value => ({
    version: 2, doors: { freezer: value.doors.freezer, fridge: value.doors.fridge }, placements: Object.fromEntries(Object.entries(value.placements)),
    positions: Object.fromEntries(Object.entries(value.version === 1 ? {} : value.positions).map(([id, p]) => [id, { x: p.x, y: p.y, z: p.z }]))
  });
  const ordered = positions => Object.entries(positions).sort((a, b) => a[1].z - b[1].z);
  function frontLayer(positions) {
    const layers = Object.values(positions).map(position => position.z);
    const highest = layers.reduce((max, layer) => Math.max(max, layer), 0);
    if (highest < Number.MAX_SAFE_INTEGER) return highest + 1;
    // Reindex inside the same transaction before the next increment can overflow.
    ordered(positions).forEach(([, position], index) => { position.z = index + 1; });
    return layers.length + 1;
  }

  function createKitchenState(options = {}) {
    const storage = options.storage, target = options.eventTarget, locks = options.locks?.request ? options.locks : null;
    const listeners = new Set();
    let state = blank(), error = '', blocked = false;
    function dispatch(name, detail) {
      if (!target?.dispatchEvent) return;
      try {
        const EventClass = target.CustomEvent || (typeof CustomEvent !== 'undefined' && CustomEvent);
        if (EventClass) target.dispatchEvent(new EventClass(name, { detail }));
      } catch (_) { /* Event delivery is optional; persistence results remain available. */ }
    }
    function fail(message) { error = message; dispatch('umf:kitchenerror', { message }); return false; }
    function readCurrent() {
      let raw;
      try { if (!storage) throw new Error('Storage unavailable'); raw = storage.getItem(KEY); }
      catch (_) { blocked = true; return fail('냉장고 화면 설정을 읽지 못했어요. 브라우저 저장 권한을 확인해 주세요.'); }
      if (raw === null) { state = blank(); if (blocked) error = ''; blocked = false; return true; }
      try {
        const value = JSON.parse(raw);
        if (!valid(value)) throw new Error('Invalid kitchen state');
        state = canonical(value); if (blocked) error = ''; blocked = false; return true;
      } catch (_) {
        blocked = true; return fail('저장된 냉장고 화면 설정을 읽지 못했어요. 기존 설정은 덮어쓰지 않았습니다.');
      }
    }
    function notify(origin) {
      for (const listener of listeners) {
        try { listener(clone(state), { origin }); } catch (_) { /* One observer cannot reject a completed save. */ }
      }
      dispatch('umf:kitchenchange', { origin });
    }
    function commit(mutator, guard) {
      if (!readCurrent() || blocked) return false;
      if (guard !== undefined) {
        try {
          const allowed = guard();
          if (allowed && typeof allowed.then === 'function') { Promise.resolve(allowed).catch(() => {}); throw new Error('Async guard'); }
          if (typeof allowed !== 'boolean') throw new Error('Invalid guard');
          if (!allowed) return false;
        } catch (_) { return fail('재료의 현재 위치와 상태를 다시 확인해 주세요.'); }
      }
      const before = JSON.stringify(state), draft = clone(state);
      try {
        const result = mutator(draft);
        if (result && typeof result.then === 'function') { Promise.resolve(result).catch(() => {}); throw new Error('Async change'); }
        if (!valid(draft, false)) throw new Error('Invalid change');
      } catch (_) { return fail('냉장고 문과 재료 위치 설정을 확인해 주세요.'); }
      const next = canonical(draft), encoded = JSON.stringify(next);
      if (encoded === before) { error = ''; return true; }
      try { storage.setItem(KEY, encoded); }
      catch (_) { return fail('냉장고 화면 설정을 저장하지 못했어요. 저장 공간과 브라우저 설정을 확인해 주세요.'); }
      state = next; error = ''; notify('local'); return true;
    }
    const ready = Promise.resolve(readCurrent());
    async function updateAsync(mutator, guard) {
      await ready;
      try {
        // The callback is synchronous. A rejected lock never retries without a lock.
        return locks ? await locks.request(KEY + ':transaction', { mode: 'exclusive' }, () => commit(mutator, guard)) : commit(mutator, guard);
      } catch (_) { return fail('냉장고 화면 설정을 저장할 차례를 확인하지 못했어요. 다시 시도해 주세요.'); }
    }
    function getState() { readCurrent(); return clone(state); }
    function zoneFor(item) {
      const id = typeof item === 'string' ? item : item?.id;
      readCurrent();
      // Names never imply freezing; only an explicit saved placement uses the freezer.
      return validId(id) && owns(state.placements, id) ? state.placements[id] : 'middle';
    }
    function positionFor(item) {
      const id = typeof item === 'string' ? item : item?.id;
      readCurrent();
      return validId(id) && owns(state.positions, id) ? { ...state.positions[id] } : null;
    }
    function setZone(id, zone) {
      if (!validId(id) || !ZONES.includes(zone)) return Promise.resolve(fail('재료와 보관 위치를 확인해 주세요.'));
      return updateAsync(draft => {
        const previous = owns(draft.placements, id) ? draft.placements[id] : 'middle';
        if (previous !== zone) delete draft.positions[id];
        setOwn(draft.placements, id, zone);
      });
    }
    function setPosition(id, zone, position, guard) {
      if (!validId(id) || !ZONES.includes(zone) || !object(position) || !unit(position.x) || !unit(position.y)) {
        return Promise.resolve(fail('재료를 선반 안에 놓아 주세요.'));
      }
      const x = position.x, y = position.y;
      return updateAsync(draft => {
        const z = frontLayer(draft.positions);
        setOwn(draft.placements, id, zone);
        setOwn(draft.positions, id, { x, y, z });
      }, guard);
    }
    async function changeLayer(id, direction = 'front', guard) {
      if (!validId(id) || !['front', 'back'].includes(direction)) return fail('재료의 앞뒤 순서를 확인해 주세요.');
      let missing = false;
      const saved = await updateAsync(draft => {
        if (!owns(draft.positions, id)) { missing = true; return; }
        if (direction === 'front') draft.positions[id].z = frontLayer(draft.positions);
        else {
          const rest = ordered(draft.positions).filter(([otherId]) => otherId !== id);
          draft.positions[id].z = 1;
          rest.forEach(([, position], index) => { position.z = index + 2; });
        }
      }, guard);
      if (missing) return fail('먼저 재료를 놓을 위치를 선택해 주세요.');
      return saved;
    }
    function toggleDoor(compartment) {
      if (!compartments.includes(compartment)) return Promise.resolve(fail('열거나 닫을 냉장고 문을 확인해 주세요.'));
      return updateAsync(draft => { draft.doors[compartment] = !draft.doors[compartment]; });
    }
    function setDoors(changes) {
      if (!object(changes) || !Object.entries(changes).every(([key, value]) => compartments.includes(key) && typeof value === 'boolean')) {
        return Promise.resolve(fail('냉장고 문 설정을 확인해 주세요.'));
      }
      const captured = { ...changes };
      return updateAsync(draft => { Object.assign(draft.doors, captured); });
    }
    function onStorage(event) {
      if ((event.key !== KEY && event.key !== null) || (event.storageArea && event.storageArea !== storage)) return;
      const before = JSON.stringify(state);
      // Read the durable key instead of replaying a possibly delayed event value.
      if (readCurrent() && JSON.stringify(state) !== before) notify('external');
    }
    target?.addEventListener?.('storage', onStorage);
    return {
      ready, getState, updateAsync, zoneFor, positionFor, setZone, setPosition, changeLayer, toggleDoor, setDoors,
      subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
      get error() { return error; }, get blocked() { return blocked; },
      get concurrency() { return locks ? 'web-locks' : 'best-effort'; },
      destroy() { target?.removeEventListener?.('storage', onStorage); listeners.clear(); }
    };
  }
  return { KEY, ZONES, blank, createKitchenState };
});
