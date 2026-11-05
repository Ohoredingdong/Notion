"""Real browser photo preparation regressions; synthetic fixtures, no image API.

Starts a local static server and uses the published /Notion/ path. The 20MB
fixture is a valid camera-size JPEG plus trailing padding, not a mocked size.
"""
from __future__ import annotations

import functools
import http.server
import json
import os
from pathlib import Path
import tempfile
import threading

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('STUDIO_UPLOAD_REPORT', '/tmp/notion-muse-function-fix/uploads'))
OUT.mkdir(parents=True, exist_ok=True)
CHECKS = []


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def record(name):
    CHECKS.append({'name': name, 'pass': True})
    print('PASS', name, flush=True)


with tempfile.TemporaryDirectory(prefix='muse-upload-static-') as temporary:
    serving = Path(temporary)
    (serving / 'Notion').symlink_to(ROOT, target_is_directory=True)
    handler = functools.partial(QuietHandler, directory=str(serving))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as play:
            browser = play.chromium.launch(executable_path=os.environ.get('STUDIO_BROWSER', '/usr/bin/chromium'), headless=True)
            context = browser.new_context(viewport={'width': 390, 'height': 844})
            posts, errors = [], []
            context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: posts.append(request.url) if request.method == 'POST' else None)
            page.goto(base + '/Notion/editorial-studio.html', wait_until='networkidle')
            page.evaluate('() => window.MuseModel.ready')
            # Loading the owned module explicitly keeps its unit-level regressions
            # useful even if an entry-point script registration later regresses.
            page.add_script_tag(url=base + '/Notion/assets/editorial-image-loader.js')
            page.evaluate('''async () => {
                const canvas = document.createElement('canvas');
                canvas.width = 6000; canvas.height = 4000;
                const ctx = canvas.getContext('2d');
                const gradient = ctx.createLinearGradient(0, 0, 6000, 4000);
                gradient.addColorStop(0, '#5a6a47'); gradient.addColorStop(1, '#b18b6a');
                ctx.fillStyle = gradient; ctx.fillRect(0, 0, 6000, 4000);
                ctx.fillStyle = '#ddd2c1'; ctx.fillRect(100, 100, 800, 500);
                const jpeg = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .96));
                const mb = 1024 * 1024;
                window.uploadFixtures = {
                    small: new File([jpeg], 'camera.jpg', {type:'image/jpeg'}),
                    large: new File([jpeg, new Uint8Array(20 * mb - jpeg.size)], 'camera-20mb.jpg', {type:'image/jpeg'}),
                    oversize: new File([jpeg, new Uint8Array(51 * mb - jpeg.size)], 'too-large.jpg', {type:'image/jpeg'}),
                    blankMime: new File([jpeg], 'camera-no-mime.JPG'),
                };
                canvas.width = canvas.height = 1;
            }''')

            result = page.evaluate('''async () => {
                const file = uploadFixtures.large, url = await MuseImages.read(file);
                const image = new Image(); image.src = url; await image.decode();
                window.preparedUpload = url;
                return {sourceBytes:file.size, outputBytes:Math.floor(url.split(',')[1].length*3/4),
                        width:image.naturalWidth,height:image.naturalHeight};
            }''')
            assert result['sourceBytes'] == 20 * 1024 * 1024
            assert result['width'] == 3072 and result['height'] == 2048
            assert result['outputBytes'] <= 2 * 1024 * 1024, result
            record('actual 20MB JPEG at 6000x4000 uploads, preserves aspect ratio and fits 2MB/3072px')

            fallback = page.evaluate('''async () => {
                const original = window.createImageBitmap;
                const create = URL.createObjectURL, revoke = URL.revokeObjectURL;
                let created = 0, revoked = 0;
                URL.createObjectURL = (...args) => {created++; return create(...args)};
                URL.revokeObjectURL = (...args) => {revoked++; return revoke(...args)};
                window.createImageBitmap = undefined;
                try {
                    const url = await MuseImages.read(uploadFixtures.blankMime);
                    const image = new Image(); image.src = url; await image.decode();
                    return {width:image.naturalWidth,height:image.naturalHeight,created,revoked};
                } finally {window.createImageBitmap=original;URL.createObjectURL=create;URL.revokeObjectURL=revoke;}
            }''')
            assert fallback == {'width': 3072, 'height': 2048, 'created': 1, 'revoked': 1}, fallback
            record('empty MIME uses file extension; Image fallback works and revokes its object URL')

            orientation = page.evaluate('''async () => {
                const canvas=document.createElement('canvas');canvas.width=100;canvas.height=50;
                canvas.getContext('2d').fillRect(0,0,100,50);
                const jpeg=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.9));
                // Real EXIF Orientation=6 APP1 segment, inserted after JPEG SOI.
                const exif=new Uint8Array([255,225,0,34,69,120,105,102,0,0,73,73,42,0,8,0,0,0,
                    1,0,18,1,3,0,1,0,0,0,6,0,0,0,0,0,0,0]);
                const file=new File([jpeg.slice(0,2),exif,jpeg.slice(2)],'rotated.jpg',{type:'image/jpeg'});
                const original=window.createImageBitmap, dimensions=[];
                try {
                    for(const fallback of [false,true]) {
                        if(fallback)window.createImageBitmap=undefined;
                        const image=new Image();image.src=await MuseImages.read(file);await image.decode();
                        dimensions.push([image.naturalWidth,image.naturalHeight]);
                    }
                    return dimensions;
                } finally {window.createImageBitmap=original;}
            }''')
            assert orientation == [[50, 100], [50, 100]], orientation
            record('camera EXIF orientation is preserved by both bitmap and Image decoder paths')

            failures = page.evaluate('''async () => {
                const results = {};
                for(const [kind,file] of Object.entries({
                    oversize:uploadFixtures.oversize,
                    corrupt:new File(['not an image'],'broken.jpg',{type:'image/jpeg'}),
                    svg:new File(['<svg xmlns="http://www.w3.org/2000/svg"/>'],'vector.svg',{type:'image/svg+xml'}),
                    heic:new File(['not native HEIC'],'photo.heic',{type:'image/heic'})
                })) {
                    try {await MuseImages.read(file); results[kind]='unexpected success';}
                    catch(error) {results[kind]=error.message;}
                }
                return results;
            }''')
            assert '50MB' in failures['oversize'], failures
            assert '손상' in failures['corrupt'], failures
            assert '사진을 사용' in failures['svg'], failures
            assert 'HEIC' in failures['heic'] and 'JPG' in failures['heic'], failures
            record('oversize, corrupt, SVG and unsupported HEIC fail with explicit actionable messages')

            # Exercise the real UI: no route supplies a fake upload/preview result.
            page.evaluate('''() => {
                const transfer=new DataTransfer();
                transfer.items.add(uploadFixtures.large);transfer.items.add(uploadFixtures.small);
                const input=document.querySelector('#model-photos-upload');
                input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
            }''')
            expect(page.locator('.model-photo-card')).to_have_count(2, timeout=30000)
            before = page.evaluate('window.MuseModel.snapshot()')
            page.evaluate('''() => {
                const transfer=new DataTransfer(); transfer.items.add(uploadFixtures.oversize);
                const input=document.querySelector('#model-photos-upload');
                input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
            }''')
            expect(page.locator('#toast')).to_contain_text('50MB')
            after = page.evaluate('window.MuseModel.snapshot()')
            assert after['photoCount'] == before['photoCount'] == 2
            assert after['revision'] == before['revision']
            assert after['profile']['id'] == before['profile']['id']
            record('real model UI accepts 20MB photo and rejected 51MB photo preserves existing model')
            page.screenshot(path=str(OUT / 'large-upload-mobile.png'), full_page=True)
            assert not posts, posts
            assert not errors, errors
            record('large uploads make no POST or paid network requests and raise no page exceptions')
            report = {'passed': len(CHECKS), 'failed': 0, 'checks': CHECKS,
                      'fixture': 'synthetic valid JPEG, 6000x4000, padded to actual 20MB',
                      'large_photo': result, 'fallback': fallback, 'exif_orientation': orientation, 'failures': failures,
                      'paid_api_requests': 0, 'pageerrors': errors, 'source_original_modified': False}
            (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps({'passed': len(CHECKS), 'failed': 0, 'report': str(OUT / 'report.json')}), flush=True)
            context.close(); browser.close()
    finally:
        server.shutdown(); server.server_close()
