/* Read-only nutrition guidance. All quantities and comparisons come from supplied reports. */
(() => {
  'use strict';
  const META = {
    kcal:['열량','kcal'],carb:['탄수화물','g'],protein:['단백질','g'],fat:['지방','g'],
    fiber:['식이섬유','g'],water:['수분','mL'],calcium:['칼슘','mg'],
    sodium:['나트륨','mg'],sugar:['총당류','g']
  };
  const known = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function render(context = {}) {
    const esc = context.esc || escape, fmt = context.fmt || (value => value.toLocaleString('ko-KR'));
    const recipe = context.recipeNutrition || {}, daily = context.daily || {}, recipeRows = recipe.nutrients || {}, standalone = context.standalone === true;
    const rows = daily.nutrients || {}, mealCount = Number.isInteger(daily.mealCount) && daily.mealCount > 0 ? daily.mealCount : 0;
    const amount = (value, key) => known(value) ? (value > 0 && value < .1 ? '0.1 미만' : fmt(Math.round(value * 10) / 10))+' '+META[key][1] : '미확인';
    const action = (label, route) => typeof context.button === 'function' ? context.button(label, route) : `<button type="button" class="small-action" data-wf="${route}">${label}</button>`;
    const sourceKind = row => ({entered:'입력값',reference:'참고 추정',partial:'일부만 확인',unknown:'미확인'}[row?.kind] || '');
    const recipeValue = key => {
      const row = recipeRows[key] || {}, complete = known(row.value);
      const partial = !complete && known(row.knownSubtotal) && row.kind === 'partial';
      const value = complete ? amount(row.value, key) : partial ? '확인분 '+amount(row.knownSubtotal, key) : '미확인';
      const missing = Array.isArray(row.missing) ? row.missing.filter(Boolean) : [];
      return {row,complete,partial,value,caption:partial ? (missing.length ? missing.join(' · ')+' 미확인' : '전체 영양량이 아니에요') : complete ? sourceKind(row) : '입력·참고값 없음'};
    };
    const fact = key => {
      const item = recipeValue(key);
      return `<div class="rn-fact" data-recipe-nutrient="${key}" data-nutrient-kind="${item.complete ? item.row.kind || 'known' : item.partial ? 'partial' : 'unknown'}"><dt>${META[key][0]}</dt><dd>${esc(item.value)}</dd>${item.caption ? `<small>${esc(item.caption)}</small>` : ''}</div>`;
    };
    const targetText = (row, key) => {
      const limit = key === 'sugar' || key === 'sodium';
      if(!mealCount || row.status === 'no-records')return '오늘 식사 기록이 없어요';
      if(row.status === 'over' && limit && row.lowerBound)return known(row.excess) && row.excess >= .1 ? '기록된 값만으로 최소 '+amount(row.excess,key)+' 초과' : '기록된 값만으로 내 기준 초과';
      if(row.missingCount > 0 || row.status === 'partial')return (row.missingCount > 0 ? row.missingCount+'끼 영양 미입력 · ' : '')+'남은 양 확인 필요';
      if(!known(row.target) || row.target === 0 || row.status === 'no-target')return limit ? '하루 관리 기준 미설정' : '하루 목표 미설정';
      if(row.status === 'over')return (limit ? '내 기준보다 ' : '목표보다 ')+amount(row.excess,key)+' 많아요';
      if(row.status === 'met')return limit ? '내 관리 기준에 도달했어요' : '하루 목표에 도달했어요';
      return (limit ? '내 기준까지 ' : '목표까지 ')+amount(row.remaining,key)+' 남음';
    };
    const comparison = key => {
      const row = rows[key] || {}, limit = key === 'sugar' || key === 'sodium', projection = standalone ? null : row.projection;
      const current = known(row.value) ? amount(row.value,key) : '미입력';
      const target = known(row.target) && row.target > 0 ? amount(row.target,key) : '미설정';
      const track = mealCount && !row.missingCount && known(row.value) && known(row.target) && row.target > 0 ? Math.max(0, Math.min(100,row.value/row.target*100)) : null;
      let after = '';
      if(projection && known(projection.total)) {
        after = '이 요리 1인분 후 '+amount(projection.total,key);
        if(projection.status === 'over' && known(projection.excess))after += ' · '+(limit ? '내 기준 ' : '목표 ')+amount(projection.excess,key)+' 초과';
        else if(projection.status === 'met')after += ' · '+(limit ? '내 기준' : '목표')+' 도달';
        else if(known(projection.remaining))after += ' · '+amount(projection.remaining,key)+' 남음';
      }
      const state = limit && row.status === 'over' ? 'over' : row.status === 'partial' || row.missingCount > 0 ? 'partial' : 'normal';
      return `<article class="rn-comparison" data-daily-nutrient="${key}" data-nutrition-status="${state}"><header><strong>${META[key][0]}</strong><span>${limit ? '내 관리 기준' : '내 목표'} ${esc(target)}</span></header><p class="rn-today"><span>${row.missingCount > 0 ? '확인된 기록' : '오늘 기록'}</span><b>${esc(current)}</b></p><p class="rn-remaining">${esc(targetText(row,key))}</p>${track !== null ? `<div class="rn-track" aria-hidden="true"><i style="width:${track}%"></i></div>` : ''}${after ? `<p class="rn-after" data-nutrient-projection="${key}">${esc(after)}</p>` : ''}</article>`;
    };
    const advice = [];
    for(const key of ['sugar','sodium']) {
      const row = rows[key] || {}, projectedOver = !standalone && row.projection?.status === 'over';
      if(row.status === 'over' || row.status === 'met' || projectedOver) {
        const lead = projectedOver && row.status !== 'over' && row.status !== 'met' ? '이 요리 1인분을 더하면 내 기준을 넘는 계산이에요. ' : '';
        advice.push(key === 'sodium' ? lead+'다음 끼니는 간장·소금 양과 먹는 국물 양을 확인해 보세요.' : lead+'단 음료·간식의 당류와 요거트의 가당 여부를 확인해 보세요.');
      }
    }
    const roles = Array.isArray(recipe.roles) ? recipe.roles.filter(row => row?.name && row?.text) : [];
    const roleRows = roles.length ? roles : [
      {name:'탄수화물',text:'일상 활동에 쓰는 에너지원이에요.'},
      {name:'단백질',text:'근육과 몸의 조직을 구성하고 유지하는 데 쓰여요.'},
      {name:'지방',text:'세포 구성과 지용성 비타민의 흡수에 필요해요.'}
    ];
    const assumptions = Array.isArray(recipe.assumptions) ? recipe.assumptions.filter(Boolean) : [];
    const sources = Array.isArray(recipe.sources) ? recipe.sources.filter(row => row?.label) : [];
    const servings = known(recipe.servings) && recipe.servings > 0 ? fmt(recipe.servings) : '선택한';
    const anyKnown = Object.values(recipeRows).some(row => known(row?.value));
    const anyPartial = Object.values(recipeRows).some(row => row?.kind === 'partial');
    const kinds = new Set(Object.values(recipeRows).map(row => row?.kind));
    const badge = anyPartial ? '일부 미확인' : kinds.has('reference') && kinds.has('entered') ? '입력·참고' : kinds.has('reference') ? '참고 추정' : anyKnown ? '입력값' : '미확인';
    const energy = recipeValue('kcal');
    const needsTargets = !mealCount || ['carb','protein','fat','sugar','sodium'].some(key => !known(rows[key]?.target));
    return `<div class="recipe-nutrition-service${standalone ? ' is-standalone' : ''}" data-recipe-nutrition-service>
      ${!standalone ? `<section class="rn-section rn-recipe" aria-label="레시피 1인분 영양">
        <header class="rn-heading"><div><h3>1인분 영양</h3><p>만들 양 ${esc(servings)}인분과 구분해요</p></div><span class="rn-source-badge" title="${esc(recipe.sourceLabel || '')}">${esc(badge)}</span></header>
        <div class="rn-energy" data-recipe-nutrient="kcal" data-nutrient-kind="${energy.complete ? energy.row.kind || 'known' : energy.partial ? 'partial' : 'unknown'}"><span>열량</span><strong>${esc(energy.value)}</strong>${energy.caption ? `<small>${esc(energy.caption)}</small>` : ''}</div>
        <dl class="rn-macros">${['carb','protein','fat'].map(fact).join('')}</dl>
        <dl class="rn-other">${['sugar','sodium','fiber','calcium','water'].map(fact).join('')}</dl>
        ${!anyKnown && !anyPartial ? '<p class="rn-note rn-missing">확인할 영양값이 아직 없어요. 모르는 값은 0으로 계산하지 않아요.</p>' : ''}
        ${anyPartial ? '<p class="rn-note rn-missing">확인분은 일부 재료의 합계예요. 소금·양념 등 빠진 재료에 따라 전체 값이 달라져요.</p>' : ''}
        ${recipe.note ? `<p class="rn-note">${esc(recipe.note)}</p>` : ''}
      </section>` : ''}
      <section class="rn-section rn-daily" aria-label="오늘 기록과 영양 목표 비교">
        <header class="rn-heading"><div><h3>${standalone ? '오늘의 영양' : '오늘 기록과 비교'}</h3><p>${mealCount ? '기록한 '+mealCount+'끼 기준'+(standalone ? '' : ' · 개인 1인분 비교') : '먹은 식사를 기록하면 비교할 수 있어요'}</p></div>${needsTargets?action('목표 설정','nutritionTargets'):''}</header>
        <div class="rn-daily-macros">${['carb','protein','fat'].map(comparison).join('')}</div>
        <div class="rn-daily-limits">${['sugar','sodium'].map(comparison).join('')}</div>
        ${standalone ? `<div class="rn-daily-other">${['kcal','fiber','calcium','water'].map(comparison).join('')}</div>` : ''}
        <p class="rn-note">기록하지 않은 식사는 포함하지 않아요. 참고 영양을 가져온 기록은 추정값이에요. 미입력 영양이 있으면 정확한 남은 양을 표시하지 않아요.</p>
        <p class="rn-note rn-sugar-note">총당류는 과일·우유의 당도 포함해요. 유리당·첨가당 기준과 같지 않으며, 여기서는 직접 정한 관리 기준과 비교해요.</p>
        ${advice.length ? `<div class="rn-guidance">${advice.map(text => `<p>${esc(text)}</p>`).join('')}</div>` : ''}
        <div class="rn-actions">${needsTargets?'':action('목표·관리 기준 설정','nutritionTargets')}${action('오늘 기록 보기','todayRecords')}</div>
      </section>
      ${!standalone ? `<details class="rn-disclosure rn-role-details"><summary>${roles.length ? '이 요리 재료의 역할' : '주요 영양소의 역할'}</summary><dl class="rn-roles">${roleRows.map(row => `<div><dt>${esc(row.name)}</dt><dd>${esc(row.text)}</dd></div>`).join('')}</dl></details>
      <details class="rn-disclosure rn-source-details"><summary>영양 계산 근거와 출처</summary><div>${recipe.sourceLabel ? `<p>${esc(recipe.sourceLabel)}</p>` : ''}${assumptions.length ? `<h4>계산 가정</h4><ul>${assumptions.map(text => `<li>${esc(text)}</li>`).join('')}</ul>` : ''}${sources.length ? `<h4>참고 자료</h4><ul>${sources.map(source => `<li>${/^https:\/\//i.test(String(source.url || '')) ? `<a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.label)}</a>` : esc(source.label)}</li>`).join('')}</ul>` : '<p>연결된 영양 출처가 아직 없어요. 입력한 영양값은 입력 출처를 확인해 주세요.</p>'}<p>참고값은 조리 손실·제품·실제 사용량에 따라 달라질 수 있어요. 확인되지 않은 성분은 미확인으로 남겨요.</p></div></details>` : ''}
    </div>`;
  }
  window.KitchenRecipeNutritionView = Object.freeze({render});
})();
