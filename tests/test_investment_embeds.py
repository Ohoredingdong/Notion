"""Offline failure cases use mocked HTTP, never an external service."""
from email.message import Message
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import urlsplit

from scripts import verify_investment_embeds as checker


class Response:
    def __init__(self, url, body, content_type, extra=()):
        self.url, self.body, self.status = url, body, 200
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        for key, value in extra:
            self.headers[key] = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self):
        return self.body


class InvestmentEmbedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Real checkout bytes and actual Node --check results, not fixture claims.
        cls.manifest = checker.source_manifest()

    def fixture(self):
        directory = tempfile.TemporaryDirectory(prefix="investment-embed-test-")
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for name in checker.FILES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((checker.ROOT / name).read_bytes())
        return root

    def response(self, request, timeout, *, mutate=None, extra=(), mime="text/html"):
        name = urlsplit(request.full_url).path.removeprefix("/Notion/")
        body = (checker.ROOT / name).read_bytes()
        if mutate:
            body = mutate(body)
        return Response(request.full_url, body,
                        mime if name.endswith(".html") else "text/plain", extra)

    def test_current_nine_sources_pass_real_node_and_reference_checks(self):
        self.assertEqual(len(self.manifest), 9)
        for name, actual in self.manifest.items():
            self.assertEqual(actual["sha256"], hashlib.sha256(
                (checker.ROOT / name).read_bytes()).hexdigest())

    def test_expected_hashes_follow_changed_checkout_bytes(self):
        root = self.fixture()
        name = "assets/investment-labs-20261016/common.js"
        path = root / name
        path.write_bytes(path.read_bytes() + b"\n// test-only candidate edit\n")
        manifest = checker.source_manifest(root)
        self.assertNotEqual(manifest[name]["sha256"], self.manifest[name]["sha256"])
        self.assertEqual(manifest[name]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_missing_trainer_reference_fails(self):
        root = self.fixture()
        path = root / "stock-paper-investing.html"
        path.write_text(path.read_text().replace(
            '<script defer src="./assets/investment-labs-20261019/trainer.js"></script>', ""))
        with self.assertRaisesRegex(checker.VerificationError, "Missing required"):
            checker.source_manifest(root)

    def test_invalid_javascript_fails_real_node_check(self):
        root = self.fixture()
        path = root / "assets/investment-labs-20261016/common.js"
        path.write_text("const = ;")
        with self.assertRaisesRegex(checker.VerificationError, "JavaScript syntax failed"):
            checker.source_manifest(root)

    def test_exact_public_bytes_and_headers_pass(self):
        with patch.object(checker, "urlopen", side_effect=self.response) as opener:
            checker.verify_public(self.manifest, checker.PUBLIC_BASE)
        self.assertEqual(opener.call_count, 9)

    def test_public_content_hash_mismatch_fails(self):
        with patch.object(checker, "urlopen", side_effect=lambda *a, **kw:
                          self.response(*a, **kw, mutate=lambda b: b + b"changed")):
            with self.assertRaisesRegex(checker.VerificationError, "SHA-256 differs"):
                checker.verify_public(self.manifest, checker.PUBLIC_BASE)

    def test_frame_blocking_headers_fail(self):
        for header in (("X-Frame-Options", "deny"), ("X-Frame-Options", " SAMEORIGIN "),
                       ("Content-Security-Policy", "default-src 'self'; FRAME-ANCESTORS    'none'"),
                       ("Content-Security-Policy", "default-src 'self', frame-ancestors 'none'"),
                       ("Content-Security-Policy", "frame-ancestors\t'self'; object-src 'none'")):
            with self.subTest(header=header), patch.object(checker, "urlopen",
                    side_effect=lambda *a, **kw: self.response(*a, **kw, extra=[header])):
                with self.assertRaisesRegex(checker.VerificationError, "Iframe blocked"):
                    checker.verify_public(self.manifest, checker.PUBLIC_BASE)

    def test_repeated_csp_headers_are_all_checked(self):
        headers = [("Content-Security-Policy", "default-src 'self'"),
                   ("Content-Security-Policy", "frame-ancestors 'none'")]
        with patch.object(checker, "urlopen", side_effect=lambda *a, **kw:
                          self.response(*a, **kw, extra=headers)):
            with self.assertRaisesRegex(checker.VerificationError, "Iframe blocked"):
                checker.verify_public(self.manifest, checker.PUBLIC_BASE)

    def test_non_html_mime_fails(self):
        with patch.object(checker, "urlopen", side_effect=lambda *a, **kw:
                          self.response(*a, **kw, mime="application/octet-stream")):
            with self.assertRaisesRegex(checker.VerificationError, "MIME"):
                checker.verify_public(self.manifest, checker.PUBLIC_BASE)

    def test_network_failure_is_not_success(self):
        with patch.object(checker, "urlopen", side_effect=URLError("test-only offline failure")):
            with self.assertRaisesRegex(checker.VerificationError, "Public request failed"):
                checker.verify_public(self.manifest, checker.PUBLIC_BASE)

    def test_arbitrary_public_origin_is_rejected_before_request(self):
        with patch.object(checker, "urlopen") as opener:
            with self.assertRaisesRegex(checker.VerificationError, "repository HTTPS Pages URL"):
                checker.verify_public(self.manifest, "https://example.invalid/")
        opener.assert_not_called()
        self.assertEqual(checker.public_base("http://127.0.0.1:8765/Notion/"),
                         "http://127.0.0.1:8765/Notion/")


if __name__ == "__main__":
    unittest.main()
