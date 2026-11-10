'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const course = require('../_auction/assets/auction-study-course-data.js');
const model = require('../_auction/assets/auction-study-model.js');

const lesson = id => course.lessons.find(item => item.id === id);
const allRows = part => part.documents.flatMap(document => document.rows);
const firstAmount = text => Number(text.match(/[\d,]+(?:\.\d+)?/)[0].replaceAll(',', ''));
const nearly = (left, right) => assert.equal(model.compareAmounts(left, right), 0, `${left} != ${right}`);
const ids = ['auction-flow', 'read-documents', 'bid-deposit', 'cash-needed', 'verify-or-hold'];

test('five beginner lessons provide concepts, a worked example and a separate practice', () => {
  assert.deepEqual(course.lessons.map(item => item.id), ids);
  for (const item of course.lessons) {
    assert.ok(item.title && item.goal && item.basics.lead && item.basics.takeaway);
    assert.ok(item.basics.terms.length >= 3 && item.basics.terms.length <= 4);
    assert.equal(new Set(item.basics.terms.map(term => term.term)).size, item.basics.terms.length);
    for (const term of item.basics.terms) assert.ok(term.term && term.text);
    assert.ok(item.example.title && item.example.answer && item.example.steps.length >= 2);
    for (const step of item.example.steps) assert.ok(step.title && step.text);
    assert.ok(item.practice.id && item.practice.question && item.practice.answerText && item.practice.explanation);
    assert.ok(['amount', 'choice'].includes(item.practice.type));
  }
});

test('all case material is fictional and lookup links do not claim official legal review', () => {
  assert.equal(course.fictional, true);
  assert.match(course.disclaimer, /가상 사례/);
  assert.match(course.disclaimer, /법률 검수 완료 자료가 아닙니다/);
  for (const item of course.lessons) {
    assert.equal(item.example.fictional, true);
    assert.equal(item.practice.fictional, true);
    assert.ok(item.example.assumptions.length > 0);
    for (const part of [item.example, item.practice]) {
      for (const document of part.documents) assert.match(document.title, /가상/);
    }
    assert.ok(item.references.length > 0);
    for (const reference of item.references) {
      const url = new URL(reference.href);
      assert.equal(url.protocol, 'https:');
      assert.ok(['www.courtauction.go.kr', 'www.iros.go.kr'].includes(url.hostname));
      assert.equal(url.pathname, '/');
      assert.ok(reference.name && reference.note);
    }
    assert.equal('legallyVerified' in item, false);
    assert.equal('officiallyReviewed' in item, false);
  }
});

test('document IDs are unique and every explanation points to rows in the correct case', () => {
  const seen = new Set(ids);
  for (const item of course.lessons) {
    for (const part of [item.example, item.practice]) {
      assert.ok(part.documents.length);
      const rowIds = new Set();
      for (const document of part.documents) {
        assert.ok(!seen.has(document.id));
        seen.add(document.id);
        assert.ok(document.rows.length >= 2);
        for (const row of document.rows) {
          assert.ok(!seen.has(row.id), 'duplicate row ' + row.id);
          seen.add(row.id); rowIds.add(row.id);
          assert.equal(typeof row.label, 'string');
          assert.equal(typeof row.value, 'string');
          assert.ok(row.label && row.value);
        }
      }
      const evidence = part === item.example
        ? part.steps.flatMap(step => step.evidenceIds || []) : part.evidenceIds;
      assert.ok(evidence.length);
      for (const id of evidence) assert.ok(rowIds.has(id), 'cross-case or missing evidence ' + id);
    }
    assert.ok(allRows(item.example).some(row => row.focus === true));
    assert.ok(allRows(item.practice).every(row => !row.focus), 'practice evidence must not be pre-highlighted');
  }
});

test('practice changes the property and scenario instead of repeating the worked answer', () => {
  for (const item of course.lessons) {
    assert.notEqual(allRows(item.example)[0].value, allRows(item.practice)[0].value);
    assert.notDeepEqual(item.example.inputs || item.example.facts, item.practice.inputs || item.practice.facts);
    // Feedback and the key stay outside the source excerpts so the UI can reveal
    // them only after submission; no stored state is needed in this data module.
    for (const document of item.practice.documents) {
      for (const key of ['answer', 'answerId', 'answerValue', 'explanation', 'evidenceIds']) assert.equal(key in document, false);
    }
  }
});

test('payment example and practice distinguish ownership, registration and actual delivery', () => {
  const item = lesson('auction-flow');
  assert.equal(item.example.facts.fullPayment, false);
  assert.equal(item.practice.facts.fullPayment, true);
  assert.equal(item.practice.facts.registrationComplete, false);
  assert.equal(item.practice.facts.deliveryComplete, false);
  assert.match(item.basics.terms.find(term => term.term === '완납').text, /소유권/);
  assert.match(item.basics.terms.find(term => term.term === '등기·인도').text, /등기는.*인도는/);
  for (const part of [item.example, item.practice]) assert.match(allRows(part)[0].value, /소유권 전부 매각/);
  assert.deepEqual(course.grade(item.id, 'paid-separate'), { valid: true, correct: true });
  assert.deepEqual(course.grade(item.id, 'permission-complete'), { valid: true, correct: false });
  assert.deepEqual(course.grade(item.id, 'move-in-now'), { valid: true, correct: false });
});

test('same-area different-unit documents require reconciliation, not an invented match', () => {
  const item = lesson('read-documents');
  const [sale, register] = item.practice.documents;
  const unit = document => document.rows[0].value.match(/(\d+)호/)[1];
  assert.equal(unit(sale), '802');
  assert.equal(unit(register), '803');
  assert.equal(firstAmount(sale.rows[1].value), firstAmount(register.rows[1].value));
  assert.equal(item.practice.facts.sameUnit, false);
  assert.deepEqual(course.grade(item.id, 'reconcile-unit'), { valid: true, correct: true });
  assert.deepEqual(course.grade(item.id, 'area-is-enough'), { valid: true, correct: false });
  assert.deepEqual(course.grade(item.id, 'pick-one-unit'), { valid: true, correct: false });
});

test('deposit arithmetic uses each notice rate and minimum rather than the intended bid', () => {
  const item = lesson('bid-deposit');
  const example = item.example.inputs, practice = item.practice.inputs;
  nearly(example.minimum * example.depositRate / 100, 1000);
  nearly(firstAmount(item.example.answer), 1000);
  nearly(example.bid - 1000, 11000);
  nearly(practice.minimum * practice.depositRate / 100, 1600);
  assert.notEqual(example.depositRate, practice.depositRate);
  assert.match(item.example.assumptions.join(' '), /모의 공고/);
  assert.match(item.practice.documents[0].rows.find(row => row.id.endsWith('-rate')).value, /모의 공고/);
  assert.equal(firstAmount(item.practice.documents[0].rows.find(row => row.id.endsWith('-minimum')).value), practice.minimum);
  assert.deepEqual(course.grade(item.id, 1600), { valid: true, correct: true });
  assert.deepEqual(course.grade(item.id, '1,600'), { valid: true, correct: true });
  assert.deepEqual(course.grade(item.id, 800), { valid: true, correct: false }); // Incorrectly assume 10%.
  assert.deepEqual(course.grade(item.id, 1900), { valid: true, correct: false }); // Incorrectly use the 9,500 bid.
  assert.match(allRows(item.example).find(row => row.id.endsWith('-minimum')).value, /10,000만원\(1억원\)/);
});

test('cash examples independently reconcile purchase, costs, financing and reserve without double-counting the deposit', () => {
  const item = lesson('cash-needed');
  function check(part, expected) {
    const input = part.inputs;
    const independent = input.bid + input.costs - input.loan + input.reserve;
    nearly(independent, expected);
    const value = text => firstAmount(allRows(part).find(row => row.id.endsWith(text)).value);
    for (const key of ['bid', 'costs', 'loan', 'reserve', 'deposit']) nearly(value('-' + key), input[key]);
    // Allocate the supplied aggregate cost to one fixed-cost input just to check
    // the existing cash formula. This is not a real tax or loan eligibility model.
    const fields = Object.fromEntries(Object.keys(model.defaults()).map(key => [key, 0]));
    const result = model.calculate({ ...fields, bid: input.bid, minimum: input.bid, depositRate: 10,
      legal: input.costs, loan: input.loan, reserve: input.reserve });
    assert.equal(result.valid, true);
    nearly(result.cashNeeded, independent);
    return independent;
  }
  nearly(check(item.example, 5000), firstAmount(item.example.answer));
  const expected = check(item.practice, 7300);
  assert.deepEqual(course.grade(item.id, expected), { valid: true, correct: true });
  assert.deepEqual(course.grade(item.id, '7,300'), { valid: true, correct: true });
  assert.deepEqual(course.grade(item.id, expected + item.practice.inputs.deposit), { valid: true, correct: false });
  assert.deepEqual(course.grade(item.id, expected - item.practice.inputs.reserve), { valid: true, correct: false });
  assert.match(item.example.assumptions.join(' '), /미확정.*완전한 필요 현금.*볼 수 없/);
  assert.match(item.practice.explanation, /대출.*지급 시점.*별도 확인/);
});

test('positive displayed profit and an occupant interview do not resolve an unknown acquisition cost', () => {
  const item = lesson('verify-or-hold');
  assert.equal(item.example.facts.occupantContacted, false);
  assert.equal(item.practice.facts.occupantContacted, true);
  assert.equal(item.example.facts.assumedCost, null);
  assert.equal(item.practice.facts.assumedCost, null);
  assert.equal(item.example.facts.displayedAssumed, 0);
  assert.ok(item.practice.facts.modeledProfit > 0);
  assert.equal(item.practice.facts.decision, 'hold');
  assert.deepEqual(course.grade(item.id, 'hold-for-evidence'), { valid: true, correct: true });
  assert.deepEqual(course.grade(item.id, 'profit-is-enough'), { valid: true, correct: false });
  assert.deepEqual(course.grade(item.id, 'unknown-is-zero'), { valid: true, correct: false });
  assert.match(item.basics.terms.find(term => term.term === '폐문부재').text, /빈집.*아니/);
  assert.match(item.basics.takeaway, /모른다면.*0원.*않아요/);
});

test('amount grading rejects blank, malformed and coercible inputs instead of turning them into zero', () => {
  const poison = { toString() { throw new Error('must not coerce answer objects'); } };
  const invalid = [undefined, null, '', ' ', '\n', true, false, [], {}, poison, Symbol('amount'), 1600n,
    NaN, Infinity, -Infinity, -1, '-1600', 'NaN', 'Infinity', '0x640', '1e3', '1,60', '1,600,0', '1600만원', '1_600', '9'.repeat(400)];
  for (const id of ['bid-deposit', 'cash-needed']) {
    for (const answer of invalid) assert.deepEqual(course.grade(id, answer), { valid: false, correct: false });
    assert.deepEqual(course.grade(id, 0), { valid: true, correct: false });
    assert.deepEqual(course.grade(id, '0'), { valid: true, correct: false });
  }
});

test('only floating-point noise is tolerated; a real one-won difference is an incorrect answer', () => {
  for (const id of ['bid-deposit', 'cash-needed']) {
    const correct = lesson(id).practice.answerValue;
    assert.deepEqual(course.grade(id, correct + Number.EPSILON * correct), { valid: true, correct: true });
    assert.deepEqual(course.grade(id, correct + 0.0001), { valid: true, correct: false });
    assert.deepEqual(course.grade(id, correct - 0.0001), { valid: true, correct: false });
    assert.deepEqual(course.grade(id, correct + 0.01), { valid: true, correct: false });
  }
});

test('choice grading validates identifiers and returns only grading flags', () => {
  for (const item of course.lessons.filter(item => item.practice.type === 'choice')) {
    for (const answer of [undefined, null, '', 0, false, {}, [], '__proto__', 'constructor', 'unknown']) {
      assert.deepEqual(course.grade(item.id, answer), { valid: false, correct: false });
    }
    const results = item.practice.choices.map(choice => course.grade(item.id, choice.id));
    assert.equal(results.filter(result => result.correct).length, 1);
    assert.ok(results.every(result => result.valid && Object.keys(result).sort().join(',') === 'correct,valid'));
  }
  for (const id of [undefined, null, '', '__proto__', 'constructor', 'unknown', {}, [], Symbol('lesson')]) {
    assert.deepEqual(course.grade(id, 'hold-for-evidence'), { valid: false, correct: false });
  }
  const result = course.grade('bid-deposit', 1600);
  result.correct = false;
  assert.equal(course.grade('bid-deposit', 1600).correct, true);
});

test('the entire course is frozen and grading cannot alter its canonical teaching material', () => {
  function check(value) {
    if (value && typeof value === 'object') {
      assert.equal(Object.isFrozen(value), true);
      Object.values(value).forEach(check);
    }
  }
  check(course);
  const before = JSON.stringify(course);
  assert.throws(() => { lesson('bid-deposit').practice.answerValue = 0; }, TypeError);
  assert.throws(() => { lesson('auction-flow').example.documents[0].rows.pop(); }, TypeError);
  for (const item of course.lessons) course.grade(item.id, item.practice.answerId || item.practice.answerValue);
  assert.equal(JSON.stringify(course), before);
});

test('browser UMD works using only AuctionModel and never reads or writes notes, storage or network', () => {
  const script = fs.readFileSync(require.resolve('../_auction/assets/auction-study-course-data.js'), 'utf8');
  const sandbox = { AuctionModel: model };
  for (const name of ['localStorage', 'sessionStorage', 'fetch', 'document', 'AuctionLessons', 'AuctionSimulationData']) {
    Object.defineProperty(sandbox, name, { get() { throw new Error('unexpected access: ' + name); } });
  }
  vm.runInNewContext(script, sandbox, { timeout: 1000 });
  assert.equal(JSON.stringify(sandbox.AuctionCourseData), JSON.stringify(course));
  assert.equal(sandbox.AuctionCourseData.grade('cash-needed', '7300').correct, true);
  assert.throws(() => vm.runInNewContext(script, {}), /requires AuctionModel/);
});
