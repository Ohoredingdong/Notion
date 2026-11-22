'use strict';
// THE PLAY ARCHIVE: modular solo-AI games extension
  const extNew={
    '해 달 별':{rule:'관전자 10명이 숨긴 해·달·별 중 하나를 예측해 베팅합니다. 4칩으로 시작하여 선공/후공 베팅 조건을 따르고, 맞히면 베팅액 3배를 받습니다. 사전 동맹·관전자 설득은 제외한 연습판입니다.',genre:'베팅 · 추리',desc:'관전자 열 명의 선택을 맞히세요',mark:'☼',mode:'ss'},
    '하나 빼기':{rule:'7명이 숫자 1~8 카드 중 두 장을 공개한 뒤 한 장을 비밀로 선택합니다. 중복되지 않은 가장 작은 수가 승리합니다. 3·6·9·12라운드에는 생존자를 선정하며 총 18라운드로 진행됩니다.',genre:'심리 · 카드',desc:'두 장을 공개하고 한 장을 남기세요',mark:'Ⅰ',mode:'ro'}
  };
  Object.assign(extensionDetails,extNew);
  Object.entries(extNew).forEach(([name,v])=>{
    supported[name]=v.rule;
    ruleStatus[name]='핵심 규칙 구현 · AI 연습';
    const match=entries.filter(e=>e.name===name);
    match.forEach(e=>e.playable=true);
    gameProfiles[name]={genre:v.genre,desc:v.desc};
    if(!osGames.includes(name)) osGames.push(name);
    const symbol=v.mark;
    const img=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400"><defs><radialGradient id="g"><stop stop-color="#65334b"/><stop offset="1" stop-color="#130b18"/></radialGradient></defs><rect width="640" height="400" fill="url(#g)"/><circle cx="320" cy="194" r="133" fill="#130e18" stroke="#bd936b" stroke-width="3"/><circle cx="320" cy="194" r="119" fill="none" stroke="#ab7384" stroke-width="2"/><text x="320" y="252" text-anchor="middle" font-family="Georgia,serif" font-size="155" fill="#f2c88e">${symbol}</text></svg>`;
    gamePosters[name]='data:image/svg+xml;charset=UTF-8,'+encodeURIComponent(img);
  });
  const origInitExt=initExtension,origDrawExt=drawExtension;
  initExtension=function(name){
    if(name==='해 달 별') ssInit();
    else if(name==='하나 빼기') roInit();
    else origInitExt(name);
  };
  drawExtension=function(){
    if(st.ext==='ss')return ssDraw();
    if(st.ext==='ro')return roDraw();
    return origDrawExt();
  };
  const ssNames=['☼ 해','☾ 달','✦ 별'];
  function ssInit(){st={ext:'ss',round:1,chips:[4,4],signs:Array.from({length:10},()=>randint(3)),first:0,phase:'ready',chosen:0,bets:[null,null],last:null};ssNew()}
  function ssAi(first){
    if(first){
      const max=Math.min(st.chips[1],Math.floor(st.chips[0]/2));
      return {sign:randint(3),amount:rand(0,Math.min(3,max))};
    }
    const minimum=st.bets[0].amount*2;
    return {sign:randint(3),amount:Math.min(st.chips[1],minimum+rand(0,Math.min(3,st.chips[1]-minimum)))};
  }
  function ssNew(){
    if(st.round>10||st.chips.some(x=>x<=0)){ssEnd();return}
    st.first=(st.round+1)%2;
    st.chosen=0;st.bets=[null,null];st.last=null;
    if(st.first===1)st.bets[1]=ssAi(true);
    st.phase='bet';render();
  }
  function ssBounds(){
    return st.first===0?[0,Math.min(st.chips[0],Math.floor(st.chips[1]/2))]:
      [st.bets[1].amount*2,st.chips[0]];
  }
  function ssBet(){
    if(finishText||st.phase!=='bet')return;
    const [min,max]=ssBounds(),amount=Number(document.getElementById('ss-amount')?.value);
    if(!Number.isInteger(amount)||amount<min||amount>max){logit(`베팅 허용 범위: ${min}~${max}칩`);render();return}
    st.bets[0]={sign:st.chosen,amount};
    if(st.first===0)st.bets[1]=ssAi(false);
    const actual=st.signs[st.round-1];
    st.bets.forEach((b,i)=>{st.chips[i]-=b.amount;if(b.sign===actual)st.chips[i]+=b.amount*3});
    st.last={actual,bets:st.bets};
    st.phase='reveal';
    logit(`${st.round}회 · 정답 ${ssNames[actual]} · 나 ${st.bets[0].amount}칩 ${st.bets[0].sign===actual?'적중':'실패'}`);
    render();
  }
  function ssContinue(){if(st.phase!=='reveal')return;st.round++;ssNew()}
  function ssEnd(){const [a,b]=st.chips;finish(a===b?null:a>b,`최종 보유 칩 나 ${a}, AI ${b}`);st.phase='done';render()}
  function ssDraw(){
    const [min,max]=ssBounds(),betting=st.phase==='bet';
    stage(`<div class="toolbar"><span class="counter">${Math.min(10,st.round)} / 10 라운드</span><span class="counter">${st.first===0?'내가 선공':'AI 선공'}</span></div>
      ${scores(['내 칩','AI 칩'],st.chips)}
      <div class="info">${betting?st.first===0?'먼저 베팅하세요. AI 칩의 절반까지만 사용할 수 있습니다.':`AI가 먼저 ${st.bets[1].amount}칩 베팅했습니다. 그 두 배 이상 베팅해야 합니다.`:`숨겨진 표식: ${ssNames[st.last?.actual??0]}`}</div>
      <div class="ss-symbols">${ssNames.map((n,i)=>`<button class="${st.chosen===i?'active':''}" onclick="st.chosen=${i};render()" ${!betting?'disabled':''}>${n}</button>`).join('')}</div>
      ${betting?`<div class="toolbar"><label class="label">베팅 칩 <input class="inp" id="ss-amount" type="number" value="${min}" min="${min}" max="${max}" aria-label="베팅 칩"></label>${action('베팅 확정','ssBet()',min>max)}</div>`:
      st.phase==='reveal'?`<div class="toolbar">${action(st.round===10?'최종 결과':'다음 관전자','ssContinue()')}</div>`:''}
      <p class="small">사용 가능 ${min}~${max}칩 · 관전자 ${Math.min(st.round,10)}명째 · 실제 방송 출연자의 사전 협상은 생략되었습니다.</p>`,
      '<p class="muted">표식이 맞으면 베팅액의 세 배를 받고, 틀리면 베팅한 칩을 잃습니다. 총 10명의 관전자가 등장합니다.</p>');
  }
  function roInit(){
    st={ext:'ro',round:1,phase:'pair',active:[0,1,2,3,4,5,6],hands:Array.from({length:7},()=>[1,2,3,4,5,6,7,8]),cool:Array.from({length:7},()=>[]),score:Array(7).fill(0),badge:Array(7).fill(0),lastwin:Array(7).fill(0),pairs:Array(7).fill(null),mark:Array(7).fill(null),pass:[],select:[],results:[]};
    roNew();
  }
  function roNew(){
    if(st.round>18){roEnd();return}
    st.phase='pair';st.pairs=Array(7).fill(null);st.mark=Array(7).fill(null);st.select=[];st.results=[];
    for(const i of st.active){
      let available=st.hands[i].filter(x=>!st.cool[i].includes(x));
      if(available.length<2){st.cool[i]=[];available=[...st.hands[i]]}
      if(i!==0){
        let first=pick(available.filter(x=>x<5).length?available.filter(x=>x<5):available);
        let second=pick(available.filter(x=>x!==first));
        st.pairs[i]=[first,second];
      }
    }render();
  }
  function roToggle(n){
    if(st.phase!=='pair'||finishText)return;
    const eligible=st.hands[0].filter(x=>!st.cool[0].includes(x));
    if(!eligible.includes(n))return;
    if(st.select.includes(n))st.select=st.select.filter(x=>x!==n);
    else if(st.select.length<2)st.select.push(n);
    render();
  }
  function roReveal(){
    if(st.phase!=='pair'||st.select.length!==2)return;
    st.pairs[0]=[...st.select];st.phase='mark';render();
  }
  function roConfirm(side){
    if(st.phase!=='mark'||finishText)return;
    st.mark[0]=side;
    for(const i of st.active.filter(x=>x!==0)){
      const a=st.pairs[i],small=Math.min(...a),count=st.active.filter(x=>x!==i).flatMap(x=>st.pairs[x]||[]).filter(x=>x===small).length;
      st.mark[i]=Math.random()<Math.min(.8,.2+count*.16)?(a[0]===small?1:0):(a[0]===small?0:1);
    }
    const picks=st.active.map(i=>[i,st.pairs[i][st.mark[i]]]);
    const counts=new Map();picks.forEach(([,n])=>counts.set(n,(counts.get(n)||0)+1));
    const candidates=picks.filter(([,n])=>counts.get(n)===1).sort((a,b)=>a[1]-b[1]);
    const winner=candidates.length?candidates[0][0]:-1;
    st.results=picks;
    st.active.forEach(i=>{
      const [a,b]=st.pairs[i],used=st.mark[i]===0?a:b;
      st.hands[i]=st.hands[i].filter(x=>x!==used);
      st.cool[i]=[st.mark[i]===0?b:a];
    });
    if(winner>=0){st.score[winner]+=candidates[0][1];st.badge[winner]++;st.lastwin[winner]=st.round;logit(`${st.round}라운드 ${winner===0?'나':'AI '+winner} 승리, 카드 ${candidates[0][1]}`)}
    else logit(`${st.round}라운드 단독 최저 숫자 없음`);
    st.phase='result';render();
  }
  function roOrder(){return st.active.slice().sort((a,b)=>st.score[b]+st.badge[b]-st.score[a]-st.badge[a]||st.badge[b]-st.badge[a]||st.lastwin[b]-st.lastwin[a])}
  function roAdvance(){
    if(st.phase!=='result')return;
    if([3,6,9,12].includes(st.round)){
      const who=roOrder()[0];
      st.pass.push(who);st.active=st.active.filter(x=>x!==who);
      logit(`${st.round}라운드 정산: ${who===0?'나':'AI '+who} 생존 확정`);
      if(who===0){finish(true,`조기 생존 확정 (${st.round}라운드)`);render();return}
      st.active.forEach(i=>st.score[i]=0);
    }
    if(st.round>=18){roEnd();return}
    if(st.round===6||st.round===12) st.active.forEach(i=>{st.hands[i]=[1,2,3,4,5,6,7,8];st.cool[i]=[]});
    st.round++;roNew();
  }
  function roEnd(){
    const order=roOrder(),qualified=st.pass.includes(0)||order.indexOf(0)>=0&&order.indexOf(0)<2;
    finish(qualified,`18라운드 종료, 순위 ${order.map(i=>i===0?'나':'AI '+i).join(' / ')}`);
    st.phase='done';render();
  }
  function roDraw(){
    const phase=st.phase,eligible=st.hands[0].filter(x=>!st.cool[0].includes(x));
    const status=st.active.map(i=>`<div class="ro-person">${i===0?'나':'AI '+i} <b>${st.score[i]}</b>점 <small>징표 ${st.badge[i]}</small></div>`).join('');
    stage(`<div class="toolbar"><span class="counter">${st.round} / 18 라운드</span><span class="counter">잔여 참가자 ${st.active.length}</span><span class="counter">생존 확정 ${st.pass.length}</span></div><div class="ro-status">${status}</div>
      <div class="info">${phase==='pair'?'사용할 두 장을 선택하세요.':phase==='mark'?'모든 후보가 공개되었습니다. 사용할 카드 한 장을 비밀로 결정하세요.':'겹치지 않는 최저 숫자만 승리합니다.'}</div>
      ${phase==='pair'?`<div class="ro-hand">${eligible.map(n=>`<button class="${st.select.includes(n)?'sel':''}" onclick="roToggle(${n})">${n}</button>`).join('')}</div><div class="toolbar">${action('두 카드 공개','roReveal()',st.select.length!==2)}</div>`:''}
      ${phase!=='pair'?`<div class="ro-pairs">${st.active.map(i=>`<div class="ro-person"><b>${i===0?'나':'AI '+i}</b><span>${(st.pairs[i]||[]).join(' / ')}</span></div>`).join('')}</div>`:''}
      ${phase==='mark'?`<div class="toolbar">${(st.pairs[0]||[]).map((n,i)=>action(`${i===0?'왼쪽':'오른쪽'} ${n}`,`roConfirm(${i})`)).join('')}</div>`:''}
      ${phase==='result'?`<div class="info">${st.results.map(([i,n])=>`${i===0?'나':'AI '+i} ${n}`).join(' · ')}</div><div class="toolbar">${action('다음 라운드 / 정산','roAdvance()')}</div>`:''}`,
      '<p class="muted">패에서 2장을 공개한 뒤 비밀로 1장을 고릅니다. 동일 숫자는 무효, 가장 낮은 단독 숫자의 소유자가 승리합니다. 사용하지 않은 후보는 다음 라운드 임시 보관됩니다.</p><p class="small">7명 → 3명 생존 구조 및 18라운드를 구현한 AI 연습판입니다. 실제 참가자 협상은 제외했습니다.</p>');
  }
  // Clarify a recurring rules bug: elimination in time auction is based on lowest marks.
  taEnd=function(){
    const low=Math.min(...st.marks),tied=st.marks.filter(x=>x===low).length;
    const result=st.marks[0]>low?true:st.marks[0]===low&&tied>1?null:false;
    finish(result,`최소 표식 ${low}개 · 내 표식 ${st.marks[0]} / AI ${st.marks.slice(1).join('·')}`);
    st.phase='ended';clearInterval(taTimer);render();
  };
  const style=document.createElement('style');
  style.textContent=`
  .ss-symbols{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:18px 0}
  .ss-symbols button{background:linear-gradient(150deg,#3a2430,#171018);color:#f1d3a6;border:1px solid #946d5f;border-radius:12px;min-height:92px;font-size:21px;cursor:pointer}
  .ss-symbols button.active{outline:3px solid #ecc89a}
  .ro-status,.ro-pairs{display:grid;grid-template-columns:repeat(auto-fit,minmax(102px,1fr));gap:8px;margin:14px 0}
  .ro-person{border:1px solid #6b4a55;background:#1f151e;color:#e9d4bd;padding:10px;border-radius:9px;font-size:12px}
  .ro-person b{color:#f0cc94;font-size:17px}.ro-person small{display:block;color:#ae9799}
  .ro-person span{display:block;font-size:19px;font-weight:800;color:#f4dbaa;margin-top:8px}
  .ro-hand{display:flex;flex-wrap:wrap;gap:8px;margin:15px 0}
  .ro-hand button{border:2px solid #a68265;background:#ede0c8;color:#2e1d20;border-radius:8px;min-width:52px;min-height:75px;font:700 25px Georgia,serif;cursor:pointer}
  .ro-hand button.sel{outline:3px solid #e6b77a;transform:translateY(-6px)}
  @media(max-width:550px){.ss-symbols button{font-size:15px;min-height:76px}.ro-status,.ro-pairs{grid-template-columns:repeat(3,minmax(0,1fr))}}
  `;
  document.head.appendChild(style);
  home();