#!/usr/bin/env python3
import argparse
import hashlib
import json
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import update_real_estate_pulse as updater

OUT = Path("real-estate-pulse-data.json")
HEALTH = Path("real-estate-pulse-health.json")
EXPECTED_REGIONS = [
    "서울", "부산", "대구", "인천", "대전", "울산", "전남광주", "세종",
    "경기", "강원", "충북", "충남", "전북", "경북", "경남", "제주",
]

# Match the 16-region geography in the current official REB release.
updater.REGIONS = EXPECTED_REGIONS


def parse_iso_date(value, key):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise RuntimeError(f"{key} must be an ISO date")


def is_official_https(url, suffix):
    parsed = urlparse(str(url or ""))
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == suffix or host.endswith("." + suffix))


def canonical_payload(data):
    return {
        "asOf": data["asOf"],
        "published": data["published"],
        "regions": data["regions"],
    }


def payload_hash(data):
    raw = json.dumps(
        canonical_payload(data), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def comparable(data):
    return {
        "asOf": data.get("asOf"),
        "published": data.get("published"),
        "baseRate": data.get("baseRate"),
        "regions": data.get("regions"),
    }


def validate_dataset(data, require_verification=True):
    as_of = parse_iso_date(data.get("asOf"), "asOf")
    published = parse_iso_date(data.get("published"), "published")
    if published < as_of:
        raise RuntimeError("published cannot be earlier than asOf")
    if published > datetime.now(ZoneInfo("Asia/Seoul")).date():
        raise RuntimeError("published cannot be in the future")

    regions = data.get("regions")
    if not isinstance(regions, list):
        raise RuntimeError("regions must be an array")
    names = [r.get("name") for r in regions]
    if names != EXPECTED_REGIONS:
        raise RuntimeError(f"expected 16 current regions, got: {names}")

    metric_count = 0
    for region in regions:
        for metric in ("sale", "lease"):
            value = region.get(metric)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise RuntimeError(f"{region.get('name')} {metric} is missing/non-numeric")
            if not -5 <= float(value) <= 5:
                raise RuntimeError(f"{region.get('name')} {metric} is outside safety range")
            metric_count += 1
        for metric in ("salePrev", "leasePrev"):
            value = region.get(metric)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise RuntimeError(f"{region.get('name')} {metric} is invalid")

    if metric_count != 32:
        raise RuntimeError("dataset must contain exactly 32 current regional metrics")

    release_url = data.get("releaseUrl") or data.get("sourceUrl")
    source_url = data.get("sourceUrl") or release_url
    if not is_official_https(release_url, "reb.or.kr"):
        raise RuntimeError("releaseUrl must be official reb.or.kr HTTPS")
    if not is_official_https(source_url, "reb.or.kr"):
        raise RuntimeError("sourceUrl must be official reb.or.kr HTTPS")

    source_method = data.get("sourceMethod")
    if source_method not in {"R-ONE Excel", "REB official PDF appendix"}:
        raise RuntimeError(f"unexpected sourceMethod: {source_method}")

    rate = data.get("baseRate") or {}
    for key in ("value", "previous"):
        value = rate.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeError(f"baseRate.{key} must be numeric")
    parse_iso_date(rate.get("changedAt"), "baseRate.changedAt")
    if not is_official_https(rate.get("source"), "bok.or.kr"):
        raise RuntimeError("baseRate.source must be official bok.or.kr HTTPS")

    if require_verification:
        verification = data.get("verification") or {}
        if verification.get("status") != "verified":
            raise RuntimeError("verification.status must be verified")
        if verification.get("regionCount") != 16 or verification.get("metricCount") != 32:
            raise RuntimeError("verification counts must be 16 regions / 32 metrics")
        if verification.get("method") != "official":
            raise RuntimeError("verification.method must be official")
        if not is_official_https(verification.get("primarySource"), "reb.or.kr"):
            raise RuntimeError("verification.primarySource must be official REB")
        if verification.get("dataSha256") != payload_hash(data):
            raise RuntimeError("verification.dataSha256 mismatch")
        checked = datetime.fromisoformat(str(verification.get("checkedAt")))
        if checked.tzinfo is None:
            raise RuntimeError("verification.checkedAt must include timezone")

    return True


def add_verification(data):
    primary = data.get("releaseUrl") or data.get("sourceUrl")
    data["verification"] = {
        "status": "verified",
        "checkedAt": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "regionCount": 16,
        "metricCount": 32,
        "method": "official",
        "primarySource": primary,
        "dataSha256": payload_hash(data),
    }
    return data


def refresh():
    original_text = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    original = json.loads(original_text) if original_text else {}
    checked = datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    try:
        data = updater.collect()
        validate_dataset(data, require_verification=False)
        if original.get("asOf") and data["asOf"] < original["asOf"]:
            raise RuntimeError("refusing to replace data with an older official release")
        add_verification(data)
        validate_dataset(data, require_verification=True)
        # All collection and validation finish before touching the last good file.
        temporary = OUT.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(OUT)
        health = {"checked_at": checked, "status": "ok", "asOf": data["asOf"],
                  "published": data["published"], "sourceUrl": data["releaseUrl"]}
        print(f"Prepared verified 16-region dataset for {data['asOf']}.")
    except Exception as exc:
        health = {"checked_at": checked, "status": "stale" if original else "error",
                  "asOf": original.get("asOf"), "error": str(exc)[:500]}
        print(f"Official REB refresh failed; previous dataset preserved: {exc}")
        HEALTH.write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return False
    HEALTH.write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    if args.validate_only:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        validate_dataset(data, require_verification=True)
        print("Verified: 16 regions / 32 current values / official provenance / integrity hash.")
        return

    if not refresh():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
