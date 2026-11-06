"""Real local-git races and deterministic health-policy regression controls."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import publish_stock_radar_health as publisher
from test_stock_data_pipeline import NOW, SCRIPTS, clock, health, health_fixture, write


class HealthPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.remote, self.local, self.writer = (self.root / name for name in ("remote.git", "local", "writer"))
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "clone", str(self.remote), str(self.local)], check=True, capture_output=True)
        self.git(self.local, "checkout", "-b", "main")
        self.configure(self.local)
        health_fixture(self.local)
        (self.local / "stock-value-radar.html").write_text("<html></html>\n")
        (self.local / "scripts").mkdir()
        for name in publisher.CONTROL_INPUTS:
            if name.startswith("scripts/"):
                shutil.copyfile(SCRIPTS.parent / name, self.local / name)
        self.old = health.inspect(self.local, NOW, clock)
        self.old["checked_at"] = "2026-11-05T09:50:00+00:00"
        write(self.local, publisher.OUTPUT, self.old)
        self.commit_push(self.local, "initial source")
        subprocess.run(["git", "clone", "--branch", "main", str(self.remote), str(self.writer)], check=True, capture_output=True)
        self.configure(self.writer)
        self.initial = (self.local / publisher.OUTPUT).read_bytes()
        self.inspections = []

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def git(root, *args, check=True):
        return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=check)

    def configure(self, root):
        self.git(root, "config", "user.name", "Health regression fixture")
        self.git(root, "config", "user.email", "fixture@example.invalid")

    def commit_push(self, root, message):
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", message)
        self.git(root, "push", "origin", "HEAD:main")
        return self.git(root, "rev-parse", "HEAD").stdout.strip()

    def inspect(self, work):
        result = health.inspect(work, NOW, clock)
        self.inspections.append(result)
        write(work, publisher.OUTPUT, result)

    def remote_report(self):
        wire = self.git(self.remote, "show", "main:" + publisher.OUTPUT).stdout
        return json.loads(wire), wire.encode()

    def publish(self, **kwargs):
        with patch.object(publisher, "run_monitor", side_effect=self.inspect), patch.object(publisher.time, "sleep"), patch("builtins.print"):
            return publisher.publish(self.local, **kwargs)

    def test_old_checkout_error_is_recomputed_against_current_main(self):
        audit = json.loads((self.local / "stock-radar-accuracy-audit.json").read_text())
        audit["source"]["market_generated_at"] = "old"
        write(self.local, "stock-radar-accuracy-audit.json", audit)
        write(self.local, publisher.OUTPUT, health.inspect(self.local, NOW, clock))
        self.assertTrue(json.loads((self.local / publisher.OUTPUT).read_text())["issues"])
        base = self.git(self.writer, "rev-parse", "HEAD").stdout.strip()
        commit = self.publish()
        report, remote_wire = self.remote_report()
        self.assertFalse(report["issues"])
        self.assertEqual(report["source_snapshot"]["commit"], base)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), remote_wire)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout.strip(), commit)

    def test_actual_current_error_is_published_without_weakening_policy(self):
        audit = json.loads((self.writer / "stock-radar-accuracy-audit.json").read_text())
        audit["data_integrity"]["check_passed"] = False
        write(self.writer, "stock-radar-accuracy-audit.json", audit)
        self.old["consecutive_failures"] = 1
        write(self.writer, publisher.OUTPUT, self.old)
        self.commit_push(self.writer, "current broken audit")
        self.publish()
        report, wire = self.remote_report()
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["consecutive_failures"], 2)
        self.assertTrue(report["notification_required"])
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), wire)

    def test_push_race_rechecks_same_timestamp_changed_audit_bytes(self):
        audit = json.loads((self.writer / "stock-radar-accuracy-audit.json").read_text())
        audit["data_integrity"]["check_passed"] = False
        write(self.writer, "stock-radar-accuracy-audit.json", audit)
        self.commit_push(self.writer, "temporary audit error")
        original_git = publisher.git
        raced = []
        def racing_git(root, *args, **kwargs):
            if args[:1] == ("push",) and not raced:
                audit["data_integrity"]["check_passed"] = True
                write(self.writer, "stock-radar-accuracy-audit.json", audit)
                raced.append(self.commit_push(self.writer, "correct audit without timestamp change"))
            return original_git(root, *args, **kwargs)
        with patch.object(publisher, "git", side_effect=racing_git):
            self.publish(attempts=2)
        report, _ = self.remote_report()
        self.assertEqual(len(self.inspections), 2)
        self.assertTrue(self.inspections[0]["issues"])
        self.assertFalse(report["issues"])
        self.assertEqual(report["source_snapshot"]["commit"], raced[0])
        audit_bytes = (self.writer / "stock-radar-accuracy-audit.json").read_bytes()
        self.assertEqual(report["source_snapshot"]["inputs"]["stock-radar-accuracy-audit.json"]["sha256"], hashlib.sha256(audit_bytes).hexdigest())

    def test_retry_uses_latest_previous_health_counter_once(self):
        (self.writer / "news-link-data.json").unlink()
        self.commit_push(self.writer, "missing required news")
        original_git = publisher.git
        previous = []
        def racing_git(root, *args, **kwargs):
            if args[:1] == ("push",) and not previous:
                updated = {**self.old, "consecutive_failures": 6}
                write(self.writer, publisher.OUTPUT, updated)
                previous.append((self.writer / publisher.OUTPUT).read_bytes())
                self.commit_push(self.writer, "another completed health observation")
            return original_git(root, *args, **kwargs)
        with patch.object(publisher, "git", side_effect=racing_git):
            self.publish(attempts=2)
        report, _ = self.remote_report()
        self.assertEqual(report["consecutive_failures"], 7)
        self.assertEqual(report["source_snapshot"]["previous_health_sha256"], hashlib.sha256(previous[0]).hexdigest())

    def test_missing_and_invalid_inputs_are_recorded_without_hiding_errors(self):
        (self.writer / "news-link-data.json").unlink()
        (self.writer / "market-events-data.json").write_bytes(b"{invalid-json")
        (self.writer / "stock-value-radar.html").write_text('<script src="assets/stock-catalog-ui.js"></script>')
        self.commit_push(self.writer, "missing and invalid required feeds")
        self.publish()
        report, _ = self.remote_report()
        inputs = report["source_snapshot"]["inputs"]
        self.assertEqual(inputs["news-link-data.json"], {"exists": False, "sha256": None})
        self.assertEqual(inputs["market-events-data.json"], {"exists": True, "sha256": hashlib.sha256(b"{invalid-json").hexdigest()})
        self.assertTrue(set(health.FILES.values()) | set(health.EXTENDED.values()) | set(publisher.CONTROL_INPUTS) <= set(inputs))
        self.assertEqual(report["status"], "error")

    def test_latest_monitor_code_executes_in_worktree_not_old_checkout(self):
        (self.local / publisher.MONITOR).write_text("raise RuntimeError('old checkout code must not run')\n")
        # Execute the real monitor in the fetched worktree. A missing local
        # calendar package is itself reported as a health error, not hidden.
        with patch("builtins.print"):
            publisher.publish(self.local)
        report, wire = self.remote_report()
        self.assertEqual(report["version"], "canonical-radar-health-v2")
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), wire)
        self.assertIn("old checkout code", (self.local / publisher.MONITOR).read_text())

    def test_changed_input_during_inspection_is_rejected(self):
        before = self.git(self.remote, "rev-parse", "main").stdout
        def mutating_inspection(work):
            self.inspect(work)
            (work / "stock-radar-accuracy-audit.json").write_text("{}")
        with patch.object(publisher, "run_monitor", side_effect=mutating_inspection):
            with self.assertRaisesRegex(RuntimeError, "health_input_changed_during_inspection"):
                publisher.publish(self.local)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout, before)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_no_fresh_monitor_output_never_copies_prior_report_as_success(self):
        with patch.object(publisher, "run_monitor"):
            with self.assertRaisesRegex(RuntimeError, "health_inspection_did_not_refresh_report"):
                publisher.publish(self.local)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_unchanged_staging_is_not_reported_as_success(self):
        original_git = publisher.git
        def no_diff(root, *args, **kwargs):
            if args == ("diff", "--cached", "--quiet"):
                return SimpleNamespace(returncode=0)
            return original_git(root, *args, **kwargs)
        with patch.object(publisher, "git", side_effect=no_diff):
            with self.assertRaisesRegex(RuntimeError, "health_publication_unchanged"):
                self.publish()
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_push_failure_and_retry_exhaustion_leave_local_alert_report_untouched(self):
        before = self.git(self.remote, "rev-parse", "main").stdout
        original_git = publisher.git
        def denied_push(root, *args, **kwargs):
            if args[:1] == ("push",):
                return SimpleNamespace(returncode=1)
            return original_git(root, *args, **kwargs)
        with patch.object(publisher, "git", side_effect=denied_push):
            with self.assertRaisesRegex(RuntimeError, "health_publication_race"):
                self.publish(attempts=2)
        self.assertEqual(len(self.inspections), 2)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout, before)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_monitor_exception_never_reuses_prior_report(self):
        with patch.object(publisher, "run_monitor", side_effect=RuntimeError("inspection failed")):
            with self.assertRaisesRegex(RuntimeError, "inspection failed"):
                publisher.publish(self.local)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_workflow_uses_published_report_and_refreshes_after_accuracy_converges(self):
        source = (SCRIPTS.parent / ".github/workflows/monitor-stock-value-radar.yml").read_text()
        self.assertIn("'Audit Stock Radar Accuracy'", source)
        self.assertIn("python scripts/publish_stock_radar_health.py", source)
        self.assertIn("test_stock_radar_health_publication.py", source)
        self.assertNotIn("python scripts/publish_widget_data.py", source)
        self.assertNotIn("run: python scripts/monitor-stock-value-radar.py", source)

    def test_pull_request_runs_read_only_regressions_without_publication_or_alerts(self):
        source = (SCRIPTS.parent / ".github/workflows/monitor-stock-value-radar.yml").read_text()
        self.assertIn("  pull_request:\n", source)
        self.assertIn("format('monitor-stock-radar-pr-{0}', github.event.pull_request.number)", source)
        regression = re.search(r"(?ms)^  publication-regression:\n(.*?)(?=^  monitor:)", source).group(1)
        self.assertIn("if: github.event_name == 'pull_request'", regression)
        self.assertIn("permissions:\n      contents: read", regression)
        self.assertIn("test_stock_radar_health_publication.py", regression)
        self.assertNotIn("python scripts/publish_stock_radar_health.py", regression)
        self.assertNotIn("gh issue", regression)
        monitor = source.split("\n  monitor:\n", 1)[1]
        self.assertIn("if: github.event_name != 'pull_request' &&", monitor)


class FullUniverseHealthTests(unittest.TestCase):
    """Synthetic health documents only; no prices or forecasts are published."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 11, 6, 16, tzinfo=timezone.utc)
        self.refresh_core(self.now)
        (self.root / 'stock-value-radar.html').write_text('<script src="assets/stock-catalog-ui.js"></script>')
        self.catalog = {'identifier_policy': 'kr-six-character-alphanumeric-v2', 'status': 'complete',
                        'generated_at': '2026-11-06T03:00:00+00:00',
                        'counts': {'total': 2, 'KR': 1, 'US': 1},
                        'items': [{'country': 'KR', 'symbol': '0001A0', 'source_symbol': '0001A0',
                                   'name': 'TEST-ONLY KR', 'exchange': 'KOSDAQ'},
                                  {'country': 'US', 'symbol': 'MOG.A', 'source_symbol': 'MOG.A',
                                   'name': 'TEST-ONLY US', 'exchange': 'NYSE'}]}
        self.feed = {'version': 'stock-extended-direction-v1', 'generation_mode': 'full_universe',
                     'source_identity_policy': 'kr-six-character-alphanumeric-v2',
                     'generated_at': '2026-11-06T07:30:00+00:00', 'automatic_orders': False,
                     'run_id': 'test-full-run', 'source_commit': 'a'*40, 'manifest_sha256': 'b'*64,
                     'source_catalog_sha256': 'c'*64, 'implementation_sha256': {'runner.py': 'd'*64},
                     'records': []}
        for item, provider, observed, start, end in (
            (self.catalog['items'][0], '0001A0.KQ', '2026-11-06T06:30:00+00:00',
             '2026-11-09T00:00:00+00:00', '2026-11-09T06:30:00+00:00'),
            (self.catalog['items'][1], 'MOG-A', '2026-11-05T21:00:00+00:00',
             '2026-11-06T14:30:00+00:00', '2026-11-06T21:00:00+00:00')):
            self.feed['records'].append({
                'key': item['country']+':'+item['symbol'], 'market': item['country'], 'mode': 'daily',
                'name': item['name'], 'catalog_name': item['name'], 'catalog_symbol': item['symbol'],
                'catalog_exchange': item['exchange'], 'symbol': provider, 'provider_symbol': provider,
                'identity_verified': True, 'source_identity_policy': 'kr-six-character-alphanumeric-v2',
                'recommendation': False, 'live_validated': False, 'source_identity_verified': True,
                'source_response_symbol': provider, 'status': 'research_prediction',
                'issued_at': '2026-11-06T07:01:00+00:00', 'received_at': '2026-11-06T07:00:00+00:00',
                'observed_until': observed, 'origin_session': observed[:10],
                'target': {'start': start, 'end': end}, 'direction': 'up',
                'probabilities': {'down': .2, 'flat': .3, 'up': .5}, 'error_kind': None, 'reason': None,
                'collection_status': 'fetched', 'source_fetch_attempts': 1,
                'source_collection_attempted': True, 'price_available': True,
                'price_provenance': {'provider_symbol': provider, 'history_sha256': 'e'*64,
                                     'source_sha256': 'f'*64, 'fetched_at': '2026-11-06T07:00:00+00:00',
                                     'last_session': observed[:10]}})
        self.feed['run'] = {'id': self.feed['run_id'], 'source_commit': self.feed['source_commit'],
                            'manifest_sha256': self.feed['manifest_sha256'], 'catalog_sha256': self.feed['source_catalog_sha256'],
                            'implementation_sha256': self.feed['implementation_sha256'],
                            'started_at': '2026-11-06T06:55:00+00:00', 'completed_at': self.feed['generated_at'],
                            'retained_predictions': 0, 'retained_unexpired_after_no_call': 0,
                            'shard_count': 1, 'shards': [{'index': 0, 'sha256': '1'*64, 'records': 2,
                                                       'started_at': '2026-11-06T06:55:00+00:00',
                                                       'completed_at': '2026-11-06T07:29:00+00:00'}]}
        self.recount()
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def refresh_core(self, now):
        data = health_fixture(self.root, now)
        # The legacy fixture's next_open is already open during US hours.
        # Give its independent core records a prospective test-only interval.
        for row in data['forecast']['records']:
            row['issued_at'] = (now-timedelta(minutes=10)).isoformat()
            row['target'] = {'start': (now+timedelta(hours=1)).isoformat(),
                             'end': (now+timedelta(hours=2)).isoformat()}
        write(self.root, health.FILES['forecast'], data['forecast'])

    def recount(self):
        rows = self.feed['records']
        prediction = sum(row['status'] == 'research_prediction' for row in rows)
        skipped = sum(row['collection_status'] in ('circuit_skipped', 'deadline_skipped') for row in rows)
        failed = len(rows)-prediction-skipped
        errors = {}
        for row in rows:
            if row.get('error_kind'):
                errors[row['error_kind']] = errors.get(row['error_kind'], 0)+1
        self.feed['coverage'] = {'total': len(rows), 'prediction': prediction, 'failed': failed,
             'not_attempted': skipped, 'attempted': len(rows)-skipped, 'no_call': len(rows)-prediction,
             'source_fetch_attempts': sum(row['source_fetch_attempts'] for row in rows),
             'source_collection_attempted': sum(row['source_collection_attempted'] for row in rows),
             'price_available': sum(row['price_available'] for row in rows),
             'cache_current': sum(row['collection_status'] == 'cache_current' for row in rows),
             'unsupported': sum(row['collection_status'] == 'unsupported' for row in rows),
             'error_kinds': errors, 'manifest_complete': True, 'coverage_complete': skipped == 0}
        c = self.feed['coverage']
        self.feed['run'].update({key: c[key] for key in
                                ('attempted', 'failed', 'not_attempted', 'source_fetch_attempts', 'source_collection_attempted')})
        self.feed['run'].update(research_prediction=prediction, no_call=failed)

    def save(self):
        write(self.root, health.EXTENDED['catalog'], self.catalog)
        write(self.root, health.EXTENDED['financial'], {
            'generated_at': self.now.isoformat(), 'identity_policy': 'official-issuer-identity-v2',
            'catalog_generated_at': self.catalog['generated_at']})
        write(self.root, health.EXTENDED['extended_forecast'], self.feed)

    def inspect(self, now=None):
        return health.inspect(self.root, now or self.now, clock)

    def extended_issues(self, result):
        return [issue for issue in result['issues'] if issue.startswith('extended_forecast')]

    def test_daily_full_universe_does_not_expire_two_hours_before_us_open(self):
        result = self.inspect()
        self.assertFalse(result['issues'], result['issues'])
        age = result['data_ages']['extended_forecast']
        self.assertEqual(age['next_due'], '2026-11-09T06:55:00+00:00')
        self.assertEqual(age['deadline'], '2026-11-09T09:55:00+00:00')
        self.assertNotIn('max_hours', age)
        self.assertEqual(result['coverage']['extended_forecast_daily']['active_by_market'], {'KR': 1, 'US': 1})

    def test_weekend_and_exact_next_weekday_deadline_match_ui(self):
        for stamp, delayed in (('2026-11-08T10:00:00+00:00', False),
                               ('2026-11-09T09:55:00+00:00', False),
                               ('2026-11-09T09:55:01+00:00', True)):
            with self.subTest(stamp=stamp):
                now = datetime.fromisoformat(stamp)
                self.refresh_core(now)
                issues = self.extended_issues(self.inspect(now))
                self.assertEqual(any('일간 갱신 지연' in issue for issue in issues), delayed, issues)
                if not delayed:
                    self.assertFalse(issues, issues)

    def test_manual_run_before_daily_schedule_keeps_same_day_deadline(self):
        self.feed['run']['started_at'] = '2026-11-06T06:54:00+00:00'
        self.feed['run']['shards'][0]['started_at'] = self.feed['run']['started_at']
        state = health.full_universe_state(self.feed, self.catalog, self.now, clock)
        self.assertEqual(state['deadline'], '2026-11-06T09:55:00+00:00')

    def test_wrapper_timestamp_cannot_reset_issuance_or_daily_deadline(self):
        self.feed['generated_at'] = self.now.isoformat()
        self.save()
        issues = self.extended_issues(self.inspect())
        self.assertTrue(any('run_timestamp_mismatch' in issue for issue in issues), issues)
        self.feed['run']['completed_at'] = self.feed['generated_at']
        self.feed['run']['started_at'] = '2026-11-05T06:55:00+00:00'
        self.feed['run']['shards'][0]['started_at'] = self.feed['run']['started_at']
        self.save()
        self.assertTrue(any('일간 갱신 지연' in issue for issue in self.extended_issues(self.inspect())))

    def test_actual_identity_and_accounting_are_required_for_daily_exception(self):
        original = json.dumps(self.feed)
        mutations = (
            lambda f: f['coverage'].update(prediction=999),
            lambda f: f['records'][1].update(catalog_symbol='MOG.B'),
            lambda f: f['records'][1].update(key=f['records'][0]['key']),
            lambda f: f['records'].pop(),
            lambda f: f['records'][1].update(issued_at='2026-11-05T07:00:00+00:00'),
            lambda f: f['records'][1]['probabilities'].update(up=.9),
            lambda f: f['records'][1]['target'].update(end='2026-11-06T22:00:00+00:00'),
        )
        for mutate in mutations:
            self.feed = json.loads(original)
            mutate(self.feed)
            self.save()
            result = self.inspect()
            issues = self.extended_issues(result)
            self.assertTrue(any('일간 계약 확인 실패' in issue for issue in issues), issues)
            self.assertEqual(result['data_ages']['extended_forecast']['max_hours'], 2)

    def test_core_and_legacy_extended_still_use_two_hour_active_market_limit(self):
        core = json.loads((self.root / health.FILES['forecast']).read_text())
        core['generated_at'] = self.feed['generated_at']
        write(self.root, health.FILES['forecast'], core)
        result = self.inspect()
        self.assertTrue(any(issue.startswith('forecast:') and '허용 2시간' in issue for issue in result['issues']))
        self.assertFalse(self.extended_issues(result))
        for mode in (None, 'FULL_UNIVERSE'):
            self.feed['generation_mode'] = mode
            self.save()
            result = self.inspect()
            self.assertTrue(any('허용 2시간' in issue for issue in self.extended_issues(result)))

    def make_no_call(self, index, collection='fetched', kind='insufficient_history'):
        row = self.feed['records'][index]
        row.update(status='no_call', probabilities=None, target=None, direction=None,
                   reason='test-only reason', error_kind=kind, collection_status=collection)
        if collection in ('circuit_skipped', 'deadline_skipped'):
            row.update(source_fetch_attempts=0, source_collection_attempted=False,
                       price_available=False, price_provenance=None, source_identity_verified=False,
                       source_response_symbol=None)
        self.recount()
        self.save()

    def test_unrequested_rows_are_reported_even_with_complete_manifest(self):
        self.make_no_call(1, 'deadline_skipped', 'deadline')
        result = self.inspect()
        self.assertTrue(any('미처리 1개' in issue for issue in self.extended_issues(result)))
        self.assertEqual(result['coverage']['extended_forecast_daily']['counts']['not_attempted'], 1)

    def test_open_us_market_cannot_be_hidden_by_future_kr_prediction(self):
        self.make_no_call(1)
        result = self.inspect()
        self.assertTrue(any(issue.startswith('extended_forecast US:') and '유효한 일간 예측이 없습니다' in issue
                            for issue in result['issues']), result['issues'])
        self.assertEqual(result['coverage']['extended_forecast_daily']['active_by_market']['KR'], 1)

    def test_all_expired_calls_during_open_market_are_visible_before_daily_deadline(self):
        self.make_no_call(0)
        now = datetime(2026, 11, 9, 3, tzinfo=timezone.utc)
        self.refresh_core(now)
        result = self.inspect(now)
        issues = self.extended_issues(result)
        self.assertFalse(any('일간 갱신 지연' in issue for issue in issues), issues)
        self.assertTrue(any(issue.startswith('extended_forecast KR:') and '유효한 일간 예측이 없습니다' in issue
                            for issue in issues), issues)
        self.assertEqual(result['coverage']['extended_forecast_daily']['expired_by_market']['US'], 1)


if __name__ == "__main__":
    unittest.main()
