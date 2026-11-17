"""One-issuer live probe. No raw data files, documents, keys or contact printed."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
from build_stock_investment_cases import Dart
from stock_corporate_actions import DartIndex


def main():
    # No arbitrary endpoint/issuer supplied by external data or a workflow input.
    key=os.getenv('DART_API_KEY','').strip()
    if not key:
        print('CORPORATE_PROBE_BLOCKED: credential_unavailable');return 2
    try:
        client=Dart(key)
        client.corpmap()
        corp=client.codes.get('005930')
        if not corp or not re.fullmatch(r'\d{8}',corp):
            print('CORPORATE_PROBE_FAILED: issuer_mapping');return 1
        end=datetime.now(timezone.utc).date();start=end-timedelta(days=14)
        result=DartIndex(key,max_pages=5).collect(corp,start.strftime('%Y%m%d'),end.strftime('%Y%m%d'))
        if not result['coverage']['complete']:
            print('CORPORATE_PROBE_FAILED: index_incomplete');return 1
        items=result.get('items',[])
        if not items:
            print('CORPORATE_PROBE_INCONCLUSIVE: no_recent_filing');return 2
        if any(r.get('corp_code')!=corp or not re.fullmatch(r'\d{14}',str(r.get('filing_id'))) for r in items):
            print('CORPORATE_PROBE_FAILED: identity_validation');return 1
        if result['coverage']['semantic_complete'] is not False:
            print('CORPORATE_PROBE_FAILED: unsupported_semantic_claim');return 1
        if key in json.dumps(result):
            print('CORPORATE_PROBE_FAILED: secret_guard');return 1
        print('CORPORATE_PROBE_PASSED: bounded_official_index_only');return 0
    except Exception:
        # Do not print exception strings/tracebacks: provider URLs may contain secrets.
        print('CORPORATE_PROBE_FAILED: protected_source_error');return 1
if __name__=='__main__':sys.exit(main())
