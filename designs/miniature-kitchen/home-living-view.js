/* Visible everyday tools. Read real records; a view never seeds products. */
(() => {
 'use strict';
 const guides=[
  {id:'labels',tag:'영양표시',title:'먼저, 몇 회분인지 확인해요',lead:'1회분과 한 봉지 전체는 달라요.',body:'영양표에 적힌 기준량과 실제 먹은 양을 함께 확인해 보세요. 한 포장에 여러 회분이 들어 있다면, 표시된 수치를 포장 전체의 수치로 읽지 않도록 기준량부터 살펴보세요.',source:'식품안전나라 · 영양표시',url:'https://www.foodsafetykorea.go.kr/'},
  {id:'allergy',tag:'식품 선택',title:'재료명과 알레르기 표시',lead:'제품 앞면보다 원재료 표시를 살펴봐요.',body:'제품명만으로 모든 원재료를 알 수는 없어요. 피해야 하는 식품이 있다면 원재료명과 알레르기 유발물질 표시를 확인하세요. 레시피의 피할 재료 조건은 입력된 재료명을 기준으로 걸러 주므로 제품의 실제 표시도 함께 확인해야 해요.',source:'식품안전나라 · 식품 표시',url:'https://www.foodsafetykorea.go.kr/'},
  {id:'storage',tag:'재료 보관',title:'보관 방법도 기한과 함께',lead:'개봉 전·후의 보관 조건을 구분해요.',body:'제품에 표시된 냉장·냉동·실온 보관 방법과 개봉 후 안내를 함께 확인하세요. 냉장고에는 인쇄된 기한과 개봉일을 따로 남길 수 있어요. 기록한 날짜만으로 식품의 현재 상태가 확인되는 것은 아니에요.',source:'식품안전나라 · 식품 보관',url:'https://www.foodsafetykorea.go.kr/'},
  {id:'supplements',tag:'영양제',title:'제품 정보와 내 일정을 따로',lead:'성분표와 복용 체크를 함께 관리해요.',body:'영양제에 적힌 성분과 섭취 방법을 제품 정보에 남기고, 실제 섭취한 날만 체크해 보세요. 체크 횟수는 섭취 기록이며 영양소가 충분한지 판정하는 수치는 아니에요. 제품 표시와 개인 기록을 구분해 살펴볼 수 있어요.',source:'식품안전나라 · 건강기능식품',url:'https://www.foodsafetykorea.go.kr/'}
 ];
 const bottle=done=>`<svg viewBox="0 0 32 44" fill="none" aria-hidden="true"><path d="M10 3h12v7H10Z" fill="${done?'#607c60':'#bfa680'}"/><path d="M11 10h10l4 5v23a3 3 0 0 1-3 3H10a3 3 0 0 1-3-3V15Z" fill="#b18a51" stroke="#8f6e43"/><path d="M8 20h16v14H8Z" fill="#fff9ec"/><path d="M12 27h8m-4-4v8" stroke="${done?'#607c60':'#aa8257'}" stroke-width="2" stroke-linecap="round"/></svg>`;
 function renderShelf({flow,day,esc,fmt}){
  const rows=flow.supplements,done=rows.filter(r=>r.days.includes(day)).length,visible=rows.slice(0,4);
  return `<button type="button" class="shelf-compact" data-living-supplements aria-label="오늘 영양제 ${done}/${rows.length}, 복용 기록과 제품 관리">${bottle(done>0)}<span><strong>영양제</strong><small>${rows.length?`${fmt(done)} / ${fmt(rows.length)} 체크`:'제품 등록'}</small></span></button><div class="shelf-wide"><div class="supplement-shelf-label"><strong>오늘의 영양제</strong><small>${fmt(done)} / ${fmt(rows.length)} 체크</small></div><div class="shelf-bottles">${visible.map(r=>`<button type="button" class="supplement-bottle" data-home-supplement-today="${esc(r.id)}" aria-pressed="${r.days.includes(day)}" aria-label="${esc(r.name)}, ${r.days.includes(day)?'오늘 복용 체크 해제':'오늘 복용 체크'}">${bottle(r.days.includes(day))}<span>${esc(r.name)}</span><small>${r.days.includes(day)?'체크 완료':'오늘 체크'}</small></button>`).join('')}</div><button type="button" class="shelf-manage" data-living-supplements>${rows.length?rows.length>4?`전체 ${fmt(rows.length)}개`:'제품 관리':'+ 영양제 등록'}</button></div>`;
 }
 function renderHealth(){return `<div class="health-hub"><header><span>부엌에서 읽는 작은 상식</span><p>먹고, 고르고, 기록할 때 알아두면 좋아요.</p></header><div class="health-guide-grid">${guides.map(g=>`<button type="button" class="health-guide-card" data-living-article="${g.id}"><small>${g.tag}</small><strong>${g.title}</strong><span>${g.lead}</span></button>`).join('')}</div><footer>참고 출처: 식품의약품안전처 식품안전나라</footer></div>`;}
 function openArticle(id){const g=guides.find(x=>x.id===id);if(!g)return;window.MiniKitchen.showTray(g.title,`<article class="health-article"><span>${g.tag}</span><h3>${g.lead}</h3><p>${g.body}</p><a href="${g.url}" target="_blank" rel="noopener noreferrer">참고 출처 · ${g.source} ↗</a><button type="button" class="small-action" data-close>상식 목록으로</button></article>`,'HEALTH');}
 window.KitchenLivingView=Object.freeze({renderShelf,renderHealth,openArticle});
})();
