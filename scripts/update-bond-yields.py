#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "bond-yields-data.json"
KST = ZoneInfo("Asia/Seoul")

TICKERS = {
    "KR": {
        "2Y": "TVC:KR02Y",
        "3Y": "TVC:KR03Y",
        "5Y": "TVC:KR05Y",
        "10Y": "TVC:KR10Y",
        "30Y": "TVC:KR30Y",
    },
    "US": {
        "3M": "TVC:US03MY",
        "2Y": "TVC:US02Y",
        "5Y": "TVC:US05Y",
        "10Y": "TVC:US10Y",
        "30Y": "TVC:US30Y",
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36",
    "Accept": "text/plain, */*; q=0.01",
    "Content-Type": "application/json",
    "Origin": "https://www.tradingview.com",
    "Referer": "https://www.tradingview.com/",
}


def load_old() -> dict:
    if not DATA.exists():
        return {}
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except Exception:
        return {}


def post_scanner(tickers: list[str]) -> dict:
    payload = {
        "symbols": {"tickers": tickers, "query": {"types": []}},
        "columns": ["name", "close", "change", "description"],
    }
    last_error = None
    for endpoint in (
        "https://scanner.tradingview.com/bond/scan",
        "https://scanner.tradingview.com/global/scan",
    ):
        try:
            r = requests.post(endpoint, json=payload, headers=HEADERS, timeout=25)
            r.raise_for_status()
            data = r.json()
            if data.get("data"):
                return data
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"TradingView scanner failed: {last_error}")


def finite_number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def change_bp_from_pct(current: float, change_pct: float | None) -> float:
    if change_pct is None or change_pct <= -99.999:
        return 0.0
    previous = current / (1.0 + change_pct / 100.0)
    return (current - previous) * 100.0


def main() -> None:
    old = load_old()
    all_tickers = [ticker for country in TICKERS.values() for ticker in country.values()]
    scan = post_scanner(all_tickers)
    rows = {}
    columns = ["name", "close", "change", "description"]

    for item in scan.get("data", []):
        symbol = item.get("s")
        values = item.get("d") or []
        row = dict(zip(columns, values))
        rows[symbol] = row

    now = datetime.now(KST)
    now_epoch = int(time.time())
    stale = False
    countries = {}

    for country, maturities in TICKERS.items():
        old_country = old.get("countries", {}).get(country, {})
        old_yields = old_country.get("yields", {})
        yields = {}

        for maturity, ticker in maturities.items():
            row = rows.get(ticker, {})
            current = finite_number(row.get("close"))
            change_pct = finite_number(row.get("change"))
            if current is None:
                stale = True
                previous = old_yields.get(maturity, {})
                current = finite_number(previous.get("yield")) or 0.0
                change_bp = finite_number(previous.get("change_bp")) or 0.0
            else:
                change_bp = change_bp_from_pct(current, change_pct)

            yields[maturity] = {
                "yield": round(current, 3),
                "change_bp": round(change_bp, 1),
                "ticker": ticker,
            }

        if country == "KR":
            spread_label = "장단기 금리차 (10년-3년)"
            spread_bp = (yields["10Y"]["yield"] - yields["3Y"]["yield"]) * 100
        else:
            spread_label = "장단기 금리차 (10년-2년)"
            spread_bp = (yields["10Y"]["yield"] - yields["2Y"]["yield"]) * 100

        history = old_country.get("history", [])
        if not isinstance(history, list):
            history = []
        main_yield = yields["10Y"]["yield"]
        if main_yield > 0:
            history.append([now_epoch, main_yield])
        history = history[-96:]

        countries[country] = {
            "label": "한국" if country == "KR" else "미국",
            "main": "10Y",
            "spread": {"label": spread_label, "value_bp": round(spread_bp, 1)},
            "history": history,
            "yields": yields,
        }

    output = {
        "generated_at": now.isoformat(),
        "source": "TradingView government bond yield snapshots",
        "source_note": "TVC government-bond yield symbols; delayed/indicative market data may apply.",
        "stale": stale,
        "countries": countries,
    }
    DATA.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
