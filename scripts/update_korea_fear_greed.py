"""Fetch the published Korean KOSPI/KOSDAQ fear-greed readings with attribution.

This is a third-party, daily AFTER-CLOSE index, NOT CNN's US index, a trading
signal, or an intraday value. Never synthesise scores if the API is unavailable.
"""
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json
import math

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "stock-korea-fear-greed.json"
URL = "https://www.koreafeargreed.com/api/fear-greed/latest"
SITE = "https://www.koreafeargreed.com"
UA = "StockRadarResearchDashboard/1.0 (+https://github.com/Ohoredingdong/Notion)"

def valid_score(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Non-numeric sentiment index")
    number = float(value)
    if not math.isfinite(number) or not (0 <= number <= 100):
        raise ValueError("Sentiment index out of range")
    return number

def run():
    request = Request(URL, headers={"Accept": "application/json", "User-Agent": UA})
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"Korean sentiment API returned {response.status}")
        body = response.read(250_000)
    data = json.loads(body.decode("utf-8"))
    source_date = date.fromisoformat(str(data["date"]))
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    if source_date > today:
        raise ValueError("Future-dated Korean sentiment response")
    indices = {}
    for market in ("kospi", "kosdaq"):
        record = data[market]
        indices[market] = {
            "index": valid_score(record["index"]),
            "label": str(record.get("label", "확인 전"))[:50],
            "close": record.get("close") if isinstance(record.get("close"), (float, int)) else None,
        }
    output = {
        "version": str(data.get("version", "unknown")),
        "market": "kr",
        "date": source_date.isoformat(),
        "source": "한국 공포탐욕지수",
        "source_url": SITE,
        "api_url": URL,
        "attribution": "출처: 한국 공포탐욕지수 " + SITE,
        "license": str(data.get("license", "출처를 표시해 주세요.")),
        "method_note": "KOSPI·KOSDAQ 별도 민간 계산 지수. 미국 CNN과 구성·산출법이 다르며 매수·매도 신호가 아닙니다.",
        "source_period": "장 마감 기준 · 매 거래일 장 마감 후 갱신",
        **indices,
    }
    if DEST.exists():
        before = json.loads(DEST.read_text(encoding="utf-8"))
        prev_date = date.fromisoformat(str(before.get("date", "1900-01-01")))
        if prev_date > source_date:
            raise ValueError("API returned a session older than the last published reading")
    wire = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if DEST.exists() and DEST.read_text(encoding="utf-8") == wire:
        print("No Korean sentiment update; published date", source_date)
        return
    DEST.write_text(wire, encoding="utf-8")
    print("Updated Korean sentiment:", source_date, "KOSPI", indices["kospi"]["index"],
          "KOSDAQ", indices["kosdaq"]["index"])

if __name__ == "__main__":
    run()
