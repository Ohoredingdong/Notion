"""Verify public prediction/controller snapshots and code; not human push receipt."""
from datetime import datetime,timezone
import argparse,hashlib,json,time,urllib.request
from pathlib import Path
from stock_forecast_paper import digest
import stock_forecast_paper as paper
BASE='https://ohoredingdong.github.io/Notion/'

def get_public(name):
    request=urllib.request.Request(BASE+name+'?check='+str(time.time_ns()),headers={'Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=15) as response:return response.read()


def verify_paper_publication(root=Path('.'),get=None,clock=None):
    """Observe exact published plan/policy bytes without inventing a receipt.

    The timestamp is taken only after both HTTP bodies have matched. A late
    first check is permanently recorded as late, never backdated to registration.
    All ledger additions are prepared before any append and repeated checks do
    not rewrite or duplicate prior first-public observations.
    """
    root=Path(root);get=get or get_public;clock=clock or (lambda:datetime.now(timezone.utc))
    names=(paper.POLICY_FILE,paper.PLAN_FILE)
    local={name:(root/name).read_bytes() for name in names}
    hashes={name:hashlib.sha256(body).hexdigest() for name,body in local.items()}
    for name in names:
        if get(name)!=local[name]:raise ValueError('public_paper_bytes_not_equal')
    if any((root/name).read_bytes()!=body for name,body in local.items()):
        raise ValueError('local_paper_changed_during_public_check')
    observed=paper.instant(clock())
    policy=paper.policy_for(json.loads(local[paper.POLICY_FILE]),observed)
    plans=[json.loads(line) for line in local[paper.PLAN_FILE].splitlines() if line.strip()]
    prior=paper.read_lines(root/paper.PUBLICATION_FILE)
    plan_ids={plan['id'] for plan in plans}
    if len(plan_ids)!=len(plans) or any(row.get('plan_id') not in plan_ids for row in prior):
        raise ValueError('public_paper_identity_mismatch')
    additions=[]
    for plan in plans:
        payload={key:value for key,value in plan.items() if key!='id'}
        registered=paper.instant(plan['registered_at']);start=paper.instant(plan['target']['start'])
        if (paper.digest(payload)!=plan['id'] or plan['policy_id']!=policy['id']
                or not paper.instant(policy['registered_at'])<=registered<=observed
                or not registered<start<paper.instant(plan['target']['end'])
                or not paper.instant(plan['first_public_at'])<=registered
                or plan.get('orders_enabled') is not False or plan.get('strict_green_override') is not False):
            raise ValueError('invalid_immutable_paper_plan')
        paper.verified_plan_publication(plan,policy,prior,observed)
        if any(row.get('plan_id')==plan['id'] for row in prior):continue
        proof={'version':paper.PUBLICATION_VERSION,'status':'public_plan_verified',
               'verified_at':observed.isoformat(),'base_url':BASE,
               'policy_id':policy['id'],'policy_sha256':paper.digest(policy),
               'plan_id':plan['id'],'plan_sha256':paper.digest(plan),'forecast_id':plan['forecast_id'],
               'public_files_sha256':hashes,'public_before_target_verified':observed<start,
               'human_notification_received':False}
        proof['verification_id']=paper.digest(proof)
        additions.append(proof)
    if additions or not (root/paper.PUBLICATION_FILE).exists():
        with (root/paper.PUBLICATION_FILE).open('a') as target:
            for record in additions:
                target.write(json.dumps(record,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    return {'new_checks':len(additions),'before_target':sum(row['public_before_target_verified'] for row in additions),
            'late_checks':sum(not row['public_before_target_verified'] for row in additions),'human_receipts_created':0}


def main(paper_only=False):
    if paper_only:
        for attempt in range(16):
            try:
                report=verify_paper_publication()
                print('EXACT_PUBLIC_PAPER_PLANS_AND_POLICY_VERIFIED',json.dumps(report));return
            except Exception as exc:
                if attempt==15:raise RuntimeError('public_paper_deployment_unverified: '+type(exc).__name__) from None
                time.sleep(8)
    names=['stock-direction-forecast.json','stock-forecast-learning.json','stock-forecast-autopilot.json']
    expected={n:json.loads(Path(n).read_text()) for n in names}
    scripts=['assets/stock-forecast.js','assets/stock-forecast-learning.js','assets/stock-forecast-directions.js','assets/stock-forecast-autopilot.js']
    hashes={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in scripts}
    for attempt in range(16):
        try:
            for name in names:
                if digest(json.loads(get_public(name)))!=digest(expected[name]):raise ValueError('public_snapshot_not_equal')
            for name in scripts:
                if hashlib.sha256(get_public(name)).hexdigest()!=hashes[name]:raise ValueError('public_code_not_equal')
            html=get_public('stock-value-radar.html').decode()
            if any(name not in html for name in scripts):raise ValueError('main_radar_not_integrated')
            record={'status':'public_verified','verified_at':datetime.now(timezone.utc).isoformat(),
                    'snapshot_generated_at':expected[names[0]]['generated_at'],
                    'prediction_ids':[r['id'] for r in expected[names[0]]['records'] if r.get('status')=='research_prediction'],
                    'human_notification_received':False}
            record['verification_id']=digest(record)
            with Path('stock-forecast-deliveries.jsonl').open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
            print('EXACT_PUBLIC_AUTOPILOT_FORECAST_AND_CODE_VERIFIED',record['verified_at']);return
        except Exception as exc:
            if attempt==15:raise RuntimeError('public_deployment_unverified: '+type(exc).__name__) from None
            time.sleep(8)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--paper-only',action='store_true',help='Verify already-published immutable paper plans and policy; no human receipt.')
    main(parser.parse_args().paper_only)

