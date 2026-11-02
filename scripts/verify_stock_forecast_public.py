"""Verify public prediction/controller snapshots and code; not human push receipt."""
from datetime import datetime,timezone
import argparse,hashlib,json,time,urllib.request
from pathlib import Path
from stock_forecast_model import digest
BASE='https://ohoredingdong.github.io/Notion/'

def main(probe_only=False):
    names=['stock-direction-forecast.json','stock-forecast-learning.json','stock-forecast-autopilot.json']
    expected={n:json.loads(Path(n).read_text()) for n in names}
    scripts=['assets/stock-forecast.js','assets/stock-forecast-learning.js','assets/stock-forecast-directions.js','assets/stock-forecast-autopilot.js']
    hashes={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in scripts}
    # Bounded Pages propagation window: 50 polls, up to 49 eight-second waits.
    for attempt in range(50):
        try:
            def get(name):
                request=urllib.request.Request(BASE+name+'?check='+str(time.time_ns()),headers={'Cache-Control':'no-cache'})
                with urllib.request.urlopen(request,timeout=15) as response:return response.read()
            for name in names:
                if digest(json.loads(get(name)))!=digest(expected[name]):raise ValueError('public_snapshot_not_equal')
            for name in scripts:
                if hashlib.sha256(get(name)).hexdigest()!=hashes[name]:raise ValueError('public_code_not_equal')
            html=get('stock-value-radar.html').decode()
            if any(name not in html for name in scripts):raise ValueError('main_radar_not_integrated')
            if probe_only:
                print('EXACT_PUBLIC_FORECAST_AND_CODE_PROBE_ONLY_VERIFIED',datetime.now(timezone.utc).isoformat())
                return
            record={'status':'public_verified','verified_at':datetime.now(timezone.utc).isoformat(),
                    'snapshot_generated_at':expected[names[0]]['generated_at'],
                    'prediction_ids':[r['id'] for r in expected[names[0]]['records'] if r.get('status')=='research_prediction'],
                    'human_notification_received':False}
            record['verification_id']=digest(record)
            with Path('stock-forecast-deliveries.jsonl').open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
            print('EXACT_PUBLIC_AUTOPILOT_FORECAST_AND_CODE_VERIFIED',record['verified_at']);return
        except Exception as exc:
            if attempt==49:
                # Safe, fixed diagnostic codes only; no public URLs or HTTP body leaks.
                safe={'public_snapshot_not_equal','public_code_not_equal','main_radar_not_integrated'}
                reason=str(exc) if type(exc) is ValueError and str(exc) in safe else type(exc).__name__
                raise RuntimeError('public_deployment_unverified: '+reason) from None
            time.sleep(8)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--probe-only',action='store_true',help='Check exact public bytes without writing any delivery proof')
    main(probe_only=parser.parse_args().probe_only)
