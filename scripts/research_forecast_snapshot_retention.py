"""Read-only diagnostic of already-public future forecasts hidden by stale-input no-calls.
Not a signal, serving policy, scoring change or delivery receipt.
"""
import argparse
import copy
import json
import unittest
import zipfile
from datetime import datetime


def stamp(value):
    try:
        t = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return t if t.utcoffset() is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def group(row):
    return tuple(row.get(k) for k in ('market', 'symbol', 'mode'))


def diagnose(snapshot, ledger, deliveries, as_of):
    cutoff, generated = stamp(as_of), stamp(snapshot.get('generated_at'))
    if cutoff is None or generated is None or generated > cutoff:
        raise ValueError('invalid_snapshot_cutoff')
    current = {}
    for row in snapshot['records']:
        key = group(row)
        if None in key or key in current:
            raise ValueError('ambiguous_snapshot_group')
        current[key] = row
    original = {}
    for row in ledger:
        pid = row.get('id')
        if not pid:
            continue
        if pid in original and original[pid] != row:
            raise ValueError('conflicting_original_id')
        original[pid] = row
    public = {}
    for proof in deliveries:
        t = stamp(proof.get('verified_at'))
        if proof.get('status') != 'public_verified' or t is None or t > generated:
            continue
        for pid in proof.get('prediction_ids', []):
            row = original.get(pid, {})
            issue = stamp(row.get('issued_at'))
            if issue is not None and issue <= t:
                public[pid] = min(public.get(pid, t), t)
    affected = []
    for pid, row in original.items():
        fresh = current.get(group(row), {})
        target = row.get('target') or {}
        obs, received, issued, start, end = [stamp(v) for v in (
            row.get('observed_until'), row.get('received_at'), row.get('issued_at'),
            target.get('start'), target.get('end'))]
        fresh_obs, proof = stamp(fresh.get('observed_until')), public.get(pid)
        if (row.get('status') != 'research_prediction' or fresh.get('status') != 'no_call'
                or None in (obs, received, issued, start, end, fresh_obs, proof)):
            continue
        if not (fresh_obs < obs <= received <= issued <= proof <= generated <= cutoff < start < end):
            continue
        affected.append({'prediction_id': pid, 'group': group(row),
                         'original_observed_until': row['observed_until'],
                         'original_issued_at': row['issued_at'], 'public_verified_at': proof.isoformat(),
                         'target_start': target['start'], 'target_end': target['end'],
                         'refresh_observed_until': fresh['observed_until'],
                         'refresh_no_call_reason': fresh.get('reason')})
    return {'scope': 'read_only_snapshot_gap_not_receipt_or_serving_policy',
            'as_of': as_of, 'snapshot_generated_at': snapshot['generated_at'],
            'affected_count': len(affected), 'affected': sorted(affected, key=lambda r: r['prediction_id'])}


class Tests(unittest.TestCase):
    def setUp(self):
        self.row = dict(id='a', market='US', symbol='X', mode='daily', status='research_prediction',
                        observed_until='2026-11-25T21:00:00Z', received_at='2026-11-25T22:00:00Z',
                        issued_at='2026-11-25T22:01:00Z', target={'start':'2026-11-27T14:30:00Z','end':'2026-11-27T18:00:00Z'})
        self.fresh = dict(market='US',symbol='X',mode='daily',status='no_call',observed_until='2026-11-24T21:00:00Z')
        self.snapshot = dict(generated_at='2026-11-26T02:19:56Z',records=[self.fresh])
        self.proof = dict(status='public_verified',verified_at='2026-11-25T22:02:00Z',prediction_ids=['a'])
        self.cutoff = '2026-11-26T03:13:43Z'
    def count(self):
        return diagnose(self.snapshot,[self.row],[self.proof],self.cutoff)['affected_count']
    def test_positive_and_immutable(self):
        before=copy.deepcopy((self.snapshot,self.row,self.proof))
        self.assertEqual(self.count(),1)
        self.assertEqual((self.snapshot,self.row,self.proof),before)
    def test_expired_or_started(self):
        self.cutoff='2026-11-27T14:30:00Z';self.assertEqual(self.count(),0)
    def test_late_proof(self):
        self.proof['verified_at']='2026-11-27T14:31:00Z';self.assertEqual(self.count(),0)
    def test_proof_after_snapshot(self):
        self.proof['verified_at']='2026-11-26T03:00:00Z';self.assertEqual(self.count(),0)
    def test_forged_before_issue(self):
        self.proof['verified_at']='2026-11-25T21:00:00Z';self.assertEqual(self.count(),0)
    def test_missing_or_unverified_proof(self):
        self.proof['status']='public_unverified';self.assertEqual(self.count(),0)
    def test_newer_input(self):
        self.fresh['observed_until']=self.row['observed_until'];self.assertEqual(self.count(),0)
    def test_unknown_or_naive_time(self):
        self.fresh['observed_until']='2026-11-24T21:00:00';self.assertEqual(self.count(),0)
    def test_other_group(self):
        self.fresh['market']='KR';self.assertEqual(self.count(),0)
    def test_current_prediction(self):
        self.fresh['status']='research_prediction';self.assertEqual(self.count(),0)
    def test_duplicate_exact_and_conflicting(self):
        self.assertEqual(diagnose(self.snapshot,[self.row,self.row],[self.proof,self.proof],self.cutoff)['affected_count'],1)
        with self.assertRaises(ValueError):
            diagnose(self.snapshot,[self.row,{**self.row,'symbol':'Y'}],[self.proof],self.cutoff)
    def test_future_snapshot(self):
        self.cutoff='2026-11-25T00:00:00Z'
        with self.assertRaises(ValueError):self.count()


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--archive')
    parser.add_argument('--as-of')
    args=parser.parse_args()
    if args.self_test:
        unittest.main(argv=['self-test'])
    else:
        if not args.archive or not args.as_of:parser.error('--archive and --as-of are required')
        with zipfile.ZipFile(args.archive) as z:
            def rows(name):return [json.loads(line) for line in z.read(name).splitlines() if line.strip()]
            result=diagnose(json.loads(z.read('stock-direction-forecast.json')),rows('stock-forecast-ledger.jsonl'),rows('stock-forecast-deliveries.jsonl'),args.as_of)
        print(json.dumps(result,ensure_ascii=False,indent=2))
