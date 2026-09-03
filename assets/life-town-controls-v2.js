(()=>{
  const colorStyleId='lt-color-balance-v2';
  if(!document.getElementById(colorStyleId)){
    const link=document.createElement('link');
    link.id=colorStyleId;link.rel='stylesheet';link.href='./assets/life-town-color-balance-v2.css?v=20260903-worktoday-color2';
    document.head.appendChild(link);
  }
  if(document.querySelector('#todayList')&&document.querySelector('#tomorrowList')&&document.querySelector('#weekList')){
    const wtStyleId='lt-work-today-palette-v3';
    if(!document.getElementById(wtStyleId)){
      const wt=document.createElement('link');
      wt.id=wtStyleId;wt.rel='stylesheet';wt.href='./assets/work-today-palette-v3.css?v=20260903-6';
      document.head.appendChild(wt);
    }
  }
  if(document.querySelector('.lt-control-rail')) return;
  const root=document.documentElement;
  const target=document.querySelector('[data-widget-control-root]')||document.querySelector('.widget')||document.querySelector('.card')||document.querySelector('.w');
  if(!target) return;
  const host=target.parentElement;
  if(!host) return;
  host.classList.add('lt-control-host');

  const slug=(target.dataset.widgetKey||document.body.dataset.widgetKey||document.title||location.pathname.split('/').pop()||'widget')
    .toLowerCase().replace(/[^a-z0-9가-힣]+/g,'-').replace(/^-|-$/g,'');
  const key=`lifetown-control-v2:${slug}`;
  const parseSizes=()=>{
    const raw=target.dataset.controlSizes||host.dataset.controlSizes||'';
    const arr=raw.split(',').map(x=>parseInt(x.trim(),10)).filter(Number.isFinite);
    if(arr.length>=2) return arr;
    const max=parseInt(getComputedStyle(host).maxWidth,10)||parseInt(getComputedStyle(target).maxWidth,10)||420;
    if(max<=380) return [280,320,360];
    if(max<=540) return [340,420,520];
    return [360,520,680];
  };
  const sizes=parseSizes();
  let state={sizeIndex:sizes.length-1,theme:'light',locked:false};
  try{state={...state,...JSON.parse(localStorage.getItem(key)||'{}')}}catch{}
  if(!['light','dark'].includes(state.theme)) state.theme='light';
  if(!Number.isInteger(state.sizeIndex)||state.sizeIndex<0||state.sizeIndex>=sizes.length) state.sizeIndex=sizes.length-1;

  const icons={
    size:'<svg viewBox="0 0 24 24"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/><path d="M3 8l5-5M21 8l-5-5M3 16l5 5M21 16l-5 5"/></svg>',
    moon:'<svg viewBox="0 0 24 24"><path d="M20.5 15.2A8 8 0 0 1 8.8 3.5 8.5 8.5 0 1 0 20.5 15.2Z"/></svg>',
    sun:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    lock:'<svg viewBox="0 0 24 24"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 1 1 8 0v3"/></svg>',
    unlock:'<svg viewBox="0 0 24 24"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 7.5-2"/></svg>',
    reset:'<svg viewBox="0 0 24 24"><path d="M4 8V4h4"/><path d="M5.5 5.5A8 8 0 1 1 4.2 14"/></svg>'
  };

  const rail=document.createElement('div');
  rail.className='lt-control-rail';
  rail.innerHTML='<span class="lt-control-line" aria-hidden="true"></span>';
  host.appendChild(rail);
  function makeButton(name,label,icon){
    const b=document.createElement('button');
    b.type='button';b.className=`lt-control-btn lt-control-${name}`;b.setAttribute('aria-label',label);b.dataset.tip=label;b.innerHTML=icon;rail.appendChild(b);return b;
  }
  const sizeBtn=makeButton('size','크기 변경',icons.size),themeBtn=makeButton('theme','다크 모드',icons.moon),lockBtn=makeButton('lock','크기 잠금',icons.unlock),resetBtn=makeButton('reset','UI 초기화',icons.reset);

  const css=document.createElement('style');
  css.textContent=`
  .lt-control-host{position:relative!important;overflow:visible!important;transition:width .18s ease,max-width .18s ease}
  .lt-control-host>.tools,.lt-control-host>.hoverTools{display:none!important}
  .lt-control-rail{position:absolute;top:8px;right:-32px;z-index:999;width:38px;min-height:165px;display:flex;flex-direction:column;align-items:flex-end;gap:7px;padding:0 0 4px 6px;opacity:0;visibility:visible;pointer-events:auto;transform:translateX(-3px);transition:opacity .14s ease,transform .14s ease}
  .lt-control-rail:hover{opacity:1;transform:translateX(0)}
  .lt-control-rail:not(:hover) .lt-control-btn{pointer-events:none}
  .lt-control-line{position:absolute;right:28px;top:0;bottom:0;width:1px;background:linear-gradient(180deg,rgba(142,142,147,.05),rgba(142,142,147,.22) 15%,rgba(142,142,147,.12) 84%,rgba(142,142,147,.02));border-radius:999px}
  .lt-control-btn{position:relative;width:30px;height:30px;min-width:30px;min-height:30px;border:1px solid #e2e2e6;background:rgba(255,255,255,.97);color:#6e6e73;border-radius:50%;display:grid;place-items:center;padding:0;cursor:pointer;box-shadow:0 3px 12px rgba(0,0,0,.06);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);transition:transform .14s ease,background .14s ease,color .14s ease,border-color .14s ease,opacity .14s ease}
  .lt-control-btn:hover{transform:translateY(-1px);background:#f7f7f8;color:#111113;border-color:#d4d4d8}
  .lt-control-btn svg{width:13px;height:13px;fill:none;stroke:currentColor;stroke-width:1.65;stroke-linecap:round;stroke-linejoin:round}
  .lt-control-btn.is-active{background:#f1f1f3;color:#111113;border-color:#cfcfd4}
  .lt-control-btn:disabled{opacity:.35;cursor:not-allowed;transform:none}
  .lt-control-btn:after{content:attr(data-tip);position:absolute;right:37px;top:50%;transform:translate(4px,-50%);opacity:0;pointer-events:none;white-space:nowrap;background:rgba(28,28,30,.92);color:#fff;border-radius:7px;padding:5px 7px;font-size:9px;font-weight:600;line-height:1;transition:.12s ease}
  .lt-control-btn:hover:after{opacity:1;transform:translate(0,-50%)}
  html[data-lt-theme="dark"]{color-scheme:dark;--lt-bg:#000;--lt-surface:#1c1c1e;--lt-surface-2:#2c2c2e;--lt-text:#f5f5f7;--lt-sub:#aeaeb2;--lt-muted:#8e8e93;--lt-line:#38383a;--lt-line-strong:#48484a;--lt-shadow:none}
  html[data-lt-theme="dark"] body{color:#f5f5f7!important}
  html[data-lt-theme="dark"] .card,html[data-lt-theme="dark"] .widget,html[data-lt-theme="dark"] .w{background:#1c1c1e!important;border-color:#38383a!important;color:#f5f5f7!important;box-shadow:none!important}
  html[data-lt-theme="dark"] input,html[data-lt-theme="dark"] select{background:#2c2c2e!important;border-color:#48484a!important;color:#f5f5f7!important}
  html[data-lt-theme="dark"] .lt-control-btn{background:rgba(44,44,46,.97);color:#aeaeb2;border-color:#48484a;box-shadow:0 3px 12px rgba(0,0,0,.26)}
  html[data-lt-theme="dark"] .lt-control-btn:hover,html[data-lt-theme="dark"] .lt-control-btn.is-active{background:#3a3a3c;color:#fff;border-color:#5a5a5e}
  @media(hover:none){.lt-control-rail{right:-30px;opacity:.92;transform:none}.lt-control-rail .lt-control-btn{pointer-events:auto}.lt-control-btn:after{display:none}}
  @media(max-width:390px){.lt-control-rail{right:-30px;width:34px;min-height:150px;padding-left:4px;gap:6px}.lt-control-btn{width:28px;height:28px;min-width:28px;min-height:28px}.lt-control-btn svg{width:12px;height:12px}}
  `;
  document.head.appendChild(css);

  function persist(){try{localStorage.setItem(key,JSON.stringify(state))}catch{}}
  function apply(){
    const px=sizes[state.sizeIndex];host.style.width='100%';host.style.maxWidth=px+'px';
    if(getComputedStyle(root).getPropertyValue('--card-w').trim()) root.style.setProperty('--card-w',px+'px');
    root.dataset.ltTheme=state.theme;root.dataset.theme=state.theme;sizeBtn.disabled=!!state.locked;
    lockBtn.classList.toggle('is-active',!!state.locked);lockBtn.innerHTML=state.locked?icons.lock:icons.unlock;lockBtn.dataset.tip=state.locked?'크기 잠금 해제':'크기 잠금';lockBtn.setAttribute('aria-label',lockBtn.dataset.tip);
    themeBtn.innerHTML=state.theme==='dark'?icons.sun:icons.moon;themeBtn.dataset.tip=state.theme==='dark'?'라이트 모드':'다크 모드';themeBtn.setAttribute('aria-label',themeBtn.dataset.tip);
  }
  sizeBtn.onclick=()=>{if(state.locked)return;state.sizeIndex=(state.sizeIndex+1)%sizes.length;persist();apply()};
  themeBtn.onclick=()=>{state.theme=state.theme==='dark'?'light':'dark';persist();apply()};
  lockBtn.onclick=()=>{state.locked=!state.locked;persist();apply()};
  resetBtn.onclick=()=>{state={sizeIndex:sizes.length-1,theme:'light',locked:false};localStorage.removeItem(key);apply()};
  apply();
})();
