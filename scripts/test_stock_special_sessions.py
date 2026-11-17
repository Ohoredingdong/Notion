"""Offline boundary regressions for the 2026 KRX CSAT regular session."""
import unittest
from datetime import datetime, timezone
from market_data_utils import market_session_clock, completed_daily_points, exchange_calendar
from stock_entry_inputs import clock, completed
from stock_exchange_calendar import get_calendar


def at(time):
    return datetime.fromisoformat('2026-11-19T' + time + '+09:00')


class SpecialSessions(unittest.TestCase):
    def test_open_and_close(self):
        c = exchange_calendar('KR', 2026)
        self.assertEqual(c.session_open('2026-11-19').hour, 1)
        self.assertEqual(c.session_close('2026-11-19').hour, 7)
        self.assertEqual(c.session_close('2026-11-19').minute, 30)
        self.assertFalse(market_session_clock('KR', at('09:59'))['market_open'])
        self.assertTrue(market_session_clock('KR', at('10:00'))['market_open'])
        self.assertTrue(market_session_clock('KR', at('16:29'))['market_open'])
        self.assertFalse(market_session_clock('KR', at('16:30'))['market_open'])

    def test_completed_buffer_and_entry_agree(self):
        for time, expected in [('16:00','2026-11-18'), ('16:30','2026-11-18'),
                               ('16:59:59','2026-11-18'), ('17:00','2026-11-19')]:
            self.assertEqual(market_session_clock('KR', at(time))['expected_session'], expected)
            self.assertEqual(clock('KR', at(time))['date'], expected)
        self.assertFalse(completed('2026-11-19','KR',at('16:59').isoformat(),at('17:00')))
        self.assertTrue(completed('2026-11-19','KR',at('17:00').isoformat(),at('17:00')))

    def test_live_daily_bar_rejected(self):
        points=[('2026-11-18',100),('2026-11-19',101)]
        self.assertEqual(len(completed_daily_points(points,'KR',at('16:00'))[0]),1)
        self.assertEqual(len(completed_daily_points(points,'KR',at('17:00'))[0]),2)

    def test_schedule_and_next_boundary_consistent(self):
        c=exchange_calendar('KR',2026)
        self.assertEqual(c.schedule.loc['2026-11-19','close'],c.session_close('2026-11-19'))
        timing=market_session_clock('KR',at('16:00'))
        self.assertEqual(timing['next_open'],'2026-11-19T01:00:00+00:00')
        self.assertEqual(timing['next_close'],'2026-11-19T07:30:00+00:00')

    def test_all_production_calendar_routes_agree(self):
        from stock_forecast_model import calendar as forecast_calendar
        from build_stock_world_flow import calendar as world_calendar
        from update_stock_decisions import latest_session
        for c in [forecast_calendar('KR',2026),world_calendar('XKRX',2026)]:
            self.assertEqual(c.session_open('2026-11-19').hour,1)
            self.assertEqual(c.session_close('2026-11-19').hour,7)
        self.assertEqual(latest_session('KR',at('16:00'))['date'],'2026-11-18')
        self.assertEqual(latest_session('KR',at('17:00'))['date'],'2026-11-19')

    def test_surrounding_holidays_and_us_unaffected(self):
        c=exchange_calendar('KR',2026)
        for day in ['2026-11-18','2026-11-20']:
            self.assertEqual(c.session_open(day).hour,0)
            self.assertEqual(c.session_close(day).hour,6)
        self.assertFalse(c.is_session('2026-11-21'))
        self.assertFalse(c.is_session('2026-12-25'))
        us=get_calendar('XNYS',start='2026-01-01',end='2026-12-31')
        self.assertEqual(us.session_close('2026-11-27').hour,18)

if __name__ == '__main__': unittest.main()
