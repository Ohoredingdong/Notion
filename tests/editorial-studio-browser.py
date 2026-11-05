"""Editorial Studio browser regressions. Run the local server first.

Uses mock image-provider responses only. No API key, real provider request or
billable generation is used. Requires Playwright and a system Chromium.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import struct
import tempfile
import zlib
from playwright.sync_api import sync_playwright, expect

URL = os.environ.get('STUDIO_URL', 'http://127.0.0.1:8787/editorial-studio.html')
BROWSER = os.environ.get('STUDIO_BROWSER', '/usr/bin/chromium')
REPORT = []


def png(width=80, height=120):
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data) & 0xFFFFFFFF)
    rows = b''.join(b'\x00' + bytes([160, 175, 134]) * width for _ in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


IMAGE = png()
DATA_URL = 'data:image/png;base64,' + base64.b64encode(IMAGE).decode()


def image_file(name='model.png'):
    return {'name': name, 'mimeType': 'image/png', 'buffer': IMAGE}


def record(name):
    REPORT.append(name)
    print('PASS', name, flush=True)


def make_page(browser, configured=False, viewport=None):
    context = browser.new_context(viewport=viewport or {'width': 1440, 'height': 1000}, accept_downloads=True)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    context.route('**/api/studio/status', lambda route: route.fulfill(json={'configured': configured, 'model': 'test-provider'}))
    page.goto(URL, wait_until='networkidle')
    page.locator('[data-view="board"]').first.click()
    page.wait_for_function('(configured) => window.EditorialStudio?.snapshot().configured === configured', arg=configured)
    return context, page, errors


def upload(page, refs=1):
    page.locator('#face-upload').set_input_files(image_file('face.png'))
    page.locator('#body-upload').set_input_files(image_file('body.png'))
    page.wait_for_function('() => window.EditorialStudio.snapshot().hasFace && window.EditorialStudio.snapshot().hasBody')
    page.locator('#reference-upload').set_input_files([image_file(f'reference-{i}.png') for i in range(refs)])
    page.wait_for_function('(n) => window.EditorialStudio.snapshot().referenceCount === n', arg=min(refs, 3))


def request_mock(context, behavior='complete'):
    state = {'payload': None, 'posts': 0, 'gets': 0, 'cancelled': False}
    def api(route):
        req = route.request
        if req.method == 'POST':
            state['posts'] += 1
            state['payload'] = req.post_data_json
            if behavior == 'failure':
                return route.fulfill(status=503, json={'message': '테스트: 생성 연결을 확인해주세요.'})
            return route.fulfill(status=202, json={'jobId': 'test-job'})
        if req.method == 'DELETE':
            state['cancelled'] = True
            return route.fulfill(json={'status': 'cancelled'})
        state['gets'] += 1
        if behavior == 'expired':
            return route.fulfill(status=404, json={'message': '작업이 없거나 보관 시간이 지났습니다.'})
        finished = behavior == 'complete' and state['gets'] > 1
        status = 'cancelled' if state['cancelled'] else 'completed' if finished else 'running'
        shots = [{
            'id': shot['id'], 'referenceId': shot['referenceId'],
            'status': 'cancelled' if state['cancelled'] else 'completed' if finished else 'running' if index < 2 else 'queued',
            **({'dataUrl': DATA_URL} if finished else {})
        } for index, shot in enumerate(state['payload']['shots'])]
        return route.fulfill(json={'id': 'test-job', 'status': status, 'total': len(shots), 'completed': len(shots) if finished else 0, 'failed': 0, 'shots': shots})
    context.route('**/api/studio/generate', api)
    context.route('**/api/studio/jobs/*', api)
    return state


def start(page, state):
    page.locator('#generate-button').click()
    expect(page.locator('#confirm-generation')).to_be_visible()
    assert state['posts'] == 0, 'A billable request must wait for the on-page confirmation'
    expect(page.locator('#dialog-body')).to_contain_text('유료 요청')
    page.locator('#confirm-generation').click()


with sync_playwright() as play:
    browser = play.chromium.launch(executable_path=BROWSER, headless=True)
    try:
        context, page, errors = make_page(browser)
        page.locator('#generate-button').click()
        expect(page.locator('#app-dialog')).to_be_visible()
        expect(page.locator('.shot-plan-row')).to_have_count(10)
        expect(page.locator('#dialog-body')).to_contain_text('예시 사진은 생성 결과가 아닙니다')
        expect(page.locator('#results-grid .result-card')).to_have_count(0)
        page.locator('#dialog-close').click()
        page.locator('[data-mode="wedding"]').click()
        expect(page.locator('#stage-main')).to_have_attribute('src', './assets/editorial-studio/bridal.jpg')
        page.locator('[data-ratio="4:5"]').click()
        page.locator('[data-brief="자연광"]').click()
        expect(page.locator('#brief')).to_have_value('자연광')
        upload(page, refs=4)
        assert page.evaluate('window.EditorialStudio.snapshot().referenceCount') == 3
        assert len(page.evaluate('window.EditorialStudio.buildPlan()')) == 30
        first_plan = page.evaluate('window.EditorialStudio.buildPlan().slice(0,10)')
        assert len({(s['pose'], s['gaze'], s['framing']) for s in first_plan}) == 10
        record('honest demo, wedding mode, upload replacement, three-reference limit, 30 distinct shot directions')

        page.locator('.reference-add').first.click()
        layer = page.locator('.stage-layer').last
        layer.focus()
        original_left = layer.evaluate('(el) => parseFloat(el.style.left)')
        layer.press('ArrowLeft')
        assert layer.evaluate('(el) => parseFloat(el.style.left)') < original_left
        box = layer.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.down()
        page.mouse.move(box['x'] + box['width'] / 2 - 35, box['y'] + box['height'] / 2 + 20, steps=5)
        page.mouse.up()
        assert layer.evaluate('(el) => parseFloat(el.style.left)') < original_left - 1
        layer.dblclick()
        expect(page.locator('#layer-scale')).to_be_visible()
        page.locator('#layer-scale').focus()
        page.locator('#layer-scale').press('ArrowRight')
        page.locator('#layer-done').click()
        assert layer.evaluate('(el) => parseFloat(el.style.width)') > 25
        with page.expect_download() as saved:
            page.locator('#save-button').click()
        data = json.loads(Path(saved.value.path()).read_text())
        assert data['mode'] == 'wedding' and len(data['shots']) == 30
        assert 'data:image' not in json.dumps(data), 'Plan exports must exclude uploaded photo bytes'
        record('pointer/keyboard placement, scale adjustment and metadata-only plan download')
        assert not errors, errors
        context.close()

        context, page, errors = make_page(browser, configured=True)
        mocked = request_mock(context)
        upload(page)
        page.locator('[data-ratio="4:5"]').click()
        start(page, mocked)
        expect(page.locator('#results-view')).to_be_visible()
        expect(page.locator('.result-card')).to_have_count(10)
        expect(page.locator('.result-image img')).to_have_count(10, timeout=15000)
        assert len(mocked['payload']['shots']) == 10
        assert mocked['payload']['identity']['face']['dataUrl'].startswith('data:image/jpeg')
        assert mocked['payload']['references'][0]['dataUrl'].startswith('data:image/jpeg')
        page.wait_for_function('() => [...document.querySelectorAll(".result-image img")].every(i=>i.complete&&i.naturalWidth>0)')
        dimensions = page.locator('.result-image img').first.evaluate('(el) => [el.naturalWidth,el.naturalHeight]')
        assert dimensions[0] * 5 == dimensions[1] * 4, dimensions
        page.locator('[data-action="favorite-shot"]').first.click()
        page.locator('[data-results-filter="favorites"]').click()
        expect(page.locator('.result-card')).to_have_count(1)
        with page.expect_download() as saved:
            page.locator('[data-action="download-shot"]').click()
        assert saved.value.suggested_filename.endswith('.jpg')
        assert Path(saved.value.path()).read_bytes().startswith(b'\xff\xd8\xff')
        page.locator('[data-action="preview-shot"]').click()
        expect(page.locator('#download-preview')).to_be_visible()
        page.locator('#dialog-close').click()
        assert not errors, errors
        page.screenshot(path='/tmp/editorial-studio-results-test.png', full_page=True)
        record('paid-action confirmation, real payload roles, progress, 10 output cards, exact 4:5 crop, favorites and JPEG download')
        context.close()

        context, page, errors = make_page(browser, configured=True)
        mocked = request_mock(context, 'cancel')
        upload(page)
        start(page, mocked)
        expect(page.locator('#cancel-button')).to_be_visible()
        page.locator('#cancel-button').click()
        page.wait_for_function('() => [...document.querySelectorAll(".result-placeholder p")].every(p=>p.textContent==="취소됨")', timeout=15000)
        assert mocked['cancelled']
        expect(page.locator('#cancel-button')).to_be_hidden()
        assert not errors, errors
        record('job cancellation terminates queued images without fabricated output')
        context.close()

        context, page, errors = make_page(browser, configured=True)
        mocked = request_mock(context, 'failure')
        upload(page)
        start(page, mocked)
        expect(page.locator('#toast')).to_contain_text('테스트: 생성 연결을 확인해주세요')
        expect(page.locator('#generate-button')).to_be_enabled()
        expect(page.locator('.result-image')).to_have_count(0)
        assert not errors, errors
        record('generation failure preserves inputs and never displays fake output')
        context.close()

        context, page, errors = make_page(browser, configured=True)
        mocked = request_mock(context, 'expired')
        upload(page)
        start(page, mocked)
        expect(page.locator('#generate-button')).to_be_enabled(timeout=10000)
        page.wait_for_timeout(3000)
        assert mocked['gets'] == 1, 'Expired jobs must stop polling'
        expect(page.locator('.result-image')).to_have_count(0)
        assert not errors, errors
        record('expired jobs terminate polling and allow a new generation')
        context.close()

        context, page, errors = make_page(browser)
        video_base64 = page.evaluate('''async () => {
            const canvas=document.createElement('canvas'); canvas.width=80;canvas.height=120;
            const context=canvas.getContext('2d');
            const stream=canvas.captureStream(10);
            const chunks=[];const recorder=new MediaRecorder(stream,{mimeType:'video/webm'});
            recorder.ondataavailable=e=>chunks.push(e.data);
            const stopped=new Promise(resolve=>recorder.onstop=resolve);
            recorder.start();
            for(let i=0;i<5;i++){context.fillStyle=i%2?'#acb88b':'#ded6ba';context.fillRect(0,0,80,120);await new Promise(r=>setTimeout(r,100));}
            recorder.stop();await stopped;stream.getTracks().forEach(t=>t.stop());
            const bytes=new Uint8Array(await new Blob(chunks,{type:'video/webm'}).arrayBuffer());
            return btoa(String.fromCharCode(...bytes));
        }''')
        page.locator('#reference-upload').set_input_files({'name': 'mood.webm', 'mimeType': 'video/webm', 'buffer': base64.b64decode(video_base64)})
        expect(page.locator('#capture-frame')).to_be_enabled(timeout=15000)
        page.locator('#capture-frame').click()
        expect(page.locator('.reference-video')).to_contain_text('영상 프레임')
        assert page.evaluate('window.EditorialStudio.snapshot().referenceCount') == 1
        assert not errors, errors
        record('video decoding and chosen-frame conversion into a mood reference')
        transfer = page.evaluate_handle('''(encoded) => {
            const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
            const transfer=new DataTransfer();
            transfer.items.add(new File([bytes],'dropped-photo.png',{type:'image/png'}));
            return transfer;
        }''', base64.b64encode(IMAGE).decode())
        page.locator('#reference-dropzone').dispatch_event('drop', {'dataTransfer': transfer})
        page.wait_for_function('() => window.EditorialStudio.snapshot().referenceCount === 2')
        record('file drag/drop adds an image reference beside the video frame')
        context.close()

        context, page, errors = make_page(browser, viewport={'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile page overflow'
        expect(page.locator('#generate-button')).to_be_visible()
        assert not errors, errors
        page.screenshot(path='/tmp/editorial-studio-mobile-test.png', full_page=True)
        record('390px mobile layout and zero page exceptions across all scenarios')
        context.close()
    finally:
        browser.close()

print(json.dumps({'passed': len(REPORT), 'failed': 0, 'checks': REPORT, 'provider': 'mocked; no real image API calls'}, ensure_ascii=False, indent=2))
