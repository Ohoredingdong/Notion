from __future__ import annotations
import json, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

OUT = Path("market-events-data.json")
KST = ZoneInfo("Asia/Seoul")
URL = "https://economic-calendar.tradingview.com/events"
COUNTRIES = ["US","KR","JP","GB","DE","FR","CN"]

HEADERS = {
    "Origin": "https://www.tradingview.com",
    "Referer": "https://www.tradingview.com/economic-calendar/",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}

KEYWORDS = [
    ("rate", ["interest rate decision","fomc","fed interest rate","boe interest rate","ecb interest rate","boj interest rate","bank of korea","base rate"]),
    ("inflation", ["cpi","consumer price","ppi","producer price","inflation","pce price","core pce"]),
    ("jobs", ["non farm payroll","nonfarm payroll","unemployment","jobless","employment","jolts","average hourly earnings","claimant count"]),
    ("growth", ["gdp","pmi","retail sales","industrial production","consumer confidence","consumer sentiment","business confidence","ism"]),
]

TRANSLATIONS = [
    (r"Interest Rate Decision", "금리 결정"),
    (r"Fed Interest Rate Decision", "연준 금리 결정"),
    (r"Consumer Price Index", "소비자물가지수"),
    (r"Producer Price Index", "생산자물가지수"),
    (r"Non Farm Payrolls|Nonfarm Payrolls", "비농업 고용"),
    (r"Unemployment Rate", "실업률"),
    (r"Initial Jobless Claims", "신규 실업수당 청구건수"),
    (r"Continuing Jobless Claims", "계속 실업수당 청구건수"),
    (r"JOLTS Job Openings", "JOLTs 구인건수"),
    (r"Gross Domestic Product", "GDP"),
    (r"Retail Sales", "소매판매"),
    (r"Consumer Confidence", "소비자신뢰지수"),
    (r"Consumer Sentiment", "소비자심리지수"),
    (r"Industrial Production", "산업생산"),
    (r"Fed Chair .* Speech", "연준 의장 연설"),
    (r"Fed .* Speech", "연준 인사 연설"),
    (r"Crude Oil Stocks Change", "원유 재고"),
]

def category(title: str) -> str:
    t = title.lower()
    for cat, words in KEYWORDS:
        if any(w in t for w in words):
            return cat
    return "other"

def title_ko(title: str) -> str:
    out = title
    for pat, rep in TRANSLATIONS:
        out = re.sub(pat, rep, out, flags=re.I)
    return out

def parse_dt(value: str) -> datetime:
    if not value:
        raise ValueError("missing date")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)

def bucket_for(dt: datetime, now: datetime) -> str:
    if dt.date() == now.date():
        return "today"
    week_end = now.date() + timedelta(days=(6 - now.weekday()))
    return "week" if dt.date() <= week_end else "later"

def normalize(row: dict, now: datetime) -> dict | None:
    try:
        dt = parse_dt(row.get("date"))
    except Exception:
        return None
    if dt < now - timedelta(hours=6) or dt > now + timedelta(days=14):
        return None
    imp = int(row.get("importance") or 0)
    title = str(row.get("title") or "").strip()
    if imp <= 0 or not title:
        return None
    return {
        "id": str(row.get("id") or ""),
        "title": title,
        "title_ko": title_ko(title),
        "country": row.get("country") or "",
        "currency": row.get("currency") or "",
        "importance": imp,
        "category": category(title),
        "datetime_kst": dt.isoformat(),
        "date_kst": f"{dt.month}월 {dt.day}일 ({'월화수목금토일'[dt.weekday()]})",
        "time_kst": dt.strftime("%H:%M"),
        "bucket": bucket_for(dt, now),
        "actual": row.get("actual"),
        "forecast": row.get("forecast"),
        "previous": row.get("previous"),
        "comment": (row.get("comment") or "")[:220],
        "comment_ko": "",
    }

def fetch_rows() -> list[dict]:
    now_utc = datetime.now(timezone.utc)
    params = {
        "from": (now_utc - timedelta(hours=12)).isoformat(timespec="milliseconds").replace("+00:00","Z"),
        "to": (now_utc + timedelta(days=14)).isoformat(timespec="milliseconds").replace("+00:00","Z"),
        "countries": ",".join(COUNTRIES),
    }
    last = None
    for attempt in range(3):
        try:
            r = requests.get(URL, headers=HEADERS, params=params, timeout=25)
            r.raise_for_status()
            rows = r.json().get("result")
            if not isinstance(rows, list):
                raise RuntimeError("unexpected TradingView payload")
            return rows
        except Exception as e:
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"TradingView calendar fetch failed: {last}")

def main():
    now = datetime.now(KST)
    try:
        events = [e for e in (normalize(r, now) for r in fetch_rows()) if e]
        events.sort(key=lambda e: (e["datetime_kst"], -e["importance"]))
        high = [e for e in events if e["importance"] >= 2]
        if len(high) >= 9:
            events = high
        events = events[:36]
        upcoming = [e for e in events if datetime.fromisoformat(e["datetime_kst"]) >= now - timedelta(minutes=30)]
        highlight = sorted(upcoming or events, key=lambda e: (-e["importance"], e["datetime_kst"]))[0] if events else None
        out = {
            "source": "TradingView Economic Calendar",
            "source_url": "https://www.tradingview.com/economic-calendar/",
            "generated_at": now.isoformat(),
            "updated_label": now.strftime("%m.%d %H:%M"),
            "stale": False,
            "countries": COUNTRIES,
            "highlight": highlight,
            "events": events,
        }
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        if OUT.exists():
            old = json.loads(OUT.read_text(encoding="utf-8"))
            old["stale"] = True
            old["last_error"] = str(exc)
            old["last_attempt_at"] = now.isoformat()
            OUT.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")
            print(exc, file=sys.stderr)
            return
        raise

if __name__ == "__main__":
    main()
