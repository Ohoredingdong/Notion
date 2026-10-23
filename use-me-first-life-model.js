/* Optional kitchen-life records. Never reads or rewrites the inventory key. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) {
    let storage; try { storage = root.localStorage; } catch (_) {}
    root.UMFLife = api;
    root.UMFLifeStore = api.createStore({storage, locks:root.navigator?.locks, events:root});
  }
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const KEY = 'use-me-first-life-v1';
  const THEMES = {oat:0, sage:10, rose:30};
  const clone = value => JSON.parse(JSON.stringify(value));
  const blank = () => ({version:1, goal:'care', theme:'oat', claims:[], budget:null,
    targets:{kcal:null, protein:null, carb:null, fat:null}, expenses:[], nutrition:[], supplements:[]});
  function day(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const date = new Date(value + 'T12:00:00Z');
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0,10) === value;
  }
  function today(date = new Date()) {
    return date.getFullYear() + '-' + String(date.getMonth()+1).padStart(2,'0') + '-' + String(date.getDate()).padStart(2,'0');
  }
  const number = value => value === null || typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1e8;
  const text = (value, limit=100) => typeof value === 'string' && value.trim().length > 0 && value.length <= limit;
  const list = value => Array.isArray(value) && value.length <= 10000;
  function valid(s) {
    if (!s || s.version !== 1 || !['care','meal','budget'].includes(s.goal) || !Object.hasOwn(THEMES,s.theme) || !number(s.budget)) return false;
    if (!s.targets || !['kcal','protein','carb','fat'].every(k => number(s.targets[k]))) return false;
    if (!list(s.claims) || !s.claims.every(day) || new Set(s.claims).size !== s.claims.length || s.claims.length*10 < THEMES[s.theme]) return false;
    if (!list(s.expenses) || !s.expenses.every(r => r && text(r.id) && day(r.day) && text(r.name) && number(r.amount) && r.amount > 0 && ['groceries','eatingout'].includes(r.category))) return false;
    if (!list(s.nutrition) || !s.nutrition.every(r => r && text(r.id) && day(r.day) && text(r.name) && ['kcal','protein','carb','fat'].every(k => number(r[k])) && ['kcal','protein','carb','fat'].some(k => r[k] !== null) && r.source === 'manual')) return false;
    if (!list(s.supplements) || !s.supplements.every(r => r && text(r.id) && text(r.name) && typeof r.amount === 'string' && r.amount.length <= 100 && list(r.days) && r.days.every(day) && new Set(r.days).size === r.days.length)) return false;
    return ['expenses','nutrition','supplements'].every(key => new Set(s[key].map(r => r.id)).size === s[key].length);
  }
  function report(s, inventory, month) {
    const rows = s.nutrition.filter(r => r.day.slice(0,7) === month);
    const expenses = s.expenses.filter(r => r.day.slice(0,7) === month);
    const complete = rows.filter(r => ['protein','carb','fat'].every(k => r[k] !== null));
    const energy = {carb:0, protein:0, fat:0};
    complete.forEach(r => {energy.carb += r.carb*4; energy.protein += r.protein*4; energy.fat += r.fat*9;});
    const total = Object.values(energy).reduce((a,b) => a+b,0);
    return {rows, expenses, spending:expenses.reduce((sum,r) => sum+r.amount,0),
      meals:inventory.meals.filter(r => r.day.slice(0,7) === month).length,
      days:new Set(rows.map(r => r.day)).size, complete:complete.length,
      ratio:total > 0 ? Object.fromEntries(Object.entries(energy).map(([k,v]) => [k,v/total*100])) : null};
  }
  function createStore({storage, locks, events} = {}) {
    let error = '', writeError = '', listeners = new Set(), queue = Promise.resolve();
    function read() {
      try {
        if (!storage) throw new Error('이 화면에서는 새 기록을 저장할 수 없어요. 저장 가능한 브라우저에서 열어 주세요.');
        const raw = storage.getItem(KEY);
        if (raw === null) {error=''; return blank();}
        const value = JSON.parse(raw);
        if (!valid(value)) throw new Error('생활 기록 형식을 확인할 수 없어 저장을 멈췄어요. 기존 원본은 유지됩니다.');
        error=''; return value;
      } catch (e) { error = e instanceof SyntaxError ? '생활 기록을 읽을 수 없어 저장을 멈췄어요. 기존 원본은 유지됩니다.' : e.message; return null; }
    }
    const notify = () => { for (const fn of listeners) fn(); };
    function update(mutator) {
      const run = async () => {
        const commit = () => {
          const state = read(); if (!state) {notify(); return false;}
          try {
            const result = mutator(state);
            if (result && typeof result.then === 'function') throw new Error('동기 저장만 지원해요.');
            if (!valid(state)) throw new Error('입력값을 확인해 주세요. 기록은 변경하지 않았어요.');
            storage.setItem(KEY,JSON.stringify(state)); error=''; writeError=''; notify(); return true;
          } catch (e) {writeError = '저장하지 못했어요. ' + e.message; notify(); return false;}
        };
        try { return locks?.request ? await locks.request(KEY + ':transaction',commit) : commit(); }
        catch (_) { writeError='다른 화면의 저장을 기다리지 못했어요. 다시 시도해 주세요.'; notify(); return false; }
      };
      const pending = queue.then(run,run); queue=pending; return pending;
    }
    events?.addEventListener('storage', e => {if (e.key === KEY || e.key === null) {read();notify();}});
    read();
    return {getState:() => clone(read() || blank()), update, subscribe:fn => {listeners.add(fn);return () => listeners.delete(fn);}, get error(){return error || writeError;}};
  }
  return {KEY, THEMES, blank, valid, day, today, report, createStore};
});
