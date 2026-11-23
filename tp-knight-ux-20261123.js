/* THE PLAY ARCHIVE · game-specific reaction and progress for Knight's Tour.
   Independent original implementation; no third-party code, artwork, or assets. */
(function(){
'use strict';
if(typeof ktInit!=='function'||typeof stage!=='function')return;
var cfg={mode:'practice',size:6},clock=0,tick=null;
var jumps=[[1,2],[2,1],[2,-1],[1,-2],[-1,-2],[-2,-1],[-2,1],[-1,2]];
function stop(){if(tick!==null)clearInterval(tick);tick=null;}
function seconds(){return clock?Math.floor((Date.now()-clock)/1000):0;}
function fmt(v){return String(Math.floor(v/60)).padStart(2,'0')+':'+String(v%60).padStart(2,'0');}
function initBoard(n,step,carry){st={ext:'kt',path:[],hint:null,kt:{mode:cfg.mode,size:n,step:step||0,carry:carry||0,phase:'setup',assists:0,undid:false,note:'시작 칸을 골라 첫 수를 놓으세요.'}};}
var oldStart=start,oldHome=home;
start=function(){stop();clock=0;return oldStart.apply(this,arguments);};
home=function(){stop();clock=0;return oldHome.apply(this,arguments);};
ktInit=function(){stop();clock=0;cfg={mode:'practice',size:6};initBoard(6);};
ktNeighbors=function(i,visited){var n=st.kt?st.kt.size:8,r=Math.floor(i/n),c=i%n;
return jumps.map(function(d){return [r+d[0],c+d[1]];}).filter(function(d){return d[0]>=0&&d[0]<n&&d[1]>=0&&d[1]<n;}).map(function(d){return d[0]*n+d[1];}).filter(function(v){return !visited.has(v);});};
window.tpKMode=function(mode){if(!st.kt||st.kt.phase!=='setup'||!['practice','challenge'].includes(mode))return;
cfg.mode=mode;cfg.size=6;initBoard(6);render();};
window.tpKSize=function(n){if(!st.kt||st.kt.phase!=='setup'||cfg.mode!=='practice'||![5,6,7,8,9,10].includes(n))return;
cfg.size=n;initBoard(n);render();};
window.tpKReset=function(){var k=st.kt;if(k&&k.mode==='challenge'&&k.phase!=='ended'){var step=k.step,carry=k.carry+(k.frozen===undefined?seconds():k.frozen),assists=k.assists;stop();clock=0;initBoard(cfg.size,step,carry);st.kt.assists=assists;st.kt.note='같은 보드를 처음부터 다시 시작합니다. 이전 판의 기록 시간은 유지됩니다.';render();return;}stop();clock=0;initBoard(cfg.size);render();};
window.tpKNext=function(){var k=st.kt;if(!k||k.phase!=='board-win'||k.mode!=='challenge'||k.step>=2)return;
var next=[6,7,8][k.step+1],carry=k.carry+(k.frozen||0),assists=k.assists,undid=k.undid;
stop();clock=0;cfg.size=next;initBoard(next,k.step+1,carry);st.kt.assists=assists;st.kt.undid=undid;render();};
ktMove=function(i){var k=st.kt;if(!k||finishText||k.phase==='board-win'||!Number.isInteger(i)||i<0||i>=k.size*k.size)return;
if(k.mode==='challenge'&&k.carry+seconds()>=3600){finish(false,'60분 제한 시간을 초과했습니다.');k.phase='ended';stop();render();return;}
if(k.phase==='setup'&&k.size%2===1&&(Math.floor(i/k.size)+i%k.size)%2!==0){k.note='홀수 크기의 판에서는 모서리와 같은 색의 칸에서 출발해야 완주할 수 있습니다.';render();return;}
if(k.phase==='setup'){st.path=[i];k.phase='playing';clock=Date.now();stop();tick=setInterval(function(){if(current!=='기사의 여행'){stop();return;}var el=document.querySelector('.ktx-clock');if(el)el.textContent=fmt(st.kt&&st.kt.mode==='challenge'?st.kt.carry+seconds():seconds());if(st.kt&&st.kt.mode==='challenge'&&st.kt.carry+seconds()>=3600){finish(false,'60분 제한 시간을 초과했습니다.');st.kt.phase='ended';stop();render();}},500);k.note='시작 칸을 선택했습니다. 밝게 표시된 칸으로 이동하세요.';render();return;}
if(!ktNeighbors(st.path[st.path.length-1],new Set(st.path)).includes(i))return;
st.path.push(i);st.hint=null;k.note=st.path.length+'번째 칸으로 이동했습니다.';
if(st.path.length===k.size*k.size){k.phase='board-win';k.frozen=seconds();stop();
k.note=k.size+'×'+k.size+' 보드를 완주했습니다.';
if(k.mode==='practice'||k.step===2){var total=k.carry+k.frozen;var key='tp_knight_best_'+k.mode+'_'+k.size;try{var saved=Number(localStorage.getItem(key));if(!k.assists&&!k.undid&&(!saved||total<saved))localStorage.setItem(key,String(total));}catch(err){}
finish(true,(k.mode==='challenge'?'6→7→8 연속 완주':'보드 완주')+' · '+fmt(total));}
}else if(!ktNeighbors(i,new Set(st.path)).length)k.note='다음 이동이 막혔습니다. 무르기 또는 다시 시작을 이용하세요.';
render();};
ktUndo=function(){if(!st.kt||st.kt.mode==='challenge'||st.kt.phase!=='playing'||st.path.length<=1)return;st.path.pop();st.hint=null;st.kt.undid=true;st.kt.note='마지막 이동을 되돌렸습니다.';render();};
ktHint=function(){if(!st.kt||st.kt.mode==='challenge'||st.kt.phase!=='playing')return;var visited=new Set(st.path),opts=ktNeighbors(st.path[st.path.length-1],visited);
if(!opts.length)return;opts.sort(function(a,b){return ktNeighbors(a,new Set(st.path.concat(a))).length-ktNeighbors(b,new Set(st.path.concat(b))).length;});
st.hint=opts[0];st.kt.assists++;st.kt.note='이동 후보를 강조했습니다. 힌트는 완주를 보장하지 않습니다.';render();};
ktDraw=function(){var k=st.kt;if(!k)return;var n=k.size,used=new Set(st.path),last=st.path[st.path.length-1],play=k.phase==='playing';
var possible=play?ktNeighbors(last,used):[],sizeButtons='',cells='',i;
for(i=5;i<=10;i++)sizeButtons+='<button class="'+(i===n?'on':'')+'" onclick="tpKSize('+i+')" '+(k.phase!=='setup'?'disabled':'')+'>'+i+'×'+i+'</button>';
for(i=0;i<n*n;i++){var isCurrent=i===last,visited=used.has(i),validStart=k.size%2===0||(Math.floor(i/n)+i%n)%2===0,enabled=k.phase==='setup'&&validStart||possible.includes(i),isHint=i===st.hint;
cells+='<button type="button" class="ktx-cell '+(isCurrent?'current ':'')+(visited?'visited ':'')+(enabled?'available ':'')+(isHint?'hint':'')+'" onclick="ktMove('+i+')" '+(!enabled||!!finishText||k.phase==='board-win'?'disabled':'')+' aria-label="'+(Math.floor(i/n)+1)+'행 '+(i%n+1)+'열 '+(isCurrent?'현재 위치':visited?'방문 완료':enabled?'이동 가능':'')+'">'+(isCurrent?'♞':visited?st.path.indexOf(i)+1:isHint?'✦':'')+'</button>';}
var opts='<div class="ktx-config"><b>플레이 방식</b><button class="'+(k.mode==='practice'?'on':'')+'" onclick="tpKMode(\'practice\')" '+(k.phase!=='setup'?'disabled':'')+'>자유 연습</button><button class="'+(k.mode==='challenge'?'on':'')+'" onclick="tpKMode(\'challenge\')" '+(k.phase!=='setup'?'disabled':'')+'>방송 챌린지 6→7→8</button>'+(k.mode==='practice'?'<b>보드 크기</b>'+sizeButtons:'<small>6×6 → 7×7 → 8×8 · 제한 60분 · 무르기와 힌트 사용 불가</small>')+'</div>';
var progress='<div class="ktx-head"><strong>'+(k.mode==='challenge'?'챌린지 '+(k.step+1)+'/3':'자유 연습')+' · '+n+'×'+n+'</strong><span class="ktx-clock">'+fmt(k.carry+(k.frozen===undefined?seconds():k.frozen))+'</span></div><div class="ktx-track"><i style="width:'+(st.path.length/(n*n)*100)+'%"></i></div>';
var next=k.phase==='board-win'&&k.mode==='challenge'&&k.step<2?'<button class="primary" onclick="tpKNext()">다음 보드 →</button>':'';
var controls='<div class="ktx-actions"><button onclick="ktUndo()" '+(st.path.length<=1||!play||k.mode==='challenge'?'disabled':'')+'>↶ 한 수 무르기</button><button onclick="ktHint()" '+(!possible.length||!play||k.mode==='challenge'?'disabled':'')+'>✦ 다음 수 힌트</button><button onclick="tpKReset()">↻ 다시 시작</button>'+next+'</div>';
var html='<section class="ktx-wrap">'+progress+opts+'<div class="ktx-board" style="--kn:'+n+'">'+cells+'</div><div class="ktx-note" role="status" aria-live="polite">'+k.note+'</div>'+controls+'<div class="ktx-foot">방문 '+st.path.length+'/'+(n*n)+' · 이동 후보 '+possible.length+' · 힌트 '+k.assists+'회</div></section>';
stage(html,'<p class="muted">나이트는 (±1,±2) 이동하며 이미 방문한 칸에는 다시 갈 수 없습니다. 모든 칸을 한 번씩 방문하면 성공입니다.</p><p class="muted">힌트와 무르기를 사용한 판은 최고 기록 대상에서 제외합니다. 기록은 이 브라우저에만 저장됩니다.</p>');};
})();