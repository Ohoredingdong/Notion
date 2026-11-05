import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import http from 'node:http';
import { createStudioServer } from './server.mjs';

// Only synthetic fixture credentials and an in-memory provider are used here.
const password = 'fixture-owner-password-for-tests';
const apiKey = 'fixture-provider-value-not-an-api-key';
const image = { name: 'fixture.png', dataUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aY6sAAAAASUVORK5CYII=' };
const payload = () => ({ identity: { face: image, body: image }, references: [{ ...image, id: 'ref' }], shots: Array.from({ length: 10 }, (_, i) => ({ id: `shot-${i}`, referenceId: 'ref', pose: 'test pose' })) });
async function start(t, options = {}) {
  const server = createStudioServer({ production: false, authPassword: password, apiKey, ...options });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
  return `http://127.0.0.1:${server.address().port}`;
}
async function login(base, production = false) {
  const response = await fetch(base + '/api/studio/session', { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: production ? base.replace('http:', 'https:') : base }, body: JSON.stringify({ password }) });
  assert.equal(response.status, 200); return response.headers.get('set-cookie').split(';')[0];
}
async function wait(base, id, cookie) {
  for (let i = 0; i < 200; i++) {
    const response = await fetch(`${base}/api/studio/jobs/${id}`, { headers: { Cookie: cookie } });
    assert.equal(response.status, 200); const job = await response.json();
    if (['completed', 'cancelled'].includes(job.status)) return job;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  throw new Error('Synthetic job did not finish');
}

test('production refuses missing credentials and disabled request limits', () => {
  assert.throws(() => createStudioServer({ production: true, apiKey: '', authPassword: password }), /STUDIO_IMAGE_API_KEY/);
  assert.throws(() => createStudioServer({ production: true, apiKey, authPassword: 'short' }), /STUDIO_ACCESS_PASSWORD/);
  assert.throws(() => createStudioServer({ production: true, apiKey, authPassword: password, dailyImageLimit: 0 }), /STUDIO_DAILY_IMAGE_LIMIT/);
});

test('public health is sanitized while status, generation and job access require a session', async t => {
  let calls = 0;
  const base = await start(t, { production: true, fetchImpl: async () => { calls++; throw new Error('Real network forbidden'); } });
  const health = await fetch(base + '/healthz'); assert.equal(health.status, 200); assert.deepEqual(await health.json(), { ok: true });
  for (const [path, method] of [['/api/studio/status', 'GET'], ['/api/studio/generate', 'POST'], ['/api/studio/model-sheet', 'POST'], ['/api/studio/preview', 'POST'], ['/api/studio/jobs/00000000-0000-0000-0000-000000000000', 'GET'], ['/api/studio/jobs/00000000-0000-0000-0000-000000000000', 'DELETE']]) {
    const response = await fetch(base + path, { method }); assert.equal(response.status, 401, path);
    const body = await response.text(); assert.match(body, /authentication_required/); assert.ok(!body.includes(apiKey) && !body.includes(password));
  }
  assert.equal(calls, 0);
});

test('production serves only MUSE public assets and issues secure owner sessions', async t => {
  const base = await start(t, { production: true });
  for (const path of ['/', '/editorial-studio.html', '/assets/editorial-service.js', '/assets/editorial-prompt-core.js', '/assets/editorial-studio/FONT-LICENSE.txt']) assert.equal((await fetch(base + path)).status, 200, path);
  for (const path of ['/README.md', '/stock-value-radar.html', '/services/editorial-studio/server.mjs', '/assets/stock-radar-clean-bridge.js', '/render.yaml', '/.git/config']) assert.equal((await fetch(base + path)).status, 404, path);
  const cookie = await login(base, true); assert.match(cookie, /^__Host-muse_session=/);
  const status = await fetch(base + '/api/studio/status', { headers: { Cookie: cookie } }); assert.equal(status.status, 200);
  const body = await status.json(); assert.equal(body.authRequired, true); assert.equal(body.authenticated, true); assert.equal(body.configured, true);
  assert.equal(body.usage.limit, 50); assert.equal(body.usage.persistent, false);
  assert.ok(!JSON.stringify(body).includes(apiKey) && !JSON.stringify(body).includes(password));
});

test('owner login, ten-shot provider routing, quota rejection and logout work together', async t => {
  let calls = 0;
  const base = await start(t, { dailyImageLimit: 10, fetchImpl: async (url, options) => {
    calls++; assert.equal(url, 'https://api.openai.com/v1/images/edits');
    assert.equal(options.headers.Authorization, `Bearer ${apiKey}`);
    assert.equal(options.body.getAll('image[]').length, 3);
    assert.equal(options.body.get('quality'), 'high');
    return { ok: true, json: async () => ({ data: [{ b64_json: image.dataUrl.split(',')[1] }] }) };
  } });
  const cookie = await login(base);
  const response = await fetch(base + '/api/studio/generate', { method: 'POST', headers: { Cookie: cookie, Origin: base, 'Content-Type': 'application/json' }, body: JSON.stringify(payload()) });
  assert.equal(response.status, 202); const { jobId } = await response.json();
  const job = await wait(base, jobId, cookie); assert.equal(calls, 10); assert.equal(job.total, 10); assert.equal(job.completed, 10);
  const rejected = await fetch(base + '/api/studio/generate', { method: 'POST', headers: { Cookie: cookie, Origin: base, 'Content-Type': 'application/json' }, body: JSON.stringify(payload()) });
  assert.equal(rejected.status, 429); assert.equal((await rejected.json()).error, 'daily_image_limit'); assert.equal(calls, 10);
  const status = await (await fetch(base + '/api/studio/status', { headers: { Cookie: cookie } })).json(); assert.equal(status.usage.requestedImages, 10); assert.equal(status.usage.remaining, 0);
  const out = await fetch(base + '/api/studio/session', { method: 'DELETE', headers: { Cookie: cookie, Origin: base } }); assert.equal(out.status, 200);
  assert.equal((await fetch(`${base}/api/studio/jobs/${jobId}`, { headers: { Cookie: cookie } })).status, 401);
});

test('invalid submissions and unauthenticated attempts never reserve provider requests', async t => {
  let calls = 0; const base = await start(t, { dailyImageLimit: 10, fetchImpl: async () => { calls++; throw new Error('Forbidden'); } });
  const cookie = await login(base);
  const response = await fetch(base + '/api/studio/generate', { method: 'POST', headers: { Cookie: cookie, Origin: base, 'Content-Type': 'application/json' }, body: '{}' }); assert.equal(response.status, 400);
  const status = await (await fetch(base + '/api/studio/status', { headers: { Cookie: cookie } })).json(); assert.equal(status.usage.requestedImages, 0); assert.equal(calls, 0);
});

test('concurrent partially received submissions cannot bypass the two-job bound', async t => {
  const base = await start(t, { dailyImageLimit: 100, fetchImpl: async (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(Object.assign(new Error('Test cleanup'), { name: 'AbortError' })), { once: true });
  }) });
  const cookie = await login(base), body = JSON.stringify(payload());
  const clients = Array.from({ length: 4 }, () => {
    let resolve, reject;
    const result = new Promise((yes, no) => { resolve = yes; reject = no; });
    const request = http.request(base + '/api/studio/generate', { method: 'POST', headers: { Cookie: cookie, Origin: base, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } }, response => {
      response.resume(); response.on('end', () => resolve(response.statusCode));
    });
    request.on('error', reject); request.write(body.slice(0, -1));
    return { request, result };
  });
  // Real slow HTTP bodies hold all requests across the server's read await.
  await new Promise(resolve => setTimeout(resolve, 30));
  for (const client of clients) client.request.end(body.slice(-1));
  const statuses = await Promise.all(clients.map(client => client.result));
  assert.equal(statuses.filter(status => status === 202).length, 2, JSON.stringify(statuses));
  assert.equal(statuses.filter(status => status === 429).length, 2, JSON.stringify(statuses));
  const status = await (await fetch(base + '/api/studio/status', { headers: { Cookie: cookie } })).json();
  assert.equal(status.usage.requestedImages, 20);
});
