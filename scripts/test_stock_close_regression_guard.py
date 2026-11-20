import unittest
from stock_close_regression_guard import guard_completed_closes,stable_universe_keys,SnapshotRegression


def snapshot(s='2026-11-19'):
    return {'version':'opportunity-v9.2','companies':[dict(symbol='AAPL',market='US',source_symbol='AAPL',currency='USD',status='current',price_session=s,price=100,
        price_source=dict(source_identity_verified=True,provider_symbol='AAPL',market='US',currency='USD',expected_session=s,latest_completed_session=s),
        price_integrity=dict(completed_session_match=True,expected_session=s,price_session=s))]}


class GuardTest(unittest.TestCase):
    def check(self, old, new, stable=frozenset({('US','AAPL')})):
        return guard_completed_closes(old,new,stable_keys=stable)

    def test_guard_allows_first_recovery(self):
        self.assertEqual(self.check(None,snapshot())['protected'],0)
        old=snapshot();old['companies'][0]['status']='failed'
        self.assertEqual(self.check(old,snapshot())['protected'],0)

    def test_allow_equal_and_later_close(self):
        for s in ('2026-11-19','2026-11-20'):
            self.assertEqual(self.check(snapshot(),snapshot(s))['protected'],1)

    def test_older_valid_looking_close(self):
        with self.assertRaisesRegex(SnapshotRegression,'completed_close_regressed'):
            self.check(snapshot(),snapshot('2026-11-18'))

    def test_detect_absence(self):
        new=snapshot();new['companies']=[]
        with self.assertRaisesRegex(SnapshotRegression,'missing_previously_accepted_stable_symbol'):
            self.check(snapshot(),new)

    def test_detect_downgrade(self):
        for field,value in [('status','incomplete'),('price',None),('price_source',{}),('price_integrity',{})]:
            new=snapshot();new['companies'][0][field]=value
            with self.assertRaisesRegex(SnapshotRegression,'downgraded_close_evidence'):
                self.check(snapshot(),new)

    def test_changed_identity_or_contract_requires_review(self):
        new=snapshot();new['companies'][0]['currency']='CAD';new['companies'][0]['price_source']['currency']='CAD'
        with self.assertRaisesRegex(SnapshotRegression,'issuer_or_currency_changed'):
            self.check(snapshot(),new)
    def test_compatible_version_change_still_checks_overlap(self):
        new=snapshot();new['version']='opportunity-next'
        self.assertEqual(self.check(snapshot(),new)['protected'],1)

    def test_dynamic_churn_and_overlap(self):
        new=snapshot();new['companies']=[]
        self.assertEqual(self.check(snapshot(),new,set())['discovery_exits'],1)
        with self.assertRaisesRegex(SnapshotRegression,'completed_close_regressed'):
            self.check(snapshot(),snapshot('2026-11-18'),set())

    def test_validate_stable_manifest(self):
        self.assertEqual(stable_universe_keys({'companies':[['AAPL','Apple','US','tech','AAPL']]}),{('US','AAPL')})
        with self.assertRaisesRegex(SnapshotRegression,'missing_stable_universe'):
            stable_universe_keys({'companies':[]})


if __name__=='__main__':
    unittest.main()
