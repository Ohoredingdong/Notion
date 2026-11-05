import http from 'node:http';
import path from 'node:path';
import { readFile, realpath, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { randomUUID, createHash } from 'node:crypto';
import promptCore from '../../assets/editorial-prompt-core.js';
import { createStudioAuth } from './auth.mjs';

const DEFAULT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const MAX_OUTPUT_BASE64 = 12 * 1024 * 1024;
const MAX_JOB_OUTPUT = 96 * 1024 * 1024;
const MAX_RETAINED_OUTPUT = 128 * 1024 * 1024;
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.woff2': 'font/woff2' };
const sharedPrompts = promptCore.createCore({
  randomUUID,
  decodeBase64: encoded => Buffer.from(encoded, 'base64'),
  encodeBase64: bytes => Buffer.from(bytes).toString('base64'),
  sha256: value => createHash('sha256').update(value).digest('hex')
});
const { MAX_BODY, MAX_SHEET_BODY } = sharedPrompts.limits;
const { RequestError, validatePayload, validateSheetPayload, buildPrompt, buildSheetPrompt, providerSize, providerInputs, buildPreview } = sharedPrompts;
export { validatePayload, validateSheetPayload, buildPrompt, buildSheetPrompt, buildPreview };

async function readJson(req, maxBytes = MAX_BODY) {
  if (!String(req.headers['content-type'] || '').startsWith('application/json')) throw new RequestError(415, 'JSON 요청이 필요합니다.');
  if (Number(req.headers['content-length']) > maxBytes) throw new RequestError(413, '사진 용량이 너무 큽니다. 이미지를 줄여 다시 시도해 주세요.');
  let size = 0; const chunks = [];
  for await (const chunk of req) { size += chunk.length; if (size > maxBytes) throw new RequestError(413, `최대 업로드 용량은 ${maxBytes / 1024 / 1024}MB입니다.`); chunks.push(chunk); }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { throw new RequestError(400, 'JSON 요청을 읽을 수 없습니다.'); }
}

export function createStudioServer({ root = DEFAULT_ROOT, apiKey = process.env.STUDIO_IMAGE_API_KEY || process.env.OPENAI_API_KEY || '', model = process.env.OPENAI_IMAGE_MODEL || 'gpt-image-1', fetchImpl = fetch, retentionMs = 30 * 60 * 1000, production = process.env.NODE_ENV === 'production', authPassword = process.env.STUDIO_ACCESS_PASSWORD || '', dailyImageLimit = Number(process.env.STUDIO_DAILY_IMAGE_LIMIT || (production ? 50 : 0)) } = {}) {
  if (production && (!apiKey || authPassword.length < 16)) throw new Error('실제 서버에는 STUDIO_IMAGE_API_KEY와 16자 이상의 STUDIO_ACCESS_PASSWORD를 설정해주세요.');
  if (!Number.isSafeInteger(dailyImageLimit) || dailyImageLimit < 0 || dailyImageLimit > 10000 || (production && !dailyImageLimit)) throw new Error('STUDIO_DAILY_IMAGE_LIMIT는 1~10000 사이의 정수로 설정해주세요.');
  const auth = createStudioAuth({ password: authPassword, production });
  let usageDay = '', requestedImages = 0;
  function usage() {
    const day = new Date().toISOString().slice(0, 10);
    if (day !== usageDay) { usageDay = day; requestedImages = 0; }
    return { day: usageDay, requestedImages, limit: dailyImageLimit || null, remaining: dailyImageLimit ? Math.max(0, dailyImageLimit - requestedImages) : null, persistent: false };
  }
  const jobs = new Map(); const rates = new Map(); const queue = []; let active = 0;
  const json = (res, status, value) => { res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' }); res.end(JSON.stringify(value)); };
  const view = job => ({ id: job.id, kind: job.kind, status: job.status, total: job.shots.length, completed: job.shots.filter(s => s.status === 'completed').length, failed: job.shots.filter(s => s.status === 'failed').length, shots: job.shots.map(({ controller, ...shot }) => shot) });
  function prune() {
    for (const [id, job] of jobs) if (job.finishedAt && Date.now() - job.finishedAt > retentionMs) jobs.delete(id);
    const retained = [...jobs.values()].filter(job => job.finishedAt).sort((a, b) => a.finishedAt - b.finishedAt);
    let total = retained.reduce((sum, job) => sum + (job.outputBytes || 0), 0);
    while (retained.length > 4 || total > MAX_RETAINED_OUTPUT) {
      const oldest = retained.shift(); jobs.delete(oldest.id); total -= oldest.outputBytes || 0;
    }
  }
  function capacity(key) {
    const recent = (rates.get(key) || []).filter(time => Date.now() - time < 60_000);
    if (recent.length >= 6) throw new RequestError(429, '잠시 후 다시 요청해 주세요.');
    if ([...jobs.values()].filter(job => !job.finishedAt).length >= 2) throw new RequestError(429, '생성 중인 작업이 있습니다. 완료 후 다시 시도해 주세요.');
    return recent;
  }
  function settle(job) {
    if (!job.shots.some(s => s.status === 'queued' || s.status === 'running')) { job.status = job.cancelled ? 'cancelled' : 'completed'; job.finishedAt = Date.now(); job.payload = null; prune(); }
  }
  async function generate(job, shot) {
    shot.status = 'running'; job.status = 'running';
    const payload = job.payload;
    const reference = payload.kind === 'model-sheet' ? null : payload.references.find(ref => ref.id === shot.referenceId);
    const controller = new AbortController(); shot.controller = controller;
    const timeout = setTimeout(() => controller.abort(), 240_000);
    try {
      const form = new FormData();
      form.set('model', model); form.set('prompt', payload.kind === 'model-sheet' ? buildSheetPrompt(payload) : buildPrompt(payload, payload.shots.find(s => s.id === shot.id)));
      form.set('n', '1'); form.set('quality', 'high'); form.set('input_fidelity', 'high'); form.set('output_format', 'jpeg');
      form.set('size', providerSize(payload));
      const inputs = providerInputs(payload, reference);
      for (const image of inputs) form.append('image[]', new Blob([image.bytes], { type: image.mime }), image.mime === 'image/jpeg' ? 'input.jpg' : image.mime === 'image/png' ? 'input.png' : 'input.webp');
      const response = await fetchImpl('https://api.openai.com/v1/images/edits', { method: 'POST', headers: { Authorization: `Bearer ${apiKey}` }, body: form, signal: controller.signal });
      const result = await response.json();
      if (!response.ok) throw new Error(response.status === 401 ? '이미지 API 인증을 확인해 주세요.' : response.status === 429 ? '이미지 API 사용량 또는 요청 한도를 확인해 주세요.' : response.status === 403 ? '이미지 모델 접근 권한을 확인해 주세요.' : `이미지 API 요청 실패 (${response.status}). 설정 또는 콘텐츠 조건을 확인해 주세요.`);
      const encoded = result.data?.[0]?.b64_json;
      if (typeof encoded !== 'string' || encoded.length < 20 || encoded.length > MAX_OUTPUT_BASE64 || !/^[A-Za-z0-9+/]+={0,2}$/.test(encoded)) throw new Error('이미지 API가 유효한 이미지 결과를 반환하지 않았습니다.');
      if (!job.cancelled) {
        if ((job.outputBytes || 0) + encoded.length > MAX_JOB_OUTPUT) throw new Error('이미지 API 결과 보관 용량을 초과했습니다. 완료된 컷을 내려받고 새 작업으로 나누어 주세요.');
        job.outputBytes = (job.outputBytes || 0) + encoded.length;
        shot.dataUrl = `data:image/jpeg;base64,${encoded}`; shot.status = 'completed';
      }
    } catch (error) {
      if (!job.cancelled) { shot.status = 'failed'; shot.error = error.name === 'AbortError' ? '생성 시간이 초과되었습니다. 다시 시도해 주세요.' : error.message.startsWith('이미지 API') ? error.message : '생성 서버 연결에 실패했습니다. 네트워크와 API 설정을 확인해 주세요.'; }
    } finally { clearTimeout(timeout); delete shot.controller; if (job.cancelled) shot.status = 'cancelled'; settle(job); }
  }
  function drain() {
    while (active < 2 && queue.length) {
      const { job, shot } = queue.shift(); if (job.cancelled) continue;
      active++; generate(job, shot).finally(() => { active--; drain(); });
    }
  }
  const server = http.createServer(async (req, res) => {
    try {
      prune();
      const url = new URL(req.url, 'http://localhost');
      if (url.pathname === '/healthz' && ['GET', 'HEAD'].includes(req.method)) {
        if (req.method === 'HEAD') { res.writeHead(200, { 'Cache-Control': 'no-store' }); res.end(); return; }
        return json(res, 200, { ok: true });
      }
      if (await auth.handle(req, res, url)) return;
      if (url.pathname.startsWith('/api/studio/')) {
        if (req.headers.origin && req.headers.origin !== `http://${req.headers.host}` && req.headers.origin !== `https://${req.headers.host}`) throw new RequestError(403, '같은 웹페이지에서만 요청할 수 있습니다.');
        if (req.headers['sec-fetch-site'] === 'cross-site') throw new RequestError(403, '다른 사이트에서 보낸 요청입니다.');
        if (!auth.authorized(req)) return json(res, 401, { error: 'authentication_required', authRequired: true, configured: false, message: '스튜디오 비밀번호로 로그인한 뒤 생성할 수 있습니다.' });
        if (req.method === 'GET' && url.pathname === '/api/studio/status') return json(res, 200, { configured: Boolean(apiKey), authenticated: true, authRequired: auth.required, model, maxReferences: 3, shotsPerReference: 10, modelSheet: true, maxModelPhotos: 10, developmentPreview: true, usage: usage() });
        if (req.method === 'POST' && url.pathname === '/api/studio/preview') {
          const data = await readJson(req, MAX_SHEET_BODY);
          if (data?.kind === 'editorial' && Buffer.byteLength(JSON.stringify(data)) > MAX_BODY) throw new RequestError(413, '화보 검증 요청의 최대 업로드 용량은 32MB입니다.');
          return json(res, 200, buildPreview(data?.kind, data?.payload, model));
        }
        if (req.method === 'POST' && ['/api/studio/generate', '/api/studio/model-sheet'].includes(url.pathname)) {
          if (!apiKey) throw new RequestError(503, '실제 이미지 생성은 서버의 STUDIO_IMAGE_API_KEY 연결 후 사용할 수 있습니다. 사진 업로드와 구성 보드는 지금 사용할 수 있습니다.', 'not_configured');
          const key = req.socket.remoteAddress;
          capacity(key);
          const isSheet = url.pathname === '/api/studio/model-sheet';
          const payload = isSheet ? validateSheetPayload(await readJson(req, MAX_SHEET_BODY)) : validatePayload(await readJson(req));
          // Recheck after reading the body; concurrent submissions may have
          // reserved work while this request was awaiting input.
          const recent = capacity(key);
          const available = usage();
          if (dailyImageLimit && payload.shots.length > available.remaining) throw new RequestError(429, `오늘 요청할 수 있는 이미지가 ${available.remaining}장 남았습니다. 서버의 요청 한도를 확인해주세요.`, 'daily_image_limit');
          requestedImages += payload.shots.length;
          recent.push(Date.now()); rates.set(key, recent);
          const job = { id: randomUUID(), kind: payload.kind, status: 'queued', payload, shots: payload.shots.map(shot => ({ id: shot.id, referenceId: shot.referenceId, status: 'queued' })), cancelled: false };
          jobs.set(job.id, job); queue.push(...job.shots.map(shot => ({ job, shot }))); json(res, 202, { jobId: job.id }); drain(); return;
        }
        const match = /^\/api\/studio\/jobs\/([a-f0-9-]+)$/.exec(url.pathname);
        if (match && ['GET', 'DELETE'].includes(req.method)) {
          const job = jobs.get(match[1]); if (!job) throw new RequestError(404, '작업이 없거나 보관 시간이 지났습니다.');
          if (req.method === 'DELETE' && !job.finishedAt) {
            job.cancelled = true;
            for (const shot of job.shots) { shot.controller?.abort(); if (shot.status === 'queued') shot.status = 'cancelled'; }
            settle(job);
          }
          return json(res, 200, view(job));
        }
        throw new RequestError(404, 'API 경로를 찾을 수 없습니다.');
      }
      if (!['GET', 'HEAD'].includes(req.method)) throw new RequestError(405, '지원하지 않는 요청입니다.');
      let decoded; try { decoded = decodeURIComponent(url.pathname); } catch { throw new RequestError(400, '잘못된 경로입니다.'); }
      if (decoded.split('/').some(part => part.startsWith('.')) || decoded.includes('\0')) throw new RequestError(404, '파일을 찾을 수 없습니다.');
      if (production && decoded !== '/' && decoded !== '/editorial-studio.html' && !/^\/assets\/editorial-[^/]+\.(?:js|css)$/.test(decoded) && !/^\/assets\/editorial-studio\/[^/]+\.(?:jpg|jpeg|png|webp|ttf|txt)$/.test(decoded)) throw new RequestError(404, '파일을 찾을 수 없습니다.');
      const rootPath = await realpath(root);
      let file = path.resolve(rootPath, `.${decoded === '/' ? '/editorial-studio.html' : decoded}`);
      file = await realpath(file).catch(() => { throw new RequestError(404, '파일을 찾을 수 없습니다.'); });
      if (!file.startsWith(rootPath + path.sep) || !(await stat(file)).isFile()) throw new RequestError(404, '파일을 찾을 수 없습니다.');
      const body = await readFile(file);
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-cache' }); res.end(req.method === 'HEAD' ? undefined : body);
    } catch (error) { if (!res.headersSent) json(res, error.status || 500, { error: error.code || 'server_error', message: error.status ? error.message : '서버 오류가 발생했습니다.' }); else res.end(); }
  });
  const cleanup = setInterval(prune, Math.min(60_000, Math.max(50, retentionMs))).unref();
  server.on('close', () => { clearInterval(cleanup); for (const job of jobs.values()) { job.cancelled = true; for (const shot of job.shots) shot.controller?.abort(); } });
  return server;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 8787); const host = process.env.HOST || '127.0.0.1';
  createStudioServer().listen(port, host, () => console.log(`Editorial Studio listening on ${host}:${port}; image API ${process.env.STUDIO_IMAGE_API_KEY || process.env.OPENAI_API_KEY ? 'configured' : 'not configured'}`));
}
