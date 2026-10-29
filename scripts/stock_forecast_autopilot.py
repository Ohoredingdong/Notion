"""Executable bounded research loop, staged writes and fail-closed promotion.

This is autonomous parameter/model experimentation within a reviewed catalogue,
not arbitrary self-writing code, continuous streaming, or guaranteed prediction.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time

VERSION = 'bounded-autopilot-1.0'
REPORT = 'stock-forecast-autopilot.json'
EVENTS = 'stock-forecast-autopilot-events.jsonl'
SOURCES = 'stock-forecast-source-state.json'
CORE_OUTPUTS = ('stock-direction-forecast.json','stock-forecast-ledger.jsonl',
                'stock-forecast-outcomes.jsonl','stock-forecast-deliveries.jsonl',
                'stock-forecast-learning-state.json','stock-forecast-learning.json',
                'stock-forecast-attempts.jsonl','stock-forecast-learning-events.jsonl')
OUTPUTS = CORE_OUTPUTS + (REPORT, EVENTS, SOURCES)
POLICY = {'version':VERSION, 'maximum_source_attempts':2,
          'rate_limit_cooldown_minutes':15, 'maximum_new_recipe_families':1,
          'allowed_variants':['adaptive','balanced_linear','balanced_nonlinear','movement_then_direction'],
          'arbitrary_source_rewrite':False, 'live_orders':False,
          'change_existing_approvals':False, 'perfection_guaranteed':False}
UTC=timezone.utc

def now(): return datetime.now(UTC)
def ts(s):
    t=datetime.fromisoformat(str(s).replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('timezone_required')
    return t.astimezone(UTC)
def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
def read(root,name,default):
    p=root/name
    return json.loads(p.read_text()) if p.exists() else deepcopy(default)
def lines(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
def write(p,x):
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def append_once(p,event):
    previous=lines(p)
    if any(v.get('id')==event['id'] for v in previous): return False
    with p.open('a') as f: f.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+'\n')
    return True

def preserve_records(old,new):
    def indexed(rows):
        out={}
        for r in rows:
            k=r.get('id') or r.get('verification_id')
            if not k: raise ValueError('immutable_row_id_missing')
            if k in out and out[k]!=r: raise ValueError('conflicting_immutable_id')
            out[k]=r
        return out
    a,b=indexed(old),indexed(new)
    if any(k not in b or b[k]!=v for k,v in a.items()):
        raise ValueError('original_evidence_was_changed_or_deleted')

def source_failure(record):
    reason=str(record.get('reason') or '')
    kind=reason.split(':',1)[0]
    if 'RateLimit' in kind or 'rate_limit_cooldown' in reason: return 'rate_limit'
    if any(x in kind for x in ('Timeout','Connection','URLError')): return 'transient_network'
    if kind=='OperationalError' and 'locked' in reason.lower(): return 'cache_lock'
    if record.get('status')=='no_call' and ':' in reason: return 'nontransient'
    return None

class SafeCollector:
    def __init__(self, process, state, clock=now, sleep=time.sleep):
        self.process,self.state,self.clock,self.sleep=process,state,clock,sleep
        self.events=[];self.lock=threading.Lock()
    def __call__(self,spec,mode):
        symbol,name,market=spec; key=symbol+'|'+mode
        with self.lock: cooldown=self.state.get('cooldowns',{}).get(key)
        if cooldown and ts(cooldown)>self.clock():
            r={'symbol':symbol,'name':name,'market':market,'mode':mode,'status':'no_call',
               'reason':'rate_limit_cooldown','issued_at':self.clock().isoformat(),
               'probabilities':None,'direction':None,'recommendation':False}
            with self.lock: self.events.append({'symbol':symbol,'mode':mode,'attempt':0,'result':'rate_limit','history_received':False})
            return r,None
        for attempt in range(1,POLICY['maximum_source_attempts']+1):
            r,bars=self.process(spec,mode)
            failure=source_failure(r)
            with self.lock:
                self.events.append({'symbol':symbol,'mode':mode,'attempt':attempt,
                    'result':failure or 'response_received','history_received':bars is not None,
                    'observed_until':r.get('observed_until'),'received_at':r.get('received_at')})
                if failure=='rate_limit':
                    self.state.setdefault('cooldowns',{})[key]=(self.clock()+timedelta(minutes=15)).isoformat()
                elif bars is not None:
                    self.state.setdefault('cooldowns',{}).pop(key,None)
            if failure not in ('transient_network','cache_lock') or attempt==POLICY['maximum_source_attempts']:
                return r,bars
            self.sleep(attempt*2)
        raise RuntimeError('unreachable_collector_state')

def diagnose(evaluation,collector_events):
    reasons=[]; quality=evaluation.get('directional_research',{}).get('actual_direction_quality',{})
    if quality.get('single_class_collapse'): reasons.append('single_direction_collapse')
    for name in ('up','down'):
        m=quality.get('directions',{}).get(name,{})
        if not m.get('actual'): reasons.append('no_forward_'+name+'_samples')
        elif (m.get('recall') or 0)<.5: reasons.append('missed_'+name+'_moves')
    if any(v['result']=='rate_limit' for v in collector_events): reasons.append('provider_cooldown_active')
    if any(v['attempt']>1 for v in collector_events): reasons.append('transient_source_retry_used')
    return reasons

def verify_stage(root,stage,cutoff):
    from audit_stock_forecast_independent import audit
    import stock_forecast_learning as learning
    for name in OUTPUTS:
        if name.endswith('.jsonl'): preserve_records(lines(root/name),lines(stage/name))
    records=lines(stage/'stock-forecast-ledger.jsonl')
    outcomes=lines(stage/'stock-forecast-outcomes.jsonl')
    deliveries=lines(stage/'stock-forecast-deliveries.jsonl')
    check=audit(records,outcomes,deliveries,cutoff)
    if check['errors']: raise ValueError('independent_audit_rejected_staged_results')
    prior=read(root,'stock-forecast-learning-state.json',learning.blank_state())
    current=read(stage,'stock-forecast-learning-state.json',learning.blank_state())
    old=set(prior['trained_events']);new=current['trained_events']
    if len(new)!=len(set(new)) or not old.issubset(set(new)):
        raise ValueError('learning_history_was_rewritten')
    pairs,_=learning.joined(records,outcomes,deliveries,cutoff)
    available={learning.key(r) for r,o in pairs}
    if not (set(new)-old).issubset(available):
        raise ValueError('learned_unavailable_or_unpublished_answer')
    if current['training_updates']-prior['training_updates']!=len(set(new)-old):
        raise ValueError('duplicate_learning_update')
    output=read(stage,'stock-direction-forecast.json',{})
    for r in output.get('records',[]):
        if r.get('recommendation') is True or r.get('strict_green_override') is True:
            raise ValueError('research_cannot_enable_buy_approval')
    summary=read(stage,'stock-forecast-learning.json',{}).get('overall',{})
    if summary.get('samples')!=check['scored'] or summary.get('correct')!=check['correct']:
        raise ValueError('model_summary_disagrees_with_independent_audit')
    return check

def run(root=Path('.'),pipeline=None,clock=now):
    import run_stock_forecasts as original
    from stock_forecast_cascade import RECIPE
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    start=clock();run_id=str(os.environ.get('GITHUB_RUN_ID') or start.isoformat())
    source_state=read(root,SOURCES,{'version':VERSION,'cooldowns':{}})
    before={name:hashlib.sha256((root/name).read_bytes()).hexdigest() if (root/name).exists() else None
            for name in OUTPUTS}
    original_count=len(lines(root/'stock-forecast-ledger.jsonl'))
    old_updates=read(root,'stock-forecast-learning-state.json',{'training_updates':0})['training_updates']
    try:
        with tempfile.TemporaryDirectory(prefix='forecast-transaction-') as temp:
            stage=Path(temp)
            for name in OUTPUTS:
                if (root/name).exists():shutil.copy2(root/name,stage/name)
            manifest={'kind':'preregistered_recipe','version':VERSION,'recipe':RECIPE,
                      'created_at':start.isoformat(),'effective_from':start.isoformat(),
                      'promotion_rule':'existing prospective directional gates; no historical score promotion',
                      'recipe_family_budget':1,'outcomes_not_read_for_recipe_parameters':True}
            manifest['id']=digest({'kind':manifest['kind'],'version':VERSION,'recipe':RECIPE})
            append_once(stage/EVENTS,manifest)
            collector=SafeCollector(original.process,source_state,clock=clock)
            engine=pipeline or original.run
            engine(root=stage,processor=collector)
            check=verify_stage(root,stage,clock())
            evaluation=read(stage,'stock-forecast-learning.json',{})
            collected={(v['symbol'],v['mode']) for v in collector.events if v['history_received']}
            if not collected: raise RuntimeError('all_collectors_failed; previous_success_is_not_current_success')
            new_count=len(lines(stage/'stock-forecast-ledger.jsonl'))-original_count
            updates=evaluation.get('learning',{}).get('training_updates',0)-old_updates
            report={'version':VERSION,'generated_at':clock().isoformat(),'run_id':run_id,
                    'source_commit':os.environ.get('GITHUB_SHA'),
                    'status':'research_cycle_verified','policy':POLICY,
                    'source_state':'received_real_history','collected_groups':len(collected),
                    'source_attempts':collector.events,'diagnosis':diagnose(evaluation,collector.events),
                    'new_frozen_predictions':new_count,'new_learning_updates':updates,
                    'independent_audit':{'status':check['status'],'samples':check['scored'],
                        'correct':check['correct'],'externally_verified_candles':False},
                    'candidate_catalogue':POLICY['allowed_variants'],
                    'recipe_sha256':manifest['id'],'immutable_evidence_preserved':True,
                    'learning_after_observed_outcome_verified':True,
                    'promotions':evaluation.get('learning',{}).get('promotions',0),
                    'rollbacks':evaluation.get('learning',{}).get('rollbacks',0),
                    'timing_utility':{'status':'not_proven','automatic_completion_notice':False,
                        'blockers':['prospective_directional_edge_requires_more_evidence',
                                    'independent_executable_quotes_and_delivery_not_connected',
                                    'cost_after_execution_and_untouched_followup_not_validated']},
                    'continuous_realtime':False,'orders_enabled':False,
                    'perfect_prediction_proven':False,
                    'scope':'Bounded automatic research and recovery; not unrestricted code self-modification'}
            write(stage/REPORT,report)
            source_state['updated_at']=clock().isoformat();write(stage/SOURCES,source_state)
            event={'id':digest({'run':run_id,'attempt':os.environ.get('GITHUB_RUN_ATTEMPT','1'),'version':VERSION}),
                   'kind':'verified_research_cycle','recorded_at':clock().isoformat(),
                   'new_predictions':new_count,'new_learning_updates':updates,
                   'source_snapshot':digest(before),'recipe_sha256':manifest['id']}
            append_once(stage/EVENTS,event)
            for name,sha in before.items():
                current=hashlib.sha256((root/name).read_bytes()).hexdigest() if (root/name).exists() else None
                if current!=sha: raise RuntimeError('working_snapshot_changed; refusing_overwrite')
            for name in OUTPUTS:
                if (stage/name).exists(): shutil.copy2(stage/name,root/name)
            print(json.dumps({k:report[k] for k in ('status','collected_groups','new_frozen_predictions','new_learning_updates','diagnosis')},ensure_ascii=False))
            return report
    except Exception as exc:
        report={'version':VERSION,'generated_at':clock().isoformat(),'run_id':run_id,
                'status':'cycle_rejected','error_type':type(exc).__name__,
                'reason':str(exc).split('https:')[0][:160],
                'previous_evidence_preserved':True,'timing_utility':{'status':'not_proven'},
                'orders_enabled':False,'perfect_prediction_proven':False}
        write(root/REPORT,report)
        raise

if __name__=='__main__': run()
