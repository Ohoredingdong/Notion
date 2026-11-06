/* Manual auction scenarios. Amounts are in 만원; rates are percentages.
 * Tax and loan inputs are user estimates, not statutory or lender eligibility rules.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.AuctionModel = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const initial = Object.freeze({
    bid: 28000, minimum: 24500, depositRate: 10, loan: 16800,
    loanRate: 4.5, months: 6, acquisitionRate: 1.1,
    legal: 120, repairs: 800, eviction: 300, arrears: 150,
    assumed: 0, reserve: 500, sale: 34000, downside: 31000,
    sellingRate: 0.5, saleTax: 0, targetProfit: 2000, available: 15000
  });
  const labels = {
    bid: '예상 낙찰가', minimum: '최저 매각가격', depositRate: '입찰보증금 비율',
    loan: '예상 대출금', loanRate: '대출 연이율', months: '보유 기간',
    acquisitionRate: '취득 관련 세율', legal: '등기·법무 비용', repairs: '수리비',
    eviction: '명도 비용', arrears: '체납 관리비', assumed: '인수 금액',
    reserve: '현금 예비비', sale: '예상 매도가', downside: '보수적 매도가',
    sellingRate: '매도 비용 비율', saleTax: '매도 세금 예상액',
    targetProfit: '목표 이익', available: '가용 현금'
  };
  const rateFields = new Set(['depositRate', 'loanRate', 'acquisitionRate', 'sellingRate']);

  function defaults() { return { ...initial }; }

  // Compare calculated amounts without mistaking a few floating-point rounding
  // bits for a real shortfall or loss. This is not currency rounding: the
  // tolerance is scaled to the operands and capped at 0.0000001만원 (0.001원),
  // well below even a 0.01만원 difference at the displayed precision.
  // Invalid operands are deliberately not equal to anything, including zero.
  function compareAmounts(left, right) {
    if (!Number.isFinite(left) || !Number.isFinite(right)) return NaN;
    const tolerance = Math.min(1e-7, Number.EPSILON * 16 * Math.max(1, Math.abs(left), Math.abs(right)));
    return Math.abs(left - right) <= tolerance ? 0 : left < right ? -1 : 1;
  }

  function amountDifference(left, right) {
    return compareAmounts(left, right) === 0 ? 0 : left - right;
  }

  function calculate(values) {
    const errors = [];
    const input = {};
    if (values === undefined) values = {};
    if (!values || typeof values !== 'object' || Array.isArray(values)) {
      return { valid: false, errors: ['계산할 입력값을 확인해 주세요.'], input };
    }
    for (const key of Object.keys(initial)) {
      const raw = Object.prototype.hasOwnProperty.call(values, key) ? values[key] : initial[key];
      const accepted = typeof raw === 'number' || (typeof raw === 'string' && raw.trim() !== '');
      const value = accepted ? Number(raw) : NaN;
      input[key] = Number.isFinite(value) ? value : null;
      if (!Number.isFinite(value) || value < 0) errors.push(labels[key] + '에 0 이상의 숫자를 입력해 주세요.');
      else if (rateFields.has(key) && value > 100) errors.push(labels[key] + '은 100% 이하여야 합니다.');
    }
    if (input.bid !== null && input.minimum !== null && compareAmounts(input.bid, input.minimum) < 0) {
      errors.push('예상 낙찰가는 최저 매각가격 이상이어야 합니다.');
    }
    if (input.loan !== null && input.bid !== null && compareAmounts(input.loan, input.bid) > 0) {
      errors.push('예상 대출금은 예상 낙찰가를 넘을 수 없습니다.');
    }
    if (errors.length) return { valid: false, errors, input };

    const deposit = input.minimum * input.depositRate / 100;
    const tax = input.bid * input.acquisitionRate / 100;
    const interest = input.loan * input.loanRate / 100 * input.months / 12;
    const fixedCosts = input.legal + input.repairs + input.eviction + input.arrears + input.assumed + interest;
    const costs = tax + fixedCosts;
    const totalCost = input.bid + costs;
    const equity = amountDifference(totalCost, input.loan);
    const cashNeeded = equity + input.reserve;
    // The deposit is part of the purchase price, not an additional expense.
    // Floor the later-payment estimate at zero: excess financing is never a negative cash payment.
    // Deposit cash must still be available before any assumed loan disbursement.
    const balanceSettlement = amountDifference(input.bid - deposit + tax + input.legal, input.loan);
    const balanceCash = Math.max(0, balanceSettlement);
    // A loan larger than the remaining settlement creates a modelled cash credit,
    // not a negative payment. Keep it visible so the payment ledger reconciles.
    // Actual loan disbursement/refund timing must be confirmed separately.
    const balanceCredit = Math.max(0, -balanceSettlement);
    const profit = amountDifference(input.sale * (1 - input.sellingRate / 100) - input.saleTax, totalCost);
    const downsideProfit = amountDifference(input.downside * (1 - input.sellingRate / 100) - input.saleTax, totalCost);
    const roi = equity > 0 ? profit / equity * 100 : null;
    // Loan principal and interest are held fixed while solving for the bid.
    // A negative ceiling means even a zero bid cannot achieve the target under these assumptions.
    const maxBid = (input.sale * (1 - input.sellingRate / 100) - input.saleTax - fixedCosts - input.targetProfit)
      / (1 + input.acquisitionRate / 100);
    const cashGap = Math.max(0, amountDifference(cashNeeded, input.available));
    // Net cash can be below the deposit if financing is high. The deposit is due
    // before that financing, so a zero net shortfall does not imply readiness.
    const depositGap = Math.max(0, amountDifference(deposit, input.available));
    const result = { deposit, tax, interest, costs, totalCost, cashNeeded, balanceCash, balanceCredit, profit, downsideProfit, roi, maxBid, cashGap, depositGap };
    if (Object.values(result).some(value => value !== null && !Number.isFinite(value))) {
      return { valid: false, errors: ['입력값이 계산 가능한 범위를 초과했습니다. 금액과 기간을 확인해 주세요.'], input };
    }
    return { valid: true, errors, input, ...result };
  }

  return Object.freeze({ defaults, calculate, compareAmounts });
});
