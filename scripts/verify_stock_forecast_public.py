"""Verify exact public forecast+learning report and code; NOT human push receipt."""
from datetime import datetime, timezone
import hashlib,json,time,urllib.request
from pathlib import Path
from stock_forecast_model import digest
BASE='https://ohoredingdong.github.io/Notion/'

def main():
    files=['stock-direction-forecast.json','stock-forecast-learning.json',
           'assets/stock-forecast.js','assets/stock-forecast-learning.js']
    hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in files}
    for attempt in range(16):
        try:
            def get(name):
                req=urllib.request.Request(BASE+name+'?check='+str(time.time_ns()),headers={'Cache-Control':'no-cache'})
                with urllib.request.urlopen(req,timeout=15) as response:return response.read()
            bodies={name:get(name) for name in files}
            for name in files:
                if hashlib.sha256(bodies[name]).hexdigest()!=hashes[name]:raise ValueError('public_bundle_mismatch')
            html=get('stock-value-radar.html').decode()
            if any(name not in html for name in files if name.endswith('.js')):raise ValueError('main_not_integrated')
            actual=json.loads(bodies[files[0]])
            record={'status':'public_verified','verified_at':datetime.now(timezone.utc).isoformat(),
                    'snapshot_generated_at':actual['generated_at'],
                    'prediction_ids':[r['id'] for r in actual['records'] if r.get('status')=='research_prediction'],
                    'learning_report_verified':True,'human_notification_received':False}
            record['verification_id']=digest(record)
            with Path('stock-forecast-deliveries.jsonl').open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
            print('EXACT_PUBLIC_FORECAST_LEARNING_AND_CODE_VERIFIED',record['verified_at']);return
        except Exception as exc:
            if attempt==15:raise RuntimeError('public_deployment_unverified: '+type(exc).__name__) from None
            time.sleep(8)
if __name__=='__main__':main()
