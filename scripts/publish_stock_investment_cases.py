"""Publish the case UI only in a fresh worktree; never force push."""
from pathlib import Path
import subprocess,sys,tempfile,time,shutil,json
ROOT=Path.cwd()
FILES=['stock-value-radar.html','assets/stock-radar-v8.html','assets/stock-radar-v8.js','assets/stock-radar-v9.js','scripts/install_stock_decision_ui.py','scripts/install_stock_audit_ui.py']
def git(*args,cwd=ROOT,check=True):return subprocess.run(['git',*args],cwd=cwd,check=check,text=True,capture_output=True)
for attempt in range(4):
 git('fetch','origin','main');path=Path(tempfile.mkdtemp(prefix='investment-case-ui-'));path.rmdir();git('worktree','add','--detach',str(path),'origin/main')
 try:
  subprocess.run([sys.executable,'scripts/install_stock_investment_cases.py'],cwd=path,check=True)
  git('config','user.name','github-actions[bot]',cwd=path);git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com',cwd=path)
  git('add','--',*FILES,cwd=path)
  if git('diff','--cached','--quiet',cwd=path,check=False).returncode==0:
   for name in FILES:shutil.copyfile(path/name,ROOT/name)
   print('Case UI already current');raise SystemExit(0)
  git('commit','-m','ui: show explicit investment appeal and the facts behind each opinion',cwd=path)
  result=git('push','origin','HEAD:main',cwd=path,check=False)
  if result.returncode==0:
   for name in FILES:shutil.copyfile(path/name,ROOT/name)
   print('Case UI published:',git('rev-parse','HEAD',cwd=path).stdout.strip());raise SystemExit(0)
  print('Concurrent update; retrying on latest main')
 finally:git('worktree','remove','--force',str(path),check=False)
 time.sleep(3*(attempt+1))
raise SystemExit('UI publication conflict; current main remains unchanged')
