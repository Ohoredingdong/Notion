"""Delayed test-then-learn evaluation. Research-only; never changes strict approvals.

Only predictions published before their frozen target may teach the challenger.
Old decisions, outcomes and baselines are never recomputed from learned weights.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from copy import deepcopy
import json
import math
from pathlib import Path
import numpy as np
from stock_forecast_model import CLASSES, FEATURES, digest, stamp

VERSION = 'delayed-forward-learning-1.0'
STATE_FILE = 'stock-forecast-learning-state.json'
REPORT_FILE = 'stock-forecast-learning.json'
ATTEMPTS_FILE = 'stock-forecast-attempts.jsonl'
EVENTS_FILE = 'stock-forecast-learning-events.jsonl'
POLICY = {'minimum_paired_targets': 120, 'minimum_sessions': 20,
          'minimum_each_class': 10, 'minimum_brier_gain': .01,
          'minimum_logloss_gain': .005, 'learning_rate': .01, 'l2': .001,
          'rollback_targets': 40, 'rollback_sessions': 5,
          'confidence_filter': .70, 'research_only': True,
          'guaranteed_accuracy': None, 'automatic_orders': False,
          'promotion_is_policy_not_statistical_proof': True}
SCALES = np.array([.01,.02,.03,.04,.05,.02,.03,.05,.04,.03,.07,.07])


def lines(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []


def append_unique(path, rows):
    old = {r['id']: r for r in lines(path)}
    with path.open('a') as f:
        for r in rows:
            if r['id'] in old:
                continue
            f.write(json.dumps(r, ensure_ascii=False, allow_nan=False, separators=(',', ':'))+'\n')
            old[r['id']] = r
    return old


def probability(value):
    if not isinstance(value, dict) or set(value) != set(CLASSES):
        raise ValueError('three_class_probabilities_required')
    if any(isinstance(value[k], bool) for k in CLASSES):
        raise ValueError('boolean_probability')
    p = np.array([value[k] for k in CLASSES], dtype=float)
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any() or abs(p.sum()-1) > 1e-7:
        raise ValueError('invalid_probability_distribution')
    return p


def pdict(p):
    return {k: float(v) for k, v in zip(CLASSES, p)}


def key(r):
    return digest({k:r[k] for k in ('symbol','market','mode','target')})


def group(r):
    return '|'.join([r['symbol'], r['mode'], r.get('policy_revision','legacy')])


def features(r):
    d = r.get('feature_values', {})
    if set(d) != set(FEATURES) or any(isinstance(d[k], bool) for k in FEATURES):
        raise ValueError('frozen_features_missing')
    x = np.array([d[k] for k in FEATURES], dtype=float)
    if not np.isfinite(x).all():
        raise ValueError('nonfinite_features')
    return np.r_[1.0, np.clip(x/SCALES, -4, 4)]


def contract(r):
    try:
        p = probability(r['probabilities'])
        return bool(r['status']=='research_prediction' and
                    r['direction']==CLASSES[int(p.argmax())] and
                    stamp(r['observed_until']) <= stamp(r['received_at']) <= stamp(r['issued_at']) <
                    stamp(r['target']['start']) < stamp(r['target']['end']) and
                    math.isfinite(r['neutral_band_pct']) and r['neutral_band_pct'] > 0)
    except (KeyError, TypeError, ValueError):
        return False


def canonical(records):
    """First issuance per event, then non-overlapping windows. Never choose on truth."""
    seen, unique, invalid = set(), [], 0
    for r in sorted(records, key=lambda v:(v.get('issued_at',''),v.get('id',''))):
        if not contract(r):
            invalid += 1
            continue
        k = key(r)
        if k not in seen:
            seen.add(k); unique.append(r)
    chosen, last = [], {}
    for r in sorted(unique, key=lambda v:(v['target']['start'],v['issued_at'],v['id'])):
        g = (r['symbol'], r['mode'])
        if g in last and stamp(r['target']['start']) < last[g]:
            continue
        chosen.append(r); last[g] = stamp(r['target']['end'])
    return chosen, {'invalid_records':invalid, 'unique_events':len(unique),
                    'duplicate_issuances':len(records)-invalid-len(unique),
                    'overlap_excluded':len(unique)-len(chosen)}


def delivery_map(deliveries):
    times = {}
    for d in deliveries:
        if d.get('status') != 'public_verified':
            continue
        try:
            t = stamp(d['verified_at'])
        except (KeyError, ValueError):
            continue
        for rid in d.get('prediction_ids', []):
            if rid not in times or t < times[rid]: times[rid] = t
    return times


def joined(records, outcomes, deliveries, now):
    selected, info = canonical(records)
    actual = {v['id']:v for v in outcomes if v.get('status')=='observed'}
    public = delivery_map(deliveries)
    eligible, counts = [], Counter()
    for r in selected:
        end = stamp(r['target']['end'])
        if end > stamp(now): counts['pending_targets'] += 1; continue
        o = actual.get(r['id'])
        if not o or o.get('actual') not in CLASSES:
            counts['outcome_missing'] += 1; continue
        try:
            op, cl = float(o['target_open']), float(o['target_close'])
            ret = cl/op-1
            expected = 'up' if ret > r['neutral_band_pct']/100 else 'down' if ret < -r['neutral_band_pct']/100 else 'flat'
            if not (math.isfinite(op) and math.isfinite(cl) and op>0 and cl>0 and
                    o.get('target')==r['target'] and o['actual']==expected):
                counts['invalid_outcome_value'] += 1; continue
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            counts['invalid_outcome_value'] += 1; continue
        try:
            available = stamp(o['evaluated_at'])
            if not end <= available <= stamp(now):
                counts['invalid_outcome_time'] += 1; continue
        except (KeyError, ValueError):
            counts['invalid_outcome_time'] += 1; continue
        d = public.get(r['id'])
        if d is None or not stamp(r['issued_at']) <= d < stamp(r['target']['start']):
            counts['not_publicly_timely'] += 1; continue
        eligible.append((r,o))
    info.update(counts); info['independent_targets'] = len(selected)
    info['eligible_scored'] = len(eligible)
    return eligible, info


def loss(p, y):
    a = np.eye(3)[y]
    return float(np.sum((p-a)**2)), float(-np.log(max(float(p[y]),1e-12)))


def wilson(correct, n):
    if not n: return None
    z=1.95996398454; a=correct/n; den=1+z*z/n
    mid=(a+z*z/(2*n))/den
    half=z*math.sqrt(a*(1-a)/n+z*z/(4*n*n))/den
    return [max(0,mid-half),min(1,mid+half)]


def statistics(pairs, field='probabilities'):
    rows=[]
    for r,o in pairs:
        source = r.get(field)
        if source is None: continue
        try: p=probability(source)
        except (ValueError, TypeError): continue
        y=CLASSES.index(o['actual']); pred=int(p.argmax()); b,ll=loss(p,y)
        rows.append((r,o,p,y,pred,b,ll))
    n=len(rows)
    if not n: return {'samples':0,'accuracy':None,'correct':0,'wilson_95_interval':None}
    successes=sum(v[3]==v[4] for v in rows)
    recalls={k: float(np.mean([v[4]==i for v in rows if v[3]==i])) if any(v[3]==i for v in rows) else None
             for i,k in enumerate(CLASSES)}
    reliability=[]
    for lo in (0,.4,.5,.6,.7,.8,.9):
        hi = .4 if lo==0 else min(1,lo+.1)
        bucket=[v for v in rows if lo<=v[2].max() and (v[2].max()<hi or (hi==1 and v[2].max()==1))]
        if bucket: reliability.append({'from':lo,'to':hi,'samples':len(bucket),
                'mean_confidence':float(np.mean([v[2].max() for v in bucket])),
                'accuracy':float(np.mean([v[3]==v[4] for v in bucket]))})
    ece=sum(v['samples']/n*abs(v['mean_confidence']-v['accuracy']) for v in reliability)
    confident=[v for v in rows if v[2].max()>=POLICY['confidence_filter']]
    # Day-cluster diagnostic, unlike a misleading i.i.d. interval alone.
    days=defaultdict(list)
    for v in rows: days[v[0]['target']['start'][:10]].append(float(v[3]==v[4]))
    daily=[np.mean(v) for v in days.values()]
    ci=None
    if len(daily)>=5:
        rng=np.random.default_rng(61129)
        b=rng.choice(daily,size=(2000,len(daily)),replace=True).mean(axis=1)
        ci=[float(v) for v in np.quantile(b,[.025,.975])]
    return {'samples':n,'correct':successes,'accuracy':successes/n,
            'wilson_95_interval':wilson(successes,n), 'calendar_days':len(days),
            'day_weighted_accuracy':float(np.mean(daily)), 'day_cluster_95_interval':ci,
            'interval_note':'Wilson assumes independent trials; day bootstrap is diagnostic, not proof against market dependence.',
            'balanced_accuracy':float(np.mean(list(recalls.values()))) if all(v is not None for v in recalls.values()) else None,
            'recall':recalls,'confusion_matrix':[[sum(v[3]==i and v[4]==j for v in rows) for j in range(3)] for i in range(3)],
            'brier_loss':float(np.mean([v[5] for v in rows])), 'log_loss':float(np.mean([v[6] for v in rows])),
            'calibration_error':ece,'reliability':reliability,
            'high_confidence':{'threshold':POLICY['confidence_filter'],'samples':len(confident),
                'coverage':len(confident)/n,'accuracy':float(np.mean([v[3]==v[4] for v in confident])) if confident else None}}


def blank_state():
    return {'version':VERSION,'revision':0,'updated_at':None,'groups':{},'trained_events':[],
            'training_updates':0,'last_outcome_available_at':None,'parent_sha256':None}


def load_state(root):
    p=root/STATE_FILE
    if not p.exists(): return blank_state(), None
    state=json.loads(p.read_text())
    if state.get('version')!=VERSION: raise ValueError('learning_state_version_mismatch')
    for g in state.get('groups',{}).values():
        w=np.asarray(g['weights'],dtype=float)
        if w.shape!=(3,len(FEATURES)+1) or not np.isfinite(w).all():
            raise ValueError('learning_state_corrupt')
    return state,digest(state)


def ensure(state, r):
    g=group(r)
    if g not in state['groups']:
        state['groups'][g]={'weights':np.zeros((3,len(FEATURES)+1)).tolist(),
                           'learned':0,'active':'incumbent','last_train_end':None,
                           'last_gate_end':None,'gate_checks':0,'promotions':0,'rollbacks':0}
    return state['groups'][g]


def adaptive(base, x, weights):
    correction=np.clip(np.asarray(weights)@x,-2,2)
    z=np.log(np.clip(base,1e-9,1))+correction
    z-=z.max(); e=np.exp(z); return e/e.sum()


def learn(state, pairs, now):
    """Score was frozen first. Only matured, timely, not-yet-learned events update."""
    done=set(state['trained_events']); events=[]
    for r,o in sorted(pairs,key=lambda v:(v[1]['evaluated_at'],v[0]['target']['end'])):
        event_key=key(r)
        if event_key in done: continue
        if stamp(o['evaluated_at'])>stamp(now) or stamp(r['target']['end'])>stamp(now): continue
        try:
            x=features(r)
            base=probability((r.get('online_learning') or {}).get('incumbent_probabilities',r['probabilities']))
        except (KeyError,ValueError,TypeError): continue
        s=ensure(state,r)
        if s['last_train_end'] and stamp(r['target']['start'])<stamp(s['last_train_end']): continue
        w=np.asarray(s['weights']); p=adaptive(base,x,w); y=CLASSES.index(o['actual'])
        before=digest(s['weights'])
        rate=POLICY['learning_rate']/math.sqrt(1+s['learned']/200)
        gradient=np.outer(p-np.eye(3)[y],x)+POLICY['l2']*w
        w=np.clip(w-rate*gradient,-1,1);w-=w.mean(axis=0)
        s.update(weights=w.tolist(),learned=s['learned']+1,last_train_end=r['target']['end'])
        done.add(event_key);state['training_updates']+=1
        state['last_outcome_available_at']=max(state.get('last_outcome_available_at') or '',o['evaluated_at'])
        event={'kind':'learn_after_score','prediction_id':r['id'],'event_key':event_key,
               'available_at':o['evaluated_at'],'learned_at':stamp(now).isoformat(),
               'group':group(r),'actual':o['actual'],'weights_before':before,
               'weights_after':digest(s['weights']),'not_rescored':True}
        event['id']=digest({'version':VERSION,'trained_event':event_key})
        events.append(event)
    state['trained_events']=sorted(done)
    return events


def comparison(pairs):
    rows=[]
    for r,o in pairs:
        v=r.get('online_learning') or {}
        if v.get('version')!=VERSION: continue
        try: a=probability(v['incumbent_probabilities']);b=probability(v['challenger_probabilities'])
        except (KeyError,ValueError,TypeError): continue
        y=CLASSES.index(o['actual']); la,lla=loss(a,y);lb,llb=loss(b,y)
        rows.append((r,o,la-lb,lla-llb,int(b.argmax()==y)-int(a.argmax()==y)))
    daily=defaultdict(list)
    for r,o,edge,_,_ in rows: daily[r['target']['start'][:10]].append(edge)
    ci=None
    if len(daily)>=5:
        means=np.array([np.mean(v) for v in daily.values()]);rng=np.random.default_rng(51029)
        draws=rng.choice(means,size=(3000,len(means)),replace=True).mean(axis=1)
        ci=[float(v) for v in np.quantile(draws,[.025,.975])]
    return {'samples':len(rows),'sessions':len(daily),
            'class_counts':dict(Counter(o['actual'] for _,o,*_ in rows)),
            'brier_gain':float(np.mean([v[2] for v in rows])) if rows else None,
            'logloss_gain':float(np.mean([v[3] for v in rows])) if rows else None,
            'accuracy_gain':float(np.mean([v[4] for v in rows])) if rows else None,
            'day_cluster_brier_gain_95_interval':ci,
            'is_live_trading_proof':False}


def select_variant(state,pairs,now):
    """Predeclared block checkpoints, not continuous fitting to a holdout score."""
    groups=defaultdict(list);events=[]
    for r,o in pairs:
        if (r.get('online_learning') or {}).get('version')==VERSION: groups[group(r)].append((r,o))
    for name,pool in groups.items():
        s=ensure(state,pool[0][0]); cursor=s.get('last_gate_end')
        rows=sorted([v for v in pool if not cursor or stamp(v[0]['target']['start'])>=stamp(cursor)],
                    key=lambda v:v[0]['target']['start'])
        rollback=s['active']=='adaptive'
        n=POLICY['rollback_targets'] if rollback else POLICY['minimum_paired_targets']
        sessions=POLICY['rollback_sessions'] if rollback else POLICY['minimum_sessions']
        if len(rows)<n: continue
        # Extend the fixed prefix until the session minimum is reached.
        while n < len(rows) and len({v[0]['target']['start'][:10] for v in rows[:n]}) < sessions:
            n += 1
        c=comparison(rows[:n])
        if c['sessions']<sessions: continue
        ci=c['day_cluster_brier_gain_95_interval']; counts=c['class_counts']
        promote=bool(not rollback and ci and ci[0]>0 and c['brier_gain']>POLICY['minimum_brier_gain'] and
                     c['logloss_gain']>POLICY['minimum_logloss_gain'] and c['accuracy_gain']>0 and
                     all(counts.get(k,0)>=POLICY['minimum_each_class'] for k in CLASSES))
        demote=bool(rollback and c['brier_gain']<-.01 and c['logloss_gain']<-.005)
        old=s['active']
        if promote: s['active']='adaptive';s['promotions']+=1
        if demote: s['active']='incumbent';s['rollbacks']+=1
        s['last_gate_end']=rows[n-1][0]['target']['end'];s['gate_checks']+=1
        event={'kind':'rollback' if demote else 'research_promotion' if promote else 'checkpoint_no_change',
               'group':name,'evaluated_at':stamp(now).isoformat(),'old':old,'new':s['active'],
               'comparison':c,'checkpoint_end':s['last_gate_end'],'policy_not_proof':True,
               'strict_green_override':False,'orders_enabled':False}
        event['id']=digest(event);events.append(event)
    return events


def augment(record,state,now):
    if record.get('status')!='research_prediction': return record
    r=deepcopy(record);s=ensure(state,r);x=features(r);base=probability(r['probabilities'])
    challenger=adaptive(base,x,s['weights']);chosen=challenger if s['active']=='adaptive' else base
    issued=stamp(now)
    if issued>=stamp(r['target']['start']):
        return {**r,'status':'no_call','reason':'learning_finished_after_target_start','probabilities':None,'direction':None}
    if state['last_outcome_available_at'] and stamp(state['last_outcome_available_at'])>issued:
        raise ValueError('future_label_in_learning_state')
    r['issued_at']=issued.isoformat()
    r['online_learning']={'version':VERSION,'active_variant':s['active'],
                         'learned_before_issuance':s['learned'],
                         'weights_sha256':digest(s['weights']),
                         'label_available_through':state['last_outcome_available_at'],
                         'incumbent_probabilities':pdict(base),'challenger_probabilities':pdict(challenger),
                         'challenger_calibration':'not_yet_forward_validated','trading_enabled':False}
    r['probabilities']=pdict(chosen);r['direction']=CLASSES[int(chosen.argmax())]
    r['id']=digest({'event':key(r),'policy':r.get('policy_revision'),
                    'base_model':r['model_sha256'],'online':r['online_learning']})
    return r


def report(records,outcomes,deliveries,attempts,state,events,now):
    pairs,counts=joined(records,outcomes,deliveries,now)
    overall=statistics(pairs)
    paired=[v for v in pairs if v[0].get('frozen_baseline_probabilities') is not None]
    bygroup={}
    for g in sorted({group(r) for r,o in pairs}):
        subset=[v for v in pairs if group(v[0])==g]
        bygroup[g]={'metrics':statistics(subset),'comparison':comparison(subset),
                    'learning':{k:v for k,v in state['groups'].get(g,{}).items() if k!='weights'}}
    valid_attempts=[a for a in attempts if a.get('version')==VERSION]
    attempted=len(valid_attempts); called=sum(a.get('status')=='research_prediction' for a in valid_attempts)
    result={'version':VERSION,'generated_at':stamp(now).isoformat(),'policy':POLICY,
            'status':'forward_validation_in_progress','real_time_connected':False,
            'refresh_mode':'scheduled_best_effort_not_realtime',
            'observations_available_through':max((o['evaluated_at'] for r,o in pairs),default=None),
            'recorded_predictions':len(records),'evaluation_counts':counts,'overall':overall,
            'baseline_paired':{'samples':len(paired),'model':statistics(paired),
                               'baseline':statistics(paired,'frozen_baseline_probabilities'),
                               'legacy_baseline_not_backfilled':True},
            'coverage':{'attempts':attempted,'prediction_attempts':called,'no_calls':attempted-called,
                        'call_rate':called/attempted if attempted else None,
                        'definition':'scheduler-attempt coverage, not whole-market coverage',
                        'no_call_reasons':dict(Counter(a.get('reason') for a in valid_attempts if a.get('status')!='research_prediction'))},
            'learning':{'training_updates':state['training_updates'],'state_revision':state['revision'],
                        'adaptive_groups':sum(s['active']=='adaptive' for s in state['groups'].values()),
                        'promotions':sum(s['promotions'] for s in state['groups'].values()),
                        'rollbacks':sum(s['rollbacks'] for s in state['groups'].values()),
                        'fresh_events':events[-8:]},'groups':bygroup,
            'human_push_receipt_verified':False,'live_profitability_proven':False,
            'accuracy_target_is_not_a_guarantee':True,
            'limitations':['타깃 시작 전 공개 확인된 예측만 주 성적에 포함',
                '공개 웹페이지 확인은 사용자 푸시 수신 확인이 아님',
                '단일 제공처 사후 가격 관찰이며 체결·비용 후 수익률이 아님',
                '하루 안의 종목·구간 간 상관 및 반복 모델 비교가 있어 통계적 우위 보장 아님',
                '적중률·표본수·보류율·기준모델·확률오차를 함께 평가; 100% 보장 없음']}
    return result
