"""Publish categorization and its UI only, from current main without force push."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,tempfile,time,sys
ROOT=Path.cwd();payload=(ROOT/'stock-market-groups.json').read_bytes()
UI=['stock-market-groups.json','stock-value-radar.html','assets/stock-radar-v8.js','assets/stock-radar-v9.js','assets/stock-radar-v8.html','scripts/install_stock_decision_ui.py','scripts/install_stock_audit_ui.py']
def git(*args,cwd=ROOT,check=True):return subprocess.run(['git',*args],cwd=cwd,check=check,text=True,capture_output=True)
def generated(body):
 try:return datetime.fromisoformat(json.loads(body)['generated_at'])
 except (ValueError,KeyError):return datetime.min.replace(tzinfo=timezone.utc)
for attempt in range(4):
 git('fetch','origin','main');work=Path(tempfile.mkdtemp(prefix='radar-market-publish-'));work.rmdir();git('worktree','add','--detach',str(work),'origin/main')
 try:
  existing=work/'stock-market-groups.json'
  if not existing.exists() or generated(existing.read_bytes())<=generated(payload):existing.write_bytes(payload)
  for script in ('scripts/install_stock_market_groups.py','scripts/apply_stock_radar_v9.py','scripts/refine_stock_radar_v8.py','scripts/install_stock_radar_v8.py'):
   subprocess.run([sys.executable,script],cwd=work,check=True)
  for asset in ('assets/stock-radar-v8.js','assets/stock-radar-v9.js','assets/stock-market-groups.js'):subprocess.run(['node','--check',asset],cwd=work,check=True)
  git('config','user.name','github-actions[bot]',cwd=work);git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com',cwd=work)
  git('add','--',*UI,cwd=work)
  if git('diff','--cached','--quiet',cwd=work,check=False).returncode==0:print('No classification changes');raise SystemExit(0)
  git('commit','-m','ui: publish KOSPI KOSDAQ Nasdaq Dow filters with dated classification sources',cwd=work)
  r=git('push','origin','HEAD:main',cwd=work,check=False)
  if not r.returncode:print('Published',git('rev-parse','HEAD',cwd=work).stdout.strip());raise SystemExit(0)
  print('Concurrent update; retrying without overwriting other files')
 finally:git('worktree','remove','--force',str(work),check=False)
 time.sleep((attempt+1)*2)
raise SystemExit('Concurrent publication did not resolve; published files preserved')
