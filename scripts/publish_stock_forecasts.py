"""Publish forecast bundle atomically; preserve append-only evidence and state CAS."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
from stock_forecast_model import digest
from stock_forecast_learning import STATE_FILE, REPORT_FILE, ATTEMPTS_FILE, EVENTS_FILE
FILES=['stock-direction-forecast.json','stock-forecast-ledger.jsonl',
       'stock-forecast-outcomes.jsonl','stock-forecast-deliveries.jsonl',
       STATE_FILE,REPORT_FILE,ATTEMPTS_FILE,EVENTS_FILE]
TAGS=['<script src="./assets/stock-forecast.js?v=direction-forecast-1.0" defer></script>',
      '<script src="./assets/stock-forecast-learning.js?v=forward-learning-1.0" defer></script>']
HTML=['stock-value-radar.html','assets/stock-radar-v8.html','stock-forecast.html']

def git(root,*args,check=True):
    return subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,check=check)

def merged_lines(old,new):
    result,seen=[],set()
    for line in (old+'\n'+new).splitlines():
        if not line.strip():continue
        r=json.loads(line);key=r.get('id') or r.get('verification_id')
        if not key:raise ValueError('ledger_record_missing_id')
        if key not in seen:
            seen.add(key);result.append(json.dumps(r,ensure_ascii=False,allow_nan=False,separators=(',',':')))
    return '\n'.join(result)+'\n' if result else ''

def publish(root=Path('.')):
    root=root.resolve();payload={p:(root/p).read_text() for p in FILES}
    data=json.loads(payload[FILES[0]]);state=json.loads(payload[STATE_FILE])
    for _ in range(8):
        git(root,'fetch','origin','main')
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)/'work';git(root,'worktree','add','--detach',str(work),'origin/main')
            try:
                remote=work/FILES[0]
                if remote.exists() and json.loads(remote.read_text())['generated_at']>data['generated_at']:
                    raise RuntimeError('newer_forecast_already_published')
                remote_state=work/STATE_FILE
                remote_hash=digest(json.loads(remote_state.read_text())) if remote_state.exists() else None
                if remote_hash not in (state.get('parent_sha256'),digest(state)):
                    raise RuntimeError('learning_state_changed; recollect rather than overwrite')
                for name,body in payload.items():
                    dest=work/name
                    if name.endswith('.jsonl'):body=merged_lines(dest.read_text() if dest.exists() else '',body)
                    dest.write_text(body)
                for name in HTML:
                    path=work/name
                    if not path.exists():raise RuntimeError('radar_template_missing')
                    text=path.read_text()
                    for tag in TAGS:
                        asset=tag.split('src="')[1].split('?')[0]
                        if asset not in text:
                            if '</head>' not in text:raise RuntimeError('template_head_missing')
                            text=text.replace('</head>',tag+'\n</head>',1)
                    path.write_text(text)
                git(work,'config','user.name','github-actions[bot]')
                git(work,'config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
                git(work,'add','--',*FILES,*HTML)
                if git(work,'diff','--cached','--quiet',check=False).returncode==0:return
                git(work,'commit','-m','forecast: score frozen calls then learn from verified outcomes')
                if git(work,'push','origin','HEAD:main',check=False).returncode==0:
                    print('Forecast and learning bundle published',git(work,'rev-parse','HEAD').stdout.strip());return
            finally:git(root,'worktree','remove','--force',str(work),check=False)
        time.sleep(2)
    raise RuntimeError('publication_race; no force push performed')

if __name__=='__main__':publish()
