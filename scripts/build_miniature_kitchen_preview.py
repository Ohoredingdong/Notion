#!/usr/bin/env python3
"""Build the isolated miniature design prototypes; never edits published entries."""
import argparse
import base64
import gzip
import hashlib
import json
from functools import lru_cache
from html import escape
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess


DELIVERY_LIMIT = 1048576
# The mobile opaque wrapper adds about 1.4KB to a packed native document.
DELIVERY_RESERVE = 2048
PACKED_MARKER = 'data-kitchen-packed="gzip-v1"'
SAFE_BASE85_ALPHABET = ('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
                        '!#$%&()*+-;<=>?@^_`{|}~').translate(str.maketrans('&<>', '.,/'))
BASE85_DECODER_JS = '''function decodeBase85(value){const alphabet=__ALPHABET__,digits=new Int16Array(128).fill(-1);for(let i=0;i<alphabet.length;i++)digits[alphabet.charCodeAt(i)]=i;if(value.length%5===1)throw new Error('Invalid kitchen base85 length');const padding=(5-value.length%5)%5,padded=value+'~'.repeat(padding),bytes=new Uint8Array(padded.length/5*4-padding);let offset=0;for(let i=0;i<padded.length;i+=5){let word=0;for(let j=0;j<5;j++){const code=padded.charCodeAt(i+j);if(code>127||digits[code]<0)throw new Error('Invalid kitchen base85 digit');word=word*85+digits[code];}if(word>4294967295)throw new Error('Invalid kitchen base85 value');for(let j=0;j<4;j++){if(offset<bytes.length)bytes[offset]=word>>>(24-j*8)&255;offset++;}}return bytes;}'''.replace('__ALPHABET__', json.dumps(SAFE_BASE85_ALPHABET))


def encode_base85(data):
    """RFC1924 base85 with three HTML-sensitive digits replaced losslessly."""
    return base64.b85encode(data).decode('ascii').translate(str.maketrans('&<>', '.,/'))


def decode_base85(value):
    if len(value) % 5 == 1:
        raise ValueError('Invalid kitchen base85 length')
    if any(character not in SAFE_BASE85_ALPHABET for character in value):
        raise ValueError('Invalid kitchen base85 digit')
    return base64.b85decode(value.translate(str.maketrans('.,/', '&<>')))


def unpack_document(content):
    """Recover and verify the exact original HTML from our optional envelope."""
    if PACKED_MARKER not in content:
        return content
    match = re.search(
        r'<template id="kitchenPacked" data-codec="(gzip-base64|gzip-base85)" '
        r'data-bytes="(\d+)" data-sha256="([0-9a-f]{64})">'
        r'([^<]*)</template>', content)
    if not match:
        raise ValueError('Invalid packed kitchen document')
    try:
        compressed = (base64.b64decode(match[4], validate=True) if match[1] == 'gzip-base64'
                      else decode_base85(match[4]))
        if not compressed.startswith(b'\x1f\x8b'):
            raise ValueError('Missing gzip header')
        raw = gzip.decompress(compressed)
    except (ValueError, OSError, EOFError) as error:
        raise ValueError('Invalid packed kitchen payload') from error
    if len(raw) != int(match[2]) or hashlib.sha256(raw).hexdigest() != match[3]:
        raise ValueError('Packed kitchen document does not match its original')
    return raw.decode('utf-8')


def pack_document(content, mode='app', *, codec='gzip-base64'):
    """Losslessly package HTML; every original image and script byte survives.

    The vendored synchronous decoder works without DecompressionStream or any
    runtime download. The original document is written only after the small
    envelope has finished parsing, retaining normal inline-script execution.
    """
    if mode not in ('app', 'widget'):
        raise ValueError('Unknown presentation')
    if codec not in ('gzip-base64', 'gzip-base85'):
        raise ValueError('Unknown kitchen codec')
    if PACKED_MARKER in content:
        unpack_document(content)
        return content
    raw = content.encode('utf-8')
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    payload = (base64.b64encode(compressed).decode('ascii') if codec == 'gzip-base64'
               else encode_base85(compressed))
    decoder = (Path(__file__).resolve().parent/'vendor/fflate-gunzip-0.8.2.min.js').read_text()
    if '</script' in decoder.lower():
        raise ValueError('Unexpected decoder script terminator')
    label = '위젯' if mode == 'widget' else '앱'
    digest = hashlib.sha256(raw).hexdigest()
    return f'''<!doctype html>
<html lang="ko" {PACKED_MARKER}><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f5eee3"><title>한끼의 부엌 · {label}</title>
<style>html,body{{margin:0;min-height:100%;background:#f5eee3;color:#514331;font:15px/1.5 -apple-system,BlinkMacSystemFont,sans-serif}}body{{display:grid;place-items:center;min-height:100vh}}p{{padding:16px}}</style>
</head><body><p role="status">부엌을 열고 있어요…</p>
<template id="kitchenPacked" data-codec="{codec}" data-bytes="{len(raw)}" data-sha256="{digest}">{payload}</template>
<script>{decoder}
(()=>{{{BASE85_DECODER_JS}function openKitchen(){{try{{const node=document.getElementById('kitchenPacked'),encoded=node.content.textContent,compressed=node.dataset.codec==='gzip-base85'?decodeBase85(encoded):Uint8Array.from(atob(encoded),c=>c.charCodeAt(0)),bytes=KitchenPackedDecoder.gunzipSync(compressed);if(bytes.length!==Number(node.dataset.bytes))throw new Error('Incomplete kitchen document');const html=new TextDecoder('utf-8',{{fatal:true,ignoreBOM:true}}).decode(bytes);document.open();document.write(html);document.close();}}catch(error){{document.body.textContent='화면을 열지 못했어요. 새로고침해 주세요.';document.body.setAttribute('role','alert');console.error(error);}}}}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',openKitchen,{{once:true}});else openKitchen();}})();
</script></body></html>'''


def fit_document(content, mode='app'):
    """Fit native and opaque-wrapper delivery without changing decoded bytes."""
    budget = DELIVERY_LIMIT - DELIVERY_RESERVE
    if len(content.encode('utf-8')) <= budget:
        return content
    original = unpack_document(content)
    packed = pack_document(original, mode)
    if len(packed.encode('utf-8')) > budget:
        packed = pack_document(original, mode, codec='gzip-base85')
    if len(packed.encode('utf-8')) > budget:
        raise ValueError('Lossless kitchen preview exceeds the 1 MiB delivery budget')
    return packed


# The compact build keeps every food/seasoning used by this isolated prototype.
# Unused atlas cells are omitted; source images and published apps stay untouched.
COMPACT_SPRITES = {
    'assets/food-miniatures-v2.webp': ('sprites', (1254,1254),
        ('carrot','onion','rice','chicken','garlic','potato','zucchini','oil','cheese','yogurt','lettuce','pepper','ingredient')),
    'assets/seasoning-miniatures-v1.png': ('seasoningSprites', (1448,1086),
        ('jar',)),
}

# Legacy tools/jars retain their original cropped pixels and encoding level.
COMPACT_REGIONS = {'designs/miniature-kitchen/assets/decor-atlas.png':
    ((1286,1223),((48,15,550,648),(773,675,445,504)))}

# New photo assets use pre-encoded full-resolution AVIF variants. Their PNG
# originals remain the authoring source; the measured encoding settings and
# WebP82 quality comparisons are recorded with the visual-fidelity evidence.
# Existing miniature assets retain their previous formats and encoding levels.
COMPACT_AVIF = {
    'designs/miniature-kitchen/assets/room-props-fullflow-v1.png':
        'designs/miniature-kitchen/assets/room-props-fullflow-v1.avif',
    'designs/miniature-kitchen/assets/fridge-cabinet-a1-v2.png':
        'designs/miniature-kitchen/assets/fridge-cabinet-a1-v2.avif',
    'designs/miniature-kitchen/assets/food-shelf-coherent-v2.png':
        'designs/miniature-kitchen/assets/food-shelf-coherent-v2.avif',
    'designs/miniature-kitchen/assets/kitchen-built-in-v2.png':
        'designs/miniature-kitchen/assets/kitchen-built-in-v2.avif',
    'designs/miniature-kitchen/assets/recipe-photos-v1.png':
        'designs/miniature-kitchen/assets/recipe-photos-v1.avif',
}


@lru_cache(maxsize=32)
def compact_script(source):
    """Keep the delivery budget without reducing image resolution or functionality."""
    encoder = os.environ.get('KITCHEN_TERSER') or shutil.which('terser')
    if not encoder:
        raise RuntimeError('--compact requires terser 5.44.1; install it outside the repository and set KITCHEN_TERSER to its executable')
    return subprocess.run([encoder, '--compress', '--mangle', '--ecma', '2020'],
                          input=source, text=True, check=True, capture_output=True).stdout.strip()


@lru_cache(maxsize=32)
def compact_style(source):
    """Minify CSS locally without rebasing URLs or fetching imports.

    Level one preserves rule order and avoids cross-rule restructuring. Image
    encoding is deliberately independent of this text-only delivery saving.
    """
    encoder = os.environ.get('KITCHEN_CLEANCSS') or shutil.which('cleancss')
    if not encoder:
        raise RuntimeError('--compact requires clean-css-cli 5.6.3 (clean-css 5.3.3); install it outside the repository and set KITCHEN_CLEANCSS to its executable')
    result = subprocess.run([encoder, '-O1', '--inline', 'none'], input=source,
                            text=True, check=True, capture_output=True)
    if result.stderr.strip():
        raise RuntimeError('CSS minifier reported a warning: '+result.stderr.strip()[:1500])
    if source.strip() and not result.stdout.strip():
        raise RuntimeError('CSS minifier returned an empty stylesheet')
    return result.stdout.strip()


def sprite_boxes(source, name, keys):
    match=re.search(r'const '+re.escape(name)+r'\s*=\s*Object\.freeze\(\{(.*?)\}\);',source,re.S)
    if not match:
        raise ValueError('Atlas map changed: '+name)
    boxes={key:tuple(map(int,values.split(','))) for key,values in
           re.findall(r"['\"]?([\w-]+)['\"]?\s*:\s*\[([\d,\s]+)\]",match[1])}
    if not all(key in boxes and len(boxes[key])==4 for key in keys):
        raise ValueError('Compact atlas cells changed: '+name)
    return tuple(boxes[key] for key in keys)


@lru_cache(maxsize=32)
def web_image(path, size, boxes):
    encoder=shutil.which('magick')
    if not encoder:
        raise RuntimeError('--compact requires ImageMagick (magick); the default build needs only Python')
    command=[encoder,'-limit','thread','2']
    if boxes:
        command+=['-size',f'{size[0]}x{size[1]}','xc:none']
        for x,y,width,height in boxes:
            command+=['(',str(path),'-crop',f'{width}x{height}+{x}+{y}','+repage',')',
                      '-geometry',f'+{x}+{y}','-composite']
    else:
        command+=[str(path)]
    if path.name=='food-miniatures-v2.webp':command+=['-resize','740x740']
    if path.name=='pantry-food-atlas.png':command+=['-resize','960x640']
    if path.name=='seasoning-miniatures-v1.png':command+=['-resize','550x413']
    if path.name=='door-insides.png':command+=['-resize','640x960']
    if path.name=='freezer-food.png':command+=['-resize','560x560']
    if path.name=='room-warm.png':command+=['-resize','900x1080']
    if path.name=='magnets.png':command+=['-resize','500x500']
    if path.name=='decor-atlas.png':command+=['-resize','560x533']
    quality='88' if path.name=='fridge-neutral-atlas.png' else '94' if path.name=='fridge-atlas.png' else '68' if path.name=='room-warm.png' else '76' if path.name in ('food-miniatures-v2.webp','freezer-food.png','decor-atlas.png') else '76' if path.name in ('room-centered.png','room-concept.png') else '82'
    command+=['-define','webp:method=6','-define','webp:alpha-quality=100','-quality',quality,'webp:-']
    return subprocess.run(command,check=True,capture_output=True).stdout


def build(root, mode, compact=False):
    if mode not in ('app', 'widget'):
        raise ValueError('Unknown presentation')
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
        # Chat previews must not depend on external image access or proxy thumbnails.
        data=path.read_bytes()
        if compact:
            if reference in COMPACT_AVIF:
                data=local(COMPACT_AVIF[reference]).read_bytes()
                mime='image/avif'
            else:
                size,boxes=None,()
                if reference in COMPACT_SPRITES:
                    name,size,keys=COMPACT_SPRITES[reference]
                    boxes=sprite_boxes(local('use-me-first-kitchen-art.js').read_text(),name,keys)
                elif reference in COMPACT_REGIONS:
                    size,boxes=COMPACT_REGIONS[reference]
                data=web_image(path,size,boxes)
                mime='image/webp'
        return 'data:'+mime+';base64,'+base64.b64encode(data).decode('ascii')

    scripts = []
    html = local('designs/miniature-kitchen/scene.html').read_text()

    def css(match):
        path = local(match[1])
        style = path.read_text()

        def url(m):
            target = (path.parent/m[1].strip('"\'')).resolve().relative_to(root).as_posix()
            return 'url("'+image(target)+'")'

        style = re.sub(r'url\([\'"]?([^\)]+?)\)', url, style)
        if compact:
            style = compact_style(style)
        if '</style' in style.lower():
            raise ValueError('Unexpected style terminator')
        return '<style>\n'+style+'\n</style>'

    def js(match):
        path = local(match[1])
        script = path.read_text()
        replacements = {
            'use-me-first-kitchen-art.js': [('ATLAS','assets/food-miniatures-v2.webp'),('SEASONING_ATLAS','assets/seasoning-miniatures-v1.png')],
            'play-ui.js': [('MAGNETS','designs/miniature-kitchen/assets/magnets.png')],
            'story-art.js': [('RECIPE_PHOTOS','designs/miniature-kitchen/assets/recipe-photos-v1.png')],
            'scene.js': [('FRIDGE','designs/miniature-kitchen/assets/fridge-cabinet-a1-v2.png'),('FOOD_SCENE','designs/miniature-kitchen/assets/food-shelf-coherent-v2.png'),('INNER_DOORS','designs/miniature-kitchen/assets/door-insides.png'),('DECOR','designs/miniature-kitchen/assets/decor-atlas.png'),('ROOM_PROPS','designs/miniature-kitchen/assets/room-props-fullflow-v1.png')]
        }
        for key, asset in replacements.get(path.name, []):
            needle=f"const {key} = './{asset}';"
            if script.count(needle) != 1:
                raise ValueError('Asset constant changed: '+key)
            script=script.replace(needle,f"const {key} = '{image(asset)}';")
        if compact:
            script = compact_script(script)
        scripts.append('<script>\n'+re.sub(r'</script',r'<\\/script',script,flags=re.I)+'\n</script>')
        return ''

    html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', css, html)
    html = re.sub(r'<script defer src="([^"]+)"></script>', js, html)
    html = html.replace('<body data-mode="app"',f'<body data-mode="{mode}"',1)
    html = html.replace('<!-- Source template. Generate the two self-contained previews with the builder. -->',
                        '<!-- Generated miniature preview. Separate preview storage only; production data untouched. -->')
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
    parser.add_argument('--compact',action='store_true',help='Embed web-encoded images and only the prototype atlas cells (requires ImageMagick)')
    args=parser.parse_args()
    root=args.root.resolve()
    output=(args.output_dir or root/'previews').resolve()
    if output.is_relative_to(root) and not output.is_relative_to(root/'previews'):
        raise SystemExit('Only previews/ or a folder outside the checkout is allowed.')
    output.mkdir(parents=True,exist_ok=True)
    pages={mode:build(root,mode,args.compact) for mode in ('app','widget')}
    if args.compact:
        pages={mode:fit_document(content,mode) for mode,content in pages.items()}
    if args.compact and any(len(page.encode('utf-8'))>DELIVERY_LIMIT for page in pages.values()):
        raise SystemExit('Compact preview exceeds the chosen 1 MiB delivery budget; no files were written.')
    for mode,content in pages.items():
        path=output/f'miniature-kitchen-{mode}.html';path.write_text(content);print(f'{path.name}: {path.stat().st_size:,} bytes')
    path=output/'miniature-kitchen-board.html';path.write_text(board(pages['app'],pages['widget']));print(f'{path.name}: {path.stat().st_size:,} bytes')


if __name__=='__main__':
    main()
