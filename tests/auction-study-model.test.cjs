'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const model = require('../_auction/assets/auction-study-model.js');

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
  assert.equal(r.balanceCredit, 0);
  assert.equal(r.profit, 3774);
  assert.equal(r.downsideProfit, 789);
  assert.equal(r.cashGap, 0);
  assert.equal(r.depositGap, 0);
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

test('an algebraic bid ceiling below the auction minimum remains an infeasible scenario', () => {
  const r = model.calculate({ sale: 20000 });
  assert.equal(r.valid, true);
  assert.ok(r.maxBid < r.input.minimum);
  assert.ok(r.maxBid < r.input.loan);
  assert.ok(r.profit < r.input.targetProfit);
  // The ceiling is a sensitivity result, not an exemption from the bid or loan constraints.
  assert.equal(model.calculate({ sale: 20000, bid: r.maxBid }).valid, false);
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
  assert.equal(r.balanceCredit, 2022);
});

test('deposit shortfall remains visible when full financing covers the net cash requirement', () => {
  const r = model.calculate({ loan: 28000, acquisitionRate: 0, legal: 0, repairs: 0,
    eviction: 0, arrears: 0, loanRate: 0, reserve: 500, available: 1000 });
  assert.equal(r.valid, true);
  assert.equal(r.cashNeeded, 500);
  assert.equal(r.cashGap, 0);
  assert.equal(r.deposit, 2450);
  assert.equal(r.depositGap, 1450);
  assert.equal(r.balanceCash, 0);
  assert.equal(r.balanceCredit, 2450);
});

test('cash ledger reconciles both ordinary financing and a credit at settlement', () => {
  for (const loan of [0, 16800, 28000]) {
    const r = model.calculate({ loan });
    // Money paid for the deposit, settlement, later work/interest and reserve,
    // less an assumed settlement credit, equals the final net cash input.
    const laterPayments = 800 + 300 + 150 + r.interest;
    near(r.deposit + r.balanceCash - r.balanceCredit + laterPayments + 500, r.cashNeeded);
    assert.ok(r.balanceCash === 0 || r.balanceCredit === 0);
  }
});

test('independent all-cash ledger includes assumed obligations and exit tax without inventing loan interest', () => {
  const r = model.calculate({ bid: 10000, minimum: 8000, depositRate: 10, loan: 0,
    loanRate: 7, months: 12, acquisitionRate: 3, legal: 80, repairs: 150,
    eviction: 20, arrears: 0, assumed: 250, reserve: 400, sale: 12500,
    downside: 11000, sellingRate: 1, saleTax: 300, targetProfit: 1000, available: 10000 });
  assert.equal(r.valid, true);
  assert.equal(r.deposit, 800);
  assert.equal(r.interest, 0);
  assert.equal(r.costs, 800);
  assert.equal(r.totalCost, 10800);
  assert.equal(r.balanceCash, 9580);
  assert.equal(r.balanceCredit, 0);
  assert.equal(r.cashNeeded, 11200);
  assert.equal(r.cashGap, 1200);
  assert.equal(r.depositGap, 0);
  assert.equal(r.profit, 1275);
  assert.equal(r.downsideProfit, -210);
  near(r.roi, 11.805555555555555);
});

test('an extra six months costs exactly six months of simple interest while principal stays fixed', () => {
  const base = model.calculate();
  const longer = model.calculate({ months: 12 });
  assert.equal(longer.interest, 756);
  assert.equal(longer.cashNeeded - base.cashNeeded, 378);
  assert.equal(base.profit - longer.profit, 378);
  assert.equal(base.downsideProfit - longer.downsideProfit, 378);
  assert.equal(longer.balanceCash, base.balanceCash);
});

test('sale-price sensitivity reflects sale costs and does not change acquisition funding', () => {
  const base = model.calculate();
  const changed = model.calculate({ sale: 35000, downside: 32000 });
  assert.equal(changed.profit - base.profit, 995);
  assert.equal(changed.downsideProfit - base.downsideProfit, 995);
  assert.equal(changed.cashNeeded, base.cashNeeded);
  assert.equal(changed.cashGap, base.cashGap);
});

test('each fixed acquisition or holding obligation raises funding and lowers both exit results once', () => {
  const base = model.calculate();
  const input = model.defaults();
  for (const field of ['legal', 'repairs', 'eviction', 'arrears', 'assumed']) {
    const r = model.calculate({ [field]: input[field] + 275 });
    assert.equal(r.cashNeeded - base.cashNeeded, 275, field);
    assert.equal(base.profit - r.profit, 275, field);
    assert.equal(base.downsideProfit - r.downsideProfit, 275, field);
  }
});

test('no proceeds preserves the entire economic loss including sale tax', () => {
  const r = model.calculate({ sale: 0, downside: 0, saleTax: 200 });
  assert.equal(r.valid, true);
  assert.equal(r.profit, -30256);
  assert.equal(r.downsideProfit, -30256);
});

test('a zero-valued scenario produces finite zero cash flows and no fabricated ROI', () => {
  const zeroes = Object.fromEntries(Object.keys(model.defaults()).map(key => [key, 0]));
  const r = model.calculate(zeroes);
  assert.equal(r.valid, true);
  for (const field of ['deposit', 'tax', 'interest', 'costs', 'totalCost', 'cashNeeded',
    'balanceCash', 'balanceCredit', 'profit', 'downsideProfit', 'maxBid', 'cashGap', 'depositGap']) {
    assert.equal(r[field], 0, field);
  }
  assert.equal(r.roi, null);
});

test('all money, period and rate fields reject blank form values instead of silently using a default', () => {
  for (const field of Object.keys(model.defaults())) {
    for (const value of ['', ' \t ', undefined, null]) {
      const r = model.calculate({ [field]: value });
      assert.equal(r.valid, false, `${field}: ${String(value)}`);
      assert.equal(Object.hasOwn(r, 'cashNeeded'), false, field);
      assert.equal(Object.hasOwn(r, 'depositGap'), false, field);
    }
  }
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
  vm.runInNewContext(fs.readFileSync(require.resolve('../_auction/assets/auction-study-model.js'), 'utf8'), context);
  assert.equal(context.AuctionModel.calculate().profit, 3774);
  assert.equal(context.AuctionModel.defaults().bid, 28000);
  assert.equal(context.AuctionModel.compareAmounts(0.1 + 0.2, 0.3), 0);
});

test('amount comparisons tolerate binary arithmetic noise without rounding real money differences away', () => {
  assert.equal(model.compareAmounts(0.1 + 0.2, 0.3), 0);
  assert.equal(model.compareAmounts(9882.900000000001, 9882.9), 0);
  assert.equal(model.compareAmounts(1999.9999999999964, 2000), 0);
  assert.equal(model.compareAmounts(9882.91, 9882.9), 1);
  assert.equal(model.compareAmounts(9882.89, 9882.9), -1);
  assert.equal(model.compareAmounts(0.000001, 0), 1);
  assert.equal(model.compareAmounts(-0.000001, 0), -1);
  // A relative epsilon alone would erase this representable 0.01만원 difference.
  assert.equal(model.compareAmounts(1e13 + 0.01, 1e13), 1);
  for (const value of [NaN, Infinity, undefined, null, '0']) {
    assert.equal(Number.isNaN(model.compareAmounts(value, 0)), true);
    assert.equal(Number.isNaN(model.compareAmounts(0, value)), true);
  }
});

test('an exactly funded decimal budget has no fictitious zero-won shortfall', () => {
  // 24,500 + 269.5 tax + 1,370 fixed costs + 43.4 interest - 16,800 + 500.
  const input = { bid: 24500, minimum: 24500, loan: 16800, loanRate: 3.1,
    months: 1, available: 9882.9 };
  const funded = model.calculate(input);
  assert.equal(funded.valid, true);
  near(funded.cashNeeded, 9882.9);
  assert.equal(funded.cashGap, 0);
  const short = model.calculate({ ...input, available: 9882.89 });
  near(short.cashGap, 0.01);
  assert.ok(short.cashGap > 0);
});

test('an exactly funded decimal deposit is not flagged while a 0.01만원 shortage is retained', () => {
  // 1,024.4 × 30% = 307.32 exactly in decimal arithmetic.
  const input = { minimum: 1024.4, depositRate: 30, available: 307.32 };
  const funded = model.calculate(input);
  assert.equal(funded.valid, true);
  assert.equal(funded.depositGap, 0);
  near(funded.deposit, 307.32);
  const short = model.calculate({ ...input, available: 307.31 });
  near(short.depositGap, 0.01);
  assert.ok(short.depositGap > 0);
});

test('decimal break-even proceeds produce zero rather than a phantom loss or negative zero', () => {
  // Sale 33,100 - 99.3 selling cost - 500 exit tax = cost basis 32,500.7.
  const input = { bid: 24500, minimum: 24500, loan: 16800, loanRate: 3.1,
    months: 1, sale: 33100, downside: 33100, sellingRate: 0.3,
    saleTax: 500, repairs: 7117.8 };
  const even = model.calculate(input);
  assert.equal(even.valid, true);
  assert.equal(even.profit, 0);
  assert.equal(even.downsideProfit, 0);
  assert.equal(Object.is(even.profit, -0), false);
  const loss = model.calculate({ ...input, repairs: 7117.81 });
  const gain = model.calculate({ ...input, repairs: 7117.79 });
  near(loss.profit, -0.01);
  near(gain.profit, 0.01);
  assert.ok(loss.profit < 0 && gain.profit > 0);
});

test('target profit at the algebraic ceiling compares equal, but a 0.01만원 higher bid misses it', () => {
  const input = { minimum: 10000, loan: 10000, sale: 28000, downside: 28000,
    acquisitionRate: 3.5, saleTax: 500, available: 50000, targetProfit: 2000 };
  const ceiling = model.calculate(input).maxBid;
  const atCeiling = model.calculate({ ...input, bid: ceiling });
  const above = model.calculate({ ...input, bid: ceiling + 0.01 });
  assert.equal(atCeiling.valid, true);
  assert.equal(model.compareAmounts(atCeiling.profit, 2000), 0);
  assert.equal(model.compareAmounts(above.profit, 2000), -1);
  near(atCeiling.profit - above.profit, 0.01035);
});

test('minimum-price and loan-price boundaries ignore only arithmetic noise', () => {
  assert.equal(model.calculate({ bid: 24500 - 4e-12 }).valid, true);
  assert.equal(model.calculate({ loan: 28000 + 4e-12 }).valid, true);
  assert.equal(model.calculate({ bid: 24499.99 }).valid, false);
  assert.equal(model.calculate({ loan: 28000.01 }).valid, false);
  assert.equal(model.compareAmounts(24500 + 4e-12, 24500), 0);
  assert.equal(model.compareAmounts(24499.99, 24500), -1);
});
