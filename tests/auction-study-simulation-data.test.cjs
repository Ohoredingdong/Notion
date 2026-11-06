'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const data = require('../_auction/assets/auction-study-simulation-data.js');
const model = require('../_auction/assets/auction-study-model.js');
const format = require('../_auction/assets/auction-study-format.js');

const kinds = ['sale', 'register', 'occupancy', 'appraisal', 'building', 'fees', 'comparables', 'fieldnotes'];
const money = number => number.toLocaleString('ko-KR', { maximumFractionDigits: 2 }) + '만원';
const doc = (item, kind) => item.documents.find(document => document.kind === kind);
const documentText = document => document.sections.flatMap(section => section.rows.map(row => row.label + ': ' + row.value)).join('\n');
const rowValue = (document, label) => document.sections.flatMap(section => section.rows).find(row => row.label === label)?.value;
const approximately = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-7, actual + ' differs from ' + expected);
const [basic, senior, hold] = data.cases;

test('simulation is visibly fictional and separate from real case records', () => {
  assert.equal(data.fictional, true);
  assert.equal(data.amountUnit, '만원');
  assert.match(data.disclaimer, /가상 학습/);
  assert.match(data.disclaimer, /실제 사건.*아니며/);
  assert.match(data.disclaimer, /공식 서류.*재현하지/);
  assert.equal(data.cases.length, 3);
  assert.equal(new Set(data.cases.map(item => item.id)).size, 3);
  for (const item of data.cases) {
    assert.equal(item.fictional, true);
    assert.match(item.address, /^연습시 가상구 /);
    assert.ok(item.title && item.level && item.summary);
    assert.ok(item.area > 0 && Number.isFinite(item.area));
    assert.ok(!JSON.stringify(item).match(/\d{4}타경\d+/), 'do not invent an apparent real court case number');
    for (const document of item.documents) {
      assert.match(document.title, /가상 발췌/);
      assert.ok(document.sourceExplanation.startsWith(data.disclaimer));
    }
  }
});

test('each case contains eight complete document types with globally unique IDs', () => {
  const seen = new Set();
  for (const item of data.cases) {
    assert.deepEqual(item.documents.map(document => document.kind).sort(), [...kinds].sort());
    for (const document of item.documents) {
      assert.ok(document.id.startsWith(item.id + '-'));
      assert.ok(!seen.has(document.id), 'duplicate document ID ' + document.id);
      seen.add(document.id);
      assert.ok(document.sections.length);
      for (const section of document.sections) {
        assert.equal(typeof section.title, 'string');
        assert.ok(section.title.length);
        assert.ok(section.rows.length);
        for (const row of section.rows) {
          assert.equal(typeof row.label, 'string');
          assert.equal(typeof row.value, 'string');
          assert.ok(row.label.length && row.value.length);
          if ('focus' in row) assert.equal(typeof row.focus, 'boolean');
        }
      }
    }
  }
});

test('identity, area and bid figures agree across the document set and calculator defaults', () => {
  for (const item of data.cases) {
    for (const kind of ['sale', 'register', 'building']) assert.ok(documentText(doc(item, kind)).includes(item.address));
    for (const kind of ['sale', 'register', 'building', 'appraisal']) {
      assert.ok(documentText(doc(item, kind)).includes(item.area + '㎡'), kind + ' area mismatch');
    }
    assert.equal(rowValue(doc(item, 'sale'), '감정평가액'), money(item.appraised));
    assert.equal(rowValue(doc(item, 'appraisal'), '감정평가액'), money(item.appraised));
    assert.equal(rowValue(doc(item, 'sale'), '최저 매각가격'), money(item.minimum));
    assert.equal(item.defaults.minimum, item.minimum);
    assert.equal(rowValue(doc(item, 'sale'), '모의 입찰일'), item.facts.bidDate);
    assert.equal(rowValue(doc(item, 'fees'), '예상 낙찰가'), money(item.defaults.bid));
  }
});

test('study timeline is coherent, with junior and senior tenants on opposite sides of the mortgage', () => {
  for (const item of data.cases) {
    const facts = item.facts;
    for (const name of ['asOf', 'bidDate', 'appraisalDate', 'visitDate', 'mortgageDate', 'auctionStartDate', 'distributionDeadline']) {
      assert.match(facts[name], /^\d{4}-\d{2}-\d{2}$/);
      assert.ok(Number.isFinite(Date.parse(facts[name])));
    }
    assert.ok(facts.mortgageDate < facts.auctionStartDate);
    assert.ok(facts.auctionStartDate < facts.distributionDeadline);
    assert.ok(facts.distributionDeadline < facts.asOf);
    assert.ok(facts.appraisalDate <= facts.asOf && facts.visitDate <= facts.asOf);
    assert.ok(facts.asOf < facts.bidDate);
    assert.ok(documentText(doc(item, 'register')).includes(facts.mortgageDate));
    assert.ok(documentText(doc(item, 'register')).includes(facts.auctionStartDate));
    if (facts.tenant) {
      const tenant = facts.tenant;
      assert.ok(tenant.moveInDate <= tenant.fixedDate);
      assert.ok(tenant.fixedDate < facts.auctionStartDate);
      assert.ok(facts.auctionStartDate <= tenant.distributionRequestDate);
      assert.ok(tenant.distributionRequestDate <= facts.distributionDeadline);
      for (const kind of ['sale', 'occupancy']) {
        const text = documentText(doc(item, kind));
        for (const value of [tenant.moveInDate, tenant.fixedDate, tenant.distributionRequestDate, money(tenant.deposit)]) {
          assert.ok(text.includes(value), kind + ' missing tenant evidence ' + value);
        }
      }
    }
  }
  assert.ok(basic.facts.mortgageDate < basic.facts.tenant.moveInDate);
  assert.ok(senior.facts.tenant.moveInDate < senior.facts.mortgageDate);
  assert.equal(hold.facts.tenant, null, 'unknown tenant is not an invented zero-deposit tenant');
});

test('management fee totals are not silently equated with buyer liability', () => {
  for (const item of data.cases) {
    const fees = item.facts.fees;
    assert.equal(rowValue(doc(item, 'fees'), '공용부분 체납'), money(fees.common));
    assert.equal(rowValue(doc(item, 'fees'), '전유부분 체납'), money(fees.private));
    assert.equal(rowValue(doc(item, 'fees'), '연체료'), money(fees.late));
    assert.equal(rowValue(doc(item, 'fees'), '체납 합계'), money(fees.common + fees.private + fees.late));
    assert.equal(rowValue(doc(item, 'fees'), '계산에 반영한 관리비'), money(item.defaults.arrears));
    assert.notEqual(item.defaults.arrears, fees.common + fees.private + fees.late);
    assert.match(rowValue(doc(item, 'fees'), '인수 근거와 정산'), /모의 조건|임시 하한/);
    assert.match(rowValue(doc(item, 'fees'), '인수 근거와 정산'), /실제.*인수/);
  }
});

test('all calculator inputs are explicit, valid, and retain nonzero provisional selling tax', () => {
  const requiredKeys = Object.keys(model.defaults()).sort();
  for (const item of data.cases) {
    assert.deepEqual(Object.keys(item.defaults).sort(), requiredKeys, 'missing calculator key for ' + item.id);
    for (const value of Object.values(item.defaults)) assert.ok(typeof value === 'number' && Number.isFinite(value) && value >= 0);
    assert.ok(item.defaults.saleTax > 0, 'do not hide an unestimated selling tax behind zero');
    assert.ok(item.defaults.loan <= item.defaults.bid);
    assert.ok(item.defaults.bid >= item.minimum);
    const result = model.calculate(item.defaults);
    assert.equal(result.valid, true, item.id + ': ' + result.errors.join(', '));
    for (const [key, value] of Object.entries(result)) {
      if (typeof value === 'number') assert.ok(Number.isFinite(value), item.id + ': invalid result ' + key);
    }
    assert.match(rowValue(doc(item, 'fees'), '매도 세금 예상액'), /추정치.*확인 필요/);
  }
});

test('basic example has an independently checked deposit, cash budget, and two profit scenarios', () => {
  const result = model.calculate(basic.defaults);
  approximately(result.deposit, 2560);
  approximately(result.tax, 297);
  approximately(result.interest, 364.5);
  approximately(result.totalCost, 28721.5);
  approximately(result.cashNeeded, 13021.5);
  approximately(result.profit, 3713.5);
  approximately(result.downsideProfit, 1226);
  approximately(result.cashGap, 0);
  assert.equal(basic.answer.assumedCost, basic.defaults.assumed);
  assert.ok(basic.answer.mainFindings.some(finding => finding.includes('2,560만원')));
  assert.match(documentText(doc(basic, 'sale')), /0만원.*날짜만으로 산정한 결과가 아니/);
  assert.match(basic.answer.plainConclusion, /남은.*확인/);
});

test('senior lease unpaid balance is explicit, arithmetic is coherent, and it changes both cash and profit', () => {
  const tenant = senior.facts.tenant;
  assert.equal(tenant.deposit - tenant.assumedDistribution, tenant.assumedUnpaid);
  assert.equal(tenant.assumedUnpaid, 5000);
  assert.equal(senior.defaults.assumed, tenant.assumedUnpaid);
  assert.equal(senior.answer.assumedCost, tenant.assumedUnpaid);
  const sale = documentText(doc(senior, 'sale'));
  assert.match(sale, /대항요건.*성립.*유지/);
  assert.match(sale, /7,000만원.*가정.*확정 배당표.*아님/);
  assert.match(sale, /5,000만원.*부담.*모의 조건/);
  const result = model.calculate(senior.defaults);
  const omitted = model.calculate({ ...senior.defaults, assumed: 0 });
  approximately(result.cashNeeded, 18464.5);
  approximately(result.cashGap, 464.5);
  approximately(result.profit, 670.5);
  approximately(result.downsideProfit, -2314.5);
  approximately(result.cashNeeded - omitted.cashNeeded, 5000);
  approximately(omitted.profit - result.profit, 5000);
  approximately(result.deposit, omitted.deposit);
  approximately(result.tax, omitted.tax);
  approximately(result.interest, omitted.interest);
  assert.ok(result.profit < senior.defaults.targetProfit);
  assert.ok(result.maxBid < senior.minimum, 'target-profit ceiling is below the permitted bid in this example');
  assert.match(senior.answer.plainConclusion, /부족|서두르지/);
});

test('rendered senior-case explanations agree with current cash inputs rather than its initial funding shortage', () => {
  const script = fs.readFileSync(path.join(__dirname, '../_auction/assets/auction-study-simulation.js'), 'utf8');
  function renderWith(inputs) {
    const sandbox = {
      window: { AuctionSimulationData: data, AuctionModel: model, AuctionFormat: format, addEventListener() {} }, AuctionModel: model,
      localStorage: { getItem() { return null; }, setItem() {} },
      document: { addEventListener() {} },
    };
    vm.createContext(sandbox);
    vm.runInContext(script, sandbox, { timeout: 1000 });
    const simulation = sandbox.window.AuctionSimulation.create();
    simulation.state.caseId = senior.id;
    const record = simulation.record();
    Object.assign(record.inputs, inputs);
    record.reviewed = senior.documents.map(document => document.id);
    for (const question of senior.quiz) {
      record.answers[question.id] = { choiceId: question.answerId, checked: true };
    }
    record.decision = 'hold';
    record.submitted = true;
    const result = simulation.calculation();
    assert.equal(result.valid, true);
    const html = simulation.results(senior, record);
    const text = html.replace(/<[^>]*>/g, ' ');
    // Check the whole rendered explanation, including reusable case findings: a correct
    // dynamic shortage row must not coexist with an obsolete claim elsewhere on screen.
    const claimsInsufficientCash = text.split(/\.(?!\d)/).some(sentence =>
      /(?:순투입|필요)\s*현금.*가용\s*현금.*(?:부족|넘|초과)/.test(sentence));
    assert.equal(claimsInsufficientCash, result.cashGap > 0, 'cash conclusions must follow the current inputs');
    const shortage = text.match(/가용 현금보다\s+([\d,]+(?:\.\d+)?)만원 부족해요/);
    assert.equal(Boolean(shortage), result.cashGap > 0);
    if (shortage) approximately(Number(shortage[1].replaceAll(',', '')), result.cashGap);
    return result;
  }

  const initial = renderWith({});
  const moreCash = renderWith({ available: '30000' });
  const moreLoan = renderWith({ loan: '20000' });
  approximately(initial.cashGap, 464.5);
  approximately(moreCash.cashGap, 0);
  approximately(moreLoan.cashGap, 0);
  approximately(initial.cashNeeded, moreCash.cashNeeded);
  approximately(initial.profit, moreCash.profit);
  assert.ok(moreLoan.cashNeeded < initial.cashNeeded, 'loan changes affect current funding needs');
  assert.ok(moreLoan.profit < initial.profit, 'larger financing also changes interest costs');
});

test('unresolved title and violation case remains on hold even when its incomplete model has a positive profit', () => {
  assert.equal(hold.financialAssumptionsConfirmed, false);
  assert.equal(hold.answer.riskLevel, 'hold');
  assert.equal(hold.answer.assumedCost, null, 'unknown acquisition cost must stay unknown');
  assert.equal(hold.defaults.assumed, 0);
  assert.match(hold.answer.estimatedCostsDescription, /미확정/);
  assert.match(hold.answer.estimatedCostsDescription, /하한 가정.*확인된 0원이 아니/);
  assert.match(rowValue(doc(hold, 'fees'), '별도 인수 금액'), /미확정.*확인된 인수액 0원 아님/);
  assert.match(documentText(doc(hold, 'register')), /미등기.*알 수 없음/);
  assert.match(documentText(doc(hold, 'building')), /위반건축 표시: 있음/);
  assert.match(documentText(doc(hold, 'appraisal')), /원상복구.*미포함/);
  const result = model.calculate(hold.defaults);
  approximately(result.cashNeeded, 13167);
  approximately(result.profit, 2368);
  approximately(result.downsideProfit, -1612);
  assert.ok(result.profit > 0);
  const illustrativeExtra = model.calculate({ ...hold.defaults, assumed: 5000 });
  assert.ok(illustrativeExtra.profit < 0, 'an unknown extra cost can reverse a superficially positive result');
  approximately(illustrativeExtra.cashNeeded - result.cashNeeded, 5000);
  assert.match(hold.answer.plainConclusion, /^입찰 보류/);
});

test('comparables are fictional dated evidence, consistent with their document excerpts', () => {
  for (const item of data.cases) {
    assert.ok(item.comparables.length >= 3);
    const text = documentText(doc(item, 'comparables'));
    for (const comparable of item.comparables) {
      assert.ok(Number.isFinite(comparable.price) && comparable.price > 0);
      assert.ok(Number.isFinite(comparable.area) && comparable.area > 0);
      assert.match(comparable.description, /가상/);
      assert.ok(comparable.date <= item.facts.asOf);
      for (const value of [comparable.date, comparable.area + '㎡', money(comparable.price), comparable.description]) assert.ok(text.includes(value));
    }
    assert.match(doc(item, 'comparables').sections[0].title, /실거래 조회 결과 아님/);
    assert.equal(rowValue(doc(item, 'comparables'), '기준 매도가'), money(item.defaults.sale));
    assert.equal(rowValue(doc(item, 'comparables'), '보수적 매도가'), money(item.defaults.downside));
    assert.ok(rowValue(doc(item, 'comparables'), '비교의 한계'));
  }
});

test('every quiz has one valid answer and an evidence link to its own case document', () => {
  const seen = new Set();
  for (const item of data.cases) {
    assert.ok(item.quiz.length >= 6);
    for (const quiz of item.quiz) {
      assert.ok(!seen.has(quiz.id), 'duplicate question ID ' + quiz.id);
      seen.add(quiz.id);
      assert.ok(item.documents.some(document => document.id === quiz.documentId), 'unknown document ' + quiz.documentId);
      assert.ok(quiz.question && quiz.explanation);
      assert.ok(quiz.choices.length >= 3);
      assert.equal(new Set(quiz.choices.map(choice => choice.id)).size, quiz.choices.length);
      assert.equal(quiz.choices.filter(choice => choice.id === quiz.answerId).length, 1);
      for (const choice of quiz.choices) assert.ok(choice.id && choice.text);
    }
    assert.ok(['review', 'hold'].includes(item.answer.riskLevel));
    assert.ok(item.answer.mainFindings.length >= 3 && item.answer.nextChecks.length >= 3);
  }
});

test('photo observations are visibly staged and cannot serve as proof of legal rights', () => {
  const keys = new Set(['exterior', 'entrance', 'interior', 'damage', 'neighborhood']);
  const seen = new Set();
  for (const item of data.cases) {
    assert.ok(item.observations.length >= 4);
    const text = documentText(doc(item, 'fieldnotes'));
    for (const observation of item.observations) {
      assert.ok(!seen.has(observation.id));
      seen.add(observation.id);
      assert.ok(keys.has(observation.photoKey));
      assert.ok(observation.title && observation.text);
      assert.ok(text.includes(observation.text));
    }
    assert.match(rowValue(doc(item, 'fieldnotes'), '사진 성격'), /연출.*실제.*아님/);
    assert.match(rowValue(doc(item, 'fieldnotes'), '사진으로 확정할 수 없는 것'), /대항력.*누수.*대지권/);
  }
});

test('case photo sheets exist, have 4:3 cells, and agree with the documented building type', () => {
  for (const item of data.cases) {
    const photos = item.photoSet;
    assert.ok(photos, item.id + ' needs its own photo mapping');
    assert.equal(photos.fictional, true);
    assert.equal(photos.aiGenerated, true);
    assert.ok(Number.isInteger(photos.columns) && photos.columns > 1);
    assert.ok(Number.isInteger(photos.rows) && photos.rows > 1);
    assert.match(photos.src, /^\.\/assets\/auction-practice\/[a-z-]+\.png$/);
    const source = fs.readFileSync(path.resolve(__dirname, '..', '_auction', photos.src));
    assert.equal(source.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
    const width = source.readUInt32BE(16), height = source.readUInt32BE(20);
    approximately((width / photos.columns) / (height / photos.rows), 4 / 3);
    const use = rowValue(doc(item, 'building'), '주용도');
    assert.equal(photos.buildingType, use.includes('아파트') ? 'apartment' : 'multifamily');
    const positions = new Set();
    for (const observation of item.observations) {
      const position = photos.positions[observation.photoKey];
      assert.equal(typeof position, 'string', item.id + ': missing cell for ' + observation.photoKey);
      const match = position.match(/^(\d+(?:\.\d+)?)% (\d+(?:\.\d+)?)%$/);
      assert.ok(match, 'invalid contact-sheet coordinate ' + position);
      const [x, y] = match.slice(1).map(Number);
      assert.ok(x <= 100 && y <= 100);
      const column = x / 100 * (photos.columns - 1), row = y / 100 * (photos.rows - 1);
      assert.ok(Math.abs(column - Math.round(column)) < 1e-6 && Math.abs(row - Math.round(row)) < 1e-6, 'coordinate must select a whole cell');
      assert.ok(!positions.has(position), 'different observations must not reuse the same photo');
      positions.add(position);
    }
  }
});

test('two different low-rise case photo sets replace the apartment reuse and preserve the original asset', () => {
  assert.equal(basic.photoSet.src, './assets/auction-practice/field-contact-sheet.png');
  assert.ok(fs.existsSync(path.resolve(__dirname, '..', basic.photoSet.src)));
  for (const item of [senior, hold]) {
    assert.notEqual(item.photoSet.src, basic.photoSet.src, 'a multifamily case must not use the apartment sheet');
    assert.equal(item.photoSet.buildingType, 'multifamily');
  }
  const identity = (item, key) => item.photoSet.src + '|' + item.photoSet.positions[key];
  const seniorCells = new Set(senior.observations.map(observation => identity(senior, observation.photoKey)));
  for (const observation of hold.observations) {
    assert.ok(!seniorCells.has(identity(hold, observation.photoKey)), 'the two low-rise properties must not reuse a scene');
  }
  const windowScene = senior.observations.find(observation => observation.photoKey === 'damage');
  assert.equal(senior.photoSet.damageLocation, 'window');
  assert.match(windowScene.title + windowScene.text, /창가|창틀/);
  assert.match(senior.quiz.find(question => question.id.endsWith('-damage')).question, /창가/);
  assert.match(documentText(doc(senior, 'appraisal')), /창가 얼룩/);
  const wallScene = hold.observations.find(observation => observation.photoKey === 'damage');
  assert.equal(hold.photoSet.damageLocation, 'wall-ceiling');
  assert.match(wallScene.title + wallScene.text, /천장.*벽면/);
  assert.doesNotMatch(wallScene.title + wallScene.text, /창가|창틀/);
});

test('all nested practice values are frozen to protect shared canonical exercises', () => {
  const check = value => {
    if (value && typeof value === 'object') {
      assert.equal(Object.isFrozen(value), true);
      Object.values(value).forEach(check);
    }
  };
  check(data);
  assert.throws(() => { basic.defaults.bid = 1; }, TypeError);
  assert.throws(() => { hold.answer.riskLevel = 'review'; }, TypeError);
});

test('browser UMD exposes the same dataset without reading storage, network, or another widget', () => {
  const script = fs.readFileSync(path.join(__dirname, '../_auction/assets/auction-study-simulation-data.js'), 'utf8');
  const context = vm.createContext({});
  for (const name of ['localStorage', 'document', 'fetch', 'AuctionModel', 'AuctionLessons']) {
    Object.defineProperty(context, name, { get() { throw new Error('unexpected external access: ' + name); } });
  }
  vm.runInContext(script, context, { timeout: 1000 });
  assert.ok(context.AuctionSimulationData);
  assert.equal(context.AuctionSimulationData.fictional, true);
  assert.equal(JSON.stringify(context.AuctionSimulationData), JSON.stringify(data));
});
