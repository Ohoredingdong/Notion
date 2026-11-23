/* THE PLAY ARCHIVE | 흑과 백: 카드 제출 -> 동시 뒤집기 -> 판정 -> 점수 -> 다음 라운드 */
(function(){
"use strict";
var pendingTimers=[], revealAI=true;
function clearBW(){pendingTimers.forEach(clearTimeout);pendingTimers=[];}
function delayed(fn,ms){var roundState=st;pendingTimers.push(setTimeout(function(){if(current==='흑과 백'&&st===roundState)fn();},ms));}
var baseInit=initBW,baseDraw=bwDrawCinematic,baseHome=home,baseStart=start;
initBW=function(){clearBW();baseInit();st.phase='choose';st.duel=null;st.winning=null;};
home=function(){clearBW();baseHome();};
start=function(name){clearBW();baseStart(name);};
bwMove=function(v){
 if(finishText||st.phase!=='choose'||!st.my.includes(v))return;
 clearBW();
 var a=st.aiPick===null?bwChoose(v%2?'흰':'검'):st.aiPick;
 st.my.splice(st.my.indexOf(v),1);st.ai.splice(st.ai.indexOf(a),1);
 st.duel={mine:v,ai:a,winner:v>a?0:v<a?1:-1};
 st.phase='sealed';bwPending=null;render();
 delayed(function(){st.phase='flip';render();},850);
 delayed(function(){if(st.phase!=='flip')return;
  var d=st.duel;
  if(d.winner!==-1){st.score[d.winner]++;st.first=d.winner;}
  st.winning=d.winner;st.phase='result';
  logit('라운드 '+st.round+': 나 '+d.mine+' / AI '+(revealAI?d.ai:(d.ai%2?'흰색':'검은색')+' 타일(숫자 비공개)')+' — '+(d.winner===0?'내 승리':d.winner===1?'AI 승리':'무승부'));
  if(st.round>=9)finish(st.score[0]===st.score[1]?null:st.score[0]>st.score[1],'9라운드 종료 · 나 '+st.score[0]+' : AI '+st.score[1]);
  render();
 },2050);
};
var baseAction=bwAction;
bwAction=function(){
 if(st.phase==='result'&&!finishText){
  if(st.round>=9)return;
  st.round++;st.phase='choose';st.duel=null;st.winning=null;bwPending=null;
  st.aiPick=st.first===1?bwChoose(null):null;render();return;
 }
 if(st.phase==='sealed'||st.phase==='flip')return;
 baseAction();
};
window.bwRevealToggle=function(){
 if(st.phase==='sealed'||st.phase==='flip')return;
 revealAI=!revealAI;render();
};
function makeCard(value,who){
 var card=document.createElement('div');card.className='bwv-unit';
 var label=document.createElement('span');label.className='bwv-label';label.textContent=who==='me'?'내 타일':'AI 타일';
 var body=document.createElement('div');body.className='bwv-card';
 var shown=(st.phase==='flip'||st.phase==='result')&&(who==='me'||revealAI);
 if(shown)body.classList.add('turned');
 var inner=document.createElement('div');inner.className='bwv-inner';
 var back=document.createElement('div');back.className='bwv-face bwv-back '+(value%2?'white':'black');back.textContent='✦';
 var front=document.createElement('div');front.className='bwv-face bwv-front '+(value%2?'white':'black');front.textContent=String(value);
 inner.append(back,front);body.append(inner);card.append(label,body);
 return card;
}
bwDrawCinematic=function(){
 baseDraw();
 if(!st.phase)st.phase='choose';
 var main=document.querySelector('.bw-theater');
 if(!main)return;
 var mainButton=main.querySelector('.bw-primary');
 var help=main.querySelector('.bw-table-help');
 var prompt=main.querySelector('.bw-prompt');
 var roundBar=main.querySelector('.bw-roundbar');
 var wrapper=main.querySelector('.bw-table-controls');
 if(st.phase==='choose'){
  if(mainButton)mainButton.innerHTML=bwPending!==null?bwPending+'번 타일 제출 &nbsp; ❯':'타일을 선택하세요';
 }else if(st.duel){
  wrapper.classList.add('bwv-stage');
  var oldTiles=main.querySelector('.bw-tiles');
  var duel=document.createElement('div');duel.className='bwv-scene';duel.setAttribute('aria-live','polite');
  duel.append(makeCard(st.duel.mine,'me'));
  var vs=document.createElement('span');vs.className='bwv-versus';vs.textContent='VS';duel.append(vs);
  duel.append(makeCard(st.duel.ai,'ai'));
  if(oldTiles)oldTiles.replaceWith(duel);
  else wrapper.append(duel);
  var status=st.phase==='sealed'?'두 타일을 제출했습니다':st.phase==='flip'?'두 타일 동시 공개':st.winning===0?'내 승리 · 1점 획득':st.winning===1?'AI 승리 · AI 1점 획득':'무승부 · 득점 없음';
  if(prompt)prompt.textContent='✦  '+status+'  ✦';
  if(help)help.textContent=st.phase==='sealed'?'딜러가 패를 확인하고 있습니다.':st.phase==='flip'?'공개 후 승패와 점수를 반영합니다.':st.winning===0?'내 타일 승리':st.winning===1?'AI 타일 승리':'같은 숫자를 냈습니다.';
  if(mainButton){
   mainButton.textContent=st.phase==='result'?'다음 라운드 →':'패 공개 및 판정 중…';
   mainButton.disabled=st.phase!=='result'||!!finishText;
  }
  if(roundBar&&roundBar.children[1])roundBar.children[1].textContent=st.phase==='sealed'?'제출 완료':st.phase==='flip'?'동시 공개':'승패 판정 완료';
  var hint=main.querySelector('.bw-bottom button:last-child');if(hint)hint.disabled=true;
  if(st.phase==='result'){
   var target=main.querySelector(st.winning===0?'.bw-scoreplate.you':'.bw-scoreplate.ai');
   if(st.winning!==-1&&target)target.classList.add('bwv-winner');
  }
 }
 var rules=document.querySelector('.bw-tabpanel');
 if(rules&&bwInfoTab==='rules'){
  var p=document.createElement('p');p.className='bwv-rule-note';p.textContent='방송 원작에서는 상대 숫자를 끝까지 공개하지 않습니다. 아래에서 공개 연습 모드와 방송 방식을 바꿀 수 있습니다.';
  var mode=document.createElement('button');mode.className='bwv-mode';mode.textContent=revealAI?'숫자 공개 연습 모드 · 방송 규칙으로 전환':'방송 규칙 모드 · 숫자 공개로 전환';
  mode.disabled=st.phase==='sealed'||st.phase==='flip';mode.onclick=window.bwRevealToggle;
  rules.append(p,mode);
 }
};
var style=document.createElement('style');style.textContent=
'.bwv-stage{top:52%!important;gap:8px!important}.bwv-stage .bw-prompt{font-size:clamp(13px,1.4vw,20px)!important}'+
'.bwv-scene{display:flex;align-items:center;justify-content:center;gap:clamp(15px,3vw,42px);width:100%;perspective:1100px}'+
'.bwv-unit{display:flex;align-items:center;flex-direction:column;gap:7px}.bwv-label{font-weight:700;font-size:11px;color:#efcf9c;text-shadow:0 2px 5px #000}'+
'.bwv-card{width:clamp(63px,7.3vw,105px);height:clamp(88px,13vh,134px);perspective:1100px;filter:drop-shadow(0 7px 12px #000)}'+
'.bwv-inner{height:100%;width:100%;position:relative;transform-style:preserve-3d;transform:rotateY(0deg)}'+
'.bwv-card.turned .bwv-inner{animation:bwvFlip .9s cubic-bezier(.17,.7,.25,1) both}'+
'.bwv-face{position:absolute;inset:0;border:2px solid #b98c58;border-radius:8px;display:grid;place-items:center;backface-visibility:hidden;box-shadow:inset 0 0 0 3px #dcb57825}'+
'.bwv-back{font:40px Georgia,serif}.bwv-back.black,.bwv-front.black{background:linear-gradient(145deg,#26222b,#0a080b);color:#f3d39c}'+
'.bwv-back.white,.bwv-front.white{background:linear-gradient(145deg,#fff0d9,#cfb696);color:#211920}'+
'.bwv-front{transform:rotateY(180deg);font:700 clamp(36px,4vw,60px) Georgia,serif}.bwv-versus{font:700 21px Georgia,serif;color:#ebc596}'+
'.bwv-winner{box-shadow:0 0 26px #e2ba7190!important}.bwv-rule-note{font-size:11px;color:#e2c7a5}.bwv-mode{background:#3b222d;color:#ffe4bd;border:1px solid #bd926b;border-radius:7px;padding:9px;font-size:11px;width:100%;cursor:pointer}'+
'@keyframes bwvFlip{from{transform:rotateY(0deg)}to{transform:rotateY(180deg)}}'+
'@media(max-width:750px){.bwv-stage{top:51%!important}.bwv-card{width:64px;height:88px}.bwv-label{font-size:10px}.bwv-scene{gap:15px}}'+
'@media(max-height:650px){.bwv-stage{top:49%!important}.bwv-card{height:82px;width:61px}}'+
'@media(prefers-reduced-motion:reduce){.bwv-card.turned .bwv-inner{animation-duration:.01ms}}';
document.head.append(style);
})();
