const SETTINGS_KEY='widget.marketEvents.controls.v2';
const root=document.getElementById('root'),widget=document.getElementById('widget');
const sizeBtn=document.getElementById('sizeBtn'),themeBtn=document.getElementById('themeBtn'),lockBtn=document.getElementById('lockBtn'),resetBtn=document.getElementById('resetBtn');
const q=new URLSearchParams(location.search), osTheme=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
let settings={theme:q.get('theme')||osTheme,size:'normal',locked:false};
try{settings={...settings,...JSON.parse(localStorage.getItem(SETTINGS_KEY)||'{}')}}catch{}
function save(){localStorage.setItem(SETTINGS_KEY,JSON.stringify(settings))}
function applyTheme(v){document.documentElement.dataset.theme=v;settings.theme=v;save()}
function applySize(v){root.dataset.size=v;settings.size=v;save();sizeBtn.disabled=settings.locked}
function applyLock(v){settings.locked=v;save();sizeBtn.disabled=v;lockBtn.dataset.tip=v?'Unlock':'Lock';document.getElementById('lockSvg').innerHTML=v?'<rect x="5" y="11" width="14" height="9" rx="2.5" stroke="currentColor" stroke-width="1.8"/><path d="M8 11V8.7a4 4 0 0 1 8 0V11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>':'<path d="M7 11V8.5a5 5 0 0 1 10 0V11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><rect x="5" y="11" width="14" height="9" rx="2.5" stroke="currentColor" stroke-width="1.8"/>'}
applyTheme(settings.theme);applySize(settings.size);applyLock(settings.locked);
themeBtn.onclick=()=>applyTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');
sizeBtn.onclick=()=>{if(settings.locked)return;const a=['compact','normal','large'];applySize(a[(a.indexOf(settings.size)+1)%a.length])};
lockBtn.onclick=()=>applyLock(!settings.locked);
resetBtn.onclick=()=>{settings={theme:q.get('theme')||osTheme,size:'normal',locked:false};applyTheme(settings.theme);applySize(settings.size);applyLock(false)};

const icons={
 rate:'<svg viewBox="0 0 24 24" fill="none"><path d="M4 10h16M6 10v8m4-8v8m4-8v8m4-8v8M3 20h18M4 8l8-4 8 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
 inflation:'<svg viewBox="0 0 24 24" fill="none"><path d="M4 18V6M4 18h16M7 14l3-4 4 3 3-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
 jobs:'<svg viewBox="0 0 24 24" fill="none"><circle cx="9" cy="9" r="3" stroke="currentColor" stroke-width="1.8"/><circle cx="17" cy="10" r="2.4" stroke="currentColor" stroke-width="1.8"/><path d="M4 18c0-2.4 2.2-4 5-4s5 1.6 5 4M15 17c.5-1.5 2-2.6 4-2.6 1.1 0 2 .3 2.8.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
 growth:'<svg viewBox="0 0 24 24" fill="none"><path d="M5 18V9m5 9V5m5 13v-7m4 7V7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
 other:'<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.8"/><path d="M8 12h8M12 8v8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'
};
const categoryLabel={rate:'금리 결정',inflation:'인플레이션',jobs:'고용지표',growth:'성장·경기',other:'기타'};
const tone={rate:'red',inflation:'amber',jobs:'green',growth:'blue',other:'green'};
const flags={US:'🇺🇸',KR:'🇰🇷',JP:'🇯🇵',GB:'🇬🇧',DE:'🇩🇪',FR:'🇫🇷',CN:'🇨🇳',EU:'🇪🇺'};
let currentData=null;

function dots(n){return Array.from({length:3},(_,i)=>`<span class="dot ${i<n?'on':''}"></span>`).join('')}
function escapeHtml(s=''){return s.replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
function eventHtml(e,hidden=false){return `<div class="event extra-event" ${hidden?'hidden':''}><div class="time">${escapeHtml(e.time_kst||'—')}</div><div class="event-main"><div class="event-title"><span class="country">${flags[e.country]||e.country||''}</span>${escapeHtml(e.title_ko||e.title||'')}</div><div class="tag-row"><span class="badge ${tone[e.category]||'green'}">${escapeHtml(categoryLabel[e.category]||'경제지표')}</span>${e.importance>=3?'<span class="badge red">높은 영향도</span>':''}</div></div></div>`}
function renderColumn(key,title,en,events){
  const first=events.slice(0,3), rest=events.slice(3);
  return `<div class="col" data-col="${key}"><div class="col-head"><div class="col-title">${title}</div><div class="col-en">${en}</div></div><div class="list">${first.map(e=>eventHtml(e)).join('')}${rest.map(e=>eventHtml(e,true)).join('')||'<div class="empty" '+(first.length?'hidden':'')+'>예정 이벤트 없음</div>'}</div><button class="more" ${rest.length?'':'hidden'} data-toggle="${key}">더 보기 〉</button></div>`;
}
function render(data){
  currentData=data;
  const ev=data.events||[];
  const highlight=data.highlight||ev[0];
  document.getElementById('updated').textContent=data.stale?'업데이트 지연':`업데이트 · ${data.updated_label||'최근'}`;
  document.getElementById('retry').hidden=!data.stale;
  document.getElementById('source').textContent=`Source · ${data.source||'TradingView Economic Calendar'} · KST`;
  if(highlight){
    document.getElementById('heroIcon').innerHTML=icons[highlight.category]||icons.other;
    document.getElementById('heroTitle').textContent=highlight.title_ko||highlight.title;
    document.getElementById('heroDate').textContent=highlight.date_kst||'—';
    document.getElementById('heroTime').textContent=highlight.time_kst||'—';
    document.getElementById('heroDesc').textContent=highlight.comment_ko||highlight.comment||'주요 경제 이벤트';
    document.getElementById('heroImpact').textContent=highlight.importance>=3?'높은 영향도':highlight.importance===2?'중간 영향도':'낮은 영향도';
    document.getElementById('heroDots').innerHTML=dots(Math.min(3,Math.max(1,highlight.importance||1)));
  } else {
    document.getElementById('heroIcon').innerHTML=icons.other;
    document.getElementById('heroTitle').textContent='예정 이벤트를 불러오는 중';
    document.getElementById('heroDate').textContent='—';document.getElementById('heroTime').textContent='—';document.getElementById('heroImpact').textContent='—';document.getElementById('heroDots').innerHTML='';
  }
  const cats=['rate','inflation','jobs','growth'];
  document.getElementById('summary').innerHTML=cats.map(c=>{
    const arr=ev.filter(e=>e.category===c), max=Math.max(0,...arr.map(e=>e.importance||0));
    return `<div class="sum"><div class="sum-top"><div class="sum-icon">${icons[c]}</div><div><div class="sum-title">${categoryLabel[c]}</div><div class="sum-sub">${arr.length}개 예정</div></div></div><div class="dots" style="margin-top:8px">${dots(Math.min(3,max))}</div></div>`
  }).join('');
  const today=ev.filter(e=>e.bucket==='today'), week=ev.filter(e=>e.bucket==='week'), later=ev.filter(e=>e.bucket==='later');
  document.getElementById('board').innerHTML=renderColumn('today','오늘','Today',today)+renderColumn('week','이번 주','This Week',week)+renderColumn('later','Later','Later',later);
  document.querySelectorAll('[data-toggle]').forEach(btn=>btn.onclick=()=>{
    const col=btn.closest('.col'), extras=col.querySelectorAll('.extra-event[hidden]');
    if(extras.length){extras.forEach(x=>x.hidden=false);btn.textContent='접기 ⌃'}else{[...col.querySelectorAll('.extra-event')].slice(3).forEach(x=>x.hidden=true);btn.textContent='더 보기 〉'}
  });
}
async function load(){
  try{
    const r=await fetch(`./market-events-data.json?t=${Date.now()}`,{cache:'no-store'});
    if(!r.ok)throw new Error(r.status);
    render(await r.json());
  }catch(e){
    render({source:'TradingView Economic Calendar',stale:true,updated_label:'지연',events:[],highlight:null});
  }
}
document.getElementById('retry').onclick=load;
load();