"""Synthetic negative controls for read-only post-validation provenance.

None of these records or altered prices are published into forecast evidence.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

from audit_stock_forecast_census import census
from audit_stock_forecast_independent import audit, ts, write_audit_report
from test_stock_timing_target_instants import fixture, proof, CUT


class SourceBindingTests(unittest.TestCase):
    def data(self):
        r, o = fixture()
        return [r], [o], proof([r])

    def test_exact_input_snapshot_is_bound(self):
        r, o, d = self.data(); upstream = audit(r, o, d, CUT)
        result = census(r, o, d, upstream, {})
        self.assertTrue(result['source_binding_verified'])
        self.assertFalse(result['errors'])
        self.assertEqual(result['source_binding']['counts'], dict(ledger=1,outcomes=1,deliveries=1))

    def test_saved_green_audit_cannot_certify_changed_provenance(self):
        for source, field, value in (
            ('ledger', 'trained_through', '2035-01-01T00:00:00Z'),
            ('ledger', 'history_sha256', 'changed-history'),
            ('ledger', 'source_commit', 'changed-commit'),
            ('outcomes', 'public_before_target_verified', False),
            ('outcomes', 'source_checked_at', '2035-01-01T00:00:00Z'),
            ('outcomes', 'single_provider_not_execution', False),
            ('deliveries', 'verification_id', '0'*64),
            ('deliveries', 'human_notification_received', True),
        ):
            with self.subTest(source=source, field=field):
                r, o, d = self.data(); upstream = audit(r, o, d, CUT)
                {'ledger':r, 'outcomes':o, 'deliveries':d}[source][0][field] = value
                result = census(r, o, d, upstream, {})
                self.assertFalse(result['source_binding_verified'])
                self.assertIn('upstream_source_binding_mismatch', result['errors'])
                self.assertEqual(result['status'], 'integrity_errors')

    def test_missing_binding_requires_new_audit_not_grandfathering(self):
        r, o, d = self.data(); upstream = audit(r, o, d, CUT)
        upstream.pop('source_binding', None)
        self.assertIn('upstream_source_binding_mismatch', census(r,o,d,upstream,{})['errors'])

    def test_each_binding_field_is_checked(self):
        r,o,d=self.data(); original=audit(r,o,d,CUT)
        for group, name in (('sha256','ledger'),('sha256','outcomes'),('sha256','deliveries'),
                            ('counts','ledger'),('counts','outcomes'),('counts','deliveries')):
            with self.subTest(group=group,name=name):
                upstream=deepcopy(original); upstream['source_binding'][group][name]='invalid'
                self.assertIn('upstream_source_binding_mismatch',census(r,o,d,upstream,{})['errors'])

    def test_appending_exact_replay_requires_new_snapshot_audit(self):
        r,o,d=self.data(); upstream=audit(r,o,d,CUT)
        r.append(deepcopy(r[0]))
        self.assertIn('upstream_source_binding_mismatch',census(r,o,d,upstream,{})['errors'])
        result=census(r,o,d,audit(r,o,d,CUT),{})
        self.assertFalse(result['errors'])
        self.assertEqual(result['row_accounting'],{'scored':1,'exact_id_replay':1})

    def test_hashes_preserve_row_order_without_using_it_for_selection(self):
        r,o,d=self.data(); second=deepcopy(r[0]);second['id']='later';second['issued_at']='2026-10-29T13:36:10Z'
        r.append(second); d=proof(r); upstream=audit(r,o,d,CUT)
        r.reverse()
        self.assertIn('upstream_source_binding_mismatch',census(r,o,d,upstream,{})['errors'])
        renewed=census(r,o,d,audit(r,o,d,CUT),{})
        self.assertEqual(renewed['observed_metrics']['samples'],1)
        self.assertFalse(renewed['errors'])

    def test_json_object_key_order_does_not_change_canonical_binding(self):
        r,o,d=self.data(); upstream=audit(r,o,d,CUT)
        r=[dict(reversed(list(r[0].items())))]
        result=census(r,o,d,upstream,{})
        self.assertTrue(result['source_binding_verified'])
        self.assertFalse(result['errors'])

    def test_nonfinite_input_never_gets_valid_fingerprint(self):
        r,o,d=self.data(); r[0]['probabilities']['up']=float('nan')
        upstream=audit(r,o,d,CUT)
        self.assertIn('source_fingerprint_unavailable',[e['error'] for e in upstream['errors']])
        result=census(r,o,d,upstream,{})
        self.assertFalse(result['source_binding_verified'])
        self.assertEqual(result['status'],'integrity_errors')

    def test_future_collector_context_is_not_a_historical_explanation(self):
        r,o,d=self.data();up=audit(r,[],d,CUT)
        for controller in (
            {'source_attempts':[{'symbol':'TEST','mode':'intraday','observed_until':'2035-01-01T00:00:00Z'}]},
            {'generated_at':'2035-01-01T00:00:00Z','source_attempts':[
                {'symbol':'TEST','mode':'intraday','observed_until':'2026-10-29T15:30:00Z'}]},
        ):
            result=census(r,[],d,up,controller)
            self.assertIn('collector_context_after_cutoff',result['errors'])
            self.assertEqual(result['missing_context_counts'],{'source_progress_unknown':1})

    def test_inputs_remain_byte_equivalent_and_no_usefulness_promotion(self):
        r,o,d=self.data();before=json.dumps([r,o,d],sort_keys=True)
        result=census(r,o,d,audit(r,o,d,CUT),{})
        self.assertEqual(before,json.dumps([r,o,d],sort_keys=True))
        self.assertEqual(result['timing_utility'],'not_proven')
        for key in ('external_exchange_prices_verified','human_receipt_verified',
                    'after_cost_usefulness_verified','untouched_followup_verified','orders_enabled'):
            self.assertIs(result[key],False)
        self.assertEqual(result['new_learning_updates'],0)

    def test_output_cannot_overwrite_original_or_upstream_evidence(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'upstream.json';path.write_bytes(b'original')
            with self.assertRaisesRegex(ValueError,'output_cannot_overwrite_evidence'):
                write_audit_report({},path,{path:b'original'})
            self.assertEqual(path.read_bytes(),b'original')

    def test_symlink_and_hardlink_output_aliases_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); source=root/'source.json';source.write_bytes(b'original')
            symlink=root/'symlink.json';symlink.symlink_to(source)
            hardlink=root/'hardlink.json';os.link(source,hardlink)
            for output in (symlink,hardlink):
                with self.assertRaisesRegex(ValueError,'output_cannot_overwrite_evidence'):
                    write_audit_report({},output,{source:b'original'})
            self.assertEqual(source.read_bytes(),b'original')

    def test_mid_audit_source_change_blocks_output(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source';source.write_bytes(b'changed')
            dest=root/'report.json'
            with self.assertRaisesRegex(RuntimeError,'source_changed_during_audit'):
                write_audit_report({},dest,{source:b'original'})
            self.assertFalse(dest.exists())

    def test_derived_output_is_written_without_mutating_sources(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source';source.write_bytes(b'original')
            dest=root/'report.json';dest.write_text('previous')
            write_audit_report({'valid':True},dest,{source:b'original'})
            self.assertEqual(json.loads(dest.read_text()),{'valid':True})
            self.assertEqual(source.read_bytes(),b'original')
            self.assertFalse(list(root.glob('.forecast-audit-*')))

if __name__=='__main__': unittest.main()
