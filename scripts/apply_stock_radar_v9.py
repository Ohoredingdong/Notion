"""Idempotent v9 enhancement of the existing v8 page; training is untouched."""
from pathlib import Path
import hashlib

css_path=Path('assets/stock-radar-v8.css');css=css_path.read_text()
# Keep colored accents and text contrast; lighten only large neutral surfaces.
css=css.replace('--bg:#f2f3f8','--bg:#f9fafb').replace('--soft:#f6f7fb','--soft:#fbfbfc')
marker='/* RADAR_V9_FIRST_CHOICES */'
if marker not in css:
 css+='''
/* RADAR_V9_FIRST_CHOICES */
#todayBrief{background:var(--card);border:1px solid var(--line);border-radius:19px;padding:21px;margin:0 0 20px}.brief-heading{display:flex;justify-content:space-between;align-items:center;gap:14px}.brief-heading h3{font-size:19px;letter-spacing:-.035em;margin-top:3px}.brief-heading>span{font-size:10px;color:var(--muted)}.brief-explain{font-size:12px;color:var(--muted);line-height:1.85;margin:9px 0 17px}.brief-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.brief-card{background:var(--soft);border:1px solid var(--line);border-radius:13px;padding:16px;min-width:0}.brief-card.ready{border-color:var(--green)}.brief-order{color:var(--muted);font-size:10px}.brief-name{display:block;border:0;background:transparent;padding:0;margin:7px 0 6px;font-size:17px;font-weight:750;letter-spacing:-.025em;text-align:left;overflow-wrap:anywhere}.brief-badge{font-size:10px;color:var(--blue);background:var(--blue-soft);border-radius:6px;padding:3px 6px;display:inline-block}.brief-card.ready .brief-badge{color:var(--green);background:var(--green-soft)}.brief-facts{font-size:11px;margin-top:12px;line-height:1.8;color:var(--muted)}.brief-facts p{margin:5px 0}.brief-price{padding-top:11px;border-top:1px solid var(--line);margin-top:12px}.brief-price small{display:block;font-size:10px;color:var(--muted)}.brief-price b{display:block;font-size:21px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}.brief-price span{display:block;font-size:11px;color:var(--blue);margin-top:4px}.brief-caution{font-size:10px;color:var(--muted);line-height:1.75;margin-top:9px}.brief-card .text-button{font-size:11px;margin-top:10px}.brief-wait{display:flex;gap:10px;align-items:center;flex-wrap:wrap;border-top:1px solid var(--line);padding-top:15px;margin-top:17px;font-size:11px}.brief-wait>b{margin-right:3px}.brief-wait button{display:block;text-align:left;border:1px solid var(--line);background:var(--card);border-radius:10px;padding:9px 12px;font-size:11px}.brief-wait strong{color:var(--amber);margin-left:6px}.brief-wait small{display:block;font-size:10px;color:var(--muted)}.brief-foot{margin:13px 0 0;color:var(--muted);font-size:10px;line-height:1.8}.brief-warning{background:var(--amber-soft);color:var(--amber);padding:12px;border-radius:10px;font-size:12px}.brief-open{border:1px solid var(--line);border-radius:10px;background:var(--card);padding:12px;font-size:13px;margin:6px}.directory-controls{display:flex;gap:8px;margin:12px 0}.directory-controls input{flex:1;min-width:0}.directory-controls input,.directory-controls select{padding:9px;border:1px solid var(--line);background:var(--card);border-radius:9px;color:var(--ink);font-size:12px}.directory-symbol{display:block;color:var(--muted);font-size:10px}.directory-count{font-size:11px;color:var(--muted);margin:7px 0}.directory-note{font-size:11px;line-height:1.8;color:var(--muted);margin-bottom:10px}#wideDirectory table{table-layout:fixed}#wideDirectory th:first-child{width:42%}#wideDirectory td{overflow-wrap:anywhere}#wideDirectory .text-button{font-size:11px}
@media(max-width:760px){.brief-grid{grid-template-columns:1fr}.brief-heading{align-items:flex-start;flex-direction:column;gap:5px}.brief-card{padding:15px}.brief-price{display:grid;grid-template-columns:1fr 1fr;gap:3px 9px}.brief-price small{grid-column:1/-1}.brief-price span{align-self:center}.brief-wait{align-items:stretch;flex-direction:column}.brief-wait button{width:100%}.brief-wait>b{margin-bottom:3px}#todayBrief{padding:17px}.brief-heading h3{font-size:18px}}
'''
css_path.write_text(css)
html_path=Path('assets/stock-radar-v8.html');html=html_path.read_text()
if 'id="todayBrief"' not in html:
 anchor=' <div class="guide" id="actionGuide">'
 if anchor not in html:raise RuntimeError('Guide anchor changed')
 html=html.replace(anchor,' <section id="todayBrief" aria-label="먼저 비교할 기업"><p class="brief-explain">후보별 투자 관점을 요약하는 중입니다.</p></section>\n'+anchor)
if 'id="wideDirectory"' not in html:
 anchor=' <button type="button" class="more" id="more" hidden>더 보기</button>'
 if anchor not in html:raise RuntimeError('More anchor changed')
 directory='''
 <details id="wideDirectory"><summary id="directoryTitle">더 넓게 찾기</summary><div class="details-inner"><p class="directory-note" id="directoryNote">기본 탐색과 정밀 분석은 구분합니다. 이 목록 자체는 매수 추천이 아닙니다.</p><div class="directory-controls"><input id="directorySearch" type="search" placeholder="넓은 목록에서 기업 검색" aria-label="전체 탐색 기업 검색"><select id="directoryMarket" aria-label="탐색 시장"><option value="ALL">전체 시장</option><option value="KR">한국</option><option value="US">미국</option></select></div><div class="directory-count" id="directoryCount"></div><div id="directoryRows">목록 확인 중…</div><button class="more" id="directoryMore" type="button" hidden>40개 더 보기</button></div></details>
'''
 html=html.replace(anchor,anchor+directory)
asset=Path('assets/stock-radar-v9.js').read_text();token=hashlib.sha256(asset.encode()).hexdigest()[:12]
import re
html=re.sub(r'<script src="\./assets/stock-radar-v9\.js[^\"]*" defer></script>\s*','',html)
html=html.replace('</head>','<script src="./assets/stock-radar-v9.js?v='+token+'" defer></script>\n</head>')
html_path.write_text(html)
js_path=Path('assets/stock-radar-v8.js');js=js_path.read_text()
if 'radar:v9-data' not in js:
 anchor='function renderCards(){summary();'
 if anchor not in js:raise RuntimeError('renderCards anchor changed')
 js=js.replace(anchor,anchor+"document.dispatchEvent(new CustomEvent('radar:v9-data',{detail:{data,mode,paused:paused()}}));",1)
# Automatically discovered additions belong in the expanded filter too.
js=js.replace("r.cohort==='확장'", "r.cohort!=='기존'")
js=js.replace("'한국·미국 고정 후보'", "'한국·미국 정밀 분석'")
js=js.replace("'고정 후보 '+(c.tracked||0)+'개", "'정밀 분석 '+(c.tracked||0)+'개")
js=js.replace("실적·가격 후보 / 공식 대조 전", "실적·가격 후보 / 공식 대조 전")
js_path.write_text(js)
print('v9 lighter gray, explicit shortlist and broad directory installed; no training or risk-gate changes')
