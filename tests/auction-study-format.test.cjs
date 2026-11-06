'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const Model = require('../_auction/assets/auction-study-model.js');
const Format = require('../_auction/assets/auction-study-format.js');

test('ordinary amounts retain the existing 만원 precision and do not invent negative zero', () => {
  assert.deepEqual(Format.parts(13756), { text: '13,756', unit: '만원', valid: true });
  assert.equal(Format.money(13021.5), '13,021.5만원');
  assert.equal(Format.money(0.01), '0.01만원');
  assert.equal(Format.money(-0.01), '−0.01만원');
  assert.equal(Format.money(0), '0만원');
  assert.equal(Format.money(-0), '0만원');
  assert.equal(Format.money('13756'), '13,756만원');
});

test('real shortfalls and losses below 100원 use won instead of displaying zero', () => {
  const cash = Model.calculate({ available: 13755.999 });
  assert.ok(cash.cashGap > 0);
  assert.equal(Format.money(cash.cashGap), '10원');
  assert.equal(Format.money(0.009), '90원');
  assert.equal(Format.money(-0.009), '−90원');
  const loss = Model.calculate({ bid: 24500, minimum: 24500, loan: 16800, loanRate: 3.1,
    months: 1, sale: 33100, downside: 33100, sellingRate: 0.3, saleTax: 500,
    repairs: 7117.801, available: 50000, targetProfit: 0 });
  assert.ok(loss.profit < 0 && loss.downsideProfit < 0);
  assert.equal(Format.money(loss.profit), '−10원');
  assert.equal(Format.money(loss.downsideProfit), '−10원');
});

test('small target differences remain visible even when profit and target round to the same 만원 text', () => {
  const target = 2000;
  const profit = 1999.99846;
  assert.equal(Format.money(profit), Format.money(target));
  assert.equal(Format.money(target - profit), '15.4원');
  assert.equal(Model.compareAmounts(profit, target), -1);
});

test('unusually small nonzero amounts retain their sign and a compact nonzero representation', () => {
  assert.equal(Format.money(0.00001), '0.1원');
  assert.equal(Format.money(-0.00001), '−0.1원');
  assert.equal(Format.money(1e-12), '1e-8원');
  assert.equal(Format.money(-1e-12), '−1e-8원');
  assert.notEqual(Format.parts(Number.MIN_VALUE).text, '0');
});

test('invalid values stay unavailable rather than being coerced into a zero-money result', () => {
  for (const value of [undefined, null, '', ' ', false, NaN, Infinity, {}, []]) {
    assert.deepEqual(Format.parts(value), { text: '—', unit: '', valid: false });
    assert.equal(Format.money(value), '—');
    assert.equal(Number.isNaN(Format.floorBid(value)), true);
  }
});

test('a copied displayed ceiling meets the target without changing the raw algebraic result', () => {
  const input = { ...Model.defaults(), saleTax: 500, downside: 34000, available: 50000 };
  const original = Model.calculate(input);
  const bid = Format.floorBid(original.maxBid);
  assert.equal(bid, 29260.13);
  assert.equal(Format.money(bid), '29,260.13만원');
  assert.ok(bid <= original.maxBid);
  const copied = Model.calculate({ ...input, bid });
  assert.equal(copied.valid, true);
  assert.ok(Model.compareAmounts(copied.profit, input.targetProfit) >= 0);
  assert.equal(Model.calculate(input).maxBid, original.maxBid);
  const above = Model.calculate({ ...input, bid: bid + 0.01 });
  assert.equal(Model.compareAmounts(above.profit, input.targetProfit), -1);
});

test('ceiling flooring preserves exact decimal steps and never clamps an infeasible negative ceiling to zero', () => {
  for (const value of [0.29, 1.15, 24500.01, 29260.13, -0.29]) {
    assert.equal(Format.floorBid(value), value, String(value));
  }
  assert.equal(Format.floorBid(0.299), 0.29);
  assert.equal(Format.floorBid(-0.001), -0.01);
  assert.equal(Format.floorBid(-1.231), -1.24);
  assert.equal(Format.floorBid(-0), 0);
  assert.equal(Object.is(Format.floorBid(-0), -0), false);
  assert.ok(Number.isFinite(Format.floorBid(Number.MAX_VALUE)));
});

test('copied ceilings meet the requested target across different sale prices and acquisition rates', () => {
  for (const sale of [28000, 33000, 38000]) {
    for (const acquisitionRate of [1.1, 3.5]) {
      for (const targetProfit of [0, 2000]) {
        const input = { ...Model.defaults(), sale, downside: sale, acquisitionRate,
          targetProfit, minimum: 10000, loan: 10000, saleTax: 500, available: 50000 };
        const original = Model.calculate(input);
        const bid = Format.floorBid(original.maxBid);
        const copied = Model.calculate({ ...input, bid });
        assert.equal(copied.valid, true);
        assert.ok(Model.compareAmounts(bid, original.maxBid) <= 0);
        assert.ok(Model.compareAmounts(copied.profit, targetProfit) >= 0,
          JSON.stringify({ sale, acquisitionRate, targetProfit, bid, profit: copied.profit }));
      }
    }
  }
});

test('browser UMD exposes the shared formatter after the model without a module loader', () => {
  const context = {};
  vm.runInNewContext(fs.readFileSync(require.resolve('../_auction/assets/auction-study-model.js'), 'utf8'), context);
  vm.runInNewContext(fs.readFileSync(require.resolve('../_auction/assets/auction-study-format.js'), 'utf8'), context);
  assert.equal(context.AuctionFormat.money(0.001), '10원');
  assert.equal(context.AuctionFormat.floorBid(29260.138476755692), 29260.13);
  assert.equal(Object.isFrozen(context.AuctionFormat), true);
});
