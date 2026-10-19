"""Install the tested audit view without replacing unrelated widget functions."""
from pathlib import Path
import re

page=Path('stock-value-radar.html')
text=page.read_text(encoding='utf-8')
for marker in ('id="researchDetails"','id="detail"','id="systemBanner"'):
 if marker not in text:raise RuntimeError('Widget structure changed: '+marker)
asset=Path('assets/stock-official-audit-v5.js').read_text(encoding='utf-8')
# Preserve insignificant numeric discrepancies, without mislabelling them as an outage.
asset=asset.replace("const states={match:","const states={minor_difference:'미세 금액 차이',match:")
asset=asset.replace("new Set(['mismatch',", "new Set(['minor_difference','mismatch',")
# Compile the UI into the existing document to avoid stale third-party embed asset caches.
compiled='<script id="official-audit-v5">\n'+asset+'\n</script>'
text=re.sub(r'<script id="official-audit-v5">[\s\S]*?</script>','',text)
text=text.replace('<script src="./assets/stock-official-audit-v5.js"></script>','')
if '</body>' not in text:raise RuntimeError('Document body missing')
text=text.replace('</body>',compiled+'\n</body>',1)
text=text.replace('const official=(financial.includes("SEC")||financial.includes("OpenDART"))&&!financial.includes("Yahoo");','const official=false; // v5: independent actual source audit required')
page.write_text(text,encoding='utf-8')

builder=Path('scripts/build-stock-investment-intelligence.py')
code=builder.read_text(encoding='utf-8')
start=code.find('def verify_official_release(row, official_sources):')
end=code.find('def thesis(row):',start)
if start<0 or end<start:raise RuntimeError('Legacy verification boundary changed')
replacement='''def verify_official_release(row, official_sources):
    """Old hand-entered reference values are not a live verification.

    Read stock-official-audit.json for independent re-fetched source comparisons.
    """
    return None

'''
code=code[:start]+replacement+code[end:]
compile(code,str(builder),'exec')
builder.write_text(code,encoding='utf-8')
assert text.count('id="official-audit-v5"')==1
print('Audit UI installed once. Old static figures no longer establish verification.')
