import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';

const MAX_LOGIN_BYTES = 4096;
const SESSION_PATH = '/api/studio/session';
const hash = value => createHash('sha256').update(value).digest();
const sessionHash = value => hash(value).toString('hex');

export function createStudioAuth({ password = '', production = false, sessionTtlMs = 12 * 60 * 60 * 1000,
  now = Date.now, maxSessions = 128, maxFailures = 8, failureWindowMs = 15 * 60 * 1000, maxClients = 2048 } = {}) {
  if (typeof password !== 'string' || Buffer.byteLength(password) > 1024) throw new Error('STUDIO_ACCESS_PASSWORD 형식을 확인해주세요.');
  if (production && password.length < 16) throw new Error('운영 서버의 STUDIO_ACCESS_PASSWORD는 16자 이상이어야 합니다.');
  for (const [name, value] of Object.entries({ sessionTtlMs, maxSessions, maxFailures, failureWindowMs, maxClients })) {
    if (!Number.isSafeInteger(value) || value <= 0) throw new Error(`${name} must be a positive integer`);
  }
  const required = password.length > 0;
  const expectedHash = hash(password);
  const cookieName = production ? '__Host-muse_session' : 'muse_session';
  const sessions = new Map(), failures = new Map();

  function prune() {
    const time = now();
    for (const [key, session] of sessions) if (session.expiresAt <= time) sessions.delete(key);
    for (const [key, failure] of failures) if (failure.resetAt <= time) failures.delete(key);
  }
  function token(req) {
    const header = req.headers.cookie;
    if (typeof header !== 'string' || header.length > 8192) return null;
    const values = header.split(';').map(value => value.trim()).filter(value => value.startsWith(cookieName + '='));
    // Ambiguous duplicate cookies are not accepted as session credentials.
    if (values.length !== 1) return null;
    const value = values[0].slice(cookieName.length + 1);
    return /^[A-Za-z0-9_-]{43}$/.test(value) ? value : null;
  }
  function authorized(req) {
    if (!required) return true;
    prune();
    const value = token(req);
    return value !== null && sessions.has(sessionHash(value));
  }
  function sameOrigin(req) {
    const host = req.headers.host;
    if (typeof host !== 'string' || /[\s/\\]/.test(host)) return false;
    const scheme = production || req.socket.encrypted ? 'https' : 'http';
    return req.headers.origin === `${scheme}://${host}` && req.headers['sec-fetch-site'] !== 'cross-site';
  }
  function cookie(value, maxAge, req) {
    return `${cookieName}=${value}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAge}${production || req.socket.encrypted ? '; Secure' : ''}`;
  }
  function json(res, status, data, headers = {}) {
    res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff', ...headers });
    res.end(JSON.stringify(data));
  }
  function client(req) { return req.socket.remoteAddress || 'unknown'; }
  function limited(req) {
    prune();
    const failure = failures.get(client(req));
    return (failure && failure.count >= maxFailures) || (!failure && failures.size >= maxClients);
  }
  function reserveAttempt(req) {
    const key = client(req), current = failures.get(key);
    if (current) current.count++;
    else if (failures.size < maxClients) failures.set(key, { count: 1, resetAt: now() + failureWindowMs });
  }
  async function credentials(req) {
    if (!/^application\/json(?:\s*;|$)/i.test(req.headers['content-type'] || '')) {
      req.resume(); throw Object.assign(new Error('JSON 요청이 필요합니다.'), { status: 415 });
    }
    const length = Number(req.headers['content-length']);
    if (Number.isFinite(length) && length > MAX_LOGIN_BYTES) {
      req.resume(); throw Object.assign(new Error('로그인 요청이 너무 큽니다.'), { status: 413 });
    }
    let size = 0;
    const chunks = [];
    const body = await new Promise((resolve, reject) => {
      const finish = error => {
        clearTimeout(timer);
        req.removeListener('data', onData); req.removeListener('end', onEnd); req.removeListener('error', onError); req.removeListener('aborted', onAbort);
        if (error) { req.resume(); reject(error); } else resolve(Buffer.concat(chunks).toString('utf8'));
      };
      const onData = chunk => {
        size += chunk.length;
        if (size > MAX_LOGIN_BYTES) finish(Object.assign(new Error('로그인 요청이 너무 큽니다.'), { status: 413 }));
        else chunks.push(chunk);
      };
      const onEnd = () => finish();
      const onError = () => finish(Object.assign(new Error('로그인 요청을 읽지 못했습니다.'), { status: 400 }));
      const onAbort = () => finish(Object.assign(new Error('로그인 요청이 중단되었습니다.'), { status: 400 }));
      const timer = setTimeout(() => finish(Object.assign(new Error('로그인 요청 시간이 초과됐습니다.'), { status: 408 })), 5000);
      req.on('data', onData); req.on('end', onEnd); req.on('error', onError); req.on('aborted', onAbort);
    });
    try {
      const data = JSON.parse(body);
      if (!data || typeof data !== 'object' || Array.isArray(data) || typeof data.password !== 'string' || Buffer.byteLength(data.password) > 1024) throw new Error();
      return data.password;
    } catch { throw Object.assign(new Error('비밀번호 형식이 올바르지 않습니다.'), { status: 400 }); }
  }
  async function handle(req, res, url) {
    if (url.pathname !== SESSION_PATH) return false;
    if (req.headers['sec-fetch-site'] === 'cross-site') {
      json(res, 403, { code: 'cross_origin', message: '같은 웹페이지에서 로그인해주세요.' }); return true;
    }
    if (req.method === 'GET') {
      json(res, 200, { authenticated: authorized(req), authRequired: required }); return true;
    }
    if (!['POST', 'DELETE'].includes(req.method)) {
      json(res, 405, { message: '지원하지 않는 요청입니다.' }, { Allow: 'GET, POST, DELETE' }); return true;
    }
    if (!sameOrigin(req)) {
      req.resume(); json(res, 403, { code: 'cross_origin', message: '같은 웹페이지에서 로그인해주세요.' }); return true;
    }
    if (req.method === 'DELETE') {
      const value = token(req);
      if (value) sessions.delete(sessionHash(value));
      json(res, 200, { authenticated: !required, authRequired: required }, { 'Set-Cookie': cookie('', 0, req) }); return true;
    }
    if (!required) {
      req.resume(); json(res, 200, { authenticated: true, authRequired: false }); return true;
    }
    if (limited(req)) {
      req.resume(); json(res, 429, { code: 'login_rate_limited', message: '로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.' }, { 'Retry-After': String(Math.ceil(failureWindowMs / 1000)) }); return true;
    }
    // Reserve before awaiting the body so parallel attempts cannot bypass the bound.
    reserveAttempt(req);
    let candidate;
    try { candidate = await credentials(req); }
    catch (error) { json(res, error.status || 400, { message: error.message }); return true; }
    if (!timingSafeEqual(hash(candidate), expectedHash)) {
      json(res, 401, { code: 'invalid_credentials', message: '비밀번호가 올바르지 않습니다.' }); return true;
    }
    failures.delete(client(req)); prune();
    while (sessions.size >= maxSessions) sessions.delete(sessions.keys().next().value);
    const previous = token(req);
    if (previous) sessions.delete(sessionHash(previous));
    const value = randomBytes(32).toString('base64url');
    sessions.set(sessionHash(value), { expiresAt: now() + sessionTtlMs });
    json(res, 200, { authenticated: true, authRequired: true }, { 'Set-Cookie': cookie(value, Math.max(1, Math.floor(sessionTtlMs / 1000)), req) });
    return true;
  }
  return Object.freeze({ handle, authorized, required, cookieName });
}
