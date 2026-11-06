import io
import unittest
import xml.etree.ElementTree as ET
import zipfile

from probe_stock_financial_reconciliation import (balance_candidate, declared_interval,
    extract_report_tables, extract_xbrl, inspect_accounts, inspect_zip, parse_xml, safe_get, TARGETS)


def fact(value, decimals):
    return {"value": str(value), "decimals": decimals}


def instance(assets_context="c", decimals="-3"):
    return ET.fromstring('''<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:ifrs="http://xbrl.ifrs.org/taxonomy" xmlns:xbrldi="http://xbrl.org/2006/xbrldi">
      <xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="corp">00153524</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="dart:ConsolidationAxis">dart:ConsolidatedMember</xbrldi:explicitMember></xbrli:segment></xbrli:entity>
      <xbrli:period><xbrli:instant>2026-06-30</xbrli:instant></xbrli:period></xbrli:context>
      <xbrli:unit id="KRW"><xbrli:measure>iso4217:KRW</xbrli:measure></xbrli:unit>
      <ifrs:Assets contextRef="%s" unitRef="KRW" decimals="%s">698863343000</ifrs:Assets>
      <ifrs:Liabilities contextRef="c" unitRef="KRW" decimals="%s">381374004000</ifrs:Liabilities>
      <ifrs:Equity contextRef="c" unitRef="KRW" decimals="%s">317489340000</ifrs:Equity>
      </xbrli:xbrl>''' % (assets_context, decimals, decimals, decimals))


class FinancialPrecisionProbeTests(unittest.TestCase):
    def test_declared_thousand_rounding_can_explain_one_thousand_not_two(self):
        supported = balance_candidate({"assets": fact(698863343000, "-3"),
            "liabilities": fact(381374004000, "-3"), "equity": fact(317489340000, "-3")})
        self.assertEqual(supported["reported_difference"], "-1000")
        self.assertEqual(supported["status"], "declared_intervals_have_interior_overlap")
        self.assertFalse(supported["publication_authorized"])
        unsupported = balance_candidate({"assets": fact(1853940513000, "-3"),
            "liabilities": fact(1468909797000, "-3"), "equity": fact(385030714000, "-3")})
        self.assertEqual(unsupported["reported_difference"], "2000")
        self.assertEqual(unsupported["status"], "outside_declared_precision")

    def test_missing_precision_and_extra_digits_do_not_waive_difference(self):
        self.assertIsNone(declared_interval(fact(1000, None)))
        self.assertIsNone(declared_interval(fact(1001, "-3")))
        self.assertIsNone(declared_interval(fact("NaN", "0")))
        self.assertIsNone(declared_interval(fact(1000, "-999")))

    def test_inf_is_exact_and_no_company_relative_tolerance(self):
        candidate = balance_candidate({"assets": fact(239741609993, "INF"),
            "liabilities": fact(33784721902, "INF"), "equity": fact(205956878286, "INF")})
        self.assertEqual(candidate["status"], "outside_declared_precision")
        self.assertEqual(candidate["difference_interval"], ["9805", "9805"])

    def test_context_period_unit_and_scope_are_preserved(self):
        parsed = extract_xbrl(instance(), "report.xbrl")
        self.assertEqual(len(parsed["balance_candidates"]), 1)
        candidate = parsed["balance_candidates"][0]
        self.assertEqual(candidate["context"]["period"]["instant"], "2026-06-30")
        self.assertEqual(candidate["context"]["dimensions"][0]["value"], "dart:ConsolidatedMember")
        self.assertEqual(candidate["unit"]["measures"], ["iso4217:KRW"])
        self.assertEqual(candidate["status"], "declared_intervals_have_interior_overlap")

    def test_different_contexts_never_form_one_equation(self):
        self.assertEqual(extract_xbrl(instance(assets_context="different"), "report.xbrl")["balance_candidates"], [])

    def test_duplicate_fact_is_ambiguous(self):
        root = instance()
        root.append(ET.fromstring('<f:Assets xmlns:f="http://xbrl.ifrs.org/taxonomy" contextRef="c" unitRef="KRW" decimals="-3">698863343000</f:Assets>'))
        self.assertEqual(extract_xbrl(root, "report.xbrl")["balance_candidates"][0]["status"], "ambiguous_duplicate_facts")

    def test_report_unit_is_preserved_without_inferring_scope(self):
        root = ET.fromstring('<DOCUMENT><TITLE>연결 재무상태표</TITLE><P>(단위 : 천원)</P><TABLE><TR><TD>자산총계</TD><TD>698,863,343</TD></TR><TR><TD>부채총계</TD><TD>381,374,004</TD></TR><TR><TD>자본총계</TD><TD>317,489,340</TD></TR></TABLE></DOCUMENT>')
        candidate = extract_report_tables(root, "document.xml")[0]
        self.assertIn("천원", candidate["unit_clauses"][0])
        self.assertTrue(candidate["consolidation_not_inferred"])

    def test_korean_report_encoding_preserves_units(self):
        raw = '<?xml version="1.0" encoding="euc-kr"?><DOCUMENT><P>(단위 : 천원)</P></DOCUMENT>'.encode('euc-kr')
        self.assertEqual(''.join(parse_xml(raw).itertext()), '(단위 : 천원)')

    def test_request_exception_does_not_expose_credential(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        def failure(*args, **kwargs):
            raise RuntimeError('request failed https://example.test?crtfc_key=sensitive-fixture')
        with patch.dict('sys.modules', {'requests': SimpleNamespace(get=failure)}):
            body, result = safe_get('document.xml', {}, 'sensitive-fixture')
        self.assertIsNone(body)
        self.assertEqual(result, {'status': 'request_failed', 'error_type': 'RuntimeError'})

    def test_zip_never_extracts_unsafe_paths(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("../unsafe.xml", "<x/>")
        with self.assertRaisesRegex(ValueError, "unsafe_archive_member"):
            inspect_zip(data.getvalue(), "document.xml")

    def test_api_identity_or_filing_mismatch_remains_explicit(self):
        body = {"status": "000", "list": [{"sj_div": "BS", "fs_div": "CFS", "account_nm": "자산총계",
                 "corp_code": "00153524", "rcept_no": "different-filing", "thstrm_amount": "1"}]}
        parsed = inspect_accounts(body, TARGETS[0], "fnlttMultiAcnt.json")
        self.assertFalse(parsed["selected_balance_rows"][0]["expected_issuer"])
        self.assertFalse(parsed["selected_balance_rows"][0]["expected_filing"])
        self.assertFalse(parsed["has_all_three_unambiguous"])


if __name__ == "__main__":
    unittest.main()
