#!/usr/bin/env python3
"""Export the existing fridge widget as one HTML file for detached previews.

The published entry and its modular sources stay unchanged. This export embeds
their styles, ordered scripts and local images; it uses the existing font stack
without downloading Google Fonts. It contains no inventory or sync credentials.
"""
import argparse
import base64
from functools import lru_cache
from html import escape
from html.parser import HTMLParser
import mimetypes
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


class TagAttributes(HTMLParser):
    def __init__(self, tag):
        super().__init__(convert_charrefs=True)
        self.attrs = {}
        self.feed(tag)

    def handle_starttag(self, _tag, attrs):
        self.attrs = dict(attrs)


def build(root):
    root = root.resolve()
    entry = root / "use-me-first.html"
    scripts = []

    def local_path(reference):
        url = urlsplit(reference)
        if url.scheme or url.netloc or url.fragment:
            raise ValueError(f"Expected a local asset: {reference}")
        path = (root / unquote(url.path)).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Asset path must stay inside the repository")
        return path

    @lru_cache(maxsize=None)
    def data_uri(reference):
        path = local_path(reference)
        mime = mimetypes.guess_type(path.name)[0]
        if not mime or not mime.startswith("image/"):
            raise ValueError(f"Expected an image: {path.name}")
        return "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode("ascii")

    def inline_css(reference):
        css = local_path(reference).read_text(encoding="utf-8")
        # The optional font import is the only external presentation dependency.
        css = re.sub(r"@import\s+url\(['\"]https://fonts\.googleapis\.com/[^)]*\)\s*;", "", css)

        def image_url(match):
            value = match.group(1).strip().strip("\"'")
            if value.startswith(("#", "data:")):
                return match.group(0)
            asset = local_path(reference).parent / value
            relative = asset.relative_to(root).as_posix()
            return 'url("' + data_uri(relative) + '")'

        css = re.sub(r"url\(\s*([^)]*?)\s*\)", image_url, css)
        if re.search(r"@import|</style", css, flags=re.I):
            raise ValueError("Unsupported CSS import or closing style tag")
        return '<style data-source="' + escape(reference, quote=True) + '">\n' + css + "\n</style>"

    def inline_link(match):
        tag = match.group(0)
        attrs = TagAttributes(tag).attrs
        if attrs.get("rel") == "stylesheet":
            return inline_css(attrs["href"])
        if attrs.get("rel") == "preload" and attrs.get("as") == "image":
            return tag.replace(attrs["href"], data_uri(attrs["href"]))
        return tag

    def collect_script(match):
        attrs = TagAttributes(match.group(0)).attrs
        if "src" not in attrs:
            raise ValueError("Entry contains an unexpected inline script")
        reference = attrs["src"]
        path = local_path(reference)
        js = path.read_text(encoding="utf-8")
        if path.name == "use-me-first-kitchen-art.js":
            needle = "const ATLAS = './assets/food-miniatures-v2.webp';"
            if js.count(needle) != 1:
                raise ValueError("The miniature atlas reference changed; update this exporter")
            js = js.replace(needle, "const ATLAS = '" + data_uri("assets/food-miniatures-v2.webp") + "';")
        # An inline script must not accidentally close its own HTML element.
        js = re.sub(r"</script", r"<\\/script", js, flags=re.I)
        scripts.append('<script data-source="' + escape(reference, quote=True) + '">\n' + js + "\n</script>")
        return ""

    html = entry.read_text(encoding="utf-8")
    html = re.sub(r"<link\b[^>]*>", inline_link, html, flags=re.I)
    html = re.sub(r"<script\b[^>]*>\s*</script\s*>", collect_script, html, flags=re.I)
    if not scripts or html.count("</body>") != 1:
        raise ValueError("The widget entry structure changed; export aborted")
    html = html.replace("</head>", '<meta name="umf-preview-mode" content="standalone">\n</head>')
    # The originals were deferred: keep their order after all markup is parsed.
    html = html.replace("</body>", "\n".join(scripts) + "\n</body>")
    return html


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    root = args.root.resolve()
    # Never replace the deployed entry or any of its original assets with an export.
    if output == root or (output.is_relative_to(root) and output.parts[len(root.parts):][0] != "previews"):
        raise SystemExit("Use an output outside the checkout or under previews/.")
    content = build(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"Standalone preview: {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
