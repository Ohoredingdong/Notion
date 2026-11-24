/* Game-based collection art, not AI product photography. All previews are decorative,
   deterministic snapshots of the in-app play mechanics. */
(function(){
'use strict';
const definitions={
'흑과 백':['duel','0,1,2,3,4,5,6,7,8'],'인디언 포커':['poker','6,?,12'],
'결! 합!':['set','●,▲,■,■,●,▲,▲,■,●'],'십이장기':['janggi','相,王,將,子,,,,子,將,王,相'],
'1·2·3 게임':['cards','1,2,3'],'마이너스 경매':['auction','−21'],
'나인 멘스 모리스':['morris',''], '콰트로':['quatro','1,2,3,4'],
'헥사곤':['hex','3,2,5,1,8,4,6,7,9'],'같은 숫자 찾기':['memory','2,7,?,4,?,2,3,7,4,?'],
'같은 그림 찾기':['memory','◆,▲,?,■,▲,?,◆,■'],
'연승게임':['cards','2,5,7'],'블라인드 오목':['gomoku',''],
'기사의 여행':['knight',''],'시간 경매':['clock','00:59'],
'큐브 세기':['cubes',''],'네모 세기':['matrix','1,4,2,3,5,8,2,6,4,3,2,4,1,3,2,8'],
'4인 3목':['gomoku',''],'바그찰':['baghchal',''],
'몽타주':['portrait',''],'신의 판결':['dice','2,5'],
'미스터리 사인':['equation','3+5=8'],'벽바둑':['wall',''],
'벽바둑 2':['wall',''],'해 달 별':['symbols','☀,☾,★'],
'하나 빼기':['cards','3,8']
};
const esc=(v)=>String(v).replace(/[&<>"']/g,(x)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const cells=(data,cls='')=>data.map((a,i)=>'<span class="tpv-cell '+cls+' '+(i%2?'tpv-even':'')+'">'+esc(a||'')+'</span>').join('');
function gamePreview(name){
 const info=definitions[name]||['cards','?'],kind=info[0],values=info[1].split(',');
 let body='';
 switch(kind){
 case 'duel':body='<div class="tpv-duel"><div class="tpv-opp">PLAYER</div><div class="tpv-card tpv-dark">?</div><span class="tpv-versus">VS</span><div class="tpv-card tpv-light">?</div><div class="tpv-opp">AI</div></div><div class="tpv-numbers">'+cells(values)+'</div>';break;
 case 'poker':body='<div class="tpv-duel"><div class="tpv-card tpv-dark">?</div><span class="tpv-versus">VS</span><div class="tpv-card tpv-light">6</div></div><div class="tpv-chips"><span>●</span><span>●</span><span>●</span><b>POT 12</b></div>';break;
 case 'set':body='<div class="tpv-set">'+cells(values.map((v,i)=>'<x>'+v+'</x>'),'tpv-shape')+'</div>';body=body.replace(/&lt;x&gt;|&lt;\/x&gt;/g,'');break;
 case 'janggi':body='<div class="tpv-board tpv-janggi">'+cells(['相','王','將','子','','','','','子','將','王','相'])+'</div>';break;
 case 'cards':body='<div class="tpv-cards">'+values.map((v,i)=>'<span class="tpv-card '+(i%2?'tpv-dark':'tpv-light')+'">'+esc(v)+'</span>').join('')+'</div>';break;
 case 'auction':body='<div class="tpv-auction"><span class="tpv-card tpv-light">'+esc(values[0])+'</span><p>● ● ● ● ● ● ●</p></div>';break;
 case 'morris':body='<div class="tpv-morris"><span></span><span></span><span></span><i class="dot d1"></i><i class="dot d2"></i><i class="dot d3"></i><i class="dot d4"></i></div>';break;
 case 'quatro':body='<div class="tpv-quatro">'+values.map((v,i)=>'<span style="--qc:'+['#b66b7d','#678eab','#719c89','#cbb16d'][i]+'">'+esc(v)+'</span>').join('')+'</div>';break;
 case 'hex':body='<div class="tpv-hex">'+cells(values)+'</div>';break;
 case 'memory':body='<div class="tpv-memory">'+cells(values.map((v,i)=>i%3===0?v:'?'))+'</div>';break;
 case 'gomoku':case 'wall':case 'baghchal':
  body='<div class="tpv-board tpv-go '+kind+'">'+cells(Array.from({length:kind==='baghchal'?25:49},(_,i)=>[8,16,24,30,40].includes(i)?'●':[12,22,34].includes(i)?'○':''))+'</div>';break;
 case 'knight':body='<div class="tpv-board tpv-knight">'+cells(Array.from({length:64},(_,i)=>i===27?'♞':''))+'</div>';break;
 case 'clock':body='<div class="tpv-clock"><div class="tpv-hands"></div><strong>'+esc(values[0])+'</strong></div>';break;
 case 'cubes':body='<div class="tpv-cubes">'+cells(['▰','▰','▰','▰','▰','▰','▰'])+'</div>';break;
 case 'matrix':body='<div class="tpv-matrix">'+cells(values)+'</div>';break;
 case 'portrait':body='<div class="tpv-portrait"><div class="tpv-face"><i></i><b>?</b></div><div class="tpv-face"><i></i><b>?</b></div></div>';break;
 case 'dice':body='<div class="tpv-dice">'+cells(values)+'</div>';break;
 case 'equation':body='<div class="tpv-equation">3 + 5 = 8<div>4 × ? = 20</div></div>';break;
 case 'symbols':body='<div class="tpv-cards">'+values.map((v,i)=>'<span class="tpv-card '+(i%2?'tpv-dark':'tpv-light')+'">'+esc(v)+'</span>').join('')+'</div>';break;
 default:body='<div class="tpv-equation">'+esc(name)+'</div>';
 }
 return '<div class="tpv-play-art tpv-'+kind+'"><div class="tpv-play-bar"><span class="tpv-live-dot"></span><span>GAME BOARD</span><span>01 / 09</span></div><div class="tpv-play-scene">'+body+'</div><div class="tpv-play-footer"><span>PLAYER 1</span><span>VS AI</span></div></div>';
}
const original=window.showHome;
if(typeof original!=='function')return;
window.showHome=function(...args){
 const out=original.apply(this,args),home=document.querySelector('.tp-home');
 if(!home||typeof tpGames!=='function')return out;
 const names=tpGames().slice(tpPage*4,tpPage*4+4);
 home.querySelectorAll('.tp-gallery .tp-game').forEach((button,i)=>{
  const art=button.querySelector('.tp-image'),name=names[i];if(!art||!name)return;
  art.style.backgroundImage='none';art.style.filter='none';art.classList.add('tpv-art');
  art.setAttribute('aria-hidden','true');art.removeAttribute('role');art.removeAttribute('aria-label');
  art.innerHTML=gamePreview(name);button.classList.add('tpv-game');
 });
 const recent=home.querySelector('.tp-recent-image');
 if(recent){recent.style.backgroundImage='none';recent.classList.add('tpv-recent');recent.innerHTML=tpRecent&&definitions[tpRecent]?gamePreview(tpRecent):''}
 return out;
};
window.showHome();
})();
