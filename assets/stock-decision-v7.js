/* Decision view v7. Read-only research; training widget remains separate. */
(()=>{'use strict';
if(window.stockDecisionV7)return;window.stockDecisionV7=true;
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safe=s=>{try{const u=new URL(s);return u.protocol==='https:'?esc(u.href):''}catch{return''}};
const num=(x,d=2)=>x==null||!Number.isFinite(Number(x))?'—':Number(x).toLocaleString('ko-KR',{maximumFractionDigits:d});
const pct=x=>x==null?'—':(x>0?'+':'')+num(x,2)+'%';
const money=(x,r)=>x==null?'—':(r.currency==='KRW'?'₩':'$')+num(x,r.currency==='KRW'?0:2);
const when=s=>{const d=new Date(s||'');return Number.isFinite(d.getTime())?d.toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false})+' KST':'미확인'};
const elapsed=s=>{const t=Date.parse(s||'');return Number.isFinite(t)?(Date.now()-t)/3600000:Infinity};
let data=null,selected=null,busy=false,error=null,market='ALL';
const CSS=`
#decision-v7-home,#decision-v7-panel{color:var(--text,#202632);font-size:13px;line-height:1.75}
.dv7-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;margin:0 0 14px}.dv7-head h2{margin:0;font-size:19px;letter-spacing:-.04em;line-height:1.45}.dv7-head small{display:block;font-size:11px;color:var(--sub,#667085);margin-top:5px}
.dv7-status{margin:0 0 18px;border:1px solid var(--line,#e5e7eb);border-radius:11px;padding:12px 15px;background:var(--soft,#f7f8fa);font-size:12px;line-height:1.75}.dv7-status strong{display:block;font-size:13px}.dv7-status.bad{border-color:#bf7056;background:rgba(180,70,50,.07)}
.dv7-counts{display:flex;gap:9px;flex-wrap:wrap;margin:14px 0 18px}.dv7-counts span{font-size:12px;background:var(--soft,#f7f8fa);border-radius:8px;padding:8px 11px}
.dv7-toolbar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:0 0 13px}.dv7-toolbar button{border:1px solid var(--line);background:var(--panel,#fff);font:inherit;font-size:12px;padding:7px 11px;border-radius:8px;cursor:pointer;color:var(--text)}.dv7-toolbar button[aria-pressed=true]{border-color:var(--blue,#3568a0);background:var(--soft)}
.dv7-row{display:grid;grid-template-columns:1.1fr 1.5fr 1.5fr;gap:16px;align-items:start;width:100%;padding:16px;border:1px solid var(--line,#e5e7eb);background:var(--panel,#fff);color:var(--text);border-radius:11px;margin:8px 0;text-align:left;cursor:pointer;font:inherit}.dv7-row:hover{border-color:var(--blue,#3568a0)}.dv7-row strong{display:block;font-size:14px;line-height:1.5}.dv7-row small{display:block;color:var(--sub);font-size:11px;line-height:1.7;margin-top:4px}.dv7-result{font-size:12px;font-weight:700;line-height:1.7}.dv7-pill{display:inline-block;background:var(--soft,#f7f8fa);border:1px solid var(--line);border-radius:6px;font-size:10px;padding:2px 7px;margin:0 0 6px}
.dv7-section{border:1px solid var(--line,#e5e7eb);border-radius:14px;padding:23px;margin:0 0 22px;background:var(--panel,#fff)}
.dv7-titleline{display:flex;justify-content:space-between;gap:15px;align-items:flex-start;margin-bottom:18px}.dv7-titleline h2{font-size:21px;line-height:1.4;letter-spacing:-.04em;margin:0}.dv7-sub{font-size:12px;color:var(--sub);line-height:1.8}.dv7-picker{border:1px solid var(--line);border-radius:8px;font:inherit;font-size:12px;padding:8px;background:var(--panel);color:var(--text);max-width:190px}
.dv7-columns{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:17px 0}.dv7-card{border:1px solid var(--line);border-radius:12px;padding:19px;min-width:0}.dv7-card h3{font-size:13px;margin:0 0 9px;color:var(--sub)}.dv7-verdict{font-size:17px;font-weight:760;letter-spacing:-.025em;line-height:1.65;margin-bottom:14px}.dv7-card p{font-size:12px;line-height:1.9;margin:8px 0}.dv7-card ul{padding-left:18px;margin:9px 0;font-size:12px;line-height:1.9}.dv7-card li{margin:6px 0}.dv7-conditions{padding:13px;background:var(--soft);border-radius:9px;margin-top:15px;font-size:12px;line-height:1.85}.dv7-conditions strong{font-size:12px}
.dv7-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:14px 0}.dv7-metric{background:var(--soft);border-radius:10px;padding:13px 15px;min-width:0}.dv7-metric small{font-size:11px;display:block;color:var(--sub);line-height:1.7}.dv7-metric b{font-size:17px;line-height:1.5;display:block;margin:5px 0;overflow-wrap:anywhere;letter-spacing:-.02em}.dv7-metric a{font-size:10px;color:var(--blue)}
.dv7-details{border:1px solid var(--line);padding:0 15px;border-radius:10px;margin:13px 0}.dv7-details summary{cursor:pointer;font-size:13px;font-weight:720;padding:14px 0;line-height:1.6}.dv7-details[open] summary{border-bottom:1px solid var(--line)}.dv7-body{padding:14px 0;font-size:12px;line-height:1.85}.dv7-body p{margin:8px 0}.dv7-body a{color:var(--blue);overflow-wrap:anywhere}.dv7-table-wrap{overflow-x:auto}.dv7-table{width:100%;border-collapse:collapse;font-size:12px}.dv7-table th,.dv7-table td{padding:12px 9px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}.dv7-table th{font-weight:600;color:var(--sub)}
.dv7-notice{font-size:11px;color:var(--sub);line-height:1.85;margin:13px 0}.dv7-linkrow{display:flex;gap:9px;flex-wrap:wrap;margin:12px 0}.dv7-linkrow a{display:inline-block;border:1px solid var(--line);border-radius:8px;padding:8px 10px;color:var(--blue);text-decoration:none;font-size:11px}
.dv7-event{padding:12px 0;border-bottom:1px solid var(--line)}.dv7-event a{font-size:12px}.dv7-event small{display:block;font-size:10px;color:var(--sub);margin-top:5px}
.dv7-section button:focus-visible,.dv7-row:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
@media(max-width:760px){.dv7-columns{grid-template-columns:1fr}.dv7-row{grid-template-columns:1fr 1fr}.dv7-row>div:first-child{grid-column:1/-1}.dv7-metrics{grid-template-columns:1fr 1fr}.dv7-row{gap:11px}}
@media(max-width:450px){.dv7-section{padding:16px}.dv7-card{padding:15px}.dv7-titleline{flex-direction:column}.dv7-picker{max-width:none;width:100%}.dv7-metric{padding:11px}.dv7-metric b{font-size:15px}.dv7-verdict{font-size:16px}.dv7-head{flex-direction:column}}
`;
const style=document.createElement('style');style.textContent=CSS;document.head.append(style);
const home=document.createElement('section');home.id='decision-v7-home';
const section=$('#candidateSection');if(section){section.hidden=true;section.parentElement.insertBefore(home,section)}
// Preserve legacy renderer hooks without running the old v6 assessment layer.
const duplicate=[...document.querySelectorAll('#candidateCards')];duplicate.slice(1).forEach(x=>x.remove());
const panel=document.createElement('section');panel.id='decision-v7-panel';panel.className='dv7-section';
$('#view-analysis')?.prepend(panel);
const oldResearch=$('#researchSection');if(oldResearch){const fold=document.createElement('details');fold.className='dv7-details';fold.innerHTML='<summary>기존 재무 가설·검증 안내 펼치기</summary>';oldResearch.parentElement.insertBefore(fold,oldResearch);fold.append(oldResearch)}
const fresh=()=>!error&&data&&elapsed(data.generated_at)<=data.max_age_hours&&elapsed(data.generated_at)>=-0.1;
const getRow=()=>data?.companies?.find(x=>x.symbol===selected);
const stateText=(r,key)=>!fresh()?'재수집 필요 · 판단 정지':(r[key]?.label||'자료 수집 실패');
function navigate(symbol){selected=symbol;renderDetail();const input=$('#search');if(input){input.value=symbol;input.dispatchEvent(new Event('input',{bubbles:true}));const row=$('#rows tr[data-symbol]');row?.click()}document.querySelector('[data-view=analysis]')?.click();panel.scrollIntoView({block:'start',behavior:'auto'})}
function renderHome(){
 const c=data?.counts||{};const r=(data?.companies||[]).filter(x=>market==='ALL'||x.market===market);
 home.innerHTML='<div class="dv7-head"><div><h2>지금 검토할까, 기다릴까?</h2><small>실제 수집 자료로 단기·장기 결론을 분리합니다. 훈련과 주문 기능은 없습니다.</small></div></div>'+
 '<div class="dv7-status '+(!fresh()?'bad':'')+'"><strong>'+(!fresh()?'최신 판단자료 확인 필요':'판단자료 수집 완료 · 추정치와 확정실적은 별개')+'</strong>'+esc(error||'수집 '+when(data?.generated_at)+' · 모든 가격 조건은 완료된 정규장 종가 기준')+'</div>'+
 '<div class="dv7-counts"><span>완료 시세 '+num(c.current_price,0)+'/10</span><span>예상 EPS '+num(c.forecasts,0)+'/10</span><span>목표가 분포 '+num(c.targets,0)+'/10</span><span>공식 소식 '+num(c.official_event_links||0,0)+'건</span></div>'+
 '<div class="dv7-toolbar">'+[['ALL','전체'],['KR','한국'],['US','미국']].map(([v,l])=>'<button type="button" data-dv-market="'+v+'" aria-pressed="'+(market===v)+'">'+l+'</button>').join('')+'</div>'+
 (r.length?r.map(x=>'<button type="button" class="dv7-row" data-dv-symbol="'+esc(x.symbol)+'"><div><strong>'+esc(x.name)+'</strong><small>'+esc(x.symbol)+' · '+esc(x.sector)+'</small><small>'+esc(money(x.price,x))+' · '+esc(x.price_session||'시세 없음')+' 종가</small></div><div><span class="dv7-pill">단기</span><div class="dv7-result">'+esc(stateText(x,'short'))+'</div><small>'+esc(x.short?.reasons?.[0]||'데이터 확인 필요')+'</small></div><div><span class="dv7-pill">장기</span><div class="dv7-result">'+esc(stateText(x,'long'))+'</div><small>'+esc(x.long?.reasons?.[0]||'데이터 확인 필요')+'</small></div></button>').join(''):'<div class="dv7-status">실제 판단자료를 불러오지 못했습니다. 잠시 후 다시 확인하세요.</div>')+
 '<p class="dv7-notice">관망·보류가 많아도 매수를 유도하기 위해 문턱값을 낮추지 않습니다. 각 결론은 공개한 규칙의 결과이며, 수익 예측·상승확률·개인 맞춤 매매 지시가 아닙니다.</p>';
 home.querySelectorAll('[data-dv-symbol]').forEach(b=>b.onclick=()=>navigate(b.dataset.dvSymbol));
 home.querySelectorAll('[data-dv-market]').forEach(b=>b.onclick=()=>{market=b.dataset.dvMarket;renderHome()});
}
function renderDetail(){
 const r=getRow();if(!r){panel.innerHTML='<div class="dv7-status">기업을 선택해 주세요.</div>';return}
 const f=r.forecasts||{},t=r.targets||{},q=r.technical||{},b=r.balance||{},proof=r.official_history||{},sources=r.sources||{};
 const link=(u,title)=>safe(u)?'<a target="_blank" rel="noopener noreferrer" href="'+safe(u)+'">'+esc(title)+' ↗</a>':'';
 const list=a=>'<ul>'+(a||[]).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>';
 const assessment=(kind,name)=>{const a=r[kind]||{};return '<div class="dv7-card"><h3>'+name+' · '+esc(a.horizon||'기간 확인')+'</h3><div class="dv7-verdict">'+esc(stateText(r,kind))+'</div>'+list(a.reasons)+'<div class="dv7-conditions"><strong>판단을 바꿀 조건</strong>'+list(a.change_conditions)+'</div></div>'};
 const metric=(title,value,note,href)=>'<div class="dv7-metric"><small>'+esc(title)+'</small><b>'+esc(value)+'</b><small>'+esc(note)+'</small>'+link(href,'숫자 비교')+'</div>';
 const epsRows=[['0y','이번 회계연도',f.current_fy||{}],['+1y','다음 회계연도',f.next_fy||{}]];
 const events=[...(r.official_events||[]),...(r.news||[])];
 const eventhtml=events.length?events.map(e=>'<div class="dv7-event">'+link(e.url,e.title)+'<small>'+esc(e.published||'시각 미상')+' · '+esc(e.source||'제공처 기사 목록')+'</small><small>자료 발행 여부만 확인 · 주가 상승/하락 원인 판정 아님</small></div>').join(''):'<p>최근 공식 소식/기사 연결을 확보하지 못했습니다. 이를 호재 없음이나 악재 없음으로 해석하지 않습니다.</p>';
 const calendar=r.earnings_calendar||{},earn=(calendar['Earnings Date']||[]).join(' ~ ')||'미제공';
 panel.innerHTML='<div class="dv7-titleline"><div><h2>'+esc(r.name)+' <span class="dv7-sub">'+esc(r.symbol)+'</span></h2><div class="dv7-sub">판단가격 '+esc(money(r.price,r))+' · '+esc(r.price_session||'미확인')+' 정규장 종가<br>예상치 수집 '+esc(when(r.collected_at))+' · '+esc(r.sector)+'</div></div><select id="dv7-select" class="dv7-picker" aria-label="분석할 기업">'+(data?.companies||[]).map(x=>'<option value="'+esc(x.symbol)+'" '+(x.symbol===selected?'selected':'')+'>'+esc(x.name)+'</option>').join('')+'</select></div>'+
 (!fresh()?'<div class="dv7-status bad">자료가 오래됐거나 재조회에 실패해 매수 판단 표시를 중지했습니다.</div>':'')+
 '<div class="dv7-columns">'+assessment('short','단기')+assessment('long','장기')+'</div>'+
 '<div class="dv7-head"><h2 style="font-size:16px">결론을 만든 실제 숫자</h2></div><div class="dv7-metrics">'+
 metric('다음 회계연도 예상 EPS',money(f.next_fy?.avg,r),(f.analysts!=null?num(f.analysts,0)+'명 추정 · ':'')+'공식 확정실적 아님',sources.estimates)+
 metric('예상 EPS 30일 변화',pct(f.eps_revision30_pct),'같은 +1y 추정값의 상향·하향',sources.estimates)+
 metric('다음 회계연도 예상 PER',f.next_fy_pe!=null?num(f.next_fy_pe,2)+'배':'—','종가 ÷ +1y 예상 EPS · 12M PER 아님',sources.estimates)+
 metric('애널리스트 목표가 중앙값',money(t.median,r),'적정가치가 아닌 시장 의견',sources.estimates)+
 metric('중앙 목표가까지 가격 차이',pct(t.median_gap_pct),'확률 가중 기대수익률 아님',sources.estimates)+
 metric('조건부 재검토 가격',money(t.review_price_ceiling,r),'중앙 목표가까지 20% 여유 가정',sources.estimates)+
 metric('20일 평균 대비 거래량',q.volume_ratio!=null?num(q.volume_ratio,2)+'배':'—','당일 미완료 거래량 제외',sources.history)+
 metric('20일 시장 대비 성과',q.relative20_pp!=null?num(q.relative20_pp,2)+'%p':'—',(r.market==='KR'?'KOSPI':'SPY')+' 대비 · 배당 제외',sources.history)+
 metric('순차입금 / EBITDA',b.net_debt_ebitda!=null?num(b.net_debt_ebitda,2)+'배':'산업별 별도 검토','기간·계열사·리스 범위 확인 필요',sources.balance)+'</div>'+
 '<details class="dv7-details"><summary>예상 EPS 범위·목표가·가격 조건의 계산식</summary><div class="dv7-body"><div class="dv7-table-wrap"><table class="dv7-table"><thead><tr><th>EPS 기준</th><th>하단</th><th>평균</th><th>상단</th><th>분석가</th></tr></thead><tbody>'+epsRows.map(([_key,title,x])=>'<tr><td>'+title+'</td><td>'+money(x.low,r)+'</td><td>'+money(x.avg,r)+'</td><td>'+money(x.high,r)+'</td><td>'+num(x.numberOfAnalysts,0)+'</td></tr>').join('')+'</tbody></table></div><p>0y 결산일(제공처): '+esc(f.current_fy_end_provider||'미상')+' · +1y 표기(1년 후 추정): '+esc(f.next_fy_end_inferred||'미상')+'</p><p>목표가 하단 '+money(t.low,r)+' / 중앙 '+money(t.median,r)+' / 상단 '+money(t.high,r)+' · 의견 수 '+num(t.analysts,0)+'명</p><p><strong>가격 대기 조건:</strong> 목표가 중앙값 ÷ 1.20 = '+money(t.review_price_ceiling,r)+'. 기업가치가 확정됐다는 뜻이 아니라, 목표가가 유지될 때 20% 가격 여유를 요구하는 필터입니다.</p><p>목표가 범위는 신뢰구간·최대손실·미래 보장가격이 아닙니다. 개별 리포트 날짜가 제공되지 않아 오래된 전망이 섞였는지 독립 확인이 필요합니다.</p><p>'+esc(f.basis||'EPS 조정 기준 미확인')+'</p></div></details>'+
 '<details class="dv7-details"><summary>단기 가격·거래량·손익비와 위험 기준</summary><div class="dv7-body"><p>20일 평균 '+money(q.ma20,r)+' · 60일 평균 '+money(q.ma60,r)+' · ATR14 '+money(q.atr14,r)+'</p><p>직전 20일 고점 '+money(q.prior_high20,r)+' · 직전 10일 저점 '+money(q.support10,r)+' · 1년 내 과거 저항 '+money(q.resistance_1y,r)+'</p><p>과거 지지·저항 기준 손익비 '+num(q.reward_risk,2)+'배 · 지지까지 하락폭 '+pct(q.support_loss_pct)+'</p><p>진입 검토 조건: 20일 고점 돌파, 종가 &gt; 20일선 &gt; 60일선, 평균 대비 거래량 1.5배 이상, 시장대비 강세, 손익비 2배 이상, 지지 이탈폭 8% 이내. 3일 내 실적발표 예상 또는 최근 분할이 있으면 보류합니다.</p><p>손절 체결가격과 손실폭은 보장되지 않습니다. 거래비용·갭 하락·유동성 위험이 남습니다.</p><p>실적발표 예정일: '+esc(earn)+' <strong>(제공처 예상 · 회사 확정 공지 아님)</strong></p><p>외국인·기관 순매수: '+esc(r.flow?.reason||'연결 전')+'</p>'+link(r.flow?.url,'투자자별 거래 자료 확인')+'</div></details>'+
 '<details class="dv7-details"><summary>회사 소식·공시와 미확인 촉매</summary><div class="dv7-body">'+eventhtml+'<p>이 자료는 발표 발생 여부를 보여줍니다. 좋은 뉴스/나쁜 뉴스, 예상 대비 실적 변화, 주가 영향은 자동 확정하지 않습니다.</p></div></details>'+
 '<details class="dv7-details"><summary>검증 범위·출처·아직 수집하지 못한 정보</summary><div class="dv7-body"><p>공식 과거 실적과 일치한 항목: '+esc((proof.matched||[]).join(', ')||'없음')+' · 확인 '+esc(when(proof.checked_at))+'</p><div class="dv7-linkrow">'+link(sources.official,'공식 과거 재무 원문')+link(sources.estimates,'예상 EPS·목표가')+link(sources.history,'일봉·거래량')+link(sources.balance,'부채·현금')+link(sources.cashflow,'현금흐름')+'</div>'+list(r.long?.remaining)+'<p>OpenDART 인증키: '+esc(data?.pending_setup?.DART_API_KEY==='configured'?'설정됨 (접속 성공과 별도)':'등록 대기')+'. '+link('https://github.com/Ohoredingdong/Notion/settings/secrets/actions','DART_API_KEY 안전하게 등록')+'</p>'+list((r.errors||[]).map(e=>e.field+': '+e.error))+'<p>'+esc(r.disclosure||'단일 제공처 데이터; 거래 전 독립 검증 필요')+'</p></div></details>'+
 '<p class="dv7-notice">판단 규칙 v7 · 백테스트 적중률이나 상승확률을 산정하지 않았습니다. 단기·장기 조건부 검토는 자동매수 신호가 아닙니다. 훈련은 기존 별도 위젯을 사용합니다.</p>';
 $('#dv7-select').onchange=e=>navigate(e.target.value);
}
async function reload(){if(busy)return;busy=true;try{const ctl=new AbortController();const timer=setTimeout(()=>ctl.abort(),18000);let res;try{res=await fetch('https://raw.githubusercontent.com/Ohoredingdong/Notion/main/stock-decision-data.json?t='+Date.now(),{cache:'no-store',signal:ctl.signal})}finally{clearTimeout(timer)}if(!res.ok)throw Error('판단자료 HTTP '+res.status);const next=await res.json();if(!Array.isArray(next.companies)||!next.version?.startsWith('decision-v7'))throw Error('판단자료 형식 불일치');data=next;error=null;if(!selected||!getRow())selected=data.companies[0]?.symbol;}catch(e){error='재조회 실패: '+e.message;}finally{busy=false;renderHome();renderDetail()}}
$('#rows')?.addEventListener('click',e=>{const row=e.target.closest('[data-symbol]');if(row){selected=row.dataset.symbol;renderDetail()}});
$('#reload')?.addEventListener('click',reload);
reload();setInterval(reload,15*60*1000);setInterval(()=>{renderHome();if(!fresh())renderDetail()},60*1000);
})();
