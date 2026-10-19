"""Install v5 UI without replacing unrelated widget logic or data collectors."""
from pathlib import Path
import re

page=Path('stock-value-radar.html')
text=page.read_text(encoding='utf-8')
for marker in ('id="researchDetails"','id="detail"','id="systemBanner"'):
 if marker not in text:raise RuntimeError('Widget structure changed: '+marker)
tag='<script src="./assets/stock-official-audit-v5.js"></script>'
if tag not in text:
 if '</body>' not in text:raise RuntimeError('Cannot find document body end')
 text=text.replace('</body>',tag+'\n</body>',1)
# Data collection is not a primary-source cross-check. The new UI computes field
# verification from stock-official-audit.json; do not credit a source label alone.
text=text.replace('const official=(financial.includes("SEC")||financial.includes("OpenDART"))&&!financial.includes("Yahoo");','const official=false; // v5: only the independent source audit can establish a match')
page.write_text(text,encoding='utf-8')

builder=Path('scripts/build-stock-investment-intelligence.py')
code=builder.read_text(encoding='utf-8')
start=code.find('def verify_official_release(row, official_sources):')
end=code.find('def thesis(row):',start)
if start<0 or end<start:raise RuntimeError('Cannot locate legacy static verification function safely')
replacement='''def verify_official_release(row, official_sources):
    """Legacy static reference figures are not current automatic verification.

    The independently fetched result is stock-official-audit.json. This function
    deliberately returns no proof rather than reusing hand-entered figures.
    """
    return None

'''
code=code[:start]+replacement+code[end:]
compile(code,str(builder),'exec')
builder.write_text(code,encoding='utf-8')
assert page.read_text().count(tag)==1
print('Installed official audit UI once; retired static figure comparisons.')
