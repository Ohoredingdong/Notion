/* Statistical FUTURE-period estimates; never a strict-green approval. */
(function(root){'use strict';
const TEXT={up:'상승',flat:'횡보',down:'하락'};
function valid(r,now=Date.now()){
 if(r?.status!=='research_prediction'||!r.target||!r.probabilities)return false;
 const p=['down','flat','up'].map(k=>r.probabilities[k]);
 return p.every(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1)&&Math.abs(p.reduce((a,b)=>a+b,0)-1)<1e-6&&
 Date.parse(r.observed_until)<=Date.parse(r.received_at)&&Date.parse(r.received_at)<=Date.parse(r.issued_at)&&
 Date.parse(r.issued_at)<=now&&Date.parse(r.issued_at)<Date.parse(r.target.start)&&Date.parse(r.target.start)<Date.parse(r.target.end);
}
if(typeof module==='object'&&module.exports)module.exports={valid};
if(!root.document)return;const doc=root.document;
let data=null,mode='daily',busy=false;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=x=>typeof x==='number'&&Number.isFinite(x)?(100*x).toFixed(1)+'%':'—';
const when=x=>x&&Number.isFinite(Date.parse(x))?new Date(x).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',hour12:false}):'미확인';
const reason=x=>({insufficient_regular_session_time:'정규장 잔여 시간 부족',target_already_started_or_delivery_window_too_short:'새 예측을 발행할 시간 구간이 아님',publication_window_missed:'배포 전에 예측 시작시각 도달',intraday_source_stale:'최신 확정 분봉 미수신',future_input_timestamp:'입력 시각 불일치',unresolved_price_discontinuity:'가격 단위·기업행사 확인 필요'}[x]||x||'자료 확인 필요');

const n=x=>typeof x==='number'&&Number.isFinite(x)?x:null;
const p2=x=>n(x)===null?'—':((x*100)>=0?'+':'')+(x*100).toFixed(1)+'%';
function normSymbol(x){return String(x||'').toUpperCase().replace(/\.(KS|KQ)$/,'')}
function recordFor(symbol,preferred='daily'){
 const key=normSymbol(symbol),all=(data?.records||[]).filter(r=>normSymbol(r.symbol)===key);
 return all.find(r=>r.mode===preferred)||all.find(r=>r.status==='research_prediction')||all[0]||null;
}
function signalCards(r){
 const f=r?.feature_values||{},items=[];
 const push=(key,label,value,kind,learn)=>{
   if(n(value)===null)return;
   const pctv=value*100;
   let side='neutral',read='중립';
   if(kind==='signed'){side=pctv>0.15?'up':pctv<-0.15?'down':'neutral';read=side==='up'?'상승 쪽':'하락 쪽';if(side==='neutral')read='중립'}
   if(kind==='risk'){side=Math.abs(pctv)>=2?'risk':'neutral';read=Math.abs(pctv)>=2?'변동성 큼':'변동성 보통'}
   if(kind==='draw'){side=pctv<-3?'down':'neutral';read=side==='down'?'낙폭 부담':'낙폭 제한'}
   if(kind==='rebound'){side=pctv>3?'up':'neutral';read=side==='up'?'반등 흔적':'반등 약함'}
   items.push({key,label,value:pctv,side,read,learn});
 };
 push('r1','최근 1구간 흐름',f.r1,'signed','아주 최근 가격 방향입니다. 짧을수록 뉴스·수급 노이즈 영향이 큽니다.');
 push('r3','최근 3구간 흐름',f.r3,'signed','초단기 흐름이 며칠·몇 봉 이어지는지 확인하는 입력입니다.');
 push('r6','최근 6구간 흐름',f.r6,'signed','단기 추세의 지속 여부를 보는 입력입니다.');
 push('r12','중기 흐름',f.r12,'signed','짧은 반등인지 더 긴 추세인지 구분할 때 함께 봅니다.');
 push('r20','20구간 흐름',f.r20,'signed','최근 흐름의 큰 방향을 확인합니다.');
 push('ma5','5구간 추세 입력',f.ma5,'signed','단기 평균선과 현재 가격 관계를 요약한 입력입니다.');
 push('ma20','20구간 추세 입력',f.ma20,'signed','중기 평균선과 현재 가격 관계를 요약한 입력입니다.');
 push('vol20','20구간 변동성',f.vol20,'risk','방향보다 흔들림의 크기입니다. 변동성이 크면 같은 신호도 실패 범위가 커질 수 있습니다.');
 push('drawdown20','최근 고점 대비 낙폭',f.drawdown20,'draw','고점에서 얼마나 밀렸는지 보여줍니다. 큰 낙폭은 약세·반등 가능성을 동시에 뜻할 수 있습니다.');
 push('rebound20','최근 저점 대비 반등',f.rebound20,'rebound','저점에서 얼마나 회복했는지 보여줍니다. 반등이 강해도 추세 전환 확정은 아닙니다.');
 return items;
}
function studyHTML(r){
 if(!r)return '<section class="fc-study"><h3>AI 예측 공부</h3><p class="fc-warning">이 종목의 방향 예측 기록이 없습니다.</p></section>';
 const good=valid(r),v=r.validation||{},items=signalCards(r),up=items.filter(x=>x.side==='up').sort((a,b)=>Math.abs(b.value)-Math.abs(a.value)).slice(0,3),down=items.filter(x=>x.side==='down').sort((a,b)=>Math.abs(b.value)-Math.abs(a.value)).slice(0,3);
 const bars=good?['up','flat','down'].map(k=>'<div class="fc-study-prob"><span>'+TEXT[k]+'</span><b>'+pct(r.probabilities[k])+'</b><i style="--w:'+Math.max(0,Math.min(100,r.probabilities[k]*100))+'%"></i></div>').join(''):'';
 const band=n(r.neutral_band_pct),virtualMove=good&&band!==null?(r.probabilities.up-r.probabilities.down)*band:null;
 const scenario=good&&band!==null?'<div class="fc-scenario"><div><small>교육용 가상 계산</small><strong>'+(virtualMove>=0?'+':'')+virtualMove.toFixed(2)+'%</strong><span>(상승확률 − 하락확률) × 분류문턱</span></div><div><small>상승 구간 문턱</small><strong>+'+band.toFixed(2)+'%</strong><span>이 이상이면 모델의 상승 클래스로 분류</span></div><div><small>하락 구간 문턱</small><strong>−'+band.toFixed(2)+'%</strong><span>이 이하이면 하락 클래스로 분류</span></div></div><p class="fc-scenario-note">이 값은 목표수익률·목표가가 아닙니다. 현재 확률과 분류 문턱을 이용한 학습용 가상 계산입니다.</p>':'';

 const cards=items.slice(0,8).map(x=>'<article class="fc-study-input '+x.side+'"><div><b>'+esc(x.label)+'</b><span>'+esc(x.read)+'</span></div><strong>'+((x.value>=0?'+':'')+x.value.toFixed(1))+'%</strong><p>'+esc(x.learn)+'</p></article>').join('');
 const reasons=(arr,empty)=>arr.length?arr.map(x=>'<li><b>'+esc(x.label)+'</b> '+((x.value>=0?'+':'')+x.value.toFixed(1))+'% · '+esc(x.learn)+'</li>').join(''):'<li>'+empty+'</li>';
 const perf=v.test_samples?'<div class="fc-study-performance"><div><small>과거 분리검증</small><strong>'+v.test_samples+'건</strong></div><div><small>방향 일치</small><strong>'+pct(v.accuracy)+'</strong></div><div><small>단순 기준</small><strong>'+pct(v.baseline_accuracy)+'</strong></div><div><small>판정</small><strong>'+(v.above_baseline_in_this_holdout?'기준 우위':'우위 미확인')+'</strong></div></div>':'';
 return '<section class="fc-study" id="forecastStudy"><div class="fc-study-head"><div><span class="fc-kicker">AI 방향예측 · 공부 모드</span><h3>'+(good?TEXT[r.direction]+' 비중이 가장 큽니다':'현재 예측 보류')+'</h3><p>'+(good?'상승·횡보·하락 중 상대적으로 가장 큰 확률입니다. 수익확률이나 매수승인이 아닙니다.':'새 방향을 내기엔 입력 시각·배포 구간이 맞지 않아 예측을 보류했습니다.')+'</p></div><span class="fc-study-badge">'+(r.mode==='intraday'?'장중 30분':'다음 정규장')+'</span></div>'+
 (good?'<div class="fc-study-probs">'+bars+'</div>'+scenario:'<div class="fc-warning">'+esc(reason(r.reason))+'</div>')+
 '<div class="fc-study-columns"><div><h4>상승 쪽으로 읽히는 입력</h4><ul>'+reasons(up,'뚜렷한 상승 방향 입력이 없습니다.')+'</ul></div><div><h4>하락 쪽으로 읽히는 입력</h4><ul>'+reasons(down,'뚜렷한 하락 방향 입력이 없습니다.')+'</ul></div></div>'+
 '<div class="fc-study-note"><b>중요:</b> 위 목록은 모델의 <b>실제 기여도/SHAP 값이 아니라 입력값을 사람이 읽기 쉽게 해석한 것</b>입니다. 그래서 “이 요인 때문에 20% 올랐다”처럼 해석하면 안 됩니다.</div>'+
 '<h4 class="fc-study-title">예측에 들어간 숫자를 공부해보기</h4><div class="fc-study-inputs">'+cards+'</div>'+perf+
 '<div class="fc-study-columns fc-study-bottom"><div><h4>왜 틀릴 수 있나요?</h4><ul><li>현재 모델은 가격 중심이며 실시간 뉴스·기관/외국인 수급·호가가 빠져 있습니다.</li><li>과거 분리검증이 좋아도 다음 시장에서 같은 성능을 보장하지 않습니다.</li><li>실적·공시·환율·금리 이벤트가 갑자기 가격 구조를 바꿀 수 있습니다.</li></ul></div><div><h4>오늘 공부할 포인트</h4><ul><li>단기 r1·r3와 중기 r12·r20의 방향이 같은지 비교하세요.</li><li>추세와 변동성이 동시에 강한지 확인하세요.</li><li>예측 방향과 기업 실사 판단은 반드시 따로 보세요.</li></ul></div></div>'+
 '<div class="fc-study-foot">관측 '+esc(when(r.observed_until))+' · 발행 '+esc(when(r.issued_at))+' · '+(r.history_is_point_in_time_vintage?'시점자료':'재수집 과거자료')+'</div></section>';
}
function renderDetailStudy(){
 const body=doc.getElementById('detailBody'),sel=doc.getElementById('companySelect');if(!body||!sel||!data)return;
 const old=doc.getElementById('forecastStudy');if(old)old.remove();
 const r=recordFor(sel.value,'daily');if(!r)return;
 const wrap=doc.createElement('div');wrap.innerHTML=studyHTML(r);const study=wrap.firstElementChild;
 const flow=body.querySelector('.study-flow');const grid=body.querySelector('.decision-grid'); if(flow)flow.insertAdjacentElement('afterend',study); else if(grid)grid.insertAdjacentElement('beforebegin',study); else body.appendChild(study);
}
function panel(){let box=doc.getElementById('directionForecast');if(box)return box;
 const anchor=doc.getElementById('todayBrief');if(!anchor)return null;
 box=doc.createElement('section');box.id='directionForecast';anchor.parentNode.insertBefore(box,anchor);return box;}
function render(){const box=panel();if(!box)return;
 const header='<div class="fc-head"><div><span class="fc-kicker">사전 방향 예측 · 연구용</span><h2>앞으로의 움직임을 따로 계산합니다</h2></div><a href="./stock-forecast.html">전체 예측·검증 ›</a></div>';
 if(!data){box.innerHTML=header+'<p class="fc-warning">최신 예측을 확인하지 못했습니다. 이전 예측을 새로 발행한 것처럼 표시하지 않습니다.</p>';return;}
 const rows=(data.records||[]).filter(r=>r.mode===mode),now=Date.now();
 const future=rows.filter(r=>valid(r,now)&&Date.parse(r.target.start)>now).length;
 box.innerHTML=header+'<p class="fc-intro">과거 가격으로 학습한 모델의 추정 분포입니다. 목표가·조사점수를 확률로 바꾸지 않습니다. 매수 추천이나 수익확률이 아닙니다.</p><div class="fc-tabs"><button data-fc="daily" aria-selected="'+(mode==='daily')+'">다음 정규장</button><button data-fc="intraday" aria-selected="'+(mode==='intraday')+'">장중 30분</button><span>시작 전 예측 '+future+'개</span></div><div class="fc-grid">'+rows.map(r=>{
 const good=valid(r,now),v=r.validation||{},ended=good&&Date.parse(r.target.end)<=now,started=good&&Date.parse(r.target.start)<=now;
 const stage=!good?'예측 보류':ended?'예측 기간 종료':started?'발행 후 진행 중':'사전 발행';
 const likely=good?TEXT[r.direction]:'—';
 return '<article class="fc-card"><div class="fc-name">'+esc(r.name||r.symbol)+' <small>'+esc(r.symbol)+'</small></div><div class="fc-stage">'+stage+'</div>'+(good?'<h3>'+likely+' 비중이 가장 큼</h3><div class="fc-probs">'+['up','flat','down'].map(k=>'<span>'+TEXT[k]+'<b>'+pct(r.probabilities[k])+'</b></span>').join('')+'</div><p class="fc-small">대상: '+esc(when(r.target.start))+' ~ '+esc(when(r.target.end))+' (한국시간)<br>발행: '+esc(when(r.issued_at))+'<br>횡보 구간: 대상 시가 대비 ±'+Number(r.neutral_band_pct).toFixed(2)+'%</p>':'<p class="fc-warning">'+esc(reason(r.reason))+'</p>')+
 '<div class="fc-evidence">'+(v.above_baseline_in_this_holdout?'과거 분리 검증에서 기준모델 우위 · 미래 검증 전':'예측 우위 입증 안 됨 · 연구용 수치')+'</div>'+
 (v.test_samples?'<details><summary>과거 검증·한계</summary><p>비중첩 검증 '+v.test_samples+'건 / '+v.test_sessions+'거래일<br>방향 일치 '+pct(v.accuracy)+' / 단순 기준 '+pct(v.baseline_accuracy)+'<br>브라이어 오차 '+v.brier_loss.toFixed(3)+' / 기준 '+v.baseline_brier_loss.toFixed(3)+' (낮을수록 좋음)<br>검증 종료 '+esc(when(v.test_end))+'</p><p>현재 재수집한 과거자료의 시간순 검증입니다. 실거래·알림 전달 성과가 아닙니다. 실시간 이벤트·기관 수급·호가 분석은 아직 이 모델에 포함되지 않습니다.</p></details>':'')+'</article>';
 }).join('')+'</div><div class="fc-bottom"><b>실제 사전 기록의 이후 결과</b> '+(data.forward_evaluation?.publicly_timely_observations||0)+'건 확인 · 방향 일치율 '+pct(data.forward_evaluation?.live_accuracy)+'<br><span>자료 생성 '+esc(when(data.generated_at))+' · 정기 실행이며 실시간 연결 아님 · 초록색 실사와 분리</span></div>';
 box.querySelectorAll('[data-fc]').forEach(b=>b.onclick=()=>{mode=b.dataset.fc;render()});renderDetailStudy();}
const style=doc.createElement('style');style.textContent='#directionForecast{margin:18px 0;padding:20px;background:#f6f8fc;color:#25334b;border:1px solid #dce4f0;border-radius:20px;font:13px/1.7 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif}#directionForecast *{box-sizing:border-box}.fc-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.fc-head h2{font-size:21px;margin:3px 0}.fc-head a{color:#365e9a;white-space:nowrap;font-size:12px}.fc-kicker{font-size:11px;color:#526684}.fc-intro,.fc-small{color:#62718a}.fc-tabs{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:14px 0}.fc-tabs button{border:1px solid #ccd7e8;border-radius:10px;background:#fff;padding:8px 12px;color:#304566;cursor:pointer}.fc-tabs button[aria-selected=true]{background:#e4ecf9;border-color:#99afd0}.fc-tabs span{margin-left:auto;font-size:12px}.fc-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.fc-card{padding:15px;border:1px solid #dfe5ef;border-radius:14px;background:#fff;min-width:0}.fc-name{font-weight:750;font-size:15px}.fc-name small{color:#697993;font-size:10px}.fc-stage{font-size:11px;color:#526b92;margin:7px 0}.fc-card h3{font-size:17px;margin:7px 0}.fc-probs{display:flex;gap:5px}.fc-probs span{background:#eef3fa;padding:6px;text-align:center;flex:1;font-size:11px;border-radius:8px}.fc-probs b{display:block;font-size:16px;color:#365a8d}.fc-small{font-size:10px;overflow-wrap:anywhere}.fc-evidence,.fc-warning{padding:9px;background:#fbf5e9;color:#805d22;font-size:11px;border-radius:8px}.fc-card details{font-size:11px;margin-top:10px;line-height:1.75}.fc-card summary{cursor:pointer}.fc-bottom{font-size:12px;margin-top:16px}.fc-bottom span{color:#64748b;font-size:11px}@media(max-width:900px){.fc-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.fc-grid{grid-template-columns:1fr}.fc-head{display:block}#directionForecast{padding:14px}.fc-head h2{font-size:19px}}.fc-study{margin:18px 0;padding:18px;background:#fff;border:1px solid #e2e7ec;border-radius:16px;color:#243547}.fc-study *{box-sizing:border-box}.fc-study-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start}.fc-study-head h3{font-size:20px;margin:4px 0}.fc-study-head p{font-size:11px;color:#667482;max-width:650px}.fc-study-badge{font-size:10px;background:#eef2f5;color:#526477;border-radius:999px;padding:6px 9px;white-space:nowrap}.fc-study-probs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:14px 0}.fc-scenario{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0}.fc-scenario>div{padding:10px;border:1px solid #e5e9ed;border-radius:10px;background:#fbfcfd}.fc-scenario small{display:block;font-size:9px;color:#7a8793}.fc-scenario strong{display:block;font-size:16px;margin:4px 0}.fc-scenario span{display:block;font-size:9px;color:#6d7b88;line-height:1.5}.fc-scenario-note{font-size:9px;color:#7c633a;background:#fff8ed;border-radius:8px;padding:8px 10px;margin:6px 0 12px}.fc-study{scroll-margin-top:20px}.fc-study-prob{position:relative;overflow:hidden;padding:10px;border:1px solid #e5e9ed;border-radius:10px;background:#fafbfc}.fc-study-prob span{font-size:10px;color:#71808d}.fc-study-prob b{display:block;font-size:18px;margin-top:3px}.fc-study-prob i{position:absolute;left:0;bottom:0;height:3px;width:var(--w);background:#506b87}.fc-study-columns{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}.fc-study-columns>div{padding:12px;background:#f8fafb;border-radius:11px}.fc-study-columns h4,.fc-study-title{font-size:12px;margin:0 0 7px}.fc-study-columns ul{margin:0;padding-left:17px;font-size:10.5px;line-height:1.75;color:#5f6f7e}.fc-study-note{padding:10px 12px;background:#fff8ed;border:1px solid #f0e1c7;border-radius:10px;font-size:10px;color:#7c633a;line-height:1.7}.fc-study-title{margin-top:16px}.fc-study-inputs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.fc-study-input{padding:10px;border:1px solid #e5e9ed;border-radius:10px;background:#fbfcfd;min-width:0}.fc-study-input>div{display:flex;justify-content:space-between;gap:6px}.fc-study-input b{font-size:10px}.fc-study-input span{font-size:8px;color:#6d7c88}.fc-study-input strong{display:block;font-size:15px;margin:5px 0}.fc-study-input p{font-size:9px;line-height:1.55;color:#74808c;margin:0}.fc-study-input.up{border-left:3px solid #d85a64}.fc-study-input.down{border-left:3px solid #3d78c5}.fc-study-input.risk{border-left:3px solid #d39b48}.fc-study-performance{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#e8ecef;border:1px solid #e8ecef;border-radius:10px;overflow:hidden;margin-top:12px}.fc-study-performance>div{background:#fff;padding:10px}.fc-study-performance small{font-size:9px;color:#7b8791;display:block}.fc-study-performance strong{font-size:12px;display:block;margin-top:3px}.fc-study-bottom{margin-top:12px}.fc-study-foot{font-size:9px;color:#7c8791;margin-top:10px}@media(max-width:900px){.fc-study-inputs{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){.fc-scenario{grid-template-columns:1fr}.fc-study-head{display:block}.fc-study-badge{display:inline-block;margin-top:8px}.fc-study-columns{grid-template-columns:1fr}.fc-study-inputs{grid-template-columns:1fr 1fr}.fc-study-performance{grid-template-columns:1fr 1fr}.fc-study{padding:14px}.fc-study-probs{gap:6px}.fc-study-prob{padding:8px}}';doc.head.appendChild(style);
async function load(){if(busy)return;busy=true;try{const r=await fetch('./stock-direction-forecast.json?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('http');const x=await r.json();if(x.version!=='direction-forecast-1.0'||!Array.isArray(x.records))throw Error('schema');data=x;}catch(_){data=null;}finally{busy=false;render();renderDetailStudy();}}
function start(){render();load();doc.addEventListener('change',e=>{if(e.target?.id==='companySelect')setTimeout(renderDetailStudy,0)});doc.addEventListener('click',e=>{if(e.target.closest?.('[data-open],[data-nr-detail],[data-nr-select]'))setTimeout(renderDetailStudy,80)});new MutationObserver(()=>{if(!doc.getElementById('view-detail')?.hidden)setTimeout(renderDetailStudy,0)}).observe(doc.body,{subtree:true,attributes:true,attributeFilter:['hidden']});}if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',start);else start();setInterval(()=>{if(!doc.hidden)load()},60000);
})(typeof window!=='undefined'?window:globalThis);
