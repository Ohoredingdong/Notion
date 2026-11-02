#!/usr/bin/env python3
"""Build small, self-contained kitchen previews for an external HTML preview URL."""
import argparse
from pathlib import Path

from build_miniature_kitchen_preview import build, fit_document, pack_document, DELIVERY_LIMIT


def mobile_page(content, mode):
    label = '앱' if mode == 'app' else '위젯'
    if '\0' in content:
        raise ValueError('A null character cannot round-trip through HTML text')
    # The template holds text, not HTML nodes or JavaScript string syntax.
    # Escape ampersands first so existing character references survive exactly;
    # escaping '<' also survives HTMLPreview's naive literal <script rewrite.
    # Quotes/backslashes need no escaping. A numeric CR reference prevents the
    # HTML parser from normalizing CR/CRLF in otherwise exact source text.
    payload = content.replace('&', '&amp;').replace('<', '&lt;').replace('\r', '&#13;')
    # Public raw-file renderers share an origin across unrelated repositories.
    # An opaque frame uses the existing temporary-storage fallback and keeps
    # preview records out of that shared origin's persistent localStorage.
    return f'''<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f5eee3">
<title>한끼의 부엌 · {label} 미리보기</title>
<style>html,body{{margin:0;width:100%;height:100%;background:#f5eee3;overflow:hidden}}iframe{{display:block;border:0;width:100%;height:100vh;height:100dvh}}</style>
</head><body>
<iframe title="한끼의 부엌 {label} 미리보기" sandbox="allow-scripts allow-forms"></iframe>
<template id="kitchenSource">{payload}</template>
<script>document.querySelector('iframe').srcdoc=document.getElementById('kitchenSource').content.textContent;document.getElementById('kitchenSource').remove();</script>
</body></html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output_dir or root / 'previews/mobile').resolve()
    if output.is_relative_to(root) and not output.is_relative_to(root / 'previews'):
        raise SystemExit('Only previews/ or a folder outside the checkout is allowed.')
    pages = {}
    for mode in ('app', 'widget'):
        content = fit_document(build(root, mode, compact=True), mode)
        page = mobile_page(content, mode)
        if len(page.encode('utf-8')) > DELIVERY_LIMIT:
            page = mobile_page(pack_document(content, mode), mode)
        pages[mode] = page
    if any(len(content.encode('utf-8')) > DELIVERY_LIMIT for content in pages.values()):
        raise SystemExit('Mobile preview exceeds the 1 MiB delivery budget; no files written.')
    output.mkdir(parents=True, exist_ok=True)
    for mode, content in pages.items():
        path = output / f'{mode}.html'
        path.write_text(content, encoding='utf-8')
        print(f'{path.name}: {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
