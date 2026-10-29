"""Record when the EXACT forecast payload was first observed on public Pages.
This is not proof of push-notification receipt by the human user.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request
from stock_forecast_model import digest

BASE = 'https://ohoredingdong.github.io/Notion/'

def main():
    expected = json.loads(Path('stock-direction-forecast.json').read_text())
    expected_js = hashlib.sha256(Path('assets/stock-forecast.js').read_bytes()).hexdigest()
    for attempt in range(16):
        try:
            def get(name):
                req = urllib.request.Request(BASE+name+'?check='+str(time.time_ns()), headers={'Cache-Control': 'no-cache'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    return response.read()
            actual = json.loads(get('stock-direction-forecast.json'))
            if digest(actual) != digest(expected):
                raise ValueError('public_snapshot_not_equal')
            if hashlib.sha256(get('assets/stock-forecast.js')).hexdigest() != expected_js:
                raise ValueError('public_code_not_equal')
            if 'assets/stock-forecast.js' not in get('stock-value-radar.html').decode():
                raise ValueError('main_radar_not_integrated')
            record = {'status': 'public_verified', 'verified_at': datetime.now(timezone.utc).isoformat(),
                      'snapshot_generated_at': actual['generated_at'],
                      'prediction_ids': [r['id'] for r in actual['records'] if r.get('status') == 'research_prediction'],
                      'human_notification_received': False}
            record['verification_id'] = digest(record)
            with Path('stock-forecast-deliveries.jsonl').open('a') as f:
                f.write(json.dumps(record, ensure_ascii=False)+'\n')
            print('EXACT_PUBLIC_FORECAST_AND_CODE_VERIFIED', record['verified_at'])
            return
        except Exception as exc:
            if attempt == 15:
                raise RuntimeError('public_deployment_unverified: '+type(exc).__name__) from None
            time.sleep(8)

if __name__ == '__main__':
    main()
