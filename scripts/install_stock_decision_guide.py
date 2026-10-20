"""Install the macro-to-company decision guide into the standalone radar page."""
from pathlib import Path
import hashlib,re,subprocess
root=Path('.')
html_path=root/'assets/stock-radar-v8.html';html=html_path.read_text(encoding='utf-8')
css=(root/'assets/stock-decision-guide.css').read_text(encoding='utf-8');js=(root/'assets/stock-decision-guide.js').read_text(encoding='utf-8');reading=(root/'assets/stock-report-reading-guide.js').read_text(encoding='utf-8')
css_hash=hashlib.sha256(css.encode()).hexdigest()[:12];js_hash=hashlib.sha256(js.encode()).hexdigest()[:12];reading_hash=hashlib.sha256(reading.encode()).hexdigest()[:12]
html=re.sub(r'<link rel="stylesheet" href="\./assets/stock-decision-guide\.css[^\"]*">\s*','',html)
html=re.sub(r'<script src="\./assets/stock-decision-guide\.js[^\"]*" defer></script>\s*','',html)
html=re.sub(r'<script src="\./assets/stock-report-reading-guide\.js[^\"]*" defer></script>\s*','',html)
main_css=re.search(r'<link rel="stylesheet" href="\./assets/stock-radar-v8\.css[^\"]*">',html)
if not main_css:raise RuntimeError('main css tag not found')
html=html[:main_css.end()]+'\n<link rel="stylesheet" href="./assets/stock-decision-guide.css?v='+css_hash+'">'+html[main_css.end():]
html=html.replace('</head>','<script src="./assets/stock-decision-guide.js?v='+js_hash+'" defer></script>\n<script src="./assets/stock-report-reading-guide.js?v='+reading_hash+'" defer></script>\n</head>')
html_path.write_text(html,encoding='utf-8')
for name in ('stock-decision-guide.js','stock-report-reading-guide.js'):
 subprocess.run(['node','--check',str(root/'assets'/name)],check=True)
print('Decision guide and filing-reading checklist installed with current asset hashes')
