(()=>{
  const IK='use-me-first-v4',SK='use-me-first-seasonings-v1',PK='use-me-first-pantry-v1',CSK='use-me-first-custom-seasonings-v1',CPK='use-me-first-custom-pantry-v1',SYNC_KEY='use-me-first-sync-code-v1';
  const SYNC_URL='https://dfklyngtjqvlirgrtdfb.supabase.co/functions/v1/use-me-first-sync';
  const BASE_S=['소금','후추','식용유','간장','설탕','식초','참기름','고춧가루','고추장','된장','다진마늘','케첩'];
  const BASE_P=['밥/즉석밥','김','참치캔','면/라면','식빵','김가루'];
  const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
  const readArray=k=>{try{const v=JSON.parse(localStorage.getItem(k));return Array.isArray(v)?v:[]}catch{return[]}};
  const readSet=k=>new Set(readArray(k)),saveSet=(k,v)=>localStorage.setItem(k,JSON.stringify([...v]));
  const uniq=a=>[...new Set(a.map(x=>String(x).trim()).filter(Boolean))];
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const today=()=>{const d=new Date;return new Date(d.getFullYear(),d.getMonth(),d.getDate())};
  const iso=n=>{const d=today();d.setDate(d.getDate()+n);return`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
  const parse=v=>{const[y,m,d]=String(v||'').split('-').map(Number);return new Date(y,m-1,d)};
  const left=v=>Math.ceil((parse(v)-today())/864e5),fmt=v=>{const d=parse(v);return`${d.getMonth()+1}.${String(d.getDate()).padStart(2,'0')}까지`},dt=d=>d<0?`D+${-d}`:d?`D-${d}`:'D-DAY';
  let items=readArray(IK),season=readSet(SK),pantry=readSet(PK),customSeason=readArray(CSK),customPantry=readArray(CPK),show=true,syncBusy=false,syncTimer=null;
  const saveItems=()=>localStorage.setItem(IK,JSON.stringify(items)),allSeason=()=>uniq([...BASE_S,...customSeason]),allPantry=()=>uniq([...BASE_P,...customPantry]);

  function icon(n){
    if(/두부/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M6 8.5 12 5l6 3.5v7L12 19l-6-3.5v-7Z" fill="#FFF1CE" stroke="#C7A257" stroke-width="1.5"/><path d="m6 8.5 6 3.4 6-3.4M12 11.9V19" stroke="#D8B66E" stroke-width="1.2"/></svg>';
    if(/시금치|상추|배추|달래|깻잎/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M18.5 5.5c-5.8.2-9.4 2.5-10.5 6.8-.8 3 1 5.6 4.1 5.8 4.8.2 7.4-3.8 6.4-12.6Z" fill="#C5E2BD" stroke="#6D9968" stroke-width="1.4"/><path d="M8.6 16.8c2.1-3 4.6-5.1 7.7-6.7" stroke="#6D9968" stroke-width="1.3" stroke-linecap="round"/></svg>';
    if(/애호박|호박/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M5 14c2.5-5 8.8-7.2 14-4.4-2 5.7-8.5 8.1-14 4.4Z" fill="#B8D98C" stroke="#6A9A50" stroke-width="1.4"/><path d="M6.5 13.6c3.2-.5 6.4-1.4 10.3-3.3" stroke="#6A9A50" stroke-width="1.1" stroke-linecap="round"/></svg>';
    if(/닭/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M10 8c2.8-1.4 6 .1 7.1 2.9 1.1 2.8-.1 6-2.8 7.1-2.7 1.1-5.8-.1-7-2.7-.6-1.3-.7-2.3-.5-3.7.2-1.3 1.5-2.9 3.2-3.6Z" fill="#F3C3B4" stroke="#BC745B" stroke-width="1.4"/><circle cx="7" cy="16.4" r="1.5" fill="#FFF7F2" stroke="#BC745B" stroke-width="1.1"/></svg>';
    if(/김치/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M6 15c3-5 8-7 12-7-1.2 3.5-3.3 6.7-6.9 8.6-2 .9-3.6.5-5.1-1.6Z" fill="#F2A164" stroke="#D16F47" stroke-width="1.4"/><path d="M8 14.5c2.6-2.2 5.3-3.6 8.4-4.4" stroke="#D16F47" stroke-width="1.1" stroke-linecap="round"/></svg>';
    if(/우유|요거트|요구르트/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M10 4h4l1 2.4V18a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2V6.4L10 4Z" fill="#DDF1F4" stroke="#72A4A7" stroke-width="1.4"/><path d="M10 8h5" stroke="#72A4A7" stroke-linecap="round"/></svg>';
    if(/양파/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M12 5c1.3 1.1 4.8 4.1 4.8 8a4.8 4.8 0 1 1-9.6 0C7.2 9 10.7 6 12 5Z" fill="#F0DCC1" stroke="#B58D64" stroke-width="1.4"/><path d="M12 6.2V18" stroke="#C9A176" stroke-width="1.1"/></svg>';
    if(/계란|달걀/.test(n))return'<svg viewBox="0 0 24 24" fill="none"><path d="M12 5.2c3 0 5.5 3.8 5.5 7.7a5.5 5.5 0 1 1-11 0c0-3.9 2.5-7.7 5.5-7.7Z" fill="#FFF0C6" stroke="#CFA45B" stroke-width="1.4"/></svg>';
    return'<svg viewBox="0 0 24 24" fill="none"><path d="M5.5 10.5h13l-1.1 6.4a2 2 0 0 1-2 1.6H8.6a2 2 0 0 1-2-1.6l-1.1-6.4Z" fill="#ECEDE7" stroke="#7D857D" stroke-width="1.4"/></svg>';
  }
  function tone(d){return d<=1?['#ed6a61','#fff0ef']:d<=2?['#ef8d32','#fff3e8']:d<=4?['#eeba43','#fff8e7']:d<=6?['#5cae9e','#eaf7f4']:['#5f8c67','#eef5ee']}
  function renderItems(){
    items.sort((a,b)=>left(a.expiry)-left(b.expiry));const v=show?items:items.slice(0,6),box=$('#list');if(!box)return;box.innerHTML=v.length?'':'<div class="empty">재료를 추가하면 여기에서 시작해요.</div>';
    v.forEach(x=>{const d=left(x.expiry),t=tone(d),r=document.createElement('div'),i=items.indexOf(x);r.className='row';r.style.setProperty('--a',t[0]);r.style.setProperty('--b',t[1]);r.innerHTML=`<div class="ic">${icon(x.name)}</div><div><div class="nm">${esc(x.name)}</div><div class="ex">${fmt(x.expiry)}</div></div><div class="bar"><i style="width:${Math.max(15,95-Math.max(0,d)*10)}%"></i></div><div class="day">${dt(d)}</div><button class="rm" data-i="${i}" aria-label="${esc(x.name)} 삭제">×</button>`;box.appendChild(r)});
    if($('#sum'))$('#sum').textContent=`재료 ${items.length}개`;if($('#fc'))$('#fc').textContent=items.length;if($('#all'))$('#all').textContent=show?'접기 ↑':`전체 재료 ${items.length}개 보기 ›`;
    $$('.rm').forEach(b=>b.onclick=()=>{items.splice(+b.dataset.i,1);saveItems();renderItems();queueSync()})
  }
  function grid(arr,setv,id,key,customKey){const box=$(id);if(!box)return;box.innerHTML='';arr.forEach(n=>{const x=document.createElement('button');x.type='button';x.className='tog'+(setv.has(n)?' on':'');x.innerHTML=`<span>${setv.has(n)?'✓ ':''}${esc(n)}</span>${customKey&&readArray(customKey).includes(n)?`<i class="mini-x" data-del="${esc(n)}">×</i>`:''}`;x.onclick=e=>{const del=e.target.closest('.mini-x');if(del){e.stopPropagation();removeCustom(n,customKey,setv);return}setv.has(n)?setv.delete(n):setv.add(n);saveSet(key,setv);renderSets();queueSync()};box.appendChild(x)})}
  function renderSets(){grid(allSeason(),season,'#sg',SK,CSK);grid(allPantry(),pantry,'#pg',PK,CPK);if($('#sc'))$('#sc').textContent=season.size+pantry.size}
  function removeCustom(name,key,setv){if(key===CSK){customSeason=customSeason.filter(x=>x!==name);localStorage.setItem(CSK,JSON.stringify(customSeason))}else{customPantry=customPantry.filter(x=>x!==name);localStorage.setItem(CPK,JSON.stringify(customPantry))}setv.delete(name);saveSet(key===CSK?SK:PK,setv);renderSets();queueSync()}
  function render(){renderItems();renderSets();renderSyncStatus()}

  const payload=()=>({items,season:[...season],pantry:[...pantry],customSeason,customPantry,version:1});
  function applyPayload(p){if(!p||typeof p!=='object')return;items=Array.isArray(p.items)?p.items:items;season=new Set(Array.isArray(p.season)?p.season:[]);pantry=new Set(Array.isArray(p.pantry)?p.pantry:[]);customSeason=Array.isArray(p.customSeason)?uniq(p.customSeason):[];customPantry=Array.isArray(p.customPantry)?uniq(p.customPantry):[];saveItems();saveSet(SK,season);saveSet(PK,pantry);localStorage.setItem(CSK,JSON.stringify(customSeason));localStorage.setItem(CPK,JSON.stringify(customPantry));render()}
  const syncCode=()=>localStorage.getItem(SYNC_KEY)||'';
  function setStatus(text,ok=true){const el=$('#syncStatus');if(!el)return;el.textContent=text;el.classList.toggle('bad',!ok)}
  function renderSyncStatus(){setStatus(syncCode()?'이 기기는 동기화 연결됨':'이 기기는 아직 로컬 저장만 사용 중',!!syncCode())}
  function randomCode(){const a=new Uint8Array(18);crypto.getRandomValues(a);return'UMF-'+[...a].map(b=>b.toString(16).padStart(2,'0')).join('')}
  async function pushSync(){const code=syncCode();if(!code||syncBusy)return;syncBusy=true;setStatus('동기화 중…');try{const r=await fetch(SYNC_URL,{method:'PUT',headers:{'Content-Type':'application/json','x-sync-code':code},body:JSON.stringify({payload:payload()})});if(!r.ok)throw new Error();setStatus('동기화 완료')}catch{setStatus('동기화 실패 · 인터넷 연결 확인',false)}finally{syncBusy=false}}
  function queueSync(){if(!syncCode())return;clearTimeout(syncTimer);syncTimer=setTimeout(pushSync,500)}
  async function pullSync(code=syncCode()){if(!code)return null;setStatus('동기화 불러오는 중…');try{const r=await fetch(SYNC_URL,{headers:{'x-sync-code':code}});if(!r.ok)throw new Error();const j=await r.json();setStatus('동기화 완료');return j.payload}catch{setStatus('동기화 실패 · 인터넷 연결 확인',false);return null}}

  function openCustom(type){$('#customType').value=type;$('#customTitle').textContent=type==='season'?'기본 양념 추가':'상비 재료 추가';$('#customName').value='';$('#customModal').classList.add('on');setTimeout(()=>$('#customName')?.focus(),30)}
  function saveCustom(){const type=$('#customType').value,n=$('#customName').value.trim();if(!n)return;const arr=type==='season'?customSeason:customPantry,base=type==='season'?BASE_S:BASE_P;if([...base,...arr].includes(n)){alert('이미 있는 항목이에요.');return}if(type==='season'){customSeason=uniq([...customSeason,n]);localStorage.setItem(CSK,JSON.stringify(customSeason));season.add(n);saveSet(SK,season)}else{customPantry=uniq([...customPantry,n]);localStorage.setItem(CPK,JSON.stringify(customPantry));pantry.add(n);saveSet(PK,pantry)}$('#customModal').classList.remove('on');renderSets();queueSync()}
  function openSync(){const code=syncCode();$('#syncCode').value=code;$('#syncModal').classList.add('on');$('#syncHelp').textContent=code?'이 코드를 다른 기기에 입력하면 같은 냉장고를 불러와요.':'첫 기기라면 새 코드를 만들고, 다른 기기라면 기존 코드를 붙여넣으세요.'}
  async function createSync(){const code=randomCode();localStorage.setItem(SYNC_KEY,code);$('#syncCode').value=code;await pushSync();renderSyncStatus();$('#syncHelp').textContent='코드가 만들어졌어요. 다른 기기에서 같은 코드를 입력해 연결하세요.'}
  async function connectSync(){const code=$('#syncCode').value.trim();if(code.length<20){$('#syncHelp').textContent='동기화 코드를 확인해 주세요.';return}localStorage.setItem(SYNC_KEY,code);const remote=await pullSync(code);if(remote){applyPayload(remote);$('#syncHelp').textContent='다른 기기의 데이터를 불러왔어요.'}else{await pushSync();$('#syncHelp').textContent='새 동기화 공간으로 연결했어요.'}renderSyncStatus()}
  function disconnectSync(){localStorage.removeItem(SYNC_KEY);$('#syncCode').value='';$('#syncHelp').textContent='이 기기만 동기화 연결을 해제했어요. 로컬 데이터는 그대로예요.';renderSyncStatus()}

  $('.tabs')?.addEventListener('click',e=>{const b=e.target.closest('.tab');if(!b)return;$$('.tab').forEach(x=>x.classList.toggle('on',x===b));$('#fridge')?.classList.toggle('on',b.dataset.tab==='fridge');$('#season')?.classList.toggle('on',b.dataset.tab==='season');const add=$('#openAdd');if(add)add.style.display=b.dataset.tab==='fridge'?'block':'none'});
  $('#all')?.addEventListener('click',()=>{show=!show;renderItems()});
  const mb=$('#mb');$('#openAdd')?.addEventListener('click',()=>{mb?.classList.add('on');if($('#expiry'))$('#expiry').value=iso(3)});$('#close')?.addEventListener('click',()=>mb?.classList.remove('on'));$('#cancel')?.addEventListener('click',()=>mb?.classList.remove('on'));
  $('#save')?.addEventListener('click',()=>{const n=$('#name')?.value.trim(),e=$('#expiry')?.value;if(!n||!e)return;items.push({name:n,expiry:e});saveItems();if($('#name'))$('#name').value='';mb?.classList.remove('on');renderItems();queueSync()});
  $('#addSeason')?.addEventListener('click',()=>openCustom('season'));$('#addPantry')?.addEventListener('click',()=>openCustom('pantry'));$('#customClose')?.addEventListener('click',()=>$('#customModal')?.classList.remove('on'));$('#customCancel')?.addEventListener('click',()=>$('#customModal')?.classList.remove('on'));$('#customSave')?.addEventListener('click',saveCustom);$('#customName')?.addEventListener('keydown',e=>{if(e.key==='Enter')saveCustom()});
  $('#syncBtn')?.addEventListener('click',openSync);$('#syncClose')?.addEventListener('click',()=>$('#syncModal')?.classList.remove('on'));$('#syncCreate')?.addEventListener('click',createSync);$('#syncConnect')?.addEventListener('click',connectSync);$('#syncDisconnect')?.addEventListener('click',disconnectSync);$('#syncCopy')?.addEventListener('click',async()=>{const v=$('#syncCode')?.value;if(!v)return;try{await navigator.clipboard.writeText(v);$('#syncHelp').textContent='코드를 복사했어요.'}catch{$('#syncHelp').textContent='코드를 길게 눌러 복사해 주세요.'}});

  render();if(syncCode())pullSync().then(p=>{if(p)applyPayload(p)});
})();
