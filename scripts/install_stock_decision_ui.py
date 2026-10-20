"""Idempotent UI deployment. Never touches the separate training widget."""
from pathlib import Path
import re
page=Path('stock-value-radar.html');s=page.read_text(encoding='utf-8')
for marker in ('id="candidateSection"','id="view-analysis"','id="rows"'):
 if marker not in s:raise RuntimeError('Cannot safely install: '+marker)
s=re.sub(r'<script\s+src=[\"\']\./assets/stock-value-radar-v6\.js[\"\'][^>]*>\s*</script>','',s)
tag='<script src="./assets/stock-decision-v7.js?v=7.1" defer></script>'
if tag not in s:s=s.replace('</body>',tag+'\n</body>',1)
if 'name="robots"' not in s:s=s.replace('</head>','<meta name="robots" content="noindex,nofollow">\n</head>',1)
assert s.count(tag)==1
page.write_text(s,encoding='utf-8')
js=Path('assets/stock-decision-v7.js');code=js.read_text(encoding='utf-8')
# GITHUB_TOKEN commits do not always trigger a branch-based Pages rebuild.
# Read the current JSON directly from the public repository rather than a stale Pages copy.
code=code.replace("fetch('./stock-decision-data.json?t='+Date.now()", "fetch('https://raw.githubusercontent.com/Ohoredingdong/Notion/main/stock-decision-data.json?t='+Date.now()")
js.write_text(code,encoding='utf-8')
print('v7 decision view installed; existing training/audit data left unchanged')
