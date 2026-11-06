"""Review the pinned four-company source probe; restore only the reviewed 011280 triple.

The original observation dates and raw quarantine are preserved. This command
never substitutes separate accounts, a summary table, or a solved balance value.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import html
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

try:
    from scripts.probe_stock_financial_reconciliation import TARGETS, extract_xbrl
    from scripts.stock_financial_precision import PRECISION_VERSION, precision_facts_check, verified_balance_precision
    from scripts.build_stock_financial_coverage import (ACCOUNT_POLICY, ACCOUNT_QUARANTINE_OUTPUT,
        OUTPUT, BALANCE_FIELDS, guard_account_records, validate_account_record, write_json)
except ModuleNotFoundError:
    from probe_stock_financial_reconciliation import TARGETS, extract_xbrl
    from stock_financial_precision import PRECISION_VERSION, precision_facts_check, verified_balance_precision
    from build_stock_financial_coverage import (ACCOUNT_POLICY, ACCOUNT_QUARANTINE_OUTPUT,
        OUTPUT, BALANCE_FIELDS, guard_account_records, validate_account_record, write_json)

REVIEWED_KEY = "KR:011280"
REVIEWED_RECEIPT = "20260814003299"
RUN_ID = 42208426915
ARTIFACT_ID = 13498570932
ARTIFACT_SHA256 = "94f2ee1d86f5078a5dc391b9fdcd24707702b9e7e5ad27b5cfb29ebd71fba991"


def digest(body):
    return hashlib.sha256(body).hexdigest()


def report_table_evidence(raw, period, amounts):
    """Parse exact well-formed table fragments, without repairing the source XML.

    These DART documents contain unrelated prose with literal '&' or '<신설>',
    so the complete document is not well-formed XML. Only unchanged, separately
    well-formed financial tables are parsed, and their raw hashes are retained.
    """
    source = raw.decode("utf-8")
    matches = []
    labels = {"자산총계": "assets", "부채총계": "liabilities", "자본총계": "equity"}
    for match in re.finditer(r"<TABLE\b[^>]*>.*?</TABLE>", source, re.S | re.I):
        fragment = match.group()
        if not all(label in re.sub(r"\s+", "", fragment) for label in labels):
            continue
        try:
            table = ET.fromstring(fragment)
        except ET.ParseError:
            continue
        preceding = source[max(0, match.start()-4000):match.start()]
        context = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", preceding)).split())
        if ("2-1. 연결 재무상태표" not in context or period.replace("-", ".") + " 현재" not in context
                or not re.search(r"단위\s*[:：]\s*천원", context[-500:])):
            continue
        rows, values = {}, {}
        for tr in table.iter("TR"):
            cells = [" ".join(" ".join(cell.itertext()).split()) for cell in list(tr)
                     if cell.tag in {"TD", "TH", "TE", "TU"}]
            if len(cells) < 2:
                continue
            key = labels.get(re.sub(r"\s+", "", cells[0]))
            if key:
                values[key] = Decimal(cells[1].replace(",", "")) * 1000
                rows[key] = {"label": cells[0], "current_period_displayed": cells[1], "source_unit": "천원"}
        if set(values) == set(amounts) and all(values[key] == Decimal(amounts[key]) for key in values):
            matches.append({"source_character_range": [match.start(), match.end()],
                            "table_sha256": digest(fragment.encode("utf-8")),
                            "preceding_context": context[-700:], "rows": rows,
                            "strict_table_fragment_parsed": True, "source_prose_not_repaired": True})
    if len(matches) != 1:
        raise ValueError("reviewed_report_table_not_unambiguous")
    return matches[0]


def build_source_review(artifact_path):
    artifact = Path(artifact_path).read_bytes()
    if digest(artifact) != ARTIFACT_SHA256:
        raise ValueError("unreviewed_source_artifact")
    reviewed_at = datetime.now(timezone.utc).isoformat()
    result = {"version": "official-financial-precision-review-v1", "reviewed_at": reviewed_at,
              "source_run_url": f"https://github.com/Ohoredingdong/Notion/actions/runs/{RUN_ID}",
              "source_artifact_id": ARTIFACT_ID, "source_artifact_sha256": ARTIFACT_SHA256,
              "records": {}, "production_fields_not_solved_or_estimated": True}
    with zipfile.ZipFile(io.BytesIO(artifact)) as archive:
        manifest = json.loads(archive.read("financial-source-precision-evidence.json"))
        if manifest["source_ref"] != "7775ab45312a2714a4fbe4a9a9b6c711a191ea4b":
            raise ValueError("probe_commit_mismatch")
        result["source_probe_completed_at"] = manifest["completed_at"]
        for target in TARGETS:
            entry = next(row for row in manifest["targets"] if row["symbol"] == target["symbol"])
            if any(entry[key] != target[key] for key in target):
                raise ValueError("source_target_mismatch")
            receipts = entry["endpoints"]
            bodies = {}
            for endpoint, receipt in receipts.items():
                suffix = endpoint.removesuffix(".xml") + ".zip" if endpoint.endswith(".xml") else endpoint
                body = archive.read(target["symbol"] + "/" + suffix)
                if receipt["status"] != "received" or digest(body) != receipt["sha256"]:
                    raise ValueError("source_response_hash_mismatch")
                bodies[endpoint] = body
            with zipfile.ZipFile(io.BytesIO(bodies["fnlttXbrl.xml"])) as xbrl_archive:
                names = [name for name in xbrl_archive.namelist() if name.endswith(".xbrl")]
                if len(names) != 1:
                    raise ValueError("ambiguous_xbrl_instance")
                instance = xbrl_archive.read(names[0])
                parsed = extract_xbrl(ET.fromstring(instance), names[0])
            candidates = [row for row in parsed["balance_candidates"]
                          if (row.get("context") or {}).get("period") == {"instant": "2026-06-30"}
                          and (row.get("context") or {}).get("dimensions") == [
                              {"kind": "explicitMember", "dimension": "ifrs-full:ConsolidatedAndSeparateFinancialStatementsAxis",
                               "value": "ifrs-full:ConsolidatedMember"}]]
            if len(candidates) != 1:
                raise ValueError("ambiguous_consolidated_context")
            candidate = candidates[0]
            amounts = {key: fact["value"] for key, fact in candidate["facts"].items()}
            api_evidence = []
            for endpoint in ("fnlttMultiAcnt.json", "fnlttSinglAcntAll.json"):
                account = receipts[endpoint]["accounts"]
                rows = account["selected_balance_rows"]
                if account["status"] != "000" or not account["has_all_three_unambiguous"]:
                    raise ValueError("unavailable_or_ambiguous_account_api")
                if not all(row["expected_issuer"] and row["expected_filing"] and row["currency"] == "KRW"
                           and Decimal(row["thstrm_amount"].replace(",", "")) == Decimal(amounts[row["field"]]) for row in rows):
                    raise ValueError("xbrl_account_api_disagreement")
                api_evidence.append({"endpoint": endpoint, "sha256": receipts[endpoint]["sha256"],
                                     "received_at": receipts[endpoint]["received_at"], "rows": rows})
            evidence = {"version": PRECISION_VERSION, "verified_at": reviewed_at,
                "issuer": {"symbol": target["symbol"], "corp_code": target["corp_code"]},
                "source": {"endpoint": "https://opendart.fss.or.kr/api/fnlttXbrl.xml", "rcept_no": target["rcept_no"],
                           "bsns_year": "2026", "reprt_code": "11012", "package_sha256": receipts["fnlttXbrl.xml"]["sha256"],
                           "instance_member": names[0], "instance_sha256": digest(instance),
                           "received_at": receipts["fnlttXbrl.xml"]["received_at"],
                           "run_url": result["source_run_url"], "artifact_id": ARTIFACT_ID,
                           "artifact_sha256": ARTIFACT_SHA256},
                "context_ref": candidate["context_ref"], "context": candidate["context"],
                "unit_ref": candidate["unit_ref"], "unit": candidate["unit"],
                "facts": {key: {field: fact.get(field) for field in
                                 ("concept", "context_ref", "unit_ref", "decimals", "precision", "nil", "value")}
                          for key, fact in candidate["facts"].items()},
                "api_crosschecks": api_evidence}
            if target["symbol"] == "011280":
                with zipfile.ZipFile(io.BytesIO(bodies["document.xml"])) as document_archive:
                    member = target["rcept_no"] + ".xml"
                    raw_document = document_archive.read(member)
                evidence["report_crosscheck"] = {"package_sha256": receipts["document.xml"]["sha256"],
                    "member": member, "member_sha256": digest(raw_document),
                    **report_table_evidence(raw_document, "2026-06-30", amounts)}
            result["records"]["KR:" + target["symbol"]] = {
                "source_precision": evidence, "source_interval_result": {key: value for key, value in candidate.items()
                    if key in {"status", "reported_difference", "difference_interval", "declared_decimals"}},
                "resolution": "restore_unchanged_reported_values_with_precision" if target["symbol"] == "011280" else "keep_withheld",
                "note": ("Official consolidated table and both account APIs match the source-declared XBRL precision."
                         if target["symbol"] == "011280" else "The consolidated XBRL balance difference is outside its declared precision; do not substitute a separate statement or summary table.")}
    return result


def apply_review(root, review):
    root = Path(root)
    data = json.loads((root / OUTPUT).read_text(encoding="utf-8"))
    archive_bytes = (root / ACCOUNT_QUARANTINE_OUTPUT).read_bytes()
    quarantine = json.loads(archive_bytes)
    current = data["records"][REVIEWED_KEY]
    if current.get("rcept_no") != REVIEWED_RECEIPT:
        raise ValueError("reviewed_record_changed_filing")
    proof = review["records"][REVIEWED_KEY]["source_precision"]
    if verified_balance_precision(current) is not None:
        return {"status": "already_reconciled", "restored_fields": 0}
    validation = (current.get("account_validation") or {}).get("balance_sheet") or {}
    if validation.get("status") != "withheld" or any(current["metrics"].get(key) is not None for key in BALANCE_FIELDS):
        raise ValueError("expected_withheld_triple_missing")
    source_hash = current["account_validation"]["quarantine_sha256"]
    entries = [row for row in quarantine["records"] if row["previous_key"] == REVIEWED_KEY and row["sha256"] == source_hash]
    if len(entries) != 1:
        raise ValueError("original_quarantined_record_not_unambiguous")
    original = entries[0]["record"]
    original_hash = digest(json.dumps([REVIEWED_KEY, original], ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    if original_hash != source_hash:
        raise ValueError("original_quarantine_record_hash_mismatch")
    restored = copy.deepcopy(current)
    for field in BALANCE_FIELDS:
        restored["metrics"][field] = original["metrics"][field]
    check = precision_facts_check(restored, proof)
    if check is None:
        raise ValueError("reviewed_precision_not_bound_to_original_values")
    old_note = current["account_validation"].get("note")
    note = "공시 원문 XBRL의 천원 단위 정확도를 확인했습니다. 자산·부채·자본 합계의 1,000원 차이는 명시된 반올림 범위 안이며, 공시에 적힌 세 금액을 그대로 표시합니다."
    restored["status"] = "stale" if current.get("status") == "stale" else original["status"]
    restored["missing_metrics"] = [key for key, value in restored["metrics"].items() if value is None]
    restored["limitations"] = [value for value in restored.get("limitations", []) if value != old_note] + [note]
    restored["account_validation"] = {"policy": ACCOUNT_POLICY, "audited_at": proof["verified_at"], "note": note,
        "balance_sheet": {"status": "verified_with_declared_precision", "equation": "assets = liabilities + equity",
                          **check, "source_precision": proof, "reported_values_unchanged": True},
        "original_withheld_at": current["account_validation"].get("audited_at"),
        "quarantine_file": str(ACCOUNT_QUARANTINE_OUTPUT), "quarantine_sha256": source_hash}
    validate_account_record(restored)
    updated = {**data["records"], REVIEWED_KEY: restored}
    checked, account_audit = guard_account_records(updated, root, proof["verified_at"])
    if any(checked[key] != row for key, row in data["records"].items() if key != REVIEWED_KEY):
        raise ValueError("unreviewed_record_would_change")
    if (root / ACCOUNT_QUARANTINE_OUTPUT).read_bytes() != archive_bytes:
        raise ValueError("quarantine_must_remain_unchanged")
    data["records"] = checked
    data["account_integrity"] = {**account_audit, "precision_reviewed_at": proof["verified_at"],
                                 "source_collection_timestamps_unchanged": True}
    write_json(root / OUTPUT, data)
    return {"status": "reconciled", "restored_record": REVIEWED_KEY, "restored_fields": 3,
            "withheld_records": account_audit["withheld_records"], "withheld_fields": account_audit["withheld_fields"],
            "source_checked_at_preserved": current["checked_at"] == restored["checked_at"],
            "generated_at_preserved": data["generated_at"], "quarantine_preserved": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    parser.add_argument("--apply-root", type=Path)
    args = parser.parse_args()
    review = build_source_review(args.artifact)
    write_json(args.evidence_output, review)
    if args.apply_root:
        print(json.dumps(apply_review(args.apply_root, review), ensure_ascii=False))
    else:
        print(json.dumps({"status": "source_review_only", "records": len(review["records"])}))


if __name__ == "__main__":
    main()
