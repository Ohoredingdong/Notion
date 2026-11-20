"""Reject incomplete replacement of a previous identity-bound research snapshot."""
from datetime import date
from math import isfinite


class SnapshotRegression(ValueError):
    pass


def _rows(doc):
    out = {}
    values = doc.get('companies')
    if not isinstance(values, list):
        raise SnapshotRegression('missing_company_list')
    for row in values:
        if not isinstance(row, dict):
            raise SnapshotRegression('malformed_company')
        key = (row.get('market'), row.get('symbol'))
        if not all(isinstance(k, str) and k for k in key) or key in out:
            raise SnapshotRegression('missing_or_ambiguous_symbol')
        out[key] = row
    return out


def _accepted(row):
    if not row:
        return None
    s = row.get('price_session')
    try:
        if not isinstance(s, str) or date.fromisoformat(s).isoformat() != s:
            return None
    except ValueError:
        return None
    val = row.get('price')
    if type(val) not in (int, float) or not isfinite(val) or val <= 0:
        return None
    source = row.get('price_source') or {}
    integrity = row.get('price_integrity') or {}
    if not isinstance(source, dict) or not isinstance(integrity, dict):
        return None
    identity = (row.get('source_symbol'), row.get('currency'))
    if (not all(identity) or row.get('status') != 'current' or
        source.get('source_identity_verified') is not True or
        source.get('market') != row.get('market') or
        (source.get('provider_symbol'), source.get('currency')) != identity or
        source.get('expected_session') != s or source.get('latest_completed_session') != s or
        integrity.get('completed_session_match') is not True or
        integrity.get('expected_session') != s or integrity.get('price_session') != s):
        return None
    return s, identity


def stable_universe_keys(manifest):
    """Validate fixed positions from the same official collector input."""
    positions = manifest.get('companies')
    if not isinstance(positions, list) or not positions:
        raise SnapshotRegression('missing_stable_universe')
    result = set()
    for row in positions:
        if (not isinstance(row, list) or len(row) < 5 or
            not all(isinstance(row[i], str) and row[i] for i in (0, 2, 4))):
            raise SnapshotRegression('malformed_stable_universe_position')
        key = (row[2], row[0])
        if key in result:
            raise SnapshotRegression('ambiguous_stable_universe_position')
        result.add(key)
    return result


def guard_completed_closes(previous, candidate, *, stable_keys):
    """Use comparable row evidence, not a global version/manifest equality test.

    Dynamic discovery churn is allowed if an old row is no longer selected.
    An overlapping market/ticker is protected regardless of cohort or version.
    A differently mapped issuer/currency is ambiguous; don't guess a match.
    """
    new = _rows(candidate)
    if previous is None:
        return {'protected': 0, 'first_recovery': True, 'discovery_exits': 0}
    old = {k: p for k, r in _rows(previous).items() if (p := _accepted(r))}
    if not old:
        return {'protected': 0, 'first_recovery': True, 'discovery_exits': 0}
    issues = []
    protected = discovery_exits = 0
    for key, (session, identity) in sorted(old.items()):
        row = new.get(key)
        if row is None and key not in stable_keys:
            discovery_exits += 1
            continue
        protected += 1
        if row is None:
            reason = 'missing_previously_accepted_stable_symbol'
        elif (accepted := _accepted(row)) is None:
            reason = 'downgraded_close_evidence'
        elif accepted[1] != identity:
            reason = 'issuer_or_currency_changed_review_required'
        elif accepted[0] < session:
            reason = 'completed_close_regressed'
        else:
            continue
        issues.append(f'{key[0]}:{key[1]}:{reason}')
    if issues:
        raise SnapshotRegression(f'{len(issues)} per-symbol close regressions: '+', '.join(issues[:15]))
    return {'protected': protected, 'first_recovery': False, 'discovery_exits': discovery_exits}
