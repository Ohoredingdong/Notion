/* Recipe and plan pages share the home frame; paging is ephemeral UI state. */
(() => {
  'use strict';
  let mealSlot = 'dinner', viewedDay = null, knownPlans = null, pendingPlan = null, planCount = 0;
  const planPages = new Map();
  const clamp = (value, end) => Math.max(0, Math.min(Math.max(0, end - 1), value));
  const nativePhoto = markup => markup.replaceAll('preserveAspectRatio="xMidYMid slice"', 'preserveAspectRatio="xMidYMid meet"');
  function renderRecommendation(ctx) {
    const {ranked, filters, esc, fmt, money, dish} = ctx;
    const candidates = ranked.slice(0, 8);
    const conditions = [filters.ingredient ? filters.ingredient+' 활용' : '', filters.time ? filters.time+'분 이내' : '', filters.budget ? money(Number(filters.budget))+' 이내' : '', filters.exclude ? '피할 재료 반영' : ''].filter(Boolean);
    const known = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
    const content = candidates.length
      ? candidates.map(({recipe,nutrients,cost,availability}) => {
        const kcalKnown=known(nutrients?.kcal),costKnown=known(cost),kcal=kcalKnown?fmt(nutrients.kcal)+' kcal':'열량 —',price=costKnown?fmt(cost)+'원':'원가 —';
        const rows=availability?.rows||[],enough=rows.filter(row=>row.status==='enough'&&!row.quantityUnknown&&!row.unknownExpiryIds?.length).length;
        const stock=rows.length?'충족 '+enough+'/'+rows.length:'재료 확인',status=availability?.status||'check';
        const detail=[recipe.name,recipe.time,kcalKnown?kcal:'열량 미입력',costKnown?'입력 원가 '+price:'원가 미입력',rows.length?'수량과 기한이 확인된 재료 '+enough+'종 / '+rows.length+'종':'재료 확인 필요','레시피 자세히'].join(' · ');
        return `<button type="button" class="recipe-grid-card recipe-comparison-card" data-home-recipe="${esc(recipe.id)}" data-wf="recipe" data-arg="${esc(recipe.id)}" aria-label="${esc(detail)}"><span class="recipe-grid-photo" aria-hidden="true">${nativePhoto(dish(recipe))}</span><span class="recipe-grid-content"><span class="recipe-grid-copy"><strong>${esc(recipe.name)}</strong></span><span class="recipe-grid-meta recipe-grid-nutrition"><small data-recipe-time>${esc(recipe.time)}</small><span data-recipe-kcal data-value="${kcalKnown?nutrients.kcal:''}" title="${kcalKnown?'입력한 레시피 1회분 열량':'열량 미입력'}">${esc(kcal)}</span></span><span class="recipe-grid-meta recipe-grid-preparation"><span data-recipe-cost data-value="${costKnown?cost:''}" title="${costKnown?'입력한 레시피 1회분 재료 원가':'원가 미입력'}">${esc(price)}</span><span data-recipe-stock data-stock-status="${esc(status)}" data-ready-count="${enough}" data-required-count="${rows.length}" title="수량과 기한을 함께 확인한 재료">${esc(stock)}</span></span></span></button>`;
      }).join('')
      : '<section class="recipe-hub-empty"><p>조건에 맞는 레시피가 없어요.</p><button type="button" class="small-action" data-home-filter-reset>조건 초기화</button></section>';
    const filterIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="var(--filter-control-fill,#fffaf5)"/><circle cx="15" cy="17" r="3" fill="var(--filter-control-fill,#fffaf5)"/></svg>';
    const filterStrip=`<div class="refresh-recipe-filters" role="group" aria-label="레시피 비교 조건"><button type="button" data-wf="recipeFilters" data-filter-active="${conditions.length>0}" aria-label="${esc(conditions.length?'요리 조건 '+conditions.length+'개 적용 · 조건 설정':'요리 조건 설정')}">${filterIcon}<span>조건 설정</span></button><div class="recipe-filter-summary" data-filter-summary aria-live="polite">${conditions.length?conditions.map(text=>`<span class="recipe-condition-chip" title="${esc(text)}">${esc(text)}</span>`).join(''):'<span class="recipe-filter-hint">시간 · 예산 · 재료로 골라보세요</span>'}</div>${conditions.length&&candidates.length?'<button type="button" class="recipe-filter-reset" data-home-filter-reset>초기화</button>':''}</div>`;
    return `<p class="recipe-comparison-context sr-only">${esc(conditions.join(' · ')||'냉장고 재료 기준 추천')} · 열량과 원가는 입력한 1회분 기준이며, —는 미입력입니다. 충족 수는 기록된 수량과 기한을 함께 확인한 재료입니다.</p>${filterStrip}<div class="recipe-hub-grid recipe-comparison-grid${conditions.length?' is-filtered':''}" aria-label="${esc('추천 레시피 비교'+(conditions.length?' · '+conditions.join(' · '):''))}" aria-live="polite">${content}</div>`;
  }

  function renderPlans(ctx) {
    const {plans, slots, flow, play, catalog, planDay, dateMarkup, esc, fmt, dish, action} = ctx;
    const snapshot = new Map(flow.plans.map(plan => [plan.id, JSON.stringify([plan.day, plan.slot, plan.recipeId, plan.portions])]));
    if (knownPlans) {
      const changed = flow.plans.filter(plan => knownPlans.get(plan.id) !== snapshot.get(plan.id));
      if (changed.length) pendingPlan = changed[changed.length - 1];
    }
    knownPlans = snapshot;
    if (viewedDay !== planDay) {
      viewedDay = planDay;
      if (!plans.some(plan => plan.slot === mealSlot)) mealSlot = Object.keys(slots).find(slot => plans.some(plan => plan.slot === slot)) || mealSlot;
    }
    if (pendingPlan?.day === planDay && plans.some(plan => plan.id === pendingPlan.id)) {
      mealSlot = pendingPlan.slot;
      planPages.set(planDay + ':' + mealSlot, plans.filter(plan => plan.slot === mealSlot).findIndex(plan => plan.id === pendingPlan.id));
      pendingPlan = null;
    }
    const rows = plans.filter(plan => plan.slot === mealSlot);
    planCount = rows.length;
    const key = planDay + ':' + mealSlot, page = clamp(planPages.get(key) || 0, rows.length);
    planPages.set(key, page);
    const plan = rows[page], recipe = plan && catalog.find(row => row.id === plan.recipeId);
    let content;
    if (plan && recipe) {
      const transaction = flow.transactions.find(row => row.planId === plan.id && row.active && play.meals.some(meal => meal.id === row.mealId));
      const kcal = flow.recipeFacts?.[recipe.id]?.kcal;
      content = `<article class="recipe-plan-card home-plan-row" data-plan-id="${esc(plan.id)}" data-home-meal-slot="${mealSlot}"><button type="button" class="recipe-plan-photo" data-wf="recipe" data-arg="${esc(recipe.id)}" aria-label="${esc(recipe.name)} 요리 상세">${nativePhoto(dish(recipe))}</button><div class="recipe-plan-copy"><strong>${esc(recipe.name)}</strong><span>${kcal == null ? '열량 미입력' : fmt(kcal * plan.portions) + ' kcal'} · ${fmt(plan.portions)}회분</span><small>${transaction ? '기록 완료' : '아직 먹지 않음'} · ${fmt(page + 1)} / ${fmt(rows.length)}</small><div class="recipe-plan-actions">${transaction ? action('기록 보기', 'planMeal', transaction.mealId, 'home-primary') : action('먹었어요', 'logPlan', plan.id, 'home-primary')}${transaction ? '' : action('계획 수정', 'editPlan', plan.id, 'recipe-plan-edit')}</div></div></article>`;
    } else {
      content = `<section class="recipe-plan-empty" data-home-meal-slot="${mealSlot}"><strong>${esc(slots[mealSlot])} 식단</strong><p>저장한 식단이 없어요.</p><span>요리를 골라 이 끼니에 계획해 보세요.</span></section>`;
    }
    return `${dateMarkup}<div class="recipe-meal-tabs" role="tablist" aria-label="계획한 끼니">${Object.entries(slots).map(([slot, label]) => `<button type="button" role="tab" data-recipe-meal-slot="${slot}" aria-selected="${slot === mealSlot}" tabindex="${slot === mealSlot ? 0 : -1}">${esc(label)} <small>${fmt(plans.filter(plan => plan.slot === slot).length)}</small></button>`).join('')}</div><div class="recipe-plan-deck" aria-live="polite">${content}</div><div class="recipe-plan-tools"><button type="button" data-recipe-plan-page="-1" aria-label="이전 계획" ${rows.length < 2 ? 'disabled' : ''}>‹</button>${action('요리 선택', 'browseRecipes', '', 'recipe-plan-browse')}${action('부족 재료 장보기', 'planShopping', planDay, 'recipe-plan-shopping')}<button type="button" data-recipe-plan-page="1" aria-label="다음 계획" ${rows.length < 2 ? 'disabled' : ''}>›</button></div>`;
  }

  function refresh(selector) {
    window.KitchenHome.update();
    if (selector) document.querySelector(selector)?.focus({preventScroll: true});
  }
  document.addEventListener('click', event => {
    const urgent = event.target.closest('[data-recipe-urgent]');
    if (urgent) return window.KitchenHome.showRecipes({ingredient: urgent.dataset.recipeUrgent});
    const slot = event.target.closest('[data-recipe-meal-slot]');
    if (slot) {
      mealSlot = slot.dataset.recipeMealSlot;
      refresh(`[data-recipe-meal-slot="${mealSlot}"]`);
      return;
    }
    const page = event.target.closest('[data-recipe-plan-page]');
    if (page && !page.disabled) {
      const key = viewedDay + ':' + mealSlot;
      const step = Number(page.dataset.recipePlanPage);
      planPages.set(key, planCount ? ((planPages.get(key) || 0) + step + planCount) % planCount : 0);
      refresh(`[data-recipe-plan-page="${step}"]`);
    }
  });
  document.addEventListener('keydown', event => {
    const target = event.target.closest('[data-recipe-meal-slot]');
    if (!target || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    const slots = ['breakfast', 'lunch', 'dinner'], index = slots.indexOf(mealSlot);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? slots.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + slots.length) % slots.length;
    event.preventDefault();event.stopImmediatePropagation();mealSlot = slots[next];
    refresh(`[data-recipe-meal-slot="${mealSlot}"]`);
  });
  window.KitchenRecipeHub = Object.freeze({renderRecommendation, renderPlans});
})();
