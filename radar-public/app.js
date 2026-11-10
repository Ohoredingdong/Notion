'use strict';
(() => {
  const KEY = 'radar-public-demo:journal:v1';
  const samples = Object.freeze([
    {id:'DEMO-A',name:'가상기업 A',sector:'예시 · 제조업',price:10000,eps:500,bps:8000,net:10000000,equity:100000000,series:[94,98,96,100,103,101,105,108,104,107,110,112]},
    {id:'DEMO-B',name:'가상기업 B',sector:'예시 · 서비스업',price:20000,eps:1250,bps:16000,net:12000000,equity:80000000,series:[110,108,112,109,106,105,109,104,103,107,102,100]},
    {id:'DEMO-C',name:'가상기업 C',sector:'예시 · 연구개발',price:15000,eps:-100,bps:10000,net:-3000000,equity:60000000,series:[98,106,102,109,104,96,100,107,102,110,106,108]}
  ]);
  const $ = id => document.getElementById(id);
  const nf = new Intl.NumberFormat('ko-KR', {maximumFractionDigits:2});
  const text = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  let current = samples[0], notes = Object.create(null), storageProblem = false, draftDirty = false;
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '{}');
    if (saved && typeof saved === 'object' && !Array.isArray(saved)) {
      for (const row of samples) if (typeof saved[row.id] === 'string') notes[row.id] = saved[row.id].slice(0,3000);
    }
  } catch (_) { storageProblem = true; }
  function ratio(value, denominator) {
    if (!finite(value) || !finite(denominator) || denominator <= 0) return null;
    const result = value / denominator;
    return finite(result) ? result : null;
  }
  function calculate(data) {
    return {per:data.price >= 0 ? ratio(data.price,data.eps) : null,
      pbr:data.price >= 0 ? ratio(data.price,data.bps) : null,
      roe:ratio(data.net,data.equity) === null ? null : ratio(data.net,data.equity)*100};
  }
  function metric(label,value,suffix,explanation) {
    return '<div class="metric"><span>'+text(label)+'</span><strong>'+ (finite(value) ? nf.format(value)+text(suffix) : '산출 안 함') +'</strong><small>'+text(explanation)+'</small></div>';
  }
  function renderMetrics(data,target) {
    const r=calculate(data);
    target.innerHTML=metric('PER',r.per,'배','주가 ÷ 주당순이익')+metric('PBR',r.pbr,'배','주가 ÷ 주당순자산')+metric('ROE',r.roe,'%','순이익 ÷ 평균 자기자본');
  }
  function renderList() {
    const q=$('search').value.trim().toLowerCase();
    const rows=samples.filter(row=>(row.id+' '+row.name+' '+row.sector).toLowerCase().includes(q));
    $('companies').innerHTML=rows.length ? rows.map(row=>'<button type="button" class="company '+(row.id===current.id?'active':'')+'" data-company="'+row.id+'" aria-pressed="'+(row.id===current.id)+'"><strong>'+row.name+'</strong><small>'+row.id+' · 가상 예시</small></button>').join('') : '<p class="empty">검색 결과가 없습니다.</p>';
  }
  function renderChart(row) {
    const lo=Math.min(...row.series)-4,hi=Math.max(...row.series)+4;
    const points=row.series.map((v,i)=>[12+i*576/(row.series.length-1),156-(v-lo)/(hi-lo)*140]);
    const path=points.map((p,i)=>(i?'L':'M')+p.map(x=>x.toFixed(2)).join(' ')).join(' ');
    const end=points[points.length-1];
    $('chart').innerHTML='<title>직접 작성한 가상 가격 예시, 실제 시세 아님</title>'+[30,70,110,150].map(y=>'<path class="chart-grid" d="M0 '+y+' H600"/>').join('')+'<path class="chart-line" d="'+path+'"/><circle class="chart-dot" cx="'+end[0]+'" cy="'+end[1]+'" r="3.5"/>';
  }
  function refreshNote() {
    $('noteCompany').textContent=current.name+' · '+current.id;
    $('notes').value=notes[current.id]||'';
    $('saveStatus').textContent=storageProblem?'저장소를 읽지 못했습니다. 기존 기록을 덮어쓰지 않습니다.':'';
    $('saveStatus').className=storageProblem?'error':'';
    draftDirty=false;
  }
  function choose(id) {
    if (draftDirty && !window.confirm('저장하지 않은 메모가 있습니다. 기업을 바꾸시겠습니까?')) return;
    current=samples.find(row=>row.id===id)||samples[0];
    $('companyName').textContent=current.name;
    $('sector').textContent=current.sector+' · '+current.id;
    $('price').textContent=nf.format(current.price)+'원';
    renderChart(current);renderMetrics(current,$('metrics'));renderList();refreshNote();
  }
  function tab(name) {
    if (!['home','compare','journal','release'].includes(name)) return;
    document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!==name);
    document.querySelectorAll('[data-tab]').forEach(el=>{el.classList.toggle('active',el.dataset.tab===name);el.setAttribute('aria-pressed',String(el.dataset.tab===name));});
  }
  $('indices').innerHTML=['코스피','코스닥','나스닥','S&P 500','다우'].map(name=>'<div class="index"><span>'+name+'</span><strong>—</strong><small>시세 미연결</small></div>').join('');
  document.querySelectorAll('[data-tab],[data-goto]').forEach(el=>el.addEventListener('click',()=>tab(el.dataset.tab||el.dataset.goto)));
  $('companies').addEventListener('click',event=>{const b=event.target.closest('[data-company]');if(b)choose(b.dataset.company);});
  $('search').addEventListener('input',renderList);
  $('notes').addEventListener('input',()=>{draftDirty=true;$('saveStatus').textContent='아직 저장하지 않았습니다.';});
  $('saveNote').addEventListener('click',()=>{
    const status=$('saveStatus');
    if(storageProblem){status.textContent='기존 기록을 읽지 못해 저장을 중단했습니다. 메모를 별도로 복사해 보관하세요.';status.className='error';return;}
    try {
      const raw=localStorage.getItem(KEY),latest=JSON.parse(raw||'{}');
      if(!latest||typeof latest!=='object'||Array.isArray(latest))throw Error('invalid storage');
      const previous=typeof latest[current.id]==='string'?latest[current.id].slice(0,3000):'';
      if(previous!==(notes[current.id]||'')){status.textContent='다른 탭의 기록이 변경됐습니다. 덮어쓰지 않았습니다. 현재 메모를 복사한 후 새로고침하세요.';status.className='error';return;}
      const updated=Object.create(null);
      for(const row of samples)if(typeof latest[row.id]==='string')updated[row.id]=latest[row.id].slice(0,3000);
      updated[current.id]=$('notes').value.slice(0,3000);
      localStorage.setItem(KEY,JSON.stringify(updated));notes=updated;draftDirty=false;
      status.className='';status.textContent='이 브라우저에 저장했습니다. 서버 전송은 없습니다.';
    }catch(_){status.className='error';status.textContent='저장하지 못했습니다. 입력한 내용은 그대로 두었습니다.';}
  });
  $('exportNotes').addEventListener('click',()=>{
    const payload={schema:'radar-public-demo-notes-1',edition:'public-demo',contains_real_market_data:false,notes:{...notes},unsaved_draft:draftDirty?{company:current.id,text:$('notes').value}:null};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='radar-public-demo-notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  $('ratioForm').addEventListener('submit',event=>{
    event.preventDefault();const f=new FormData(event.currentTarget),data={};
    for(const name of ['price','eps','bps','net','equity']) {const raw=String(f.get(name)||'').trim();data[name]=raw===''?NaN:Number(raw);}
    renderMetrics(data,$('ratioOutput'));
  });
  window.addEventListener('beforeunload',event=>{if(draftDirty){event.preventDefault();event.returnValue='';}});
  renderMetrics(samples[0],$('ratioOutput'));choose(samples[0].id);
})();
