"""Syntax and real checked-in data checks. Never repairs or refreshes a snapshot."""
from __future__ import annotations

import argparse
import ast
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit


def fail_constant(value):
    raise ValueError('Non-finite JSON constant: ' + value)


def strict_json(text):
    return json.loads(text, parse_constant=fail_constant)


def data_errors(root: Path, names: list[str]) -> list[str]:
    errors = []
    for name in names:
        path = root / name
        if not path.is_file() or path.suffix not in ('.json', '.jsonl'):
            continue
        try:
            text = path.read_text()
            if path.suffix == '.jsonl':
                for number, line in enumerate(text.splitlines(), 1):
                    if line.strip():
                        try:
                            strict_json(line)
                        except ValueError as error:
                            raise ValueError(f'line {number}: {error}') from error
            else:
                value = strict_json(text)
                # Existing real market snapshots: reject broken identity/price
                # types, while preserving missing values and honest no-call data.
                if name == 'stock-opportunity-data.json':
                    companies = value.get('companies')
                    if not isinstance(companies, list) or not companies:
                        raise ValueError('Missing actual company snapshot')
                    for row in companies:
                        if not isinstance(row.get('symbol'), str) or not row['symbol']:
                            raise ValueError('Company symbol must retain its string identity')
                        price = row.get('price')
                        if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float))
                                                  or not math.isfinite(price) or price <= 0):
                            raise ValueError('Price must be positive/finite or explicitly missing')
        except (OSError, ValueError, TypeError, AttributeError) as error:
            errors.append(f'{name}: {error}')
    return errors


class Sources(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inline = []
        self.references = []
        self.script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script':
            kind = attrs.get('type', '').lower()
            if attrs.get('src'):
                self.references.append(attrs['src'])
            elif kind in ('', 'text/javascript', 'application/javascript', 'module'):
                self.script = [kind, '']
        elif tag == 'link' and 'stylesheet' in attrs.get('rel', '') and attrs.get('href'):
            self.references.append(attrs['href'])

    def handle_data(self, text):
        if self.script is not None:
            self.script[1] += text

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            self.inline.append(self.script)
            self.script = None


def syntax_errors(root: Path, names: list[str]) -> list[str]:
    errors = []
    context_path = root / 'config/site-sources.json'
    config = json.loads(context_path.read_text()) if context_path.is_file() else {}
    contexts = {name: row['render_at'] for name, row in config.get('template_contexts', {}).items()}
    contexts.update({name: row['original_context'] for name, row in config.get('preserved_archives', {}).items()})
    for name in names:
        path = root / name
        if not path.is_file():
            continue
        try:
            if path.suffix == '.py':
                ast.parse(path.read_bytes(), filename=name)
            elif path.suffix in ('.js', '.mjs', '.cjs'):
                result = subprocess.run(['node', '--check', str(path)], text=True, capture_output=True)
                if result.returncode:
                    raise ValueError(result.stderr.strip())
            elif path.suffix == '.html':
                sources = Sources()
                sources.feed(path.read_text())
                for index, (kind, body) in enumerate(sources.inline):
                    if not body.strip():
                        continue
                    command = ['node', '--check']
                    if kind == 'module':
                        command.append('--input-type=module')
                    result = subprocess.run(command, input=body, text=True, capture_output=True)
                    if result.returncode:
                        raise ValueError(f'inline script {index}: {result.stderr.strip()}')
                for reference in sources.references:
                    url = urlsplit(reference)
                    if url.scheme or url.netloc or not url.path:
                        continue
                    context = root / contexts[name] if name in contexts else path
                    target = root / unquote(url.path).lstrip('/') if url.path.startswith('/') else context.parent / unquote(url.path)
                    target = target.resolve()
                    if not target.is_relative_to(root.resolve()) or not target.is_file():
                        raise ValueError('Missing local script/stylesheet: ' + reference)
            elif path.suffix == '.sh':
                result = subprocess.run(['bash', '-n', str(path)], text=True, capture_output=True)
                if result.returncode:
                    raise ValueError(result.stderr.strip())
        except (OSError, ValueError, SyntaxError) as error:
            errors.append(f'{name}: {error}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--files-json', type=Path, required=True)
    parser.add_argument('--kind', choices=['syntax', 'data'], required=True)
    args = parser.parse_args()
    names = json.loads(args.files_json.read_text())
    if not isinstance(names, list) or not all(isinstance(n, str) and not Path(n).is_absolute()
                                            and '..' not in Path(n).parts for n in names):
        parser.error('Expected normalized repository-relative files')
    errors = (syntax_errors if args.kind == 'syntax' else data_errors)(args.root.resolve(), names)
    for error in errors:
        print(error, file=sys.stderr)
    print(f'{args.kind}: inspected {len(names)} selected paths; {len(errors)} errors')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
