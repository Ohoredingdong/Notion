'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const D = require('../use-me-first-domain.js');
const NOW = new Date(2026, 9, 20, 12);
const item = (name, expiry = '2026-10-25', quantity = '2개', id = name) => ({ id, name, expiry, quantity });
const rice = { name: '계란 볶음밥', f: ['계란', '양파'], s: ['식용유', '간장'], p: ['밥/즉석밥'] };
const stock = (items = []) => ({ items, season: ['식용유', '간장'], pantry: ['밥/즉석밥'] });

test('normalizes NFKC and whitespace without interpreting HTML', () => {
  assert.equal(D.normalizeName('  닭\n 가슴살  '), '닭 가슴살');
  assert.equal(D.normalizeName('３００ｇ'), '300g');
  assert.equal(D.normalizeName(null), '');
  assert.equal(D.normalizeName('<img src=x onerror=alert(1)>'), '<img src=x onerror=alert(1)>');
});

test('canonicalizes explicit ingredient aliases and spacing variants', () => {
  for (const name of ['달걀', '계 란', '유정란']) assert.equal(D.canonical(name), '계란');
  for (const name of ['깐 양파', '적양파']) assert.equal(D.canonical(name), '양파');
  for (const name of ['표고', '느타리버섯', '팽이', '양송이버섯', '새송이버섯']) assert.equal(D.canonical(name), '버섯');
  assert.equal(D.canonical('방울토마토'), '토마토');
  assert.equal(D.canonical('부침용 두부'), '두부');
  assert.equal(D.canonical('즉석밥'), '밥/즉석밥');
  assert.equal(D.canonical('간 마늘'), '다진마늘');
});

test('does not overgeneralize soft tofu, processed foods, or arbitrary substrings', () => {
  for (const name of ['순두부', '연두부', '두부과자']) assert.notEqual(D.canonical(name), '두부');
  for (const name of ['계란빵', '무계란빵', '계란과자', '계란말이', '계란찜', '삶은계란']) assert.notEqual(D.canonical(name), '계란');
  assert.notEqual(D.canonical('닭가슴살소시지'), '닭가슴살');
  assert.notEqual(D.canonical('토마토소스'), '토마토');
  assert.notEqual(D.canonical('요구르트'), '요거트');
  assert.notEqual(D.canonical('국간장'), '간장');
  assert.notEqual(D.canonical('쌀'), '밥/즉석밥');
});

test('prototype-like names remain ordinary unknown names', () => {
  for (const name of ['__proto__', 'constructor', 'toString']) assert.equal(D.canonical(name), name);
  assert.equal(D.matchIngredient([item('__proto__')], '계란', NOW), null);
});

test('strictly validates calendar dates and reports local calendar days', () => {
  assert.equal(D.daysLeft('2026-10-20', NOW), 0);
  assert.equal(D.daysLeft('2026-10-22', NOW), 2);
  assert.equal(D.daysLeft('2026-10-19', NOW), -1);
  assert.equal(D.daysLeft('2024-02-29', new Date(2024, 1, 28, 12)), 1);
  for (const date of ['', null, '2026-2-01', '2026-02-29', '2026-02-30', '2026-13-01', '2026-00-20', '2026-10-00', '2026-10-32', '2026-10-20T12:00:00', '0000-01-01', 'not a date']) {
    assert.equal(D.daysLeft(date, NOW), null, String(date));
  }
  assert.equal(D.daysLeft('2026-10-20', new Date('invalid')), null);
});

test('calendar distance remains correct across spring and autumn DST boundaries', () => {
  const previousTimezone = process.env.TZ;
  try {
    process.env.TZ = 'America/New_York';
    assert.equal(D.daysLeft('2026-03-09', new Date(2026, 2, 7, 12)), 2);
    assert.equal(D.daysLeft('2026-11-02', new Date(2026, 9, 31, 12)), 2);
  } finally {
    if (previousTimezone === undefined) delete process.env.TZ;
    else process.env.TZ = previousTimezone;
  }
});

test('parses supported units, decimals, full-width text, and grouped thousands', () => {
  for (const [text, amount, unit] of [['300g', 300, 'g'], ['1.5 kg', 1.5, 'kg'], ['250ml', 250, 'ml'], ['.5L', .5, 'l'], ['３개', 3, '개'], ['2팩', 2, '팩'], ['1모', 1, '모'], ['2봉', 2, '봉'], ['1공기', 1, '공기'], ['1,000g', 1000, 'g'], ['2', 2, null]]) {
    assert.deepEqual(D.parseQuantity(text), { amount, unit, empty: false, known: true }, text);
  }
});

test('recognizes explicit zero and depleted stock without guessing arbitrary text', () => {
  for (const text of ['0', 0, '0개', '0g', '0.00 KG', '０ml', '소진', '없음']) {
    const q = D.parseQuantity(text);
    assert.equal(q.empty, true, String(text));
    assert.equal(q.known, true, String(text));
    assert.equal(q.amount, 0);
  }
  for (const text of ['', null, '조금', '반 팩', '한 봉지', '300g 정도', '1,2g', '-1개', 'NaN', 'Infinity', '0<img src=x>']) {
    assert.deepEqual(D.parseQuantity(text), { amount: null, unit: null, empty: false, known: false }, String(text));
  }
});

test('excludes expired and explicitly empty items while retaining unknown dates and amounts', () => {
  assert.equal(D.usable(item('계란', '2026-10-19'), NOW), false);
  assert.equal(D.usable(item('계란', '2026-10-20'), NOW), true);
  assert.equal(D.usable(item('계란', '2026-10-25', '0개'), NOW), false);
  assert.equal(D.usable(item('계란', '', '조금'), NOW), true);
  assert.equal(D.usable(item('계란', '2026-02-30'), NOW), true);
  assert.equal(D.usable(item(''), NOW), false);
  assert.equal(D.usable(null, NOW), false);
});

test('matches aliases and selects the earliest usable batch without mutating inventory', () => {
  const expired = item('계란', '2026-10-19', '8개', 'expired');
  const unknown = item('달걀', '', '4개', 'unknown');
  const later = item('계란', '2026-10-30', '10개', 'later');
  const soon = item('달걀', '2026-10-21', '3개', 'soon');
  const empty = item('계란', '2026-10-20', '0개', 'empty');
  const inventory = [expired, unknown, later, soon, empty];
  const snapshot = JSON.stringify(inventory);
  assert.equal(D.matchIngredient(inventory, '계란', NOW), soon);
  assert.equal(JSON.stringify(inventory), snapshot);
  assert.equal(D.matchIngredient([empty, expired], '계란', NOW), null);
});

test('an expired batch cannot make a recipe available', () => {
  const result = D.evaluate(rice, stock([item('계란', '2000-01-01'), item('양파')]), NOW);
  assert.equal(result.available, false);
  assert.deepEqual(result.missing, [{ name: '계란', kind: 'fridge', reason: 'expired' }]);
  assert.equal(result.usedItems.some(x => x.name === '계란'), false);
});

test('reports explicit depletion separately from missing or expired ingredients', () => {
  const result = D.evaluate(rice, stock([item('계란', '2026-10-25', '소진')]), NOW);
  assert.deepEqual(result.missing, [{ name: '계란', kind: 'fridge', reason: 'empty' }, { name: '양파', kind: 'fridge', reason: 'missing' }]);
  const duplicate = D.evaluate(rice, stock([item('계란', '2026-10-19'), item('계란', '2026-10-25', '0개'), item('양파')]), NOW);
  assert.equal(duplicate.missing[0].reason, 'empty');
});

test('fresh duplicate batch remains usable when another same-name batch expired or ran out', () => {
  const fresh = item('계란', '2026-10-21', '2개', 'fresh');
  const result = D.evaluate(rice, stock([item('계란', '2026-10-19'), item('계란', '2026-10-25', '0개'), fresh, item('양파')]), NOW);
  assert.equal(result.available, true);
  assert.equal(result.urgentCount, 1);
  assert.equal(result.usedItems.filter(x => D.canonical(x.name) === '계란').length, 1);
  assert.equal(result.usedItems[0], fresh);
});

test('counts stock across refrigerator, checked seasonings, and checked pantry', () => {
  const state = { items: [item('달걀'), item('깐 양파'), item('간장', '2027-01-01', '300ml'), item('즉석밥', '2027-01-01', '2공기')], season: [], pantry: ['식용유'] };
  const result = D.evaluate(rice, state, NOW);
  assert.equal(result.available, true);
  assert.equal(result.matchedCount, 5);
  assert.equal(result.usedItems.length, 4);
  assert.equal(result.quantityUnknown, true);
});

test('only explicitly checked stock can fulfill a missing fresh ingredient', () => {
  const state = { items: [item('계란', '2026-10-19')], season: [], pantry: [] };
  assert.equal(D.evaluate({ f: ['계란'] }, state, NOW).available, false);
  state.pantry = ['달걀'];
  const result = D.evaluate({ f: ['계란'] }, state, NOW);
  assert.equal(result.available, true);
  assert.deepEqual(result.usedItems, []);
  assert.equal(result.quantityUnknown, true);
});

test('preserves missing ingredient category for the correct add flow', () => {
  const result = D.evaluate(rice, { items: [], season: [], pantry: [] }, NOW);
  assert.deepEqual(result.missing, [
    { name: '계란', kind: 'fridge', reason: 'missing' },
    { name: '양파', kind: 'fridge', reason: 'missing' },
    { name: '식용유', kind: 'season', reason: 'missing' },
    { name: '간장', kind: 'season', reason: 'missing' },
    { name: '밥/즉석밥', kind: 'pantry', reason: 'missing' }
  ]);
});

test('flags unknown expiry and amount rather than inventing expiry or portions', () => {
  const result = D.evaluate({ f: ['계란'] }, { items: [item('계란', '', '조금')] }, NOW);
  assert.equal(result.available, true);
  assert.equal(result.expiryUnknown, true);
  assert.equal(result.quantityUnknown, true);
  assert.equal(result.urgentCount, 0);
  const known = D.evaluate({ f: ['계란'] }, { items: [item('계란', '2026-10-22', '1개')] }, NOW);
  assert.equal(known.expiryUnknown, false);
  assert.equal(known.quantityUnknown, false);
  assert.equal(known.urgentCount, 1);
});

test('does not claim recipe-specific portion checks', () => {
  const result = D.evaluate({ name: '계란 요리', f: ['계란'], portions: 20 }, { items: [item('계란', '2026-10-25', '1개')] }, NOW);
  assert.equal(result.available, true);
  assert.equal(result.usedItems[0].quantity, '1개');
});

test('deduplicates equivalent ingredient requirements and used batches', () => {
  const egg = item('달걀', '2026-10-21');
  const result = D.evaluate({ f: ['계란', '달걀'], s: ['계란'], p: [] }, { items: [egg] }, NOW);
  assert.equal(result.available, true);
  assert.equal(result.matchedCount, 1);
  assert.equal(result.urgentCount, 1);
  assert.deepEqual(result.usedItems, [egg]);
});

test('DOM-shaped names cannot satisfy an unrelated ingredient or execute code', () => {
  const names = ['계란<img src=x onerror=alert(1)>', '<script>계란</script>', '무계란빵', '계란\" onclick=alert(1)'];
  for (const name of names) {
    const result = D.evaluate({ f: ['계란'] }, { items: [item(name)] }, NOW);
    assert.equal(result.available, false, name);
    assert.deepEqual(result.missing, [{ name: '계란', kind: 'fridge', reason: 'missing' }]);
  }
});

test('ready recipes rank first, then urgent ingredients, matched count, missing count, name', () => {
  const recipes = [
    { name: '다 많은 보유', f: ['계란', '양파'] },
    { name: '가 기한 여유', f: ['양파'] },
    { name: '나 임박 우선', f: ['계란'] },
    { name: '마 부족 둘', f: ['계란', '버섯', '토마토'] },
    { name: '라 부족 하나', f: ['계란', '버섯'] }
  ];
  const state = { items: [item('계란', '2026-10-21'), item('양파', '2026-10-30')] };
  const snapshot = JSON.stringify({ recipes, state });
  const ranked = D.rankRecipes(recipes, state, NOW);
  assert.deepEqual(ranked.map(x => x.recipe.name), ['다 많은 보유', '나 임박 우선', '가 기한 여유', '라 부족 하나', '마 부족 둘']);
  assert.equal(JSON.stringify({ recipes, state }), snapshot);
  assert.equal(ranked[0].recipe, recipes[0]);
  assert.ok(ranked.every(x => Array.isArray(x.missing) && Array.isArray(x.usedItems)));
});

test('ties use stable Korean name ordering, then original input order', () => {
  const first = { name: '같은 이름', f: ['계란'], marker: 1 };
  const second = { name: '같은 이름', f: ['계란'], marker: 2 };
  const result = D.rankRecipes([{ name: '나 메뉴', f: ['계란'] }, second, { name: '가 메뉴', f: ['계란'] }, first], { items: [item('계란')] }, NOW);
  assert.deepEqual(result.map(x => x.recipe.name), ['가 메뉴', '같은 이름', '같은 이름', '나 메뉴']);
  assert.equal(result[1].recipe, second);
  assert.equal(result[2].recipe, first);
});

test('handles absent or malformed inventory collections without fabricating stock', () => {
  const result = D.evaluate(rice, { items: null, season: {}, pantry: '밥/즉석밥' }, NOW);
  assert.equal(result.available, false);
  assert.equal(result.missing.length, 5);
  assert.deepEqual(D.rankRecipes(null, null, NOW), []);
  assert.equal(D.matchIngredient(undefined, '계란', NOW), null);
});

test('exports the same public API to a browser-style window without needing a DOM', () => {
  const source = fs.readFileSync(require.resolve('../use-me-first-domain.js'), 'utf8');
  const context = { window: {} };
  vm.runInNewContext(source, context, { timeout: 1000 });
  assert.deepEqual(Object.keys(context.window.UMFDomain).sort(), Object.keys(D).sort());
  assert.equal(context.window.UMFDomain.canonical('달걀'), '계란');
  assert.equal(Object.isFrozen(context.window.UMFDomain), true);
});
