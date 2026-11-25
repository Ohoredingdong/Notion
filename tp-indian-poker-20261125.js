// Indian Poker: season 1 standard duel, equal 20-chip starting stacks.
(function(){
function cap(w){const o=1-w,d=st.contrib[o]-st.contrib[w];return Math.max(0,Math.min(st.chips[w]-d,st.chips[o]));}
function pay(w,n){st.chips[w]-=n;st.contrib[w]+=n;st.pot+=n;}
function settle(w,kind){
 const pot=st.pot, cards=st.cards.slice();let penalty=0,refund=false;
 if(kind==='fold'&&cards[1-w]===10){penalty=Math.min(10,st.chips[1-w]);st.chips[1-w]-=penalty;st.chips[w]+=penalty;}
 if(w!==null)st.chips[w]+=pot;else {st.carry=pot;if(st.chips.some(x=>x===0)){st.chips[0]+=pot/2;st.chips[1]+=pot/2;st.carry=0;refund=true;}}
 st.pot=0;st.phase='showdown';st.seen.push(...cards);
 const summary=w===null?(refund?'동점 · 올인 팟 균등 반환':'동점 · 팟 이월'):(w===0?'내 승리':'AI 승리')+(kind==='fold'?' · 다이':' · 카드 공개');
 st.reveal={kind,cards,pot,penalty,summary};logit(summary+' · '+cards.join(' : ')+(penalty?' · 10카드 벌금 '+penalty+'칩':''));
 if(st.chips.some(x=>x===0))finish(st.chips[0]>st.chips[1],`최종 칩: 나 ${st.chips[0]} / AI ${st.chips[1]}`);
}
function move(w,type,n){
 if(finishText||st.phase!=='bet'||st.turn!==w)return false;
 const d=st.contrib[1-w]-st.contrib[w];
 if(type==='fold'){settle(1-w,'fold');return true;}
 if(type==='call'){if(d<=0||d>st.chips[w])return false;pay(w,d);pokerShowdown();return true;}
 if(type!=='raise'||!Number.isInteger(n)||n<1||n>cap(w))return false;
 pay(w,d+n);logit((w===0?'나':'AI')+' '+(d?'레이즈':'첫 베팅')+' · '+(d+n)+'칩 제출');st.turn=1-w;return true;
}
// Decision receives only visible opponent card, public history and betting state.
function choose(visible,seen,d,max,pot,stack,random){
 const pool=Array.from({length:10},(_,i)=>[i+1,i+1]).flat();for(const v of [...seen,visible]){const i=pool.indexOf(v);if(i>=0)pool.splice(i,1);}
 const equity=(pool.filter(v=>v>visible).length+.5*pool.filter(v=>v===visible).length)/Math.max(1,pool.length);
 const risk=pool.filter(v=>v===10).length/Math.max(1,pool.length);
 if(d===0)return ['raise',Math.min(max,equity>.65||random<.16?3:1)];
 const odds=d/(pot+d);if(equity+Math.min(.22,risk*10/Math.max(1,d))<odds&&random>.12)return ['fold',0];
 if(max>0&&((equity>.73&&random<.42)||random<.08))return ['raise',Math.min(max,3)];
 return ['call',0];
}
initPoker=function(){st={chips:[20,20],deck:[],seen:[],pot:0,carry:0,round:0,cards:[],contrib:[0,0],turn:0,first:Math.random()<.5?0:1,phase:'bet',reveal:null};pokerDeal();};
pokerDeal=function(){
 if(finishText)return;
 if(st.chips.some(x=>x<1)){finish(st.chips[0]>st.chips[1],`최종 칩: 나 ${st.chips[0]} / AI ${st.chips[1]}`);return;}
 if(st.deck.length<2){st.deck=shuffle(Array.from({length:10},(_,i)=>[i+1,i+1]).flat());st.seen=[];}
 st.round++;st.cards=[st.deck.pop(),st.deck.pop()];st.contrib=[0,0];st.pot=st.carry;st.carry=0;st.phase='bet';st.reveal=null;st.turn=(st.first+st.round-1)%2;pay(0,1);pay(1,1);logit(st.round+'번째 판 · 기본 1칩씩');
 if(st.chips.some(x=>x===0)){pokerShowdown();return;}if(st.turn===1)pokerAI();
};
pokerShowdown=function(){if(st.phase!=='bet'||st.contrib[0]!==st.contrib[1])return;const [a,b]=st.cards;settle(a===b?null:a>b?0:1,'showdown');};
pokerFold=function(w){if(st.phase==='bet'&&st.turn===w&&!finishText)settle(1-w,'fold');};
pokerAI=function(){if(st.phase!=='bet'||st.turn!==1||finishText)return;const [type,n]=choose(st.cards[0],st.seen,st.contrib[0]-st.contrib[1],cap(1),st.pot,st.chips[1],Math.random());move(1,type,n);};
pokerAct=function(type,n=0){if(current!=='인디언 포커')return;if(move(0,type,n)&&st.phase==='bet'&&st.turn===1)pokerAI();render();};
pokerNext=function(){if(current==='인디언 포커'&&st.phase==='showdown'&&!finishText){pokerDeal();render();}};
drawPoker=function(){
 const done=st.phase==='showdown',r=st.reveal,d=st.contrib[1]-st.contrib[0],max=cap(0);
 const cards=done?`${flipTile('front',r.cards[0],'내 카드')}<span class="round-vs">VS</span>${flipTile('front',r.cards[1],'AI 카드')}`:`${flipTile('back','?','내 이마 카드')}<span class="round-vs">VS</span>${flipTile('front',st.cards[1],'AI 이마 카드')}`;
 const controls=done?(finishText?'':action('다음 판 배분','pokerNext()')):`${d>0?action('콜 '+d+'칩',"pokerAct('call')",d>st.chips[0]):''}${max>0?`<label class="small">추가 칩 <input id="ip-raise" aria-label="추가 베팅 칩" type="number" min="1" max="${max}" value="1" step="1" style="width:62px;padding:8px;background:#21181a;color:#f1e4d0;border:1px solid #8a7058;border-radius:5px"></label>${action(d?'레이즈':'베팅',"pokerAct('raise',Number(document.getElementById('ip-raise').value))",false,'blue')}${action('최대 '+max,"pokerAct('raise',"+max+")",false,'blue')}`:''}${action('다이',"pokerAct('fold')",false,'red')}`;
 stage(`${exBar([st.round+'번째 판','팟 '+(done?r.pot:st.pot)+'칩','남은 덱 '+st.deck.length+'장'])}${scores(['내 칩','AI 칩'],st.chips)}<section class="round-frame"><div class="round-kicker">${done?'SHOWDOWN · 판정 공개':'BETTING · 베팅 중'}</div><h2>${done?txt(r.summary):'상대의 카드만 보고 선택하세요'}</h2><div class="round-flip-row">${cards}</div><div class="info">${done?(r.penalty?'10카드 벌금 '+r.penalty+'칩 · ':'')+'정산된 칩을 확인하세요.':d>0?'콜 '+d+'칩 또는 레이즈·다이':'첫 베팅 또는 다이 · 체크 없음'}</div><div class="round-controls" style="flex-wrap:wrap">${controls}</div></section>`,`<div class="info">1:1 · 각 20칩 시작 · 기본 1칩. 동점 팟 이월, 10을 들고 다이하면 10칩 벌금(잔액 한도). 상대가 맞출 수 있는 칩까지만 베팅. 올인 동점은 팟 균등 반환.</div>${scores(['내 판 베팅','AI 판 베팅'],st.contrib)}<p class="small">이번 덱 공개 카드: ${st.seen.join(' · ')||'없음'}</p>`);
};
})();
