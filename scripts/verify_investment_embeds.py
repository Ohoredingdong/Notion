"""Check candidate investment embeds; compare public bytes only when requested.

This command never publishes files. Expected hashes come from the exact checkout,
not a previous deployment. Live Notion UI remains a separate browser check.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import time
from urllib.error import URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BASE = "https://ohoredingdong.github.io/Notion/"
FILES = (
    "stock-paper-investing.html", "property-paper-investing.html",
    "assets/investment-labs-20261016/common.js",
    "assets/investment-labs-20261016/lab.css",
    "assets/investment-labs-20261016/stock.js",
    "assets/investment-labs-20261016/property.js",
    "assets/investment-labs-20261019/curriculum.js",
    "assets/investment-labs-20261019/trainer.js",
    "assets/investment-labs-20261019/trainer.css",
)


class VerificationError(RuntimeError):
    pass


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("src"):
            self.references.append(attrs["src"])
        if tag == "link" and "stylesheet" in attrs.get("rel", "").lower().split():
            self.references.append(attrs.get("href", ""))


def source_manifest(root=ROOT):
    """Validate local candidate assets and run real Node syntax checks."""
    root = Path(root).resolve()
    manifest = {}
    javascript = {root / name for name in FILES if name.endswith(".js")}
    for name in FILES:
        path = root / name
        if not path.resolve().is_relative_to(root) or not path.is_file():
            raise VerificationError(f"Missing or outside-checkout source: {name}")
        body = path.read_bytes()
        manifest[name] = {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        if name.endswith(".html"):
            parser = Assets()
            parser.feed(body.decode("utf-8"))
            local = []
            for reference in parser.references:
                parts = urlsplit(reference)
                if parts.scheme or parts.netloc:
                    continue
                asset = (path.parent / unquote(parts.path)).resolve()
                if not asset.is_relative_to(root) or not asset.is_file():
                    raise VerificationError(f"Missing or unsafe asset in {name}: {reference}")
                if asset.suffix == ".js":
                    javascript.add(asset)
                local.append(asset.relative_to(root).as_posix())
            required = {
                "assets/investment-labs-20261019/trainer.js",
                "assets/investment-labs-20261019/trainer.css",
                "assets/investment-labs-20261019/curriculum.js",
                "assets/investment-labs-20261016/common.js",
                "assets/investment-labs-20261016/lab.css",
                "assets/investment-labs-20261016/" +
                ("stock.js" if name.startswith("stock-") else "property.js"),
            }
            if not required.issubset(local) or len(local) != len(set(local)):
                raise VerificationError(f"Missing required or duplicate runtime/styles in {name}")
    for path in sorted(javascript):
        result = subprocess.run(["node", "--check", str(path)], text=True, capture_output=True)
        if result.returncode:
            raise VerificationError(f"JavaScript syntax failed: {path.relative_to(root)}\n{result.stderr}")
    return manifest


def public_base(value):
    parts = urlsplit(value)
    if parts.username or parts.password or parts.query or parts.fragment:
        raise VerificationError("Public base must not contain credentials, query or fragment")
    if value == PUBLIC_BASE:
        return value
    if (parts.hostname in {"localhost", "127.0.0.1", "::1"}
            and parts.scheme in {"http", "https"} and parts.path.endswith("/")):
        return value
    raise VerificationError("Public base must be the repository HTTPS Pages URL or a loopback test server")


def check_frame_headers(headers, name):
    xfo = ",".join(headers.get_all("X-Frame-Options", [])).upper()
    if "DENY" in xfo or "SAMEORIGIN" in xfo:
        raise VerificationError(f"Iframe blocked by X-Frame-Options: {name}")
    for policy in headers.get_all("Content-Security-Policy", []):
        # Repeated CSP headers may be combined into a comma-separated policy list.
        for directive in policy.replace(",", ";").split(";"):
            tokens = directive.lower().split()
            if tokens and tokens[0] == "frame-ancestors":
                if len(tokens) == 1 or "'none'" in tokens or "'self'" in tokens:
                    raise VerificationError(f"Iframe blocked by frame-ancestors: {name}")


def verify_public(manifest, base):
    """Require exact public bytes and embeddable HTML; no retries hide failure."""
    base = public_base(base)
    for name, expected in manifest.items():
        url = urljoin(base, name) + "?verify=" + str(time.time_ns())
        request = Request(url, headers={"User-Agent": "Investment-Embed-Check/3.0",
                                        "Cache-Control": "no-cache"})
        try:
            with urlopen(request, timeout=12) as response:
                if response.status != 200:
                    raise VerificationError(f"Public HTTP {response.status}: {name}")
                if urlsplit(response.geturl())[:3] != urlsplit(url)[:3]:
                    raise VerificationError(f"Unexpected public redirect: {name}")
                body = response.read()
                if hashlib.sha256(body).hexdigest() != expected["sha256"]:
                    raise VerificationError(f"Public SHA-256 differs from checkout: {name}")
                if name.endswith(".html"):
                    if response.headers.get_content_type() != "text/html":
                        raise VerificationError(f"Public HTML MIME is not text/html: {name}")
                    check_frame_headers(response.headers, name)
        except (OSError, URLError) as error:
            raise VerificationError(f"Public request failed for {name}: {type(error).__name__}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--public-base", help="Explicit read-only check of the Pages URL or a loopback server")
    args = parser.parse_args()
    manifest = source_manifest(args.root)
    if args.public_base:
        verify_public(manifest, args.public_base)
    print(json.dumps({"local_source": "passed", "files": manifest,
                      "public_comparison": "passed" if args.public_base else "not_requested",
                      "live_notion_ui": "not_checked"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error
