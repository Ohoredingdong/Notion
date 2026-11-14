"""Read-only full-ledger accounting, independent of forecasting/learning code.

Every original row is retained in this report, including exclusions. Saved price
arithmetic is not raw exchange-price authentication, a fill, or a human receipt.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

CLASSES = ('down', 'flat', 'up')
ZONES = {'KR': ZoneInfo('Asia/Seoul'), 'US': ZoneInfo('America/New_York')}


def instant(value):
    if not isinstance(value, str):
        raise ValueError('invalid_timestamp')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timezone_required')
    return result.astimezone(timezone.utc)


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('finite_number_required')
    return float(value)


def vector(value):
    if not isinstance(value, dict) or set(value) != set(CLASSES):
        raise ValueError('invalid_probability_keys')
    p = [finite(value[c]) for c in CLASSES]
    if min(p) < 0 or max(p) > 1 or abs(math.fsum(p)-1) > 1e-6:
        raise ValueError('invalid_probability_vector')
    return p


def input_binding(records, outcomes, deliveries):
    """Independent reconstruction of the upstream input fingerprint contract."""
    sources = dict(ledger=records, outcomes=outcomes, deliveries=deliveries)
    result = {'version': 'canonical-json-rows-sha256-v1', 'counts': {}, 'sha256': {}}
    for name, rows in sources.items():
        result['counts'][name] = len(rows)
        try:
            encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                                 separators=(',', ':'), allow_nan=False).encode('utf-8')
            result['sha256'][name] = hashlib.sha256(encoded).hexdigest()
        except (TypeError, ValueError, OverflowError):
            result['sha256'][name] = None
    return result


def stats(entries):
    cm = [[0]*3 for _ in CLASSES]
    briers, logs = [], []
    for actual, predicted, p in entries:
        i, j = CLASSES.index(actual), CLASSES.index(predicted)
        cm[i][j] += 1
        briers.append(math.fsum((p[k]-int(k == i))**2 for k in range(3)))
        logs.append(-math.log(max(p[i], 1e-12)))
    n = len(entries); hits = sum(cm[i][i] for i in range(3)); directions = {}
    for i, name in enumerate(CLASSES):
        actual = sum(cm[i]); calls = sum(row[i] for row in cm); hit = cm[i][i]
        directions[name] = dict(actual=actual, calls=calls, hits=hit, missed=actual-hit,
            false_calls=calls-hit, recall=hit/actual if actual else None,
            precision=hit/calls if calls else None)
    return dict(samples=n, correct=hits, accuracy=hits/n if n else None,
        brier_loss=math.fsum(briers)/n if n else None,
        log_loss=math.fsum(logs)/n if n else None,
        confusion_matrix=cm, directions=directions)



def missing_window_clusters(missing_ids, valid):
    """Describe only already-unscored mature first issuances; never infer OHLC/labels.

    Normalize absolute UTC target instants (the same distinction enforced for
    event identity), and keep market/mode/explicit-or-unverified venue separate.
    """
    grouped=defaultdict(list)
    for rid in missing_ids:
        row, group, start, end, _, _ = valid[rid]
        key=(group[1], group[2], group[3], start.isoformat(), end.isoformat())
        grouped[key].append((rid, row))
    return [
        {
            'market':market, 'mode':mode, 'venue':venue,
            'target_start_utc':start, 'target_end_utc':end,
            'count':len(entries),
            'symbols':sorted(row['symbol'] for _,row in entries),
            'forecast_ids':sorted(rid for rid,_ in entries),
            'missing_context_counts':dict(sorted(Counter(
                row.get('missing_context') or 'source_progress_unknown'
                for _,row in entries).items())),
            'root_cause':'unverified', 'exchange_raw_bars_verified':False,
        }
        for (market,mode,venue,start,end),entries in sorted(grouped.items())
    ]



def census(records, outcomes, deliveries, independent, controller):
    """Use the upstream cutoff, but independently account/select/recalculate rows."""
    cutoff = instant(independent['audit_cutoff']); errors = []
    binding = input_binding(records, outcomes, deliveries)
    binding_verified = (binding == independent.get('source_binding') and
                        all(value is not None for value in binding['sha256'].values()))
    if not binding_verified:
        errors.append('upstream_source_binding_mismatch')
    if independent.get('status') != 'ledger_arithmetic_consistent' or independent.get('errors'):
        errors.append('upstream_integrity_not_verified')
    public = {}; repeated_proofs = 0
    for proof in deliveries:
        try:
            seen = instant(proof['verified_at']); snapshot = instant(proof['snapshot_generated_at'])
            if proof['status'] != 'public_verified' or snapshot > seen:
                raise ValueError('invalid_public_proof')
            if seen > cutoff:
                continue
            members = proof['prediction_ids']
            if not isinstance(members,list) or not members or len(set(members)) != len(members):
                raise ValueError('invalid_public_members')
            if all(rid in public for rid in members):
                repeated_proofs += 1
            for rid in members:
                if rid not in public or seen < public[rid]:
                    public[rid] = seen
        except (KeyError, TypeError, ValueError):
            errors.append('invalid_public_proof')
    actual = {}; duplicate_outcomes = 0
    for out in outcomes:
        rid = out.get('id')
        if rid in actual:
            duplicate_outcomes += 1
            if out != actual[rid]:errors.append('conflicting_outcome_id')
        else:actual[rid] = out
    rows = []; by_id = {}; candidates = defaultdict(list); valid = {}; verified = {}
    for index, record in enumerate(records):
        rid = record.get('id')
        row = {'ledger_row':index+1, 'id':rid, 'symbol':record.get('symbol'),
            'market':record.get('market'), 'mode':record.get('mode'),
            'venue':record.get('venue'), 'policy_revision':record.get('policy_revision'),
            'probabilities':record.get('probabilities'), 'predicted':record.get('direction'),
            'band_pct':record.get('neutral_band_pct'), 'target':record.get('target'),
            'observed_until':record.get('observed_until'), 'received_at':record.get('received_at'),
            'issued_at':record.get('issued_at'), 'first_public_verified_at':None,
            'human_received_at':None, 'outcome_source_checked_at':None,
            'outcome_evaluated_at':None, 'disposition':None}
        rows.append(row)
        try:
            if not isinstance(rid,str) or not rid or record['status'] != 'research_prediction':
                raise ValueError('invalid_frozen_record')
            if rid in by_id:
                row['disposition'] = 'exact_id_replay' if record == by_id[rid] else 'conflicting_id'
                if row['disposition'] == 'conflicting_id':errors.append('conflicting_prediction_id')
                continue
            by_id[rid] = record
            p=vector(record['probabilities']); direction=record['direction']; band=finite(record['neutral_band_pct'])
            if band < 0 or direction not in CLASSES or abs(p[CLASSES.index(direction)]-max(p))>1e-12:
                raise ValueError('invalid_frozen_prediction')
            obs, received, issued, start, end = map(instant, (record['observed_until'], record['received_at'],
                record['issued_at'], record['target']['start'], record['target']['end']))
            if not obs <= received <= issued < start < end:
                raise ValueError('nonprospective_record')
            if record['market'] not in ZONES or record['mode'] not in ('daily','intraday'):
                raise ValueError('invalid_market_mode')
            venue=record.get('venue') or 'venue_unverified'
            if not isinstance(venue,str):raise ValueError('invalid_venue')
            group=(record['symbol'],record['market'],record['mode'],venue)
            row['input_age_at_issue_seconds']=(issued-obs).total_seconds()
            row['first_public_verified_at']=public[rid].isoformat() if rid in public else None
            row['first_public_lead_seconds']=(start-public[rid]).total_seconds() if rid in public else None
            row['session_day']=start.astimezone(ZONES[record['market']]).date().isoformat()
            if issued>cutoff:
                row['disposition']='not_available_at_cutoff';continue
            valid[rid]=(row,group,start,end,issued,p)
            candidates[group+(start,end)].append(rid)
        except (KeyError,TypeError,ValueError,OverflowError):
            row['disposition']='invalid_forecast';errors.append('invalid_frozen_prediction')
    for rid,out in actual.items():
        if rid not in valid:
            errors.append('outcome_without_valid_forecast');continue
        row,group,start,end,issued,p=valid[rid];record=by_id[rid]
        row.update(outcome_source_checked_at=out.get('source_checked_at'), outcome_evaluated_at=out.get('evaluated_at'))
        try:
            a,b=finite(out['target_open']),finite(out['target_close'])
            if min(a,b)<=0 or out['status']!='observed' or out['target']!=record['target'] or out['symbol']!=record['symbol'] or out['mode']!=record['mode']:
                raise ValueError('outcome_identity')
            if not end<=instant(out['evaluated_at'])<=cutoff:raise ValueError('outcome_time')
            change=100*(b/a-1);band=finite(record['neutral_band_pct'])
            label='up' if change>band else 'down' if change < -band else 'flat'
            correct=label==record['direction'];loss=math.fsum((p[i]-int(c==label))**2 for i,c in enumerate(CLASSES))
            if (abs(finite(out['return_pct'])-change)>1e-8 or out['actual']!=label or out['predicted']!=record['direction'] or out['correct'] is not correct or abs(finite(out['brier_loss'])-loss)>1e-8):
                raise ValueError('outcome_arithmetic')
            row.update(opening=a,closing=b,change_pct=change,actual=label,correct=correct,brier_loss=loss)
            verified[rid]=(label,record['direction'],p)
        except (KeyError,TypeError,ValueError,OverflowError,ZeroDivisionError):
            errors.append('invalid_stored_outcome');row['outcome_integrity']='invalid'
    first=[]
    for ids in candidates.values():
        moment=min(valid[rid][4] for rid in ids); earliest=[rid for rid in ids if valid[rid][4]==moment]
        if len(earliest)>1:
            errors.append('ambiguous_first_issuance')
            for rid in ids:valid[rid][0]['disposition']='ambiguous_first_issuance'
            continue
        chosen=earliest[0];first.append(chosen)
        for rid in ids:
            if rid!=chosen:valid[rid][0]['disposition']='later_reissue'
    last={};scored=[];missing=[]
    for rid in sorted(first,key=lambda rid:(valid[rid][1],valid[rid][2],valid[rid][4])):
        row,group,start,end,issued,p=valid[rid]
        if group in last and start<last[group]:row['disposition']='overlap_excluded';continue
        last[group]=end
        if end>cutoff:row['disposition']='pending_target';continue
        seen=public.get(rid)
        if seen is None or not issued<=seen<start:row['disposition']='public_not_timely';continue
        if rid not in actual:row['disposition']='outcome_missing_at_snapshot';missing.append(rid);continue
        if rid not in verified:row['disposition']='invalid_outcome';continue
        row['disposition']='scored';scored.append(rid)
    upstream={row['id']:row for row in independent.get('rows',[])}
    if set(scored)!=set(upstream) or len(upstream)!=len(independent.get('rows',[])):
        errors.append('independent_scored_cohort_mismatch')
    for rid in set(scored)&set(upstream):
        row=valid[rid][0];other=upstream[rid]
        if any(row.get(k)!=other.get(k) for k in ('predicted','actual','correct')) or abs(row['brier_loss']-finite(other['brier_loss']))>1e-8:
            errors.append('independent_row_mismatch')
    aggregate=stats([verified[rid] for rid in scored]);groups=defaultdict(list);policies=defaultdict(list)
    for rid in scored:
        groups['|'.join(valid[rid][1])].append(rid)
        policies[str(by_id[rid].get('policy_revision') or 'legacy')+'|'+by_id[rid]['mode']].append(rid)
    per_group={}
    for name,ids in groups.items():
        metrics=stats([verified[rid] for rid in ids]);days=len({valid[rid][0]['session_day'] for rid in ids})
        minimum=(len(ids)>=120 and days>=20 and all(v['actual']>=10 for v in metrics['directions'].values()) and all(metrics['directions'][c]['calls']>=10 for c in ('down','up')))
        per_group[name]={'metrics':metrics,'market_local_days':days,'minimal_sample_gate_met':minimum}
    paired=[rid for rid in scored if 'frozen_baseline_probabilities' in by_id[rid]]
    baseline=[]
    for rid in paired:
        p=vector(by_id[rid]['frozen_baseline_probabilities'])
        baseline.append((verified[rid][0],CLASSES[max(range(3),key=lambda i:p[i])],p))
    pm=stats([verified[rid] for rid in paired]);pb=stats(baseline)
    latest={}
    for attempt in controller.get('source_attempts',[]):
        if attempt.get('observed_until'):
            g=(attempt.get('symbol'),attempt.get('mode'))
            try:
                observed = instant(attempt['observed_until'])
                generated = controller.get('generated_at')
                if observed > cutoff or (generated and instant(generated) > cutoff):
                    errors.append('collector_context_after_cutoff')
                    continue
                latest[g] = max(latest.get(g, observed), observed)
            except (TypeError,ValueError):errors.append('invalid_collector_observation_clock')
    for rid in missing:
        row=valid[rid][0];last_observed=latest.get((row['symbol'],row['mode']))
        row['missing_context']=('awaiting_later_source_observation' if last_observed and last_observed<valid[rid][3]
            else 'missing_despite_later_source_snapshot' if last_observed else 'source_progress_unknown')
    counts=dict(Counter(row['disposition'] or 'unaccounted' for row in rows))
    if counts.get('unaccounted'):errors.append('unaccounted_ledger_rows')
    if aggregate['samples']!=independent.get('scored') or aggregate['correct']!=independent.get('correct'):
        errors.append('independent_aggregate_mismatch')
    return {'version':'forecast-postvalidation-census-1.0','audit_cutoff':cutoff.isoformat(),
        'status':'integrity_errors' if errors else 'internal_arithmetic_and_accounting_consistent',
        'source_binding_verified':binding_verified,'source_binding':binding,
        'ledger_rows':len(records),'outcome_rows':len(outcomes),'verified_outcome_ids':len(verified),
        'duplicate_outcome_rows':duplicate_outcomes,'row_accounting':counts,'rows':rows,
        'observed_metrics':aggregate,'per_group':per_group,
        'groups_meeting_minimal_sample_gate':sum(v['minimal_sample_gate_met'] for v in per_group.values()),
        'by_policy_and_mode':{k:stats([verified[rid] for rid in v]) for k,v in policies.items()},
        'paired_baseline':{'model':pm,'baseline':pb,'missing_original_baseline':len(scored)-len(paired),
            'brier_gain':pb['brier_loss']-pm['brier_loss'] if paired else None,
            'log_loss_gain':pb['log_loss']-pm['log_loss'] if paired else None},
        'repeated_public_checks_without_new_id':repeated_proofs,
        'missing_context_counts':dict(Counter(valid[rid][0]['missing_context'] for rid in missing)),
        'missing_target_windows':missing_window_clusters(missing, valid),
        'errors':sorted(set(errors)),'external_exchange_prices_verified':False,
        'human_receipt_verified':False,'after_cost_usefulness_verified':False,'untouched_followup_verified':False,
        'timing_utility':'not_proven','orders_enabled':False,'new_learning_updates':0,'model_trials':0,
        'scope':'All original rows accounted; source/price arithmetic only. Missing at snapshot does not itself prove collection failure. Repeated web checks are not new forecasts or user receipts. Descriptive pooled metrics are not independent trials or per-group promotion proof.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--audit',type=Path);parser.add_argument('--output',type=Path,default=Path('stock-forecast-postvalidation-census.json'))
    args=parser.parse_args();files=['stock-forecast-ledger.jsonl','stock-forecast-outcomes.jsonl','stock-forecast-deliveries.jsonl','stock-forecast-autopilot.json']
    original={name:(args.root/name).read_bytes() for name in files}
    data=[[json.loads(line) for line in original[name].decode().splitlines() if line.strip()] for name in files[:3]]
    upstream=(args.audit or args.root/'stock-forecast-independent-audit.json').read_bytes()
    result=census(*data,json.loads(upstream),json.loads(original[files[3]]))
    result['source_sha256']={name:hashlib.sha256(raw).hexdigest() for name,raw in original.items()}
    result['upstream_audit_sha256']=hashlib.sha256(upstream).hexdigest()
    # Sharing only the output I/O guard does not share census selection or arithmetic.
    from audit_stock_forecast_independent import write_audit_report
    inputs = {args.root/name: raw for name, raw in original.items()}
    inputs[args.audit or args.root/'stock-forecast-independent-audit.json'] = upstream
    protected = [p for p in args.root.glob('stock-*') if p.is_file()
                 and p.name != 'stock-forecast-postvalidation-census.json']
    write_audit_report(result, args.output, inputs, protected)
    print(json.dumps({k:result[k] for k in ('status','ledger_rows','outcome_rows','verified_outcome_ids','row_accounting','missing_context_counts','groups_meeting_minimal_sample_gate','errors')},ensure_ascii=False))
    raise SystemExit(1 if result['errors'] else 0)

if __name__=='__main__':main()
