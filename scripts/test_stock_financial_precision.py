"""Adversarial boundaries for an actual official rounding resolution."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import build_stock_financial_coverage as builder
from scripts.reconcile_stock_financial_precision import apply_review, RESTORED_NOTE
from scripts.stock_financial_precision import precision_facts_check, verified_balance_precision

ROOT = Path(__file__).resolve().parent.parent
REVIEW = json.loads((ROOT / 'data-evidence/stock-financial-precision-review-20261106.json').read_text())


def original(symbol='011280'):
    proof = REVIEW['records']['KR:' + symbol]['source_precision']
    return {'symbol': symbol, 'country': 'KR', 'corp_code': proof['issuer']['corp_code'],
            'rcept_no': proof['source']['rcept_no'], 'report_year': 2026, 'report_code': '11012',
            'period_end': '2026-06-30', 'consolidation': 'CFS', 'currency': 'KRW',
            'status': 'available', 'checked_at': '2026-11-05T12:12:44.891213+00:00',
            'metrics': {**{key: int(fact['value']) for key, fact in proof['facts'].items()}, 'revenue': 123},
            'limitations': [], 'missing_metrics': []}


def resolved():
    row = original()
    proof = copy.deepcopy(REVIEW['records']['KR:011280']['source_precision'])
    check = precision_facts_check(row, proof)
    assert check is not None
    row['account_validation'] = {'note': 'source precision confirmed', 'audited_at': proof['verified_at'],
        'balance_sheet': {'status': 'verified_with_declared_precision', 'source_precision': proof,
                          **check, 'reported_values_unchanged': True}}
    return row


class FinancialPrecisionTests(unittest.TestCase):
    def test_actual_source_bound_thousand_unit_evidence_is_recalculated(self):
        row = resolved()
        check = verified_balance_precision(row)
        self.assertEqual(check['reported_difference'], '-1000')
        self.assertEqual(check['difference_interval'], ['-2500', '500'])
        self.assertIsNone(builder.balance_equation_issue(row))
        builder.validate_account_record(row)

    def test_actual_other_three_discrepancies_stay_outside_precision(self):
        for symbol in ('038110', '264450', '352770'):
            row = original(symbol)
            proof = REVIEW['records']['KR:' + symbol]['source_precision']
            self.assertIsNone(precision_facts_check(row, proof), symbol)
            self.assertIsNotNone(builder.balance_equation_issue(row), symbol)

    def test_record_identity_period_currency_or_amount_change_invalidates_proof(self):
        for key, value in [('symbol', '999999'), ('corp_code', '00000000'), ('rcept_no', '20260814000000'),
                           ('period_end', '2026-03-31'), ('consolidation', 'OFS'), ('currency', 'USD'),
                           ('report_code', '11013'), ('report_year', 2025)]:
            row = resolved(); row[key] = value
            self.assertIsNone(verified_balance_precision(row), key)
            with self.assertRaises(ValueError): builder.validate_account_record(row)
        row = resolved(); row['metrics']['equity'] += 1
        self.assertIsNone(verified_balance_precision(row))

    def test_missing_or_modified_source_context_and_precision_is_not_accepted(self):
        for operation in ('missing_decimal', 'wrong_scope', 'wrong_unit', 'future_receipt', 'bad_hash', 'missing_api', 'wrong_api_amount'):
            row = resolved(); proof = row['account_validation']['balance_sheet']['source_precision']
            if operation == 'missing_decimal': del proof['facts']['assets']['decimals']
            elif operation == 'wrong_scope': proof['context']['dimensions'][0]['value'] = 'ifrs-full:SeparateMember'
            elif operation == 'wrong_unit': proof['unit']['measures'] = ['iso4217:USD']
            elif operation == 'future_receipt': proof['verified_at'] = '2099-01-01T00:00:00+00:00'
            elif operation == 'bad_hash': proof['source']['package_sha256'] = 'not-a-hash'
            elif operation == 'missing_api': proof['api_crosschecks'].pop()
            elif operation == 'wrong_api_amount': proof['api_crosschecks'][0]['rows'][0]['thstrm_amount'] = '1'
            self.assertIsNone(verified_balance_precision(row), operation)

    def test_claimed_interval_cannot_override_recomputed_interval(self):
        row = resolved()
        row['account_validation']['balance_sheet']['difference_interval'] = ['-999999999', '999999999']
        self.assertIsNone(verified_balance_precision(row))
        with self.assertRaises(ValueError): builder.validate_account_record(row)

    def test_fresh_identical_source_inherits_existing_proof_without_refreshing_proof_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); old = resolved()
            (root / builder.OUTPUT).write_text(json.dumps({'records': {'KR:011280': old}}))
            fresh = original(); fresh['checked_at'] = '2026-11-06T11:30:00+00:00'
            rows, audit = builder.guard_account_records({'KR:011280': fresh}, root, '2026-11-06T11:31:00+00:00')
            self.assertIsNotNone(verified_balance_precision(rows['KR:011280']))
            self.assertEqual(rows['KR:011280']['checked_at'], fresh['checked_at'])
            self.assertEqual(rows['KR:011280']['account_validation']['audited_at'], old['account_validation']['audited_at'])
            self.assertEqual(audit['withheld_fields'], 0)
            self.assertEqual(audit['precision_verified_fields'], 3)

    def test_new_filing_or_changed_amount_cannot_inherit_precision_exception(self):
        for change in ('new_receipt', 'changed_amount'):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / builder.OUTPUT).write_text(json.dumps({'records': {'KR:011280': resolved()}}))
                fresh = original()
                if change == 'new_receipt': fresh['rcept_no'] = '20261116000001'
                else: fresh['metrics']['assets'] += 1
                rows, audit = builder.guard_account_records({'KR:011280': fresh}, root, '2026-11-06T11:31:00+00:00')
                self.assertTrue(all(rows['KR:011280']['metrics'][key] is None for key in builder.BALANCE_FIELDS), change)
                self.assertEqual(audit['precision_verified_fields'], 0)
                self.assertEqual(audit['withheld_fields'], 3)

    def test_restoration_changes_only_reviewed_triple_and_preserves_source_clocks_and_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = {f'KR:{symbol}': original(symbol) for symbol in ('011280', '038110', '264450', '352770')}
            held, audit = builder.guard_account_records(before, root, '2026-11-06T09:29:26+00:00')
            data = {'generated_at': '2026-11-05T12:12:44+00:00', 'records': held, 'account_integrity': audit}
            (root / builder.OUTPUT).write_text(json.dumps(data))
            archive = (root / builder.ACCOUNT_QUARANTINE_OUTPUT).read_bytes()
            result = apply_review(root, REVIEW)
            after = json.loads((root / builder.OUTPUT).read_text())
            self.assertEqual(result['restored_fields'], 3)
            self.assertEqual(after['generated_at'], data['generated_at'])
            self.assertEqual(after['records']['KR:011280']['checked_at'], before['KR:011280']['checked_at'])
            self.assertEqual(after['records']['KR:011280']['metrics'], before['KR:011280']['metrics'])
            for key in ('KR:038110', 'KR:264450', 'KR:352770'):
                actual = copy.deepcopy(after['records'][key])
                review = actual['account_validation']['balance_sheet'].pop('source_review')
                self.assertEqual(review['status'], 'completed_source_mismatch')
                self.assertEqual(review['difference_interval'], REVIEW['records'][key]['source_interval_result']['difference_interval'])
                self.assertEqual(review['reviewed_at'], REVIEW['records'][key]['source_precision']['verified_at'])
                self.assertTrue(all(actual['metrics'][field] is None for field in builder.BALANCE_FIELDS))
                self.assertNotIn('재확인해야', actual['account_validation']['note'])
                actual['account_validation']['note'] = held[key]['account_validation']['note']
                actual['limitations'] = held[key]['limitations']
                self.assertEqual(actual, held[key])
            self.assertEqual((root / builder.ACCOUNT_QUARANTINE_OUTPUT).read_bytes(), archive)
            self.assertEqual(after['account_integrity']['withheld_fields'], 9)
            self.assertEqual(after['account_integrity']['precision_verified_fields'], 3)

    def test_already_restored_snapshot_gets_only_review_copy_then_is_byte_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = {f'KR:{symbol}': original(symbol) for symbol in ('011280', '038110', '264450', '352770')}
            held, audit = builder.guard_account_records(source, root, '2026-11-06T09:29:26+00:00')
            data = {'generated_at': '2026-11-05T12:12:44+00:00', 'records': held, 'account_integrity': audit}
            (root / builder.OUTPUT).write_text(json.dumps(data))
            apply_review(root, REVIEW)
            previous = json.loads((root / builder.OUTPUT).read_text())
            previous['records']['KR:011280']['account_validation']['note'] = '공시에 적힌 세 금액을 그대로 표시합니다.'
            previous['records']['KR:011280']['limitations'] = ['공시에 적힌 세 금액을 그대로 표시합니다.']
            for key in ('KR:038110', 'KR:264450', 'KR:352770'):
                previous['records'][key]['account_validation']['balance_sheet'].pop('source_review')
                previous['records'][key]['account_validation']['note'] = '원문을 재확인해야 합니다.'
                previous['records'][key]['limitations'] = ['원문을 재확인해야 합니다.']
            (root / builder.OUTPUT).write_text(json.dumps(previous))
            archive = (root / builder.ACCOUNT_QUARANTINE_OUTPUT).read_bytes()
            result = apply_review(root, REVIEW)
            after = json.loads((root / builder.OUTPUT).read_text())
            self.assertEqual(result['restored_fields'], 0)
            self.assertEqual(len(result['changed_records']), 4)
            self.assertEqual(after['account_integrity'], previous['account_integrity'])
            self.assertEqual(after['generated_at'], previous['generated_at'])
            for key, row in after['records'].items():
                self.assertEqual(row['metrics'], previous['records'][key]['metrics'])
                self.assertEqual(row['checked_at'], previous['records'][key]['checked_at'])
                self.assertEqual(row['account_validation']['audited_at'], previous['records'][key]['account_validation']['audited_at'])
            self.assertEqual(after['records']['KR:011280']['account_validation']['note'], RESTORED_NOTE)
            self.assertEqual(after['records']['KR:011280']['account_validation']['balance_sheet'],
                             previous['records']['KR:011280']['account_validation']['balance_sheet'])
            written = (root / builder.OUTPUT).read_bytes()
            again = apply_review(root, REVIEW)
            self.assertEqual(again['status'], 'already_reconciled')
            self.assertEqual(again['changed_records'], [])
            self.assertEqual((root / builder.OUTPUT).read_bytes(), written)
            self.assertEqual((root / builder.ACCOUNT_QUARANTINE_OUTPUT).read_bytes(), archive)

    def test_completed_review_rejects_changed_source_proof_record_or_archive(self):
        for alteration in ('proof_amount', 'proof_period', 'claimed_interval', 'current_receipt', 'archive_amount'):
            with self.subTest(alteration=alteration), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = {f'KR:{symbol}': original(symbol) for symbol in ('011280', '038110', '264450', '352770')}
                held, audit = builder.guard_account_records(source, root, '2026-11-06T09:29:26+00:00')
                review = copy.deepcopy(REVIEW)
                if alteration == 'proof_amount':
                    review['records']['KR:038110']['source_precision']['facts']['assets']['value'] = '1'
                elif alteration == 'proof_period':
                    review['records']['KR:038110']['source_precision']['context']['period']['instant'] = '2026-03-31'
                elif alteration == 'claimed_interval':
                    review['records']['KR:038110']['source_interval_result']['difference_interval'] = ['1', '2']
                elif alteration == 'current_receipt':
                    held['KR:038110']['rcept_no'] = '20261116000001'
                else:
                    archive = json.loads((root / builder.ACCOUNT_QUARANTINE_OUTPUT).read_text())
                    next(row for row in archive['records'] if row['previous_key'] == 'KR:038110')['record']['metrics']['assets'] += 1
                    (root / builder.ACCOUNT_QUARANTINE_OUTPUT).write_text(json.dumps(archive))
                (root / builder.OUTPUT).write_text(json.dumps({'generated_at': '2026-11-05T12:12:44+00:00',
                                                              'records': held, 'account_integrity': audit}))
                snapshot = (root / builder.OUTPUT).read_bytes()
                with self.assertRaises(ValueError):
                    apply_review(root, review)
                self.assertEqual((root / builder.OUTPUT).read_bytes(), snapshot)


if __name__ == '__main__':
    unittest.main()
