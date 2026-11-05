"""Install operating UI/template only; keep all investment decisions unchanged."""
from pathlib import Path
import hashlib,re
root=Path(__file__).resolve().parents[1]
main=(root/'stock-value-radar.html').read_text(encoding='utf-8')
if 'data-custom-radar-ui="flow-v3"' in main:
    # The canonical dashboard is independently authored. An old theme installer
    # must verify its entry points, never inject a second renderer into it.
    for required in ('stock-radar-clean-bridge.js','stock-radar-flow-v2.js'):
        if required not in main or not (root/'assets'/required).is_file():
            raise ValueError('canonical_ui_missing_'+required)
    if 'stock-radar-neutral.js' in main or 'stock-radar-v8.js' in main:
        raise ValueError('canonical_ui_contains_legacy_renderer')
    print('CANONICAL_UI_VERIFIED: legacy neutral installer has no writes')
    raise SystemExit(0)
legacy=root/'assets/stock-radar-v8.js';code=legacy.read_text()
marker='// NEUTRAL_WATCH_SYNC'
if marker not in code:
    anchor='// MARKET_GROUP_FILTERS_V1'
    assert anchor in code
    addition="\n// NEUTRAL_WATCH_SYNC\ndocument.addEventListener('radar:watchlist-changed',()=>{try{const x=JSON.parse(localStorage.getItem('radar-v8-stars')||'[]');favorites=new Set(Array.isArray(x)?x:[])}catch{favorites=new Set()}if(data)renderCards()});\n"
    code=code.replace(anchor,addition+anchor,1);legacy.write_text(code)
legacy_hash=hashlib.sha256(legacy.read_bytes()).hexdigest()[:12]
assets=['assets/stock-radar-neutral.css','assets/stock-radar-neutral.js']
tags=[]
for name in assets:
    digest=hashlib.sha256((root/name).read_bytes()).hexdigest()[:12]
    tags.append(f'<link rel="stylesheet" href="./{name}?v={digest}">' if name.endswith('.css') else f'<script src="./{name}?v={digest}" defer></script>')
for name in ['stock-value-radar.html','assets/stock-radar-v8.html']:
    p=root/name;s=p.read_text()
    for a in assets:
        s=re.sub(r'<(?:link|script)\b[^>]*(?:href|src)="\./'+re.escape(a)+r'[^\"]*"[^>]*>(?:</script>)?\s*','',s)
    if '</head>' not in s:raise ValueError('head_missing_'+name)
    s=s.replace('</head>','\n'.join(tags)+'\n</head>',1)
    s=re.sub(r'(stock-radar-v8\.js\?v=)[^\"]+',lambda m:m[1]+legacy_hash,s)
    s=s.replace('<meta name="color-scheme" content="light dark">','<meta name="color-scheme" content="light">')
    p.write_text(s)
print('NEUTRAL_UI_INSTALLED: operating page and canonical template; investment data/logic untouched')

