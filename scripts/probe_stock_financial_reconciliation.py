"""Read four withheld official balance sheets and preserve their precision evidence.

This probe does not change production financial records or waive a discrepancy.
It obtains both account APIs, the submitted report XML, and the XBRL package.
Only an explicit fact's decimals/context/unit may explain its rounding interval;
the size of the company or the smallness of a residual never supplies precision.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET
import zipfile

API_ROOT = "https://opendart.fss.or.kr/api/"
TARGETS = (
    {"symbol": "038110", "corp_code": "00139153", "rcept_no": "20260814003056", "name": "에코플라스틱"},
    {"symbol": "264450", "corp_code": "01203376", "rcept_no": "20260814001072", "name": "유비쿼스"},
    {"symbol": "352770", "corp_code": "01201970", "rcept_no": "20260814003475", "name": "셀레스트라"},
    {"symbol": "011280", "corp_code": "00153524", "rcept_no": "20260814003299", "name": "태림포장"},
)
BALANCE_NAMES = {"Assets": "assets", "Liabilities": "liabilities", "Equity": "equity"}
ACCOUNT_LABELS = {"자산총계": "assets", "부채총계": "liabilities", "자본총계": "equity"}
EXTRA_FACTS = {"EquityAndLiabilities", "EquityAttributableToOwnersOfParent", "NoncontrollingInterests",
               "CurrentAssets", "NoncurrentAssets", "CurrentLiabilities", "NoncurrentLiabilities",
               "RetainedEarnings", "ProfitLoss"}
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 48 * 1024 * 1024
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def local_name(name):
    return name.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def normalized_text(element):
    return " ".join(" ".join(element.itertext()).split())


def parse_xml(raw):
    """Read common DART document encodings locally; never resolve a DTD."""
    declaration = re.search(br'<\?xml[^>]+encoding=["\x27]([^"\x27]+)["\x27]', raw[:300], re.I)
    if declaration:
        encoding = declaration.group(1).decode("ascii", errors="strict").lower()
        if encoding in {"euc-kr", "ks_c_5601-1987", "cp949"}:
            return ET.fromstring(raw.decode(encoding))
    return ET.fromstring(raw)


def decimal_value(value):
    try:
        number = Decimal(str(value).replace(",", "").strip())
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def declared_interval(fact):
    """Conservative interior evidence only; do not infer missing decimals.

    Facts with extra lexical digits outside the declared quantum are preserved
    but left unresolved. Boundary equality is not declared consistent here.
    """
    value = decimal_value(fact.get("value"))
    decimals = fact.get("decimals")
    if value is None:
        return None
    if decimals == "INF":
        return value, value
    if not isinstance(decimals, str) or not re.fullmatch(r"[+-]?\d{1,3}", decimals):
        return None
    d = int(decimals)
    if not -18 <= d <= 18:
        return None
    with localcontext() as ctx:
        ctx.prec = 80
        quantum = Decimal(10) ** -d
        if value % quantum != 0:
            return None
        half = quantum / 2
        return value - half, value + half


def balance_candidate(facts):
    values = [decimal_value(facts[k].get("value")) for k in ("assets", "liabilities", "equity")]
    if any(value is None for value in values):
        return {"status": "unresolved", "reason": "non_numeric_balance_fact"}
    with localcontext() as ctx:
        ctx.prec = 80
        difference = values[0] - values[1] - values[2]
        intervals = [declared_interval(facts[k]) for k in ("assets", "liabilities", "equity")]
        result = {"reported_difference": str(difference), "declared_decimals": {k: facts[k].get("decimals") for k in facts}}
        if any(interval is None for interval in intervals):
            return {**result, "status": "unresolved", "reason": "declared_precision_unavailable_or_unsupported"}
        lower = intervals[0][0] - intervals[1][1] - intervals[2][1]
        upper = intervals[0][1] - intervals[1][0] - intervals[2][0]
        if difference == 0:
            status = "exact_reported_equation"
        elif lower < 0 < upper:
            status = "declared_intervals_have_interior_overlap"
        elif lower == 0 or upper == 0:
            status = "rounding_boundary_requires_review"
        else:
            status = "outside_declared_precision"
        return {**result, "status": status, "difference_interval": [str(lower), str(upper)],
                "publication_authorized": False}


def extract_xbrl(root, member):
    contexts, units, facts = {}, {}, []
    for node in root.iter():
        tag = local_name(node.tag)
        if tag == "context" and node.get("id"):
            identity = node.get("id")
            if identity in contexts:
                raise ValueError("duplicate_xbrl_context_id")
            contexts[identity] = {
                "identifiers": [{"scheme": child.get("scheme"), "value": normalized_text(child)}
                                for child in node.iter() if local_name(child.tag) == "identifier"],
                "period": {local_name(child.tag): normalized_text(child) for child in node.iter()
                           if local_name(child.tag) in {"instant", "startDate", "endDate", "forever"}},
                "dimensions": [{"kind": local_name(child.tag), "dimension": child.get("dimension"),
                                "value": normalized_text(child)} for child in node.iter()
                               if local_name(child.tag) in {"explicitMember", "typedMember"}],
            }
        elif tag == "unit" and node.get("id"):
            identity = node.get("id")
            if identity in units:
                raise ValueError("duplicate_xbrl_unit_id")
            units[identity] = {"measures": [normalized_text(child) for child in node.iter()
                                           if local_name(child.tag) == "measure"],
                               "has_divide": any(local_name(child.tag) == "divide" for child in node.iter())}
    for node in root.iter():
        attrs = {local_name(k): value for k, value in node.attrib.items()}
        tag = local_name(node.tag)
        if attrs.get("contextRef") and tag in set(BALANCE_NAMES) | EXTRA_FACTS:
            facts.append({"member": member, "concept": node.tag, "concept_name": tag,
                          "context_ref": attrs.get("contextRef"), "unit_ref": attrs.get("unitRef"),
                          "decimals": attrs.get("decimals"), "precision": attrs.get("precision"),
                          "nil": attrs.get("nil"), "value": normalized_text(node),
                          "context": contexts.get(attrs.get("contextRef")),
                          "unit": units.get(attrs.get("unitRef"))})
    groups = defaultdict(lambda: defaultdict(list))
    for fact in facts:
        if fact["concept_name"] in BALANCE_NAMES:
            groups[(fact["context_ref"], fact["unit_ref"])][BALANCE_NAMES[fact["concept_name"]]].append(fact)
    candidates = []
    for (context, unit), group in groups.items():
        if set(group) != {"assets", "liabilities", "equity"}:
            continue
        candidate = {"member": member, "context_ref": context, "context": contexts.get(context),
                     "unit_ref": unit, "unit": units.get(unit)}
        if any(len(rows) != 1 for rows in group.values()):
            candidates.append({**candidate, "status": "ambiguous_duplicate_facts", "facts": dict(group)})
            continue
        selected = {key: rows[0] for key, rows in group.items()}
        if not candidate["context"] or not candidate["unit"] or candidate["unit"]["has_divide"]:
            candidates.append({**candidate, "status": "missing_context_or_non_currency_unit", "facts": selected})
            continue
        candidates.append({**candidate, **balance_candidate(selected), "facts": selected})
    return {"facts": facts, "balance_candidates": candidates}


def extract_report_tables(root, member):
    document = normalized_text(root)
    candidates = []
    for table in root.iter():
        if local_name(table.tag).upper() != "TABLE":
            continue
        text = normalized_text(table)
        compact = re.sub(r"\s+", "", text)
        if not all(label in compact for label in ("자산총계", "부채총계", "자본총계")):
            continue
        position = document.find(text)
        context = document[max(0, position - 2200):position] if position >= 0 else ""
        candidates.append({"member": member, "preceding_report_context": context,
                           "unit_clauses": re.findall(r"단위\s*[:：]\s*[^)]{1,60}", context + " " + text[:500]),
                           "table_text": text[:30000], "truncated": len(text) > 30000,
                           "consolidation_not_inferred": True})
    return candidates[:50]


def inspect_zip(body, endpoint):
    output = {"endpoint": endpoint, "files": [], "xbrl_facts": [], "balance_candidates": [], "report_balance_tables": []}
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        members = archive.infolist()
        if len(members) > 500 or sum(row.file_size for row in members) > MAX_ARCHIVE_BYTES:
            raise ValueError("archive_size_limit")
        for member in members:
            path = PurePosixPath(member.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in member.filename:
                raise ValueError("unsafe_archive_member")
            if member.is_dir():
                continue
            if member.file_size > MAX_MEMBER_BYTES:
                raise ValueError("archive_member_size_limit")
            raw = archive.read(member)
            info = {"member": member.filename, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            output["files"].append(info)
            if not member.filename.lower().endswith((".xml", ".xbrl", ".xhtml", ".html")):
                continue
            if b"<!ENTITY" in raw.upper():
                info["parse_status"] = "entity_declaration_rejected"
                continue
            try:
                root = parse_xml(raw)
            except (ET.ParseError, UnicodeError, LookupError):
                info["parse_status"] = "xml_not_parsed_raw_preserved"
                continue
            info["parse_status"] = "parsed"
            if local_name(root.tag).lower() == "xbrl":
                xbrl = extract_xbrl(root, member.filename)
                output["xbrl_facts"].extend(xbrl["facts"])
                output["balance_candidates"].extend(xbrl["balance_candidates"])
            elif endpoint == "document.xml":
                output["report_balance_tables"].extend(extract_report_tables(root, member.filename))
    return output


def inspect_accounts(body, target, endpoint):
    rows = body.get("list") or []
    picked = []
    for row in rows:
        label = re.sub(r"\s+", "", row.get("account_nm", ""))
        if row.get("sj_div") != "BS" or (endpoint == "fnlttMultiAcnt.json" and row.get("fs_div") != "CFS"):
            continue
        field = ACCOUNT_LABELS.get(label) or BALANCE_NAMES.get(row.get("account_id", "").split("_")[-1])
        if not field:
            continue
        picked.append({"field": field, **{key: row.get(key) for key in
                       ("rcept_no", "corp_code", "fs_div", "sj_div", "account_id", "account_nm",
                        "thstrm_nm", "thstrm_dt", "thstrm_amount", "currency", "ord")},
                       "expected_issuer": row.get("corp_code") == target["corp_code"],
                       "expected_filing": row.get("rcept_no") == target["rcept_no"]})
    return {"status": body.get("status"), "row_count": len(rows), "selected_balance_rows": picked,
            "has_all_three_unambiguous": all(sum(row["field"] == key for row in picked) == 1
                                             for key in ("assets", "liabilities", "equity"))}


def safe_get(endpoint, params, key):
    import requests
    try:
        with requests.get(API_ROOT + endpoint, params={**params, "crtfc_key": key},
                          timeout=(10, 30), stream=True) as response:
            if response.status_code != 200:
                return None, {"status": "http_error", "http_status": response.status_code}
            chunks, size = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    return None, {"status": "response_size_limit"}
                chunks.append(chunk)
            body = b"".join(chunks)
            if key.encode() in body:
                return None, {"status": "credential_echo_rejected"}
            return body, {"status": "received", "http_status": response.status_code,
                          "received_at": now_iso(), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                          "content_type": response.headers.get("Content-Type")}
    except Exception as exc:
        # Request exception text may include the query string; never emit it.
        return None, {"status": "request_failed", "error_type": type(exc).__name__}


def write_json(path, document):
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_probe(request, out, key):
    if request.get("operation") != "inspect-official-balance-precision" or request.get("bsns_year") != "2026" or request.get("reprt_code") != "11012":
        raise ValueError("unexpected_probe_request")
    if request.get("targets") != [row["symbol"] for row in TARGETS]:
        raise ValueError("unexpected_probe_targets")
    if not key:
        raise ValueError("configured_credential_unavailable")
    out.mkdir(parents=True, exist_ok=True)
    results = {"version": "financial-source-precision-probe-v1", "started_at": now_iso(),
               "source_ref": os.environ.get("GITHUB_SHA"), "request": request, "production_records_modified": False,
               "automatic_release_authorized": False, "targets": []}
    for target in TARGETS:
        target_out = out / target["symbol"]
        target_out.mkdir(exist_ok=True)
        item = {**target, "expected_period_end": "2026-06-30", "endpoints": {}}
        for endpoint in ("fnlttMultiAcnt.json", "fnlttSinglAcntAll.json", "document.xml", "fnlttXbrl.xml"):
            if endpoint.endswith(".json"):
                params = {"corp_code": target["corp_code"], "bsns_year": "2026", "reprt_code": "11012"}
                if endpoint == "fnlttSinglAcntAll.json":
                    params["fs_div"] = "CFS"
            else:
                params = {"rcept_no": target["rcept_no"]}
                if endpoint == "fnlttXbrl.xml":
                    params["reprt_code"] = "11012"
            body, receipt = safe_get(endpoint, params, key)
            receipt["public_source"] = {"endpoint": API_ROOT + endpoint, "parameters_without_credential": params}
            item["endpoints"][endpoint] = receipt
            if body is not None:
                if endpoint.endswith(".json"):
                    try:
                        document = json.loads(body)
                        receipt["accounts"] = inspect_accounts(document, target, endpoint)
                        (target_out / endpoint).write_bytes(body)
                    except (ValueError, TypeError):
                        receipt["status"] = "invalid_json"
                elif zipfile.is_zipfile(io.BytesIO(body)):
                    (target_out / (endpoint.removesuffix(".xml") + ".zip")).write_bytes(body)
                    try:
                        receipt["extracted_evidence"] = inspect_zip(body, endpoint)
                    except (ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
                        receipt["extraction_status"] = "failed_raw_preserved"
                        receipt["error_type"] = type(exc).__name__
                else:
                    (target_out / endpoint).write_bytes(body)
                    try:
                        error = ET.fromstring(body)
                        receipt["api_status"] = next((normalized_text(node) for node in error.iter()
                                                       if local_name(node.tag) == "status"), None)
                    except ET.ParseError:
                        receipt["api_status"] = None
                    receipt["status"] = "no_zip_returned"
            print(json.dumps({"symbol": target["symbol"], "endpoint": endpoint,
                              "status": receipt["status"], "bytes": receipt.get("bytes"),
                              "api_status": receipt.get("api_status")}, ensure_ascii=False), flush=True)
        write_json(target_out / "source-evidence.json", item)
        results["targets"].append(item)
        write_json(out / "financial-source-precision-evidence.json", results)
    results["completed_at"] = now_iso()
    results["status"] = "probe_completed_requires_source_review"
    write_json(out / "financial-source-precision-evidence.json", results)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if request.get("branch") != os.environ.get("GITHUB_REF_NAME"):
        raise SystemExit("Probe request must match the current branch")
    try:
        run_probe(request.get("financial_probe", request), args.output, os.environ.get("DART_API_KEY", "").strip())
    except Exception as exc:
        raise SystemExit("Official source probe failed: " + type(exc).__name__) from None


if __name__ == "__main__":
    main()
