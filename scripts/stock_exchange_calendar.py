"""Exchange calendars plus date-specific, sourced regular-session corrections.

No price data, weekday fallback, or global mutation of the vendor calendar.
"""

KRX_CSAT_DATE = '2026-11-19'
# KOSPI: KRX direct notice. KOSDAQ: broker notice, KRX direct notice pending.
KOSDAQ_CSAT_CORROBORATION = 'https://www.hanwhawm.com/main/bbs/indexView.cmd?cc_gubun=1&mode=center&nn_id=69155&pageVal=1&vc_bid=notice'
KRX_CSAT_SOURCE = 'https://kind.krx.co.kr/external/2026/11/05/000141/20261105000216/99303.htm'


def get_calendar(name, start=None, end=None):
    import exchange_calendars as xc
    if name != 'XKRX':
        return xc.get_calendar(name, start=start, end=end)
    import pandas as pd
    from exchange_calendars.exchange_calendar_xkrx import XKRXExchangeCalendar

    class VerifiedKRXCalendar(XKRXExchangeCalendar):
        @property
        def special_offsets_adhoc(self):
            # Preserve historical offsets, without applying a future upstream
            # correction twice. Absolute expected hours are tested separately.
            rows = super().special_offsets_adhoc
            day = pd.Timestamp(KRX_CSAT_DATE)
            if not any(day in dates for *offsets, dates in rows):
                rows = rows + [(pd.Timedelta(hours=1), None, None,
                                pd.Timedelta(hours=1), pd.DatetimeIndex([day]))]
            return rows

    return VerifiedKRXCalendar(start=start, end=end)
