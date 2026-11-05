"""Read-only contract for data jobs serving the current canonical radar UI."""
from __future__ import annotations
import argparse
from html.parser import HTMLParser
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

MARKER = 'data-custom-radar-ui="flow-v3"'


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            src = dict(attrs).get('src')
            if src:
                self.sources.append(src)


def verify_canonical(root=Path('.')):
    root = Path(root)
    text = (root / 'stock-value-radar.html').read_text(encoding='utf-8')
    if MARKER not in text:
        return False
    parser = Scripts()
    parser.feed(text)
    sources = [urlsplit(src).path.removeprefix('./') for src in parser.sources]
    for name in ('assets/stock-radar-clean-bridge.js', 'assets/stock-radar-flow-v2.js'):
        if sources.count(name) != 1:
            raise RuntimeError('canonical_runtime_missing_or_duplicate: ' + name)
    if any(name in sources for name in ('assets/stock-radar-v8.js', 'assets/stock-radar-v9.js', 'assets/stock-radar-neutral.js')):
        raise RuntimeError('legacy_overlay_loaded_in_canonical_page')
    bridge = (root / 'assets/stock-radar-clean-bridge.js').read_text()
    for name in ('stock-opportunity-data.json', 'stock-investment-cases.json',
                 'stock-green-review-summary.json', 'stock-entry-plan-summary.json',
                 'stock-radar-accuracy-audit.json'):
        if name not in bridge:
            raise RuntimeError('canonical_evidence_feed_not_connected: ' + name)
    for name in sources:
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise RuntimeError('canonical_asset_missing_or_outside_checkout: ' + name)
        if path.suffix == '.js':
            subprocess.run(['node', '--check', str(path)], check=True, capture_output=True)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    args = parser.parse_args()
    if not verify_canonical(args.root):
        raise SystemExit('Canonical UI marker missing; refusing to treat the legacy page as verified.')
    print('Canonical runtime, source-bound evidence feeds and JS syntax verified without changing HTML or data.')
