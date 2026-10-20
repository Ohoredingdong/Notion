"""Install one v8 page. Preserve collectors, raw figures and training files.

Legacy workflows may still collect data, but their UI installers must not append
old overlays to this standalone view. Guards are idempotent and scoped to v8.
"""
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import ast,hashlib,json,re

class IDs(HTMLParser):
 def __init__(self):super().__init__();self.ids=[]
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k=='id':self.ids.append(v)

root=Path('.')
page=root/'stock-value-radar.html'
text=(root/'assets/stock-radar-v8.html').read_text(encoding='utf-8')
css=(root/'assets/stock-radar-v8.css').read_text(encoding='utf-8')
js=(root/'assets/stock-radar-v8.js').read_text(encoding='utf-8')
assert 'data-radar-version="8"' in text
parser=IDs();parser.feed(text)
assert all(n==1 for n in Counter(parser.ids).values()), 'Duplicate DOM id'
for required in ('liveStatus','view-discover','view-detail','view-system','cards','detailBody','companySelect','systemBody'):
 assert required in parser.ids, required
assert all(x not in text+js for x in ('v6Save','v6Reason','v6Condition','v6Export','v6DecisionPanel'))
assert 'stock-paper-investing.html' in text, 'Keep separate training link'
assert 'stock-opportunity-data.json' in js
# Bust asset caches by the content hash instead of claiming a refresh changed old bytes.
for filename,body in [('css',css),('js',js)]:
 digest=hashlib.sha256(body.encode()).hexdigest()[:12]
 text=text.replace('stock-radar-v8.'+filename+'?v=8.0','stock-radar-v8.'+filename+'?v='+digest)

marker='# RADAR_V8_LEGACY_UI_GUARD'
guard='''# RADAR_V8_LEGACY_UI_GUARD
from pathlib import Path as _V8Path
if 'data-radar-version="8"' in _V8Path('stock-value-radar.html').read_text(encoding='utf-8'):
    print('Standalone v8 owns the UI; legacy data collection remains unchanged.')
    raise SystemExit(0)

'''
for name in ('scripts/install_stock_decision_ui.py','scripts/install_stock_audit_ui.py'):
 path=root/name;code=path.read_text(encoding='utf-8')
 if marker not in code:
  tree=ast.parse(code);lines=code.splitlines(keepends=True);at=0
  if tree.body and isinstance(tree.body[0],ast.Expr) and isinstance(tree.body[0].value,ast.Constant) and isinstance(tree.body[0].value.value,str):at=tree.body[0].end_lineno
  for node in tree.body:
   if isinstance(node,ast.ImportFrom) and node.module=='__future__':at=max(at,node.end_lineno)
  code=''.join(lines[:at])+'\n'+guard+''.join(lines[at:])
  compile(code,name,'exec');path.write_text(code,encoding='utf-8')
# Replace only the designated widget page. Training, financial values and key files are not modified.
page.write_text(text,encoding='utf-8')
print('v8 installed;',len(parser.ids),'unique DOM IDs;',len(text),'HTML characters; training unchanged')
