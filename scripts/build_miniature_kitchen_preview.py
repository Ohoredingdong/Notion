#!/usr/bin/env python3
"""Build the isolated miniature design prototypes; never edits published entries."""
import argparse
import base64
from functools import lru_cache
from html import escape
import mimetypes
from pathlib import Path
import re


def build(root, mode, asset_revision=None):
    if mode not in ('app', 'widget'):
        raise ValueError('Unknown presentation')
    if asset_revision is not None and not re.fullmatch(r'[0-9a-f]{40}', asset_revision):
        raise ValueError('Asset revision must be a full lowercase Git commit SHA')
    root = root.resolve()

    def local(reference):
        path = (root/reference).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Asset outside the checkout')
        return path

    @lru_cache(maxsize=None)
    def image(reference):
        path = local(reference)
        mime = mimetypes.guess_type(path.name)[0]
        if not mime or not mime.startswith('image/'):
            raise ValueError('Expected an image')
        if asset_revision is not None:
            return ('https://raw.githubusercontent.com/Ohoredingdong/Notion/'
                    +asset_revision+'/'+path.relative_to(root).as_posix())
        return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode('ascii')

    scripts = []
    html = local('designs/miniature-kitchen/scene.html').read_text()

    def css(match):
        path = local(match[1])
        style = path.read_text()

        def url(m):
            target = (path.parent/m[1].strip('"\'')).resolve().relative_to(root).as_posix()
            return 'url("'+image(target)+'")'

        style = re.sub(r'url\([\'"]?([^\)]+?)\)', url, style)
        if '</style' in style.lower():
            raise ValueError('Unexpected style terminator')
        return '<style>\n'+style+'\n</style>'

    def js(match):
        path = local(match[1])
        script = path.read_text()
        replacements = {
            'use-me-first-kitchen-art.js': [('ATLAS','assets/food-miniatures-v2.webp'),('SEASONING_ATLAS','assets/seasoning-miniatures-v1.png')],
            'scene.js': [('FRIDGE','designs/miniature-kitchen/assets/fridge-atlas.png'),('DECOR','designs/miniature-kitchen/assets/decor-atlas.png')]
        }
        for key, asset in replacements.get(path.name, []):
            needle=f"const {key} = './{asset}';"
            if script.count(needle) != 1:
                raise ValueError('Asset constant changed: '+key)
            script=script.replace(needle,f"const {key} = '{image(asset)}';")
        scripts.append('<script>\n'+re.sub(r'</script',r'<\\/script',script,flags=re.I)+'\n</script>')
        return ''

    html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', css, html)
    html = re.sub(r'<script defer src="([^"]+)"></script>', js, html)
    html = html.replace('data-mode="app"',f'data-mode="{mode}"')
    html = html.replace('<!-- Source template. Generate the two self-contained previews with the builder. -->',
                        '<!-- Generated isolated visual prototype. Example data only; no application storage. -->')
    return html.replace('</body>','\n'.join(scripts)+'\n</body>')


def board(app_html, widget_html):
    html = '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>한끼의 부엌 · 미니어처 앱/위젯 비교</title>
<style>*{box-sizing:border-box}body{margin:0;background:#eeebe4;color:#393d32;font:14px/1.6 -apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic',sans-serif}main{max-width:1840px;margin:auto;padding:24px}header{margin-bottom:20px}h1{font-size:25px;letter-spacing:-1px;margin:0 0 6px}p{margin:0;color:#716a5c;font-size:13px}.views{display:grid;grid-template-columns:minmax(0,1fr) 520px;gap:22px}.view{min-width:0}h2{font-size:14px;display:flex;justify-content:space-between;align-items:center;margin:0 0 10px}a{color:#4c7150;font-size:12px}iframe{width:100%;height:1040px;border:1px solid #d7cdbb;border-radius:24px;display:block;background:#faf7f0;box-shadow:0 10px 35px #6f5c3f13}@media(max-width:1200px){.views{grid-template-columns:minmax(0,1fr)}.view.widget{width:min(100%,560px);margin:auto}main{padding:16px}h1{font-size:22px}}</style></head>
<body><main><header><h1>직접 만지고 꾸미는, 나의 작은 부엌</h1><p>선택하신 미니어처 방향의 디자인·조작 시안입니다. 예시 재료로 동작하며 기존 앱 기록을 사용하지 않습니다.</p></header><div class="views">
<section class="view"><h2>앱 시안 <a href="miniature-kitchen-app.html" target="_blank" rel="noopener">크게 열기 ↗</a></h2><iframe src="miniature-kitchen-app.html" title="미니어처 부엌 앱 시안" sandbox="allow-scripts"></iframe></section>
<section class="view widget"><h2>위젯 시안 <a href="miniature-kitchen-widget.html" target="_blank" rel="noopener">크게 열기 ↗</a></h2><iframe src="miniature-kitchen-widget.html" title="미니어처 부엌 위젯 시안" sandbox="allow-scripts"></iframe></section>
</div></main><script>
const previewURLs=[];
for(const link of document.querySelectorAll('.view h2 a'))link.addEventListener('click',event=>{
 event.preventDefault();const html=link.closest('.view').querySelector('iframe').srcdoc;
 const url=URL.createObjectURL(new Blob([html],{type:'text/html'}));previewURLs.push(url);window.open(url,'_blank','noopener');
});
window.addEventListener('pagehide',()=>previewURLs.forEach(url=>URL.revokeObjectURL(url)));
</script></body></html>'''
    return html.replace('src="miniature-kitchen-app.html"','srcdoc="'+escape(app_html,quote=True)+'"').replace(
        'src="miniature-kitchen-widget.html"','srcdoc="'+escape(widget_html,quote=True)+'"')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--asset-revision',help='Use image URLs pinned to this full Git commit instead of embedding images')
    args=parser.parse_args()
    root=args.root.resolve()
    output=(args.output_dir or root/'previews').resolve()
    if output.is_relative_to(root) and not output.is_relative_to(root/'previews'):
        raise SystemExit('Only previews/ or a folder outside the checkout is allowed.')
    output.mkdir(parents=True,exist_ok=True)
    pages={mode:build(root,mode,args.asset_revision) for mode in ('app','widget')}
    for mode,content in pages.items():
        path=output/f'miniature-kitchen-{mode}.html';path.write_text(content);print(f'{path.name}: {path.stat().st_size:,} bytes')
    path=output/'miniature-kitchen-board.html';path.write_text(board(pages['app'],pages['widget']));print(f'{path.name}: {path.stat().st_size:,} bytes')


if __name__=='__main__':
    main()
