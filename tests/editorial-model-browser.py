"""Reusable model-sheet browser regressions; all image generation is mocked.

Start the Editorial Studio server, then run with Python + Playwright. No API key
or billable image calls are used. STUDIO_URL and STUDIO_BROWSER override defaults.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import struct
import zlib
from playwright.sync_api import sync_playwright, expect

URL = os.environ.get('STUDIO_URL', 'http://127.0.0.1:8787/editorial-studio.html')
BROWSER = os.environ.get('STUDIO_BROWSER', '/usr/bin/chromium')
REPORT = []


def png(width=100, height=150, color=(164, 172, 145)):
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data) & 0xFFFFFFFF)
    rows = b''.join(b'\x00' + bytes(color) * width for _ in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


PHOTO = png()
SHEET = 'data:image/png;base64,' + base64.b64encode(png(300, 200, (197, 202, 178))).decode()


def photo(name):
    return {'name': name, 'mimeType': 'image/png', 'buffer': PHOTO}


def record(name):
    REPORT.append(name)
    print('PASS', name, flush=True)


def make_page(browser, configured=False, viewport=None):
    context = browser.new_context(viewport=viewport or {'width': 1440, 'height': 1100}, accept_downloads=True)
    context.route('**/api/studio/**', lambda route: route.fulfill(status=501, json={'message': 'Unmocked API call forbidden in browser tests'}))
    context.route('**/api/studio/status', lambda route: route.fulfill(json={'configured': configured, 'model': 'mocked-provider'}))
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL, wait_until='networkidle')
    page.wait_for_function('() => !!window.MuseModel')
    page.evaluate('() => window.MuseModel.ready')
    page.locator('[data-view="model"]').first.click()
    return context, page, errors


def upload_model(page, count=4):
    page.locator('#model-photos-upload').set_input_files([photo(name) for name in ['front.png', 'body.png', 'side.png', 'back.png'][:count]])
    expect(page.locator('.model-photo-card')).to_have_count(count)
    # The first two images default to face and body; explicit role controls keep
    # optional profile/rear photographs distinguishable from the face anchor.
    cards = page.locator('.model-photo-card')
    if count > 2:
        cards.nth(2).locator('select').select_option('side')
    if count > 3:
        cards.nth(3).locator('select').select_option('back')
    page.locator('#model-name').fill('테스트 모델 01')
    details = page.locator('details.model-anchor-fields')
    if details.count() and not details.evaluate('(el) => el.open'):
        details.locator('summary').click()
    page.locator('#model-hair').fill('검은 단발')
    page.locator('#model-notes').fill('얼굴의 비율과 왼쪽 눈 밑 점 유지')


def export_kit(page):
    page.locator('#model-kit-export').click()
    expect(page.locator('#model-export-confirm')).to_be_visible()
    with page.expect_download() as exported:
        page.locator('#model-export-confirm').click()
    return json.loads(Path(exported.value.path()).read_text())


def mock_jobs(context, behavior='complete'):
    state = {'model_payload': None, 'editorial_payload': None, 'sheet_posts': 0, 'editorial_posts': 0, 'sheet_gets': 0, 'cancelled': False, 'release': False}

    def api(route):
        request = route.request
        if request.method == 'POST':
            is_sheet = request.url.split('?')[0].endswith('/model-sheet')
            key = 'model_payload' if is_sheet else 'editorial_payload'
            state[key] = request.post_data_json
            state['sheet_posts' if is_sheet else 'editorial_posts'] += 1
            if behavior == 'failure' and is_sheet:
                return route.fulfill(status=503, json={'message': '테스트: 생성 설정을 확인해주세요.'})
            return route.fulfill(status=202, json={'jobId': 'model-test-job' if is_sheet else 'editorial-test-job'})
        is_sheet = request.url.endswith('/model-test-job')
        if request.method == 'DELETE':
            state['cancelled'] = True
            return route.fulfill(json={'status': 'cancelled'})
        if is_sheet:
            state['sheet_gets'] += 1
            done = behavior == 'complete' or (behavior == 'delayed' and state['release'])
            status = 'cancelled' if state['cancelled'] else 'completed' if done else 'running'
            shots = [{'id': 'model-sheet-01', 'referenceId': state['model_payload']['profile']['id'], 'status': status, **({'dataUrl': SHEET} if done else {})}]
        else:
            done = True
            status = 'completed'
            shots = [{**shot, 'status': 'completed', 'dataUrl': SHEET} for shot in state['editorial_payload']['shots']]
        return route.fulfill(json={'id': 'model-test-job' if is_sheet else 'editorial-test-job', 'kind': 'model-sheet' if is_sheet else 'editorial', 'status': status, 'total': len(shots), 'completed': len(shots) if done else 0, 'failed': 0, 'shots': shots})

    context.route('**/api/studio/model-sheet', api)
    context.route('**/api/studio/generate', api)
    context.route('**/api/studio/jobs/*', api)
    return state


def start_sheet(page, mocked):
    page.locator('#model-sheet-generate').click()
    expect(page.locator('#model-dialog')).to_be_visible()
    assert mocked['sheet_posts'] == 0, 'A sheet must wait for the explicit paid-action confirmation'
    expect(page.locator('#model-dialog-content')).to_contain_text('유료')
    page.locator('#model-generation-confirm').click()


with sync_playwright() as play:
    browser = play.chromium.launch(executable_path=BROWSER, headless=True)
    try:
        context, page, errors = make_page(browser)
        expect(page.locator('#model-board')).to_contain_text('표정')
        expect(page.locator('#model-board')).to_contain_text('측면')
        expect(page.locator('#model-generated-preview img')).to_have_count(0)
        upload_model(page)
        expect(page.locator('#model-board')).to_contain_text('테스트 모델 01')
        page.locator('.model-photo-card').nth(2).locator('[data-model-action="primary"]').click()
        expect(page.locator('.model-photo-card').nth(2)).to_have_class('model-photo-card is-primary')
        page.locator('.model-photo-card').nth(0).locator('[data-model-action="primary"]').click()
        page.locator('.model-photo-card').nth(2).locator('select').select_option('side')
        page.locator('#model-sheet-generate').click()
        expect(page.locator('#model-dev-prompt')).to_be_visible()
        assert 'PRIORITY ORDER' in page.locator('#model-dev-prompt').input_value()
        assert not page.evaluate('window.MuseModel.snapshot().hasSheet'), 'Preparing source instructions must not fabricate an AI sheet'
        page.locator('#model-dialog-close').click()
        kit = export_kit(page)
        assert 'data:image' in json.dumps(kit), 'A reusable model kit must retain its source photos'
        page.reload(wait_until='networkidle')
        page.evaluate('() => window.MuseModel.ready')
        expect(page.locator('.model-photo-card')).to_have_count(4)
        expect(page.locator('#model-name')).to_have_value('테스트 모델 01')
        with page.expect_download() as board:
            page.locator('#model-board-export').click()
        assert Path(board.value.path()).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        assert not errors, errors
        record('source roles, truthful expression placeholders, local model persistence, reusable kit and original-photo PNG board')
        context.close()

        context, page, errors = make_page(browser, configured=True)
        mocked = mock_jobs(context)
        upload_model(page)
        start_sheet(page, mocked)
        expect(page.locator('#model-sheet-approve')).to_be_visible(timeout=15000)
        assert mocked['model_payload']['expressionCount'] == 8
        assert len(mocked['model_payload']['photos']) == 4
        assert len([p for p in mocked['model_payload']['photos'] if p.get('primary') and p['role'] == 'face']) == 1
        expect(page.locator('#model-generated-preview img')).to_have_count(2)
        page.locator('#model-sheet-approve').click()
        expect(page.locator('#board-view')).to_be_visible()
        expect(page.locator('#active-model-name')).to_contain_text('테스트 모델 01')
        page.locator('#reference-upload').set_input_files(photo('inspiration.png'))
        page.wait_for_function('() => window.EditorialStudio.snapshot().referenceCount === 1')
        page.locator('#generate-button').click()
        expect(page.locator('#confirm-generation')).to_be_visible()
        assert mocked['editorial_posts'] == 0
        page.locator('#confirm-generation').click()
        expect(page.locator('.result-image img')).to_have_count(10, timeout=15000)
        payload = mocked['editorial_payload']
        assert payload['identitySheet']['dataUrl'] == SHEET
        assert payload['identityProfile']['sheetApproved'] is True
        assert len(payload['supportingPhotos']) == 2
        original_face = next(p['dataUrl'] for p in mocked['model_payload']['photos'] if p.get('primary'))
        assert payload['identity']['face']['dataUrl'] == original_face
        page.locator('[data-view="model"]').first.click()
        approved_kit = export_kit(page)
        assert 'data:image' in json.dumps(approved_kit)
        page.screenshot(path='/tmp/editorial-model-approved-test.png', full_page=True)
        assert not errors, errors
        record('one paid sheet request, source comparison, explicit approval and unchanged face/body/sheet reused in all 10 editorial shots')
        context.close()

        context, page, errors = make_page(browser)
        page.locator('#model-kit-import').set_input_files({'name': 'approved-model.json', 'mimeType': 'application/json', 'buffer': json.dumps(approved_kit).encode()})
        expect(page.locator('#model-import-confirm')).to_be_visible()
        page.locator('#model-import-confirm').click()
        expect(page.locator('.model-photo-card')).to_have_count(4)
        expect(page.locator('#model-name')).to_have_value('테스트 모델 01')
        assert page.evaluate('window.MuseModel.snapshot().approved')
        details = page.locator('details.model-anchor-fields')
        if details.count() and not details.evaluate('(el) => el.open'):
            details.locator('summary').click()
        page.locator('#model-notes').fill('기준 변경: 피부의 작은 점을 보존')
        assert not page.evaluate('window.EditorialStudio.snapshot().sheetApproved')
        expect(page.locator('#model-sheet-approve')).to_be_hidden()
        edited_kit = export_kit(page)
        assert edited_kit != approved_kit
        invalid_kit = json.loads(json.dumps(approved_kit))
        invalid_kit['model']['photos'][0]['dataUrl'] = 'data:image/png;base64,AAAA'
        page.locator('#model-kit-import').set_input_files({'name': 'corrupt.json', 'mimeType': 'application/json', 'buffer': json.dumps(invalid_kit).encode()})
        expect(page.locator('#model-import-confirm')).to_have_count(0)
        expect(page.locator('.model-photo-card')).to_have_count(4)
        expect(page.locator('#model-notes')).to_have_value('기준 변경: 피부의 작은 점을 보존')
        assert not errors, errors
        record('approved kit import, source-edit approval invalidation and corrupt-import preservation')
        context.close()

        context, page, errors = make_page(browser, configured=True)
        mocked = mock_jobs(context, 'delayed')
        upload_model(page)
        start_sheet(page, mocked)
        expect(page.locator('#model-sheet-cancel')).to_be_visible()
        page.locator('#model-notes').fill('생성 중에 변경한 새 기준')
        mocked['release'] = True
        page.wait_for_timeout(4500)
        expect(page.locator('#model-sheet-approve')).to_be_hidden()
        assert not errors, errors
        record('an in-flight result cannot approve against a newer source revision')
        context.close()

        context, page, errors = make_page(browser, configured=True)
        mocked = mock_jobs(context, 'cancel')
        upload_model(page)
        start_sheet(page, mocked)
        expect(page.locator('#model-sheet-cancel')).to_be_visible()
        page.locator('#model-sheet-cancel').click()
        page.wait_for_function('() => document.querySelector("#model-sheet-cancel").hidden', timeout=15000)
        assert mocked['cancelled']
        expect(page.locator('#model-generated-preview img')).to_have_count(0)
        assert not errors, errors
        record('sheet cancellation stops queued work without fabricated output')
        context.close()

        context, page, errors = make_page(browser, configured=True)
        mocked = mock_jobs(context, 'failure')
        upload_model(page)
        start_sheet(page, mocked)
        expect(page.locator('#model-generation-status')).to_contain_text('테스트: 생성 설정을 확인해주세요')
        expect(page.locator('#model-generated-preview img')).to_have_count(0)
        expect(page.locator('.model-photo-card')).to_have_count(4)
        assert not errors, errors
        record('provider failures preserve source photos and never invent a generated sheet')
        context.close()

        context, page, errors = make_page(browser, viewport={'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile model view overflows'
        expect(page.locator('#model-sheet-generate')).to_be_visible()
        assert not errors, errors
        page.screenshot(path='/tmp/editorial-model-mobile-test.png', full_page=True)
        record('390px model workspace fits viewport with zero page exceptions')
        context.close()
    finally:
        browser.close()

print(json.dumps({'passed': len(REPORT), 'failed': 0, 'checks': REPORT, 'provider': 'mocked; no real image API calls'}, ensure_ascii=False, indent=2))
