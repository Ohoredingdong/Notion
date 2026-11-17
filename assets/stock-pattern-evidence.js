/* Research heuristics; confirmed pivot evidence, never an order or probability. */
(function(root){'use strict';
const n=x=>typeof x==='number'&&Number.isFinite(x);
function validate(input,now=Date.now()){
 const errors=[],bars=input?.bars,e=input?.evidence||{};
 for(const k of ['identity_verified','exchange_sessions_verified','adjustment_verified','corporate_actions_reviewed','use_rights_verified'])if(e[k]!==true)errors.push(k);
 if(!input?.symbol||e.symbol!==input.symbol)errors.push('symbol_mismatch');
 if(!/^https:\/\//.test(e.source_url||''))errors.push('source_missing');
 if(!['split_adjusted','split_and_dividend_adjusted'].includes(e.price_basis))errors.push('price_basis_unverified');
 if(!Number.isFinite(Date.parse(e.observed_at))||now-Date.parse(e.observed_at)>18*3600000||Date.parse(e.observed_at)>now+300000)errors.push('stale_observation');
 if(!Array.isArray(bars)||bars.length<40)errors.push('insufficient_bars');
 else {for(let i=0;i<bars.length;i++){const b=bars[i];if(!b||!['open','high','low','close','volume'].every(k=>n(b[k]))||b.low<=0||b.volume<0||b.high<Math.max(b.open,b.close,b.low)||b.low>Math.min(b.open,b.close,b.high)||!/^\d{4}-\d{2}-\d{2}$/.test(b.date||'')||!Number.isFinite(Date.parse(b.date))||(i&&b.date<=bars[i-1].date))errors.push('invalid_ohlcv');}if(bars.at(-1).date!==e.expected_session)errors.push('incomplete_session');}
 return [...new Set(errors)];
}
function pivots(bars,w=3){const out=[];for(let i=w;i<bars.length-w;i++){const side=bars.slice(i-w,i).concat(bars.slice(i+1,i+w+1));if(side.every(x=>x.high<bars[i].high))out.push({index:i,value:bars[i].high,type:'high',confirmed_at:i+w});if(side.every(x=>x.low>bars[i].low))out.push({index:i,value:bars[i].low,type:'low',confirmed_at:i+w})}return out}
function line(points){const mx=points.reduce((s,p)=>s+p.index,0)/points.length,my=points.reduce((s,p)=>s+p.value,0)/points.length,den=points.reduce((s,p)=>s+(p.index-mx)**2,0);if(!den)return null;const slope=points.reduce((s,p)=>s+(p.index-mx)*(p.value-my),0)/den,intercept=my-slope*mx;return{slope,intercept,at:i=>slope*i+intercept,error:Math.max(...points.map(p=>Math.abs(p.value-(slope*p.index+intercept))))/my}}
function analyze(input,now=Date.now()){
 const errors=validate(input,now);if(errors.length)return{status:'blocked',errors,patterns:[],orders_enabled:false};
 const b=input.bars,last=b.length-1,p=pivots(b),highs=p.filter(x=>x.type==='high').slice(-3),lows=p.filter(x=>x.type==='low').slice(-3),patterns=[];
 const avg=b.slice(-21,-1).reduce((s,x)=>s+x.volume,0)/20,vr=avg>0?b[last].volume/avg:null;
 if(highs.length===3&&lows.length===3){const hi=line(highs),lo=line(lows),start=Math.max(highs[0].index,lows[0].index),span=last-start,widthStart=hi.at(start)-lo.at(start),widthNow=hi.at(last)-lo.at(last);if(span>=15&&hi.error<=.02&&lo.error<=.02&&widthStart>0&&widthNow>0&&widthNow/widthStart<.8){let kind=null;if(hi.slope<0&&lo.slope>0)kind='symmetrical_triangle';else if(hi.slope>0&&lo.slope>0&&lo.slope>hi.slope)kind='rising_wedge';else if(hi.slope<0&&lo.slope<0&&hi.slope<lo.slope)kind='falling_wedge';if(kind){const direction=b[last].close>hi.at(last)?'up':b[last].close<lo.at(last)?'down':null;patterns.push({kind,state:direction?(vr>=1.5?'breakout_volume_confirmed':'breakout_volume_unconfirmed'):'forming',direction,confirmed_at:Math.max(...highs.concat(lows).map(x=>x.confirmed_at)),observed_at:b[last].date,resistance:hi.at(last),support:lo.at(last),volume_ratio:vr,method:'3 high + 3 low pivots, 3-bar confirmation, <=2% line error; heuristic, unvalidated predictive value'});}}}
 if(lows.length>=2){const [a,z]=lows.slice(-2),distance=z.index-a.index,near=Math.abs(a.value-z.value)/Math.max(a.value,z.value);if(distance>=10&&distance<=60&&near<=.03){const neck=Math.max(...b.slice(a.index+1,z.index).map(x=>x.high)),bottom=Math.min(a.value,z.value);if(neck/bottom>=1.05)patterns.push({kind:'double_bottom',state:b[last].close<bottom?'invalidated':b[last].close>neck?(vr>=1.5?'breakout_volume_confirmed':'breakout_volume_unconfirmed'):'forming',direction:b[last].close>neck?'up':null,confirmed_at:z.confirmed_at,observed_at:b[last].date,resistance:neck,support:bottom,volume_ratio:vr,method:'two confirmed lows within 3%; 10–60 bars; neckline at least 5% above bottom; heuristic'});}}
 return{status:'observed',patterns,orders_enabled:false,probability:null,warning:'패턴 유사성은 검증된 수익 예측이 아닙니다. 확인 시점 이전으로 소급하지 않습니다.'};
}
const api={validate,pivots,line,analyze};if(typeof module==='object'&&module.exports)module.exports=api;else root.StockPatternEvidence=api;
})(typeof window==='object'?window:globalThis);
