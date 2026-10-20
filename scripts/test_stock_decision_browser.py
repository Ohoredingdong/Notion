"""Exercise the real widget with the latest collected snapshot in Chromium.
Routes data and UI assets to the checked-out files for deterministic tests;
checks the deployed HTML separately rather than claiming fixture tests are live.
"""
import json,threading,http.server,urllib.parse,urllib.request,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path.cwd();OUT=ROOT/'decision-browser-tests';OUT.mkdir(exist_ok=True)
report={'cases':[],'errors':[],'mode':'Real collected JSON + checked-out complete widget; independent public HTML fetch'}
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',8766),Quiet)
threading.Thread(target=server.serve_forever,daemon=True).start()
data=json.loads(Path('stock-decision-data.json').read_text())
files={p.name:p for p in ROOT.glob('*.json')}
files.update({p.name:p for p in ROOT.glob('assets/*.js')})
state={'stale':False,'missing':False}

def record(name,success,detail=''):
 report['cases'].append({'name':name,'passed':bool(success),'detail':detail})
 if not success:report['errors'].append(name+': '+str(detail))

try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
  for width,height,label in [(1120,900,'desktop'),(390,844,'mobile')]:
   page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
   errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
   def intercept(route):
    parsed=urllib.parse.urlparse(route.request.url);name=Path(parsed.path).name
    if name=='stock-decision-data.json':
     if state['missing']:route.fulfill(status=503,body='test source failure');return
     value={**data}
     if state['stale']:value['generated_at']='2025-01-01T00:00:00+00:00'
     route.fulfill(status=200,content_type='application/json',body=json.dumps(value));return
    if name in files:
     file=files[name];route.fulfill(status=200,content_type='application/javascript' if file.suffix=='.js' else 'application/json',body=file.read_bytes());return
    if parsed.netloc=='127.0.0.1:8766':route.continue_();return
    route.fulfill(status=404,body='Fixture does not include external resource')
   page.route('**/*',intercept)
   page.goto('http://127.0.0.1:8766/stock-value-radar.html',wait_until='networkidle')
   page.wait_for_selector('#decision-v7-home .dv7-row')
   record(label+' ten firms',page.locator('#decision-v7-home .dv7-row').count()==10)
   record(label+' no training forms',page.locator('#v6Save,#v6Reason,#v6Decision,#v6DecisionBody').count()==0)
   record(label+' page width',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),str(page.evaluate('[innerWidth,document.documentElement.scrollWidth]')))
   page.screenshot(path=str(OUT/(label+'-overview.png')),full_page=True)
   page.locator('[data-dv-symbol="MSFT"]').click()
   page.wait_for_selector('#decision-v7-panel .dv7-verdict')
   record(label+' MSFT price condition','가격 대기' in page.locator('#decision-v7-panel').inner_text())
   record(label+' unique research view',page.locator('#decision-v7-panel').count()==1)
   page.screenshot(path=str(OUT/(label+'-msft.png')),full_page=True)
   page.select_option('#dv7-select','000660')
   record(label+' SK different decision','전망 편차' in page.locator('#decision-v7-panel').inner_text())
   page.locator('#decision-v7-panel summary').first.click()
   record(label+' numeric source links',page.locator('#decision-v7-panel a[href*="finance.yahoo.com"]').count()>=5)
   record(label+' detail width',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),str(page.evaluate('[innerWidth,document.documentElement.scrollWidth]')))
   page.screenshot(path=str(OUT/(label+'-skhynix.png')),full_page=True)
   state['stale']=True;page.locator('#reload').click();page.wait_for_timeout(800)
   record(label+' stale disables verdict','재수집 필요' in page.locator('#decision-v7-panel .dv7-verdict').first.inner_text())
   state['stale']=False;state['missing']=True;page.locator('#reload').click();page.wait_for_timeout(800)
   record(label+' fetch failure disables verdict','재수집 필요' in page.locator('#decision-v7-panel .dv7-verdict').first.inner_text())
   state['missing']=False
   record(label+' no runtime errors',not errors,'; '.join(errors))
   page.close()
  browser.close()
except Exception as e:report['errors'].append(type(e).__name__+': '+str(e))
finally:server.shutdown()
try:
 request=urllib.request.Request('https://ohoredingdong.github.io/Notion/stock-value-radar.html?verify=v7',headers={'User-Agent':'Stock-Decision-Deployment-Check/7.1'})
 with urllib.request.urlopen(request,timeout=20) as response:
  body=response.read();report['deployment']={'status':response.status,'contains_v7':b'stock-decision-v7.js' in body,'sha256':hashlib.sha256(body).hexdigest(),'x_frame_options':response.headers.get('X-Frame-Options')}
except Exception as e:report['deployment']={'error':str(e)[:200]}
report['passed']=not report['errors']
(OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['passed'] else 1)
