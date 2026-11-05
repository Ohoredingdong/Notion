"""Build a searchable KRX + US issuer catalogue from attributed listing sources.

Does not generate quotes or AI predictions, never scrapes indiscriminately, and
will not silently replace valid catalogues with a failed or empty download.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UTC = timezone.utc
VERSION = "radar-universe-catalog-v1"
IDENTIFIER_POLICY = "kr-six-character-alphanumeric-v2"
NASDAQ = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
KIND = "https://kind.krx.co.kr/corpgeneral/corpList.do"
SEC = "https://www.sec.gov/files/company_tickers_exchange.json"
HEADERS = {"User-Agent": "GeoyeonInvestmentRadar/1.0 (+https://github.com/Ohoredingdong/Notion)",
           "Accept": "text/plain,text/html,application/json,*/*"}
BAD_INSTRUMENT = re.compile(
    r"\b(warrants?|rights?|preferred|depositary shares?|units?\s+consisting|notes?\s+due|"
    r"exchange traded funds?|etfs?|trust units?)\b", re.I,
)
_SYMBOL_US = re.compile(r"^[A-Z][A-Z0-9.^-]{0,14}$")
_SYMBOL_KR = re.compile(r"^[0-9A-Z]{6}$")


def korean_symbol(value):
    """Preserve the exchange identifier; letters are significant, not decoration."""
    code = str(value or "").strip().upper()
    # Excel/HTML exports may omit numeric leading zeroes. Never apply this to
    # alphanumeric identifiers: 0001A0 must not become the unrelated 000010.
    if re.fullmatch(r"[0-9]{1,6}", code):
        code = code.zfill(6)
    return code if _SYMBOL_KR.fullmatch(code) else None


def fetch(url, *, timeout=20):
    headers = dict(HEADERS)
    if url == SEC:
        agent = os.getenv("SEC_USER_AGENT", "").strip()
        if not re.search(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", agent):
            raise ValueError("SEC_fallback_requires_real_contact_user_agent")
        headers["User-Agent"] = agent
    with urlopen(Request(url, headers=headers), timeout=timeout) as response:
        data = response.read(10_000_001)
        if len(data) > 10_000_000:
            raise ValueError("listing_source_over_10_mb")
        return data


def listing_text(raw: bytes):
    for enc in ("utf-8-sig", "euc-kr", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("unrecognized_listing_encoding")


def nasdaq_rows(raw, other=False):
    rows = listing_text(raw).splitlines()
    if not rows or "|" not in rows[0]:
        raise ValueError("Nasdaq symbol-directory header missing")
    headers = [s.strip().lstrip("\ufeff") for s in rows[0].split("|")]
    items = []
    for line in rows[1:]:
        if not line.strip() or line.startswith("File Creation Time"):
            continue
        fields = line.split("|")
        if len(fields) != len(headers):
            continue
        rec = dict(zip(headers, fields))
        symbol = (rec.get("ACT Symbol") if other else rec.get("Symbol") or "").strip().upper()
        if other and not symbol:
            symbol = rec.get("NASDAQ Symbol", "").strip().upper()
        name = rec.get("Security Name", "").strip()
        venue = {"N": "NYSE", "A": "NYSE AMERICAN", "P": "NYSE ARCA",
                 "Z": "CBOE", "V": "IEX"}.get(rec.get("Exchange"), "OTHER") if other else "NASDAQ"
        if not symbol or not _SYMBOL_US.fullmatch(symbol) or not name:
            continue
        if rec.get("ETF", "N") == "Y" or rec.get("Test Issue", "N") != "N":
            continue
        if BAD_INSTRUMENT.search(name):
            continue
        if venue == "OTHER":
            continue
        items.append({"symbol": symbol, "name": name[:180], "country": "US",
                      "exchange": venue, "source": "Nasdaq Trader",
                      "source_url": OTHER if other else NASDAQ})
    return items


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.rows, self.cells = [], [], []
        self.in_table = self.in_cell = False
        self.level = 0
        self.value = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.level += 1
            if self.level == 1:
                self.rows = []
                self.in_table = True
        if not self.in_table or self.level != 1:
            return
        if tag == "tr":
            self.cells = []
        if tag in ("td", "th"):
            self.in_cell = True
            self.value = []

    def handle_data(self, data):
        if self.in_cell:
            self.value.append(data)

    def handle_endtag(self, tag):
        if self.in_table and self.level == 1:
            if tag in ("td", "th"):
                self.cells.append(re.sub(r"\s+", " ", "".join(self.value)).strip())
                self.in_cell = False
            if tag == "tr" and self.cells:
                self.rows.append(self.cells)
        if tag == "table":
            if self.level == 1:
                self.tables.append(self.rows)
                self.in_table = False
            self.level -= 1


def kind_rows(raw, exchange):
    page = listing_text(raw)
    parser = _TableParser()
    parser.feed(page)
    result = []
    for rows in parser.tables:
        if not rows:
            continue
        head = rows[0]
        code_idx = next((i for i, col in enumerate(head) if "종목코드" in col), None)
        name_idx = next((i for i, col in enumerate(head) if "회사명" in col or "법인명" in col), None)
        if code_idx is None or name_idx is None:
            continue
        for row in rows[1:]:
            if max(code_idx, name_idx) >= len(row):
                continue
            code = korean_symbol(row[code_idx])
            name = row[name_idx].strip()
            if code and name:
                result.append({"symbol": code, "name": name[:180], "country": "KR",
                               "exchange": exchange, "source": "KRX KIND",
                               "source_url": KIND, "source_symbol": code})
    return result


def sec_rows(raw):
    obj = json.loads(raw)
    fields = obj.get("fields") or []
    data = obj.get("data") or []
    keys = [str(s).lower() for s in fields]
    try:
        name_i, symbol_i, exchange_i = (keys.index(key) for key in ("name", "ticker", "exchange"))
    except ValueError:
        raise ValueError("SEC ticker file required fields missing")
    items = []
    for row in data:
        if max(name_i, symbol_i, exchange_i) >= len(row):
            continue
        name, ticker, exchange = row[name_i], row[symbol_i], row[exchange_i]
        if not isinstance(ticker, str) or not _SYMBOL_US.fullmatch(ticker.upper()):
            continue
        if not isinstance(name, str) or not isinstance(exchange, str):
            continue
        if exchange.strip().lower() not in ("nasdaq", "nyse", "nyse american", "cboe", "iex"):
            continue
        items.append({"symbol": ticker.upper(), "name": name[:180], "country": "US",
                      "exchange": exchange.upper(), "source": "SEC EDGAR",
                      "source_url": SEC})
    return items


def deduplicate(records):
    seen = {}
    for row in records:
        key = (row["country"], row["symbol"])
        if key in seen and (seen[key]["name"].casefold(), seen[key]["exchange"]) != (
                row["name"].casefold(), row["exchange"]):
            raise ValueError(f"conflicting_listing_identity: {key[0]}:{key[1]}")
        if key not in seen:
            seen[key] = row
    return sorted(seen.values(), key=lambda x: (x["country"], x["exchange"], x["symbol"]))


def build(fetcher=fetch):
    sources, issues, items = [], [], []
    checked_at = datetime.now(UTC).isoformat()

    for name, url, parser in (
        ("NASDAQ-listed", NASDAQ, lambda x: nasdaq_rows(x)),
        ("US-other-listed", OTHER, lambda x: nasdaq_rows(x, other=True)),
        ("KR-KOSPI", KIND + "?" + urlencode({"method":"download","marketType":"stockMkt","searchType":13}),
         lambda x: kind_rows(x, "KOSPI")),
        ("KR-KOSDAQ", KIND + "?" + urlencode({"method":"download","marketType":"kosdaqMkt","searchType":13}),
         lambda x: kind_rows(x, "KOSDAQ")),
    ):
        try:
            rows = parser(fetcher(url))
            if not rows:
                raise ValueError("empty_or_unrecognized_listing")
            items.extend(rows)
            sources.append({"name": name, "url": url, "rows": len(rows), "status": "ok",
                            "checked_at": checked_at})
        except Exception as exc:
            issues.append(f"{name}: {type(exc).__name__} ({str(exc)[:140]})")
            sources.append({"name": name, "url": url, "rows": 0, "status": "unavailable",
                            "checked_at": checked_at})
    us = sum(x["country"]=="US" for x in items)
    if us < 1000:
        try:
            fallback = sec_rows(fetcher(SEC))
            if len(fallback) < 1000:
                raise ValueError("SEC_listing_response_too_small")
            items.extend(fallback)
            sources.append({"name":"US-SEC-fallback","url":SEC,"status":"ok",
                            "rows":len(fallback),"checked_at":checked_at})
        except Exception as exc:
            issues.append(f"SEC fallback: {type(exc).__name__} ({str(exc)[:140]})")
    normalized = deduplicate(items)
    kr_n = sum(x["country"]=="KR" for x in normalized)
    us_n = sum(x["country"]=="US" for x in normalized)
    if us_n + kr_n < 1000:
        raise RuntimeError("too_few_verified_listings; preserving previous catalog")
    return {"version": VERSION, "identifier_policy": IDENTIFIER_POLICY,
            "generated_at": checked_at,
            "status": "complete" if kr_n >= 1000 and us_n >= 1000 and not issues else "partial",
            "sources": sources, "issues": issues,
            "counts": {"total":len(normalized),"KR":kr_n,"US":us_n},
            "scope_note": "검색용 상장종목 명부. 주가·재무제표·상승 확률 제공 보장 아님. 출처가 누락되면 부분 명부임.",
            "items": normalized}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="stock-universe-catalog.json")
    args = ap.parse_args()
    data = build()
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n",
                   encoding="utf-8")
    tmp.replace(target)
    print("CATALOG_REAL_SOURCES", data["status"], data["counts"])
    if data["issues"]:
        print("SOURCES_UNAVAILABLE", " | ".join(data["issues"]))


if __name__=="__main__":
    main()
