
(function(){
'use strict';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let official=null,radar=null,selected=null;
const sectors={'005930':'반도체·전자','000660':'메모리 반도체','035420':'플랫폼','207940':'바이오 위탁생산','005380':'자동차','AAPL':'소비자 기술','MSFT':'클라우드','NVDA':'AI 반도체','AMZN':'커머스·클라우드','TSLA':'전기차'};
const style=document.createElement('style');
style.textContent='.v6-compare{display:grid;grid-template-columns:1fr 1fr;gap:12px}.v6-panel{padding:15px;border:1px solid var(--line);border-radius:10px}.v6-panel h3{font-size:13px}.v6-panel p,.v6-panel li{font-size:11px;line-height:1.85}@media(max-width:640px){.v6-compare{grid-template-columns:1fr}}.v6-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.v6-card{font:inherit;color:var(--text);cursor:pointer;text-align:left;border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:16px}.v6-card:hover{background:var(--soft);border-color:var(--blue)}.v6-card strong{display:block;font-size:14px;margin:6px 0}.v6-card small{display:block;color:var(--sub);font-size:11px;line-height:1.8}.v6-note{background:var(--soft);padding:15px;border-radius:10px;font-size:12px;line-height:1.85;margin:14px 0}.v6-paper{border:1px solid var(--line);border-radius:12px;padding:19px;margin:22px 0}.v6-paper h3{font-size:15px;margin:0 0 9px}.v6-paper label{display:block;font-size:12px;font-weight:700;margin-top:15px;margin-bottom:5px}.v6-paper textarea,.v6-paper select{width:100%;border:1px solid var(--line);border-radius:8px;padding:10px;color:var(--text);background:var(--panel);font:inherit}.v6-paper textarea{min-height:72px}.v6-paper button{padding:9px 12px;background:var(--panel);color:var(--blue);border:1px solid var(--line);border-radius:8px;cursor:pointer;margin-top:12px}.v6-paper small{font-size:11px;color:var(--sub)}@media(max-width:720px){.v6-cards{grid-template-columns:1fr 1fr}}@media(max-width:520px){.v6-cards{grid-template-columns:1fr}}';
document.head.append(style);
const candidates=$('#candidateSection');
if(candidates)candidates.innerHTML='<div class="section-head"><h2>먼저 검증할 기업</h2><small>공식 자료 우선 · 매수 추천 아님</small></div><div id="v6Cards" class="v6-cards">공식 자료를 확인하는 중입니다.</div><p class="v6-note">이 화면은 공식 자료 확보 여부부터 보여줍니다. 같은 업종·동일한 실적 기준끼리 비교해야 합니다. 미검증 기업을 저평가 기업으로 추천하지 않습니다.</p>';
const detail=$('#view-analysis');
const decision=document.createElement('section');
decision.id='v6DecisionPanel';
decision.className='v6-paper';
decision.innerHTML='<h3>매수 여부 판단 · 단기 / 장기</h3><div id="v6DecisionBody">기업을 선택하면 분석 결과가 표시됩니다.</div>';
if(detail)detail.appendChild(decision);
function status(sym){const x=official?.companies?.find(r=>r.symbol===sym);if(!x)return{kind:'미검증',n:0};const arr=x.fields||[],matched=arr.filter(z=>z.status==='match').length,broken=arr.filter(z=>['mismatch','basis_mismatch','unit_mismatch'].includes(z.status)).length;return {kind:broken?'불일치 확인':matched===8?'공식 8/8 일치':matched?'부분 검증':'미검증',n:matched,issues:broken};}
function items(){const rows=radar?.companies||[];return rows.filter(x=>x.symbol).map(r=>({r,s:status(r.symbol)})).sort((a,b)=>b.s.n-a.s.n);}
function decisionView(){
 const r=radar?.companies?.find(x=>x.symbol===selected),box=$('#v6DecisionBody');if(!box)return;
 if(!r){box.textContent='먼저 기업을 선택하세요.';return}
 const a=status(selected),m=r.review_rank||{},q=r.quality||{},priceOk=r.price!=null&&q.status!=='error';
 const ver=a.n===8;
 const shortData=['실적 발표·뉴스 촉매 검증','가격 반응·거래량·수급 확인','손실 한도 및 무효화 조건'];
 const longData=['공시 실적·현금흐름 검증','향후 EPS·현금흐름 추정 검증','동종업계 대비 밸류에이션·부채 비교'];
 const panel=(name,list,ready,reason)=>'<div class="v6-panel"><h3>'+name+' · '+(ready?'조건부 검토':'관망 / 검증 필요')+'</h3><p>'+reason+'</p><p><b>매수 판단 전에 필요한 확인</b></p><ul>'+list.map(x=>'<li>'+x+'</li>').join('')+'</ul></div>';
 // No real verified catalysts, forecast EPS or margin of safety currently; no fabricated buy signal.
 const short=panel('단기',shortData,false,'최신 뉴스 촉매·거래량·수급·손절 기준을 아직 데이터로 함께 검증하지 못했습니다.');
 const long=panel('장기',longData,false,(ver?'과거 8개 재무수치가 공식 공시와 일치합니다. ':'공식 수치 검증이 아직 완료되지 않았습니다. ')+'하지만 현재 가격에 미래 실적 기대가 얼마나 반영됐는지는 산정되지 않았습니다.');
 box.innerHTML='<div class="v6-note"><b>현재 분석 결론: 매수 판단 보류</b><div>이것은 주가 하락 예측이 아니라, 매수 근거에 필요한 필수 데이터가 부족하다는 표시입니다.</div><div>공시: '+esc(a.kind)+' · 시세: '+(priceOk?'수집값 있음':'확인 필요')+' · 산업: '+esc(sectors[selected]||'미분류')+'</div></div><div class="v6-compare">'+short+long+'</div><p class="v6-note"><b>확인 기준</b> · 단기는 촉매·수급·위험대비 기대수익, 장기는 예상 이익·적정 가치범위·안전마진이 뒷받침돼야 합니다. 현재 시스템은 이 항목을 모두 확인하지 못하므로 매수 추천이나 상승확률을 표시하지 않습니다.</p>';
}
function render(){
 const arr=items();const verified=arr.filter(x=>x.s.n===8).length;const risks=arr.filter(x=>x.s.issues).length;
 if($('#countReady')){$('#countReady').textContent=verified;const parent=$('#countReady').parentElement;const label=parent?.querySelector('.sub');if(label)label.textContent='공식 8항목 일치';}
 if($('#countRisk')){$('#countRisk').textContent=risks;const label=$('#countRisk').parentElement?.querySelector('.sub');if(label)label.textContent='수치·기준 불일치';}
 const root=$('#v6Cards');if(!root)return;
 root.innerHTML=arr.slice(0,3).map(x=>'<button class="v6-card" data-v6="'+esc(x.r.symbol)+'"><small>'+esc(sectors[x.r.symbol]||'산업 확인')+' · '+esc(x.r.symbol)+'</small><strong>'+esc(x.r.name)+'</strong><small>매출 성장 '+(x.r.revenue_growth??'—')+'% · 영업이익률 '+(x.r.operating_margin??'—')+'%</small><small>공식 대조: '+esc(x.s.kind)+' ('+x.s.n+'/8)</small><small>선택하여 기업분석 보기 →</small></button>').join('');
}
async function load(){try{const stamp=Date.now();const get=async name=>{const res=await fetch('./'+name+'?t='+stamp,{cache:'no-store'});if(!res.ok)throw Error(name+' HTTP '+res.status);return res.json()};[official,radar]=await Promise.all([get('stock-official-audit.json'),get('stock-investment-intelligence.json')]);render();}catch(e){if($('#v6Cards'))$('#v6Cards').textContent='공식 대조자료 불러오기 실패: '+e.message;}}
document.addEventListener('click',e=>{const x=e.target.closest('[data-v6]');if(!x)return;selected=x.dataset.v6;const search=$('#search');if(search){search.value=selected;search.dispatchEvent(new Event('input',{bubbles:true}));const row=$('#rows tr[data-symbol]');if(row)row.click()}document.querySelector('[data-view="analysis"]')?.click();});
document.querySelector('#rows')?.addEventListener('click',e=>{const row=e.target.closest('[data-symbol]');if(row){selected=row.dataset.symbol;setTimeout(decisionView,0);}});
$('#reload')?.addEventListener('click',load);
load();setInterval(load,30*60*1000);
})();