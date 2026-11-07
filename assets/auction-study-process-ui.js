/* Read-only auction roadmap. Court notices determine actual case deadlines. */
(() => {
  'use strict';
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  class ProcessDesk {
    constructor(callbacks){
      this.callbacks=callbacks;this.stage='application';this.document=null;this.pane='list';this.listScroll=0;
      document.addEventListener('click',event=>this.click(event));
    }
    render(){
      const data=window.AuctionProcessData;
      const stage=data.stages.find(item=>item.id===this.stage)||data.stages[0];
      const doc=data.documentSet.find(item=>item.id===this.document);
      const phases=[...new Set(data.stages.map(item=>item.phase))];
      return `<section class="auction-process" data-pane="${this.pane}"><div class="process-intro"><div><span class="badge neutral">신청 · 매각 · 잔금 · 인도</span><p>단계를 선택해 서류와 확인 항목을 보세요.</p></div><button class="button primary small" data-process-action="practice">모의경매 →</button></div><nav class="process-panes" aria-label="경매 절차 보기"><button type="button" data-process-pane="list" aria-pressed="${this.pane==='list'}">목록</button><button type="button" data-process-pane="detail" aria-pressed="${this.pane==='detail'}">상세</button></nav><div class="process-layout"><aside class="process-list" aria-label="경매 단계와 서류 목록"><div class="process-list-scroll">${phases.map(phase=>`<section class="process-phase"><h2>${esc(phase)}</h2>${data.stages.filter(item=>item.phase===phase).map(item=>`<button type="button" data-process-stage="${item.id}" class="${!doc&&stage.id===item.id?'selected':''}" ${!doc&&stage.id===item.id?'aria-current="step"':''}><span>${String(data.stages.indexOf(item)+1).padStart(2,'0')}</span><strong>${esc(item.title)}</strong><i aria-hidden="true">›</i></button>`).join('')}</section>`).join('')}<section class="process-phase process-doc-list"><h2>입찰 전 서류</h2>${data.documentSet.map(item=>`<button type="button" data-process-document="${item.id}" class="${doc?.id===item.id?'selected':''}"><span aria-hidden="true">▤</span><strong>${esc(item.name)}</strong><i aria-hidden="true">›</i></button>`).join('')}</section></div></aside><article class="process-detail" aria-live="polite"><div class="process-detail-scroll">${doc?`<h2>${esc(doc.name)}</h2><p class="process-lead">${esc(doc.purpose)}</p><dl class="process-doc-meta"><div><dt>확인 시점</dt><dd>${esc(doc.when)}</dd></div><div><dt>열람처</dt><dd>${esc(doc.where)}</dd></div></dl><h3>확인 항목</h3><ul>${doc.checklist.map(text=>`<li>${esc(text)}</li>`).join('')}</ul><p class="process-learning-note">모의경매에서 가상 서류로 연습할 수 있습니다. 실제 물건은 최신 원문을 확인하세요.</p>`:`<span class="process-kicker">${esc(stage.phase)} · 단계 ${data.stages.indexOf(stage)+1}</span><h2>${esc(stage.title)}</h2><p class="process-lead">${esc(stage.description)}</p><h3>확인 항목</h3><ul>${stage.actions.map(text=>`<li>${esc(text)}</li>`).join('')}</ul><h3>관련 서류</h3><div class="process-doc-links">${stage.documents.map(name=>{const item=data.documentSet.find(d=>d.name===name);return item?`<button type="button" data-process-document="${item.id}">${esc(name)} ↗</button>`:`<span>${esc(name)}</span>`;}).join('')}</div><div class="process-timing"><strong>기한·진행 유의사항</strong><p>${esc(stage.timingNote)}</p></div><h3>다음 절차</h3><div class="process-branches">${stage.branches.map(branch=>`<div><button type="button" ${branch.to?`data-process-stage="${branch.to}"`:'disabled'}>${esc(branch.label)} ${branch.to?'→':''}</button><p>${esc(branch.note)}</p></div>`).join('')}</div>`}<footer class="process-disclaimer">${esc(data.disclaimer)}</footer></div></article></div></section>`;
    }
    click(event){
      const root=document.querySelector('.auction-process');if(!root)return;
      const button=event.target.closest('[data-process-stage],[data-process-document],[data-process-pane],[data-process-action]');if(!button||!root.contains(button))return;
      if(button.dataset.processAction==='practice'){this.callbacks.openPage('simulation');return;}
      if(button.dataset.processPane)this.pane=button.dataset.processPane;
      if(button.dataset.processStage){this.stage=button.dataset.processStage;this.document=null;if(innerWidth<=1000)this.pane='detail';}
      if(button.dataset.processDocument){this.document=button.dataset.processDocument;if(innerWidth<=1000)this.pane='detail';}
      this.listScroll=root.querySelector('.process-list-scroll').scrollTop;
      const template=document.createElement('template');template.innerHTML=this.render();root.replaceWith(template.content.firstElementChild);
      document.querySelector('.process-list-scroll').scrollTop=this.listScroll;
      if(button.dataset.processStage||button.dataset.processDocument){
        const heading=document.querySelector('.process-detail h2');heading.setAttribute('tabindex','-1');heading.focus({preventScroll:true});
      }else if(button.dataset.processPane){
        document.querySelector(`[data-process-pane="${this.pane}"]`).focus({preventScroll:true});
      }
    }
  }
  window.AuctionProcess={create:callbacks=>new ProcessDesk(callbacks)};
})();
