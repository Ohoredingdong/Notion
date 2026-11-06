'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const lessons = require('../assets/auction-study-lessons.js');

test('both fictional cases cover all six reading tasks with usable source excerpts', () => {
  const topicIds = ['identity', 'priority', 'tenant', 'occupancy', 'costs', 'exceptions'];
  assert.deepEqual(lessons.topics.map(topic => topic.id), topicIds);
  assert.equal(new Set(lessons.topics.map(topic => topic.id)).size, 6);
  assert.equal(lessons.cases.length, 2);
  assert.equal(new Set(lessons.cases.map(item => item.id)).size, 2);
  const choiceIds = new Set();
  for (const item of lessons.cases) {
    assert.equal(item.fictional, true);
    assert.ok(item.title && item.summary && item.level);
    assert.deepEqual(item.steps.map(step => step.id), topicIds);
    for (const step of item.steps) {
      assert.ok(step.title && step.documentTitle && step.evidencePrompt);
      assert.match(step.documentCaption, /가상/);
      assert.ok(step.rows.length >= 2 && step.rows.length <= 6);
      assert.ok(step.rows.some(row => row.focus === true), `${item.id}/${step.id}: missing a reading focus`);
      assert.ok(step.rows.every(row => row.label && row.value));
      for (const [field, maximum] of [['question', 60], ['hint', 80], ['explanation', 120]]) {
        assert.ok(step[field] && [...step[field]].length <= maximum, `${item.id}/${step.id}: ${field} exceeds its reading budget`);
      }
      assert.equal(step.choices.length, 3);
      assert.equal(step.choices.filter(choice => choice.id === step.correctChoice).length, 1);
      for (const choice of step.choices) {
        assert.ok(choice.id && choice.text && [...choice.text].length <= 50);
        assert.ok(!choiceIds.has(choice.id), `cross-case or cross-step choice ID reused: ${choice.id}`);
        choiceIds.add(choice.id);
      }
      assert.equal(step.checklist.length, 2);
      assert.ok(step.checklist.every(text => typeof text === 'string' && text.length));
      assert.ok(step.sources.length);
      for (const link of step.sources) {
        assert.ok(link.name);
        assert.equal(new URL(link.href).protocol, 'https:');
      }
    }
  }
  assert.doesNotMatch(JSON.stringify(lessons.cases), /\d{4}\s*타경\s*\d+/);
});

test('each actual choice is graded, with exactly one correct answer per source-reading task', () => {
  for (const item of lessons.cases) {
    item.steps.forEach((step, index) => {
      const results = step.choices.map(choice => lessons.validateAnswer(item.id, index, choice.id));
      assert.ok(results.every(result => result.valid));
      assert.equal(results.filter(result => result.correct).length, 1);
      assert.deepEqual(lessons.validateAnswer(item.id, index, step.correctChoice), {valid: true, correct: true});
      for (const choice of step.choices.filter(choice => choice.id !== step.correctChoice)) {
        assert.deepEqual(lessons.validateAnswer(item.id, index, choice.id), {valid: true, correct: false});
      }
    });
  }
});

test('unknown, missing, inherited and malformed identifiers can never be marked correct', () => {
  const item = lessons.cases[0];
  const answer = item.steps[0].correctChoice;
  const poison = {toString() { throw new Error('must not coerce identifiers'); }};
  const invalid = [
    [], [undefined, undefined, undefined], [null, null, null],
    ['unknown-case', 0, answer], ['', 0, answer], ['__proto__', 0, answer], ['constructor', 0, answer],
    [item.id, -1, answer], [item.id, 6, answer], [item.id, 0.5, answer],
    [item.id, Infinity, answer], [item.id, NaN, answer], [item.id, '0', answer],
    [item.id, 0, undefined], [item.id, 0, ''], [item.id, 0, '__proto__'],
    [item.id, 0, 'constructor'], [item.id, 0, 'unknown-choice'],
    [poison, 0, answer], [item.id, poison, answer], [item.id, 0, poison],
    [Symbol('case'), 0, answer], [item.id, 0n, answer], [item.id, 0, Symbol('choice')],
  ];
  for (const args of invalid) {
    assert.deepEqual(lessons.validateAnswer(...args), {valid: false, correct: false});
  }
});

test('a correct choice from another step or case is not an answer to the current question', () => {
  const [first, second] = lessons.cases;
  assert.deepEqual(lessons.validateAnswer(first.id, 0, first.steps[1].correctChoice), {valid: false, correct: false});
  assert.deepEqual(lessons.validateAnswer(first.id, 0, second.steps[0].correctChoice), {valid: false, correct: false});
  assert.deepEqual(lessons.validateAnswer(second.id, 2, first.steps[2].correctChoice), {valid: false, correct: false});
});

test('the two date scenarios differ, and neither teaches automatic zero or full-deposit liability', () => {
  const tenantStep = item => item.steps.find(step => step.id === 'tenant');
  const date = (step, label) => Date.parse(step.rows.find(row => row.label === label).value);
  const [basic, earlier] = lessons.cases.map(tenantStep);
  assert.ok(date(basic, '임차인 전입일') > date(basic, '근저당권 접수일'));
  assert.ok(date(earlier, '임차인 전입일') < date(earlier, '근저당권 접수일'));
  for (const item of lessons.cases) {
    const step = tenantStep(item);
    const correct = step.choices.find(choice => choice.id === step.correctChoice);
    assert.match(correct.text, /확인/);
    assert.match(step.explanation, /점유/);
    assert.match(step.explanation, /배당/);
    const automaticAnswers = step.choices.filter(choice => /0원|전액/.test(choice.text));
    assert.ok(automaticAnswers.length >= 2);
    for (const choice of automaticAnswers) {
      assert.deepEqual(lessons.validateAnswer(item.id, 2, choice.id), {valid: true, correct: false});
    }
  }
});

test('grading and modifying returned results preserve the source cases and answer keys', () => {
  const before = JSON.stringify({cases: lessons.cases, topics: lessons.topics});
  for (const item of lessons.cases) {
    item.steps.forEach((step, index) => {
      for (const choice of step.choices) lessons.validateAnswer(item.id, index, choice.id);
    });
  }
  const item = lessons.cases[0], answer = item.steps[0].correctChoice;
  const result = lessons.validateAnswer(item.id, 0, answer);
  result.valid = false;
  result.correct = false;
  assert.deepEqual(lessons.validateAnswer(item.id, 0, answer), {valid: true, correct: true});
  assert.throws(() => { item.steps[0].correctChoice = item.steps[0].choices[0].id; }, TypeError);
  assert.throws(() => { item.steps[0].rows[0].value = 'changed'; }, TypeError);
  assert.equal(JSON.stringify({cases: lessons.cases, topics: lessons.topics}), before);
});

test('the browser export loads and grades without storage, network or notebook access', () => {
  const sandbox = {
    localStorage: {getItem() { throw new Error('lesson module must not read notebooks'); }, setItem() { throw new Error('lesson module must not write notebooks'); }},
    fetch() { throw new Error('fictional source excerpts must not make live requests'); },
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(require.resolve('../assets/auction-study-lessons.js'), 'utf8'), sandbox);
  const browser = sandbox.AuctionLessons;
  assert.ok(browser);
  assert.deepEqual(JSON.parse(JSON.stringify(browser.topics)), lessons.topics);
  const item = browser.cases[1];
  assert.equal(browser.validateAnswer(item.id, 2, item.steps[2].correctChoice).correct, true);
  assert.equal(browser.validateAnswer(undefined, undefined, undefined).correct, false);
});
