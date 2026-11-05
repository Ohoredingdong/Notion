/* The kitchen hub reads its chosen goal; only existing actions write records. */
(() => {
  'use strict';
  function renderGrowth(ctx) {
    const {firstDone,goal,daily,propsMarkup,esc,fmt,routeButton,icons,fridgeArt,giftIcon}=ctx;
    const label=goal.label,value=goal.value,target=goal.target;
    const percent=target>0?Math.max(0,Math.min(100,value/target*100)):0;
    const progress=`<span class="growth-goal-label">${esc(label)}</span><span class="growth-first-track" role="progressbar" aria-label="${esc(label)}" aria-valuemin="0" aria-valuemax="${target}" aria-valuenow="${value}"><i style="width:${percent}%"></i></span><span class="growth-first-counter"><span>${fmt(value)} / ${fmt(target)}</span><span>${firstDone?'목표 보기':'첫 요리 기록'} <span aria-hidden="true">›</span></span></span>`;
    return `<section class="growth-first-goal"><div class="growth-first-progress"><span class="growth-goal-icon" aria-hidden="true">${icons.icon('diary')}</span>${routeButton(progress,firstDone?'book':'recipes',`class="growth-goal-main" aria-label="${esc(firstDone?label+' · 요리 도감과 목표 보기':'첫 요리 기록하기') }"`)}${routeButton(giftIcon+' 꾸밈권 '+fmt(daily.tickets),'rewards','class="ticket-pill" aria-label="모은 소품과 꾸밈권 보기"')}</div><div class="growth-goal-actions">${routeButton('요리 도감　›','book')}<button type="button" data-home-open="decor">부엌 꾸미기　›</button></div></section><div class="growth-room-slot"><button type="button" class="growth-preview home-kitchen-scene" data-home-open="decor" aria-label="내 부엌 꾸미기 열기">${fridgeArt||''}<span id="growthSceneDecor" class="committed-scene-props" aria-hidden="true">${propsMarkup}</span><span class="growth-preview-callout">나의 부엌 꾸미기 ›</span></button></div>`;
  }
  window.KitchenGrowthHub=Object.freeze({renderGrowth});
})();
