"""Collect dated, public first-party supply-chain releases; preserve valid values."""
from __future__ import annotations

import calendar
import csv
import io
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'supply-chain-data.json'
NYFED = 'https://www.newyorkfed.org/research/policy/gscpi'
NYFED_CSV = 'https://www.newyorkfed.org/medialibrary/research/interactives/data/gscpi/gscpi_interactive_data.csv'
ISM = 'https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/pmi/'
ISM_RELEASES = 'https://www.prnewswire.com/news/institute-for-supply-management/'
DREWRY = 'https://www.drewry.co.uk/trackers-and-indices/latest-trackers-and-indices/world-container-index-assessed-by-drewry'
MONTHS = {name.lower(): number for number, name in enumerate(calendar.month_name) if name}


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def text(html):
    parser = TextParser()
    parser.feed(html)
    return re.sub(r'\s+', ' ', ' '.join(parser.parts))


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=25) as response:
        if '/errors/404' in response.url or '/SSO/' in response.url:
            raise ValueError('Public report is unavailable at this URL')
        return response.read().decode('utf-8-sig')


def parse_gscpi(raw):
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows or rows[0][0] != 'Date':
        raise ValueError('NYFed observation CSV missing Date column')
    # Columns are release vintages, rows are observation months. Use one vintage
    # for the entire history so revisions do not mix different releases.
    vintage_columns = [i for i, value in enumerate(rows[0]) if i and re.fullmatch(r'[A-Z][a-z]{2}-\d{2}', value)]
    points = []
    for column in reversed(vintage_columns):
        points = []
        for row in rows[1:]:
            try:
                date = datetime.strptime(row[0], '%d-%b-%Y')
                value = float(row[column])
            except (ValueError, IndexError):
                continue
            points.append({'label': date.strftime('%m'), 'date': date.date().isoformat(), 'value': value})
        if points:
            break
    if len(points) < 2:
        raise ValueError('NYFed CSV has fewer than two observations')
    points.sort(key=lambda point: point['date'])
    return {'value': points[-1]['value'], 'previous': points[-2]['value'],
            'reference_month': points[-1]['date'][:7], 'reference_date': points[-1]['date'],
            'source_vintage': datetime.strptime(rows[0][column], '%b-%y').strftime('%Y-%m'),
            'history': points[-6:], 'primary_source': 'Federal Reserve Bank of New York',
            'source_url': NYFED_CSV, 'stale': False, 'cadence': 'monthly'}


def parse_ism(html, source_url):
    report = text(html)
    match = re.search(r'([A-Za-z]+)\s+(20\d{2})\s+ISM.{0,12}Manufacturing PMI', report, re.I)
    if not match or match.group(1).lower() not in MONTHS:
        raise ValueError('ISM report observation month missing')
    month = f'{int(match.group(2)):04d}-{MONTHS[match.group(1).lower()]:02d}'
    result = {}
    for key, label in [('supplier_deliveries', 'Supplier Deliveries'), ('ism_prices', 'Prices')]:
        row = re.search(r'\b' + label + r'\s+([0-9]+(?:\.[0-9]+)?)\s+([0-9]+(?:\.[0-9]+)?)\s+([+−-]?[0-9]+(?:\.[0-9]+)?)(?:\s|$)', report, re.I)
        if not row:
            raise ValueError(f'ISM at-a-glance row missing: {label}')
        value, previous = float(row.group(1)), float(row.group(2))
        if not (0 <= value <= 100 and 0 <= previous <= 100):
            raise ValueError('ISM index outside 0–100')
        result[key] = {'value': value, 'previous': previous, 'change': round(value - previous, 1),
                       'reference_month': month, 'source_url': source_url, 'cadence': 'monthly', 'stale': False}
    return result


def collect_ism():
    # ISM's public month pages are sometimes moved; the institute's own public
    # release channel carries the same monthly report without requiring a login.
    listing = get(ISM_RELEASES)
    links = set(re.findall(r'href=["\']([^"\']*manufacturing-pmi[^"\']*)["\']', listing))
    dated = []
    for link in links:
        match = re.search(r'-(' + '|'.join(MONTHS) + r')-(20\d{2})-ism-manufacturing-pmi-report-', link)
        if match:
            dated.append(((int(match.group(2)), MONTHS[match.group(1)]), link))
    if not dated:
        raise ValueError('No dated ISM manufacturing release in the official release channel')
    url = urllib.parse.urljoin(ISM_RELEASES, max(dated)[1])
    return parse_ism(get(url), url)


def parse_wci(html, source_url=DREWRY):
    report = text(html)
    pattern = (r'(\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2})\s*[:–-]?\s*(?:Drewry[’\']?s?\s+)?World Container Index.{0,100}?'
               r'(?:(increased|decreased|rose|fell|dropped|declined)\s+([0-9.]+)%\s+to|(?:remained|was)\s+(?:stable|unchanged)\s+at)\s+\$([0-9,]+)\s+per\s+40(?:ft|[- ]foot)')
    match = re.search(pattern, report, re.I)
    if not match:
        raise ValueError('Dated WCI weekly quote missing')
    date = None
    for fmt in ('%d %b %Y', '%d %B %Y'):
        try:
            date = datetime.strptime(match.group(1), fmt).date().isoformat()
            break
        except ValueError:
            pass
    if not date:
        raise ValueError('WCI release date unreadable')
    pct = float(match.group(3)) * (1 if match.group(2).lower() in ('increased', 'rose') else -1) if match.group(2) else 0.0
    return {'value': int(match.group(4).replace(',', '')), 'change_pct': pct,
            'reference_date': date, 'source_url': source_url, 'cadence': 'weekly', 'stale': False}


def main():
    checked = datetime.now(timezone.utc).isoformat()
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    data = dict(old)
    errors = []
    successes = 0
    for keys, fetch in [(['gscpi'], lambda: {'gscpi': parse_gscpi(get(NYFED_CSV))}),
                        (['supplier_deliveries', 'ism_prices'], collect_ism),
                        (['wci'], lambda: {'wci': parse_wci(get(DREWRY))})]:
        try:
            values = fetch()
            for key, value in values.items():
                value['checked_at'] = checked
                data[key] = value
            successes += 1
        except Exception as exc:
            errors.append(f'{" / ".join(keys)}: {exc}')
            for key in keys:
                data[key] = {**(old.get(key) or {}), 'checked_at': checked, 'stale': True, 'error': str(exc)[:180]}
            print(f'::warning::{keys}: kept last valid release: {exc}')
    data['checked_at'] = checked
    if successes:
        data['generated_at'] = checked
    periods = [x.get('reference_date') or (x.get('reference_month') + '-01' if x.get('reference_month') else None)
               for key in ('gscpi', 'supplier_deliveries', 'ism_prices', 'wci') if isinstance(x := data.get(key), dict)]
    # Each card shows its own reference period; this is the newest actual release.
    data['data_as_of'] = max([x for x in periods if x and re.fullmatch(r'20\d{2}-\d{2}-\d{2}', x)], default=None)
    data['sources'] = {'nyfed': NYFED, 'nyfed_data': NYFED_CSV, 'ism': ISM_RELEASES, 'drewry': DREWRY}
    data['stale'] = bool(errors)
    data['last_errors'] = errors
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
