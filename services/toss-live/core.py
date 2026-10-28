"""Toss live quote validation and observation-only alerts. No order APIs."""
from __future__ import annotations
import datetime as dt
import json, math, re, time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

UTC = dt.timezone.utc
SYMBOL = re.compile(r"^[A-Za-z0-9.\-]{1,16}$")
MAX_TOPICS = 100
FRESH_SECONDS = 90

def utcnow():
    return dt.datetime.now(UTC)

def parse_time(x):
    try:
        val = dt.datetime.fromisoformat(str(x).replace("Z", "+00:00"))
        return val.astimezone(UTC) if val.tzinfo else None
    except (TypeError, ValueError):
        return None

def positive(x):
    try:
        if x is None or isinstance(x, bool):
            return None
        v = float(x)
        return v if math.isfinite(v) and v > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None

def normalize_universe(raw):
    """Only validated KR 6-character codes or US tickers. Preserves leading zero."""
    seen, rows = set(), []
    for row in raw.get("companies", []):
        market, code = row.get("market"), str(row.get("symbol", "")).upper()
        if market not in ("KR", "US") or not SYMBOL.fullmatch(code):
            continue
        if market == "KR" and not re.fullmatch(r"[0-9A-Z]{6}", code):
            continue
        if market == "US" and code.isdigit():
            continue
        key = (market, code)
        if key in seen:
            continue
        seen.add(key)
        tech = row.get("technical") or {}
        rows.append({
            "symbol": code, "market": market, "name": row.get("name") or code,
            "currency": "KRW" if market == "KR" else "USD",
            "prior_high20": positive(tech.get("prior_high20")),
            "price_session": row.get("price_session"),
            "technical_date": tech.get("date"),
            "reference_price": positive(row.get("price")),
        })
    return rows

def subscription_rows(rows, max_topics=MAX_TOPICS):
    if not 1 <= max_topics <= MAX_TOPICS:
        raise ValueError("one WebSocket connection supports at most 100 topics")
    primary = rows[:max_topics]
    secondary = rows[max_topics:]
    groups = []
    for market, channel in (("KR", "trade:kr"), ("US", "trade:us")):
        codes = [r["symbol"] for r in primary if r["market"] == market]
        if codes:
            groups.append({"type": channel, "codes": codes})
    assert sum(len(g["codes"]) for g in groups) <= MAX_TOPICS
    return groups, secondary

def quote_from_rest(entry):
    price = positive(entry.get("lastPrice"))
    stamp = parse_time(entry.get("timestamp"))
    symbol = str(entry.get("symbol", "")).upper()
    if not price or not stamp or not SYMBOL.fullmatch(symbol):
        return None
    return {"symbol": symbol, "price": price, "timestamp": stamp, "currency": entry.get("currency"), "source": "REST"}

def quote_from_trade(frame):
    if frame.get("type") != "message":
        return None
    topic = str(frame.get("topic", ""))
    parts = topic.split(":")
    if len(parts) != 3 or parts[0] != "trade" or parts[1] not in ("kr", "us") or not SYMBOL.fullmatch(parts[2]):
        return None
    data = frame.get("data") or {}
    price, stamp = positive(data.get("price")), parse_time(data.get("timestamp"))
    if not price or not stamp:
        return None
    return {"symbol": parts[2].upper(), "market": parts[1].upper(), "price": price, "timestamp": stamp, "currency": data.get("currency"), "source": "WebSocket"}

@dataclass
class WatchEngine:
    rows: list
    threshold_pct: float = 2.0
    cooldown_seconds: int = 1800
    now_fn: object = utcnow
    latest: dict = field(default_factory=dict)
    baseline: dict = field(default_factory=dict)
    last_notification: dict = field(default_factory=dict)
    alerts: deque = field(default_factory=lambda: deque(maxlen=80))
    accepted: int = 0
    dropped: int = 0

    def __post_init__(self):
        self.lookup = {r["symbol"]: r for r in self.rows}
        if not (0.1 <= self.threshold_pct <= 25):
            raise ValueError("unreasonable observation threshold")

    def ingest(self, q, alert=True):
        if not q or q["symbol"] not in self.lookup:
            self.dropped += 1
            return None
        now = self.now_fn()
        age = (now - q["timestamp"]).total_seconds()
        if not -5 <= age <= FRESH_SECONDS:
            self.dropped += 1
            return None
        row = self.lookup[q["symbol"]]
        if q["currency"] != row["currency"]:
            self.dropped += 1
            return None
        prev = self.latest.get(q["symbol"])
        if prev and prev["timestamp"] >= q["timestamp"]:
            self.dropped += 1
            return None
        self.latest[q["symbol"]] = q
        self.accepted += 1
        if q["symbol"] not in self.baseline:
            self.baseline[q["symbol"]] = {"price": q["price"], "timestamp": q["timestamp"]}
            return None
        first = self.baseline[q["symbol"]]["price"]
        change = 100*(q["price"]/first-1)
        level = "up" if change >= self.threshold_pct else "down" if change <= -self.threshold_pct else None
        # A prior-high observation needs a dated reference, and is never a buy signal.
        prior = row.get("prior_high20")
        refdate = row.get("price_session")
        asof = parse_time(refdate+"T00:00:00+00:00") if isinstance(refdate,str) else None
        recent_ref = asof and 0 <= (now-asof).total_seconds() <= 3*86400 and refdate == row.get("technical_date")
        breakout = bool(recent_ref and prior and q["price"] >= prior and first < prior)
        reasons = []
        if level:
            reasons.append("기준 시각 이후 "+("상승" if level=="up" else "하락")+" "+format(change, ".2f")+"%")
        if breakout:
            reasons.append("기준일 "+refdate+"의 과거 20일 고점 관찰선 돌파")
        if not reasons or not alert:
            return None
        # Once per move direction for a window; never spam every trade.
        eventkey = (q["symbol"], level or "breakout")
        last = self.last_notification.get(eventkey)
        if last and (now-last).total_seconds() < self.cooldown_seconds:
            return None
        self.last_notification[eventkey] = now
        event = {
            "type": "research_watch_only", "symbol": q["symbol"], "name": row["name"],
            "market": row["market"], "price": q["price"], "currency": q["currency"],
            "timestamp": q["timestamp"].isoformat(), "observed_at": now.isoformat(),
            "change_since_watch_start_pct": round(change, 3), "reasons": reasons,
            "baseline_at": self.baseline[q["symbol"]]["timestamp"].isoformat(),
            "strict_green_eligible": False, "order_authorized": False,
            "disclaimer": "시세 변동 관찰이며 매수 추천·성공확률·수익 보장이 아닙니다. WebSocket 체결은 일부 유실될 수 있습니다.",
        }
        self.alerts.appendleft(event)
        return event

    def status(self, connected, source_state, watch_count, rest_count):
        now = self.now_fn()
        safe_quotes = []
        for sym, q in self.latest.items():
            age = (now-q["timestamp"]).total_seconds()
            if -5 <= age <= FRESH_SECONDS:
                r = self.lookup[sym]
                baseline = self.baseline.get(sym)
                safe_quotes.append({
                    "symbol": sym, "name": r["name"], "market": r["market"],
                    "price": q["price"], "currency": q["currency"],
                    "timestamp": q["timestamp"].isoformat(),
                    "change_since_watch_start_pct": round(100*(q["price"]/baseline["price"]-1), 3) if baseline else None,
                    "reference_kind": "watch_start_not_session_change",
                })
        return {
            "status": source_state, "connected": bool(connected), "source": "Toss Securities official Open API",
            "generated_at": now.isoformat(), "active_fresh_quotes": len(safe_quotes),
            "ws_topics": watch_count, "rest_fallback_symbols": rest_count,
            "quotes": sorted(safe_quotes, key=lambda x:x["symbol"]),
            "alerts": list(self.alerts)[:30], "accepted": self.accepted, "dropped": self.dropped,
            "live_buy_recommendations": 0, "order_execution_enabled": False,
            "note": "미완료 실사 종목은 실시간 움직임을 감지해도 매수로 승인하지 않습니다.",
        }
