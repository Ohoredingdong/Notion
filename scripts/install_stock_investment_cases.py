"""Integrate the case view into existing cards/detail; preserve market filters.
Idempotent, explicit anchors; does not modify financial data or training widgets.
"""
from pathlib import Path
import hashlib,re,subprocess,sys
root=Path('.')
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
s=s.replace('>매수 조건 충족</button>','>투자 매력 있음</button>').replace('>가격·실적 후보</button>','>긍정·조건부 의견</button>')
p.write_text(s)
code=(root/'assets/stock-radar-v9.js').read_text();digest=hashlib.sha256(code.encode()).hexdigest()[:12]
s=re.sub(r'(stock-radar-v9\.js\?v=)[^\"]+',lambda m:m[1]+digest,s);p.write_text(s)
for name in ('stock-radar-v8.js','stock-radar-v9.js','stock-investment-cases.js'):
 subprocess.run(['node','--check',str(root/'assets'/name)],check=True)
subprocess.run([sys.executable,'scripts/install_stock_radar_v8.py'],check=True)
print('Investment case integrated. Market filters and separate training preserved.')
