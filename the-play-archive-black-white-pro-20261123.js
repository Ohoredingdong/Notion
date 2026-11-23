/* THE PLAY ARCHIVE / BLACK & WHITE 2.0
   Broadcast-faithful parity information; explicit turn phases; probability-based AI.
   Noncommercial original UI. Other 25 games remain untouched. */
(function(){
'use strict';
if(typeof initBW!=='function'||typeof render!=='function'||typeof header!=='function')return;
const tiles=[0,1,2,3,4,5,6,7,8];
const color=n=>n%2?'흰색':'검정';
const digit=n=>String(n).padStart(2,'0');
let timers=[];
let aiDifficulty='normal';
let revealNumbers=false;
let reduced=false;
let mobileOptions=false;
const clear=()=>{timers.forEach(clearTimeout);timers=[];};
function delayed(fn,ms){const target=st;const timer=setTimeout(()=>{if(current==='흑과 백'&&st===target)fn();},reduced?30:ms);timers.push(timer);}

// Exact inference over all hidden-number assignments consistent with colours and win/loss.
// No access to the opponent's hidden numbers, unlike a cheating perfect-information AI.
function distribution(history,seenColor){
 let states=new Map([[0,1]]);
 for(const h of history){
  const next=new Map();
  for(const [mask,count] of states){
   for(const n of tiles){
    if(mask&(1<<n)||color(n)!==h.hiddenColor)continue;
    const result=h.known>n?'known':h.known<n?'hidden':'tie';
    if(result!==h.result)continue;
    const key=mask|(1<<n);
    next.set(key,(next.get(key)||0)+count);
   }
  }
  states=next;
  if(!states.size)break;
 }
 const probability=new Map();
 for(const [mask,count] of states){
  for(const n of tiles){
   if(mask&(1<<n)||(seenColor&&color(n)!==seenColor))continue;
   probability.set(n,(probability.get(n)||0)+count);
  }
 }
 if(!probability.size){for(const n of tiles)if(!seenColor||color(n)===seenColor)probability.set(n,1)}
 return probability;
}
function chooseFrom(pool,seenColor){
 const options=st.bw?.aiPublic||[];
 const dist=distribution(options,seenColor);
 const sum=[...dist.values()].reduce((a,b)=>a+b,0);
 const sorted=pool.map(n=>{
  let win=0,tie=0;
  for(const [v,c] of dist){if(n>v)win+=c;if(n===v)tie+=c}
  const chance=win/sum,draw=tie/sum;
  const reserve=pool.length>4?Math.pow(n/8,1.6)*.21:Math.pow(n/8,1.4)*.07;
  const bonus=(1-chance)*(n<=2?.05:0);
  return {n,metric:chance+draw*.10-reserve+bonus};
 }).sort((a,b)=>b.metric-a.metric);
 if(aiDifficulty==='easy')return pool[Math.floor(Math.random()*pool.length)];
 if(aiDifficulty==='normal'&&Math.random()<.35)return pool[Math.floor(Math.random()*pool.length)];
 const best=sorted.slice(0,aiDifficulty==='hard'?2:3);
 return best[Math.floor(Math.random()*best.length)].n;
}

const baseHome=home,baseStart=start;
home=function(){clear();return baseHome.apply(this,arguments)};
start=function(){clear();return baseStart.apply(this,arguments)};
initBW=function(){
 clear();bwPending=null;bwInfoTab='rules';bwHintText='';
 st={my:[...tiles],ai:[...tiles],round:1,set:1,score:[0,0],first:Math.random()<.5?0:1,
  aiPick:null,phase:'choose',duel:null,winning:null,bwHistory:[],bw:{aiPublic:[],playerPublic:[],lastResult:null}};
 if(st.first===1)st.aiPick=chooseFrom(st.ai,null);
};
bwChoose=function(seenColor){return chooseFrom(st.ai,seenColor)};
function winnerName(n){return n===0?'플레이어 승리':n===1?'AI 승리':'무승부'}
function settle(){
 if(finishText||st.phase!=='flip'||!st.duel)return;
 const d=st.duel;
 if(d.winner!==-1){st.score[d.winner]++;st.first=d.winner}
 st.winning=d.winner;
 st.phase='result';
 st.bwHistory.push({round:st.round,mine:d.mine,aiColor:color(d.ai),winner:d.winner,lead:d.lead,set:st.set||1,
                     ai:revealNumbers?d.ai:null});
 const knownResult=d.winner===0?'hidden':d.winner===1?'known':'tie';
 const playerResult=d.winner===1?'hidden':d.winner===0?'known':'tie';
 st.bw.aiPublic.push({known:d.ai,hiddenColor:color(d.mine),result:knownResult});
 st.bw.playerPublic.push({known:d.mine,hiddenColor:color(d.ai),result:playerResult});
 logit(`ROUND ${st.round} · 나 ${d.mine} / AI ${color(d.ai)} (비공개) · ${winnerName(d.winner)}`);
 if(st.round===9){
  if(st.score[0]===st.score[1]){
   st.phase='overtime';
   logit('9라운드 동점 ('+st.score[0]+':'+st.score[1]+') · 새 숫자타일 9장으로 연장전을 진행합니다.');
  }else{
   finish(st.score[0]>st.score[1],
    (st.set>1?'연장전 '+(st.set-1)+'회 · ':'')+'최종 점수 '+st.score[0]+' : '+st.score[1]);
  }
 }
 render();
}
bwMove=function(value){
 if(current!=='흑과 백'||finishText||st.phase!=='choose'||!st.my.includes(value))return;
 clear();
 const enemy=st.aiPick===null?chooseFrom(st.ai,color(value)):st.aiPick;
 if(!st.ai.includes(enemy))return;
 const lead=st.first;
 st.my.splice(st.my.indexOf(value),1);
 st.ai.splice(st.ai.indexOf(enemy),1);
 st.duel={mine:value,ai:enemy,lead,winner:value>enemy?0:value<enemy?1:-1};
 st.phase='sealed';st.winning=null;bwPending=null;
 render();
 delayed(()=>{if(st.phase==='sealed'){st.phase='flip';render()}},520);
 delayed(settle,1230);
};
bwPick=function(n){if(current!=='흑과 백'||finishText||st.phase!=='choose'||!st.my.includes(n))return;bwPending=n;render()};
bwConfirm=function(){if(bwPending===null||finishText||st.phase!=='choose')return;const value=bwPending;bwMove(value)};
bwNextRound=function(){
 if(current!=='흑과 백'||finishText||!['result','overtime'].includes(st.phase))return;
 clear();
 if(st.phase==='overtime'){
  st.set++;st.round=1;st.score=[0,0];st.my=[...tiles];st.ai=[...tiles];
  st.bw={aiPublic:[],playerPublic:[],lastResult:null};
  logit('연장전 '+(st.set-1)+'회 시작 · 0~8 타일 재지급');
 }else{
  if(st.round>=9)return;
  st.round++;
 }
 st.phase='choose';st.duel=null;st.winning=null;bwPending=null;bwHintText='';
 st.aiPick=st.first===1?chooseFrom(st.ai,null):null;
 render();
};
bwAction=function(){if(st.phase==='choose')return bwConfirm();if(st.phase==='result'||st.phase==='overtime')return bwNextRound()};
window.bwV2SetDifficulty=function(level){
 if(!['easy','normal','hard'].includes(level)||current!=='흑과 백'||(st.set||1)!==1||st.round!==1||st.phase!=='choose')return;
 aiDifficulty=level;
 if(st.first===1)st.aiPick=chooseFrom(st.ai,null);
 render();
};
window.bwV2SetMode=function(mode){
 if(!['broadcast','practice'].includes(mode)||current!=='흑과 백'||(st.set||1)!==1||st.round!==1||st.phase!=='choose')return;
 revealNumbers=mode==='practice';render();
};
window.bwV2ToggleMotion=function(){reduced=!reduced;render()};
window.bwV2MobileSettings=function(){mobileOptions=!mobileOptions;render()};
window.bwV2Hint=function(){
 if(current!=='흑과 백'||st.phase!=='choose')return;
 const dist=distribution(st.bw.playerPublic,st.aiPick===null?null:color(st.aiPick));
 const candidates=[...dist.keys()].sort((a,b)=>a-b);
 bwHintText=st.aiPick!==null?
  `상대가 지금 낸 ${color(st.aiPick)} 타일의 가능한 숫자: ${candidates.join(' · ')}. 색과 이전 승패만 반영한 추정입니다.`:
  '선공입니다. AI는 내 타일의 색을 본 뒤 응수합니다. 높은 카드를 아껴둘지도 고민해 보세요.';
 render();
};
window.bwV2Test={distribution,chooseFrom};

const face=(value,hidden,stage,owner)=>{
 const c=color(value);
 const shown=stage==='flip'||stage==='result'||stage==='overtime';
 const text=hidden?'?':value;
 const symbol=c==='검정'?'◆':'◇';
 const back=shown?'bw2-turned':'';
 return `<div class="bw2-tile bw2-${c==='검정'?'black':'white'} ${back}">
  <span class="bw2-tile-mark">${symbol}</span><strong>${shown?text:'—'}</strong><small>${shown?(hidden?c+' · 비공개':c):'SEALED'}</small></div>`;
};
function historyHtml(){
 const entries=[...st.bwHistory].reverse().slice(0,9);
 if(!entries.length)return '<p class="bw2-empty">첫 라운드 이후 기록이 남습니다.</p>';
 return entries.map(h=>`<div class="bw2-log"><span>${digit(h.round)}</span><strong>${h.winner===0?'WIN':h.winner===1?'LOSE':'DRAW'}</strong><small>내 카드 ${h.mine} · AI ${h.aiColor}${h.ai!==null?' '+h.ai:''}</small></div>`).join('');
}
bwDrawCinematic=function(){
 const active=st.phase==='choose',ended=!!finishText,d=st.duel;
 const lead=st.first===0?'내가 먼저 제출':'AI가 먼저 제출';
 const phaseText={choose:st.first===0?'내 타일을 선택하세요':`AI ${color(st.aiPick)} 타일 제출 · 숫자 비공개`,sealed:'두 타일 제출 완료 · 딜러 확인 중',flip:'타일 공개 · 승패 판정 중',result:st.winning===0?'플레이어 승리 · +1':st.winning===1?'AI 승리 · +1':'무승부 · 득점 없음',overtime:'9라운드 동점 · 새 타일로 연장전을 진행합니다'};
 const summary=ended?'9라운드 종료':phaseText[st.phase]||'게임 진행 중';
 const youTile=d?face(d.mine,false,st.phase,'me'):
  (bwPending!==null?face(bwPending,false,'result','me'):'<div class="bw2-tile bw2-unset"><span class="bw2-tile-mark">◇</span><strong>?</strong><small>SELECT</small></div>');
 const aiTile=d?face(d.ai,!revealNumbers,st.phase,'ai'):
  (st.aiPick!==null?`<div class="bw2-tile bw2-${st.aiPick%2?'white':'black'}"><span class="bw2-tile-mark">${st.aiPick%2?'◇':'◆'}</span><strong>?</strong><small>숫자 비공개</small></div>`:'<div class="bw2-tile bw2-unset"><span class="bw2-tile-mark">◇</span><strong>?</strong><small>WAITING</small></div>');
 const roundPips=Array.from({length:9},(_,i)=>`<i class="${i<st.round-1?'past':i===st.round-1?'now':''}"></i>`).join('');
 const selection=st.my.map(v=>`<button type="button" class="bw2-pick bw2-pick-${v%2?'white':'black'} ${bwPending===v?'selected':''}" onclick="bwPick(${v})" aria-pressed="${bwPending===v}" aria-label="${v}번 ${color(v)} 타일 선택" ${!active||ended?'disabled':''}><span>${v}</span></button>`).join('');
 const actionText=ended?'대결 완료':st.phase==='choose'?(bwPending===null?'타일을 선택하세요':`${bwPending}번 타일 제출`):st.phase==='overtime'?'연장전 시작 →':st.phase==='result'?'다음 라운드 →':'딜러가 확인 중…';
 const finished=ended?`<div class="bw2-finish" role="status"><div class="bw2-finish-kicker">MATCH COMPLETE</div><strong>${st.score[0]>st.score[1]?'승리':st.score[0]<st.score[1]?'패배':'무승부'}</strong><p>9라운드 최종 결과 · ${st.score[0]} : ${st.score[1]}</p><div><button onclick="start('흑과 백')">다시 대결</button><button onclick="home()">게임 목록</button></div></div>`:'';
 const settingsDisabled=(st.set||1)!==1||st.round!==1||!active;
 $('#app').innerHTML=header()+`<section class="bw2-shell" aria-label="흑과 백 게임">
 <div class="bw2-menu"><button onclick="home()" class="bw2-back">← 게임 목록</button><span>THE PLAY ARCHIVE <b>/</b> DEATH MATCH</span><button onclick="start('흑과 백')">↻ 새 대결</button></div>
 <div class="bw2-layout"><aside class="bw2-panel ${mobileOptions?'bw2-settings-open':''}">
   <p class="bw2-eyebrow">THE GENIUS · BLACK & WHITE</p><h1>흑과 백</h1><p class="bw2-desc">숫자를 숨기고, 색으로 읽는 심리전.</p>
   <div class="bw2-score"><div><span>PLAYER</span><strong>${st.score[0]}</strong></div><i>:</i><div><span>DEALER AI</span><strong>${st.score[1]}</strong></div></div>
   <div class="bw2-minor">${st.set>1?'연장전 '+(st.set-1)+' · ':''}ROUND <b>${digit(st.round)}</b> / 09 <span>·</span> ${lead}</div>
   <div class="bw2-pips">${roundPips}</div><button class="bw2-mobile-open" onclick="bwV2MobileSettings()" aria-expanded="${mobileOptions}">${mobileOptions?'설정 닫기':'규칙 · 난이도 설정'} ↗</button>
   <div class="bw2-rule"><strong>게임 규칙</strong><p>0~8 타일을 한 번씩 사용합니다. 짝수는 검정, 홀수는 흰색. 높은 숫자가 1점을 얻습니다. 9라운드 승점이 같으면 새 타일로 연장전을 진행합니다.</p><p>선공의 <b>색만</b> 보고 후공이 응수합니다. 원작 모드에서 상대 숫자는 끝까지 공개하지 않습니다.</p></div>
   <div class="bw2-choices"><div class="bw2-section-head"><strong>게임 설정</strong><small>첫 턴에만 변경</small></div>
     <div class="bw2-choice-label">모드</div><div class="bw2-switches"><button class="${!revealNumbers?'on':''}" onclick="bwV2SetMode('broadcast')" ${!settingsDisabled?'disabled':''}>방송 규칙</button><button class="${revealNumbers?'on':''}" onclick="bwV2SetMode('practice')" ${!settingsDisabled?'disabled':''}>숫자 공개 연습</button></div>
     <div class="bw2-choice-label">AI 난이도</div><div class="bw2-switches"><button class="${aiDifficulty==='easy'?'on':''}" onclick="bwV2SetDifficulty('easy')" ${!settingsDisabled?'disabled':''}>초급</button><button class="${aiDifficulty==='normal'?'on':''}" onclick="bwV2SetDifficulty('normal')" ${!settingsDisabled?'disabled':''}>보통</button><button class="${aiDifficulty==='hard'?'on':''}" onclick="bwV2SetDifficulty('hard')" ${!settingsDisabled?'disabled':''}>상급</button></div>
   </div>
 </aside>
 <main class="bw2-stage"><div class="bw2-table">
   <div class="bw2-tablebar"><span>TABLE 01 <i></i> PLAYER vs AI</span><span>${st.set>1?'연장전 '+(st.set-1)+' · ':''}ROUND ${digit(st.round)} / 09</span></div>
   <div class="bw2-dealer"><span class="bw2-seal">✦</span><span>THE DEALER</span></div>
   <div class="bw2-duel"><div class="bw2-contender"><span>01 &nbsp; PLAYER</span>${youTile}</div><div class="bw2-versus"><span>VS</span><em>${st.phase==='choose'?'CHOOSE':st.phase==='sealed'?'SEALED':st.phase==='flip'?'REVEAL':st.phase==='overtime'?'OVERTIME':'RESULT'}</em></div><div class="bw2-contender"><span>02 &nbsp; ARTIFICIAL INTELLIGENCE</span>${aiTile}</div></div>
   <div class="bw2-status" aria-live="polite"><strong>${summary}</strong>${st.phase==='choose'?`<small>${st.first===1?'AI 타일의 색만 보고 판단하세요.':'AI는 내 타일의 색을 보고 고릅니다.'}</small>`:''}</div>
   <div class="bw2-deck"><div class="bw2-deck-title"><strong>MY TILES</strong><span>${st.my.length} / 9 REMAINING</span></div><div class="bw2-hand">${selection||'<span class="bw2-deck-empty">모든 타일을 사용했습니다.</span>'}</div></div>
   <div class="bw2-controls"><button type="button" class="bw2-hint" onclick="bwV2Hint()" ${!active?'disabled':''}>전략 힌트</button><button type="button" class="bw2-submit" onclick="bwAction()" ${ended||st.phase==='sealed'||st.phase==='flip'||active&&bwPending===null?'disabled':''}>${actionText}</button></div>
   ${bwHintText?`<div class="bw2-hint-text" role="status">${txt(bwHintText)}</div>`:''}
   ${finished}
 </div></main>
 <aside class="bw2-right"><div class="bw2-section-head"><strong>ROUND HISTORY</strong><small>최근 9판</small></div><div class="bw2-log-list">${historyHtml()}</div><div class="bw2-key"><i class="bw2-legend-black"></i> 짝수 · 검정 <i class="bw2-legend-white"></i> 홀수 · 흰색</div><button class="bw2-motion" onclick="bwV2ToggleMotion()">${reduced?'모션 켜기':'모션 줄이기'}</button></aside>
 </div></section>`;
};
})();
