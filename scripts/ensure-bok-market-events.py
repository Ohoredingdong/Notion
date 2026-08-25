from __future__ import annotations

import html as html_lib
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

DATA = Path('market-events-data.json')
KST = ZoneInfo('Asia/Seoul')
BOK_URL = 'https://www.bok.or.kr/portal/singl/crncyPolicyDrcMtg/listYear.do'
BOK_SOURCE_URL = 'https://www.bok.or.kr/portal/singl/crncyPolicyDrcMtg/listYear.do?menuNo=200755&mtgSe=A'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36'

# Official 2026 BOK monetary-policy decision dates. Fallback only if the
# official annual schedule page cannot be parsed during an update.
FALLBACK = {
    2026: [(1, 15), (2, 26), (4, 10), (5, 28), (7, 16), (8, 27), (10, 22), (11, 26)],
}


def fetch_dates(year: int) -> list[date]:
    try:
        r = requests.get(
            BOK_URL,
            params={'menuNo': '200755', 'mtgSe': 'A', 'pYear': str(year)},
            headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml'},
            timeout=25,
        )
        r.raise_for_status()
        text = html_lib.unescape(re.sub(r'<[^>]+>', ' ', r.text))
        text = re.sub(r'\s+', ' ', text)
        if '통화정책방향 회의' in text:
            text = text.split('통화정책방향 회의', 1)[1]
        if '담당부서' in text:
            text = text.split('담당부서', 1)[0]
        dates = []
        for month, day in re.findall(r'(\d{1,2})월\s*(\d{1,2})일', text):
            try:
                dates.append(date(year, int(month), int(day)))
            except ValueError:
                pass
        dates = sorted(set(dates))
        if dates:
            return dates
    except Exception as exc:
        print(f'BOK schedule fetch warning: {exc}', file=sys.stderr)
    return [date(year, m, d) for m, d in FALLBACK.get(year, [])]


def bucket_for(dt: datetime, now: datetime) -> str:
    if dt.date() == now.date():
        return 'today'
    week_end = now.date() + timedelta(days=(6 - now.weekday()))
    return 'week' if dt.date() <= week_end else 'later'


def event_for(meeting: date, now: datetime) -> dict:
    # The official annual schedule verifies the date but not a clock time.
    # Noon is only an internal sort key; UI displays "시간 미정".
    dt = datetime(meeting.year, meeting.month, meeting.day, 12, 0, tzinfo=KST)
    return {
        'id': f'official-bok-{meeting.isoformat()}',
        'title': 'Bank of Korea Monetary Policy Decision',
        'title_ko': '한국은행 기준금리 결정',
        'country': 'KR',
        'currency': 'KRW',
        'source_importance': 3,
        'importance': 3,
        'impact_level': 3,
        'impact_reason': 'official:bank-of-korea',
        'category': 'rate',
        'datetime_kst': dt.isoformat(),
        'date_kst': f"{dt.month}월 {dt.day}일 ({'월화수목금토일'[dt.weekday()]})",
        'time_kst': '시간 미정',
        'time_is_tba': True,
        'bucket': bucket_for(dt, now),
        'actual': None,
        'forecast': None,
        'previous': None,
        'comment': '',
        'comment_ko': '한국은행 금융통화위원회가 기준금리 수준과 통화정책 방향을 결정하는 핵심 일정입니다.',
        'time_verification': {
            'verified': True,
            'date_verified': True,
            'time_verified': False,
            'agency': 'Bank of Korea',
            'url': BOK_SOURCE_URL,
            'note': 'Official meeting date verified; decision time is not stated on the annual schedule page.',
        },
        'source_type': 'official_schedule',
    }


def same_day_kr_rate(event: dict, meeting: date) -> bool:
    if event.get('country') != 'KR':
        return False
    try:
        event_date = datetime.fromisoformat(event['datetime_kst']).date()
    except Exception:
        return False
    title = (event.get('title') or '').lower()
    is_rate = event.get('category') == 'rate' or any(
        key in title for key in ('bank of korea', 'interest rate decision', 'base rate')
    )
    return event_date == meeting and is_rate


def main() -> None:
    if not DATA.exists():
        raise SystemExit('market-events-data.json missing')

    payload = json.loads(DATA.read_text(encoding='utf-8'))
    now = datetime.now(KST)
    horizon_start = now.date() - timedelta(days=1)
    horizon_end = (now + timedelta(days=14)).date()

    meeting_dates = []
    for year in sorted({horizon_start.year, horizon_end.year}):
        meeting_dates.extend(fetch_dates(year))
    meeting_dates = sorted({d for d in meeting_dates if horizon_start <= d <= horizon_end})

    events = list(payload.get('events') or [])
    for meeting in meeting_dates:
        existing = [e for e in events if same_day_kr_rate(e, meeting)]
        official = event_for(meeting, now)
        if existing:
            # Preserve a source-provided clock time if available, but mark it as not
            # official-verified. The BOK annual schedule remains the date authority.
            candidate = existing[0]
            if candidate.get('time_kst') and candidate.get('time_kst') != '시간 미정':
                official['datetime_kst'] = candidate['datetime_kst']
                official['time_kst'] = candidate['time_kst']
                official['time_is_tba'] = False
                official['time_verification']['note'] = 'Date verified by Bank of Korea; clock time retained from source and is not official-verified.'
            events = [e for e in events if not same_day_kr_rate(e, meeting)]
        events.append(official)

    events.sort(key=lambda e: (e.get('datetime_kst', ''), -int(e.get('impact_level') or 0)))
    payload['events'] = events

    accuracy = payload.setdefault('accuracy', {})
    agencies = list(accuracy.get('official_agencies') or [])
    if 'Bank of Korea' not in agencies:
        agencies.insert(0, 'Bank of Korea')
    accuracy['official_agencies'] = agencies
    accuracy.setdefault('official_schedule_sources', {})['KR_policy_decisions'] = BOK_SOURCE_URL

    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
