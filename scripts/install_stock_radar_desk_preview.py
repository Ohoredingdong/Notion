"""Upgrade only the isolated clickable design preview; preserve demo state/routes."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'stock-radar-ui-preview.html'
s=p.read_text()
css=(ROOT/'assets/stock-radar-desk.css').read_text()
js=(ROOT/'assets/stock-radar-desk-home.js').read_text()
# Idempotent generated slots; strict anchors stop accidental production edits.
start='/* DESK_HOME_START */';end='/* DESK_HOME_END */'
if start in s:
    a=s.index(start); b=s.index(end,a)+len(end);s=s[:a]+start+'\n'+js+'\n'+end+s[b:]
else:
    a=s.index('function home(){');b=s.index('\nfunction discover()',a)
    s=s[:a]+start+'\n'+js+'\n'+end+s[b:]
style_start='/* DESK_STYLE_START */';style_end='/* DESK_STYLE_END */'
if style_start in s:
    a=s.index(style_start);b=s.index(style_end,a)+len(style_end);s=s[:a]+style_start+'\n'+css+'\n'+style_end+s[b:]
else:
    assert s.count('</style>')==1
    s=s.replace('</style>',style_start+'\n'+css+'\n'+style_end+'\n</style>',1)
s=s.replace('globeCleanup();parse();nav();','parse();nav();')
s=s.replace("if(route==='home')mountGlobe();",'')
s=s.replace(',globeCleanup=()=>{}','')
a=s.find('// Stylized geographic silhouettes')
if a>=0:
    b=s.index("window.addEventListener('popstate'",a)
    s=s[:a]+s[b:]
# Keep existing localStorage key, watch list and all non-home screens untouched.
s=s.replace("['forecast','예측','globe']","['forecast','예측','chart']")
s=s.replace("${icon('globe')}","${icon('chart')}")
s=s.replace('투자 레이더 · Globe UI','투자 레이더 · Investment Desk')
s=s.replace('투자 레이더 Globe 시안','투자 레이더 데스크 시안')
s=s.replace('YOUR WORLD, IN FOCUS.','YOUR INVESTMENT DESK.')
s=s.replace('GLOBE CONCEPT 01 · 차트는 디자인 예시입니다. 관심·조건은 이 브라우저의 시안에만 저장됩니다.','DESK CONCEPT 02 · 차트는 디자인 예시입니다. 관심·조건은 이 브라우저에만 저장되며 실제 주문·알림은 없습니다.')
old="if(el.dataset.homemarket){market=el.dataset.homemarket;render();return}"
new="if(el.dataset.homemarket){market=el.dataset.homemarket;deskMarket=market==='미국'?'나스닥':'코스피';render();return}"
s=s.replace(old,new)
if 'if(el.dataset.deskIndex)' not in s:
    anchor="if(el.dataset.market){filter=el.dataset.market;query='';go('discover');return}"
    assert s.count(anchor)==1
    s=s.replace(anchor,anchor+"if(el.dataset.deskIndex){deskMarket=el.dataset.deskIndex;render();return}if(el.dataset.deskRange){deskRange=el.dataset.deskRange;render();return}")
assert 'function mountGlobe' not in s and 'id="globe"' not in s
assert 'fetch(' not in s and 'type="password"' not in s
assert s.count('function home()')==1 and s.count('let deskMarket=')==1
assert 'radar_globe_preview_v1' in s
p.write_text(s)
script=re.search(r'<script>(.*?)</script>',s,re.S).group(1)
Path('/tmp/radar-desk-preview.js').write_text(script)
print('DESK_PREVIEW_INSTALLED; existing routes and localStorage preserved; production data untouched')
