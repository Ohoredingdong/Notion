/* Official source reconciliation UI. No estimated probabilities; no financial inputs. */
(()=>{
'use strict';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safe=u=>{try{const x=new URL(u);return ['https:','http:'].includes(x.protocol)?esc(x.href):''}catch{return''}};
const states={match:'수치 일치',mismatch:'수치 차이',period_mismatch:'기간 다름',unit_mismatch:'단위 다름',basis_mismatch:'연결·별도 확인',definition_check:'FCF·CAPEX 정의 확인',account_check:'계정 기준 확인',widget_missing:'위젯 값 없음',unverified:'검증 보류',outdated:'검증 결과 오래됨',input_changed:'새 데이터 재검증 대기'};
const special=new Set(['mismatch','period_mismatch','unit_mismatch','basis_mismatch','definition_check','account_check']);
const number=(v,d=2)=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('ko-KR',{maximumFractionDigits:d});
const when=v=>{const d=new Date(v||'');return Number.isFinite(d.getTime())?d.toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false})+' KST':'미확인'};
const age=v=>{const d=Date.parse(v||'');return Number.isFinite(d)?(Date.now()-d)/3600000:Infinity};
let report=null,baseline=null,selected=null,fetchError=null,busy=false,renderPending=false;
const FIELDS=['revenue','revenue_growth','operating_income','operating_margin','net_income','eps','capex','fcf'];
const style=document.createElement('style');style.textContent=`
.official-status{margin:0 24px 16px;padding:12px 14px;border:1px solid var(--line,#e5e7eb);border-radius:10px;display:flex;gap:10px;align-items:center;font-size:12px;background:var(--soft,#f6f7f9);color:var(--text,#26313e);line-height:1.7}.official-status strong{font-size:12px}.official-status .a-link{margin-left:auto;white-space:nowrap}.official-status.problem{border-color:#bb674b}.official-status small{display:block;color:var(--sub,#687382);font-size:11px}
.official-section{margin:20px 0 26px;padding:22px;border:1px solid var(--line,#e5e7eb);border-radius:14px;background:var(--panel,#fff);color:var(--text,#26313e)}.official-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:15px}.official-heading h3{margin:0;font-size:17px;letter-spacing:-.02em}.official-intro{margin:9px 0 15px;font-size:12px;line-height:1.85;color:var(--sub,#687382)}.a-link{color:var(--blue,#3663a7);text-decoration:none;font-weight:650;font-size:12px;background:transparent;border:0;padding:3px;cursor:pointer}.a-link:hover{text-decoration:underline}
.official-stats{display:flex;flex-wrap:wrap;gap:10px;margin:13px 0 18px}.official-stat{background:var(--soft,#f6f7f9);padding:8px 12px;border-radius:8px;font-size:12px}.official-stat b{margin-left:8px;font-size:15px}
.official-field{border-top:1px solid var(--line,#e5e7eb);padding:17px 0}.official-field-top{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:9px}.official-field-name{font-size:13px;font-weight:740}.official-pill{font-size:11px;border-radius:6px;border:1px solid var(--line,#e5e7eb);padding:3px 8px;white-space:nowrap;color:var(--sub,#687382);background:var(--soft,#f6f7f9)}.official-pill.good{color:#137350;border-color:#bfdfcf;background:#f0f9f4}.official-pill.check{color:#8a5124;border-color:#e5d2bc;background:#fff8ef}.official-pill.bad{color:#b94343;border-color:#e9b6b6;background:#fff4f4}
.official-values{display:grid;grid-template-columns:1fr 1fr;gap:12px}.official-value{min-width:0;padding:10px 12px;border-radius:8px;background:var(--soft,#f6f7f9)}.official-value small{font-size:11px;display:block;color:var(--sub,#687382)}.official-value strong{font-variant-numeric:tabular-nums;font-size:15px;display:block;margin-top:4px;overflow-wrap:anywhere}.official-value span{font-size:11px;display:block;color:var(--sub,#687382);margin-top:4px}.official-reason{font-size:12px;line-height:1.8;margin:10px 0 4px;color:var(--sub,#687382)}.official-change{font-size:12px;font-weight:680;color:#9b5934;line-height:1.8;margin:6px 0}.official-source{font-size:11px;line-height:1.8;margin-top:7px;color:var(--sub,#687382);overflow-wrap:anywhere}.official-source a{color:var(--blue,#3663a7)}.official-meta{font-size:11px;line-height:1.85;color:var(--sub,#687382);overflow-wrap:anywhere}.official-meta summary{font-size:11px!important}.official-log{border:1px solid var(--line,#e5e7eb);padding:14px;border-radius:10px;margin-top:14px;font-size:12px;line-height:1.85}.official-log p{margin:6px 0}.official-disclaimer{font-size:11px;line-height:1.9;border-top:1px solid var(--line,#e5e7eb);padding-top:12px;margin-top:15px;color:var(--sub,#687382)}
#researchDetails .claim-row .verify-more,#researchDetails .claim-row .release-proof{display:none!important}
@media(max-width:650px){.official-section{padding:17px 14px}.official-heading h3{font-size:16px}.official-values{gap:8px}.official-value{padding:10px}.official-value strong{font-size:13px}.official-status{margin:0 14px 14px;padding:11px 12px;align-items:flex-start}.official-status .a-link{font-size:11px}.official-heading{gap:8px}}
@media(prefers-color-scheme:dark){.official-pill.good{color:#94d4b9;background:#21372c;border-color:#345b46}.official-pill.check{color:#efd0a2;background:#3e3425;border-color:#655035}.official-pill.bad{color:#eab0b0;background:#3e2b2b;border-color:#744444}.official-change{color:#e0b17c}}
`;
document.head.appendChild(style);
function format(v,field,currency){
 if(v==null)return'—';
 if(field==='revenue_growth'||field==='operating_margin')return number(v,2)+'%';
 if(field==='eps')return (currency==='KRW'?'₩':'$')+number(v,2);
 if(currency==='KRW')return Math.abs(v)>=1e12?number(v/1e12,4)+'조 원':number(v/1e8,4)+'억 원';
 return Math.abs(v)>=1e9?'$'+number(v/1e9,4)+'B':'$'+number(v/1e6,4)+'M';
}
function outdated(){return !report||age(report.generated_at)>36||age(report.generated_at)<-1||Boolean(fetchError)}
function current(r){
 if(outdated())return false;
 const b=baseline?.rows?.find(x=>x.symbol===r.symbol);if(!b)return false;
 if(b.filing_period!==r.input_period)return false;
 return r.fields.every(f=>f.widget_currency===b.currency&&(b[f.field]==null?f.widget_value==null:Number(b[f.field])===Number(f.widget_value)));
}
function activeFields(r){return r.fields.map(f=>({...f,status:outdated()?'outdated':current(r)?f.status:'input_changed'}))}
function symbolFromDetail(){
 const title=$('#detail .heading h2')?.textContent||'';
 return report?.companies?.find(r=>title.includes(r.symbol))?.symbol||selected;
}
function level(s){return s==='match'?'good':s==='mismatch'?'bad':'check'}
function evidenceKinds(text){
 if(/FCF|현금흐름|현금 창출|잉여현금/.test(text))return['fcf'];
 if(/부채|차입|관세|규제|정책|실적 전망|가이던스|다음 분기/.test(text))return[];
 if(/매출|수요|고객/.test(text))return['revenue','revenue_growth'];
 if(/이익률|영업이익|경쟁 우위/.test(text))return['operating_income','operating_margin'];
 if(/PER|주가 배수|기업가치/.test(text))return['eps'];
 return[];
}
function applyClaimLabels(r){
 const fs=activeFields(r);
 document.querySelectorAll('#researchDetails .claim-row').forEach(el=>{
  const badge=el.querySelector('.evidence-badge'),text=el.querySelector('.claim-text')?.textContent||'';
  if(!badge)return;
  const keys=evidenceKinds(text),matches=keys.filter(k=>fs.find(f=>f.field===k)?.status==='match');
  const label=keys.length?'과거 원문 대조 '+matches.length+'/'+keys.length:'미래·위험 가설 미검증';
  if(badge.textContent!==label)badge.textContent=label;
  badge.title='실제 재수집한 원문 금액의 일치 항목 수입니다. 미래 성장이나 주가 상승 확률이 아닙니다.';
 });
 const row=$('#researchDetails .evidence-row');
 if(row&&!row.dataset.v5){row.dataset.v5='true';row.innerHTML='<strong>검증 범위를 분리했습니다.</strong> 아래 대조표는 실제로 다시 가져온 공식 문서의 과거 숫자만 비교합니다. 고객 수요·경쟁력 지속·부채 위험·정책 영향은 별도 가설이며, 자료를 수집하지 않았으면 검증 완료로 표시하지 않습니다.';}
}
function renderSelected(){
 const research=$('#researchDetails');if(!research)return;
 selected=symbolFromDetail();
 const r=report?.companies?.find(x=>x.symbol===selected);
 let section=$('#officialComparison');
 if(!section){section=document.createElement('section');section.className='official-section';section.id='officialComparison';research.parentElement.insertBefore(section,research);}
 if(!r){section.innerHTML='<div class="official-heading"><h3>공식 공시 자동 대조</h3></div><p class="official-intro">'+(fetchError?'검증 결과를 읽지 못했습니다. 오래된 값을 새 검증 결과로 표시하지 않습니다.':'기업을 선택하면 원문 숫자·차이·확인 방법이 표시됩니다.')+'</p>';return;}
 const fs=activeFields(r),good=fs.filter(x=>x.status==='match').length,different=fs.filter(x=>special.has(x.status)).length;
 section.innerHTML='<div class="official-heading"><h3>'+esc(r.name)+' · 공식 원문 대조</h3><button class="a-link" type="button" data-audit-refresh>결과 다시 읽기 ↻</button></div>'+
 '<p class="official-intro">대상 '+esc(r.input_period)+' 연간 재무정보 · 원문 재조회 '+esc(when(r.checked_at))+'<br>새로고침은 저장된 결과를 읽습니다. 서버 수집은 정기 작업으로 별도 실행됩니다.</p>'+
 '<div class="official-stats"><span class="official-stat">수치 일치<b>'+good+'</b></span><span class="official-stat">기준·금액 차이<b>'+different+'</b></span><span class="official-stat">보류·대기<b>'+(fs.length-good-different)+'</b></span></div>'+
 fs.map(f=>{
  const currency=f.widget_currency||'USD';
  const delta=f.difference!=null&&special.has(f.status)?'<p class="official-change">위젯 − 원문: '+esc(format(f.difference,f.field,currency))+(f.difference_pct!=null?' ('+number(f.difference_pct,4)+'%)':'')+'</p>':'';
  const why=f.status==='outdated'?'검증 결과가 오래됐거나 연결이 실패했습니다. 이전 일치를 현재 정상 상태로 간주하지 않습니다.':f.status==='input_changed'?'위젯 원시 숫자가 검증 이후 변경됐습니다. 다음 검증이 끝날 때까지 일치 표시를 보류합니다.':f.reason;
  const link=safe(f.source_url);
  return '<article class="official-field"><div class="official-field-top"><span class="official-field-name">'+esc(f.label)+'</span><span class="official-pill '+level(f.status)+'">'+esc(states[f.status]||f.status)+'</span></div>'+
  '<div class="official-values"><div class="official-value"><small>위젯 수치</small><strong>'+esc(format(f.widget_value,f.field,currency))+'</strong><span>'+esc(f.widget_period||'기간 미상')+'</span></div><div class="official-value"><small>공식 원문 수치</small><strong>'+esc(format(f.official_value,f.field,currency))+'</strong><span>'+esc(f.official_period||'원문 미확보')+'</span></div></div>'+delta+
  '<p class="official-reason">'+esc(why)+'</p>'+
  (link?'<div class="official-source"><a href="'+link+'" target="_blank" rel="noopener noreferrer">해당 공시·실적자료 원문 ↗</a> · '+esc(f.official_account||'')+'</div>':'')+
  '<details class="official-meta"><summary>정확한 숫자·단위·검증 이력</summary><div>위젯: '+esc(number(f.widget_value,8))+' / 원문: '+esc(number(f.official_value,8))+'<br>단위: '+esc(f.official_unit||currency)+' · 비교 허용오차: '+esc(number(f.tolerance,8))+'<br>원문 계정: '+esc(f.official_account||'미확인')+'<br>원문 조회: '+esc(when(f.fetched_at))+(f.formula?'<br>계산 구성: '+esc(JSON.stringify(f.formula)):'')+'<br>원문 파일 SHA-256: '+esc(f.document_sha256||'수집되지 않음')+'</div></details></article>';
 }).join('')+
 '<div class="official-log"><strong>원문 수집 경로와 남은 작업</strong>'+(r.source?'<p>'+esc(r.source.kind)+' · '+esc(r.source.period)+'</p>':'<p>이번 실행에서 신뢰할 수 있는 공식 숫자를 추출하지 못했습니다.</p>')+
 (r.attempts||[]).map(a=>'<p><b>'+esc(a.code)+'</b> — '+esc(a.message)+(safe(a.url)?' <a class="a-link" href="'+safe(a.url)+'" target="_blank" rel="noopener noreferrer">해당 출처 ↗</a>':'')+'</p>').join('')+
 ((r.attempts||[]).some(a=>a.code==='credential_required')?'<p>OpenDART 인증키를 한 번 연결하면 회사별 공시를 자동으로 탐색할 수 있습니다. 키는 채팅에 붙이지 말고 GitHub 저장소의 <b>DART_API_KEY</b> 비밀 설정에 저장하세요. <a class="a-link" href="https://opendart.fss.or.kr/" target="_blank" rel="noopener noreferrer">인증키 발급 ↗</a> · <a class="a-link" href="https://github.com/Ohoredingdong/Notion/settings/secrets/actions" target="_blank" rel="noopener noreferrer">안전한 키 설정 ↗</a></p>':'')+
 (r.previous_success?'<p>이전 성공: '+esc(when(r.previous_success.checked_at))+' / '+esc(r.previous_success.period)+' — 이번 결과로 재사용하지 않았습니다.</p>':'')+'</div>'+
 '<p class="official-disclaimer">기업 자체 실적발표·주총 참고서류는 최종 감사보고서와 다릅니다. 원문 숫자의 일치가 기업의 안전성, 미래 실적 또는 주가 상승확률을 보증하지 않습니다. 서로 다른 FCF 정의·결산일·EPS 기준은 자동으로 같다고 처리하지 않습니다.</p>';
 section.querySelector('[data-audit-refresh]')?.addEventListener('click',refresh);
 applyClaimLabels(r);
}
function renderGlobal(){
 let banner=$('#officialAuditStatus');if(!banner){banner=document.createElement('div');banner.id='officialAuditStatus';banner.className='official-status';$('#systemBanner')?.after(banner);}
 const active=report?.companies?.flatMap(r=>activeFields(r))||[],m=active.filter(x=>x.status==='match').length,d=active.filter(x=>special.has(x.status)).length;
 banner.className='official-status'+(outdated()||d?' problem':'');
 banner.innerHTML='<div><strong>'+(outdated()?'공시 검증 결과 확인 필요':'공시 자동 대조 · 일치 '+m+' / 차이 확인 '+d+' / 보류 '+(active.length-m-d))+'</strong><small>'+esc(fetchError||('검증한 기업 '+(report?.companies?.length||0)+'개 · '+when(report?.generated_at)))+'</small></div><button type="button" class="a-link" data-open-audit>대조표 보기 ›</button>';
 banner.querySelector('[data-open-audit]')?.addEventListener('click',()=>{document.querySelector('[data-view="analysis"]')?.click();renderSelected();$('#officialComparison')?.scrollIntoView({behavior:'smooth',block:'start'});});
}
function schedule(){if(renderPending)return;renderPending=true;setTimeout(()=>{renderPending=false;renderSelected();},40)}
async function refresh(){
 if(busy)return;busy=true;fetchError=null;
 try{
  const get=async path=>{const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),18000);try{const r=await fetch('./'+path+'?audit='+Date.now(),{cache:'no-store',signal:controller.signal});if(!r.ok)throw Error(path+' HTTP '+r.status);return await r.json()}finally{clearTimeout(timer)}};
  const values=await Promise.all([get('stock-official-audit.json'),get('stock-value-radar-data.json')]);report=values[0];baseline=values[1];
  if(!Array.isArray(report.companies))throw Error('검증 결과 형식 오류');
 }catch(e){fetchError='검증 결과 조회 실패: '+e.message;}
 finally{busy=false;renderGlobal();schedule();}
}
const research=$('#researchDetails');if(research)new MutationObserver(()=>schedule()).observe(research,{childList:true,subtree:false});
const detail=$('#detail');if(detail)new MutationObserver(()=>schedule()).observe(detail,{childList:true});
$('#rows')?.addEventListener('click',e=>{const row=e.target.closest('[data-symbol]');if(row){selected=row.dataset.symbol;schedule();}});
$('#reload')?.addEventListener('click',refresh);
refresh();setInterval(refresh,15*60*1000);setInterval(()=>{renderGlobal();schedule()},60000);
})();
