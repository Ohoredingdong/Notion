#!/usr/bin/env python3
"""Build small, self-contained kitchen previews for an external HTML preview URL."""
import argparse
from html import escape
from pathlib import Path

from build_miniature_kitchen_preview import build


def mobile_page(content, mode):
    label = '앱' if mode == 'app' else '위젯'
    # Public raw-file renderers share an origin across unrelated repositories.
    # An opaque frame uses the existing temporary-storage fallback and keeps
    # preview records out of that shared origin's persistent localStorage.
    return f'''<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#faf7f0">
<title>한끼의 부엌 · {label} 미리보기</title>
<style>html,body{{margin:0;width:100%;height:100%;background:#faf7f0;overflow:hidden}}iframe{{display:block;border:0;width:100%;height:100vh;height:100dvh}}</style>
</head><body>
<iframe title="한끼의 부엌 {label} 미리보기" sandbox="allow-scripts" srcdoc="{escape(content, quote=True)}"></iframe>
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
    pages = {mode: mobile_page(build(root, mode, compact=True), mode)
             for mode in ('app', 'widget')}
    if any(len(content.encode('utf-8')) > 1048576 for content in pages.values()):
        raise SystemExit('Mobile preview exceeds the 1 MiB delivery budget; no files written.')
    output.mkdir(parents=True, exist_ok=True)
    for mode, content in pages.items():
        path = output / f'{mode}.html'
        path.write_text(content, encoding='utf-8')
        print(f'{path.name}: {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
