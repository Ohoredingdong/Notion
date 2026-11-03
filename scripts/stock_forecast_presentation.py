"""Select already public, originally frozen pending research signals for display only.

Never issues, scores, learns, or converts a no-call into a new prediction.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math


def _clock(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    else:
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else None


def prior_public_forecasts(ledger, deliveries, current_records, as_of):
    """One nonexpired earlier public forecast per exact market/symbol/mode.

    Inputs are frozen evidence. as_of is the generation time. Only a
    separately archived pre-target PUBLIC HTTP check qualifies; never a
    user-push receipt or proof of tradability. Current issue rows are retained.
    """
    cutoff = _clock(as_of)
    if cutoff is None:
        raise ValueError('as_of_requires_offset_aware_time')
    proofs = {}
    for proof in deliveries:
        if proof.get('status') != 'public_verified':
            continue
        published = _clock(proof.get('verified_at'))
        snapshot = _clock(proof.get('snapshot_generated_at'))
        if published is None or snapshot is None or snapshot > published:
            continue
        for identifier in proof.get('prediction_ids') or []:
            if isinstance(identifier, str) and identifier:
                proofs.setdefault(identifier, []).append((published, snapshot))

    current_ids = {r.get('id') for r in current_records
                   if r.get('status') == 'research_prediction' and r.get('id')}
    first_by_target = {}
    for r in ledger:
        if r.get('status') != 'research_prediction' or not r.get('id'):
            continue
        key = (r.get('symbol'), r.get('market'), r.get('mode'),
               (r.get('target') or {}).get('start'), (r.get('target') or {}).get('end'))
        if not all(key) or key[1] not in ('KR', 'US') or key[2] not in ('daily', 'intraday'):
            continue
        previous = first_by_target.get(key)
        if previous is None or str(r.get('issued_at', '')) < str(previous.get('issued_at', '')):
            first_by_target[key] = r

    chosen = {}
    for key, r in first_by_target.items():
        if r['id'] in current_ids or r.get('recommendation') is True or r.get('strict_green_override') is True:
            continue
        observed, received, issued = (_clock(r.get(k)) for k in
                                      ('observed_until', 'received_at', 'issued_at'))
        start = _clock(r['target']['start'])
        end = _clock(r['target']['end'])
        if any(v is None for v in (observed, received, issued, start, end)):
            continue
        if not (observed <= received <= issued < start < end and issued <= cutoff < end):
            continue
        probs = r.get('probabilities')
        if not isinstance(probs, dict) or r.get('direction') not in ('up', 'down', 'flat'):
            continue
        if any(type(probs.get(k)) not in (int, float) or not math.isfinite(probs[k]) or not 0 <= probs[k] <= 1
               for k in ('up', 'down', 'flat')):
            continue
        if abs(sum(probs[k] for k in ('up', 'down', 'flat')) - 1) > 1e-5:
            continue
        allowed = [(pub, snap) for pub, snap in proofs.get(r['id'], ())
                   if issued <= snap <= pub <= cutoff and pub <= start]
        if not allowed:
            continue
        verified_at = min(allowed)[0]
        group = (r['symbol'], r['market'], r['mode'])
        order = (start, issued, str(r['id']))
        if group in chosen and chosen[group][0] <= order:
            continue
        fields = ('id', 'symbol', 'market', 'mode', 'status', 'direction',
                  'issued_at', 'received_at', 'observed_until', 'neutral_band_pct',
                  'source_run_id', 'provider_is_official_exchange', 'policy_revision')
        display = {k: r[k] for k in fields if k in r}
        display['probabilities'] = {k: probs[k] for k in ('down', 'flat', 'up')}
        display['target'] = {'start': r['target']['start'], 'end': r['target']['end']}
        display.update(display_origin='earlier_public_frozen_record',
                       public_verified_at=verified_at.isoformat(),
                       user_receipt_verified=False,
                       recommendation=False, strict_green_override=False)
        chosen[group] = (order, display)
    return [chosen[k][1] for k in sorted(chosen)]
