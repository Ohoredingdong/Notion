/* Practical recommendation summary. Recommendation != guaranteed return. */
(()=>{'use strict';
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const N=x=>x!==null&&x!==undefined&&Number.isFinite(Number(x));
const F=(x,d=1)=>N(x)?Number(x).toLocaleString('ko-KR',{maximumFractionDigits:d}):'—';
const M=(x,c)=>N(x)?(c==='KRW'?F(x,0)+'원':'$'+F(x,2)):'—';
let data=null,source=null,error=null;
function card(x,i){
 const s=x.scores||{},m=x.metrics||{};
 return '<article class="rec-card"><div class="rec-rank">'+(i+1)+'순위 · '+E(x.grade)+'</div><h3>'+E(x.display_name||x.name)+'</h3><p class="rec-meta">'+E(x.symbol)+' · '+E(x.sector)+' · '+E(x.price_session||'기준일 미확인')+'</p><div class="rec-price">'+M(x.price,x.currency)+'</div><p class="rec-action">'+E(x.action)+'</p><div class="rec-score"><span>사업·재무 <b>'+F(s.quality,0)+'/35</b></span><span>성장 <b>'+F(s.growth,0)+'/25</b></span><span>가격 <b>'+F(s.valuation,0)+'/25</b></span><span>위험 <b>'+F(s.risk,0)+'/15</b></span></div><div class="rec-total">'+F(x.score,0)+' / 100</div><div class="rec-why"><b>왜 추천하나요?</b>'+(x.why||[]).slice(0,4).map(v=>'<p>• '+E(v)+'</p>').join('')+'</div><p class="rec-note">목표가 차이는 100점 중 최대 4점만 반영합니다. 점수는 예상수익률·상승확률이 아닙니다.</p><button class="text-button" data-rec-open="'+E(x.symbol)+'">기업 상세 보기 ›</button></article>';
}
function aligned(){return data&&source&&data.source_generated_at===source.generated_at}
function render(){
 const old=document.getElementById('practicalRecommendations');if(old)old.remove();
 const anchor=document.getElementById('todayBrief');if(!anchor||!data)return;
 if(!aligned()){
   const sec=document.createElement('section');sec.id='practicalRecommendations';sec.className='rec-section';
   sec.innerHTML='<div class="rec-head"><div><span class="eyebrow">실전 추천 기준</span><h3>최신 자료로 추천을 다시 계산하고 있어요</h3></div></div><p class="rec-intro">주가·실적·3년 재무자료의 기준시점이 모두 맞은 뒤에만 추천 순위를 보여줍니다. 이전 추천을 최신처럼 남겨두지 않습니다.</p>';
   anchor.parentNode.insertBefore(sec,anchor);return;
 }
 const sec=document.createElement('section');sec.id='practicalRecommendations';sec.className='rec-section';
 const top=data.top_recommendations||[];
 sec.innerHTML='<div class="rec-head"><div><span class="eyebrow">실전 추천 기준</span><h3>지금 먼저 볼 종목</h3></div><span>'+top.length+'개 추천</span></div><p class="rec-intro">완벽한 실사 여부와 별개로, 실제 매수 후보를 고르기 위한 기준입니다. 탈락조건을 먼저 적용한 뒤 사업·재무 35점, 성장 25점, 가격 25점, 위험 15점으로 비교합니다.</p>'+(top.length?'<div class="rec-grid">'+top.slice(0,3).map(card).join('')+'</div>':'<div class="empty">현재 기준을 통과한 추천 종목이 없습니다. 기준을 낮춰 억지 추천하지 않습니다.</div>')+'<details class="rec-method"><summary>추천 기준 자세히 보기</summary><div class="details-inner"><p><b>먼저 탈락:</b> 최신성·회계기간·유동성·3년 실적·영업이익·CFO·FCF·부채·예상 EPS·분석가 수·전망편차·예상 PER 이상치를 확인합니다.</p><p><b>점수:</b> 사업·재무 35 + 성장 25 + 가격 25 + 관측 위험 15. 애널리스트 목표가는 가격점수 25점 중 최대 4점뿐입니다.</p><p><b>우선 추천:</b> 85점 이상이며 탈락조건과 경고가 없는 종목. <b>추천:</b> 75점 이상이며 탈락조건과 경고가 없는 종목.</p></div></details>';
 anchor.parentNode.insertBefore(sec,anchor);
 sec.addEventListener('click',e=>{const b=e.target.closest('[data-rec-open]');if(!b)return;const sel=document.getElementById('companySelect');if(sel&&[...sel.options].some(o=>o.value===b.dataset.recOpen)){sel.value=b.dataset.recOpen;sel.dispatchEvent(new Event('change',{bubbles:true}));document.getElementById('tab-detail')?.click();}});
}
async function load(){
 try{
   const t=Date.now();
   const [a,b]=await Promise.all([
     fetch('./stock-recommendations-summary.json?t='+t,{cache:'no-store'}),
     fetch('./stock-opportunity-summary.json?t='+t,{cache:'no-store'})
   ]);
   if(!a.ok||!b.ok)throw Error('HTTP '+a.status+'/'+b.status);
   data=await a.json();source=await b.json();error=null;render()
 }catch(e){error=e.message}
}
const st=document.createElement('style');st.textContent='.rec-section{margin:0 0 22px}.rec-head{display:flex;align-items:end;justify-content:space-between;gap:10px;margin-bottom:5px}.rec-head h3{font-size:20px;margin:2px 0}.rec-head>span{font-size:11px;color:var(--muted)}.rec-intro{font-size:12px;color:var(--muted);line-height:1.8;margin-bottom:12px}.rec-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.rec-card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:17px;position:relative}.rec-card:first-child{border-color:var(--green);box-shadow:0 5px 18px rgba(20,120,80,.08)}.rec-rank{font-size:10px;color:var(--green);font-weight:750}.rec-card h3{font-size:17px;margin:4px 0 0}.rec-meta,.rec-note{font-size:10px;color:var(--muted);line-height:1.7}.rec-price{font-size:21px;font-weight:760;margin:12px 0 2px}.rec-action{font-size:12px;line-height:1.8;margin-bottom:10px}.rec-score{display:grid;grid-template-columns:1fr 1fr;gap:6px}.rec-score span{font-size:10px;background:var(--soft);border-radius:8px;padding:7px}.rec-score b{display:block;font-size:12px}.rec-total{font-size:21px;font-weight:800;color:var(--blue);margin:10px 0}.rec-why{border-top:1px solid var(--line);padding-top:10px;font-size:11px;line-height:1.75}.rec-why p{margin:4px 0}.rec-method{margin-top:10px}@media(max-width:760px){.rec-grid{grid-template-columns:1fr}.rec-score{grid-template-columns:repeat(4,1fr)}.rec-score span{padding:6px 4px;text-align:center}}';
document.head.append(st);load();setInterval(load,5*60*1000);
})();