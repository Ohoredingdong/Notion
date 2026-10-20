#!/usr/bin/env python3
"""Collect actual BOK and KFB announcements; keep the last good source on failure."""
import json
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "mortgage-rates-data.json"
BOK = "https://www.bok.or.kr/portal/singl/baseRate/list.do?menuNo=200643"
KFB = "https://m.kfb.or.kr/eng/cofix/cofix.php"
KFB_KO = "https://portal.kfb.or.kr/fingoods/cofix.php"
KST = ZoneInfo("Asia/Seoul")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NotionMortgageRateWatch/1.0)"}


def document(url):
    response = requests.get(url, headers=HEADERS, timeout=35)
    response.raise_for_status()
    # Both official pages declare their own encoding in HTML.
    return BeautifulSoup(response.content, "html.parser")


def percent(raw):
    value = float(str(raw).strip().replace("%", ""))
    if not 0 <= value <= 30:
        raise ValueError("Rate outside the expected percentage range")
    return value


def official_date(raw):
    result = date.fromisoformat(raw.replace("/", "-").replace(".", "-"))
    if result > datetime.now(KST).date():
        raise ValueError("Official date is in the future")
    return result.isoformat()


def collect_bok(soup=None):
    soup = soup if soup is not None else document(BOK)
    rows, year = [], None
    for tr in soup.select("table tr"):
        cells = [e.get_text(" ", strip=True) for e in tr.select("td")]
        if not cells:
            continue
        if re.fullmatch(r"20\d{2}", cells[0]):
            year, cells = int(cells[0]), cells[1:]
        if not year or len(cells) < 2:
            continue
        match = re.fullmatch(r"(\d{1,2})월\s*(\d{1,2})일", cells[0])
        if not match:
            continue
        stamp = official_date(f"{year:04d}-{int(match[1]):02d}-{int(match[2]):02d}")
        rows.append((stamp, percent(cells[1])))
    rows = sorted(set(rows), reverse=True)
    if len(rows) < 2 or rows[0][0] == rows[1][0]:
        raise ValueError("BOK current and previous dated announcements were not found")
    return {"value": rows[0][1], "previous": rows[1][1],
            "changed_at": rows[0][0], "previous_changed_at": rows[1][0],
            "source_url": BOK}


def collect_cofix(soup=None):
    soup = soup if soup is not None else document(KFB)
    rows = []
    for tr in soup.select("table tr"):
        cells = [e.get_text(" ", strip=True) for e in tr.select("td")]
        if len(cells) != 5 or not re.fullmatch(r"20\d{2}/\d{2}/\d{2}", cells[0]):
            continue
        if not re.fullmatch(r"20\d{2}/\d{2}", cells[1]):
            continue
        published = official_date(cells[0])
        month = cells[1].replace("/", "-")
        if month >= published[:7]:
            raise ValueError("COFIX reference month must precede publication")
        rows.append({"published_at": published, "reference_month": month,
                     "new_funds": percent(cells[2]), "outstanding": percent(cells[3]),
                     "new_outstanding": percent(cells[4])})
    rows.sort(key=lambda r: (r["published_at"], r["reference_month"]), reverse=True)
    if len(rows) < 2 or rows[0]["reference_month"] <= rows[1]["reference_month"]:
        raise ValueError("Two distinct COFIX monthly announcements were not found")
    return {**rows[0], "previous": rows[1], "source_url": KFB_KO,
            "data_source_url": KFB}


def refresh():
    previous = json.loads(OUT.read_text()) if OUT.exists() else {}
    now = datetime.now(KST).isoformat(timespec="seconds")
    data = {"schema_version": 1, "checked_at": now,
            "update_schedule": "매일 공식 발표 확인 · COFIX 월별 발표",
            "sources": {}}
    for name, collector in (("base_rate", collect_bok), ("cofix", collect_cofix)):
        old = previous.get(name)
        try:
            value = collector()
            date_key = "changed_at" if name == "base_rate" else "published_at"
            if old and value[date_key] < old[date_key]:
                raise ValueError("Refusing an older official announcement")
            data[name] = value
            data["sources"][name] = {"status": "ok", "checked_at": now, "last_success_at": now}
        except Exception as exc:
            if old:
                data[name] = old
            data["sources"][name] = {
                "status": "stale" if old else "unavailable", "checked_at": now,
                "last_success_at": (previous.get("sources", {}).get(name) or {}).get("last_success_at"),
                "error": str(exc)[:300],
            }
            print(f"{name}: official collection failed; retained last good announcement: {exc}")
    errors = sum(v["status"] != "ok" for v in data["sources"].values())
    data["status"] = "ok" if errors == 0 else "partial" if errors == 1 else "error"
    temp = OUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(OUT)
    print(f"Mortgage references: {data['status']}; checked {now}")
    return errors == 0


if __name__ == "__main__":
    raise SystemExit(0 if refresh() else 1)
