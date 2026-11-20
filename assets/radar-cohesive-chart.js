(function(){
'use strict';
let span=63;
const E=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const num=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
const f=(v,d=2)=>num(v)===null?'미확인':v.toLocaleString('ko-KR',{maximumFractionDigits:d});
const norm=s=>String(s||'').toUpperCase().replace(/\.(KS|KQ)$/,'');
// Synchronous SHA-256 over the exact ASCII JSON evidence bytes; no network/async render.
function digest(s){
 if(/[^\x00-\x7f]/.test(s))throw Error('non_ascii_evidence');
 const primes=[],K=[],H=[];for(let n=2;primes.length<64;n++){if(primes.every(p=>n%p)){primes.push(n);K.push((Math.cbrt(n)%1*4294967296)|0);if(H.length<8)H.push((Math.sqrt(n)%1*4294967296)|0);}}
 const a=Array.from(s,c=>c.charCodeAt(0)),bits=a.length*8;a.push(128);while(a.length%64!==56)a.push(0);for(let j=7;j>=0;j--)a.push(j>=4?0:(bits>>>j*8)&255);
 const rr=(x,n)=>(x>>>n)|(x<<(32-n));
 for(let z=0;z<a.length;z+=64){const w=[];for(let i=0;i<16;i++)w[i]=(a[z+i*4]<<24)|(a[z+i*4+1]<<16)|(a[z+i*4+2]<<8)|a[z+i*4+3];for(let i=16;i<64;i++){let x=w[i-15],y=w[i-2];w[i]=(w[i-16]+(rr(x,7)^rr(x,18)^(x>>>3))+w[i-7]+(rr(y,17)^rr(y,19)^(y>>>10)))|0;}let [h0,b,c,d,e,f,g,h]=H;for(let i=0;i<64;i++){const t1=(h+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^(~e&g))+K[i]+w[i])|0,t2=((rr(h0,2)^rr(h0,13)^rr(h0,22))+((h0&b)^(h0&c)^(b&c)))|0;h=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=h0;h0=(t1+t2)|0;}[h0,b,c,d,e,f,g,h].forEach((v,i)=>H[i]=(H[i]+v)|0);}
 return H.map(v=>(v>>>0).toString(16).padStart(8,'0')).join('');
}
const eq=(a,b)=>{if(a===b)return true;if(!a||!b||typeof a!=='object'||typeof b!=='object')return false;const k=Object.keys(a);return k.length===Object.keys(b).length&&k.every(x=>eq(a[x],b[x]));};
const validDate=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
const exchangeMatches=(market,symbol,exchange)=>{
 const exchanges=market==='KR'?(String(symbol).endsWith('.KQ')?['KOE','KOSDAQ']:['KSC','KOSPI']):['NMS','NGM','NCM','NAS','NASDAQ','NASDAQGS','NASDAQGM','NASDAQCM','NYQ','NYSE','ASE','AMEX','NYSEAMERICAN','PCX','NYSEARCA','BTS','BATS','CBOE'];
 return ['KR','US'].includes(market)&&exchanges.includes(String(exchange).toUpperCase());
};
function observed(c){
 const ev=c?.technical?.evidence;if(!ev?.stock)return {reason:'원시 OHLCV 증거 없음'};
 try{
 const require=(v,m)=>{if(!v)throw Error(m);},block=ev.stock,s=block.source||{},meta=s.source_metadata||{},market=c.market,symbol=c.source_symbol,expected=c.expected_session?.date;
 require(ev.version==='technical-window-evidence-v1'&&ev.market===market,'증거 버전·시장 불일치');
 require(typeof block.rows_json==='string'&&block.rows_json.length<1000000&&digest(block.rows_json)===block.rows_sha256,'SHA-256 불일치');
 require(eq(block.columns,['date','open','high','low','close','volume','split']),'열 정의 불일치');
 require(s.source_identity_verified===true&&s.provider_symbol===symbol&&norm(symbol)===norm(c.symbol)&&s.market===market&&s.currency===c.currency&&eq(s,c.price_source),'기업·가격 출처 결합 불일치');
 require(['US','KR'].includes(market)&&meta.symbol===symbol&&meta.currency===c.currency&&meta.instrumentType==='EQUITY'&&meta.exchangeTimezoneName===(market==='KR'?'Asia/Seoul':'America/New_York'),'응답 종목·통화·시간대 불일치');
 require(exchangeMatches(market,symbol,meta.exchangeName),'거래소 불일치');
 require(s.basis==='provider_close_auto_adjust_false'&&validDate(expected)&&s.expected_session===expected,'세션·가격 조정 기준 불일치');
 const attempt=s.attempts?.[s.selected_attempt-1],stamp=Date.parse(attempt?.received_at),closed=Date.parse(c.expected_session?.closed_at),buffer=c.expected_session?.buffer_minutes;
 require(Number.isInteger(s.selected_attempt)&&s.selected_attempt>0&&attempt?.status==='verified_response'&&Number.isFinite(stamp)&&stamp<=Date.now()&&Number.isFinite(closed)&&closed<=stamp&&num(buffer)!==null&&buffer>=0&&closed+buffer*60000<=stamp,'완료 세션·수집 시점 불일치');
 require(attempt.request?.period==='1y'||(validDate(attempt.request?.start)&&validDate(attempt.request?.end)),'수집 기간 미확인');
 const rows=JSON.parse(block.rows_json);require(Array.isArray(rows)&&rows.length>=2&&rows.length===block.stored_count&&Number.isInteger(block.original_count)&&block.original_count>=rows.length,'봉 수 불일치');
 let previous='';const bars=rows.map(r=>{require(Array.isArray(r)&&r.length===7&&validDate(r[0])&&r[0]>previous&&r[0]<=expected,'날짜·순서·중복 불일치');previous=r[0];require(r.slice(1,5).every(v=>num(v)!==null&&v>0)&&num(r[5])!==null&&r[5]>=0&&num(r[6])!==null&&r[6]>=0&&r[2]>=Math.max(r[1],r[4])&&r[3]<=Math.min(r[1],r[4]),'OHLCV 범위 오류');return {date:r[0],open:r[1],high:r[2],low:r[3],close:r[4],volume:r[5],split:r[6]};});
 const last=bars.at(-1),same=(a,b)=>num(a)!==null&&Math.abs(a-b)<=Math.max(1e-7,Math.abs(b)*1e-9);
 require(last.date===s.latest_completed_session&&last.date===attempt.latest_completed_session&&last.date===c.price_session&&last.date===c.technical.date&&same(c.price,last.close)&&same(c.technical.close,last.close),'최종 종가·세션 결합 불일치');
 return {bars,ohlc:true,proof:true,src:{currency:c.currency,status:last.date<expected?'stale':'ok',collected_at:attempt.received_at,source_url:'',basis:ev.basis},digest:block.rows_sha256};
 }catch(e){return {reason:'원시 OHLCV 검증 제외: '+e.message};}
}

const closeBasis='provider_close_auto_adjust_false';
const near=(a,b)=>num(a)!==null&&num(b)!==null&&Math.abs(a-b)<=Math.max(1e-7,Math.abs(b)*1e-9);
function dailyPair(c,d,ctx){
 const bars=d.bars,last=bars.at(-1),prev=bars.at(-2),src=d.proof?c:d.src,proof=src?.daily_change,source=src?.price_source,meta=source?.source_metadata,
 symbol=c?.source_symbol||src?.provider||c?.symbol,market=c?.market,currency=c?.currency;
 const expected=d.proof?c.expected_session?.date:src.expected_session;
 const world=ctx?.data?.worldFlow?.indicators;
 const expectedWorld=Array.isArray(world)?world.find(x=>x?.id===(market==='KR'?'kospi':'sp500')&&x.region===market&&x.freshness?.basis==='completed_exchange_session'&&x.freshness?.calendar===(market==='KR'?'XKRX':'XNYS'))?.freshness?.expected_session:null;
 const attempt=source?.attempts?.[source.selected_attempt-1],received=Date.parse(attempt?.received_at);
 if(!proof||!source||!meta||!last||!prev||!currency||!['KR','US'].includes(market))return null;
 if(d.src.status!=='ok'||!validDate(expected)||last.date!==expected||src.price_session!==last.date||(validDate(expectedWorld)&&last.date<expectedWorld))return null;
 if(source.source_identity_verified!==true||source.provider_symbol!==symbol||source.market!==market||source.currency!==currency||source.basis!==closeBasis||
    source.expected_session!==last.date||source.latest_completed_session!==last.date||meta.symbol!==symbol||meta.currency!==currency||
    meta.instrumentType!=='EQUITY'||meta.exchangeTimezoneName!==(market==='KR'?'Asia/Seoul':'America/New_York')||!exchangeMatches(market,symbol,meta.exchangeName)||
    !Number.isInteger(source.selected_attempt)||source.selected_attempt<1||attempt?.status!=='verified_response'||attempt.latest_completed_session!==last.date||
    !Number.isFinite(received)||received<Date.parse(last.date)||received>Date.now())return null;
 if(proof.version!=='completed-session-change-v1'||proof.status!=='verified'||proof.reason!=null||proof.source_identity_verified!==true||
    proof.consecutive_sessions!==true||proof.market!==market||proof.provider_symbol!==symbol||proof.currency!==currency||proof.basis!==closeBasis||
    proof.price_session!==last.date||proof.previous_session!==prev.date||proof.expected_previous_session!==prev.date||
    !near(proof.close,last.close)||!near(proof.previous_close,prev.close)||!near(proof.change_1d_pct,(last.close/prev.close-1)*100)||
    (d.proof&&last.split!==0)||(!d.proof&&(!Array.isArray(src.corporate_actions)||src.corporate_actions.some(e=>e?.date===last.date&&e.split!==0))))return null;
 return {last,prev};
}
function volumeRatio(b,end){
 const prior=b.slice(Math.max(0,end-20),end).map(x=>x.volume),vol=b[end]?.volume;
 if(prior.length!==20||!prior.every(v=>num(v)!==null&&v>=0)||num(vol)===null||vol<0)return null;
 const avg=prior.reduce((a,v)=>a+v,0)/20;
 return avg>0?vol/avg:null;
}
function hasRecentSplit(d){
 if(d.bars.length<22)return true;
 const start=d.bars.at(-22).date;
 return d.proof?d.bars.slice(-22).some(x=>x.split!==0):
  !Array.isArray(d.src.corporate_actions)||d.src.corporate_actions.some(e=>validDate(e?.date)&&e.date>=start&&num(e.split)!==null&&e.split!==0);
}
function dataset(c,ctx){
 const evidence=observed(c);if(evidence.proof){const sources=ctx?.data?.charts?.series||{},matched=Object.keys(sources).find(k=>norm(k)===norm(c?.symbol));evidence.src.source_url=sources[matched]?.source_url||'';return evidence;}
 const series=ctx?.data?.charts?.series||{};const key=Object.keys(series).find(k=>norm(k)===norm(c?.symbol));const src=series[key];
 if(!src||!Array.isArray(src.bars))return {error:'선택 기업의 저장 가격 자료가 없습니다.'};
 if(norm(src.symbol)!==norm(c?.symbol)||(src.market&&src.market!==c.market)||(src.currency&&src.currency!==c.currency))return {error:'저장 종가의 종목·시장·통화가 선택 기업과 일치하지 않습니다.'};
 let bars=src.bars;const seen=new Set();
 if(bars.some(b=>!/^\d{4}-\d{2}-\d{2}$/.test(b.date)||!Number.isFinite(Date.parse(b.date))||new Date(b.date).toISOString().slice(0,10)!==b.date||Date.parse(b.date)>Date.now()+86400000||num(b.close)===null||b.close<=0||seen.has(b.date)||(seen.add(b.date),false)))return {error:'날짜·가격·중복 검사를 통과하지 못해 차트를 숨겼습니다.'};
 bars=[...bars].sort((a,b)=>a.date.localeCompare(b.date));
 if(bars.length<2)return {error:'가격 흐름을 그릴 저장 종가가 2개 미만입니다.'};
 const ohlc=bars.every(b=>['open','high','low'].every(k=>num(b[k])!==null&&b[k]>0)&&b.high>=Math.max(b.open,b.close)&&b.low<=Math.min(b.open,b.close)&&b.high>=b.low);
 return {src,bars,ohlc:false,reason:evidence.reason};
}
function ema(a,n){if(a.length<n)return [];let v=a.slice(0,n).reduce((s,x)=>s+x,0)/n;const out=Array(n-1).fill(null);out.push(v);for(let i=n;i<a.length;i++){v=a[i]*2/(n+1)+v*(1-2/(n+1));out.push(v);}return out;}
function rsi(a,n=14){if(a.length<=n)return null;let g=0,l=0;for(let i=1;i<=n;i++){let d=a[i]-a[i-1];g+=Math.max(0,d)/n;l+=Math.max(0,-d)/n;}for(let i=n+1;i<a.length;i++){let d=a[i]-a[i-1];g=(g*(n-1)+Math.max(0,d))/n;l=(l*(n-1)+Math.max(0,-d))/n;}return !g&&!l?50:!l?100:100-100/(1+g/l);}
function indicators(b){const a=b.map(x=>x.close),e12=ema(a,12),e26=ema(a,26),m=a.map((_,i)=>num(e12[i])!==null&&num(e26[i])!==null?e12[i]-e26[i]:null),valid=m.filter(x=>x!==null),sig=ema(valid,9);const last=valid.at(-1)??null,signal=sig.at(-1)??null;let bb=null;if(a.length>=20){const t=a.slice(-20),mid=t.reduce((s,v)=>s+v,0)/20,sd=Math.sqrt(t.reduce((s,v)=>s+(v-mid)**2,0)/20);bb={mid,up:mid+2*sd,low:mid-2*sd};}return {rsi:rsi(a),macd:last,signal,hist:last!==null&&signal!==null?last-signal:null,bb};}
function pivots(b){const hi=[],lo=[];for(let i=2;i<b.length-2;i++){const v=b[i].close;if([-2,-1,1,2].every(k=>v>b[i+k].close))hi.push(i);if([-2,-1,1,2].every(k=>v<b[i+k].close))lo.push(i);}return {hi:hi.slice(-2),lo:lo.slice(-2)};}
function lineFor(ids,b){if(ids.length!==2)return null;const [a,z]=ids,s=(b[z].close-b[a].close)/(z-a);return {a,z,s,value:i=>b[z].close+s*(i-z)};}
function comparisons(b,p,all){
 const up=lineFor(p.hi,b),lo=lineFor(p.lo,b),last=b.length-1,results=[];
 const stamp=ids=>ids.map(i=>b[i].date+' '+f(b[i].close)).join(' → ');
 const both=up&&lo, gap0=both?up.value(Math.max(up.z,lo.z))-lo.value(Math.max(up.z,lo.z)):null,gap1=both?up.value(last)-lo.value(last):null;
 const converge=both&&gap0>0&&gap1>0&&gap1<gap0&&up.s<lo.s;
 results.push(['삼각형',converge&&up.s<0&&lo.s>0?'수렴 후보':'조건 미충족','최근 고점선 하향 + 저점선 상향 + 양의 간격 축소']);
 results.push(['쐐기형',converge&&up.s>0&&lo.s>0?'상승쐐기 후보':converge&&up.s<0&&lo.s<0?'하락쐐기 후보':'조건 미충족','두 선 같은 방향 + 양의 간격 축소']);
 let bottom='저점 두 점 부족',bottomRule='두 종가 저점 차이 ≤ 3%, 간격 ≥ 5봉, 사이 반등 ≥ 5%. 넥라인 돌파는 별도 확인';
 if(p.lo.length===2){const [a,z]=p.lo,v=b[a].close,w=b[z].close,peak=Math.max(...b.slice(a+1,z).map(x=>x.close)),match=Math.abs(v-w)/Math.min(v,w)<=.03&&z-a>=5&&peak/Math.max(v,w)>=1.05;bottom=match?'이중바닥 모양 후보 · '+(b[last].close>peak?'현재 종가 넥라인 위':'넥라인 종가 돌파 미확인'):'조건 미충족';}
 results.push(['이중바닥',bottom,bottomRule]);
 let div=[];for(const [ids,name] of [[p.lo,'상승'],[p.hi,'하락']]){if(ids.length!==2)continue;const [a,z]=ids,ia=all.findIndex(v=>v.date===b[a].date),iz=all.findIndex(v=>v.date===b[z].date),r1=rsi(all.slice(0,ia+1).map(v=>v.close)),r2=rsi(all.slice(0,iz+1).map(v=>v.close));if(r1===null||r2===null){div.push(name+': RSI 표본 부족');continue;}const regular=name==='상승'?b[z].close<b[a].close&&r2>r1:b[z].close>b[a].close&&r2<r1;const hidden=name==='상승'?b[z].close>b[a].close&&r2<r1:b[z].close<b[a].close&&r2>r1;div.push(name+': '+(regular?'일반 후보':hidden?'히든 후보':'엇갈림 미확인')+' (RSI '+f(r1)+' → '+f(r2)+')');}
 results.push(['RSI 다이버전스',div.join(' / ')||'피벗 부족','같은 두 저점/고점에서 가격·RSI 변화 방향 비교. 일반: 가격 극값 갱신·RSI 미갱신, 히든: 그 반대']);
 return '<section class="rc-card"><h3>패턴 비교 · 관찰 후보만 표시</h3><p class="rcc-note">종가 피벗의 단순 규칙 비교입니다. 정식 패턴 확정·검증된 매매성과·확률이 아닙니다. 기간을 바꾸면 후보도 달라질 수 있습니다.</p><div class="rcc-indicators">'+results.map(([name,result,rule])=>'<div><h4>'+E(name)+'</h4><strong>'+E(result)+'</strong><p>'+E(rule)+'</p></div>').join('')+'</div><p class="rcc-note">관찰 고점: '+E(stamp(p.hi)||'부족')+'<br>관찰 저점: '+E(stamp(p.lo)||'부족')+'</p></section>';
}
function svg(b,ohlc,overlay,piv,scale){
 const W=760,H=320,L=14,R=86,T=16,B=66,pw=W-L-R,ph=H-T-B;const x=i=>L+i*pw/(b.length-1),y=v=>T+(scale.max-v)*ph/(scale.max-scale.min);let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${overlay?'같은 저장 가격과 최근 확인 피벗 연장선':'실제 저장 가격과 거래량'}">`;
 for(let i=0;i<5;i++){const v=scale.min+(scale.max-scale.min)*i/4;s+=`<line x1="${L}" y1="${y(v)}" x2="${W-R}" y2="${y(v)}" stroke="#e5ebe7"/><text x="${W-R+8}" y="${y(v)+4}" fill="#53626a" font-size="12">${f(v)}</text>`;}
 if(ohlc){const bw=Math.max(1,Math.min(5,pw/b.length*.3));b.forEach((v,i)=>{const color=v.close>=v.open?'#76a58e':'#d49d9c';s+=`<line x1="${x(i)}" x2="${x(i)}" y1="${y(v.high)}" y2="${y(v.low)}" stroke="${color}"/><rect x="${x(i)-bw}" y="${Math.min(y(v.open),y(v.close))}" width="${2*bw}" height="${Math.max(1,Math.abs(y(v.open)-y(v.close)))}" fill="${color}"/>`;});}
 else s+=`<polyline points="${b.map((v,i)=>`${x(i)},${y(v.close)}`).join(' ')}" fill="none" stroke="#579579" stroke-width="2.4"/>`;
 if(overlay)for(const [ids,color] of [[piv.hi,'#55846d'],[piv.lo,'#ac8656']]){const ln=lineFor(ids,b);if(ln){s+=`<line x1="${x(ln.a)}" y1="${y(b[ln.a].close)}" x2="${x(b.length-1)}" y2="${y(ln.value(b.length-1))}" stroke="${color}" stroke-width="2" stroke-dasharray="5 3"/>`;ids.forEach(i=>s+=`<circle cx="${x(i)}" cy="${y(b[i].close)}" r="4" fill="${color}"/>`);}}
 const vols=b.map(v=>num(v.volume)!==null&&v.volume>=0?v.volume:null),max=Math.max(0,...vols.filter(v=>v!==null));if(max)vols.forEach((v,i)=>{if(v!==null)s+=`<rect x="${x(i)-2}" y="${H-27-v/max*26}" width="4" height="${v/max*26}" fill="#a2b8aa"/>`;});
 s+=`<text x="${L}" y="${H-5}" font-size="12" fill="#53626a">${E(b[0].date)}</text><text x="${W-R}" y="${H-5}" text-anchor="end" font-size="12" fill="#53626a">${E(b.at(-1).date)}</text></svg>`;return s;
}
function render(c,ctx){const d=dataset(c,ctx);if(d.error)return `<section class="rc-card rcc"><h3>차트 자료 확인</h3><p>${E(d.error)}</p><p>없는 봉·거래량·지표를 만들어 채우지 않습니다.</p></section>`;
 const b=d.bars.slice(-span),p=pivots(b),up=lineFor(p.hi,b),low=lineFor(p.lo,b),end=b.length-1,price=b.at(-1).close,u=up?.value(end),l=low?.value(end),valid=num(u)!==null&&num(l)!==null&&u>l&&l>0;
 const levels=b.flatMap(v=>d.ohlc?[v.low,v.high]:[v.close]);if(valid)levels.push(u,l);let min=Math.min(...levels),max=Math.max(...levels),pad=(max-min||max*.02)*.08;const scale={min:min-pad,max:max+pad};
 const pos=!valid?'판단선 확인 대기':price>u?'종가가 윗선 위':price<l?'종가가 아랫선 아래':'두 판단선 사이';const ind=indicators(d.bars),pair=dailyPair(c,d,ctx),prior=pair?indicators(d.bars.slice(0,-1)):{},ratio=volumeRatio(d.bars,d.bars.length-1),priorRatio=pair&&!hasRecentSplit(d)?volumeRatio(d.bars,d.bars.length-2):null;
 const mv=(v,w,label,unit='')=>f(v)+(num(v)!==null?unit:'')+(window.RadarCohesive?.compare?.(v,w,{verified:Boolean(pair)&&num(v)!==null&&num(w)!==null,label:label+(pair?' · '+pair.last.date+' / 직전 거래일 '+pair.prev.date:'')})||'');
 const safeURL=(()=>{try{const u=new URL(d.src.source_url);return u.protocol==='https:'&&!u.username&&!u.password;}catch(_){return false;}})();const source=safeURL?`<a href="${E(d.src.source_url)}" target="_blank" rel="noopener noreferrer">가격 출처</a>`:'출처 링크 미확인';
 const pivotText=ids=>ids.length===2?ids.map(i=>`${b[i].date} · ${f(b[i].close)}`).join(' / '):'확인된 피벗 두 점 부족';
 return `<div class="rcc"><div class="rcc-toolbar"><span>${E(c?.name||c?.symbol)} · ${E(d.src.currency||c?.currency||'통화 미확인')} · ${E(b.at(-1).date)} 저장 종가</span><div>${[[21,'최근 21봉'],[63,'최근 63봉'],[126,'최근 126봉']].map(([n,label])=>`<button type="button" data-rcc-span="${n}" aria-pressed="${n===span}">${label}</button>`).join('')}</div></div><p class="rcc-note">${d.ohlc?'출처·해시·종가 결합을 확인한 원시 일봉 캔들':'시가·고가·저가가 없어 종가선으로 표시합니다. 캔들을 추정하지 않습니다.'} ${d.reason?E(d.reason)+' · 종가선 대체':''} · 두 화면은 같은 기간·가격축입니다. ${d.src.status==='stale'?'저장 데이터 지연 표시됨 · ':''}${source}</p>
 <div class="rc-grid rcc-main"><section class="rc-card"><h3>가격 흐름 그대로 보기</h3>${svg(b,d.ohlc,false,p,scale)}<p class="rcc-note">아래 막대: 저장 거래량. 누락 거래량은 빈칸. ${d.bars.length}개 저장봉 중 ${b.length}개 표시.</p></section><section class="rc-card"><h3>같은 차트에 판단선 더하기</h3><strong>${pos}</strong>${svg(b,d.ohlc,true,valid?p:{hi:[],lo:[]},scale)}<p>윗선 ${valid?f(u):'미확인'} · 종가 ${mv(price,pair?.prev.close,'저장 종가')} · 아랫선 ${valid?f(l):'미확인'}</p><p class="rcc-note">마지막 저장봉 거래량 / 직전 20봉 평균: ${mv(ratio,priorRatio,'거래량 배율','배')}. 돌파·반전·수익을 보장하는 신호가 아닙니다.</p></section></div>
 <div class="rcc-conditions"><section class="rc-card"><h4>윗선 위</h4><p>종가 유지와 거래량 동반 여부를 확인합니다. 장중 돌파만으로 확정하지 않습니다.</p></section><section class="rc-card"><h4>구간 안</h4><p>방향 확인 대기. 수렴 모양만으로 삼각형·쐐기형의 성공을 판단하지 않습니다.</p></section><section class="rc-card"><h4>아랫선 아래</h4><p>기존 지지 가정을 재검토합니다. 실제 손절 가격이나 주문 지시가 아닙니다.</p></section></div>
 ${comparisons(b,p,d.bars)}<section class="rc-card"><h3>보조지표 · 패턴 함께 읽기</h3><p class="rcc-note">화살표는 같은 기준으로 확인한 직전 거래일과 비교합니다. 기준선·판단선에는 표시하지 않습니다.</p><div class="rcc-indicators"><div><h4>RSI(14) ${mv(ind.rsi,prior.rsi,'RSI')}</h4><p>Wilder 방식. 30·70은 과매도·과매수 참고선이며 매매 확정 기준이 아닙니다.</p></div><div><h4>MACD(12,26,9)</h4><p>MACD ${mv(ind.macd,prior.macd,'MACD')} / 시그널 ${mv(ind.signal,prior.signal,'MACD 시그널')}<br>히스토그램 ${mv(ind.hist,prior.hist,'MACD 히스토그램')}. 교차만으로 추세 전환을 확정하지 않습니다.</p></div><div><h4>볼린저(20, 2σ)</h4><p>${ind.bb?`상단 ${mv(ind.bb.up,prior.bb?.up,'볼린저 상단')} / 중앙 ${mv(ind.bb.mid,prior.bb?.mid,'볼린저 20봉 평균')} / 하단 ${mv(ind.bb.low,prior.bb?.low,'볼린저 하단')}`:'저장 종가 20개 미만'}<br>종가의 모집단 표준편차. 밴드 이탈은 매수 확정이 아닙니다.</p></div><div><h4>패턴 · 다이버전스</h4><p>위 비교는 종가 피벗 규칙으로 찾은 관찰 후보입니다. 거래량·추세 맥락과 이후 봉 확인 없이 진입 신호로 사용하지 않습니다.</p></div></div><details><summary>판단선과 계산 기준 보기</summary><p>표시 구간의 종가가 앞뒤 2개 봉보다 모두 높은/낮은 점을 확인 피벗으로 사용합니다. 마지막 2개 봉은 미확정으로 제외합니다. 최근 두 고점/두 저점을 직선 연장했으며, 이후 봉에 따라 바뀝니다. 정식 패턴 감지나 미래 예측이 아닙니다.</p><p>고점: ${pivotText(p.hi)}<br>저점: ${pivotText(p.lo)}</p><p>지표는 확보된 전체 ${d.bars.length}개 저장 종가로 계산하며 표시기간 변경과 독립적입니다. EMA는 최초 기간 단순평균으로 초기화. 조정·분할·배당 처리: ${E(d.src.basis||ctx?.data?.charts?.basis||'원천 확인 필요')}. 검증 범위: SHA-256·응답 종목/시장/통화/거래소·저장 세션 종료시간과 수집시간·정렬/중복·OHLCV 범위·마지막 종가 결합. 거래소 휴장 달력을 독립 재검증하거나 기존 14개 기술지표를 재감사하는 것은 아닙니다. 분봉 자료는 없어 최근 21봉도 일봉입니다. ${d.digest?'증거 SHA-256: '+E(d.digest):'원시 OHLCV 증거 사용 안 함'}. 수집: ${E(d.src.collected_at||ctx?.data?.charts?.generated_at||'미확인')}.</p></details></section></div>`;
}
function handle(event){const el=event.target?.closest?.('[data-rcc-span]');if(!el)return false;const v=Number(el.dataset.rccSpan);if(![21,63,126].includes(v))return false;span=v;return true;}
window.RadarCohesiveChart={render,handle};
})();
