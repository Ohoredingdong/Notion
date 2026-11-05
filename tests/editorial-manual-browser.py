"""No-billing development workflow regressions.

Run the latest local Editorial Studio server, then execute this file using Python
with Playwright installed. Preview prompts are built locally in the browser.
Every billable or obsolete preview endpoint is forbidden by these tests;
fixture images are synthetic test inputs, never presented as generated photos.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import struct
import zlib
from playwright.sync_api import sync_playwright, expect

URL = os.environ.get('STUDIO_URL', 'http://127.0.0.1:8792/editorial-studio.html')
BROWSER = os.environ.get('STUDIO_BROWSER', '/usr/bin/chromium')
REPORT = []


def png(width=100, height=150, color=(164, 172, 145)):
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data) & 0xFFFFFFFF)
    rows = b''.join(b'\x00' + bytes(color) * width for _ in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


def image_file(name='fixture.png', width=100, height=150, color=(164, 172, 145)):
    return {'name': name, 'mimeType': 'image/png', 'buffer': png(width, height, color)}


def record(name):
    REPORT.append(name)
    print('PASS', name, flush=True)


def make_page(browser, viewport=None):
    context = browser.new_context(viewport=viewport or {'width': 1440, 'height': 1100}, accept_downloads=True, permissions=['clipboard-read', 'clipboard-write'])
    calls = {'paid': [], 'preview': []}
    def forbidden(route):
        calls['paid'].append(route.request.url)
        route.fulfill(status=418, json={'message': 'Billable endpoint forbidden by manual-development browser test'})
    def preview(route):
        calls['preview'].append(route.request.post_data_json)
        route.fulfill(status=418, json={'message': 'Preview must be built in the browser without a server request'})
    context.route('**/api/studio/model-sheet', forbidden)
    context.route('**/api/studio/generate', forbidden)
    context.route('**/api/studio/status', lambda route: route.fulfill(json={'configured': False, 'model': 'gpt-image-1'}))
    context.route('**/api/studio/preview', preview)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL, wait_until='networkidle')
    page.wait_for_function('() => !!window.MuseModel')
    page.evaluate('() => window.MuseModel.ready')
    page.locator('[data-view="model"]').first.click()
    return context, page, calls, errors


def upload_model(page):
    page.locator('#model-photos-upload').set_input_files([
        image_file('front.png', color=(173, 156, 136)),
        image_file('body.png', color=(121, 137, 104)),
        image_file('side.png', color=(155, 165, 123)),
    ])
    expect(page.locator('.model-photo-card')).to_have_count(3)
    page.locator('.model-photo-card').nth(2).locator('select').select_option('side')
    page.locator('#model-name').fill('개발 검증 모델')
    page.evaluate('() => window.MuseModel.flush()')


def export_model_kit(page):
    page.locator('#model-kit-export').click()
    with page.expect_download() as downloaded:
        page.locator('#model-export-confirm').click()
    return json.loads(Path(downloaded.value.path()).read_text())


def assert_clean(calls, errors):
    assert not calls['paid'], f'Billable requests were attempted: {calls["paid"]}'
    assert not calls['preview'], 'Local prompt preparation must not POST photos to a preview API'
    assert not errors, errors


def model_preview(page):
    page.locator('#model-dev-preview').click()
    expect(page.locator('#model-dev-prompt')).to_be_visible(timeout=15000)
    expect(page.locator('#model-dev-prompt')).not_to_have_value('')
    return page.locator('#model-dev-prompt').input_value()


def import_manual_sheet(page):
    page.locator('#model-sheet-import').set_input_files(image_file('external-sheet.png', 300, 200, (194, 201, 174)))
    expect(page.locator('#model-manual-confirm')).to_be_visible()
    expect(page.locator('#model-manual-confirm')).not_to_be_checked()
    expect(page.locator('#model-manual-import-confirm')).to_be_disabled()
    page.locator('#model-manual-confirm').check()
    page.locator('#model-manual-import-confirm').click()
    expect(page.locator('#model-generated-preview img')).to_have_count(2)


with sync_playwright() as play:
    browser = play.chromium.launch(executable_path=BROWSER, headless=True)
    try:
        context, page, calls, errors = make_page(browser)
        upload_model(page)
        prompt = model_preview(page)
        assert 'PRIORITY ORDER' in prompt and 'authoritative' in prompt
        expect(page.locator('#model-dialog-content')).to_contain_text('ChatGPT')
        with page.expect_download() as downloaded:
            page.locator('#model-dev-export').click()
        manifest = json.loads(Path(downloaded.value.path()).read_text())
        # The downloaded pack exposes the actual provider prompt and original
        # image order; synthetic fixture pixels are not generated image output.
        raw = manifest.get('manifest', manifest)
        assert raw['billable'] is False
        assert raw['kind'] == 'model-sheet'
        assert raw['shots'][0]['prompt'] == prompt
        inputs = {item['id']: item for item in raw['inputs']}
        ordered = [inputs[key] for key in raw['shots'][0]['inputIds']]
        assert len(ordered) == 3
        assert ordered[0]['role'] == 'face' and ordered[1]['role'] == 'body'
        assert all(item['dataUrl'].startswith('data:image/') for item in ordered)
        page.locator('#model-dev-copy').click()
        assert page.evaluate('navigator.clipboard.readText()') == prompt
        page.locator('#model-dialog-close').click()
        assert not page.evaluate('window.MuseModel.snapshot().hasSheet')
        assert_clean(calls, errors)
        record('local unconfigured preview exports exact prompt and numbered source inputs without any preview API, paid call or fabricated output')
        context.close()

        context, page, calls, errors = make_page(browser)
        upload_model(page)
        model_preview(page)
        page.locator('#model-dialog-close').click()
        import_manual_sheet(page)
        expect(page.locator('#model-generated-preview')).to_contain_text('외부')
        assert not page.evaluate('window.MuseModel.snapshot().approved')
        page.locator('#model-sheet-approve').click()
        expect(page.locator('#board-view')).to_be_visible()
        assert page.evaluate('window.EditorialStudio.snapshot().sheetApproved')
        page.locator('[data-view="model"]').first.click()
        kit = export_model_kit(page)
        assert kit['model']['sheet']['origin'] == 'manual'
        assert kit['model']['sheet']['approved'] is True
        page.reload(wait_until='networkidle')
        page.evaluate('() => window.MuseModel.ready')
        assert page.evaluate('window.EditorialStudio.snapshot().sheetApproved')
        assert_clean(calls, errors)
        record('external sheet import requires attestation, stays unapproved until review and preserves manual origin across saved-kit reload')
        context.close()

        context, page, calls, errors = make_page(browser)
        page.locator('#model-kit-import').set_input_files({'name':'manual-model-kit.json','mimeType':'application/json','buffer':json.dumps(kit).encode()})
        page.locator('#model-import-confirm').click()
        page.locator('[data-view="board"]').first.click()
        page.locator('#reference-upload').set_input_files(image_file('mood.png', color=(151, 148, 130)))
        page.wait_for_function('() => window.EditorialStudio.snapshot().referenceCount === 1')
        page.locator('[data-ratio="4:5"]').click()
        page.locator('#studio-dev-preview').click()
        expect(page.locator('#studio-dev-prompt')).to_be_visible(timeout=15000)
        expect(page.locator('#studio-dev-shot option')).to_have_count(10)
        first_prompt = page.locator('#studio-dev-prompt').input_value()
        page.locator('#studio-dev-shot').select_option('9')
        tenth_prompt = page.locator('#studio-dev-prompt').input_value()
        assert first_prompt != tenth_prompt, 'Each planned pose/gaze/framing needs its own prompt'
        with page.expect_download() as exported:
            page.locator('#studio-dev-export').click()
        editorial = json.loads(Path(exported.value.path()).read_text())
        assert editorial['billable'] is False and editorial['kind'] == 'editorial'
        assert len(editorial['shots']) == 10
        sources = {item['id']:item for item in editorial['inputs']}
        ordered = [sources[key] for key in editorial['shots'][0]['inputIds']]
        assert [item['role'] for item in ordered[:4]] == ['face','body','identity-sheet','reference']
        assert editorial['shots'][0]['prompt'] == first_prompt
        assert editorial['shots'][9]['prompt'] == tenth_prompt
        page.locator('#studio-dev-copy').click()
        assert page.evaluate('navigator.clipboard.readText()') == tenth_prompt
        page.locator('#dialog-close').click()
        page.locator('#studio-manual-import').set_input_files([
            image_file('external-shot-a.png', 100, 150, (133, 148, 120)),
            image_file('external-shot-b.png', 120, 180, (177, 160, 137)),
        ])
        expect(page.locator('#studio-manual-confirm')).to_be_visible()
        expect(page.locator('#studio-manual-confirm')).not_to_be_checked()
        expect(page.locator('#studio-manual-import-confirm')).to_be_disabled()
        page.locator('[data-import-index="1"]').select_option('0')
        page.locator('#studio-manual-confirm').check()
        page.locator('#studio-manual-import-confirm').click()
        expect(page.locator('#toast')).to_contain_text('중복 선택')
        expect(page.locator('#results-grid .result-image img')).to_have_count(0)
        page.locator('[data-import-index="1"]').select_option('3')
        page.locator('#studio-manual-import-confirm').click()
        expect(page.locator('#results-view')).to_be_visible()
        expect(page.locator('#results-grid .result-image img')).to_have_count(2)
        expect(page.locator('#results-grid .result-card')).to_have_count(10)
        expect(page.locator('#results-grid')).to_contain_text('외부 결과 가져오기 대기')
        expect(page.locator('#results-grid')).to_contain_text('외부 생성 · 수동 검증')
        page.wait_for_function('() => [...document.querySelectorAll("#results-grid .result-image img")].every(image => image.complete && image.naturalWidth*5 === image.naturalHeight*4)')
        with page.expect_download() as downloaded:
            page.locator('#results-grid .is-complete [data-action="download-shot"]').first.click()
        assert downloaded.value.suggested_filename.endswith('.jpg')
        assert Path(downloaded.value.path()).read_bytes().startswith(b'\xff\xd8')
        page.locator('#results-grid .is-complete [data-action="favorite-shot"]').first.click()
        page.locator('[data-results-filter="favorites"]').click()
        expect(page.locator('#results-grid .result-image img')).to_have_count(1)
        page.locator('[data-results-filter="all"]').click()
        page.screenshot(path='/tmp/editorial-manual-results-test.png', full_page=True)
        page.locator('[data-view="board"]').first.click()
        page.locator('#brief').fill('새 방향으로 바꾸면 이전 결과와 연결하지 않기')
        page.locator('#studio-manual-import').set_input_files(image_file('stale-shot.png'))
        expect(page.locator('#toast')).to_contain_text('변경됐어요')
        expect(page.locator('#studio-manual-confirm')).to_be_hidden()
        assert_clean(calls, errors)
        record('editorial preview reuses approved identity, exposes 10 distinct prompts and imports cropped labeled external results with slot validation/downloads/favorites')
        context.close()

        context, page, calls, errors = make_page(browser)
        upload_model(page)
        model_preview(page)
        page.locator('#model-dialog-close').click()
        details = page.locator('details.model-anchor-fields')
        if details.count() and not details.evaluate('(element) => element.open'):
            details.locator('summary').click()
        page.locator('#model-notes').fill('원본 수정 후에는 새 검증 자료를 준비해야 합니다.')
        page.locator('#model-sheet-import').set_input_files(image_file('old-source-result.png', 300, 200))
        expect(page.locator('#toast')).to_contain_text('원본이 바뀌었습니다')
        expect(page.locator('#model-manual-confirm')).to_have_count(0)
        assert not page.evaluate('window.MuseModel.snapshot().hasSheet')
        model_preview(page)
        page.locator('#model-dialog-close').click()
        import_manual_sheet(page)
        assert page.evaluate('window.MuseModel.snapshot().sheetOrigin') == 'manual'
        assert_clean(calls, errors)
        record('changed source revisions reject old-preview result imports until new prompt evidence is prepared')
        context.close()

        context, page, calls, errors = make_page(browser)
        upload_model(page)
        page.evaluate('''() => {
          window.__originalMusePrompts = window.MusePrompts;
          window.MusePrompts = {...window.MusePrompts, buildPreview: async () => {
            throw new Error('테스트: 브라우저 제작자료 준비 실패');
          }};
        }''')
        page.locator('#model-dev-preview').click()
        expect(page.locator('#toast')).to_contain_text('테스트: 브라우저 제작자료 준비 실패')
        expect(page.locator('#model-dev-prompt')).to_have_count(0)
        expect(page.locator('.model-photo-card')).to_have_count(3)
        assert not page.evaluate('window.MuseModel.snapshot().hasSheet')
        page.evaluate('() => {window.MusePrompts = window.__originalMusePrompts;}')
        model_preview(page)
        assert not page.evaluate('window.MuseModel.snapshot().hasSheet')
        assert_clean(calls, errors)
        record('local prompt builder failure preserves originals without fake output and recovers without a server')
        context.close()

        context, page, calls, errors = make_page(browser)
        upload_model(page)
        page.evaluate('''() => {
          const original = window.MusePrompts;
          window.MusePrompts = {...original, buildPreview: async (...args) => {
            const result = await original.buildPreview(...args);
            await new Promise(resolve => {window.__releaseModelPreview = resolve;});
            return result;
          }};
        }''')
        page.locator('#model-dev-preview').click()
        page.wait_for_function('() => typeof window.__releaseModelPreview === "function"')
        page.locator('#model-name').fill('준비 중 바뀐 모델')
        page.evaluate('() => window.__releaseModelPreview()')
        expect(page.locator('#toast')).to_contain_text('원본이 바뀌었습니다')
        expect(page.locator('#model-dev-prompt')).to_have_count(0)
        expect(page.locator('.model-photo-card')).to_have_count(3)
        assert not page.evaluate('window.MuseModel.snapshot().hasDevPreview')
        assert not page.evaluate('window.MuseModel.snapshot().hasSheet')
        assert_clean(calls, errors)
        record('an asynchronous local prompt cannot attach stale evidence after its source revision changes')
        context.close()

        context, page, calls, errors = make_page(browser)
        upload_model(page)
        page.locator('#model-use-photos').click()
        page.locator('#reference-upload').set_input_files(image_file('race-mood.png'))
        page.wait_for_function('() => window.EditorialStudio.snapshot().referenceCount === 1')
        page.evaluate('''() => {
          const original = window.MusePrompts;
          window.MusePrompts = {...original, buildPreview: async (...args) => {
            const result = await original.buildPreview(...args);
            await new Promise(resolve => {window.__releaseEditorialPreview = resolve;});
            return result;
          }};
        }''')
        page.locator('#studio-dev-preview').click()
        page.wait_for_function('() => typeof window.__releaseEditorialPreview === "function"')
        page.locator('#brief').fill('자료 준비 중 바뀐 화보 방향')
        page.evaluate('() => window.__releaseEditorialPreview()')
        expect(page.locator('#toast')).to_contain_text('방향이 바뀌었습니다')
        expect(page.locator('#studio-dev-prompt')).to_have_count(0)
        expect(page.locator('#results-grid .result-image img')).to_have_count(0)
        assert page.evaluate('window.EditorialStudio.snapshot().hasFace && window.EditorialStudio.snapshot().hasBody')
        assert_clean(calls, errors)
        record('an asynchronous editorial prompt rejects a changed brief without losing uploaded source photographs')
        context.close()

        context, page, calls, errors = make_page(browser, {'width':390,'height':844})
        upload_model(page)
        model_preview(page)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('#model-dialog').evaluate('(element) => element.scrollWidth <= element.clientWidth+1')
        page.screenshot(path='/tmp/editorial-manual-mobile-test.png', full_page=True)
        assert_clean(calls, errors)
        record('mobile no-billing developer tools fit the viewport without page errors')
        context.close()
    finally:
        browser.close()

print(json.dumps({'passed': len(REPORT), 'failed': 0, 'checks': REPORT, 'paid_requests': 0, 'quality_validation': 'fixture workflow only; real generation quality untested'}, ensure_ascii=False, indent=2))
