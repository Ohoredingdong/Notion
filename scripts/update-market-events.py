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
    ("growth", ["gdp","pmi","retail sales","industrial production","consumer confidence","consumer sentiment","business confidence","business climate","ifo","ism"]),
]

EXACT_TRANSLATIONS = {
    "Ifo Business Climate": "Ifo 기업환경지수",
    "S&P Global Manufacturing PMI Flash": "S&P 글로벌 제조업 PMI 잠정치",
    "S&P Global Services PMI Flash": "S&P 글로벌 서비스업 PMI 잠정치",
    "GDP Growth Rate QoQ 2nd Est": "GDP 성장률 전분기 대비 2차 추정치",
    "Durable Goods Orders MoM": "내구재 주문 전월 대비",
    "Core PCE Price Index MoM": "근원 PCE 물가지수 전월 대비",
    "Personal Spending MoM": "개인소비지출 전월 대비",
    "Personal Income MoM": "개인소득 전월 대비",
    "GfK Consumer Confidence": "GfK 소비자신뢰지수",
    "Consumer Confidence": "소비자신뢰지수",
    "Inflation Rate YoY Prel": "물가상승률 전년 대비 잠정치",
    "Non Farm Payrolls Annual Revision Prel": "비농업 고용 연간 수정 잠정치",
    "NBS Manufacturing PMI": "중국 NBS 제조업 PMI",
    "RatingDog Manufacturing PMI": "중국 RatingDog 제조업 PMI",
    "ISM Manufacturing PMI": "미국 ISM 제조업 PMI",
    "JOLTS Job Openings": "JOLTs 구인건수",
    "Retail Sales MoM": "소매판매 전월 대비",
    "Crude Oil Stocks Change": "원유 재고 증감",
}

TRANSLATIONS = [
    (r"Fed Interest Rate Decision", "연준 금리 결정"),
    (r"Interest Rate Decision", "금리 결정"),
    (r"Consumer Price Index", "소비자물가지수"),
    (r"Producer Price Index", "생산자물가지수"),
    (r"Core PCE Price Index", "근원 PCE 물가지수"),
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
    (r"Durable Goods Orders", "내구재 주문"),
    (r"Personal Spending", "개인소비지출"),
    (r"Personal Income", "개인소득"),
    (r"Business Climate", "기업환경지수"),
    (r"Manufacturing PMI", "제조업 PMI"),
    (r"Services PMI", "서비스업 PMI"),
    (r"Fed Chair .* Speech", "연준 의장 연설"),
    (r"Fed .* Speech", "연준 인사 연설"),
    (r"Crude Oil Stocks Change", "원유 재고 증감"),
    (r"\bFlash\b", "잠정치"),
    (r"\bPrel\b", "잠정치"),
    (r"\b2nd Est\b", "2차 추정치"),
    (r"\bAnnual Revision\b", "연간 수정"),
    (r"\bYoY\b", "전년 대비"),
    (r"\bMoM\b", "전월 대비"),
    (r"\bQoQ\b", "전분기 대비"),
]

def category(title: str) -> str:
    t = title.lower()
    for cat, words in KEYWORDS:
        if any(w in t for w in words):
            return cat
    return "other"

def title_ko(title: str) -> str:
    if title in EXACT_TRANSLATIONS:
        return EXACT_TRANSLATIONS[title]
    out = title
    for pat, rep in TRANSLATIONS:
        out = re.sub(pat, rep, out, flags=re.I)
    out = re.sub(r"\s+", " ", out).strip()
    return out

def comment_ko(title: str, cat: str, country: str) -> str:
    exact = {
        "Ifo Business Climate": "독일 기업들의 현재 경기 판단과 향후 6개월 전망을 보여주는 대표적인 기업심리지표입니다.",
        "FOMC Interest Rate Decision": "미국 연방공개시장위원회(FOMC)의 기준금리 결정과 향후 통화정책 방향을 확인하는 핵심 이벤트입니다.",
        "Fed Interest Rate Decision": "미국 연방준비제도의 금리 결정과 향후 통화정책 방향을 확인하는 핵심 이벤트입니다.",
        "Core PCE Price Index MoM": "미 연준이 중요하게 보는 근원 PCE 물가의 월간 변화를 확인하는 인플레이션 지표입니다.",
        "Non Farm Payrolls Annual Revision Prel": "미국 비농업 고용 통계의 연간 수정 규모를 확인하는 고용시장 이벤트입니다.",
        "ISM Manufacturing PMI": "미국 제조업 경기의 확장·위축 흐름을 보여주는 대표적인 선행 경기지표입니다.",
    }
    if title in exact:
        return exact[title]
    if cat == "rate":
        return "중앙은행의 기준금리 결정과 향후 통화정책 방향을 확인하는 이벤트입니다."
    if cat == "inflation":
        return "물가 상승 압력과 향후 통화정책 방향에 영향을 줄 수 있는 인플레이션 지표입니다."
    if cat == "jobs":
        return "고용시장 강도와 경기 흐름을 확인하는 주요 고용지표입니다."
    if cat == "growth":
        return "경기 확장·위축과 기업·소비자 심리를 확인하는 주요 경기지표입니다."
    return "금융시장에 영향을 줄 수 있는 주요 경제 일정입니다."

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
    cat = category(title)
    country = row.get("country") or ""
    return {
        "id": str(row.get("id") or ""),
        "title": title,
        "title_ko": title_ko(title),
        "country": country,
        "currency": row.get("currency") or "",
        "importance": imp,
        "category": cat,
        "datetime_kst": dt.isoformat(),
        "date_kst": f"{dt.month}월 {dt.day}일 ({'월화수목금토일'[dt.weekday()]})",
        "time_kst": dt.strftime("%H:%M"),
        "bucket": bucket_for(dt, now),
        "actual": row.get("actual"),
        "forecast": row.get("forecast"),
        "previous": row.get("previous"),
        "comment": (row.get("comment") or "")[:220],
        "comment_ko": comment_ko(title, cat, country),
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
