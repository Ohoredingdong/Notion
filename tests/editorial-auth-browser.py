"""Real same-origin login/browser regressions with a mock image provider.

Starts the actual Node server. Passwords and API keys below are test fixtures;
the provider is replaced in memory and no external or billable request is made.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('STUDIO_AUTH_REPORT', '/tmp/notion-muse-live-validation/browser-auth'))
PASSWORD = 'test-only-studio-password-2026'
PROVIDER_KEY = 'test-only-provider-key-never-valid'
CHECKS = []


def fixture(name):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    rows = (b'\0' + bytes((161, 178, 140)) * 90) * 140
    image = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 90, 140, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')
    return {'name': name, 'mimeType': 'image/png', 'buffer': image}


def record(name):
    CHECKS.append(name)
    print('PASS', name, flush=True)


def start_server(temporary, configured=True):
    metrics = Path(temporary) / ('configured.json' if configured else 'no-key.json')
    metrics.write_text('{"calls":0}')
    source = f"""
      import {{ createStudioServer }} from {json.dumps((ROOT / 'services/editorial-studio/server.mjs').as_uri())};
      import {{ writeFileSync }} from 'node:fs';
      let calls = 0;
      const server = createStudioServer({{
        root: {json.dumps(str(ROOT))}, production: false,
        authPassword: {json.dumps(PASSWORD)}, apiKey: {json.dumps(PROVIDER_KEY if configured else '')},
        fetchImpl: async (url, options) => {{
          if (url !== 'https://api.openai.com/v1/images/edits') throw new Error('Unexpected provider destination');
          calls++; writeFileSync({json.dumps(str(metrics))}, JSON.stringify({{calls}}));
          const image = options.body.getAll('image[]')[0];
          const bytes = Buffer.from(await image.arrayBuffer());
          return {{ok:true, json:async()=>({{data:[{{b64_json:bytes.toString('base64')}}]}})}};
        }}
      }});
      server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({{port:server.address().port}})));
      process.on('SIGTERM', () => {{ server.closeAllConnections(); server.close(()=>process.exit(0)); }});
    """
    process = subprocess.Popen(['node', '--input-type=module', '-e', source], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    line = process.stdout.readline()
    if not line:
        raise AssertionError('Server did not start: ' + process.stderr.read())
    return process, f'http://127.0.0.1:{json.loads(line)["port"]}', metrics


def login(page):
    expect(page.locator('#studio-session-dialog')).to_be_visible()
    page.locator('#studio-session-password').fill(PASSWORD)
    page.locator('#studio-session-submit').click()
    expect(page.locator('#studio-session-dialog')).not_to_be_visible()


OUT.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='muse-auth-browser-') as temporary, sync_playwright() as play:
    processes = []
    browser = play.chromium.launch(executable_path=os.environ.get('STUDIO_BROWSER', '/usr/bin/chromium'), headless=True)
    try:
        process, base, metrics = start_server(temporary)
        processes.append(process)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        errors, external = [], []
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else (external.append(route.request.url), route.abort())[-1])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/editorial-studio.html', wait_until='networkidle')
        page.evaluate('() => window.MuseModel.ready')
        expect(page.locator('#studio-session-dialog')).to_be_visible()
        expect(page.locator('#connection-status')).to_contain_text('로그인')
        assert json.loads(metrics.read_text())['calls'] == 0
        record('protected service opens one accessible login dialog without starting generation')

        page.locator('#studio-session-close').click()
        page.locator('#model-photos-upload').set_input_files([fixture('face.png'), fixture('body.png')])
        expect(page.locator('.model-photo-card')).to_have_count(2)
        page.wait_for_function('() => !window.MuseModel.snapshot().uploadingPhotos')
        original = page.evaluate('() => window.MuseModel.snapshot()')
        page.locator('#settings-button').click()
        page.locator('#studio-signin-button').click()
        page.locator('#studio-session-password').fill('wrong-test-password')
        page.locator('#studio-session-submit').click()
        expect(page.locator('#studio-session-message')).to_contain_text('비밀번호')
        expect(page.locator('#studio-session-password')).to_have_value('')
        assert page.evaluate('() => window.MuseModel.snapshot().photoCount') == 2
        record('wrong password remains an explicit error and preserves uploaded model photos')

        login(page)
        expect(page.locator('#connection-status')).to_contain_text('생성 설정')
        assert page.evaluate('() => document.cookie').find('muse_session') == -1
        assert page.evaluate('() => window.MuseModel.snapshot().profile.id') == original['profile']['id']
        assert PROVIDER_KEY not in page.locator('body').inner_text()
        assert PASSWORD not in page.evaluate('() => JSON.stringify({...localStorage})')
        expect(page.locator('#studio-session-password')).to_have_value('')
        record('successful cookie login keeps secrets out of page storage and restores configured state')

        page.locator('#model-next-button').click()
        page.locator('#reference-upload').set_input_files(fixture('mood.png'))
        page.wait_for_function('() => window.EditorialStudio.snapshot().referenceCount === 1')
        page.locator('#generate-button').click()
        expect(page.locator('#confirm-generation')).to_be_visible()
        assert json.loads(metrics.read_text())['calls'] == 0
        page.locator('#confirm-generation').click()
        expect(page.locator('.result-image img')).to_have_count(10, timeout=20000)
        assert json.loads(metrics.read_text())['calls'] == 10
        record('authenticated generation waits for paid-action confirmation and completes 10 mock-provider shots')

        page.locator('#settings-button').click()
        page.locator('#studio-signout-button').click()
        expect(page.locator('#connection-status')).to_contain_text('로그인')
        expect(page.locator('#studio-session-dialog')).not_to_be_visible()
        assert page.evaluate('() => window.MuseModel.snapshot().photoCount') == 2
        page.locator('#settings-button').click()
        page.locator('#studio-signin-button').click()
        login(page)
        expect(page.locator('#connection-status')).to_contain_text('생성 설정')
        assert json.loads(metrics.read_text())['calls'] == 10
        record('logout and relogin preserve local photos and never retry a billable POST')

        context.clear_cookies()
        page.evaluate("async () => { await Promise.all([window.MuseService.request('/api/studio/status'),window.MuseService.request('/api/studio/status')]); }")
        expect(page.locator('#studio-session-dialog')).to_be_visible()
        expect(page.locator('#studio-session-dialog')).to_have_count(1)
        assert page.evaluate('() => window.MuseModel.snapshot().profile.id') == original['profile']['id']
        login(page)
        assert json.loads(metrics.read_text())['calls'] == 10
        refused = page.evaluate("async () => { try { await window.MuseService.request('https://example.invalid/api/studio/generate'); return false; } catch { return true; } }")
        assert refused and not external
        record('expired sessions request one login and cross-origin service requests are refused locally')
        assert not errors, errors
        page.screenshot(path=str(OUT / 'authenticated-studio.png'))
        context.close()

        process, base, metrics = start_server(temporary, configured=False)
        processes.append(process)
        context = browser.new_context(viewport={'width': 390, 'height': 844})
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
        page = context.new_page()
        page.goto(base + '/editorial-studio.html', wait_until='networkidle')
        login(page)
        expect(page.locator('#connection-status')).to_contain_text('미리보기')
        expect(page.locator('#studio-generation-notice')).to_contain_text('생성은 아직 연결되지')
        assert json.loads(metrics.read_text())['calls'] == 0
        page.screenshot(path=str(OUT / 'authenticated-no-provider.png'))
        context.close()
        record('login without a configured provider remains clearly disconnected and produces no fake photograph')
    finally:
        browser.close()
        for process in processes:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.communicate(timeout=5)

report = {'passed': len(CHECKS), 'failed': 0, 'checks': CHECKS, 'provider': 'in-memory mock; zero external/billable calls'}
(OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False), flush=True)
