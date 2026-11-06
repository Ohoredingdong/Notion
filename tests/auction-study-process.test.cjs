'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const processData = require('../_auction/assets/auction-study-process.js');

const requiredStages = ['application', 'commencement', 'investigation', 'distribution-deadline', 'sale-preparation', 'sale-notice', 'bidding', 'permission', 'finalization', 'payment', 'registration', 'distribution', 'delivery', 'failed-auction', 'reauction', 'complete'];
const text = value => typeof value === 'string' && value.trim().length > 0;

test('the learning map covers the normal route and both kinds of renewed sale', () => {
  assert.deepEqual(processData.stages.map(stage => stage.id), requiredStages);
  assert.equal(new Set(processData.stages.map(stage => stage.id)).size, processData.stages.length);
  const ids = new Set(requiredStages);
  const names = new Set(processData.documentSet.map(document => document.name));
  for (const stage of processData.stages) {
    for (const field of ['id', 'title', 'phase', 'description', 'timingNote']) {
      assert.ok(text(stage[field]), `${stage.id}: ${field} missing`);
    }
    assert.ok(stage.documents.length > 0, `${stage.id}: document references missing`);
    assert.ok(stage.documents.every(name => names.has(name)), `${stage.id}: unknown document name`);
    assert.ok(stage.actions.length > 0 && stage.actions.every(text), `${stage.id}: actions missing`);
    assert.ok(stage.branches.length > 0, `${stage.id}: branches missing`);
    for (const branch of stage.branches) {
      assert.ok(text(branch.label) && text(branch.note));
      assert.ok(branch.to === null || ids.has(branch.to), `${stage.id}: missing target ${branch.to}`);
      if (branch.to === null) assert.equal(stage.id, 'complete');
    }
  }
  const reachable = new Set();
  const pending = ['application'];
  while (pending.length) {
    const id = pending.shift();
    if (reachable.has(id)) continue;
    reachable.add(id);
    const stage = processData.stages.find(item => item.id === id);
    for (const branch of stage.branches) if (branch.to !== null) pending.push(branch.to);
  }
  assert.equal(reachable.size, requiredStages.length, 'every stage must be reachable from the start');
});

test('nine document guides have unique ids, usable checks and privacy-aware sources', () => {
  assert.equal(processData.documentSet.length, 9);
  assert.equal(new Set(processData.documentSet.map(document => document.id)).size, 9);
  assert.equal(new Set(processData.documentSet.map(document => document.name)).size, 9);
  for (const document of processData.documentSet) {
    for (const field of ['id', 'name', 'purpose', 'when', 'where']) assert.ok(text(document[field]), `${document.id}: ${field} missing`);
    assert.ok(document.checklist.length >= 3 && document.checklist.every(text));
  }
  const tenancy = processData.documentSet.find(document => document.id === 'tenancy');
  assert.match(tenancy.where, /자격.*신청 요건.*적법/);
  assert.match(tenancy.checklist.join(' '), /개인정보.*입력하지/);
  const management = processData.documentSet.find(document => document.id === 'management');
  assert.match(management.checklist.join(' '), /개별 세대 체납 증빙.*구분/);
});

test('decision points distinguish ownership, registration, deposit rules and lawful delivery', () => {
  const stage = id => processData.stages.find(item => item.id === id);
  assert.match(stage('payment').description, /매각대금을 다 낸 때/);
  assert.match(stage('payment').description, /이전등기.*인도.*별도/);
  assert.match(stage('finalization').timingNote, /확정만으로 소유권.*않습니다/);
  assert.deepEqual(stage('payment').branches.map(branch => branch.to), ['registration', 'distribution', 'delivery', 'reauction']);
  assert.match(stage('payment').timingNote, /병행.*고정된 순서가 아닙니다/);
  assert.match(stage('bidding').actions.join(' '), /최저매각가격 × 보증 비율/);
  assert.match(stage('bidding').actions.join(' '), /재매각.*비율이 달라/);
  assert.match(stage('sale-notice').actions.join(' '), /사유 공간.*허락 없이 들어가지/);
  assert.match(stage('delivery').actions.join(' '), /신청기간.*상대방.*권원/);
  assert.match(stage('delivery').actions.join(' '), /임의로 문을 열거나.*옮기지 마세요/);
  assert.match(stage('reauction').description, /단순 유찰.*구분/);
});

test('the map uses actual court schedules instead of a universal flowchart timetable', () => {
  const copy = JSON.stringify(processData);
  assert.match(processData.disclaimer, /법원 공고·사건 진행·기한을 직접 확인/);
  assert.match(processData.disclaimer, /학습 자료/);
  assert.match(processData.disclaimer, /권리·인수금액은 별도 검토가 필요/);
  assert.doesNotMatch(copy, /10\s*[:시]\s*00|11\s*[:시]\s*10|\d+\s*일\s*(이내|후|전|내)|\d+\s*%/);
  for (const milestone of processData.milestones) {
    assert.ok(text(milestone.id) && text(milestone.title));
    assert.ok(milestone.stageIds.length && milestone.stageIds.every(id => requiredStages.includes(id)));
    assert.ok(milestone.checks.length && milestone.checks.every(text));
  }
  assert.equal(new Set(processData.milestones.map(item => item.id)).size, processData.milestones.length);
});

test('the browser export is immutable and works without network or notebook access', () => {
  const forbidden = () => { throw new Error('process learning map must not access network or storage'); };
  const sandbox = {fetch: forbidden, localStorage: {getItem: forbidden, setItem: forbidden}};
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(require.resolve('../_auction/assets/auction-study-process.js'), 'utf8'), sandbox);
  assert.ok(sandbox.AuctionProcessData);
  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.AuctionProcessData)), JSON.parse(JSON.stringify(processData)));
  assert.throws(() => { processData.stages[0].title = 'changed'; }, TypeError);
  assert.throws(() => { processData.documentSet[0].checklist.push('changed'); }, TypeError);
  assert.throws(() => { processData.milestones[0].checks[0] = 'changed'; }, TypeError);
});
