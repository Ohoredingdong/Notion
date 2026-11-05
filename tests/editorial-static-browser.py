"""Exercise the published MUSE workflow on a real static HTTP server.

The server has no API implementation. No API response is mocked, no photograph
is generated and no paid service is called. Synthetic PNGs stand for source and
externally imported pictures; these checks do not measure image-generation quality.
Run with Python + Playwright; artifacts stay outside the checkout.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import struct
import tempfile
from threading import Thread
import traceback
import zlib

from playwright.sync_api import sync_playwright, expect


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', default='/usr/bin/chromium')
    return parser.parse_args()


def fixture(name, width=80, height=120, color=(160, 175, 134), compress=True):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    rows = (b'\0' + bytes(color) * width) * height
    image = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
             + chunk(b'IDAT', zlib.compress(rows, level=6 if compress else 0)) + chunk(b'IEND', b''))
    return {'name': name, 'mimeType': 'image/png', 'buffer': image}


def main():
    args = arguments()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='muse-static-browser-'))
    if output == root or root in output.parents:
        raise SystemExit('Keep browser artifacts outside the checkout')
    output.mkdir(parents=True, exist_ok=True)
    sources = [root / 'editorial-studio.html', *sorted((root / 'assets').glob('editorial-*.js'))]
    fingerprint = lambda: {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    before = fingerprint()
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'source': str(root),
              'mode': 'static server; no mocked API responses; synthetic test images; no paid generation',
              'checks': [], 'requests': [], 'screenshots': [], 'errors': []}

    def check(name, condition, detail=None):
        report['checks'].append({'name': name, 'pass': bool(condition), 'detail': detail})
        print(('PASS ' if condition else 'FAIL ') + name, flush=True)
        if not condition:
            raise AssertionError(f'{name}: {detail}')

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    with tempfile.TemporaryDirectory(prefix='muse-static-root-') as temp:
        serve = Path(temp)
        (serve / 'Notion').symlink_to(root, target_is_directory=True)
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(serve)))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_address[1]}'
        url = origin + '/Notion/editorial-studio.html'
        report['url'] = url
        try:
            with sync_playwright() as api:
                browser = api.chromium.launch(executable_path=args.browser_executable, headless=True)
                for kind, width, height, embed in [('desktop', 1440, 1100, False), ('mobile', 390, 844, False), ('notion-iframe', 320, 640, True), ('large-source', 390, 844, False)]:
                    context = browser.new_context(viewport={'width': 700 if embed else width, 'height': 800 if embed else height},
                                                  accept_downloads=True, has_touch=kind == 'mobile')
                    errors, requests, responses, external = [], [], [], []

                    def guard(route):
                        if route.request.url.startswith(origin + '/'):
                            route.continue_()
                        else:
                            external.append(route.request.url)
                            route.abort()

                    context.route('**/*', guard)
                    context.on('request', lambda request: requests.append({'method': request.method, 'url': request.url}))
                    context.on('response', lambda response: responses.append({'status': response.status, 'url': response.url}))
                    top = context.new_page()
                    top.on('pageerror', lambda error: errors.append(str(error)))

                    def screenshot(name):
                        path = output / f'{kind}-{name}.png'
                        top.screenshot(path=str(path), full_page=True)
                        report['screenshots'].append(str(path))

                    try:
                        if embed:
                            top.goto(origin + '/')
                            top.set_content(f'<body style="margin:0"><iframe title="Notion" src="{url}" style="border:0;width:320px;height:640px"></iframe>')
                            page = top.frames[1]
                            page.wait_for_load_state('networkidle')
                        else:
                            top.goto(url, wait_until='networkidle')
                            page = top
                        page.evaluate('() => window.MuseModel.ready')
                        expect(page.locator('#connection-status')).to_contain_text(re.compile('미연결|미리보기|연결 전|연결 안'))
                        expect(page.locator('#studio-generation-notice')).to_be_visible()
                        expect(page.locator('#studio-generation-notice')).to_contain_text(re.compile('AI|이미지'))
                        check(kind + ' real missing API is reported honestly', any('/api/studio/status' in item['url'] and item['status'] == 404 for item in responses))
                        check(kind + ' layout fits', page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1'))
                        check(kind + ' all source assets load', not any(item['status'] >= 400 and '/api/' not in item['url'] and not item['url'].endswith('/favicon.ico') for item in responses), responses)

                        page.locator('[data-view="model"]').first.click()
                        face_source = fixture('face.png', 4000, 1600, compress=False) if kind == 'large-source' else fixture('face.png')
                        if kind == 'large-source':
                            check(kind + ' source really exceeds the former upload limit', len(face_source['buffer']) > 15 * 1024 * 1024)
                        page.locator('#model-photos-upload').set_input_files(face_source)
                        expect(page.locator('.model-photo-card')).to_have_count(1, timeout=15000)
                        page.locator('#model-next-button').click()
                        expect(page.locator('#model-next-status')).to_contain_text('전신')
                        check(kind + ' next step explains a missing body without duplicating the face', page.locator('#model-view').is_visible() and not page.evaluate('window.MuseModel.snapshot().hasBody'))
                        page.locator('#model-photos-upload').set_input_files(fixture('body.png'))
                        expect(page.locator('.model-photo-card')).to_have_count(2)
                        if kind == 'large-source':
                            check(kind + ' large image is normalized to the supported edge', page.locator('.model-photo-card img').first.evaluate('(image) => image.naturalWidth <= 3072 && image.naturalHeight <= 3072'))
                        page.locator('#model-view .flow-steps [data-view="board"]').click()
                        expect(page.locator('#board-view')).to_be_visible()
                        check(kind + ' natural upper next-step click transfers the original model anchors', page.evaluate('window.EditorialStudio.snapshot().hasFace && window.EditorialStudio.snapshot().hasBody'))
                        page.locator('[data-view="model"]').first.click()
                        expected_photo_count = 2
                        if kind == 'desktop':
                            # Delay image decoding only, with no mocked API or image
                            # result. This exposes navigation/clear/import contention.
                            saved_profile = page.evaluate('window.MuseModel.snapshot().profile')
                            saved_sources = page.locator('.model-photo-card img').evaluate_all('(images) => images.map(image => image.src)')
                            page.evaluate('''() => {
                              const original = window.MuseImages;
                              window.__originalMuseImages = original;
                              window.MuseImages = {...original, read: async (...args) => {
                                await new Promise(resolve => {window.__releaseContendedImage = resolve;});
                                return original.read(...args);
                              }};
                            }''')
                            page.locator('#model-photos-upload').set_input_files(fixture('delayed-support-fixture.png'))
                            page.wait_for_function('() => window.MuseModel.snapshot().uploadingPhotos && typeof window.__releaseContendedImage === "function"')
                            page.locator('.tool-rail [data-view="board"]').click()
                            check('desktop pending image read cannot navigate past unfinished model sources', page.locator('#model-view').is_visible())
                            check('desktop clear and import stay disabled during an image read', all(page.locator(selector).is_disabled() for selector in ['#model-clear', '#model-kit-import-button', '#model-kit-import']))
                            check('desktop contended upload preserves existing photographs and profile', page.locator('.model-photo-card').count() == 2 and page.evaluate('window.MuseModel.snapshot().profile') == saved_profile and page.locator('.model-photo-card img').evaluate_all('(images) => images.map(image => image.src)') == saved_sources)
                            page.evaluate('() => window.__releaseContendedImage()')
                            page.wait_for_function('() => !window.MuseModel.snapshot().uploadingPhotos && window.MuseModel.snapshot().photoCount === 3')
                            page.evaluate('() => {window.MuseImages = window.__originalMuseImages;}')
                            page.locator('#model-next-button').click()
                            expect(page.locator('#board-view')).to_be_visible()
                            check('desktop completed image read enables next step with real model anchors', page.evaluate('window.EditorialStudio.snapshot().hasFace && window.EditorialStudio.snapshot().hasBody && window.EditorialStudio.snapshot().modelId === window.MuseModel.snapshot().profile.id'))
                            page.locator('[data-view="model"]').first.click()
                            expected_photo_count = 3
                        page.locator('#model-sheet-generate').click()
                        expect(page.locator('#model-dev-prompt')).to_be_visible()
                        model_prompt = page.locator('#model-dev-prompt').input_value()
                        check(kind + ' primary model action prepares actual prompt locally', 'PRIORITY ORDER' in model_prompt and 'authoritative' in model_prompt)
                        check(kind + ' preparing a prompt does not invent a model sheet', not page.evaluate('window.MuseModel.snapshot().hasSheet'))
                        screenshot('after-model-prompt')
                        with top.expect_download() as downloaded:
                            page.locator('#model-dev-export').click()
                        pack = json.loads(Path(downloaded.value.path()).read_text())
                        source_pack = pack.get('manifest', pack)
                        by_id = {item['id']: item for item in source_pack['inputs']}
                        ordered = [by_id[key] for key in source_pack['shots'][0]['inputIds']]
                        check(kind + ' model pack preserves ordered original anchors', source_pack['billable'] is False and [item['role'] for item in ordered[:2]] == ['face', 'body'] and len(ordered) == expected_photo_count)
                        check(kind + ' model pack contains the visible exact prompt', source_pack['shots'][0]['prompt'] == model_prompt)
                        if kind == 'large-source':
                            check(kind + ' normalized source fits the working-copy budget', len(ordered[0]['dataUrl']) <= 2 * 1024 * 1024 * 4 / 3 + 100)
                        page.locator('#model-dialog-close').click()
                        with top.expect_download() as downloaded:
                            page.locator('#model-board-export').click()
                        check(kind + ' original-photo board saves as a real PNG', Path(downloaded.value.path()).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))

                        page.locator('#model-sheet-import').set_input_files(fixture('external-sheet-fixture.png', 300, 200))
                        expect(page.locator('#model-manual-import-confirm')).to_be_disabled()
                        page.locator('#model-manual-confirm').check()
                        page.locator('#model-manual-import-confirm').click()
                        check(kind + ' imported model sheet starts unapproved', page.evaluate('window.MuseModel.snapshot().sheetOrigin') == 'manual' and not page.evaluate('window.MuseModel.snapshot().approved'))
                        page.locator('#model-sheet-approve').click()
                        expect(page.locator('#board-view')).to_be_visible()
                        check(kind + ' explicit sheet approval transfers original identity', page.evaluate('window.EditorialStudio.snapshot().sheetApproved'))
                        page.evaluate('() => window.MuseModel.flush()')
                        page.locator('#reference-upload').set_input_files(fixture('mood-1.png'))
                        page.wait_for_function('() => window.EditorialStudio.snapshot().referenceCount === 1')
                        page.locator('[data-ratio="4:5"]').click()
                        page.locator('#generate-button').click()
                        expect(page.locator('#studio-dev-prompt')).to_be_visible()
                        expect(page.locator('#studio-dev-shot option')).to_have_count(10)
                        first_prompt = page.locator('#studio-dev-prompt').input_value()
                        page.locator('#studio-dev-shot').select_option('9')
                        tenth_prompt = page.locator('#studio-dev-prompt').input_value()
                        check(kind + ' primary editorial action prepares ten different directions', first_prompt != tenth_prompt)
                        page.locator('#dialog-close').click()
                        page.locator('#reference-upload').set_input_files([fixture('mood-2.png'), fixture('mood-3.png')])
                        page.wait_for_function('() => window.EditorialStudio.snapshot().referenceCount === 3')
                        page.locator('#generate-button').click()
                        expect(page.locator('#studio-dev-shot option')).to_have_count(30)
                        with top.expect_download() as downloaded:
                            page.locator('#studio-dev-export').click()
                        editorial = json.loads(Path(downloaded.value.path()).read_text())
                        inputs = {item['id']: item for item in editorial['inputs']}
                        check(kind + ' three references produce thirty local prompt records', editorial['billable'] is False and len(editorial['shots']) == 30)
                        for group in range(3):
                            shots = editorial['shots'][group * 10:(group + 1) * 10]
                            reference_ids = []
                            for shot in shots:
                                actual = [inputs[key] for key in shot['inputIds']]
                                check(kind + f' shot {group * 10 + len(reference_ids) + 1} source order', [item['role'] for item in actual[:4]] == ['face', 'body', 'identity-sheet', 'reference'])
                                reference_ids.append(actual[3]['id'])
                            check(kind + f' reference group {group + 1} remains distinct', len(set(reference_ids)) == 1 and (group == 0 or reference_ids[0] != prior_reference))
                            prior_reference = reference_ids[0]
                        page.locator('#dialog-close').click()
                        page.locator('#studio-manual-import').set_input_files([fixture('external-a.png'), fixture('external-b.png')])
                        expect(page.locator('#studio-manual-import-confirm')).to_be_disabled()
                        page.locator('#studio-manual-confirm').check()
                        page.locator('#studio-manual-import-confirm').click()
                        expect(page.locator('#results-grid .result-image img')).to_have_count(2)
                        expect(page.locator('#results-grid .result-card')).to_have_count(30)
                        expect(page.locator('#results-grid')).to_contain_text('외부 생성 · 수동 검증')
                        check(kind + ' only imported fixtures are shown as completed results', page.locator('#results-grid .is-complete').count() == 2)
                        with top.expect_download() as downloaded:
                            page.locator('#results-grid .is-complete [data-action="download-shot"]').first.click()
                        check(kind + ' imported result downloads as a real JPEG', Path(downloaded.value.path()).read_bytes().startswith(b'\xff\xd8'))
                        page.locator('#results-grid .is-complete [data-action="favorite-shot"]').first.click()
                        page.locator('[data-results-filter="favorites"]').click()
                        expect(page.locator('#results-grid .result-image img')).to_have_count(1)
                        check(kind + ' result favorites filter acts on imported pictures', True)
                        screenshot('after-editorial-results')
                        if embed:
                            page.goto(url, wait_until='networkidle')
                        else:
                            page.reload(wait_until='networkidle')
                        page.evaluate('() => window.MuseModel.ready')
                        check(kind + ' original identity and approved sheet survive re-entry', page.evaluate('(expected) => window.MuseModel.snapshot().photoCount === expected && window.MuseModel.snapshot().approved && window.EditorialStudio.snapshot().sheetApproved', expected_photo_count))
                        check(kind + ' no POST to any API while completing the static workflow', not any(item['method'] != 'GET' for item in requests), requests)
                        check(kind + ' no external network or JavaScript exceptions', not external and not errors, {'external': external, 'errors': errors})
                    except Exception as error:
                        report['checks'].append({'name': kind + ' execution completes', 'pass': False, 'detail': str(error), 'traceback': traceback.format_exc()})
                        screenshot('failure')
                    finally:
                        report['errors'].extend(errors)
                        report['requests'].extend(requests)
                        context.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
    report['checks'].append({'name': 'source files unchanged by browser tests', 'pass': before == fingerprint()})
    report.update({'finished_at': datetime.now(timezone.utc).isoformat(),
                   'passed': all(item['pass'] for item in report['checks']),
                   'checks_passed': sum(item['pass'] for item in report['checks']),
                   'checks_failed': sum(not item['pass'] for item in report['checks'])})
    path = output / 'report.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"{report['checks_passed']} checks passed; {report['checks_failed']} failed. Report: {path}", flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
