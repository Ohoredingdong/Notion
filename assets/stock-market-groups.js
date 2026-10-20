/* Listing / index membership only. Does not modify any financial or decision field. */
(()=>{'use strict';
const labels={ALL:'전체',KR:'한국 전체',US:'미국 전체',KOSPI:'코스피',KOSDAQ:'코스닥',NASDAQ:'나스닥',DOW:'다우',NYSE:'뉴욕증권거래소',OTHER:'기타 상장시장',UNKNOWN:'상장시장 미확인'};
const codes={KSC:'KOSPI',KOE:'KOSDAQ',NMS:'NASDAQ',NGM:'NASDAQ',NCM:'NASDAQ',NYQ:'NYSE',ASE:'OTHER',PCX:'OTHER',BTS:'OTHER'};
let snapshot=null,loading=null,error=null,deep=[];
const key=r=>r.source_symbol||r.symbol;
const isFresh=()=>{const t=Date.parse(snapshot?.generated_at||'');const age=(Date.now()-t)/36e5;return Number.isFinite(age)&&age>=-1&&age<=(snapshot?.max_age_hours||36)};
function get(r){let found=isFresh()?snapshot?.members?.[key(r)]:null;if(!found&&isFresh()&&r.market==='KR'){const aliases=[snapshot?.members?.[r.symbol+'.KS'],snapshot?.members?.[r.symbol+'.KQ']].filter(Boolean);if(aliases.length===1)found=aliases[0]}
let venue=found?.venue||codes[r.exchange]||'UNKNOWN';const s=key(r)||'';
if(r.market==='KR'&&!found)venue=s.endsWith('.KQ')?'KOSDAQ':s.endsWith('.KS')?'KOSPI':venue;
if(r.market==='US'&&['KOSPI','KOSDAQ'].includes(venue))venue='UNKNOWN';
if(!['KOSPI','KOSDAQ','NASDAQ','NYSE','UNKNOWN'].includes(venue))venue='OTHER';
const dow=r.market==='US'&&isFresh()&&snapshot?.dow?.status==='current'?snapshot.dow.symbols.includes(s):r.market==='KR'?false:null;
return {venue,dow};}
function match(r,selection){if(!selection||selection==='ALL')return true;if(selection==='KR'||selection==='US')return r.market===selection;const x=get(r);return selection==='DOW'?x.dow===true:x.venue===selection;}
function label(r){const x=get(r);return (labels[x.venue]||'상장시장 미확인')+(x.dow===true?' · 다우':'');}
function fill(select,rows){if(!select)return;const choice=select.value||'ALL';select.replaceChildren();
for(const value of ['ALL','KOSPI','KOSDAQ','NASDAQ','DOW','NYSE','KR','US','OTHER','UNKNOWN']){const option=document.createElement('option');option.value=value;const n=rows.filter(r=>match(r,value)).length;option.textContent=labels[value]+(value==='DOW'&&(!isFresh()||snapshot?.dow?.status!=='current')?' · 확인 대기':' · '+n);select.append(option)}
select.value=Object.hasOwn(labels,choice)?choice:'ALL';select.setAttribute('aria-label','상장시장 또는 다우 지수 선택');}
function populate(rows){deep=rows||[];fill(document.getElementById('market'),deep);const host=document.getElementById('marketGroupsBar');if(!host)return;host.replaceChildren();const selected=document.getElementById('market')?.value||'ALL';
for(const value of ['ALL','KOSPI','KOSDAQ','NASDAQ','DOW','NYSE']){const b=document.createElement('button');b.type='button';b.dataset.listing=value;b.className=selected===value?'active':'';b.setAttribute('aria-pressed',String(selected===value));const unknown=value==='DOW'&&(!isFresh()||snapshot?.dow?.status!=='current');b.textContent=(value==='NYSE'?'NYSE':labels[value])+' '+(unknown?'…':deep.filter(r=>match(r,value)).length);b.onclick=()=>{const select=document.getElementById('market');select.value=value;select.dispatchEvent(new Event('change',{bubbles:true}));};host.append(b)}
const note=document.getElementById('marketGroupsNote');if(note)note.textContent='다우는 상장시장이 아닌 지수라 나스닥·NYSE와 중복될 수 있습니다. 종목 수는 현재 정밀분석 목록 기준입니다.'+(isFresh()&&snapshot?.dow?.status==='current'?' 다우 분류: '+snapshot.dow.as_of+' DIA 공식 보유종목 기준.':' 다우 명단 '+(error?'조회 실패':'확인 대기')+' — 임의 분류하지 않습니다.');}
async function load(){if(loading)return loading;loading=(async()=>{try{const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),18000);try{const r=await fetch('https://raw.githubusercontent.com/Ohoredingdong/Notion/main/stock-market-groups.json?t='+Date.now(),{cache:'no-store',signal:controller.signal});if(!r.ok)throw Error('HTTP '+r.status);const j=await r.json();if(!j.members||!Array.isArray(j.dow?.symbols))throw Error('분류자료 형식 오류');snapshot=j;error=null;}finally{clearTimeout(timer)}}catch(e){snapshot=null;error=e.message}finally{loading=null;document.dispatchEvent(new CustomEvent('radar:markets-ready'));}})();return loading;}
window.RadarMarkets={get,match,label,populate,fill,load,labels,status:()=>({fresh:isFresh(),error,dow:snapshot?.dow,sources:snapshot?.sources})};
const style=document.createElement('style');style.textContent='.market-groups{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 9px}.market-groups button{border:1px solid var(--line);border-radius:11px;background:var(--card);color:var(--muted);padding:9px 14px;font-size:12px;font-weight:680}.market-groups button.active{background:var(--blue-soft);color:var(--blue);border-color:var(--blue)}.market-groups-note{font-size:10px;line-height:1.8;color:var(--muted);margin:0 0 20px}.listing-label{font-size:10px;font-weight:650;color:var(--blue);display:block;margin:5px 0 3px}@media(max-width:640px){.market-groups{gap:6px}.market-groups button{padding:8px 11px;font-size:11px}}';document.head.append(style);
load();setInterval(load,30*60*1000);
})();
