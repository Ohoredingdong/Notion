"""Forward-looking, event-conditioned market watch. Not a buy signal.

Economic calendar events and manually verified official policy dates are linked
to conditional sector hypotheses. No claim is made that future asset returns or
event probabilities are forecast by this rule-based report.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CALENDAR = ROOT / "market-events-data.json"
POLICY = ROOT / "stock-event-calendar-seed.json"
OUTPUT = ROOT / "stock-event-outlook.json"
VERSION = "stock-event-outlook-v1"
UTC = timezone.utc
KST = ZoneInfo("Asia/Seoul")
MAX_CALENDAR_AGE_HOURS = 12

CONDITIONS = {
    "rate": {
        "focus": "중앙은행 정책금리와 향후 금리 경로",
        "stronger": "예상보다 매파적이면 시장금리가 상승해 고평가 성장주·차입 부담 기업에 불리할 수 있습니다.",
        "weaker": "예상보다 완화적이면 장기금리 부담이 줄어 성장주·금리 민감 업종에 우호적일 수 있습니다. 경기 악화에 따른 인하는 별도 위험입니다.",
        "watch": ["국채금리", "환율", "성장주 대비 가치주"],
    },
    "inflation": {
        "focus": "물가의 시장 예상 대비 차이",
        "stronger": "예상보다 높은 물가가 금리 인하 기대를 낮추면 성장주에 부담이 될 수 있습니다.",
        "weaker": "예상보다 낮은 물가가 장기금리를 낮추면 성장주에 우호적일 수 있습니다.",
        "watch": ["미국 10년물 국채금리", "달러", "나스닥"],
    },
    "jobs": {
        "focus": "고용의 시장 예상 대비 차이",
        "stronger": "고용 호조는 경기민감 업종에 우호적일 수 있지만 금리 상승 우려로 주가 반응이 혼재할 수 있습니다.",
        "weaker": "고용 부진은 금리 인하 기대를 키우지만 경기침체 우려가 더 크면 주가가 하락할 수 있습니다.",
        "watch": ["미국 10년물 국채금리", "경기민감주", "나스닥"],
    },
    "growth": {
        "focus": "경기 지표의 시장 예상 대비 차이",
        "stronger": "성장 지표 호조는 경기민감 업종에 긍정적일 수 있으나 금리 상승 부담도 확인해야 합니다.",
        "weaker": "성장 지표 악화는 경기민감 업종에 부정적일 수 있습니다. 금리 인하 기대가 반응을 상쇄할 수도 있습니다.",
        "watch": ["주가지수", "국채금리", "경기민감 업종"],
    },
    "policy": {
        "focus": "정책 발표의 실제 내용과 시장 기대의 차이",
        "stronger": "정책 지원이 예상보다 강하면 직접 수혜 업종에 우호적일 수 있지만 선반영 여부를 확인해야 합니다.",
        "weaker": "정책 지원이 예상보다 약하거나 규제가 강하면 관련 업종에 부정적일 수 있습니다.",
        "watch": ["관련 법안·공식 발표", "업종별 상대수익률", "거래량"],
    },
}

ALLOWED_OFFICIAL_HOSTS = {"www.bok.or.kr", "bok.or.kr", "www.federalreserve.gov", "federalreserve.gov"}


def aware(value: str) -> datetime:
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp_timezone_required")
    return result.astimezone(UTC)


def valid_url(value: str, official: bool = False) -> bool:
    try:
        result = urlparse(value)
        return result.scheme == "https" and bool(result.hostname) and (
            not official or result.hostname in ALLOWED_OFFICIAL_HOSTS
        )
    except (TypeError, ValueError):
        return False


def hypotheses(category: str) -> dict:
    row = CONDITIONS.get(category, CONDITIONS["policy"])
    return {**row, "probability": None, "interpretation": "조건부 가설 · 투자 신호 아님"}


def make_calendar_events(data: dict, now: datetime) -> tuple[list, bool]:
    try:
        stamped = aware(data["generated_at"])
        fresh = timedelta(minutes=-5) <= now - stamped <= timedelta(hours=MAX_CALENDAR_AGE_HOURS)
    except (KeyError, ValueError, TypeError):
        fresh = False
    if not fresh or data.get("stale") is True:
        return [], False
    url = data.get("source_url", "")
    if not valid_url(url):
        return [], False
    out = []
    seen = set()
    for row in data.get("events", []):
        if not isinstance(row, dict):
            continue
        if row.get("country") not in ("US", "KR") or row.get("actual") is not None:
            continue
        cat = row.get("category")
        if cat not in CONDITIONS or cat == "policy":
            continue
        impact = row.get("impact_level")
        if type(impact) is not int or impact < 2:
            continue
        try:
            when = aware(row["datetime_kst"])
        except (KeyError, ValueError, TypeError):
            continue
        if not now < when <= now + timedelta(days=21):
            continue
        title = str(row.get("title_ko") or row.get("title") or "").strip()
        if not title:
            continue
        identifier = str(row.get("id") or f"{row['country']}|{title}|{when.isoformat()}")
        if identifier in seen:
            continue
        seen.add(identifier)
        out.append({
            "id": "calendar-" + identifier, "kind": "economic_calendar",
            "title": title, "region": row["country"], "category": cat,
            "event_at": when.isoformat(), "time_precision": "minute",
            "impact_level": impact, "source_url": url,
            "source_type": "third_party_calendar", "source_as_of": stamped.isoformat(),
            "hypotheses": hypotheses(cat),
        })
    return out, True


def make_official_events(data: dict, now: datetime) -> list:
    out = []
    seen = set()
    for row in data.get("events", []):
        if not isinstance(row, dict):
            continue
        try:
            title = str(row["title"]).strip()
            category = str(row["category"])
            region = str(row["region"])
            tzname = str(row["timezone"])
            day = datetime.strptime(row["event_date"], "%Y-%m-%d")
            zone = ZoneInfo(tzname)
            event_start = day.replace(tzinfo=zone).astimezone(UTC)
            event_end = (day + timedelta(days=1)).replace(tzinfo=zone).astimezone(UTC)
            source = str(row["source_url"])
        except (KeyError, TypeError, ValueError):
            continue
        if not title or category not in CONDITIONS or not valid_url(source, official=True):
            continue
        if not now < event_end <= now + timedelta(days=70) or region not in ("US", "KR"):
            continue
        identifier = str(row.get("id") or f"{region}|{title}|{day.date()}")
        if identifier in seen:
            continue
        seen.add(identifier)
        out.append({
            "id": "official-" + identifier, "kind": "official_policy_schedule",
            "title": title, "region": region, "category": category,
            "event_at": event_start.isoformat(), "time_precision": "date_only",
            "event_date": row["event_date"], "event_timezone": tzname,
            "impact_level": 3, "source_url": source,
            "source_type": "official_schedule", "source_as_of": str(data.get("verified_at") or ""),
            "hypotheses": hypotheses(category),
        })
    return out


def build(calendar: dict, policy: dict, now: datetime) -> dict:
    now = now.astimezone(UTC)
    dynamic, fresh = make_calendar_events(calendar, now)
    official = make_official_events(policy, now)
    combined = sorted(dynamic + official, key=lambda e: (e["event_at"], -e["impact_level"], e["id"]))
    return {
        "version": VERSION,
        "generated_at": now.isoformat(),
        "status": "ok" if fresh else "partial_calendar_stale",
        "calendar_fresh": fresh,
        "source_calendar_generated_at": calendar.get("generated_at"),
        "coverage": "미국·한국 경제 일정과 사전 검증된 공식 정책 일정만 포함. 선거·법안·정치 뉴스는 일정 및 출처 검증 후 별도 등록.",
        "probabilities_available": False,
        "returns_backtested": False,
        "research_only": True,
        "automatic_orders": False,
        "events": combined[:30],
        "warnings": ([] if fresh else ["경제 일정이 오래되었거나 검증되지 않아 공식 일정만 표시합니다."])
                    + (["예정일만으로 업종·종목 상승을 보장할 수 없습니다."]),
    }


def main() -> None:
    def read(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    report = build(read(CALENDAR), read(POLICY), datetime.now(UTC))
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"EVENT_OUTLOOK {report['status']} {len(report['events'])} events; research only")


if __name__ == "__main__":
    main()
