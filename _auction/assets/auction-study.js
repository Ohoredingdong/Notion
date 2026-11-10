/* A local-first study notebook. Monetary inputs and outputs are in 만원. */
(() => {
  'use strict';
  const Model = window.AuctionModel;
  const Format = window.AuctionFormat;
  const KEY = 'auction-study-v1';
  const TEXT_LIMIT = 20000;
  const PAGES = ['course','home','rights','money','area','notes','learn','simulation','process'];
  const PAGE_LABELS = {course:'학습',simulation:'모의경매',learn:'서류 연습',process:'경매 절차',home:'검토 요약',rights:'권리 분석',money:'투자금 계산',area:'지역·시세',notes:'최종 검토'};
  const CASE_LIMIT_MESSAGE = '최대 100개이므로 정리에서 노트를 백업·삭제한 뒤 추가하세요.';
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = n => (typeof n==='number'||typeof n==='string'&&n.trim()!=='')&&Number.isFinite(Number(n)) ? Number(n).toLocaleString('ko-KR',{maximumFractionDigits:2}) : '—';
  const amount = n => esc(Format.money(n));
  const money = n => {const value=Format.parts(n);return esc(value.text)+(value.unit?`<small>${esc(value.unit)}</small>`:'');};
  const paths = {
    book:'M4 4h6l2 2 2-2h6v15h-6l-2 2-2-2H4z M12 6v15',
    grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
    shield:'M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6z M8 12l3 3 5-6',
    calc:'M6 3h12v18H6z M9 7h6 M9 11h1 M14 11h1 M9 15h1 M14 15h1 M9 18h1 M14 18h1',
    pin:'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1116 0z M15 10a3 3 0 11-6 0 3 3 0 016 0',
    note:'M14 3H5v18h14V8z M14 3v6h5 M8 13h8 M8 17h6',
    arrow:'M5 12h14 M13 6l6 6-6 6', plus:'M12 5v14 M5 12h14',
    down:'M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5',
    check:'M5 12l4 4L19 6', clock:'M12 8v5l3 2 M21 12a9 9 0 11-18 0 9 9 0 0118 0',
    link:'M10 13a5 5 0 007 0l3-3a5 5 0 00-7-7l-2 2 M14 11a5 5 0 00-7 0l-3 3a5 5 0 007 7l2-2',
    info:'M12 11v6 M12 7h.01 M21 12a9 9 0 11-18 0 9 9 0 0118 0',
    leaf:'M20 4c0 10-4 16-10 16a6 6 0 01-6-6C4 8 10 4 20 4z M4 20L16 8',
  };
  const icon = (key, size=20) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${(paths[key]||paths.note).split(' M').map((p,i)=>`<path d="${i?'M':''}${p}"/>`).join('')}</svg>`;
  const steps = [
    {id:'rights', n:'01', icon:'shield', name:PAGE_LABELS.rights, desc:'등기·임차인·점유 근거를 기록하세요.', short:'등기 · 임차인 · 점유'},
    {id:'money', n:'02', icon:'calc', name:PAGE_LABELS.money, desc:'낙찰가·대출·비용으로 현금과 손익을 계산하세요.', short:'입찰보증금 · 대출 · 부대비용'},
    {id:'area', n:'03', icon:'pin', name:PAGE_LABELS.area, desc:'비교 거래와 수요·공급 근거를 기록하세요.', short:'실거래 · 수요 · 공급'},
    {id:'notes', n:'04', icon:'note', name:'최종 검토', desc:'내 입찰 상한과 보류 사유 정리.', short:'손익 · 리스크 · 나의 결론'},
  ];
  const rights = [
    ['물건·서류 대조', '주소·동호수·면적·지분을 명세서·현황조사서·감정평가서·최신 등기와 대조하세요.'],
    ['소멸·인수 권리', '말소기준권리 후보의 종류·접수일과 매각 조건을 대조하세요. 선순위 가처분·가등기·법정지상권은 날짜만으로 판단하지 마세요.'],
    ['임차보증금', '점유·전입·확정일자·배당요구·예상 배당액을 확인하세요. 전입일만으로 인수액을 정하지 마세요.'],
    ['점유·인도', '현황조사와 현장을 대조하고 점유자·인도 시점·적법한 절차·명도비를 기록하세요.'],
    ['체납·인수 비용', '관리비의 공용·전유 구분과 특별매각조건·추가 인수액을 확인해 계산에 반영하세요.'],
    ['건물·토지 예외', '대지권·토지별도등기·위반건축·유치권 주장·공유지분·정비사업을 확인하세요. 불명확한 항목은 전문가에게 확인하세요.'],
  ];
  const statuses = [['unknown','미확인'],['checking','확인 중'],['clear','확인 완료'],['risk','위험 발견']];
  const options = (items, selected) => items.map(([v,t])=>`<option value="${v}" ${v===selected?'selected':''}>${t}</option>`).join('');
  const id = () => 'case-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,7);
  function newCase(demo=false) {
    const finance=Model.defaults();
    if(!demo)for(const key of Object.keys(finance))finance[key]='';
    return {id:id(),demo,name:demo?'처음 배우는 아파트 경매':'새 경매 물건',address:demo?'연습용 아파트 · 전용 84㎡':'',number:demo?'연습 사례 01':'',area:demo?84:'', date:'', finance,
      rights:rights.map(()=>({status:'unknown',evidence:''})), timeline:{base:'',move:'',fixed:'',demand:''},
      region:{station:'',supply:'unknown',demand:'unknown',evidence:'',checked:'',comps:[{price:'',area:'',date:'',source:''},{price:'',area:'',date:'',source:''},{price:'',area:'',date:'',source:''}]},
      thesis:'',questions:'',conclusion:'hold',updated:''};
  }
  const requestedPage=()=>{const view=new URLSearchParams(location.search).get('view');return PAGES.includes(view)?view:'course';};
  let storageOK=true, storageConflict=false, storedSnapshot=null, pristineNotebook=false, state, page=requestedPage(), homePanel='progress', rightsStep=0, toastTimer;
  try {
    const raw=storedSnapshot=localStorage.getItem(KEY);
    if(raw){const x=JSON.parse(raw);if(!validImport(x))throw Error('Invalid notebook');state=x;}
    else pristineNotebook=raw===null;
  }catch(e){storageOK=false;}
  if(!state){const c=newCase(true);state={version:1,active:c.id,cases:[c]};}
  // Merge defaults so older locally saved fields can grow without deleting notes.
  state.cases=state.cases.map(c=>{const d=newCase(false);return {...d,...c,finance:{...d.finance,...c.finance},region:{...d.region,...c.region},timeline:{...d.timeline,...c.timeline}};});
  if(!state.cases.some(c=>c.id===state.active))state.active=state.cases[0].id;
  const current=()=>state.cases.find(c=>c.id===state.active);
  const toast=t=>{clearTimeout(toastTimer);const notice=$('#toast');if(!notice)return;notice.textContent=t;notice.hidden=false;toastTimer=setTimeout(()=>notice.hidden=true,3500);};
  function openPage(next,{replace=false,focus=true}={}){
    if(!PAGES.includes(next))return;
    page=next;
    const url=new URL(location.href);url.searchParams.set('view',page);
    if(url.href!==location.href)history[replace?'replaceState':'pushState']({view:page},'',url);
    render();
    if(focus){window.scrollTo({top:0,behavior:'instant'});$('h1')?.setAttribute('tabindex','-1');$('h1')?.focus({preventScroll:true});}
  }
  const course=window.AuctionCourse.create({openPage});
  const learning=window.AuctionStudyLearning.create({openPage});
  const simulation=window.AuctionSimulation.create({openPage,copyToNotebook:copyScenario});
  const processDesk=window.AuctionProcess.create({openPage});
  function copyScenario(scenario){
    if(state.cases.length>=100){toast(CASE_LIMIT_MESSAGE);return;}
    const item=newCase(true);
    item.name=scenario.title+' · 모의 분석';item.address=scenario.address;
    item.number='가상 연습 '+scenario.id;item.area=scenario.area;
    item.finance={...Model.defaults(),...scenario.defaults};
    item.region.comps=scenario.comparables.slice(0,3).map(row=>({price:String(row.price),area:String(row.area),date:row.date,source:'가상 연습 자료 · '+row.description}));
    while(item.region.comps.length<3)item.region.comps.push({price:'',area:'',date:'',source:''});
    item.thesis='모의경매에서 복사한 가상 학습 사례입니다. '+(scenario.practiceNote||'');
    item.questions='원문 서류와 실제 조사 결과가 아닙니다. 권리 확인 상태는 직접 다시 기록하세요.\n'+(scenario.answer?.nextChecks||[]).join('\n');
    state.cases.push(item);state.active=item.id;const saved=save();openPage('money');
    toast(saved?'연습 노트를 추가했어요.':unsavedMessage('가상 분석 노트를 이 화면에 만들었어요.'));
  }
  function save(){
    pristineNotebook=false;
    current().updated=new Date().toISOString();
    const saved=writeState(state);
    updateStorageStatus();
    return saved;
  }
  function writeState(nextState){
    if(!storageOK)return false;
    try{
      if(localStorage.getItem(KEY)!==storedSnapshot)return failStorage(true);
      const serialized=JSON.stringify(nextState);
      localStorage.setItem(KEY,serialized);storedSnapshot=serialized;
      return true;
    }catch(e){return failStorage(false);}
  }
  function storageWarning(){return storageConflict?'다른 탭에서 기록이 바뀌어 저장을 멈췄으니 현재 기록을 백업하세요.':'저장소를 사용할 수 없거나 기록을 읽지 못했으니 현재 내용을 백업하세요.';}
  function updateStorageStatus(){
    const el=$('#saveStatus');if(el)el.textContent=storageOK?'이 기기에 저장됨':'저장 불가 · 백업 필요';
    const warning=$('#storageWarning');if(warning){warning.hidden=storageOK;warning.className=storageOK?'':'notice warning';warning.textContent=storageOK?'':storageWarning();}
    const deletionError=$('#deleteCaseError');if(deletionError){deletionError.hidden=storageOK;deletionError.textContent=storageOK?'':storageConflict?'다른 탭에서 기록이 바뀌어 삭제를 멈췄으니 현재 기록을 백업하세요.':'저장할 수 없어 삭제를 멈췄으니 현재 기록을 백업하세요.';}
    const deletionButton=$('#deleteCaseSubmit');if(deletionButton)deletionButton.disabled=!storageOK;
  }
  function failStorage(conflict){
    storageOK=false;storageConflict=conflict;pristineNotebook=false;updateStorageStatus();
    toast(conflict?'다른 탭의 변경으로 저장을 멈췄으니 현재 기록을 백업하세요.':'기기 저장에 실패했으니 현재 기록을 백업하세요.');
    return false;
  }
  function unsavedMessage(action){return action+' ('+(storageConflict?'다른 탭 충돌':'기기 저장 중지')+' · 백업 필요)';}
  window.addEventListener('storage',event=>{
    if(!storageOK||(event.key!==KEY&&event.key!==null))return;
    try{if(event.storageArea===localStorage&&localStorage.getItem(KEY)!==storedSnapshot)failStorage(true);}
    catch(_){failStorage(false);}
  });
  const complete = c => c.rights.filter(r=>r.status==='clear'&&r.evidence.trim()).length;
  function regionEvidence(c){const seen=new Set();return c.region.comps.filter(x=>{const key=[x.price,x.area,x.date,x.source.trim()].join('|');if(!(Number(x.price)>0&&Number(x.area)>0&&x.date&&x.source.trim())||seen.has(key))return false;seen.add(key);return true;});}
  function verdict(c,r){
    const reasons=[];
    const risks=c.rights.filter(x=>x.status==='risk').length;
    if(risks)reasons.push(`권리·점유 위험 ${risks}건의 해소 방법이 필요해요.`);
    const pending=rights.length-complete(c)-risks;
    if(pending)reasons.push(`권리분석 ${pending}건의 확인 또는 근거 기록이 남았어요.`);
    if(!r.valid)reasons.push('투자금 계산의 입력 오류를 먼저 확인하세요.');
    else{if(r.cashGap>0)reasons.push(`준비 현금이 ${amount(r.cashGap)} 부족해요.`);if(r.depositGap>0)reasons.push(`입찰 전 보증금 ${amount(r.deposit)}을 준비하세요.`);if(r.downsideProfit<0)reasons.push('보수적인 매도가에서는 손실이 예상돼요.');if(Model.compareAmounts(r.profit,r.input.targetProfit)<0)reasons.push(`기준 손익이 목표보다 ${amount(r.input.targetProfit-r.profit)} 부족해요.`);if(!Number(c.finance.saleTax))reasons.push('매도 세금이 0원이에요. 적용 세금을 별도로 확인하세요.');}
    if(regionEvidence(c).length<2)reasons.push('출처·거래일을 갖춘 비교 실거래를 2건 이상 기록하세요.');
    if(!(Number(c.area)>0))reasons.push('물건의 전용면적을 입력하세요.');
    if(c.region.supply==='unknown'||c.region.demand==='unknown'||!c.region.evidence.trim()||!c.region.checked)reasons.push('지역 수요·공급의 확인일과 근거가 필요해요.');
    if(c.region.supply==='high'||c.region.demand==='weak')reasons.push('공급 부담 또는 약한 거래 수요를 재검토하세요.');
    return {title:reasons.length?'검토 보류':'추가 검토 가능',tone:risks?'red':reasons.length?'amber':'sage',reasons,description:reasons.length?'남은 확인 근거를 기록하세요.':'입찰 전 최신 서류와 개별 조건을 다시 확인하세요.'};
  }
  function field(label,key,value,help='',type='number',extra=''){
    return `<div class="field"><label for="f-${key}">${label}</label><div class="input-wrap${type==='number'?' has-unit':''}"><input id="f-${key}" data-field="${key}" type="${type}" value="${esc(value)}" ${type==='text'?`maxlength="${TEXT_LIMIT}"`:''} ${type==='number'?'min="0" step="any" inputmode="decimal"':''} ${extra}>${type==='number'?`<span class="input-unit">${key==='area'?'㎡':'만원'}</span>`:''}</div>${help?`<p class="field-help">${help}</p>`:''}</div>`;
  }
  function calcField(label,key,c,help='',unit='만원'){
    return `<div class="field"><label for="cash-${key}">${label}</label><div class="input-wrap has-unit"><input id="cash-${key}" data-finance="${key}" type="number" min="0" step="any" inputmode="decimal" value="${esc(c.finance[key])}"><span class="input-unit">${unit}</span></div>${help?`<p class="field-help">${help}</p>`:''}</div>`;
  }
  const navButton=(p,n,i)=>`<button type="button" class="nav-item ${page===p?'active':''}" data-page="${p}" ${page===p?'aria-current="page"':''}>${icon(i)}<span>${n}</span>${['home','learn','simulation','process'].includes(p)?'':`<span class="nav-index">${steps.find(s=>s.id===p)?.n||''}</span>`}</button>`;
  function resultPanel(c,r){return `<section class="panel"><div class="panel-header"><div><h2 class="panel-title">필요한 현금</h2><p class="panel-subtitle">입력한 금액으로 계산해요 · 만원</p></div>${icon('calc')}</div><div class="panel-body" data-results aria-live="polite">${cashContent(c,r)}</div></section>`;}
  function cashContent(c,r){
    if(!r.valid)return `<div class="form-error" role="alert">${r.errors.map(esc).join('<br>')}</div>`;
    return `<div class="cash-highlight"><div class="cash-caption">필요 현금 · 예비비 포함</div><div class="cash-number" data-result="cashNeeded">${money(r.cashNeeded)}</div><div class="cash-caption">대출 ${amount(c.finance.loan)} 실행 가정</div></div><div class="cost-stack"><div class="cost-row"><span>예상 낙찰가</span><strong>${amount(c.finance.bid)}</strong></div><div class="cost-row"><span>취득·보유 비용</span><strong>+ ${amount(r.costs)}</strong></div><div class="cost-row"><span>대출 실행액</span><strong>− ${amount(c.finance.loan)}</strong></div><div class="cost-row"><span>예비비</span><strong>+ ${amount(c.finance.reserve)}</strong></div><div class="cost-row total"><span>필요 현금</span><strong>${amount(r.cashNeeded)}</strong></div></div>${r.cashGap>0?`<p class="notice warning">준비 현금이 <strong data-result="cashGap">${amount(r.cashGap)}</strong> 부족해요.</p>`:''}<p class="field-help">입찰 전 보증금 ${amount(r.deposit)}이 필요해요.${r.depositGap>0?` <strong data-result="depositGap">준비 현금보다 ${amount(r.depositGap)} 부족해요.</strong>`:''}</p><details><summary>보증금 계산</summary><p class="field-help">보증금은 낙찰대금의 일부이므로 필요 현금에 중복해서 더하지 않아요.${Model.compareAmounts(r.deposit,r.cashNeeded)>0?' 순투입 현금보다 큰 보증금을 먼저 준비해야 해요.':''}</p></details><button class="text-link" data-page="money">투자금 계산 ${icon('arrow',16)}</button>`;
  }
  function decisionPanel(c,r,compact=false,expanded=false){const v=verdict(c,r);if(compact)return `<section class="panel decision-panel rights-verdict"><div class="panel-body"><div class="rights-verdict-heading"><h2 class="decision-title">${v.title}</h2><span class="badge ${v.tone}">${v.reasons.length?`확인 ${v.reasons.length}건`:'근거 기록됨'}</span></div><p class="decision-text">${esc(v.reasons[0]||v.description)}</p><details class="decision-details" ${expanded?'open':''}><summary>상세 근거</summary><ul class="reason-list">${v.reasons.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><button class="text-link" data-page="notes">최종 검토 ${icon('arrow',15)}</button></details></div></section>`;return `<section class="panel decision-panel"><div class="panel-body"><span class="badge ${v.tone}">${icon('clock',13)} 검토 신호</span><h2 class="decision-title">${v.title}</h2><p class="decision-text">${v.description}</p><ul class="reason-list">${v.reasons.slice(0,3).map(x=>`<li>${esc(x)}</li>`).join('')}</ul><button class="text-link" data-page="notes">사유 보기 ${icon('arrow',16)}</button></div></section>`;}
  function displayMoney(value){return Format.parts(value).valid?amount(value):'미입력';}
  function nextStudy(c,r){
    if(complete(c)<rights.length)return {page:'rights',title:'권리 확인',description:'서류 예시를 보고 근거를 기록하세요.'};
    if(!r.valid||!Number(c.finance.saleTax))return {page:'money',title:'비용·세금 확인',description:'빠진 비용과 자금 조건을 확인하세요.'};
    if(regionEvidence(c).length<2||c.region.supply==='unknown'||c.region.demand==='unknown')return {page:'area',title:'실거래 확인',description:'가격·면적·계약일·출처를 기록하세요.'};
    return {page:'notes',title:'최종 검토',description:'보류 사유와 입찰 전 질문을 검토하세요.'};
  }
  function home(c,r){
    const v=verdict(c,r),next=nextStudy(c,r),done=complete(c),taxMissing=!Number(c.finance.saleTax);
    const stepStatus={rights:`${done} / 6 근거 기록`,money:r.valid?'계산값 입력됨':'계산값 확인 필요',area:`비교 거래 ${regionEvidence(c).length}건`,notes:c.thesis.trim()?'검토 메모 작성됨':'나의 판단 기록하기'};
    return `<div class="home-screen"><section class="overview-verdict ${v.reasons.length?'pending':'reviewed'}"><div><span class="verdict-label">현재 검토 상태</span><h2 class="verdict-heading">${v.reasons.length?'검토 보류':'추가 검토 가능'}</h2><p class="verdict-description">${v.reasons.length?`${v.reasons.length}개 확인이 남았어요: ${esc(v.reasons[0])}`:'입찰 전 최신 서류와 자금 조건을 다시 확인하세요.'}</p></div><button class="button primary" data-page="${next.page}">${next.title} ${icon('arrow',17)}</button></section>
      <div class="overview-metrics"><section class="overview-metric"><span class="metric-label">필요 현금</span><strong class="overview-value" data-result="cashNeeded">${displayMoney(r.cashNeeded)}</strong><p class="metric-subline">대출 전 입찰보증금 <strong>${displayMoney(r.deposit)}</strong></p><span class="metric-note">예상 순투입 현금 · 예비비 포함</span></section><section class="overview-metric"><span class="metric-label">보수적 매도 손익</span><strong class="overview-value ${r.downsideProfit<0?'loss':''}" data-result="downsideProfit">${displayMoney(r.downsideProfit)}</strong><p class="metric-subline">매도가 ${displayMoney(r.valid?r.input.downside:NaN)} 가정</p><span class="badge ${taxMissing?'amber':'neutral'}">${taxMissing?'매도 세금 미반영':'입력한 매도 세금 반영'}</span></section><section class="overview-metric"><span class="metric-label">권리 확인 근거</span><strong class="overview-value">${done}<small> / 6건</small></strong><p class="metric-subline">${done===6?'각 항목에 직접 근거를 기록했어요.':`${6-done}건의 상태 또는 근거를 확인하세요.`}</p><button class="text-link" data-page="rights">근거 보기 ${icon('arrow',15)}</button></section></div>
      <nav class="home-tabs" aria-label="대시보드 상세 보기">${[['progress','검토 순서'],['reasons','보류 사유 '+v.reasons.length],['cash','현금 계산']].map(([key,label])=>`<button type="button" data-home-panel="${key}" aria-pressed="${homePanel===key}" aria-controls="home-${key}">${label}</button>`).join('')}</nav><div class="overview-layout"><div class="main-column"><section id="home-progress" class="panel home-panel home-panel-progress ${homePanel==='progress'?'home-tab-active':''}"><div class="panel-header"><div><h2 class="panel-title">검토 순서</h2><p class="panel-subtitle">각 단계에서 확인한 내용이 최종 검토에 모입니다.</p></div></div><div class="analysis-progress">${steps.map(s=>`<button class="analysis-step" data-page="${s.id}"><span class="analysis-step-index">${s.n}</span><span class="analysis-step-copy"><strong>${s.name}</strong><span>${s.desc}</span></span><span class="analysis-step-status">${stepStatus[s.id]}</span><span class="analysis-step-arrow">${icon('arrow',18)}</span></button>`).join('')}</div></section>
      <section id="home-reasons" class="panel overview-tasks home-panel home-panel-reasons ${homePanel==='reasons'?'home-tab-active':''}"><div class="panel-header"><h2 class="panel-title">보류 사유</h2><span class="badge ${v.tone}">${v.reasons.length}개 사유</span></div><div class="panel-body">${v.reasons.length?v.reasons.map((reason,i)=>`<div class="task-item"><span class="task-label">${String(i+1).padStart(2,'0')}</span><p>${esc(reason)}</p></div>`).join(''):'<p>입력한 조건의 확인 항목을 채웠어요. 이 결과는 실제 권리의 안전성이나 수익을 보장하지 않습니다.</p>'}</div></section>
      <div class="overview-caveat">${icon('info',18)}<p>${c.demo?'현재 숫자는 가상 연습 사례입니다. ':''}가격·대출·비용을 바꾸면 손익도 바뀝니다. 원문 서류와 실제 조달 조건은 직접 확인해 기록하세요.</p></div></div>
      <aside class="side-column"><section id="home-cash" class="panel overview-summary home-panel home-panel-cash ${homePanel==='cash'?'home-tab-active':''}"><div class="panel-header"><h2 class="panel-title">현금 계산</h2></div><div class="panel-body">${r.valid?`<div class="cost-row"><span>예상 낙찰가</span><strong>${displayMoney(r.input.bid)}</strong></div><div class="cost-row"><span>취득·보유 부대비용</span><strong>+ ${displayMoney(r.costs)}</strong></div><div class="cost-row"><span>대출 실행 가정</span><strong>− ${displayMoney(r.input.loan)}</strong></div><div class="cost-row"><span>현금 예비비</span><strong>+ ${displayMoney(r.input.reserve)}</strong></div><div class="cost-row total"><span>예상 순투입 현금</span><strong class="cash-number" data-result="cashNeeded">${money(r.cashNeeded)}</strong></div><p class="field-help">보증금은 낙찰대금의 일부입니다. 총비용에 중복해서 더하지 않아요.</p>`:'<p class="form-error">투자금 계산의 빈칸과 오류를 먼저 확인하세요.</p>'}<button class="text-link" data-page="money">계산 ${icon('arrow',15)}</button></div></section><section class="panel"><div class="panel-header"><h2 class="panel-title">다음 확인</h2></div><div class="panel-body"><p class="next-action-title">${next.title}</p><p class="panel-subtitle">${next.description}</p><button class="button" data-page="${next.page}">확인 ${icon('arrow',16)}</button></div></section><section class="panel"><div class="panel-body"><h2 class="panel-title">원문 서류 찾기</h2>${sourceLinks()}</div></section></aside></div></div>`;
  }
  function sourceLinks(){return `<div class="source-links"><a href="https://www.courtauction.go.kr/" target="_blank" rel="noopener noreferrer">법원경매정보 <span>매각 서류</span>${icon('link',14)}</a><a href="https://www.iros.go.kr/" target="_blank" rel="noopener noreferrer">인터넷등기소 <span>등기 확인</span>${icon('link',14)}</a><a href="https://rt.molit.go.kr/" target="_blank" rel="noopener noreferrer">국토부 실거래가 <span>거래 비교</span>${icon('link',14)}</a><a href="https://www.eum.go.kr/" target="_blank" rel="noopener noreferrer">토지이음 <span>토지·규제</span>${icon('link',14)}</a></div>`;}
  function documentExample(){return `<details class="study-example"><summary>${icon('book',18)} 서류 예시·용어</summary><div class="example-answer"><p class="example-intro"><span class="badge neutral">가상 학습 예시</span> 실제 물건의 입력값이나 확인 상태에는 반영되지 않습니다.</p><div class="example-document"><strong>① 법원 매각물건명세서</strong><p>물건번호 1 · 연습시 가상로 10, 101동 803호<br>건물의 표시: 아파트 · 전용 84.00㎡</p></div><div class="example-document"><strong>② 등기사항증명서 표제부</strong><p>소재지: 연습시 가상로 10, 101동 803호<br>전유부분 건물의 표시: 제8층 제803호 · 84.00㎡</p></div><div class="example-question"><strong>여기서 무엇을 확인할까요?</strong><p>서류마다 주소 표기 방식이 달라도 같은 물건인지, 동·호수와 면적이 일치하는지 대조해요. 지분만 매각되는 물건인지와 최신 발급 서류인지도 별도로 확인해요.</p></div><div class="example-document"><strong>③ 내 노트에는 이렇게 기록해요</strong><p>“열람일: 실제 확인한 날짜. 물건번호 1의 소재지·동호수·전용면적을 최신 등기 표제부와 대조함. 지분·매각범위는 매각 서류에서 추가 확인 필요.”</p></div><p>서류가 일치해도 임차인·인수권리는 각 항목에서 따로 확인하세요.</p><section class="learning-glossary" aria-label="경매 용어"><h3>헷갈리는 말, 짧게 보기</h3>${[
      ['말소기준권리','경매에서 권리의 소멸·인수 관계를 검토할 때 기준이 되는 권리를 찾는 개념이에요. 가장 빠른 날짜 하나만 고르지 말고 권리의 종류와 특별매각조건을 함께 봐요.'],
      ['대항력','임차인이 새로운 소유자에게 임대차 관계를 주장할 수 있는 효력이에요. 주택은 인도와 주민등록 등 요건과 효력 발생 시점을 함께 확인해요.'],
      ['우선변제와 배당요구','보증금을 배당에서 먼저 돌려받을 수 있는지는 대항요건, 확정일자, 배당요구 등 여러 조건에 달려 있어요. 대항력이 있다는 것과 전액 배당받는다는 것은 달라요.'],
      ['인수금액','낙찰대금과 별개로 낙찰자가 부담할 수 있는 금액이에요. 배당 후 남는 임차보증금 등은 개별 사실관계를 확인해 계산에 넣어요.']
    ].map(([title,body])=>`<details><summary>${title}</summary><p>${body}</p></details>`).join('')}</section><h3>원문 서류 찾기</h3>${sourceLinks()}</div></details>`;}
  const rightLabels = ['서류 대조','말소·인수','임차보증금','점유·인도','추가 비용','현장·예외'];
  function rightsChecklist(c){return `<section class="panel rights-checklist"><div class="panel-header"><div><h2 class="panel-title">권리 분석 기록</h2><p class="panel-subtitle">확인한 근거를 항목별로 기록하세요.</p></div><span class="badge sage" id="rightsCount">${complete(c)} / 6 완료</span></div><div class="rights-step-navigation" role="group" aria-label="권리분석 항목 선택">${rightLabels.map((label,i)=>`<button type="button" class="rights-step-button ${i===rightsStep?'active':''}" data-right-step="${i}" aria-pressed="${i===rightsStep}" aria-controls="rights-panel-${i}"><span class="rights-step-number">${String(i+1).padStart(2,'0')}</span><span>${label}</span><span class="rights-step-state" data-right-state="${i}" aria-label="${c.rights[i].status==='clear'&&c.rights[i].evidence.trim()?'근거 기록 완료':'근거 확인 필요'}">${c.rights[i].status==='clear'&&c.rights[i].evidence.trim()?icon('check',13):''}</span></button>`).join('')}</div>${rights.map(([title,desc],i)=>`<section id="rights-panel-${i}" class="rights-card" data-right-panel="${i}" aria-label="${i+1}번 ${rightLabels[i]}" ${i===rightsStep?'':'hidden'}><div class="panel-body"><div class="rights-top"><span class="rights-index">${String(i+1).padStart(2,'0')}</span><div class="rights-text"><h3>${title}</h3><p>${desc}</p></div></div><div class="rights-controls"><label for="right-${i}">확인 상태</label><select id="right-${i}" data-right="${i}">${options(statuses,c.rights[i].status)}</select></div><label class="evidence-field" for="evidence-${i}">확인 근거·남은 질문<textarea id="evidence-${i}" data-evidence="${i}" maxlength="${TEXT_LIMIT}" rows="3" placeholder="서류명, 발급·열람일, 확인 내용과 남은 질문을 적어 주세요.">${esc(c.rights[i].evidence)}</textarea><span class="evidence-print" data-print-evidence="${i}">${esc(c.rights[i].evidence)}</span></label></div></section>`).join('')}<div class="rights-pagination"><button type="button" class="button small" data-right-step="${Math.max(0,rightsStep-1)}" ${rightsStep===0?'disabled':''}>이전 항목</button><span>${rightsStep+1} / 6</span>${rightsStep<5?`<button type="button" class="button primary small" data-right-step="${rightsStep+1}">다음 항목 ${icon('arrow',15)}</button>`:`<button type="button" class="button primary small" data-page="money">투자금 계산 ${icon('arrow',15)}</button>`}</div></section>`;}
  function rightsPage(c,r){return `<div class="split-layout rights-layout"><div class="rights-main">${rightsChecklist(c)}${documentExample()}</div><aside class="side-column"><section class="panel rights-dates"><div class="panel-header"><h2 class="panel-title">날짜 비교</h2></div><div class="panel-body"><p class="panel-subtitle">대항력·인수 여부는 날짜와 서류를 함께 확인하세요.</p><div class="form-grid timeline-fields">${field('말소기준권리 후보 접수일','timeline.base',c.timeline.base,'','date')}${field('임차인 전입일','timeline.move',c.timeline.move,'','date')}${field('확정일자','timeline.fixed',c.timeline.fixed,'','date')}${field('배당요구 종기','timeline.demand',c.timeline.demand,'','date')}</div><p class="notice">등기 종류·실제 점유·배당요구·매각 조건을 함께 확인하세요. 임차인이 여럿이면 각각 기록하세요.</p></div></section>${decisionPanel(c,r,true)}</aside></div>`;}
  function moneyPage(c,r){return `<div class="split-layout"><div><section class="panel"><div class="panel-header"><div><h2 class="panel-title">투자금과 손익</h2><p class="panel-subtitle">입력 단위: 만원 · 세율·대출 조건은 직접 확인</p></div></div><div class="panel-body"><div class="calculator-guide"><div><p>낙찰가·대출·비용을 입력하세요.</p><details><summary>계산 가정</summary><p>세금·대출 실행액은 입력한 가정이며 예비비는 현금에만 더하고 손익 비용에서 제외해요.</p></details></div><button type="button" class="button small" data-page="simulation">모의경매</button></div><div class="form-section"><h3 class="form-section-title">01 &nbsp; 입찰과 자금 조달</h3><div class="form-grid">${calcField('예상 낙찰가','bid',c)}${calcField('최저매각가격','minimum',c)}${calcField('입찰보증금 비율','depositRate',c,'매각 공고에서 확인 · 재매각은 달라질 수 있어요.','%')}${calcField('예상 대출 실행액','loan',c,'한도·실행일·규제는 금융기관에 확인하세요.')}${calcField('가용 현금','available',c)}${calcField('현금 예비비','reserve',c,'예상 밖 지출에 대비해 남겨 둘 현금')}</div></div><div class="form-section"><h3 class="form-section-title">02 &nbsp; 취득·인수·정리 비용</h3><div class="form-grid">${calcField('취득 관련 세금 적용률','acquisitionRate',c,'연습 기본값 1.1% · 주택 수·가액·인수금액 등 과세표준과 부가세목을 별도 확인','%')}${calcField('법무·등기·보유 등 기타 정액비용','legal',c,'법무비·보유세·보유기간 관리비 등 별도 지출을 합산해요.')}${calcField('수리·청소비','repairs',c)}${calcField('명도·인도 예상 비용','eviction',c)}${calcField('인수할 관리비 등','arrears',c,'체납액 전부를 자동 인수하는 것으로 보지 않아요.')}${calcField('임차보증금 등 별도 인수액','assumed',c,'권리분석에서 확인한 추가 부담액')}</div></div><div class="form-section"><h3 class="form-section-title">03 &nbsp; 보유와 매도 시나리오</h3><div class="form-grid">${calcField('대출 연이율','loanRate',c,'원금 고정·단리로 추정','%')}${calcField('예상 보유기간','months',c,'임대수익은 제외하며 보유세·관리비 지출은 기타 정액비용에 반영하세요.','개월')}${calcField('기준 시나리오 매도가','sale',c)}${calcField('보수적 시나리오 매도가','downside',c)}${calcField('매도 중개 등 비례 비용률','sellingRate',c,'기본값은 연습 가정이며 법정 요율 자동 산정이 아니에요.','%')}${calcField('양도 관련 세금 예상액','saleTax',c,'0이면 세금 미반영 · 실제 세무 검토값을 입력하세요.')}${calcField('내 목표 순수익','targetProfit',c)}</div></div></div></section></div><aside class="side-column">${resultPanel(c,r)}<section class="panel"><div class="panel-header"><h2 class="panel-title">자금 일정</h2></div><div class="panel-body" id="cashSchedule">${schedule(c,r)}</div></section><section class="panel"><div class="panel-body"><p class="panel-subtitle">예비비는 지출이 아닌 현금 완충액으로, 수익 계산에서는 제외해요. 잔금 현금은 대출이 잔금일에 실행된다고 가정한 추정치이며 이후 수리·보유비는 별도로 필요해요.</p></div></section></aside></div>`;}
  function schedule(c,r){return !r.valid?'입력 오류를 확인해 주세요.':`<div class="timeline"><div class="timeline-item"><span class="timeline-date">입찰일</span><strong>${amount(r.deposit)}</strong><span class="timeline-label">입찰보증금 · 낙찰 시 대금에 충당</span></div><div class="timeline-item"><span class="timeline-date">잔금·취득 시점</span><strong>추가 ${amount(r.balanceCash)}</strong><span class="timeline-label">잔금 − 보증금 − 대출 + 취득세·등기비</span></div>${r.balanceCredit>0?`<div class="calculator-credit">대출·정산 후 반환 ${amount(r.balanceCredit)}을 가정했어요. 실제 실행·정산 조건을 금융기관에 확인하고, 이후 수리·보유 비용에 다시 투입할 현금으로 구분하세요.</div>`:''}<div class="timeline-item"><span class="timeline-date">인도·수리·보유 시점</span><strong>${amount(Number(c.finance.repairs)+Number(c.finance.eviction)+Number(c.finance.arrears)+Number(c.finance.assumed)+r.interest)}</strong><span class="timeline-label">예상 정리 비용과 보유기간 이자</span></div></div>`;}
  function areaPage(c,r){const comps=regionEvidence(c),per=comps.map(x=>Number(x.price)/Number(x.area)),avg=per.length?per.reduce((a,b)=>a+b,0)/per.length:0;return `<div class="split-layout"><div><section class="panel"><div class="panel-header"><div><h2 class="panel-title">비교 실거래</h2><p class="panel-subtitle">같은 단지·유형, 비슷한 면적과 층, 최근 거래부터 찾아보세요.</p></div></div><div class="panel-body"><div class="form-grid">${field('내 물건 전용면적','area',c.area,'㎡ 단위로 입력 · 면적만 같아도 층·향·상태는 달라요.')}<div class="field"><label for="region-date">지역 자료 확인일</label><input id="region-date" type="date" data-region="checked" value="${esc(c.region.checked)}"></div></div><div class="table-wrap"><table class="data-table"><caption>비교 실거래 기록 · 실제 조회한 내용만 입력</caption><thead><tr><th>거래가 · 만원</th><th>전용 · ㎡</th><th>계약일</th><th>출처·비교 조건</th></tr></thead><tbody>${c.region.comps.map((x,i)=>`<tr>${['price','area','date','source'].map(k=>`<td><input aria-label="비교 거래 ${i+1} ${ {price:'거래가 만원',area:'전용면적 제곱미터',date:'계약일',source:'출처와 조건'}[k]}" data-comp="${i}" data-comp-key="${k}" type="${k==='date'?'date':k==='source'?'text':'number'}" ${k==='price'||k==='area'?'min="0" step="any"':k==='source'?`maxlength="${TEXT_LIMIT}"`:''} value="${esc(x[k])}" placeholder="${k==='source'?'단지·층·조회 출처':'미입력'}"></td>`).join('')}</tr>`).join('')}</tbody></table></div><div id="compSummary">${compSummary(c)}</div></div></section><section class="panel"><div class="panel-header"><h2 class="panel-title">수요·공급 근거</h2></div><div class="panel-body"><div class="form-grid"><div class="field"><label for="station">교통·생활권 메모</label><input id="station" data-region="station" maxlength="${TEXT_LIMIT}" value="${esc(c.region.station)}" placeholder="역 도보 시간, 직장, 학교와 생활 편의"></div><div class="field"><label for="demand">거래·임대 수요</label><select id="demand" data-region="demand">${options([['unknown','미확인'],['steady','수요 근거 있음'],['weak','거래·임대 수요 약함']],c.region.demand)}</select></div><div class="field"><label for="supply">주변 공급 부담</label><select id="supply" data-region="supply">${options([['unknown','미확인'],['manageable','확인한 범위에서 부담 제한적'],['high','입주 물량·매물 부담 있음']],c.region.supply)}</select></div></div><label class="evidence-field" for="region-evidence">수요·공급을 판단한 근거<textarea rows="4" id="region-evidence" data-region="evidence" maxlength="${TEXT_LIMIT}" placeholder="거래량, 매물 체류기간, 입주 예정 물량, 현장 중개업소 확인 내용과 출처를 기록하세요.">${esc(c.region.evidence)}</textarea></label></div></section></div><aside class="side-column"><section class="panel"><div class="panel-body"><span class="badge sage">비교의 원칙</span><h3>싼 이유를 먼저 찾아보세요.</h3><ul class="reason-list"><li>실거래가의 해제 여부와 계약일을 확인해요.</li><li>층·향·수리 상태·점유 차이를 기록해요.</li><li>개발 호재는 확정된 계획과 기대를 구분해요.</li><li>거래가 적으면 매도까지 걸릴 시간을 늘려 계산해요.</li></ul>${sourceLinks()}</div></section>${decisionPanel(c,r)}</aside></div>`;}
  function compSummary(c){const comps=regionEvidence(c);if(!comps.length)return '<p class="notice">거래가·면적·계약일·출처를 입력하면 면적 환산 참고값을 볼 수 있어요.</p>';const avg=comps.reduce((a,x)=>a+Number(x.price)/Number(x.area),0)/comps.length;return `<p class="notice">기록한 ${comps.length}건의 ㎡당 평균 × 내 면적: <strong>${amount(avg*Number(c.area))}</strong><br>단순 면적 환산 참고값이며 감정가나 자동 매도가 추정이 아니에요. 매도 시나리오는 투자금 계산에서 직접 설정하세요.</p>`;}
  function notesPage(c,r){const v=verdict(c,r);return `<div class="split-layout"><div><section class="panel"><div class="panel-header"><div><h2 class="panel-title">손익과 검토 사유</h2><p class="panel-subtitle">지금 적은 조건과 확인 근거를 바탕으로 정리해요.</p></div></div><div class="panel-body"><span class="badge ${v.tone}">${v.title}</span><div class="scenario-grid">${[['기준 매도 시나리오',c.finance.sale,r.profit,''],['보수적 매도 시나리오',c.finance.downside,r.downsideProfit,'stress']].map(([name,sale,p,cls])=>`<div class="scenario-card ${cls}"><span class="metric-label">${name}</span><p>매도가 ${amount(sale)}</p><strong class="profit-number" data-result="${cls==='stress'?'downsideProfit':'profit'}">${money(p)}</strong><span class="metric-note">예상 순손익 · 예비비 제외</span></div>`).join('')}</div>${r.valid?`<div class="cost-row total"><span>${Model.compareAmounts(r.maxBid,r.input.loan)<0?'대출 재설정 참고값':'목표 수익을 위한 계산상 입찰 상한'}</span><strong data-result="maxBid">${amount(Format.floorBid(r.maxBid))}</strong></div>${Model.compareAmounts(r.maxBid,r.input.loan)<0?'<p class="calculator-credit">현재 고정 대출액에서는 목표를 만족하는 입찰 상한이 없어 대출액을 다시 설정해야 해요.</p>':''}${Model.compareAmounts(r.maxBid,r.input.minimum)<0?'<p class="calculator-credit">이 가정에서는 최저매각가격으로도 목표 수익에 미달해요.</p>':''}<details><summary>상한 계산 가정</summary><p class="field-help">고정한 대출·비용·세금 가정의 역산값을 100원 단위로 내렸으며 실제 대출 한도나 적정 입찰가를 보장하지 않아요.</p></details>`:`<p class="form-error">${r.errors.map(esc).join('<br>')}</p>`}<h3>검토가 더 필요한 이유</h3>${v.reasons.length?`<ul class="reason-list">${v.reasons.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p>입력한 조건의 확인 항목을 채웠어요. 입찰 직전에 최신 서류와 자금 실행 조건을 다시 확인하세요.</p>'}</div></section><section class="panel"><div class="panel-header"><h2 class="panel-title">나의 판단</h2></div><div class="panel-body"><label class="evidence-field" for="thesis">이 물건을 검토하는 이유<textarea id="thesis" rows="4" data-field="thesis" maxlength="${TEXT_LIMIT}" placeholder="어떤 가격과 조건이라면 매력이 있나요? 누구에게, 언제, 어떤 가격에 팔거나 임대할 수 있나요?">${esc(c.thesis)}</textarea></label><label class="evidence-field" for="questions">입찰 전 꼭 해결할 질문<textarea id="questions" rows="4" data-field="questions" maxlength="${TEXT_LIMIT}" placeholder="예: 선순위 임차인의 배당 부족액은? 잔금일 대출 실행이 가능한가?">${esc(c.questions)}</textarea></label><div class="field"><label for="conclusion">내가 내린 현재 결론</label><select id="conclusion" data-field="conclusion">${options([['hold','보류 · 근거를 더 확인하기'],['review','계속 검토 · 현장·전문가 확인하기'],['pass','제외 · 이번 물건은 넘기기']],c.conclusion)}</select><p class="field-help">직접 남긴 결론입니다. 위의 미확인·위험 표시는 그대로 유지돼요.</p></div></div></section></div><aside class="side-column">${resultPanel(c,r)}<section class="panel"><div class="panel-body"><h3>노트 백업</h3><p class="panel-subtitle">분석노트를 JSON 파일로 백업하세요.</p><button class="button" data-action="export">${icon('down',16)} 백업</button><button class="text-link" data-action="print">인쇄 ${icon('arrow',16)}</button></div></section></aside></div>`;}
  function render(){
    const c=current(),r=Model.calculate(c.finance),step=steps.find(s=>s.id===page);
    $('#app').innerHTML=`<div class="app-shell"><aside class="sidebar"><a class="brand" href="./auction-study.html"><span class="brand-mark">${icon('book',23)}</span><span><strong class="brand-name">경매노트<span>auct. note</span></strong><span class="brand-sub">근거를 쌓는 투자 공부</span></span></a><div class="nav-label">나의 스터디</div><nav aria-label="경매 분석 단계">${navButton('course',PAGE_LABELS.course,'book')}${navButton('simulation',PAGE_LABELS.simulation,'shield')}${navButton('learn',PAGE_LABELS.learn,'book')}${navButton('process',PAGE_LABELS.process,'note')}${navButton('home',PAGE_LABELS.home,'grid')}${steps.map(s=>navButton(s.id,s.name,s.icon)).join('')}</nav><div class="sidebar-bottom"><span class="save-indicator" id="saveStatus">${storageOK?'이 기기에 자동 저장':'저장 불가 · 백업 필요'}</span><button class="text-link" data-action="export">${icon('down',15)} 백업</button><button class="text-link" data-action="import">가져오기 ${icon('plus',15)}</button><span>나의 경매 공부, 나의 속도로.</span></div></aside><main class="workspace"><header class="topbar"><span class="breadcrumb">나의 스터디 <span>/</span> ${PAGE_LABELS[page]}</span><div class="top-actions"><label class="case-switch"><span class="sr-only">분석할 물건 선택</span><select id="caseSelect">${state.cases.map(x=>`<option value="${esc(x.id)}" ${x.id===c.id?'selected':''}>${esc(x.name)}</option>`).join('')}</select></label><button class="button small" data-action="new">${icon('plus',16)} 추가</button><button class="button small" data-action="manage" title="선택 노트 정리">정리</button></div></header><div class="page-heading"><div><div class="eyebrow">AUCTION STUDY NOTE${step?' / '+step.n:''}</div><h1>${PAGE_LABELS[page]}</h1><p class="heading-description">${step?step.desc:page==='course'?'기초부터 예제와 실습까지 차례로 익히세요.':page==='simulation'?'가상 서류로 자금과 판단을 연습하세요.':page==='learn'?'서류의 근거를 읽고 답해 보세요.':page==='process'?'경매 순서와 준비 자료를 확인하세요.':'필요한 현금과 남은 확인 사항을 보세요.'}</p></div>${['course','learn','simulation','process'].includes(page)?'<button class="button small" data-page="rights">내 노트</button>':`<button class="button small" data-action="edit">정보 수정 ${icon('note',15)}</button>`}</div>${['course','learn','simulation','process'].includes(page)?'':`<div class="case-banner"><div><span class="badge ${c.demo?'amber':'sage'}">${c.demo?'가상 연습 물건 · 실매물 아님':'직접 입력한 물건'}</span><strong class="case-title" title="${esc(c.name)}">${esc(c.name)}</strong><span class="case-address" title="${esc(c.address)}">${esc(c.address||'주소를 입력해 주세요.')}</span></div><div class="case-meta"><span>${esc(c.number||'사건번호 미입력')}</span><span>${c.date?'입찰일 '+esc(c.date):'입찰일 미입력'}</span></div></div>`}<div id="storageWarning" class="${storageOK?'':'notice warning'}" role="alert" ${storageOK?'hidden':''}>${storageOK?'':esc(storageWarning())}</div><div class="page-content" data-view="${page}">${page==='course'?course.render():page==='simulation'?simulation.render():page==='process'?processDesk.render():page==='learn'?learning.render(c):page==='home'?home(c,r):page==='rights'?rightsPage(c,r):page==='money'?moneyPage(c,r):page==='area'?areaPage(c,r):notesPage(c,r)}</div><footer class="page-footer"><span>경매노트 · 판단의 근거가 쌓이는 곳</span><span>직접 입력한 정보로 학습하는 노트 · 법률·세금·대출 조건은 개별 확인</span></footer></main></div><dialog id="caseDialog" class="dialog-form" aria-labelledby="caseDialogTitle"></dialog><input id="importFile" type="file" accept="application/json,.json" hidden>`;
    if(page==='course')course.afterRender();
    document.querySelectorAll('.page-content .split-layout>div:first-child,.page-content .split-layout>.side-column').forEach((el,i)=>{el.setAttribute('role','region');el.setAttribute('aria-label',i===0?'분석 입력 내용':'분석 요약과 참고 자료');});
    if(window.innerWidth<=760){const nav=$('.sidebar nav'),active=nav?.querySelector('.active');if(nav&&active)nav.scrollLeft=Math.max(0,active.offsetLeft-nav.offsetLeft-(nav.clientWidth-active.offsetWidth)/2);}
  }
  function setPath(obj,path,value){const p=path.split('.');if(p.length===2)obj[p[0]][p[1]]=value;else obj[path]=value;}
  function refreshCalculations(){const c=current(),r=Model.calculate(c.finance);document.querySelectorAll('[data-results]').forEach(e=>e.innerHTML=cashContent(c,r));if($('#cashSchedule'))$('#cashSchedule').innerHTML=schedule(c,r);if($('#compSummary'))$('#compSummary').innerHTML=compSummary(c);document.querySelectorAll('.decision-panel').forEach(el=>el.outerHTML=decisionPanel(c,r,el.classList.contains('rights-verdict'),!!el.querySelector('details[open]')));if($('#rightsCount'))$('#rightsCount').textContent=complete(c)+' / 6 완료';document.querySelectorAll('[data-print-evidence]').forEach(el=>el.textContent=c.rights[Number(el.dataset.printEvidence)].evidence);document.querySelectorAll('[data-right-state]').forEach(el=>{const item=c.rights[Number(el.dataset.rightState)],done=item.status==='clear'&&item.evidence.trim();el.innerHTML=done?icon('check',13):'';el.setAttribute('aria-label',done?'근거 기록 완료':'근거 확인 필요');});}
  function editCase(isNew){if(isNew&&state.cases.length>=100){toast(CASE_LIMIT_MESSAGE);return;}const c=isNew?newCase(false):current();const d=$('#caseDialog');d.innerHTML=`<form id="caseForm"><h2 id="caseDialogTitle">${isNew?'노트 추가':'물건 정보'}</h2><p class="panel-subtitle">직접 확인한 사건 정보를 입력하세요.</p><details><summary>계산 입력 안내</summary><p>실제 물건의 계산값은 비워 두며 확인한 금액을 투자금 계산에 입력합니다.</p></details><div class="form-grid">${[['name','노트 이름',c.name,'text'],['address','주소·동·호수',c.address,'text'],['number','법원·사건번호·물건번호',c.number,'text'],['date','입찰 예정일',c.date,'date']].map(([key,label,val,type])=>`<div class="field full-span"><label for="case-${key}">${label}</label><input id="case-${key}" name="${key}" type="${type}" value="${esc(val)}" ${key==='name'?'required maxlength="100"':type==='text'?`maxlength="${TEXT_LIMIT}"`:''}></div>`).join('')}</div><div class="heading-actions"><button type="button" class="button" data-action="close-dialog">취소</button><button class="button primary" type="submit">${isNew?'추가':'저장'}</button></div></form>`;d.showModal();$('#caseForm').onsubmit=e=>{e.preventDefault();const f=new FormData(e.target);const name=String(f.get('name')).trim();if(!name)return;for(const k of ['name','address','number','date'])c[k]=String(f.get(k)).trim();if(isNew){state.cases.push(c);state.active=c.id;rightsStep=0;}const saved=save();d.close();if(isNew)openPage('rights');else render();toast(saved?(isNew?'노트를 추가했어요.':'저장했어요.'):unsavedMessage(isNew?'새 물건 노트를 이 화면에 만들었어요.':'물건 정보를 이 화면에 유지했어요.'));};}
  function exportNotes(){const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='경매노트-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('분석노트를 백업했어요.');const status=$('#deleteCaseBackup');if(status)status.textContent='전체 분석노트를 백업했어요.';}
  function manageCase(){
    const target=current(),targetId=target.id,d=$('#caseDialog');
    d.innerHTML=`<form id="deleteCaseForm"><h2 id="caseDialogTitle">노트 정리</h2><p class="panel-subtitle">선택한 노트만 삭제해요.</p><div class="notice"><strong id="deleteCaseName">${esc(target.name)}</strong><p>${state.cases.length===1?'마지막 노트를 삭제하면 빈 노트 1개를 만듭니다.':`다른 노트 ${state.cases.length-1}개는 유지됩니다.`}</p></div><p id="deleteCaseError" class="notice warning" role="alert" hidden></p><p><label><input id="confirmCaseDelete" type="checkbox" required> 위 노트를 삭제하는 데 동의합니다.</label></p><p id="deleteCaseBackup" class="field-help">삭제 전에 전체 분석노트를 백업할 수 있어요.</p><div class="heading-actions"><button type="button" class="button" data-action="export">백업</button><button id="deleteCaseCancel" type="button" class="button" data-action="close-dialog">취소</button><button id="deleteCaseSubmit" type="submit" class="button">삭제</button></div></form>`;
    d.showModal();updateStorageStatus();$('#deleteCaseCancel').focus({preventScroll:true});
    $('#deleteCaseForm').onsubmit=event=>{
      event.preventDefault();
      if(!$('#confirmCaseDelete').checked||current().id!==targetId||!storageOK){updateStorageStatus();return;}
      const position=state.cases.findIndex(item=>item.id===targetId);
      if(position<0)return;
      const kept=state.cases.filter(item=>item.id!==targetId);
      if(!kept.length)kept.push(newCase(false));
      const next={...state,cases:kept,active:kept[Math.min(position,kept.length-1)].id};
      // Commit the candidate before changing the working notebook; failed or
      // conflicting storage must preserve every note in this screen as well.
      if(!writeState(next)){updateStorageStatus();toast('삭제하지 않았어요. 현재 기록을 백업하세요.');return;}
      state=next;pristineNotebook=false;rightsStep=0;d.close();render();
      $('#caseSelect')?.focus({preventScroll:true});toast('선택한 노트를 삭제했어요.');
    };
  }
  function validImport(x){
    // Existing long notes remain readable and round-trip through backups without truncation.
    const text = (v,max=Infinity) => typeof v==='string' && v.length<=max;
    const date = v => text(v) && (v==='' || /^\d{4,6}-\d{2}-\d{2}$/.test(v));
    const numeric = v => (typeof v==='number' && Number.isFinite(v)) || (text(v) && (v==='' || Number.isFinite(Number(v))));
    const oneOf=(v,items)=>items.includes(v);
    if(!x||x.version!==1||!Array.isArray(x.cases)||!x.cases.length||x.cases.length>100)return false;
    if(new Set(x.cases.map(c=>c?.id)).size!==x.cases.length)return false;
    return x.cases.every(c=>c&&text(c.name,100)&&text(c.id,150)&&typeof c.demo==='boolean'&&
      ['address','number','thesis','questions','updated'].every(k=>text(c[k]))&&date(c.date)&&numeric(c.area)&&
      oneOf(c.conclusion,['hold','review','pass'])&&c.finance&&Object.keys(Model.defaults()).every(k=>numeric(c.finance[k]))&&
      Array.isArray(c.rights)&&c.rights.length===6&&c.rights.every(r=>r&&statuses.some(s=>s[0]===r.status)&&text(r.evidence))&&
      c.timeline&&['base','move','fixed','demand'].every(k=>date(c.timeline[k]))&&c.region&&
      ['station','evidence'].every(k=>text(c.region[k]))&&date(c.region.checked)&&
      oneOf(c.region.supply,['unknown','manageable','high'])&&oneOf(c.region.demand,['unknown','steady','weak'])&&
      Array.isArray(c.region.comps)&&c.region.comps.length===3&&c.region.comps.every(r=>r&&numeric(r.price)&&numeric(r.area)&&date(r.date)&&text(r.source)));
  }
  document.addEventListener('click',e=>{const b=e.target.closest('[data-page],[data-action],[data-home-panel],[data-right-step]');if(!b)return;if(b.dataset.rightStep!==undefined){rightsStep=Math.max(0,Math.min(5,Number(b.dataset.rightStep)));$('.rights-checklist').outerHTML=rightsChecklist(current());$(`.rights-step-button[data-right-step="${rightsStep}"]`)?.focus({preventScroll:true});return;}if(b.dataset.homePanel){homePanel=b.dataset.homePanel;render();$(`[data-home-panel="${homePanel}"]`)?.focus({preventScroll:true});return;}if(b.dataset.page){openPage(b.dataset.page);return;}switch(b.dataset.action){case'new':editCase(true);break;case'edit':editCase(false);break;case'manage':manageCase();break;case'close-dialog':$('#caseDialog').close();break;case'export':exportNotes();break;case'import':$('#importFile').click();break;case'print':window.print();break;}});
  document.addEventListener('input',e=>{const t=e.target,c=current();if(t.dataset.finance){c.finance[t.dataset.finance]=t.value===''?'':Number(t.value);save();refreshCalculations();}else if(t.dataset.evidence!==undefined){c.rights[Number(t.dataset.evidence)].evidence=t.value;save();refreshCalculations();}else if(t.dataset.field){setPath(c,t.dataset.field,t.type==='number'?(t.value===''?'':Number(t.value)):t.value);save();refreshCalculations();}else if(t.dataset.region){c.region[t.dataset.region]=t.value;save();refreshCalculations();}else if(t.dataset.comp!==undefined){c.region.comps[Number(t.dataset.comp)][t.dataset.compKey]=t.value;save();refreshCalculations();}});
  document.addEventListener('change',async e=>{const t=e.target,c=current();if(t.id==='caseSelect'){state.active=t.value;save();render();$('#caseSelect')?.focus({preventScroll:true});}else if(t.dataset.right!==undefined){c.rights[Number(t.dataset.right)].status=t.value;save();refreshCalculations();}else if(t.dataset.evidence!==undefined||t.dataset.region||t.dataset.comp!==undefined){refreshCalculations();}else if(t.id==='importFile'&&t.files[0]){try{const x=JSON.parse(await t.files[0].text());if(!validImport(x))throw Error();const kept=pristineNotebook?[]:state.cases;if(kept.length+x.cases.length>100){toast('노트는 최대 100개까지 보관할 수 있어요. 가져올 노트와 기존 노트의 개수를 확인해 주세요.');t.value='';return;}const added=x.cases.map(c=>({...c,id:id()}));state.cases=[...kept,...added];state.active=added[0].id;const saved=save();render();toast(saved?`${added.length}개 노트를 추가했어요.`:unsavedMessage(`${added.length}개 노트를 이 화면에 가져왔어요.`));}catch(err){toast('유효한 경매노트 파일이 아니에요.');t.value='';}}});
  let printDetails=[];
  window.addEventListener('beforeprint',()=>{printDetails=[...document.querySelectorAll('.rights-verdict details:not([open])')];printDetails.forEach(el=>el.open=true);});
  window.addEventListener('afterprint',()=>{printDetails.forEach(el=>el.open=false);printDetails=[];});
  window.addEventListener('popstate',()=>openPage(requestedPage(),{replace:true}));
  openPage(page,{replace:true,focus:false});
})();
