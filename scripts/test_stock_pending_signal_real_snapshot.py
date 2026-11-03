"""Read-only frozen-main reproducibility control for pending prior-public forecasts.

Uses git-show for a separately pinned main commit; never rewrites source evidence.
No exchange data, outcome peeking, replay or operational release.
"""
import json
import subprocess
from stock_forecast_presentation import prior_public_forecasts

PINNED = "910f8dfb0503c59cc989c67f31cdc7da56ee7762"
AS_OF = "2026-11-02T22:30:31+00:00"


def read(path):
    return subprocess.check_output(["git", "show", f"{PINNED}:{path}"], text=True)


def lines(path):
    return [json.loads(x) for x in read(path).splitlines() if x.strip()]


def main():
    originals = lines("stock-forecast-ledger.jsonl")
    proofs = lines("stock-forecast-deliveries.jsonl")
    report = json.loads(read("stock-direction-forecast.json"))
    before = json.dumps(report, sort_keys=True)
    now_records = report["records"]
    kr_nocall = [r for r in now_records if r.get("market") == "KR"
                 and r.get("mode") == "daily" and r.get("status") == "no_call"]
    assert len(kr_nocall) == 6, f"Frozen counterexample changed: {len(kr_nocall)}"
    retained = prior_public_forecasts(originals, proofs, now_records, AS_OF)
    assert len(retained) == 6, f"Unseen carryover or missing public proof: {len(retained)}"
    assert all(r["market"] == "KR" and r["mode"] == "daily"
               and r["display_origin"] == "earlier_public_frozen_record"
               and not r["recommendation"] and not r["user_receipt_verified"] for r in retained)
    selected = {r["symbol"]: r["direction"] for r in retained}
    assert selected["^KS11"] == "up" and selected["^KQ11"] == "down"
    assert len(set(r["id"] for r in retained)) == 6
    assert json.dumps(report, sort_keys=True) == before, "Current no-call evidence modified"
    print(json.dumps({"status": "research_only_disappearance_reproduced",
                      "frozen_main": PINNED, "valid_prior_public": len(retained),
                      "latest_snapshot_no_call": len(kr_nocall),
                      "prior_symbols_and_directions": selected,
                      "operating_display_changed": False,
                      "actual_user_receipt": "unverified",
                      "timing_utility": "not_proven"}, sort_keys=True))


if __name__ == "__main__":
    main()
