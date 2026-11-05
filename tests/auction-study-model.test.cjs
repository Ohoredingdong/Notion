'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const model = require('../assets/auction-study-model.js');

function near(actual, expected, tolerance = 1e-8) {
  assert.ok(Math.abs(actual - expected) < tolerance, `${actual} differs from ${expected}`);
}

test('default scenario accounts for purchase, carrying costs and exit proceeds in 만원', () => {
  const r = model.calculate(model.defaults());
  assert.equal(r.valid, true);
  assert.deepEqual(r.errors, []);
  assert.equal(r.deposit, 2450);
  near(r.tax, 308);
  assert.equal(r.interest, 378);
  assert.equal(r.costs, 2056);
  assert.equal(r.totalCost, 30056);
  assert.equal(r.cashNeeded, 13756);
  assert.equal(r.balanceCash, 9178);
  assert.equal(r.profit, 3774);
  assert.equal(r.downsideProfit, 789);
  assert.equal(r.cashGap, 0);
  near(r.roi, 3774 / 13256 * 100);
});

test('deposit rate changes the payment schedule without double counting total cost or profit', () => {
  const base = model.calculate();
  const changed = model.calculate({ depositRate: 20 });
  assert.equal(changed.deposit, 4900);
  assert.equal(changed.balanceCash, base.balanceCash - 2450);
  for (const field of ['costs', 'totalCost', 'cashNeeded', 'profit', 'downsideProfit', 'maxBid']) {
    assert.equal(changed[field], base[field]);
  }
});

test('reserve increases cash needed and cash shortfall but is not treated as a consumed expense', () => {
  const base = model.calculate();
  const r = model.calculate({ reserve: 2500, available: 14000 });
  assert.equal(r.cashNeeded, base.cashNeeded + 2000);
  assert.equal(r.cashGap, 1756);
  assert.equal(r.profit, base.profit);
  assert.equal(r.roi, base.roi);
  assert.equal(r.totalCost, base.totalCost);
});

test('all entered non-price costs and sale taxes reduce profit', () => {
  const base = model.calculate();
  const r = model.calculate({ assumed: 1000, saleTax: 300 });
  assert.equal(r.cashNeeded, base.cashNeeded + 1000);
  assert.equal(r.profit, base.profit - 1300);
  assert.equal(r.downsideProfit, base.downsideProfit - 1300);
});

test('negative sale proceeds and downside profit are preserved for loss scenarios', () => {
  const r = model.calculate({ sale: 28000, downside: 20000 });
  assert.equal(r.valid, true);
  assert.equal(r.profit, -2196);
  assert.equal(r.downsideProfit, -10156);
  assert.ok(r.roi < 0);
});

test('maximum bid algebra achieves target profit with the same financing and selling assumptions', () => {
  const r = model.calculate();
  const atCeiling = model.calculate({ bid: r.maxBid });
  assert.equal(atCeiling.valid, true);
  near(atCeiling.profit, r.input.targetProfit);
  const aboveCeiling = model.calculate({ bid: r.maxBid + 100 });
  assert.ok(aboveCeiling.profit < r.input.targetProfit);
});

test('zero interest and zero holding period do not invent carrying costs', () => {
  assert.equal(model.calculate({ loanRate: 0 }).interest, 0);
  assert.equal(model.calculate({ months: 0 }).interest, 0);
});

test('financing cannot erase the initial deposit requirement or create negative later-payment cash', () => {
  const r = model.calculate({ loan: 28000 });
  assert.equal(r.valid, true);
  assert.equal(r.balanceCash, 0);
  assert.equal(r.deposit, 2450);
});

test('ROI is unavailable when invested equity is zero rather than reporting infinite returns', () => {
  const r = model.calculate({ loan: 28000, acquisitionRate: 0, legal: 0, repairs: 0,
    eviction: 0, arrears: 0, loanRate: 0, reserve: 500 });
  assert.equal(r.valid, true);
  assert.equal(r.roi, null);
  assert.equal(r.cashNeeded, 500);
});

test('minimum bid and financing constraints reject scenarios without stale output fields', () => {
  for (const input of [{ bid: 24000 }, { loan: 28001 }]) {
    const r = model.calculate(input);
    assert.equal(r.valid, false);
    assert.ok(r.errors.length);
    assert.equal(Object.hasOwn(r, 'profit'), false);
    assert.equal(Object.hasOwn(r, 'maxBid'), false);
  }
});

test('explicit blank, missing-value representations, booleans and nonfinite inputs are rejected', () => {
  for (const value of ['', '  ', null, undefined, false, NaN, Infinity, 'not a number']) {
    const r = model.calculate({ bid: value });
    assert.equal(r.valid, false, `Should reject ${String(value)}`);
  }
  assert.equal(model.calculate({ bid: '28000', loanRate: '4.5' }).valid, true);
});

test('negative values and rates outside the declared 0..100 interval are rejected', () => {
  for (const field of Object.keys(model.defaults())) {
    assert.equal(model.calculate({ [field]: -1 }).valid, false, field);
  }
  for (const field of ['depositRate', 'loanRate', 'acquisitionRate', 'sellingRate']) {
    assert.equal(model.calculate({ [field]: 101 }).valid, false, field);
  }
});

test('default input objects are independent and caller input is never mutated', () => {
  const first = model.defaults();
  first.bid = 1;
  assert.equal(model.defaults().bid, 28000);
  const input = Object.freeze({ bid: '28000', repairs: 1200 });
  const r = model.calculate(input);
  assert.equal(input.bid, '28000');
  assert.equal(r.input.bid, 28000);
  assert.equal(r.input.repairs, 1200);
});

test('unusable whole inputs and overflowing calculations fail validation', () => {
  assert.equal(model.calculate(null).valid, false);
  assert.equal(model.calculate([]).valid, false);
  assert.equal(model.calculate({ bid: Number.MAX_VALUE, loan: Number.MAX_VALUE,
    loanRate: 100, months: Number.MAX_VALUE }).valid, false);
});

test('browser global exposes the same API without a module loader', () => {
  const context = {};
  vm.runInNewContext(fs.readFileSync(require.resolve('../assets/auction-study-model.js'), 'utf8'), context);
  assert.equal(context.AuctionModel.calculate().profit, 3774);
  assert.equal(context.AuctionModel.defaults().bid, 28000);
});
