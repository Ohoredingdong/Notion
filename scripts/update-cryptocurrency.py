from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# Live Upbit KRW spot updater for the Notion cryptocurrency widget.
OUT = Path("cryptocurrency-data.json")
KST = ZoneInfo("Asia/Seoul")
BASE = "https://api.upbit.com/v1"
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome/124 Safari/537.36"}

ASSETS = [
    ("KRW-BTC", "BTC", "Bitcoin"),
    ("KRW-ETH", "ETH", "Ethereum"),
    ("KRW-XRP", "XRP", "XRP"),
    ("KRW-SOL", "SOL", "Solana"),
    ("KRW-DOGE", "DOGE", "Dogecoin"),
]


def request_json(path: str, params=None):
    url = f"{BASE}{path}"
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, params=params or {}, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                time.sleep(1.2 * (attempt + 1))
                last = RuntimeError("Upbit rate limit")
                continue
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            time.sleep(0.8 * (attempt + 1))
    raise last or RuntimeError(f"failed: {path}")


def downsample(values, limit=18):
    vals = [float(v) for v in values if v is not None]
    if len(vals) <= limit:
        return vals
    if limit <= 1:
        return [vals[-1]]
    out = []
    n = len(vals)
    for i in range(limit):
        idx = round(i * (n - 1) / (limit - 1))
        out.append(vals[idx])
    return out


def candle_prices(path: str, market: str, count: int):
    data = request_json(path, {"market": market, "count": count})
    data = list(reversed(data))
    return [float(x["trade_price"]) for x in data if x.get("trade_price") is not None]


def latest_existing():
    if not OUT.exists():
        return {}
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_coin(market, symbol, name, ticker, old_coin=None):
    series = {}
    errors = []
    try:
        hourly = candle_prices("/candles/minutes/60", market, 168)
        series["1D"] = downsample(hourly[-24:])
        series["1W"] = downsample(hourly[-168:])
    except Exception as exc:
        errors.append(f"{symbol} hourly: {exc}")
    try:
        daily = candle_prices("/candles/days", market, 90)
        series["1M"] = downsample(daily[-30:])
        series["3M"] = downsample(daily[-90:])
    except Exception as exc:
        errors.append(f"{symbol} daily: {exc}")
    try:
        weekly = candle_prices("/candles/weeks", market, 52)
        series["1Y"] = downsample(weekly[-52:])
    except Exception as exc:
        errors.append(f"{symbol} weekly: {exc}")

    if old_coin:
        for key in ("1D", "1W", "1M", "3M", "1Y"):
            if not series.get(key):
                prev = (old_coin.get("series") or {}).get(key)
                if prev:
                    series[key] = prev

    price = float(ticker["trade_price"])
    change_price = float(ticker.get("signed_change_price") or 0)
    change_rate = float(ticker.get("signed_change_rate") or 0) * 100
    return {
        "market": market,
        "symbol": symbol,
        "name": name,
        "price_krw": round(price),
        "change_krw": round(change_price),
        "change_pct": round(change_rate, 2),
        "series": series,
    }, errors


def main():
    old = latest_existing()
    old_map = {c.get("symbol"): c for c in old.get("coins", []) if c.get("symbol")}
    errors = []

    markets = request_json("/market/all", {"is_details": "false"})
    supported = {m.get("market") for m in markets}
    selected = [a for a in ASSETS if a[0] in supported]
    if not selected:
        raise RuntimeError("None of the requested KRW markets are currently available on Upbit")

    market_list = ",".join(a[0] for a in selected)
    tickers = request_json("/ticker", {"markets": market_list})
    ticker_map = {t["market"]: t for t in tickers}

    coins = []
    latest_ms = 0
    for market, symbol, name in selected:
        ticker = ticker_map.get(market)
        if not ticker:
            errors.append(f"{symbol}: ticker missing")
            continue
        latest_ms = max(latest_ms, int(ticker.get("timestamp") or 0))
        coin, errs = build_coin(market, symbol, name, ticker, old_map.get(symbol))
        errors.extend(errs)
        coins.append(coin)
        time.sleep(0.15)

    if len(coins) < 3:
        raise RuntimeError("Too few valid crypto quotes returned")

    if latest_ms:
        updated = datetime.fromtimestamp(latest_ms / 1000, tz=timezone.utc).astimezone(KST)
    else:
        updated = datetime.now(KST)

    data = {
        "generated_at": datetime.now(KST).isoformat(),
        "updated_at": updated.isoformat(),
        "source": "Upbit Open API · KRW spot",
        "source_url": "https://docs.upbit.com/kr/reference/ticker",
        "accuracy_note": "KRW spot quotes from Upbit. Change is versus previous closing price. Informational use only.",
        "stale": bool(errors),
        "last_errors": errors,
        "filters": ["ALL", "TOP GAINERS", "TOP LOSERS"],
        "ranges": ["1D", "1W", "1M", "3M", "1Y"],
        "activeFilter": "ALL",
        "activeRange": "1D",
        "coins": coins,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        old = latest_existing()
        if old:
            old["generated_at"] = datetime.now(KST).isoformat()
            old["stale"] = True
            old["last_errors"] = [str(exc)]
            OUT.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            raise
