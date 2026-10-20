"""Integrate the case view and plain Korean labels. Keep data, gates and market filters.
Idempotent with explicit structural anchors; no financial or training file changes.
"""
from pathlib import Path
import hashlib,re,subprocess,sys
root=Path('.')
# Keep original terminology next to the plain explanation, without new signals.
subprocess.run([sys.executable,'scripts/install_stock_term_labels.py'],check=True)
def replace_once(s,a,b):
 if b in s:return s
 if s.count(a)!=1:raise RuntimeError('Changed UI anchor: '+a[:60])
 return s.replace(a,b,1)
p=root/'assets/stock-radar-v8.js';s=p.read_text()
s=replace_once(s,'function tag(r){',"function tag(r){if(mode==='long'&&!paused()&&window.StockInvestmentCase)return window.StockInvestmentCase.tag(r,data);")
s=replace_once(s,'function summary(){',"function summary(){if(mode==='long'&&!paused()&&window.StockInvestmentCase){window.StockInvestmentCase.summary(data);return;}")
s=replace_once(s,"return '<article class=\"candidate ","if(mode==='long'&&window.StockInvestmentCase)next=window.StockInvestmentCase.cardReason(r,data);\nreturn '<article class=\"candidate ")
s=s.replace('<strong>지금 할 일</strong>','<strong>왜 이런 판단인가</strong>')
for fn,nextfn,call in [('function detail(){','function system(){','if(window.StockInvestmentCase)window.StockInvestmentCase.decorate(r,data);'),('function system(){','function banner(){','if(window.StockInvestmentCase)window.StockInvestmentCase.authStatus(data);')]:
 a=s.index(fn);b=s.index(nextfn,a);part=s[a:b]
 if call not in part:
  brace=part.rfind('}');part=part[:brace]+';'+call+part[brace:];s=s[:a]+part+s[b:]
if "addEventListener('radar:cases-ready'" not in s:
 s=replace_once(s,'load();setInterval(load,5*60*1000);',"document.addEventListener('radar:cases-ready',()=>{if(data){renderCards();detail();system()}});\nload();setInterval(load,5*60*1000);")
for before,after in [
 ('가격·실적과 검증을 함께 보는 순서','다른 종목도 살펴보세요'),
 ('목표가 중앙값과 차이','전문가 예상가격까지 차이'),
 ('EPS 전망 30일 변화','한 달 전보다 이익 예상'),
 ('조건·근거 보기 ›','이유·조심할 점 보기 ›'),
 ('정규장 종가','정규장 마감 가격'),
 ('종가 기준 판단 · ','장 마감 가격으로 비교 · '),
 ('실적·목표가 단일 제공처 · 실시간 호가 아님','예상은 틀릴 수 있어요 · 실시간 가격 아님'),
 ('분석 점수는 고정 가중치를 적용한 조사 순서입니다. 성공확률이나 적정가치 점수가 아니며, 산업별 비교가 추가로 필요합니다.','종목을 누르면 괜찮게 본 이유와 조심할 점을 볼 수 있어요. 예상 가격까지 실제로 오른다는 보장은 없어요.'),
 ('단기 기술 조건 충족','짧게 볼 때의 조건을 통과했어요'),
 ('단기 추세 약세','최근 주가 흐름이 약해요'),
 ('단기 시세 확인','최근 주가 자료를 확인해야 해요'),
 ('돌파·거래량 조건 대기','주가 흐름과 거래량을 더 기다려요')
]:s=s.replace(before,after)
s=s.replace("<small>과거 공식대조 '+(r.official_history?.matched?.length||0)+'/8</small>","<small>'+esc(window.StockInvestmentCase?.get(r,data)?.confidence||'공식 숫자 비교 필요')+'</small>")
p.write_text(s)
p=root/'assets/stock-radar-v9.js';s=p.read_text()
a="function brief(){const root=$('#todayBrief');if(!root)return;"
b=a+"if(mode==='long'&&!paused&&window.StockInvestmentCase){root.innerHTML=window.StockInvestmentCase.brief(current,typeof selectedMarket==='undefined'?'ALL':selectedMarket);return;}"
s=replace_once(s,a,b);p.write_text(s)
p=root/'assets/stock-radar-v8.html';s=p.read_text();code=(root/'assets/stock-investment-cases.js').read_text();digest=hashlib.sha256(code.encode()).hexdigest()[:12]
s=re.sub(r'<script src="\./assets/stock-investment-cases\.js[^\"]*" defer></script>\s*','',s)
anchor=re.search(r'<script src="\./assets/stock-radar-v8\.js',s)
if not anchor:raise RuntimeError('Main JS tag not found')
s=s[:anchor.start()]+'<script src="./assets/stock-investment-cases.js?v='+digest+'" defer></script>\n'+s[anchor.start():]
for before,after in [('>매수 조건 충족</button>','>지금 살 만한 편</button>'),('>투자 매력 있음</button>','>지금 살 만한 편</button>'),('>가격·실적 후보</button>','>괜찮아 보이는 종목</button>'),('>긍정·조건부 의견</button>','>괜찮아 보이는 종목</button>'),('MY INVESTMENT RADAR','내 투자 후보'),('A CLEARER NEXT STEP','어떤 종목부터 볼까요?'),('좋은 기업보다, 내게 맞는 기회를.','살 만한 이유와 조심할 점을 한눈에.')]:s=s.replace(before,after)
p.write_text(s)
code=(root/'assets/stock-radar-v9.js').read_text();digest=hashlib.sha256(code.encode()).hexdigest()[:12]
s=re.sub(r'(stock-radar-v9\.js\?v=)[^\"]+',lambda m:m[1]+digest,s);p.write_text(s)
for name in ('stock-radar-v8.js','stock-radar-v9.js','stock-investment-cases.js','stock-decision-guide.js'):
 subprocess.run(['node','--check',str(root/'assets'/name)],check=True)
subprocess.run([sys.executable,'scripts/install_stock_decision_guide.py'],check=True)
subprocess.run([sys.executable,'scripts/install_stock_radar_v8.py'],check=True)
print('Plain-language investment view and macro-to-company decision guide installed. Financial values, rules, market filters and training unchanged.')
