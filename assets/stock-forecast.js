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
 box.querySelectorAll('[data-fc]').forEach(b=>b.onclick=()=>{mode=b.dataset.fc;render()});}
const style=doc.createElement('style');style.textContent='#directionForecast{margin:18px 0;padding:20px;background:#f6f8fc;color:#25334b;border:1px solid #dce4f0;border-radius:20px;font:13px/1.7 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif}#directionForecast *{box-sizing:border-box}.fc-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.fc-head h2{font-size:21px;margin:3px 0}.fc-head a{color:#365e9a;white-space:nowrap;font-size:12px}.fc-kicker{font-size:11px;color:#526684}.fc-intro,.fc-small{color:#62718a}.fc-tabs{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:14px 0}.fc-tabs button{border:1px solid #ccd7e8;border-radius:10px;background:#fff;padding:8px 12px;color:#304566;cursor:pointer}.fc-tabs button[aria-selected=true]{background:#e4ecf9;border-color:#99afd0}.fc-tabs span{margin-left:auto;font-size:12px}.fc-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.fc-card{padding:15px;border:1px solid #dfe5ef;border-radius:14px;background:#fff;min-width:0}.fc-name{font-weight:750;font-size:15px}.fc-name small{color:#697993;font-size:10px}.fc-stage{font-size:11px;color:#526b92;margin:7px 0}.fc-card h3{font-size:17px;margin:7px 0}.fc-probs{display:flex;gap:5px}.fc-probs span{background:#eef3fa;padding:6px;text-align:center;flex:1;font-size:11px;border-radius:8px}.fc-probs b{display:block;font-size:16px;color:#365a8d}.fc-small{font-size:10px;overflow-wrap:anywhere}.fc-evidence,.fc-warning{padding:9px;background:#fbf5e9;color:#805d22;font-size:11px;border-radius:8px}.fc-card details{font-size:11px;margin-top:10px;line-height:1.75}.fc-card summary{cursor:pointer}.fc-bottom{font-size:12px;margin-top:16px}.fc-bottom span{color:#64748b;font-size:11px}@media(max-width:900px){.fc-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.fc-grid{grid-template-columns:1fr}.fc-head{display:block}#directionForecast{padding:14px}.fc-head h2{font-size:19px}}';doc.head.appendChild(style);
async function load(){if(busy)return;busy=true;try{const r=await fetch('./stock-direction-forecast.json?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('http');const x=await r.json();if(x.version!=='direction-forecast-1.0'||!Array.isArray(x.records))throw Error('schema');data=x;}catch(_){data=null;}finally{busy=false;render();}}
function start(){render();load()}if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',start);else start();setInterval(()=>{if(!doc.hidden)load()},60000);
})(typeof window!=='undefined'?window:globalThis);
