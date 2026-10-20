"""Integrate strict green in existing renderers. No financial/training edits.
The companion is explicitly called, not another mutation-observer overlay.
"""
from pathlib import Path
import hashlib,re,subprocess
p=Path('assets/stock-investment-cases.js');s=p.read_text()
def replace(a,b):
 global s
 if b in s:return
 if s.count(a)!=1:raise RuntimeError('UI anchor changed: '+a[:100])
 s=s.replace(a,b,1)
replace('?c:null}',"?(window.StockGreenReview?window.StockGreenReview.normalise(c,r,d):{...c,state:c.state==='attractive'?'conditional':c.state,strict_ui_blocked:true}):null}")
replace('const okay=fresh(d),cs=okay?snapshot.counts:{};','const okay=fresh(d),cs={};if(okay)for(const row of d.companies||[]){const opinion=get(row,d);if(opinion)cs[opinion.state]=(cs[opinion.state]||0)+1;}')
s=s.replace("okay?cs.attractive:'—'","okay?(cs.attractive||0):'—'").replace("okay?cs.price_wait:'—'","okay?(cs.price_wait||0):'—'").replace("okay?cs.conditional:'—'","okay?(cs.conditional||0):'—'")
s=s.replace("attractive:'지금 가격은 살 만한 편이에요'","attractive:'핵심 검증 통과 · 조건부 투자 후보'")
s=s.replace("conditional:'괜찮아 보이지만, 숫자 확인이 남았어요'","conditional:'좋은 점은 있지만 핵심 검증이 남았어요'")
s=s.replace("avoid:'지금은 조심하는 편이 좋아요'","avoid:'위험 신호의 원인을 먼저 확인해요'")
s=s.replace("['green','지금 살 만한 편'","['green','엄격 검증 통과'").replace("'실적·가격 기준 통과'","'12개 조건 통과 · 수익 보장 아님'")
s=s.replace('선택한 시장에서 살 만한 편 ','선택한 시장에서 엄격 검증 통과 ')
s=s.replace('초록은 이 도구의 실적·가격 기준을 통과한 종목이에요. 파랑은 공식 숫자 확인이 남아 있어요. 수익이 확실하다는 뜻은 아니에요.','초록은 현금·부채·사업위험·독립 가격평가까지 명시된 검증을 통과한 후보예요. 파랑은 핵심 검증이 남아 있어요. 어떤 색도 수익을 보장하지 않아요.')
s=s.replace("'[data-filter=\"ready\"]':'지금 살 만한 편'","'[data-filter=\"ready\"]':'엄격 검증 통과'")
replace('function explainDecision(c){','function explainDecision(c){if(window.StockGreenReview)return window.StockGreenReview.description(c);')
replace('function priceGuide(r,c,compact=false){','function priceGuide(r,c,compact=false){if(window.StockGreenReview)return window.StockGreenReview.prices(r,c,compact);')
replace("+'</p><h4>가격 3개를 따로 보세요</h4>'","+'</p>'+(window.StockGreenReview?window.StockGreenReview.panel(c,r):'')+'<h4>현재 주가·전문가 예상·검증용 가격을 구분해요</h4>'")
s=s.replace('어떤 기준을 통과했나요?','기존 숫자 선별 기준 보기 · 엄격 실사와 별개');p.write_text(s)
p=Path('assets/stock-radar-v8.js');s=p.read_text();s=s.replace("s.state==='conditional'?'ready'","s.state==='conditional'?'verify'")
s=s.replace("?'짧게 볼 때의 조건을 통과했어요'","?'기술 조건만 통과 · 실사 검증과 별개'")
s=s.replace("['green','가격·실적 후보'","['blue','숫자 선별 후보'")
s=s.replace('초록: 명시 조건 충족 · 파랑: 가격·실적은 후보, 공식대조 전','초록: 별도 엄격 실사 통과만 · 파랑: 기술 또는 숫자 선별 조건 통과')
p.write_text(s)
p=Path('assets/stock-radar-v8.html');h=p.read_text();h=re.sub(r'<script src="\./assets/stock-green-review\.js[^\"]*" defer></script>\s*','',h)
tag=re.search(r'<script src="\./assets/stock-investment-cases\.js',h)
if not tag:tag=re.search(r'<script src="\./assets/stock-radar-v8\.js',h)
if not tag:raise RuntimeError('case/main script not found')
digest=hashlib.sha256(Path('assets/stock-green-review.js').read_bytes()).hexdigest()[:12]
h=h[:tag.start()]+'<script src="./assets/stock-green-review.js?v='+digest+'" defer></script>\n'+h[tag.start():]
h=h.replace('>지금 살 만한 편</button>','>엄격 검증 통과</button>');p.write_text(h)
for name in ('stock-green-review.js','stock-investment-cases.js','stock-radar-v8.js'):subprocess.run(['node','--check','assets/'+name],check=True)
print('Strict green integrated: no qualifying packet, no green; technical-only conditions stay blue')
