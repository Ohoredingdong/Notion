
// THE PLAY ARCHIVE v6: stable visual hierarchy and user-reachable controls for all 26 existing modes.
const v6Family={
 '결! 합!':'puzzle','연승게임':'card','1·2·3 게임':'card','인디언 포커':'card','마이너스 경매':'auction',
 '나인 멘스 모리스':'board','콰트로':'card','십이장기':'board','헥사곤':'puzzle','같은 숫자 찾기':'memory',
 '같은 그림 찾기':'memory','블라인드 오목':'board','기사의 여행':'board','시간 경매':'auction',
 '큐브 세기':'puzzle','네모 세기':'puzzle','4인 3목':'board','바그찰':'board','몽타주':'memory',
 '신의 판결':'card','미스터리 사인':'puzzle','벽바둑':'board','벽바둑 2':'board','해 달 별':'card','하나 빼기':'card'
};
const v6Stages={choose:'선택 단계',sealed:'제출 완료',flip:'동시 공개',reveal:'카드 공개',result:'결과 확인',review:'정답 확인',ai:'AI 차례',thinking:'AI 생각 중',place:'말 배치',select:'말 선택',move:'이동 선택',wall:'벽 설치',pair:'카드 공개 준비',pick:'카드 결정',bet:'베팅',ready:'준비',bidding:'입찰 중',countdown:'카운트다운',answer:'정답 제출',ended:'최종 결과'};
const _stageBeforeV6=stage;
stage=function(inner,aside){
 _stageBeforeV6(inner,aside);
 try{
  const root=document.querySelector('.arena-stage.game-skin');
  const play=root?.querySelector('.match-actualplay');
  const board=root?.querySelector('.match-board');
  const footer=root?.querySelector('.match-footer');
  if(!root||!play||!board||!footer)return;
  root.setAttribute('data-family',v6Family[current]||'puzzle');
  root.setAttribute('data-phase',String(st?.phase||'play'));
  const p=st?.phase;
  const thinking=!!st?.aiThinking||(current==='4인 3목'&&st?.turn>0)||(current==='블라인드 오목'&&st?.turn===1)||(current==='십이장기'&&st?.turn===2)||(current==='나인 멘스 모리스'&&st?.turn===2);
  const label=thinking?'AI 생각 중':(v6Stages[p]||'내 차례');
  const meta=root.querySelector('.match-meta-strip');
  if(meta){const tag=document.createElement('span');tag.className='match-step-indicator';tag.dataset.stage=String(thinking?'thinking':p||'play');tag.innerHTML='<i></i>'+label;meta.appendChild(tag)}
  const dock=document.createElement('div');dock.className='match-actiondock';dock.setAttribute('aria-label','현재 게임 조작');
  const all=[...play.querySelectorAll('.toolbar,.round-controls')].filter(el=>el.querySelector('button:not([disabled]),button[disabled]'));
  let selected=[];
  if(all.length){
    const withActions=all.filter(el=>![...el.querySelectorAll('button')].every(b=>!b.hasAttribute('onclick')));
    const last=withActions.at(-1);
    if(last)selected=[last];
    if((current==='벽바둑'||current==='벽바둑 2')&&st.phase==='wall'&&withActions.length>=2)selected=withActions.slice(-2);
  }
  for(const el of selected){dock.appendChild(el)}
  if(dock.children.length)footer.before(dock);
  if(st?.turn===1){for(const b of play.querySelectorAll('.tt-cell,.gm-cell'))b.disabled=true}
  if(current==='하나 빼기')root.classList.add('skin-ro');
  // User's focused input is never replaced by a background-only render in a separate frame.
 }catch(e){console.warn('Optional game chrome could not be applied',e)}
};

// Isometric cube scene built from the game's ACTUAL column heights, not a misleading flat 2-D strip.
function isoCubeScene(heights,n){
 const W=n<=4?30:n===5?25:21,D=W*.5,H=W*.72;
 const max=Math.max(...heights),cx=n*W+22,topY=max*H+18;
 let parts=[];
 const order=[];for(let r=0;r<n;r++)for(let c=0;c<n;c++)order.push({r,c,h:heights[r*n+c]});
 order.sort((a,b)=>(a.r+a.c)-(b.r+b.c));
 for(const {r,c,h} of order){
   for(let z=0;z<h;z++){
    const x=cx+(c-r)*W,y=topY+(c+r)*D-z*H;
    const p=(dx,dy)=>`${(x+dx).toFixed(2)},${(y+dy).toFixed(2)}`;
    parts.push(`<g aria-hidden="true"><polygon class="iso-left" points="${p(-W,0)} ${p(0,D)} ${p(0,D+H)} ${p(-W,H)}"/><polygon class="iso-right" points="${p(W,0)} ${p(0,D)} ${p(0,D+H)} ${p(W,H)}"/><polygon class="iso-top" points="${p(0,-D)} ${p(W,0)} ${p(0,D)} ${p(-W,0)}"/></g>`)
   }
 }
 const w=2*n*W+44,h=topY+2*(n-1)*D+H+24;
 return `<div class="iso-cube-stage" aria-label="입체적으로 쌓인 큐브 세기 퍼즐"><svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${n}행 ${n}열에 층층이 쌓인 정육면체 구조">${parts.join('')}</svg></div>`;
}
ccDraw=function(){
 const scene=isoCubeScene(st.heights,st.size);
 stage(`${exBar([`문제 ${st.round}/5`,`맞힌 문제 ${st.score}`])}<div class="info">앞쪽 큐브뿐 아니라 뒤에 가려진 층까지 합쳐 세어 보세요.</div>${scene}${st.feedback?`<div class="${st.phase==='review'?'result':'info'}">${txt(st.feedback)}</div>`:''}${st.phase==='review'?`<div class="round-controls">${action(st.round===5?'최종 결과':'다음 문제','ccNext()')}</div>`:`<div class="toolbar"><input id="ex-answer" class="inp" type="number" min="1" inputmode="numeric" aria-label="큐브 개수" placeholder="총 몇 개?">${action('정답 제출','ccSubmit()',Date.now()<st.blocked)}</div>`}`,`<p class="muted">방송에 나온 물체의 정확한 모형이 아니라 규칙을 참고해 자동 생성한 연습용 입체 퍼즐입니다.</p>`);
};

// Staged deduction, revealing the decision before updating points.
let v6GHReview=null;
const _v6GHInit=initGH;
initGH=function(){v6GHReview=null;_v6GHInit();st.phase='choose'};
const _v6GhSelect=ghSelect;
ghSelect=function(i){if(v6GHReview)return;_v6GhSelect(i)};
ghSubmit=function(){
 if(finishText||v6GHReview||st.selected.length!==3)return;
 const ids=[...st.selected].sort((a,b)=>a-b),k=ids.map(i=>i+1).join('-');
 const good=ghValid(...ids.map(i=>st.cards[i]))&&!st.found.includes(k);
 v6GHReview={kind:'합',ids,k,good,phase:'sealed',delta:good?1:-1};st.phase='sealed';render();
};
ghEnd=function(){
 if(finishText||v6GHReview)return;
 const remain=ghTriples().length;
 v6GHReview={kind:'결',ids:[],good:remain===0,remain,delta:remain===0?3:-1,phase:'sealed'};
 st.phase='sealed';render();
};
const _v6GhPass=ghPass;
ghPass=function(){if(v6GHReview)return;_v6GhPass()};
function v6GHReveal(){if(!v6GHReview||v6GHReview.phase!=='sealed')return;v6GHReview.phase='reveal';st.phase='reveal';render()}
function v6GHSettle(){
 const d=v6GHReview;if(!d||d.phase!=='reveal')return;
 st.score[0]+=d.delta;
 if(d.kind==='합'){if(d.good){st.found.push(d.k);st.pass=0}else st.pass++;logit(`${d.ids.map(i=>i+1).join('·')} 합 ${d.good?'성공 +1':'오답 -1'}`);st.selected=[];ghAi()}
 else if(d.good){logit('결 정답 +3');ghNext()}
 else{logit(`결 오답 -1 (아직 ${d.remain}개 조합)`);ghAi()}
 d.phase='result';d.message=`${d.kind} ${d.good?'성공':'실패'} · 내 점수 ${d.delta>0?'+':''}${d.delta}점`;
 st.phase='result';render();
}
function v6GHContinue(){if(!v6GHReview||v6GHReview.phase!=='result')return;v6GHReview=null;st.phase='choose';render()}
const _v6DrawGH=drawGH;
drawGH=function(){
 if(!v6GHReview){_v6DrawGH();return}
 const d=v6GHReview;
 const sample=d.ids.length?d.ids.map(i=>`<span class="tile ${d.phase==='sealed'?'black':'white'}" style="display:grid;place-items:center">${d.phase==='sealed'?'?':i+1}</span>`).join(''):`<span class="tile ${d.phase==='sealed'?'black':'white'}" style="display:grid;place-items:center">${d.phase==='sealed'?'?':'결'}</span>`;
 const details=d.phase==='sealed'?'선택한 카드를 봉인했습니다. 판정 전에 공개할까요?':d.phase==='reveal'?d.kind==='합'?`세 가지 속성이 각각 모두 같거나 모두 달라야 합니다. ${d.good?'유효한 합입니다.':'조건을 만족하지 않습니다.'}`:d.good?'남은 합이 없으므로 결이 성공합니다.':`아직 찾지 않은 합이 ${d.remain}개 남았습니다.`:d.message;
 stage(`${exBar([`라운드 ${st.round} / 10`])}${scores(['나','AI'],st.score)}<div class="round-frame"><h2>${d.phase==='sealed'?'선택 제출':d.phase==='reveal'?'딜러 판정':'라운드 결과'}</h2><div class="round-flip-row">${sample}</div><div class="info">${details}</div><div class="round-controls">${d.phase==='sealed'?action('카드 공개','v6GHReveal()'):d.phase==='reveal'?action('판정 후 점수 반영','v6GHSettle()'):action(finishText?'결과 확인':'다음 선택','v6GHContinue()')}</div></div>`,`<p class="muted">〈결! 합!〉은 제출·공개·판정·점수 반영을 분리했습니다. 점수는 판정 버튼을 누른 뒤에만 반영됩니다.</p>`)
};

// God's Verdict: dice are cast face-down, revealed, and only then scored.
const _v6VDInit=vdInit;
vdInit=function(){_v6VDInit();st.phase='choose';st.roll=null};
vdRoll=function(){if(finishText||st.phase!=='choose')return;
 const a=pick(st.faces[0]),b=pick(st.faces[1]),ai=rand(2,12),sum=a+b;
 st.roll={a,b,ai,sum,hit:st.targets.includes(sum),phase:'sealed'};st.phase='sealed';render();
};
function v6VDReveal(){if(st.phase!=='sealed')return;st.phase='reveal';render()}
function v6VDSettle(){if(st.phase!=='reveal')return;
 const d=st.roll;st.score[0]+=d.hit?1:0;st.score[1]+=d.sum===d.ai?1:0;
 logit(`${st.round}회: ${d.a}+${d.b}=${d.sum} · ${d.hit?'적중 +1':'미적중'} · AI 예상 ${d.ai}`);
 if(st.round>=10)finish(st.score[0]===st.score[1]?null:st.score[0]>st.score[1],`최종 나 ${st.score[0]}, AI ${st.score[1]}`);
 st.phase='result';render();
}
function v6VDNext(){if(st.phase!=='result'||finishText)return;st.phase='choose';st.roll=null;st.round++;render()}
vdDraw=function(){
 const d=st.roll,choose=st.phase==='choose';
 const dice=st.faces.map((die,i)=>`<div><b>주사위 ${i+1}</b><div class="vd-face-grid">${die.map((n,j)=>`<button class="vd-face" onclick="vdSet(${i},${j},${n>=6?1:n+1})" ${choose?'':'disabled'}>${n}</button>`).join('')}</div></div>`).join('');
 const duel=d?`<div class="round-frame"><h2>${st.phase==='sealed'?'주사위 굴림 완료':st.phase==='reveal'?'주사위 동시 공개':'판정 결과'}</h2><div class="round-flip-row">${[d.a,d.b].map(x=>`<div class="round-flip ${st.phase==='sealed'?'is-back':''}"><small>주사위</small><strong>${st.phase==='sealed'?'?':x}</strong></div>`).join('')}</div><div class="info">${st.phase==='sealed'?'두 주사위가 봉인됐습니다. 공개 후 합계와 목표를 비교합니다.':`합계 ${d.sum} · 내 목표 ${st.targets.join(' / ')} · ${d.hit?'적중':'미적중'} · AI 목표 ${d.ai}`}</div><div class="round-controls">${st.phase==='sealed'?action('주사위 공개','v6VDReveal()'):st.phase==='reveal'?action('점수 반영','v6VDSettle()'):finishText?'':action('다음 판','v6VDNext()')}</div></div>`:'';
 stage(`${exBar([`라운드 ${st.round} / 10`])}${scores(['나','AI'],st.score)}${choose?`<div class="info">주사위 면을 클릭해 조정한 후 목표 합을 설정하세요.</div><div class="vd-dice">${dice}</div><div class="toolbar"><label class="label">목표 A <select class="inp" onchange="vdTarget(this.value,0)">${Array.from({length:24},(_,i)=>i+1).map(n=>`<option ${n===st.targets[0]?'selected':''}>${n}</option>`).join('')}</select></label><label class="label">목표 B <select class="inp" onchange="vdTarget(this.value,1)">${Array.from({length:24},(_,i)=>i+1).map(n=>`<option ${n===st.targets[1]?'selected':''}>${n}</option>`).join('')}</select></label>${action('주사위 굴리기','vdRoll()')}</div>`:duel}`,`<p class="muted">주사위가 실제로 나온 값을 먼저 공개하고, 이후 적중 여부에 따라 점수를 반영합니다.</p>`);
};

// Strategic board games: show AI's turn rather than silently applying its move in the same frame.
const _v6MorrisAI=mmAIMove;
mmAIMove=function(){
 const match=st;if(match.aiThinking)return;match.aiThinking=true;render();
 setTimeout(()=>{if(current!=='나인 멘스 모리스'||st!==match||finishText)return;match.aiThinking=false;_v6MorrisAI();render()},530);
};
const _v6JangAI=jangAI;
jangAI=function(){
 const match=st;if(match.aiThinking)return;match.aiThinking=true;render();
 setTimeout(()=>{if(current!=='십이장기'||st!==match||finishText)return;match.aiThinking=false;_v6JangAI();render()},560);
};
const _v6BaghAI=bgAi;
bgAi=function(){
 const match=st;if(match.aiThinking)return;match.aiThinking=true;render();
 setTimeout(()=>{if(current!=='바그찰'||st!==match||finishText)return;match.aiThinking=false;_v6BaghAI();render()},510);
};
const _v6BaghMove=bgMove;
bgMove=function(i){if(st.aiThinking)return;_v6BaghMove(i)};
const _v6WallAI=wgAI;
wgAI=function(){
 const match=st;if(match.aiThinking)return;match.aiThinking=true;render();
 setTimeout(()=>{if(!['벽바둑','벽바둑 2'].includes(current)||st!==match||finishText)return;match.aiThinking=false;_v6WallAI();match.turn=0;render()},520);
};
const _v6WallSelect=wgSelect;
wgSelect=function(i){if(st.aiThinking)return;_v6WallSelect(i)};
const _v6WallMove=wgPlace;
wgPlace=function(i){if(st.aiThinking)return;_v6WallMove(i)};