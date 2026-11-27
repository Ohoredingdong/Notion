"""Read-only accounting of original active targets absent from a no-call snapshot.
Never a serving rule, trading signal, new issuance or human receipt.
"""
import argparse
import copy
import json
import math
import unittest
import zipfile
from datetime import datetime

REASON = 'target_already_started_or_delivery_window_too_short'


def time(value):
    try:
        t = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return t if t.utcoffset() is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def group(row):
    return tuple(row.get(k) for k in ('market', 'symbol', 'mode'))


def diagnose(snapshot, ledger, deliveries, as_of):
    cutoff, generated = time(as_of), time(snapshot.get('generated_at'))
    if None in (cutoff, generated) or generated > cutoff:
        raise ValueError('invalid_snapshot_cutoff')
    current, ids, first, proof = {}, {}, {}, {}
    for row in snapshot['records']:
        g = group(row)
        if None in g or g in current:
            raise ValueError('ambiguous_snapshot_group')
        current[g] = row
    for row in ledger:
        pid = row.get('id')
        if not pid:
            continue
        if pid in ids and ids[pid] != row:
            raise ValueError('conflicting_original_id')
        ids[pid] = row
        target = row.get('target') or {}
        start, end, issue = map(time, (target.get('start'), target.get('end'), row.get('issued_at')))
        g = group(row)
        if row.get('status') != 'research_prediction' or None in (*g, start, end, issue):
            continue
        if not start <= generated <= cutoff < end:
            continue
        key = (*g, start, end)
        old = first.get(key)
        if old is not None and issue == old[0] and pid != old[1]['id']:
            raise ValueError('ambiguous_first_issue')
        if old is None or issue < old[0]:
            first[key] = (issue, row)
    for p in deliveries:
        verified = time(p.get('verified_at'))
        if p.get('status') != 'public_verified' or verified is None or verified > generated:
            continue
        for pid in p.get('prediction_ids', []):
            issue = time(ids.get(pid, {}).get('issued_at'))
            if issue is not None and issue <= verified:
                proof[pid] = min(proof.get(pid, verified), verified)
    affected = []
    for key, (issue, row) in first.items():
        g, start, end = key[:3], key[3], key[4]
        pid = row['id']
        fresh = current.get(g, {})
        obs, receipt, new_obs, published = (time(row.get('observed_until')), time(row.get('received_at')),
                                               time(fresh.get('observed_until')), proof.get(pid))
        if fresh.get('status') != 'no_call' or fresh.get('reason') != REASON:
            continue
        if None in (obs, receipt, new_obs, published) or new_obs != obs:
            continue
        band = row.get('neutral_band_pct')
        if not isinstance(band, (int, float)) or isinstance(band, bool) or not math.isfinite(band) or band < 0:
            continue
        if not obs <= receipt <= issue <= published < start <= generated <= cutoff < end:
            continue
        affected.append(dict(prediction_id=pid, group=g, observed_until=row['observed_until'],
                             issued_at=row['issued_at'], first_public=published.isoformat(),
                             target=row['target'].copy(), neutral_band_pct=band,
                             policy_revision=row.get('policy_revision'), refresh_reason=REASON))
    return dict(scope='read_only_active_target_snapshot_gap_not_receipt_or_serving_policy',
                as_of=as_of, affected_count=len(affected),
                affected=sorted(affected, key=lambda x: x['prediction_id']))


class Tests(unittest.TestCase):
    def setUp(self):
        self.row = dict(id='x', market='KR', symbol='X', mode='daily', status='research_prediction',
                        observed_until='2026-11-26T06:30:00Z', received_at='2026-11-26T13:00:00Z',
                        issued_at='2026-11-26T13:01:00Z', neutral_band_pct=.5,
                        policy_revision='session-complete-targets-v2',
                        target=dict(start='2026-11-27T00:00:00Z', end='2026-11-27T06:30:00Z'))
        self.fresh = dict(market='KR', symbol='X', mode='daily', status='no_call', reason=REASON,
                          observed_until=self.row['observed_until'])
        self.snap = dict(generated_at='2026-11-27T03:00:00Z', records=[self.fresh])
        self.proof = dict(status='public_verified', verified_at='2026-11-26T13:02:00Z', prediction_ids=['x'])
        self.cutoff = '2026-11-27T03:13:05Z'
    def count(self, rows=None, proofs=None):
        return diagnose(self.snap, rows if rows is not None else [self.row],
                        proofs if proofs is not None else [self.proof], self.cutoff)['affected_count']
    def test_positive_immutable(self):
        before=copy.deepcopy((self.row,self.snap,self.proof)); self.assertEqual(self.count(),1)
        self.assertEqual(before,(self.row,self.snap,self.proof))
    def test_expired(self):
        self.cutoff='2026-11-27T06:30:00Z'; self.assertEqual(self.count(),0)
    def test_future_target(self):
        self.row['target']['start']='2026-11-27T03:30:00Z'; self.assertEqual(self.count(),0)
    def test_proof_late(self):
        self.proof['verified_at']='2026-11-27T00:00:00Z'; self.assertEqual(self.count(),0)
    def test_no_proof(self): self.assertEqual(self.count(proofs=[]),0)
    def test_unverified(self):
        self.proof['status']='unknown'; self.assertEqual(self.count(),0)
    def test_stale_and_newer(self):
        for v in ('2026-11-25T06:30:00Z','2026-11-27T00:00:00Z'):
            self.fresh['observed_until']=v; self.assertEqual(self.count(),0)
    def test_group_mismatch(self):
        self.fresh['market']='US'; self.assertEqual(self.count(),0)
    def test_current_call(self):
        self.fresh['status']='research_prediction'; self.assertEqual(self.count(),0)
    def test_other_reason(self):
        self.fresh['reason']='missing_data'; self.assertEqual(self.count(),0)
    def test_naive_time(self):
        self.row['received_at']='2026-11-26T13:00:00'; self.assertEqual(self.count(),0)
    def test_exact_duplicate(self): self.assertEqual(self.count([self.row,self.row]),1)
    def test_conflicting_id(self):
        with self.assertRaises(ValueError): self.count([self.row,{**self.row,'symbol':'Y'}])
    def test_same_time_distinct_ids(self):
        with self.assertRaises(ValueError): self.count([self.row,{**self.row,'id':'y'}])
    def test_later_reissue_not_rescored(self):
        later={**self.row,'id':'y','issued_at':'2026-11-26T13:03:00Z'}
        self.assertEqual(self.count([later,self.row]),1)
        self.proof['prediction_ids']=['y']; self.proof['verified_at']='2026-11-26T13:04:00Z'
        self.assertEqual(self.count([later,self.row]),0)
    def test_snapshot_after_cutoff(self):
        self.cutoff='2026-11-27T02:59:00Z'
        with self.assertRaises(ValueError): self.count()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--archive');p.add_argument('--as-of');a=p.parse_args()
    if a.self_test: unittest.main(argv=['self-test'])
    else:
        if not a.archive or not a.as_of: p.error('--archive and --as-of required')
        with zipfile.ZipFile(a.archive) as z:
            def rows(n): return [json.loads(l) for l in z.read(n).splitlines() if l.strip()]
            result=diagnose(json.loads(z.read('stock-direction-forecast.json')),rows('stock-forecast-ledger.jsonl'),rows('stock-forecast-deliveries.jsonl'),a.as_of)
        print(json.dumps(result,ensure_ascii=False,indent=2))
