/* Amount presentation only. Model inputs and results stay in 만원 unchanged.
 * Load after auction-study-model.js. Bid ceilings use a conservative 100원 step.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./auction-study-model.js'));
  else root.AuctionFormat = factory(root.AuctionModel);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (Model) {
  'use strict';

  if (!Model || typeof Model.compareAmounts !== 'function') {
    throw new Error('AuctionFormat requires AuctionModel to load first.');
  }

  const manwon = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 });
  const won = new Intl.NumberFormat('ko-KR', { maximumSignificantDigits: 6 });

  function number(value) {
    const accepted = typeof value === 'number' || (typeof value === 'string' && value.trim() !== '');
    const parsed = accepted ? Number(value) : NaN;
    return Number.isFinite(parsed) ? parsed : NaN;
  }

  function parts(value) {
    const parsed = number(value);
    if (!Number.isFinite(parsed)) return { text: '—', unit: '', valid: false };
    const absolute = Math.abs(parsed);
    const sign = parsed < 0 ? '−' : '';
    if (absolute > 0 && absolute < 0.01) {
      const inWon = absolute * 10000;
      // Keep even unusually small, explicitly entered amounts nonzero without
      // producing a long string of leading zeroes in a narrow widget.
      const text = inWon < 1e-6
        ? inWon.toExponential(5).replace(/\.?0+(?=e)/, '')
        : won.format(inWon);
      return { text: sign + text, unit: '원', valid: true };
    }
    return { text: sign + manwon.format(absolute), unit: '만원', valid: true };
  }

  function money(value) {
    const result = parts(value);
    return result.text + result.unit;
  }

  function floorBid(value) {
    const parsed = number(value);
    if (!Number.isFinite(parsed)) return NaN;
    if (parsed === 0) return 0;
    const scaled = parsed * 100;
    // At this magnitude a Number already has no sub-100원 precision to discard.
    if (!Number.isFinite(scaled)) return parsed;
    const nearest = Math.round(scaled) / 100;
    // Avoid losing 100원 merely because an exact decimal such as 0.29 scales
    // to 28.999999999999996. Use the model's existing arithmetic tolerance only.
    const result = Model.compareAmounts(nearest, parsed) <= 0 ? nearest : Math.floor(scaled) / 100;
    return result === 0 ? 0 : result;
  }

  return Object.freeze({ parts, money, floorBid });
});
