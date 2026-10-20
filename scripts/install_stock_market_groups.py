"""Idempotent market-filter integration; no financial/decision value changes."""
from pathlib import Path
import hashlib,re
p=Path('assets/stock-radar-v8.js');s=p.read_text(encoding='utf-8')
if '// MARKET_GROUP_FILTERS_V1' not in s:
 if "(market==='ALL'||r.market===market)" not in s:raise RuntimeError('Main market filter anchor changed')
 s=s.replace("(market==='ALL'||r.market===market)","window.RadarMarkets.match(r,market)")
 s=s.replace('function renderCards(){summary();','function renderCards(){window.RadarMarkets.populate(rows());summary();',1)
 s=s.replace('detail:{data,mode,paused:paused()}','detail:{data,mode,paused:paused(),market:$(\'#market\').value}')
 s=s.replace("esc(r.symbol)+' · '+esc(r.sector)","esc(r.symbol)+' · '+esc(window.RadarMarkets.label(r))+' · '+esc(r.sector)")
 s=s.replace("esc(r.symbol)+' · 수집 '","esc(r.symbol)+' · '+esc(window.RadarMarkets.label(r))+' · 수집 '")
 s=s.replace("esc(r.name)+' · '+esc(r.symbol)+'</option>'", "esc(r.name)+' · '+esc(r.symbol)+' ['+esc(window.RadarMarkets.label(r))+']</option>'")
 anchor='load();setInterval(load,5*60*1000);'
 if anchor not in s:raise RuntimeError('Refresh anchor changed')
 s=s.replace(anchor,"// MARKET_GROUP_FILTERS_V1\ndocument.addEventListener('radar:markets-ready',()=>{if(data){renderCards();detail();for(const o of $('#companySelect').options){const r=rows().find(x=>x.symbol===o.value);if(r)o.textContent=r.name+' · '+r.symbol+' ['+window.RadarMarkets.label(r)+']'}}});\n"+anchor)
 p.write_text(s,encoding='utf-8')
p=Path('assets/stock-radar-v9.js');s=p.read_text(encoding='utf-8')
if '// MARKET_GROUP_BRIEF_V1' not in s:
 s=s.replace("mode='long',paused=true;", "mode='long',paused=true,selectedMarket='ALL';")
 helper="""// MARKET_GROUP_BRIEF_V1
function filteredBrief(){
 const original=current?.decision_brief;if(!original||selectedMarket==='ALL')return original;
 const pool=(current.companies||[]).filter(r=>window.RadarMarkets.match(r,selectedMarket)&&r.status==='current'&&r.period_integrity?.status==='ok'&&r.model_integrity?.status!=='needs_sector_model');
 function choose(states,n){const rs=pool.filter(r=>states.includes(r.assessment?.state)).sort((a,b)=>((a.assessment.state!=='ready')-(b.assessment.state!=='ready'))||((b.priority?.display_score??b.priority?.score??0)-(a.priority?.display_score??a.priority?.score??0)));const picked=[],seen=new Set();for(const r of rs){if(seen.has(r.sector))continue;picked.push(r);seen.add(r.sector);if(picked.length===n)break}for(const r of rs){if(picked.length===n)break;if(!picked.includes(r))picked.push(r)}return picked.map(r=>({symbol:r.symbol,source_symbol:r.source_symbol,name:r.name,market:r.market,sector:r.sector,currency:r.currency,state:r.assessment.state,price:r.price,price_session:r.price_session,price_condition:r.assessment.price_condition,why:['다음 FY 예상 EPS 성장 '+(number(r.forecasts?.eps_growth_next_fy_pct)?fmt(r.forecasts.eps_growth_next_fy_pct)+'%':'미확인'),'같은 FY EPS 30일 변화 '+(number(r.forecasts?.eps_revision30_pct)?fmt(r.forecasts.eps_revision30_pct)+'%':'미확인')]}));}
 const now=choose(['ready','verify'],3),wait=choose(['price'],2),name=window.RadarMarkets.labels[selectedMarket]||selectedMarket;
 return {...original,now,wait,summary:name+' 분류 안에서 기존 판단 기준을 통과한 후보입니다. '+(now.length?'공식 대조 여부와 남은 조건을 확인하세요.':'현재 가격·실적 우선 후보가 없습니다. 가격 대기 후보가 있으면 아래에 표시합니다.')};
}
"""
 if 'function brief(){' not in s:raise RuntimeError('Brief anchor changed')
 s=s.replace('function brief(){',helper+'function brief(){',1)
 s=s.replace('const b=current?.decision_brief;', 'const b=filteredBrief();',1)
 s=s.replace("r.short?.state==='conditional'&&r.period_integrity?.status==='ok'", "r.short?.state==='conditional'&&r.period_integrity?.status==='ok'&&window.RadarMarkets.match(r,selectedMarket)")
 s=s.replace("esc(r.sector)+'</div><button class=", "esc(r.sector)+' · '+esc(window.RadarMarkets.label(r))+'</div><button class=")
 s=s.replace("(market==='ALL'||r.market===market)","window.RadarMarkets.match(r,market)")
 s=s.replace("const q=$('#directorySearch').value", "window.RadarMarkets.fill($('#directoryMarket'),scan.companies||[]);const q=$('#directorySearch').value")
 s=s.replace("esc(r.market)+'<br>'", "esc(window.RadarMarkets.label(r))+'<br>'")
 s=s.replace('current=e.detail.data;mode=e.detail.mode;',"current=e.detail.data;mode=e.detail.mode;selectedMarket=e.detail.market||'ALL';")
 s=s.replace("$('#wideDirectory')?.addEventListener", "document.addEventListener('radar:markets-ready',()=>{brief();if(scan)directory()});\n$('#wideDirectory')?.addEventListener",1)
 p.write_text(s,encoding='utf-8')
p=Path('assets/stock-radar-v8.html');html=p.read_text(encoding='utf-8')
if 'id="marketGroupsBar"' not in html:
 anchor=' <div class="summary-grid" id="summary">'
 if anchor not in html:raise RuntimeError('Summary anchor changed')
 html=html.replace(anchor,' <div class="market-groups" id="marketGroupsBar" role="group" aria-label="코스피 코스닥 나스닥 다우 분류"></div><p class="market-groups-note" id="marketGroupsNote">상장시장과 다우 지수 편입 여부를 구분해서 확인합니다.</p>\n'+anchor,1)
asset=Path('assets/stock-market-groups.js').read_text(encoding='utf-8');token=hashlib.sha256(asset.encode()).hexdigest()[:12]
html=re.sub(r'<script src="\./assets/stock-market-groups\.js[^\"]*" defer></script>\s*','',html)
tag='<script src="./assets/stock-market-groups.js?v='+token+'" defer></script>\n'
anchor='<script src="./assets/stock-radar-v8.js'
if anchor not in html:raise RuntimeError('Main script anchor changed')
html=html.replace(anchor,tag+anchor,1)
p.write_text(html,encoding='utf-8')
print('Market filters integrated in overview, shortlist, details and wide directory; risk rules unchanged.')
