/* Pure inventory rules shared by the refrigerator UI and its regression tests. */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.UMFDomain = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this), function () {
  'use strict';

  function normalizeName(value) {
    return String(value == null ? '' : value).normalize('NFKC').replace(/\s+/g, ' ').trim();
  }

  // Deliberately explicit: a product containing an ingredient's name need not be
  // that ingredient. In particular, soft tofu and egg-containing bread are not
  // interchangeable with the firm tofu and raw eggs required by these recipes.
  var aliasGroups = [
    ['계란', '달걀', '유정란', '무정란', '생계란', '생달걀'],
    ['양파', '깐양파', '적양파', '자색양파'],
    ['버섯', '표고', '표고버섯', '느타리', '느타리버섯', '팽이', '팽이버섯', '양송이', '양송이버섯', '새송이', '새송이버섯'],
    ['토마토', '방울토마토', '대추방울토마토'],
    ['두부', '부침두부', '부침용두부', '찌개두부', '찌개용두부', '단단한두부'],
    ['애호박'],
    ['닭가슴살', '생닭가슴살'],
    ['요거트', '플레인요거트', '플레인요구르트', '그릭요거트'],
    ['치즈', '슬라이스치즈', '체다치즈', '모차렐라치즈', '모짜렐라치즈'],
    ['밥/즉석밥', '밥', '즉석밥', '쌀밥', '흰밥', '백미밥', '잡곡밥', '현미밥', '햇반'],
    ['다진마늘', '간마늘'],
    ['식용유', '콩기름', '대두유', '카놀라유', '해바라기유', '포도씨유', '현미유'],
    ['간장', '진간장', '양조간장'],
    ['소금', '꽃소금', '천일염', '맛소금'],
    ['후추', '후춧가루', '흑후추', '백후추'],
    ['고춧가루', '고추가루'],
    ['된장'], ['고추장'], ['설탕'], ['식초'], ['참기름'], ['케첩', '케찹'],
    ['김'], ['김가루'], ['참치캔'], ['면/라면', '라면', '라면사리'], ['식빵']
  ];
  var aliases = new Map();
  aliasGroups.forEach(function (group) {
    group.forEach(function (name) { aliases.set(normalizeName(name).replace(/\s/g, ''), group[0]); });
  });

  function canonical(name) {
    var normalized = normalizeName(name);
    // Spacing variants are accepted only for names in the explicit dictionary.
    return aliases.get(normalized.replace(/\s/g, '')) || normalized;
  }

  function calendarDay(value) {
    if (typeof value !== 'string') return null;
    var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
    if (!match) return null;
    var year = Number(match[1]), month = Number(match[2]), day = Number(match[3]);
    if (year < 1 || month < 1 || month > 12 || day < 1 || day > 31) return null;
    var date = new Date(0);
    date.setUTCHours(0, 0, 0, 0);
    date.setUTCFullYear(year, month - 1, day);
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
    return date.getTime();
  }

  function daysLeft(expiry, now) {
    var end = calendarDay(expiry);
    if (end === null) return null;
    var date = now === undefined ? new Date() : (now instanceof Date ? now : new Date(now));
    if (!Number.isFinite(date.getTime())) return null;
    // Compare calendar days instead of elapsed local-midnight milliseconds, so a
    // daylight-saving change cannot turn one calendar day into zero or two.
    var start = new Date(0);
    start.setUTCHours(0, 0, 0, 0);
    start.setUTCFullYear(date.getFullYear(), date.getMonth(), date.getDate());
    return Math.round((end - start.getTime()) / 86400000);
  }

  function parseQuantity(value) {
    var text = normalizeName(value).toLowerCase();
    var unknown = { amount: null, unit: null, empty: false, known: false };
    if (!text) return unknown;
    if (text === '소진' || text === '없음') return { amount: 0, unit: null, empty: true, known: true };
    var match = /^((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)\s*(kg|g|ml|l|개|팩|모|봉|공기)?$/.exec(text);
    if (!match) return unknown;
    var amount = Number(match[1].replace(/,/g, ''));
    if (!Number.isFinite(amount) || amount < 0) return unknown;
    return { amount: amount, unit: match[2] || null, empty: amount === 0, known: true };
  }

  function usable(item, now) {
    if (!item || typeof item !== 'object' || !normalizeName(item.name)) return false;
    var left = daysLeft(item.expiry, now);
    return !(left !== null && left < 0) && !parseQuantity(item.quantity).empty;
  }

  function matchIngredient(items, key, now) {
    var name = canonical(key);
    if (!name) return null;
    var best = null, bestLeft = Infinity;
    (Array.isArray(items) ? items : []).forEach(function (item) {
      if (!usable(item, now) || canonical(item.name) !== name) return;
      var left = daysLeft(item.expiry, now);
      var order = left === null ? Infinity : left;
      if (best === null || order < bestLeft) { best = item; bestLeft = order; }
    });
    return best;
  }

  function asArray(value) {
    return Array.isArray(value) ? value : (value instanceof Set ? Array.from(value) : []);
  }

  function requirements(recipe) {
    var out = [], seen = new Set();
    [['f', 'fridge'], ['s', 'season'], ['p', 'pantry']].forEach(function (entry) {
      asArray(recipe && recipe[entry[0]]).forEach(function (value) {
        var name = normalizeName(value), key = canonical(name);
        if (!key || seen.has(key)) return;
        seen.add(key);
        out.push({ name: name, key: key, kind: entry[1] });
      });
    });
    return out;
  }

  function missingReason(items, key, now) {
    var matching = items.filter(function (item) { return item && canonical(item.name) === key; });
    // A current but empty package is more actionable than a second expired one.
    if (matching.some(function (item) {
      var left = daysLeft(item.expiry, now);
      return !(left !== null && left < 0) && parseQuantity(item.quantity).empty;
    })) return 'empty';
    if (matching.some(function (item) {
      var left = daysLeft(item.expiry, now);
      return left !== null && left < 0;
    })) return 'expired';
    return 'missing';
  }

  function evaluate(recipe, state, now) {
    state = state && typeof state === 'object' ? state : {};
    var items = Array.isArray(state.items) ? state.items : [];
    var checked = new Set(asArray(state.season).concat(asArray(state.pantry)).map(canonical).filter(Boolean));
    var missing = [], usedItems = [], used = new Set(), matchedCount = 0;
    var expiryUnknown = false, quantityUnknown = false, urgentCount = 0;
    requirements(recipe).forEach(function (required) {
      var item = matchIngredient(items, required.key, now);
      if (item) {
        matchedCount += 1;
        if (!used.has(item)) {
          used.add(item);
          usedItems.push(item);
          var left = daysLeft(item.expiry, now);
          if (left === null) expiryUnknown = true;
          if (left !== null && left >= 0 && left <= 2) urgentCount += 1;
          if (!parseQuantity(item.quantity).known) quantityUnknown = true;
        }
      } else if (checked.has(required.key)) {
        // Checked stock confirms possession; it does not promise recipe portions.
        matchedCount += 1;
        quantityUnknown = true;
      } else {
        missing.push({ name: required.name, kind: required.kind, reason: missingReason(items, required.key, now) });
      }
    });
    return {
      missing: missing,
      usedItems: usedItems,
      available: missing.length === 0,
      urgentCount: urgentCount,
      matchedCount: matchedCount,
      expiryUnknown: expiryUnknown,
      quantityUnknown: quantityUnknown
    };
  }

  function rankRecipes(recipes, state, now) {
    return (Array.isArray(recipes) ? recipes : []).map(function (recipe, index) {
      return { index: index, value: Object.assign({ recipe: recipe }, evaluate(recipe, state, now)) };
    }).sort(function (a, b) {
      var av = a.value, bv = b.value;
      return Number(bv.available) - Number(av.available) ||
        bv.urgentCount - av.urgentCount ||
        bv.matchedCount - av.matchedCount ||
        av.missing.length - bv.missing.length ||
        normalizeName(av.recipe && av.recipe.name).localeCompare(normalizeName(bv.recipe && bv.recipe.name), 'ko') ||
        a.index - b.index;
    }).map(function (entry) { return entry.value; });
  }

  return Object.freeze({
    normalizeName: normalizeName,
    canonical: canonical,
    daysLeft: daysLeft,
    parseQuantity: parseQuantity,
    usable: usable,
    matchIngredient: matchIngredient,
    evaluate: evaluate,
    rankRecipes: rankRecipes
  });
});
