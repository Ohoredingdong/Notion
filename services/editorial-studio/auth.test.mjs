import assert from 'node:assert/strict';
import http from 'node:http';
import test from 'node:test';
import { createStudioAuth } from './auth.mjs';

const PASSWORD = 'dummy-test-password-never-a-real-secret';

async function fixture(t, options = {}) {
  const auth = createStudioAuth({ password: PASSWORD, ...options });
  const server = http.createServer(async (req, res) => {
    if (await auth.handle(req, res, new URL(req.url, 'http://localhost'))) return;
    const allowed = auth.authorized(req);
    res.writeHead(allowed ? 200 : 401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ allowed }));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); });
  const base = `http://127.0.0.1:${server.address().port}`;
  const login = (password = PASSWORD, headers = {}) => fetch(base + '/api/studio/session', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Origin: base, ...headers }, body: JSON.stringify({ password })
  });
  return { auth, base, login };
}
function cookie(response) { return response.headers.get('set-cookie').split(';')[0]; }

test('private API stays denied until same-origin password login; credentials are not returned', async t => {
  const f = await fixture(t);
  assert.equal((await fetch(f.base + '/api/studio/generate')).status, 401);
  assert.deepEqual(await (await fetch(f.base + '/api/studio/session')).json(), { authenticated: false, authRequired: true });
  const wrong = await f.login('not-the-password'); assert.equal(wrong.status, 401); assert.equal(wrong.headers.get('set-cookie'), null);
  const response = await f.login(); assert.equal(response.status, 200);
  const body = await response.text(); assert.equal(body.includes(PASSWORD), false); assert.deepEqual(JSON.parse(body), { authenticated: true, authRequired: true });
  assert.equal(response.headers.get('cache-control'), 'no-store');
  const session = cookie(response);
  assert.match(session, /^muse_session=[A-Za-z0-9_-]{43}$/);
  assert.match(response.headers.get('set-cookie'), /HttpOnly; SameSite=Strict/);
  assert.match(response.headers.get('set-cookie'), /Path=\//);
  assert.equal((await fetch(f.base + '/api/studio/generate', { headers: { Cookie: session } })).status, 200);
  assert.deepEqual(await (await fetch(f.base + '/api/studio/session', { headers: { Cookie: session } })).json(), { authenticated: true, authRequired: true });
});

test('forged, malformed, oversized and duplicate session cookies fail closed', async t => {
  const f = await fixture(t), valid = cookie(await f.login());
  for (const value of [
    'muse_session=' + 'a'.repeat(43),
    'muse_session=short',
    'muse_session=%2f' + 'a'.repeat(43),
    valid + '; ' + valid,
    valid + '; unrelated=' + 'a'.repeat(8200)
  ]) assert.equal((await fetch(f.base + '/api/studio/jobs/private-id', { headers: { Cookie: value } })).status, 401);
});

test('logout revokes the server session and expires its cookie', async t => {
  const f = await fixture(t), session = cookie(await f.login());
  const response = await fetch(f.base + '/api/studio/session', { method: 'DELETE', headers: { Cookie: session, Origin: f.base } });
  assert.equal(response.status, 200); assert.match(response.headers.get('set-cookie'), /Max-Age=0/);
  assert.equal((await fetch(f.base + '/api/studio/jobs/any', { headers: { Cookie: session } })).status, 401);
});

test('sessions expire and older sessions are evicted at the configured bound', async t => {
  let clock = 1000;
  const f = await fixture(t, { now: () => clock, sessionTtlMs: 1000, maxSessions: 2 });
  const first = cookie(await f.login()), second = cookie(await f.login()), third = cookie(await f.login());
  assert.notEqual(first, second); assert.notEqual(second, third);
  assert.equal((await fetch(f.base + '/protected', { headers: { Cookie: first } })).status, 401);
  assert.equal((await fetch(f.base + '/protected', { headers: { Cookie: second } })).status, 200);
  clock += 1000;
  assert.equal((await fetch(f.base + '/protected', { headers: { Cookie: third } })).status, 401);
});

test('login rotates the supplied session and invalidates the previous token', async t => {
  const f = await fixture(t), old = cookie(await f.login());
  const current = cookie(await f.login(PASSWORD, { Cookie: old }));
  assert.notEqual(current, old);
  assert.equal((await fetch(f.base + '/protected', { headers: { Cookie: old } })).status, 401);
  assert.equal((await fetch(f.base + '/protected', { headers: { Cookie: current } })).status, 200);
});

test('mutation requires the exact browser origin and rejects forged forwarding headers', async t => {
  const f = await fixture(t);
  assert.equal((await f.login(PASSWORD, { Origin: 'https://unrelated.example' })).status, 403);
  assert.equal((await f.login(PASSWORD, { Origin: f.base + '/path' })).status, 403);
  assert.equal((await f.login(PASSWORD, { Origin: f.base, 'Sec-Fetch-Site': 'cross-site' })).status, 403);
  assert.equal((await f.login(PASSWORD, { Origin: 'https://forwarded.example', 'X-Forwarded-Host': 'forwarded.example', 'X-Forwarded-Proto': 'https' })).status, 403);
  const missing = await fetch(f.base + '/api/studio/session', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: PASSWORD }) });
  assert.equal(missing.status, 403);
  assert.equal((await fetch(f.base + '/api/studio/session', { headers: { 'Sec-Fetch-Site': 'cross-site' } })).status, 403);
});

test('production sets a host-only secure cookie and accepts only HTTPS origin', async t => {
  const f = await fixture(t, { production: true });
  assert.equal((await f.login()).status, 403);
  const response = await f.login(PASSWORD, { Origin: f.base.replace('http:', 'https:') });
  assert.equal(response.status, 200);
  assert.match(response.headers.get('set-cookie'), /^__Host-muse_session=/);
  assert.match(response.headers.get('set-cookie'), /; Secure$/);
  assert.equal(response.headers.get('set-cookie').includes('Domain='), false);
  assert.throws(() => createStudioAuth({ production: true }), /16자/);
  assert.throws(() => createStudioAuth({ production: true, password: 'short' }), /16자/);
});

test('password failures are rate limited even with forged forwarding IP and expire', async t => {
  let clock = 1000;
  const f = await fixture(t, { now: () => clock, maxFailures: 2, failureWindowMs: 1000 });
  assert.equal((await f.login('wrong', { 'X-Forwarded-For': '1.1.1.1' })).status, 401);
  assert.equal((await f.login('wrong', { 'X-Forwarded-For': '2.2.2.2' })).status, 401);
  const blocked = await f.login(); assert.equal(blocked.status, 429); assert.ok(Number(blocked.headers.get('retry-after')) > 0);
  clock += 1000;
  assert.equal((await f.login()).status, 200);
});

test('login rejects non-JSON, malformed and oversized bodies without authorizing', async t => {
  const f = await fixture(t, { maxFailures: 20 });
  for (const [body, type, status] of [
    ['password=' + PASSWORD, 'text/plain', 415], ['{', 'application/json', 400],
    ['[]', 'application/json', 400], [JSON.stringify({ password: 12 }), 'application/json', 400],
    [JSON.stringify({ password: 'a'.repeat(5000) }), 'application/json', 413]
  ]) {
    const response = await fetch(f.base + '/api/studio/session', { method: 'POST', headers: { Origin: f.base, 'Content-Type': type }, body });
    assert.equal(response.status, status); assert.equal(response.headers.get('set-cookie'), null);
  }
  assert.equal((await fetch(f.base + '/protected')).status, 401);
  assert.equal((await f.login()).status, 200);
});

test('parallel password attempts reserve the failure bound before reading their bodies', async t => {
  const f = await fixture(t, { maxFailures: 2 });
  const responses = await Promise.all(Array.from({ length: 8 }, () => f.login('wrong')));
  assert.equal(responses.filter(response => response.status === 401).length, 2);
  assert.equal(responses.filter(response => response.status === 429).length, 6);
  assert.equal((await fetch(f.base + '/protected')).status, 401);
});

test('disabled local development auth preserves API behavior without manufacturing cookies', async t => {
  const f = await fixture(t, { password: '' });
  assert.equal(f.auth.required, false);
  assert.equal((await fetch(f.base + '/protected')).status, 200);
  const response = await f.login();
  assert.deepEqual(await response.json(), { authenticated: true, authRequired: false });
  assert.equal(response.headers.get('set-cookie'), null);
  const unsupported = await fetch(f.base + '/api/studio/session', { method: 'PUT' });
  assert.equal(unsupported.status, 405); assert.equal(unsupported.headers.get('allow'), 'GET, POST, DELETE');
});
