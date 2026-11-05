"""Offline regressions for completed bars, health coverage and atomic audit publication."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from market_data_utils import completed_daily_points, market_session_clock, utc_stamp
import audit_stock_radar_accuracy as accuracy
import publish_stock_radar_audit as publisher
import publish_widget_data as widget_publisher
from verify_stock_canonical_pipeline import verify_canonical

spec = importlib.util.spec_from_file_location('radar_health', SCRIPTS / 'monitor-stock-value-radar.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)
UTC = timezone.utc
NOW = datetime(2026, 11, 5, 10, tzinfo=UTC)


class Calendar:
    """Explicit session fixtures, including a weekend/holiday gap and short day."""
    def __init__(self, market='KR', rows=None):
        days = ('2026-11-03', '2026-11-04', '2026-11-05', '2026-11-06', '2026-11-09', '2026-11-10')
        self.rows = rows or {day: (day + ('T00:00:00+00:00' if market == 'KR' else 'T14:30:00+00:00'),
                                   day + ('T06:30:00+00:00' if market == 'KR' else 'T21:00:00+00:00')) for day in days}
        self.days = sorted(self.rows)

    def date_to_session(self, day, direction='previous'):
        return max(value for value in self.days if value <= str(day)[:10])

    def previous_session(self, day):
        return self.days[self.days.index(day) - 1]

    def next_session(self, day):
        return self.days[self.days.index(day) + 1]

    def session_open(self, day):
        return utc_stamp(self.rows[day][0])

    def session_close(self, day):
        return utc_stamp(self.rows[day][1])

    def is_session(self, day):
        return day in self.rows


def clock(market, now, delay_minutes=30):
    return market_session_clock(market, now, delay_minutes, Calendar(market))


def write(root, name, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False) + '\n')


def health_fixture(root, now=NOW, source_at=None):
    stamp = (source_at or now).isoformat()
    raw = {'generated_at': stamp, 'companies': []}
    charts = {'generated_at': stamp, 'source_generated_at': stamp, 'series': {}}
    macro = {'generated_at': stamp, 'indicators': {}}
    for symbol, market in (('005930', 'KR'), ('AAPL', 'US')):
        date = clock(market, now)['expected_session']
        raw['companies'].append({'symbol': symbol, 'market': market, 'price_session': date, 'price': 100, 'collected_at': stamp})
    for symbol, market in {**{r['symbol']: r['market'] for r in raw['companies']}, **health.INDEX_MARKETS}.items():
        date = clock(market, now)['expected_session']
        charts['series'][symbol] = {'status': 'ok', 'price_session': date, 'collected_at': stamp, 'bars': [{'date': date, 'close': 100}]}
    for key, market in health.MACRO_MARKETS.items():
        macro['indicators'][key] = {'date': clock(market, now)['expected_session'], 'value': 100, 'collected_at': stamp, 'price_basis': 'completed_regular_session_close'}
    calls = []
    for row in raw['companies']:
        timing = clock(row['market'], now)
        calls.append({'symbol': row['symbol'], 'market': row['market'], 'status': 'research_prediction',
                      'issued_at': stamp, 'target': {'start': timing['next_open'], 'end': timing['next_close']},
                      'probabilities': {'down': .3, 'flat': .4, 'up': .3}})
    data = {
        'opportunity': raw, 'charts': charts, 'market': macro,
        'cases': {'generated_at': stamp, 'source_generated_at': stamp},
        'entry': {'generated_at': stamp, 'source_generated_at': stamp},
        'forecast': {'generated_at': stamp, 'records': calls},
        'learning': {'generated_at': stamp}, 'news': {'generated_at': now.isoformat()},
        'calendar': {'generated_at': now.isoformat(), 'stale': False},
        'events': {'generated_at': now.isoformat(), 'calendar_fresh': True, 'source_calendar_generated_at': now.isoformat()},
        'accuracy': {'source': {key: stamp for key in ('forecasts_generated_at', 'learning_generated_at',
                        'opportunity_generated_at', 'chart_generated_at', 'market_generated_at')},
                     'data_integrity': {'check_passed': True}},
    }
    for key, value in data.items():
        write(root, health.FILES[key], value)
    return data


def audit_fixture(root, stamp='2026-11-05T08:00:00+00:00'):
    overall = {'samples': 3, 'correct': 1, 'accuracy': 1/3, 'confusion_matrix': [[1, 0, 0], [1, 0, 0], [1, 0, 0]],
               'balanced_accuracy': 1/3, 'recall': {'down': 1, 'flat': 0, 'up': 0}, 'calendar_days': 1}
    pair = {'samples': 3, 'correct': 1, 'accuracy': 1/3, 'brier_loss': .7, 'log_loss': 1.1}
    write(root, 'stock-forecast-learning.json', {'generated_at': stamp, 'overall': overall,
          'policy': {'minimum_brier_gain': .01, 'minimum_logloss_gain': .005, 'minimum_paired_targets': 120, 'minimum_sessions': 20},
          'baseline_paired': {'samples': 3, 'model': pair, 'baseline': pair}})
    write(root, 'stock-direction-forecast.json', {'generated_at': stamp, 'records': []})
    write(root, 'stock-market-context.json', {'generated_at': stamp, 'indicators': {}})
    write(root, 'stock-radar-chart-data.json', {'generated_at': stamp, 'source_generated_at': stamp, 'series': {}})
    write(root, 'stock-opportunity-summary.json', {'generated_at': stamp, 'counts': {'tracked': 2}})
    write(root, 'stock-investment-cases-summary.json', {'generated_at': stamp, 'counts': {'attractive': 0}})
    write(root, 'stock-entry-plan-summary.json', {'generated_at': stamp, 'counts': {'paper_candidate': 0}, 'live_recommendations': 0})
    (root / 'stock-forecast-outcomes.jsonl').write_text('\n'.join(json.dumps({'id': str(i), 'status': 'observed', 'correct': i == 0, 'public_before_target_verified': True}) for i in range(3)) + '\n')


class SessionTests(unittest.TestCase):
    def test_current_kr_intraday_bar_is_not_a_close(self):
        now = NOW.replace(hour=3)
        rows, meta = completed_daily_points([('2026-11-04', 100), ('2026-11-05', 999)], 'KR', now, Calendar())
        self.assertEqual(rows, [('2026-11-04', 100)])
        self.assertEqual(meta['expected_session'], '2026-11-04')

    def test_close_requires_thirty_minute_buffer(self):
        before = NOW.replace(hour=6, minute=59)
        after = NOW.replace(hour=7)
        self.assertEqual(clock('KR', before)['expected_session'], '2026-11-04')
        self.assertEqual(clock('KR', after)['expected_session'], '2026-11-05')

    def test_weekend_keeps_friday_without_invented_sessions(self):
        now = datetime(2026, 11, 8, 10, tzinfo=UTC)
        self.assertEqual(clock('KR', now)['expected_session'], '2026-11-06')
        self.assertFalse(clock('US', now)['market_open'])

    def test_short_session_and_holiday_use_calendar_close(self):
        cal = Calendar(rows={'2026-11-25': ('2026-11-25T14:30:00Z', '2026-11-25T21:00:00Z'),
                             '2026-11-27': ('2026-11-27T14:30:00Z', '2026-11-27T18:00:00Z'),
                             '2026-11-30': ('2026-11-30T14:30:00Z', '2026-11-30T21:00:00Z')})
        now = datetime(2026, 11, 27, 18, 30, tzinfo=UTC)
        self.assertEqual(market_session_clock('US', now, calendar=cal)['expected_session'], '2026-11-27')
        self.assertEqual(market_session_clock('US', now - timedelta(minutes=1), calendar=cal)['expected_session'], '2026-11-25')

    def test_fx_excludes_unfinished_utc_day_and_invalid_values(self):
        rows, _ = completed_daily_points([('2026-11-04', 1300), ('2026-11-05', 1400),
                                         ('2026-11-03', True), ('2026-11-02', float('nan'))], 'FX', NOW)
        self.assertEqual(rows, [('2026-11-04', 1300)])


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = health_fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def result(self, now=NOW):
        return health.inspect(self.root, now, clock)

    def test_uses_actual_canonical_rows_and_all_required_feeds(self):
        result = self.result()
        self.assertEqual(result['coverage']['tracked'], 2)
        self.assertEqual(result['coverage']['required_chart_series'], 6)
        self.assertFalse(result['issues'], result['issues'])
        self.assertNotIn('stock-value-radar-data.json', result['monitored_files'].values())

    def test_new_wrapper_timestamp_does_not_refresh_old_prices(self):
        self.data['opportunity']['companies'][0]['price_session'] = '2026-11-04'
        write(self.root, health.FILES['opportunity'], self.data['opportunity'])
        self.assertTrue(any('stale_source_session' in value for value in self.result()['issues']))

    def test_missing_chart_is_a_failure_even_with_recent_other_files(self):
        (self.root / health.FILES['charts']).unlink()
        self.assertTrue(any('charts:' in value for value in self.result()['issues']))

    def test_collected_before_close_is_not_confirmed_by_generation_time(self):
        self.data['opportunity']['companies'][0]['collected_at'] = '2026-11-05T03:00:00Z'
        write(self.root, health.FILES['opportunity'], self.data['opportunity'])
        self.assertTrue(any('close_not_confirmed_at_collection' in value for value in self.result()['issues']))

    def test_old_news_is_reported_when_markets_are_closed(self):
        write(self.root, health.FILES['news'], {'generated_at': (NOW - timedelta(hours=7)).isoformat()})
        self.assertTrue(any('news:' in value for value in self.result()['issues']))

    def test_audit_timestamp_mismatch_cannot_pass(self):
        self.data['accuracy']['source']['forecasts_generated_at'] = '2026-11-05T06:38:00Z'
        write(self.root, health.FILES['accuracy'], self.data['accuracy'])
        self.assertTrue(any('accuracy:' in value for value in self.result()['issues']))

    def test_regenerated_event_wrapper_cannot_hide_stale_source_calendar(self):
        self.data['calendar']['stale'] = True
        self.data['events']['calendar_fresh'] = False
        for key in ('calendar', 'events'):
            write(self.root, health.FILES[key], self.data[key])
        self.assertTrue(any('calendar:' in value for value in self.result()['issues']))
        self.assertTrue(any('events:' in value for value in self.result()['issues']))

    def test_weekend_old_generation_is_valid_when_source_sessions_match(self):
        now = datetime(2026, 11, 8, 10, tzinfo=UTC)
        source = datetime(2026, 11, 6, 22, tzinfo=UTC)
        health_fixture(self.root, now, source)
        self.assertFalse(self.result(now)['issues'], self.result(now)['issues'])

    def test_expired_forecast_is_not_made_fresh_by_wrapper(self):
        self.data['forecast']['records'][0]['target'] = {'start': '2026-11-04T00:00:00Z', 'end': '2026-11-04T06:30:00Z'}
        self.data['forecast']['records'][0]['issued_at'] = '2026-11-03T08:00:00Z'
        write(self.root, health.FILES['forecast'], self.data['forecast'])
        self.assertTrue(any('종료된 예측' in value for value in self.result()['issues']))

    def test_no_call_outside_session_is_not_misreported_as_failure(self):
        self.data['forecast']['records'] = [{'symbol': 'AAPL', 'status': 'no_call', 'reason': 'insufficient_regular_session_time'}]
        write(self.root, health.FILES['forecast'], self.data['forecast'])
        self.assertFalse(self.result()['issues'], self.result()['issues'])


class CanonicalAndAuditTests(unittest.TestCase):
    def test_modern_installer_preserves_html_and_rejects_missing_evidence_feed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'assets').mkdir()
            page = '<html data-custom-radar-ui="flow-v3"><script src="./assets/stock-radar-clean-bridge.js"></script><script src="./assets/stock-radar-flow-v2.js"></script></html>'
            (root / 'stock-value-radar.html').write_text(page)
            bridge = '// stock-opportunity-data.json stock-investment-cases.json stock-green-review-summary.json stock-entry-plan-summary.json stock-radar-accuracy-audit.json\n'
            (root / 'assets/stock-radar-clean-bridge.js').write_text(bridge)
            (root / 'assets/stock-radar-flow-v2.js').write_text('// canonical UI\n')
            for script in ('install_stock_strict_green.py', 'install_stock_investment_cases.py'):
                subprocess.run([sys.executable, str(SCRIPTS / script)], cwd=root, check=True, capture_output=True)
            self.assertEqual((root / 'stock-value-radar.html').read_text(), page)
            self.assertEqual((root / 'assets/stock-radar-clean-bridge.js').read_text(), bridge)
            (root / 'assets/stock-radar-clean-bridge.js').write_text(bridge.replace('stock-green-review-summary.json', ''))
            with self.assertRaisesRegex(RuntimeError, 'evidence_feed_not_connected'):
                verify_canonical(root)

    def test_audit_uses_provided_snapshot_and_refuses_mixed_forecast_learning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audit_fixture(root)
            self.assertTrue(accuracy.report(root, NOW)['data_integrity']['check_passed'])
            write(root, 'stock-direction-forecast.json', {'generated_at': '2026-11-05T09:00:00Z', 'records': []})
            self.assertFalse(accuracy.report(root, NOW)['data_integrity']['check_passed'])

    def test_publication_race_recomputes_audit_and_preserves_unrelated_file(self):
        def git(root, *args):
            return subprocess.run(['git', *args], cwd=root, check=True, text=True, capture_output=True)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            remote, local, other = (base / name for name in ('remote.git', 'local', 'other'))
            git(base, 'init', '--bare', str(remote))
            git(base, 'clone', str(remote), str(local))
            for name, value in (('user.name', 'test'), ('user.email', 'test@example.invalid')):
                git(local, 'config', name, value)
            git(local, 'checkout', '-b', 'main')
            audit_fixture(local)
            git(local, 'add', '.')
            git(local, 'commit', '-m', 'initial data')
            git(local, 'push', '-u', 'origin', 'main')
            git(base, 'clone', '--branch', 'main', str(remote), str(other))
            git(other, 'config', 'user.name', 'other')
            git(other, 'config', 'user.email', 'other@example.invalid')
            original, raced = publisher.git, []
            new_stamp = '2026-11-05T09:00:00+00:00'
            def concurrent(root, *args, **kwargs):
                if args[:1] == ('push',) and not raced:
                    raced.append(True)
                    audit_fixture(other, new_stamp)
                    (other / 'unrelated.txt').write_text('preserve this newer work')
                    git(other, 'add', '.')
                    git(other, 'commit', '-m', 'parallel new forecast and unrelated work')
                    git(other, 'push', 'origin', 'HEAD:main')
                return original(root, *args, **kwargs)
            with patch.object(publisher, 'git', side_effect=concurrent), patch.object(publisher.time, 'sleep'):
                publisher.publish(local, attempts=3)
            git(other, 'pull', '--ff-only')
            report = json.loads((other / publisher.OUTPUT).read_text())
            self.assertEqual(report['source']['forecasts_generated_at'], new_stamp)
            self.assertEqual((other / 'unrelated.txt').read_text(), 'preserve this newer work')
            self.assertFalse(report['promotion_gates']['investment_use_approved'])

    def test_explicit_repair_branch_preserves_main_and_parallel_entry_records(self):
        def git(root, *args):
            return subprocess.run(['git', *args], cwd=root, check=True, text=True, capture_output=True)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            remote, local = base / 'remote.git', base / 'local'
            git(base, 'init', '--bare', str(remote))
            git(base, 'clone', str(remote), str(local))
            git(local, 'config', 'user.name', 'test')
            git(local, 'config', 'user.email', 'test@example.invalid')
            git(local, 'checkout', '-b', 'main')
            write(local, 'stock-radar-health.json', {'generated_at': '2026-11-05T08:00:00Z', 'status': 'old'})
            (local / 'stock-entry-ledger.jsonl').write_text('{"id":"existing","value":1}\n')
            git(local, 'add', '.')
            git(local, 'commit', '-m', 'initial data')
            main_sha = git(local, 'rev-parse', 'HEAD').stdout.strip()
            branch = 'fix/radar-integrity-20261105'
            git(local, 'push', 'origin', 'HEAD:main', 'HEAD:' + branch)
            write(local, 'stock-radar-health.json', {'generated_at': '2026-11-05T09:00:00Z', 'status': 'new'})
            (local / 'stock-entry-ledger.jsonl').write_text('{"id":"new","value":2}\n')
            widget_publisher.publish(local, ['stock-radar-health.json'], 'refresh branch', branch=branch,
                                     append_ledgers=('stock-entry-ledger.jsonl',))
            git(local, 'fetch', 'origin')
            self.assertEqual(git(local, 'rev-parse', 'origin/main').stdout.strip(), main_sha)
            published = json.loads(git(local, 'show', 'origin/' + branch + ':stock-radar-health.json').stdout)
            self.assertEqual(published['status'], 'new')
            rows = [json.loads(line) for line in git(local, 'show', 'origin/' + branch + ':stock-entry-ledger.jsonl').stdout.splitlines()]
            self.assertEqual([row['id'] for row in rows], ['existing', 'new'])

    def test_entry_evidence_conflicts_are_rejected_before_overwrite(self):
        with self.assertRaisesRegex(ValueError, 'conflicting_immutable_entry_record'):
            widget_publisher.merge_entry_ledger(b'{"id":"same","price":10}\n', b'{"id":"same","price":20}\n')
        with self.assertRaisesRegex(ValueError, 'entry_ledger_record_missing_id'):
            widget_publisher.merge_entry_ledger(None, b'{"price":20}\n')


if __name__ == '__main__':
    unittest.main()
