"""Publish only generated investment artifacts; never force-push or replace newer data.

A fresh detached worktree avoids rebase conflicts with concurrent market jobs.
UI is regenerated from that worktree's latest template. The source collectors,
training widgets, secrets and unrelated repository files are not overwritten.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys,tempfile,time

ROOT=Path.cwd()
OUTPUTS=['stock-opportunity-data.json','stock-opportunity-summary.json','stock-opportunity-tests.json','stock-opportunity-filing-tests.json','stock-opportunity-date-tests.json','stock-opportunity-extension-audit.json']
UI=['stock-value-radar.html','assets/stock-radar-v8.js','scripts/install_stock_decision_ui.py','scripts/install_stock_audit_ui.py']
ENGINE=['stock-opportunity-universe.json','scripts/update_stock_opportunities.py','scripts/update_stock_decisions.py','scripts/finalize_stock_opportunities.py','scripts/validate_stock_opportunity_dates.py']
def git(*args,cwd=ROOT,check=True):return subprocess.run(['git',*args],cwd=cwd,check=check,text=True,capture_output=True)
def date(path):
 try:return datetime.fromisoformat(json.loads(path.read_text())['generated_at'].replace('Z','+00:00'))
 except (OSError,KeyError,ValueError):return datetime.min.replace(tzinfo=timezone.utc)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
payload={p:(ROOT/p).read_bytes() for p in OUTPUTS if (ROOT/p).exists()}
assert 'stock-opportunity-data.json' in payload
engine={p:digest(ROOT/p) for p in ENGINE}
for attempt in range(4):
 git('fetch','origin','main')
 path=Path(tempfile.mkdtemp(prefix='radar-publish-'));path.rmdir()
 git('worktree','add','--detach',str(path),'origin/main')
 try:
  if any(digest(path/p)!=v for p,v in engine.items()):raise RuntimeError('Collector inputs changed during collection; current data is preserved and a new run is needed.')
  if date(path/'stock-opportunity-data.json')>date(ROOT/'stock-opportunity-data.json'):
   print('A newer completed snapshot already exists; not replacing it.');raise SystemExit(0)
  for name,body in payload.items():(path/name).write_bytes(body)
  subprocess.run([sys.executable,'scripts/refine_stock_radar_v8.py'],cwd=path,check=True)
  subprocess.run(['node','--check','assets/stock-radar-v8.js'],cwd=path,check=True)
  subprocess.run([sys.executable,'scripts/install_stock_radar_v8.py'],cwd=path,check=True)
  git('config','user.name','github-actions[bot]',cwd=path)
  git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com',cwd=path)
  git('add','--',*payload.keys(),*UI,cwd=path)
  if git('diff','--cached','--quiet',cwd=path,check=False).returncode==0:
   print('No changes to publish.');raise SystemExit(0)
  git('commit','-m','data: publish period-validated opportunities and source-linked iOS view',cwd=path)
  pushed=git('push','origin','HEAD:main',cwd=path,check=False)
  if pushed.returncode==0:print('Published on current main:',git('rev-parse','HEAD',cwd=path).stdout.strip());raise SystemExit(0)
  print('Concurrent update; retrying without force push:',pushed.stderr[-800:])
 finally:
  git('worktree','remove','--force',str(path),check=False)
 time.sleep((attempt+1)*3)
raise SystemExit('Publication conflict persisted; old published data has not been rewritten.')
