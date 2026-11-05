"""Validate a coherent catalogue/financial snapshot without inventing coverage."""
import json
from pathlib import Path

from scripts.build_stock_financial_coverage import (
    CATALOG_POLICY, IDENTITY_POLICY, FINANCIAL_STATUSES, KR_SYMBOL,
    verified_financial_record,
)


def validate(catalog, data):
    assert catalog.get("identifier_policy") == CATALOG_POLICY, "Unrepaired catalogue identifier policy"
    assert catalog.get("status") == "complete", "Official catalogue source refresh is incomplete"
    items = catalog["items"]
    by_key = {x["country"]+":"+x["symbol"]: x for x in items}
    assert len(by_key) == len(items), "Conflicting catalogue identifiers"
    counts = {country: sum(x["country"] == country for x in items) for country in ("KR", "US")}
    assert catalog["counts"] == {"total":len(items), **counts}, "Incorrect source catalogue counts"
    assert all(KR_SYMBOL.fullmatch(x["symbol"]) and x.get("source_symbol") == x["symbol"]
               for x in items if x["country"] == "KR"), "Korean official symbol was not preserved"
    assert data.get("identity_policy") == IDENTITY_POLICY, "Unverified issuer identity policy"
    assert data.get("catalog_generated_at") == catalog.get("generated_at"), "Unaligned source snapshots"
    assert data["universe"] == catalog["counts"], "Financial scope differs from source catalogue"
    assert data["processed"] == len(data["records"]), "Incorrect processed count"
    available = {"KR":0, "US":0}
    for key, row in data["records"].items():
        assert key in by_key and key == row["country"]+":"+row["symbol"], "Unknown financial identity"
        if row.get("status") in FINANCIAL_STATUSES or row.get("metrics") is not None:
            assert verified_financial_record(row, key, by_key[key]), "Unverified financial record: "+key
            assert row.get("full_financial_statements") is False, "Selected accounts labelled as full statements"
            assert row.get("source") in ("DART periodic reports", "SEC EDGAR XBRL"), "Unsupported financial source"
            available[row["country"]] += 1
    assert data["financial_available"] == available, "Historical coverage counter is inaccurate"
    failed = False
    for market, counter in data["run"].items():
        for field in ("attempted","available","blocked","provider_errors","identity_errors","no_report"):
            assert isinstance(counter[field], int) and counter[field] >= 0, "Invalid run counter"
        assert counter["attempted"] == counter["available"]+counter["blocked"], "Run accounting differs"
        assert counter["provider_errors"] <= counter["attempted"], "Invalid provider failure count"
        failed |= bool(counter["provider_errors"] or counter["identity_errors"])
    assert data.get("current_run_failed") == failed, "Current-run failure hidden by historical coverage"
    assert data.get("refresh_status") in ("success","partial","blocked","not_requested")
    return available


def main():
    catalog = json.loads(Path("stock-universe-catalog.json").read_text(encoding="utf-8"))
    data = json.loads(Path("stock-financial-coverage.json").read_text(encoding="utf-8"))
    available = validate(catalog, data)
    print("OFFICIAL_IDENTITY_SNAPSHOT_VALID", available, "of", catalog["counts"],
          "current_refresh", data["refresh_status"], "quarantined", data.get("quarantined_records",0))


if __name__ == "__main__":
    main()
