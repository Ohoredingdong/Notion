"""Install the complete macro-to-company reading path without altering values."""
from pathlib import Path
import hashlib,re,subprocess
root=Path('.')
html_path=root/'assets/stock-radar-v8.html';html=html_path.read_text(encoding='utf-8')
for filename in ('stock-decision-guide.css','stock-reading-depth.css'):
 code=(root/'assets'/filename).read_text(encoding='utf-8');token=hashlib.sha256(code.encode()).hexdigest()[:12]
 html=re.sub(r'<link rel="stylesheet" href="\./assets/'+re.escape(filename)+r'[^\"]*">\s*','',html)
 anchor=re.search(r'<link rel="stylesheet" href="\./assets/stock-radar-v8\.css[^\"]*">',html)
 if not anchor:raise RuntimeError('Main stylesheet tag not found')
 html=html[:anchor.end()]+'\n<link rel="stylesheet" href="./assets/'+filename+'?v='+token+'">'+html[anchor.end():]
for filename in ('stock-decision-guide.js','stock-report-reading-guide.js'):
 code=(root/'assets'/filename).read_text(encoding='utf-8');token=hashlib.sha256(code.encode()).hexdigest()[:12]
 html=re.sub(r'<script src="\./assets/'+re.escape(filename)+r'[^\"]*" defer></script>\s*','',html)
 html=html.replace('</head>','<script src="./assets/'+filename+'?v='+token+'" defer></script>\n</head>')
 subprocess.run(['node','--check',str(root/'assets'/filename)],check=True)
html_path.write_text(html,encoding='utf-8')
print('Complete reading path installed: rates, business, 3-year financials, cash, debt, valuation and expectations.')
