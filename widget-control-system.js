(()=>{
  const root=document.documentElement;
  const card=document.querySelector('.w');
  if(!card||document.querySelector('.widget-control-rail')) return;

  const slug=(document.body.dataset.widgetKey||document.title||location.pathname.split('/').pop()||'widget')
    .toLowerCase().replace(/[^a-z0-9가-힣]+/g,'-').replace(/^-|-$/g,'');
  const KEY=`widget-control:${slug}:v1`;
  const defaults={size:'normal',theme:null,locked:false};
  let saved={};
  try{saved=JSON.parse(localStorage.getItem(KEY))||{}}catch(e){}
  const state={...defaults,...saved};
  if(!state.theme) state.theme=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';

  const shell=document.createElement('div');
  shell.className='widget-control-shell';
  card.parentNode.insertBefore(shell,card);
  shell.appendChild(card);

  const oldTools=card.querySelector('.hoverTools');
  const syncBtn=document.getElementById('syncBtn');
  if(oldTools) oldTools.remove();

  const rail=document.createElement('div');
  rail.className='widget-control-rail';
  rail.setAttribute('aria-label','위젯 컨트롤');
  shell.appendChild(rail);

  const icons={
    size:'<svg viewBox="0 0 24 24"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/><path d="M3 8l5-5M21 8l-5-5M3 16l5 5M21 16l-5 5"/></svg>',
    dark:'<svg viewBox="0 0 24 24"><path d="M20.5 15.2A8 8 0 0 1 8.8 3.5 8.5 8.5 0 1 0 20.5 15.2Z"/></svg>',
    light:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    lock:'<svg viewBox="0 0 24 24"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>',
    unlock:'<svg viewBox="0 0 24 24"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 7.5-2"/></svg>',
    reset:'<svg viewBox="0 0 24 24"><path d="M4 8V4h4"/><path d="M5.5 5.5A8 8 0 1 1 4.2 14"/></svg>'
  };

  function btn(id,tip,svg){
    const b=document.createElement('button');
    b.type='button'; b.className='widget-control-btn'; b.id=id; b.dataset.tip=tip; b.setAttribute('aria-label',tip); b.innerHTML=svg; rail.appendChild(b); return b;
  }
  const sizeBtn=btn('widgetSizeControl','크기 변경',icons.size);
  const themeBtn=btn('widgetThemeControl','다크 모드',icons.dark);
  const lockBtn=btn('widgetLockControl','크기 잠금',icons.unlock);
  const resetBtn=btn('widgetResetControl','UI 초기화',icons.reset);

  if(syncBtn){
    syncBtn.classList.remove('hoverTool');
    syncBtn.classList.add('widget-control-btn','widget-sync-control');
    syncBtn.dataset.tip='동기화 설정';
    rail.appendChild(syncBtn);
  }

  const css=document.createElement('style');
  css.textContent=`
  :root{--wc-bg:#fff;--wc-fg:#657067;--wc-border:#dfe4de;--wc-shadow:0 3px 10px rgba(42,51,43,.08)}
  html[data-widget-theme="dark"]{color-scheme:dark;--wc-bg:#262a27;--wc-fg:#d7ddd7;--wc-border:#404640;--wc-shadow:0 4px 12px rgba(0,0,0,.24)}
  body{padding-right:44px!important;transition:background .18s ease}
  .widget-control-shell{position:relative;width:min(100%,var(--widget-max,430px));margin:0 auto;transition:width .18s ease,max-width .18s ease}
  .widget-control-shell>.w{width:100%!important;max-width:none!important;margin:0!important;transition:background .18s ease,border-color .18s ease,box-shadow .18s ease,padding .18s ease}
  html[data-widget-size="compact"] .widget-control-shell{--widget-max:360px}
  html[data-widget-size="normal"] .widget-control-shell{--widget-max:430px}
  html[data-widget-size="large"] .widget-control-shell{--widget-max:520px}
  .widget-control-rail{position:absolute;top:8px;right:-38px;z-index:30;display:flex;flex-direction:column;gap:5px;opacity:0;transform:translateX(-3px);pointer-events:none;transition:opacity .18s ease,transform .18s ease}
  .widget-control-shell:hover>.widget-control-rail,.widget-control-shell:focus-within>.widget-control-rail{opacity:1;transform:translateX(0);pointer-events:auto}
  .widget-control-btn{width:28px;height:28px;border:1px solid var(--wc-border)!important;background:var(--wc-bg)!important;color:var(--wc-fg)!important;border-radius:9px!important;display:grid!important;place-items:center!important;padding:0!important;box-shadow:var(--wc-shadow)!important;position:relative!important;cursor:pointer!important;transition:background .15s ease,color .15s ease,transform .15s ease,opacity .15s ease!important}
  .widget-control-btn:hover{transform:translateY(-1px);filter:brightness(.98)}
  .widget-control-btn svg{width:14px!important;height:14px!important;fill:none!important;stroke:currentColor!important;stroke-width:1.7!important;stroke-linecap:round!important;stroke-linejoin:round!important}
  .widget-control-btn:after{content:attr(data-tip);position:absolute;right:35px;top:50%;transform:translateY(-50%) translateX(3px);background:#30352f;color:#fff;font-size:7.5px;line-height:1;padding:5px 6px;border-radius:6px;white-space:nowrap;opacity:0;pointer-events:none;transition:.12s}
  .widget-control-btn:hover:after{opacity:1;transform:translateY(-50%) translateX(0)}
  .widget-control-btn.is-active{background:#eef4ee!important;color:#4f7355!important;border-color:#cbdccb!important}
  html[data-widget-theme="dark"] .widget-control-btn.is-active{background:#344238!important;color:#cfe4d3!important;border-color:#526458!important}
  .widget-control-btn:disabled{opacity:.38!important;cursor:not-allowed!important;transform:none!important}
  .widget-control-btn .syncDot{position:absolute;right:3px;bottom:3px;width:6px;height:6px;border-radius:50%;background:#c7cbc5;border:1px solid var(--wc-bg)}
  .widget-control-btn .syncDot.on{background:#6f9b73}.widget-control-btn .syncDot.bad{background:#d47b70}
  .head{padding-right:0!important}

  html[data-widget-theme="dark"] body{background:transparent!important;color:#e7ebe7!important}
  html[data-widget-theme="dark"] .w{background:#1f2320!important;border-color:#3a403a!important;box-shadow:0 8px 24px rgba(0,0,0,.22)!important;color:#e8ece8!important}
  html[data-widget-theme="dark"] .sub,html[data-widget-theme="dark"] .ss,html[data-widget-theme="dark"] .ex,html[data-widget-theme="dark"] .use,html[data-widget-theme="dark"] .lbl{color:#9fa8a0!important}
  html[data-widget-theme="dark"] .tabs{background:#272c28!important;border-color:#3a403a!important}
  html[data-widget-theme="dark"] .tab{color:#aeb6af!important}html[data-widget-theme="dark"] .tab.on{background:#343a35!important;color:#e3e9e4!important;box-shadow:none!important}
  html[data-widget-theme="dark"] .card,html[data-widget-theme="dark"] .season,html[data-widget-theme="dark"] .recipe,html[data-widget-theme="dark"] .modal{background:#252a26!important;border-color:#3b423c!important;color:#e6ebe7!important}
  html[data-widget-theme="dark"] .row{border-color:#343a35!important}html[data-widget-theme="dark"] .row:hover{background:#2b302c!important}
  html[data-widget-theme="dark"] .foot,html[data-widget-theme="dark"] .rb,html[data-widget-theme="dark"] .detail{background:#232824!important;border-color:#383e39!important;color:#b6beb7!important}
  html[data-widget-theme="dark"] .ic,html[data-widget-theme="dark"] .meta span,html[data-widget-theme="dark"] .chip{background:#2f3530!important;border-color:#414841!important;color:#dfe5df!important}
  html[data-widget-theme="dark"] .tog{background:#2b302c!important;border-color:#3b423c!important;color:#bfc7c0!important}html[data-widget-theme="dark"] .tog.on{background:#344238!important;border-color:#526458!important;color:#d9e9dc!important}
  html[data-widget-theme="dark"] .add,html[data-widget-theme="dark"] .tinyAdd,html[data-widget-theme="dark"] .pill,html[data-widget-theme="dark"] .act{background:#303631!important;border-color:#414841!important;color:#dce3dc!important}
  html[data-widget-theme="dark"] .act.primary,html[data-widget-theme="dark"] .save{background:#607c64!important;border-color:#607c64!important;color:#fff!important}
  html[data-widget-theme="dark"] .recipe{background:#2b2925!important;border-color:#4b443a!important}
  html[data-widget-theme="dark"] .visual{background:#302d28!important}
  html[data-widget-theme="dark"] .tip,html[data-widget-theme="dark"] .syncHelp{background:#293029!important;border-color:#3b473c!important;color:#aab5ab!important}
  html[data-widget-theme="dark"] input{background:#242925!important;border-color:#404740!important;color:#e7ece8!important}
  html[data-widget-theme="dark"] .modalbg{background:rgba(0,0,0,.5)!important}

  @media(hover:none){.widget-control-rail{opacity:1;transform:none;pointer-events:auto}.widget-control-btn:after{display:none}}
  @media(max-width:390px){body{padding-right:38px!important}.widget-control-rail{right:-33px;top:7px}.widget-control-btn{width:26px;height:26px}.widget-control-btn svg{width:13px!important;height:13px!important}}
  `;
  document.head.appendChild(css);

  function persist(){
    localStorage.setItem(KEY,JSON.stringify(state));
  }
  function apply(){
    root.dataset.widgetSize=state.size;
    root.dataset.widgetTheme=state.theme;
    root.dataset.widgetLocked=state.locked?'true':'false';
    sizeBtn.disabled=!!state.locked;
    lockBtn.classList.toggle('is-active',!!state.locked);
    lockBtn.innerHTML=state.locked?icons.lock:icons.unlock;
    lockBtn.dataset.tip=state.locked?'크기 잠금 해제':'크기 잠금';
    themeBtn.innerHTML=state.theme==='dark'?icons.light:icons.dark;
    themeBtn.dataset.tip=state.theme==='dark'?'라이트 모드':'다크 모드';
  }
  function cycleSize(){
    if(state.locked) return;
    const sizes=['compact','normal','large'];
    state.size=sizes[(sizes.indexOf(state.size)+1)%sizes.length];
    persist();apply();
  }
  sizeBtn.addEventListener('click',cycleSize);
  themeBtn.addEventListener('click',()=>{state.theme=state.theme==='dark'?'light':'dark';persist();apply()});
  lockBtn.addEventListener('click',()=>{state.locked=!state.locked;persist();apply()});
  resetBtn.addEventListener('click',()=>{state.size='normal';state.theme=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';state.locked=false;localStorage.removeItem(KEY);apply()});

  const ro=new ResizeObserver(entries=>{
    const w=entries[0].contentRect.width;
    root.dataset.widgetWidth=w<330?'narrow':w<390?'medium':'wide';
  });
  ro.observe(card);
  apply();
})();