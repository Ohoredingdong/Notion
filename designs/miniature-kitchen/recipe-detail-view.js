/* Read-only recipe detail. Prices, portions and stock are supplied by the models. */
(() => {
  'use strict';
  const known = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  // Presentation only: keep model quantities and receipt arithmetic untouched.
  function formatQuantityText(value) {
    const text = String(value ?? ''), parsed = window.KitchenJourneyModel?.parseQuantity(text);
    if(!parsed || !['개','알','모','팩','병','봉','조각','장','공기','큰술','작은술','인분','캔'].includes(parsed.unit))return text;
    const whole = Math.floor(parsed.amount), part = parsed.amount - whole;
    for(const denominator of [2,3,4,6,8]) {
      const numerator = Math.round(part * denominator);
      if(numerator > 0 && numerator < denominator && Math.abs(part - numerator / denominator) <= 1e-6)
        return (parsed.prefix || '') + (whole ? whole+' ' : '') + numerator+'/'+denominator + parsed.unit;
    }
    return text;
  }
  const textOf = source => {
    if(typeof source === 'string')return source;
    const nested = source?.source && typeof source.source === 'object' ? source.source : null;
    const label = source?.label || nested?.label || source?.product || source?.name ||
      (typeof source?.source === 'string' ? source.source : '');
    return [label,source?.day || source?.date || nested?.day].filter(Boolean).join(' · ');
  };

  function render(ctx) {
    const {recipe:r, portions, availability:a, values:v, facts, notes = {},
      esc, fmt, won, dish, button, foodArt, availabilityTable} = ctx;
    const rows = a?.rows || [], supplied = ctx.cost || {};
    const cost = known(v?.cost) ? {...supplied, scope:'recipe', kind:'entered', total:v.cost} : supplied;
    const kind = ['entered','purchase','reference','mixed','partial'].includes(cost.kind) ? cost.kind : 'unknown';
    const mainScope = cost.scope === 'main', reference = ['reference','mixed'].includes(kind);
    const scopeLabel = mainScope ? '주재료 참고비용' : '사용 재료비';
    const full = !['partial','unknown'].includes(kind) && known(cost.total);
    const partial = kind === 'partial' && known(cost.knownSubtotal);
    const displayCost = value => {
      if(kind === 'entered')return won(value);
      if(kind === 'partial' || kind === 'purchase')return '약 '+won(Math.round(value));
      if(mainScope || reference){const rounded=Math.round(value/100)*100;return value>0&&rounded===0?'100원 미만':'약 '+won(rounded);}
      return '약 '+won(Math.round(value));
    };
    const amount = full ? displayCost(cost.total) : partial ? displayCost(cost.knownSubtotal) : '금액 확인 필요';
    const missing = Array.isArray(cost.missing) ? cost.missing : [];
    const sources = Array.isArray(cost.sources) ? cost.sources.map(textOf).filter(Boolean) : [];
    const costRows = Array.isArray(cost.rows) ? cost.rows : [];
    const kindLabel = {entered:'직접 입력', purchase:'구매 기록 기반', reference:'참고 가격 기준', mixed:'구매 기록·참고 가격', partial:'일부 재료만 계산', unknown:'가격 정보 없음'}[kind];
    const basis = cost.basisNote || {
      entered:'입력한 1회분 금액을 선택한 분량에 맞춰 계산했어요.',
      purchase:'구매 기록의 단가와 레시피 사용량으로 계산한 값이에요.',
      reference:'표시한 기준일의 참고 가격과 레시피 사용량으로 계산했어요. 실제 구매 금액은 달라질 수 있어요.',
      mixed:'구매 기록이 있는 재료와 참고 가격을 함께 사용해 계산한 금액이에요.',
      partial:'확인한 재료만 합산한 금액이며, 전체 재료비가 아니에요.',
      unknown:'재료 가격이나 1회분 재료비를 입력하면 금액을 확인할 수 있어요.'
    }[kind];
    const roundingNote = (mainScope || reference) && !['entered','purchase','partial','unknown'].includes(kind) && !String(basis).includes('100원') ? '참고 표시 금액은 100원 단위로 반올림했어요.' : '';
    const costValue = partial ? amount+' +' : amount;
    const missingNames = missing.map(row => typeof row === 'string' ? row : row?.name).filter(Boolean);
    const excluded = Array.isArray(cost.excluded) ? cost.excluded.map(row => typeof row === 'string' ? row : row?.name).filter(Boolean) : [];
    const hasAssumptions = costRows.some(row => row.assumption) || (Array.isArray(cost.assumptions) && cost.assumptions.length>0);
    const referenceNote = cost.referenceDay ? '참고 기준일 '+String(cost.referenceDay).replaceAll('-','.')+' · 실제 구매가 아님' : reference ? '참고 가격으로 계산 · 실제 구매가 아님' : '';
    const compactPriceNote = [partial?(missing.length?missing.length+'종 미확인':'일부만 확인'):mainScope?'양념 제외':'',partial?'전체 아님':'',cost.referenceDay?String(cost.referenceDay).slice(5).replace('-','.')+' 가격':'',hasAssumptions?'가정 포함':'',(reference || mainScope&&cost.referenceDay)?'구매가 아님':''].filter(Boolean).join('·');
    const assumptionText = value => (Array.isArray(value) ? value.filter(Boolean).join(' · ') : typeof value === 'string' ? value : '').replace(/^(?:계산 가정\s*[:：]\s*)+/, '');
    const sourceText = facts?.source ? '입력 출처: '+facts.source : '';
    const hasNutrition = ['kcal','carb','protein','fat'].some(key => known(v?.[key]));
    const macros = ['carb','protein','fat'].map(key =>
      `<span>${{carb:'탄수화물',protein:'단백질',fat:'지방'}[key]} <b>${known(v?.[key])?fmt(v[key])+'g':'미입력'}</b></span>`).join('');
    const priceDetail = costRows.length || sources.length || sourceText || excluded.length ?
      `<details class="recipe-cost-basis"><summary>재료비 계산 근거</summary><p>${esc(basis)}</p>${roundingNote?`<p class="recipe-reference-rounding">${esc(roundingNote)}</p>`:''}<p>이 금액은 실제 지출에 더해지지 않아요.</p>${costRows.length?`<dl class="recipe-cost-breakdown">${costRows.map(row => `<div><dt>${esc(row.name || '재료')} ${(row.usedQuantity || row.required)?`<small>사용량 ${esc(formatQuantityText(row.usedQuantity || row.required))}</small>`:''}${row.assumption?`<small class="recipe-price-assumption">계산 가정: ${esc(assumptionText(row.assumption))}</small>`:''}</dt><dd>${known(row.cost)?won(row.cost):'금액 확인 필요'}</dd></div>`).join('')}</dl>`:''}${excluded.length?`<p>계산 제외: ${esc(excluded.join(' · '))}</p>`:''}${sources.map(source => `<p class="recipe-price-source">${esc(source)}</p>`).join('')}${sourceText?`<p class="recipe-price-source">${esc(sourceText)}</p>`:''}</details>` : '';
    const missingLabel = partial ? `${missing.length?missing.length+'종 재료 가격 미확인 · ':''}전체 금액이 아니에요` :
      full ? mainScope?'양념 등 제외 · 한 끼 전체 비용 아님':'보유 재료를 포함한 사용량 기준' : '모르는 금액은 계산하지 않아요';

    return `<div class="recipe-detail-layout" data-screen-id="B2">
      <div class="recipe-detail-scroll">
        <div class="recipe-detail-sidebar">
        <section class="recipe-detail-overview" aria-label="요리와 비용 요약">
          <div class="recipe-hero">${dish(r).replaceAll('xMidYMid slice','xMidYMid meet')}<span class="recipe-time">${esc(r.time)}</span><button type="button" class="recipe-favorite" data-wf="favoriteRecipe" data-arg="${esc(r.id)}" aria-label="${notes.favorite?'찜 해제':'요리 찜하기'}" aria-pressed="${!!notes.favorite}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20S3 14.2 3 8.3A4.6 4.6 0 0 1 12 7a4.6 4.6 0 0 1 9 1.3C21 14.2 12 20 12 20Z"/></svg></button></div>
          <div class="recipe-detail-heading"><h3 class="recipe-detail-name">${esc(r.name)}</h3><p class="recipe-detail-description">${esc(r.desc || '')}</p></div>
          <div class="recipe-cost-summary" data-cost-scope="${mainScope?'main':'recipe'}" data-cost-kind="${kind}" data-cost-total="${full?cost.total:''}" data-cost-subtotal="${partial?cost.knownSubtotal:''}">
            <div class="recipe-cost-value"><small>${partial?'확인된 재료 금액':scopeLabel} <span>${esc(kindLabel)}</span></small><strong>${esc(costValue)}</strong></div>
            <button type="button" class="small-action recipe-cost-edit" data-wf="recipeCost" data-arg="${esc(r.id)}" aria-label="요리 1회분 재료비 입력 또는 수정" title="요리 1회분 재료비 입력 또는 수정"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 5 4 4M4 20l4-1L20 7a2.8 2.8 0 0 0-4-4L4 15Z"/></svg><span>${full||partial?'수정':'입력'}</span></button>
            <p class="recipe-cost-status">${esc(missingLabel)}</p>
          </div>
          <div class="recipe-energy-macros${hasNutrition?'':' is-unknown'}"><strong>${known(v?.kcal)?fmt(v.kcal)+' kcal':hasNutrition?'영양 일부 입력':'영양 정보 미입력'}</strong><div class="recipe-macro-strip" ${hasNutrition?'':'hidden'}>${hasNutrition?macros:''}</div></div>
          ${referenceNote || compactPriceNote?`<p class="recipe-reference-note" title="${esc([referenceNote,basis].filter(Boolean).join(' · '))}"><span class="recipe-price-note-compact">${esc(compactPriceNote || referenceNote)}</span><span class="recipe-price-note-full">${esc(referenceNote || compactPriceNote)}</span></p>`:''}
        </section>
        <div class="recipe-cost-context">${missingNames.length?`<p class="recipe-cost-missing">가격 미확인: ${esc(missingNames.join(' · '))}</p>`:''}${priceDetail}</div>
        </div>
        <div class="recipe-detail-main">
          <nav data-recipe-tabs role="tablist" aria-label="레시피 상세 보기">${[['ingredients','재료'],['steps','조리 순서'],['nutrition','영양·내 팁']].map(([tab,label]) => `<button type="button" role="tab" id="recipe-detail-tab-${tab}" data-recipe-tab="${tab}" data-wf="recipeDetailTab" data-arg="${tab}" aria-controls="recipe-detail-panel-${tab}" aria-selected="${tab==='ingredients'}">${label}</button>`).join('')}</nav>
          <div class="recipe-section-heading recipe-detail-toolbar"><h3>재료 <small>${rows.length}종</small></h3><label class="workflow-label recipe-portions"><span>분량</span><input id="recipePortions" type="number" min="0.01" max="100" step="any" value="${esc(portions)}" aria-label="레시피 분량"><span>회분</span></label><button type="button" class="small-action recipe-toolbar-shopping" data-wf="missingToShopping" data-arg="${esc(r.id)}" aria-label="부족 재료 장보기"><span class="recipe-shop-wide">부족 재료 </span>장보기</button></div>
          <section class="recipe-ingredients-section" id="recipe-detail-panel-ingredients" data-recipe-panel="ingredients" role="tabpanel" aria-labelledby="recipe-detail-tab-ingredients"><div class="recipe-ingredient-list">${rows.map(row => `<div><span class="recipe-ingredient-art" aria-hidden="true">${foodArt?foodArt(row.name):''}</span><span class="recipe-ingredient-copy"><strong>${esc(row.name)}</strong><span class="recipe-ingredient-amounts"><span>필요 ${esc(formatQuantityText(row.required))}</span><small>${row.available===null?'보유량 확인 필요':'보유 '+esc(formatQuantityText(row.availableQuantity || '0'+(row.unit || '')))}</small></span>${missingNames.includes(row.name)?'<small class="recipe-ingredient-price-state">가격 미확인</small>':''}</span><span class="ingredient-stock-status" data-status="${row.status}" title="${esc(row.reason || '')}">${row.status==='enough'?'충분':row.status==='shortage'?'부족':'확인'}</span></div>`).join('')}</div>${r.water?`<p class="recipe-water">${esc(r.water)}</p>`:''}</section>
          <section class="recipe-instructions" id="recipe-detail-panel-steps" data-recipe-panel="steps" role="tabpanel" aria-labelledby="recipe-detail-tab-steps" hidden><h3>조리 순서 <small>${esc(r.time)}</small></h3><ol class="recipe-steps">${r.steps.map(step => `<li>${esc(step)}</li>`).join('')}</ol></section>
          <section class="recipe-additional-details" id="recipe-detail-panel-nutrition" data-recipe-panel="nutrition" role="tabpanel" aria-labelledby="recipe-detail-tab-nutrition" hidden><h3>영양 정보 <small>${fmt(portions)}회분 · 입력값 기준</small></h3>${hasNutrition?`<div class="recipe-nutrition-facts"><div><span>열량</span><strong>${known(v?.kcal)?fmt(v.kcal)+' kcal':'미입력'}</strong></div>${['carb','protein','fat'].map(key => `<div><span>${{carb:'탄수화물',protein:'단백질',fat:'지방'}[key]}</span><strong>${known(v?.[key])?fmt(v[key])+'g':'미입력'}</strong></div>`).join('')}</div>`:'<p class="recipe-nutrition-empty">아직 입력한 영양 정보가 없어요.</p>'}<div class="recipe-source-action">${button('영양 정보 입력·수정','recipeFacts',r.id)}</div><p class="recipe-information-hint">영양은 직접 입력한 값으로 표시해요.${sourceText?' '+esc(sourceText):''}</p><details class="recipe-stock-details"><summary>재고 상세 확인</summary>${availabilityTable(a)}</details><form data-wf-form="recipeNotes" data-id="${esc(r.id)}" class="notes-box"><label class="workflow-label">나의 팁<textarea name="note" rows="2" maxlength="3000" placeholder="다음 요리 때 기억할 내용을 적어보세요">${esc(notes.note || '')}</textarea></label><label class="workflow-label">대체 재료<textarea name="variation" rows="2" maxlength="1000">${esc(notes.variation || '')}</textarea></label><button type="submit" class="small-action">내 팁 저장</button></form></section>
        </div>
      </div>
      <div class="workflow-footer recipe-detail-actions">${button('식단에 넣기','planRecipe',r.id)}${button('먹었어요','logMeal',r.id,true)}</div>
    </div>`;
  }
  window.KitchenRecipeDetail = Object.freeze({render, formatQuantityText});
})();
