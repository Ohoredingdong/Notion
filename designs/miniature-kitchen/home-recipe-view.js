/* Recipe and plan pages share the home frame; paging is ephemeral UI state. */
(() => {
  'use strict';
  let recipeId = null, recipeIds = [], recipeFilterKey = '';
  let mealSlot = 'dinner', viewedDay = null, knownPlans = null, pendingPlan = null, planCount = 0;
  const planPages = new Map();
  const clamp = (value, end) => Math.max(0, Math.min(Math.max(0, end - 1), value));
  const nativePhoto = markup => markup.replaceAll('preserveAspectRatio="xMidYMid slice"', 'preserveAspectRatio="xMidYMid meet"');
  const funnel = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 5h18l-7 8v6l-4 2v-8Z"/></svg>';

  function renderRecommendation(ctx) {
    const {ranked, near, filters, esc, fmt, money, recommendationView} = ctx;
    const filterKey = JSON.stringify(filters);
    recipeIds = ranked.map(candidate => candidate.recipe.id);
    if (filterKey !== recipeFilterKey || !recipeIds.includes(recipeId)) recipeId = recipeIds[0] || null;
    recipeFilterKey = filterKey;
    const index = Math.max(0, recipeIds.indexOf(recipeId));
    const candidate = ranked[index];
    const conditions = [filters.time ? filters.time + '분 이내' : '', filters.budget ? money(Number(filters.budget)) + ' 이내' : '', filters.exclude ? '피할 재료 반영' : ''].filter(Boolean);
    let priority;
    if (filters.ingredient) {
      priority = `<span class="recipe-hub-priority">활용할 재료: <strong>${esc(filters.ingredient)}</strong></span><button type="button" class="recipe-hub-reset" data-home-filter-reset aria-label="레시피 조건 해제">×</button>`;
    } else if (conditions.length) {
      priority = `<span class="recipe-hub-priority">${esc(conditions.join(' · '))}</span><button type="button" class="recipe-hub-reset" data-home-filter-reset aria-label="레시피 조건 해제">×</button>`;
    } else if (near.length) {
      priority = `<button type="button" class="recipe-hub-priority" data-recipe-urgent="${esc(near[0].name)}" aria-label="${esc(near[0].name)} 활용 레시피 보기"><span class="recipe-hub-priority-art" aria-hidden="true">${window.MiniKitchen.getArt(near[0])}</span><span>먼저 먹을 재료: <strong>${near.slice(0, 2).map(item => esc(item.name)).join(' · ')}</strong></span></button>`;
    } else {
      priority = '<span class="recipe-hub-priority">냉장고 속 재료로 만드는 한 끼</span>';
    }
    const content = candidate
      ? `<article class="home-featured-recipe recipe-hub-card" data-home-recipe="${esc(candidate.recipe.id)}">${nativePhoto(recommendationView(candidate))}</article>`
      : '<section class="recipe-hub-empty"><p>조건에 맞는 레시피가 없어요.</p><button type="button" class="small-action" data-home-filter-reset>조건 초기화</button></section>';
    const catalogLabel = Object.values(filters).some(Boolean) ? '요리 목록 보기' : '전체 요리 보기';
    return `<div class="recipe-hub-toolbar">${priority}<button type="button" class="recipe-hub-filter" data-wf="recipeFilters" aria-label="레시피 조건 조정">${funnel}</button></div><div class="recipe-hub-deck" aria-live="polite">${content}</div><div class="recipe-hub-pager"><button type="button" data-recipe-hub-nav="-1" aria-label="이전 추천 요리" ${recipeIds.length < 2 ? 'disabled' : ''}>‹</button><button type="button" class="recipe-hub-catalog" data-wf="recipeCatalog"><span>${recipeIds.length ? fmt(index + 1) : '0'} / ${fmt(recipeIds.length)}</span><strong>${catalogLabel} <span aria-hidden="true">›</span></strong></button><button type="button" data-recipe-hub-nav="1" aria-label="다음 추천 요리" ${recipeIds.length < 2 ? 'disabled' : ''}>›</button></div>`;
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
    const previous = event.target.closest('[data-recipe-hub-nav]');
    if (previous && !previous.disabled && recipeIds.length) {
      const step = Number(previous.dataset.recipeHubNav), index = Math.max(0, recipeIds.indexOf(recipeId));
      recipeId = recipeIds[(index + step + recipeIds.length) % recipeIds.length];
      refresh(`[data-recipe-hub-nav="${step}"]`);
      return;
    }
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
