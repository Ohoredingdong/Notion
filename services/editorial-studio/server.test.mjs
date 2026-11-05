import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createStudioServer, validatePayload, buildPrompt, validateSheetPayload, buildSheetPrompt } from './server.mjs';

const image = { name: 'fixture.png', dataUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aY6sAAAAASUVORK5CYII=' };
const request = () => ({ mode: 'wedding', aspectRatio: '4:5', brief: 'Soft daylight', identity: { face: image, body: image }, references: [{ ...image, id: 'ref-a' }], shots: Array.from({ length: 10 }, (_, i) => ({ id: `shot-${i}`, referenceId: 'ref-a', pose: `pose ${i}` })) });
async function start(t, options) {
  const server = createStudioServer(options); server.listen(0, '127.0.0.1'); await once(server, 'listening');
  t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
  return `http://127.0.0.1:${server.address().port}`;
}
const post = (base, value, extra = {}) => fetch(base + '/api/studio/generate', { method: 'POST', headers: { 'Content-Type': 'application/json', ...extra }, body: JSON.stringify(value) });
async function waitForJob(base, id, predicate) {
  for (let i = 0; i < 100; i++) { const value = await (await fetch(`${base}/api/studio/jobs/${id}`)).json(); if (predicate(value)) return value; await new Promise(resolve => setTimeout(resolve, 10)); }
  throw new Error('Job did not reach expected state');
}

test('validates image signatures, reference counts and distinct shot IDs', () => {
  const data = request(); assert.equal(validatePayload(data).shots.length, 10);
  data.identity.face = { dataUrl: 'data:image/png;base64,bm90IGFuIGltYWdl' }; assert.throws(() => validatePayload(data), /유효한 이미지/);
  const duplicate = request(); duplicate.shots[1].id = duplicate.shots[0].id; assert.throws(() => validatePayload(duplicate), /컷 ID/);
  const missing = request(); missing.shots.pop(); assert.throws(() => validatePayload(missing), /10개의 컷/);
});

test('prompt keeps identity/body roles separate from mood and original wedding styling', () => {
  const data = validatePayload(request()); const prompt = buildPrompt(data, data.shots[0]);
  assert.match(prompt, /face\/identity anchor/); assert.match(prompt, /body\/proportion anchor/);
  assert.match(prompt, /mood inspiration ONLY/); assert.match(prompt, /NEW clothing/); assert.match(prompt, /wedding fashion/);
});

test('unconfigured API reports truthfully without credential values', async t => {
  const base = await start(t, { apiKey: '' });
  const status = await (await fetch(base + '/api/studio/status')).json(); assert.equal(status.configured, false);
  const response = await post(base, request()); assert.equal(response.status, 503); assert.equal((await response.json()).error, 'not_configured');
});

test('same-origin checks reject cross-origin billing requests', async t => {
  const base = await start(t, { apiKey: 'test-only' });
  const response = await post(base, request(), { Origin: 'https://unrelated.example' }); assert.equal(response.status, 403);
});

test('asynchronous job sends identity images, limits concurrency and returns 10 distinct results', async t => {
  let active = 0; let highest = 0; let calls = 0;
  const base = await start(t, { apiKey: 'test-only', fetchImpl: async (url, options) => {
    assert.equal(url, 'https://api.openai.com/v1/images/edits');
    assert.equal(options.body.getAll('image[]').length, 3); assert.match(options.body.get('prompt'), /SHOT DIRECTION: pose/);
    active++; highest = Math.max(highest, active); const index = ++calls;
    await new Promise(resolve => setTimeout(resolve, 12)); active--;
    return { ok: true, json: async () => ({ data: [{ b64_json: Buffer.from(`mock-output-image-number-${index}`).toString('base64') }] }) };
  } });
  const response = await post(base, request()); assert.equal(response.status, 202);
  const { jobId } = await response.json(); const result = await waitForJob(base, jobId, job => job.status === 'completed');
  assert.equal(result.completed, 10); assert.equal(result.failed, 0); assert.equal(calls, 10); assert.equal(highest, 2);
  assert.equal(new Set(result.shots.map(shot => shot.dataUrl)).size, 10);
  assert.ok(result.shots.every(shot => !('controller' in shot)));
});

test('provider errors are preserved as failures without fake output or credential leaks', async t => {
  const base = await start(t, { apiKey: 'private-test-key', fetchImpl: async () => ({ ok: false, status: 401, json: async () => ({ error: { message: 'private-test-key' } }) }) });
  const { jobId } = await (await post(base, request())).json(); const result = await waitForJob(base, jobId, job => job.status === 'completed');
  assert.equal(result.failed, 10); assert.equal(result.completed, 0); assert.ok(result.shots.every(shot => !shot.dataUrl));
  assert.ok(!JSON.stringify(result).includes('private-test-key')); assert.match(result.shots[0].error, /인증/);
});

test('cancellation aborts active requests and prevents queued calls', async t => {
  let calls = 0;
  const base = await start(t, { apiKey: 'test-only', fetchImpl: (_url, { signal }) => {
    calls++; return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(Object.assign(new Error('abort'), { name: 'AbortError' })), { once: true }));
  } });
  const { jobId } = await (await post(base, request())).json();
  await waitForJob(base, jobId, job => job.shots.filter(shot => shot.status === 'running').length === 2);
  assert.equal((await fetch(`${base}/api/studio/jobs/${jobId}`, { method: 'DELETE' })).status, 200);
  const result = await waitForJob(base, jobId, job => job.status === 'cancelled');
  assert.equal(calls, 2); assert.equal(result.completed, 0); assert.ok(result.shots.every(shot => shot.status === 'cancelled'));
});

test('static server refuses dotfiles and encoded traversal', async t => {
  const base = await start(t, { apiKey: '' });
  assert.equal((await fetch(base + '/.git/config')).status, 404);
  assert.equal((await fetch(base + '/%2e%2e%2f%2e%2e%2fetc/passwd')).status, 404);
  const response = await fetch(base + '/README.md'); assert.equal(response.status, 200);
});

test('completed uploads/results expire and oldest jobs are evicted after retention cap', async t => {
  const fetchImpl = async () => ({ ok: true, json: async () => ({ data: [{ b64_json: Buffer.from('mock-output-retention-check').toString('base64') }] }) });
  const base = await start(t, { apiKey: 'test-only', fetchImpl });
  const ids = [];
  for (let i = 0; i < 5; i++) {
    const { jobId } = await (await post(base, request())).json(); ids.push(jobId);
    await waitForJob(base, jobId, job => job.status === 'completed');
  }
  assert.equal((await fetch(`${base}/api/studio/jobs/${ids[0]}`)).status, 404);
  assert.equal((await fetch(`${base}/api/studio/jobs/${ids[4]}`)).status, 200);
  const expiring = await start(t, { apiKey: 'test-only', fetchImpl, retentionMs: 30 });
  const { jobId } = await (await post(expiring, request())).json();
  await waitForJob(expiring, jobId, job => job.status === 'completed');
  await new Promise(resolve => setTimeout(resolve, 90));
  assert.equal((await fetch(`${expiring}/api/studio/jobs/${jobId}`)).status, 404);
});


const sheetRequest = () => ({
  profile: { id: 'model-01', name: 'Same model', hair: 'unchanged short dark hair', bodyNotes: 'preserve shoulder width' },
  photos: [
    { ...image, id: 'face-primary', role: 'face', primary: true },
    { ...image, id: 'body-primary', role: 'body' },
    { ...image, id: 'side', role: 'side' },
    { ...image, id: 'back', role: 'back' }
  ], expressionCount: 8
});
const postSheet = (base, value, extra = {}) => fetch(base + '/api/studio/model-sheet', { method: 'POST', headers: { 'Content-Type': 'application/json', ...extra }, body: JSON.stringify(value) });

test('model sheet validates one authoritative frontal face, body evidence and 6–8 expressions', () => {
  const payload = validateSheetPayload(sheetRequest());
  assert.equal(payload.kind, 'model-sheet'); assert.equal(payload.shots.length, 1); assert.equal(payload.expressionCount, 8);
  assert.deepEqual(payload.supportingPhotos.map(photo => photo.role), ['side', 'back']);
  const noPrimary = sheetRequest(); noPrimary.photos[0].primary = false; assert.throws(() => validateSheetPayload(noPrimary), /기준 얼굴/);
  const noBody = sheetRequest(); noBody.photos[1].role = 'extra'; assert.throws(() => validateSheetPayload(noBody), /전신/);
  const doublePrimary = sheetRequest(); doublePrimary.photos[2].role = 'face'; doublePrimary.photos[2].primary = true; assert.throws(() => validateSheetPayload(doublePrimary), /기준 얼굴/);
  const tooMany = sheetRequest(); tooMany.photos = Array.from({ length: 11 }, (_, i) => ({ ...tooMany.photos[i % 4], id: String(i) })); assert.throws(() => validateSheetPayload(tooMany), /2~10개/);
  assert.throws(() => validateSheetPayload({ ...sheetRequest(), expressionCount: 9 }), /6~8개/);
});

test('model sheet prompt prioritizes structure, aligned three views and honest inferred angles', () => {
  const payload = validateSheetPayload(sheetRequest()); const prompt = buildSheetPrompt(payload);
  assert.match(prompt, /PRIORITY ORDER: \(1\) facial identity consistency/);
  assert.match(prompt, /FRONT \/ true PROFILE \/ BACK/);
  assert.match(prompt, /8 evenly sized face-expression panels/);
  assert.match(prompt, /eye, lips and natural skin texture/);
  assert.match(prompt, /inferred reconstruction, not a measured or verified unseen view/);
  assert.match(prompt, /not a guarantee of exact identity reproduction/);
  assert.match(prompt, /image 3: side evidence; image 4: back evidence/);
});

test('single model-sheet job uses original face/body first and makes exactly one landscape edit', async t => {
  let calls = 0;
  const base = await start(t, { apiKey: 'test-only', fetchImpl: async (_url, { body }) => {
    calls++;
    assert.equal(body.get('size'), '1536x1024'); assert.equal(body.get('n'), '1'); assert.equal(body.getAll('image[]').length, 4);
    assert.match(body.get('prompt'), /ONE photorealistic MODEL IDENTITY REFERENCE SHEET/);
    assert.match(body.get('prompt'), /Image 2 is the full-body/);
    return { ok: true, json: async () => ({ data: [{ b64_json: Buffer.from('mock-model-reference-sheet-image').toString('base64') }] }) };
  } });
  const response = await postSheet(base, sheetRequest()); assert.equal(response.status, 202);
  const { jobId } = await response.json(); const job = await waitForJob(base, jobId, value => value.status === 'completed');
  assert.equal(calls, 1); assert.equal(job.total, 1); assert.equal(job.kind, 'model-sheet'); assert.equal(job.completed, 1);
  assert.equal(job.shots[0].referenceId, 'model-01'); assert.match(job.shots[0].dataUrl, /^data:image\/jpeg;base64,/);
});

test('model sheet endpoint enforces key availability and same-origin before billed work', async t => {
  const unconfigured = await start(t, { apiKey: '' });
  assert.equal((await postSheet(unconfigured, sheetRequest())).status, 503);
  const configured = await start(t, { apiKey: 'test-only' });
  assert.equal((await postSheet(configured, sheetRequest(), { Origin: 'https://other.example' })).status, 403);
});

test('approved identity sheets and support originals are sent to every editorial shot with stable roles', async t => {
  const data = request(); data.identityProfile = { id: 'model-01', name: 'Same model', sheetApproved: true, hair: 'unchanged hair' };
  data.identitySheet = image; data.supportingPhotos = [{ ...image, role: 'side' }];
  const payload = validatePayload(data); const prompt = buildPrompt(payload, payload.shots[0]);
  assert.match(prompt, /Image 3 is the USER-REVIEWED APPROVED identity sheet/);
  assert.match(prompt, /image 4 is mood inspiration ONLY/);
  assert.match(prompt, /image 5: additional side evidence/);
  assert.match(prompt, /Identity consistency has priority/);
  let calls = 0;
  const base = await start(t, { apiKey: 'test-only', fetchImpl: async (_url, { body }) => {
    calls++; assert.equal(body.getAll('image[]').length, 5); assert.match(body.get('prompt'), /image 4 is mood inspiration ONLY/);
    return { ok: true, json: async () => ({ data: [{ b64_json: Buffer.from('mock-new-photograph-with-approved-sheet').toString('base64') }] }) };
  } });
  const response = await post(base, data); assert.equal(response.status, 202);
  const { jobId } = await response.json(); const job = await waitForJob(base, jobId, value => value.status === 'completed');
  assert.equal(calls, 10); assert.equal(job.completed, 10);
  const missing = { ...data, identitySheet: undefined }; assert.throws(() => validatePayload(missing), /기준 시트 이미지/);
  const unapproved = { ...data, identityProfile: { ...data.identityProfile, sheetApproved: false } }; assert.throws(() => validatePayload(unapproved), /검토하고 승인/);
  const tooMany = { ...data, supportingPhotos: Array.from({ length: 9 }, () => image) }; assert.throws(() => validatePayload(tooMany), /최대 8개/);
});

const postPreview = (base, kind, payload, extra = {}) => fetch(base + '/api/studio/preview', {
  method: 'POST', headers: { 'Content-Type': 'application/json', ...extra }, body: JSON.stringify({ kind, payload })
});

test('development previews need no key, call no provider and return real prompt/source manifests only', async t => {
  let providerCalls = 0;
  const base = await start(t, { apiKey: '', fetchImpl: async () => { providerCalls++; throw new Error('Preview must never call the provider'); } });
  const source = sheetRequest(); source.profile.revision = 7;
  const response = await postPreview(base, 'model-sheet', source);
  assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'no-store');
  const preview = await response.json();
  assert.equal(preview.billable, false); assert.equal(preview.kind, 'model-sheet'); assert.equal(preview.requestedQuality, 'high');
  assert.equal(preview.profileId, 'model-01'); assert.equal(preview.profileRevision, 7); assert.match(preview.sourceFingerprint, /^[a-f0-9]{64}$/);
  assert.equal(preview.shots.length, 1); assert.equal(preview.inputs.length, 4); assert.equal(preview.shots[0].size, '1536x1024');
  assert.equal(preview.shots[0].prompt, buildSheetPrompt(validateSheetPayload(source)));
  assert.deepEqual(preview.shots[0].inputIds.map(id => preview.inputs.find(input => input.id === id).role), ['face', 'body', 'support-side', 'support-back']);
  assert.ok(preview.inputs.every(input => input.dataUrl === image.dataUrl && /^[a-f0-9]{64}$/.test(input.sha256)));
  assert.match(preview.instructions, /ChatGPT/); assert.match(preview.instructions, /사용 한도/); assert.match(preview.instructions, /검증된 것은 아닙니다/);
  assert.equal(preview.jobId, undefined); assert.equal(preview.shots[0].dataUrl, undefined); assert.equal(providerCalls, 0);
  const repeated = await (await postPreview(base, 'model-sheet', source)).json();
  assert.equal(repeated.sourceFingerprint, preview.sourceFingerprint);
  source.photos.pop();
  const changed = await (await postPreview(base, 'model-sheet', source)).json();
  assert.notEqual(changed.sourceFingerprint, preview.sourceFingerprint); assert.equal(providerCalls, 0);
});

test('editorial preview deduplicates source files and preserves each reference order and approved identity', async t => {
  let providerCalls = 0;
  const base = await start(t, { apiKey: 'configured-but-not-used', fetchImpl: async () => { providerCalls++; throw new Error('No paid calls'); } });
  const source = request();
  source.identityProfile = { id: 'model-01', revision: 4, sheetApproved: true };
  source.identitySheet = { ...image, name: 'approved.png' };
  source.supportingPhotos = [{ ...image, role: 'side', name: 'side.png' }];
  source.references.push({ ...image, id: 'ref-b', name: 'other-mood.png' });
  source.shots.push(...source.shots.map(shot => ({ ...shot, id: shot.id + '-b', referenceId: 'ref-b' })));
  const response = await postPreview(base, 'editorial', source); assert.equal(response.status, 200);
  const preview = await response.json(), payload = validatePayload(source);
  assert.equal(preview.inputs.length, 6); assert.equal(preview.shots.length, 20); assert.equal(preview.profileRevision, 4);
  assert.equal(preview.shots[0].prompt, buildPrompt(payload, payload.shots[0]));
  assert.equal(preview.shots[10].prompt, buildPrompt(payload, payload.shots[10]));
  const first = preview.shots[0].inputIds.map(id => preview.inputs.find(input => input.id === id));
  const second = preview.shots[10].inputIds.map(id => preview.inputs.find(input => input.id === id));
  assert.deepEqual(first.map(input => input.role), ['face', 'body', 'identity-sheet', 'reference', 'support-side']);
  assert.deepEqual(first.slice(0, 3).map(input => input.id), second.slice(0, 3).map(input => input.id));
  assert.equal(first[3].name, 'fixture.png'); assert.equal(second[3].name, 'other-mood.png'); assert.notEqual(first[3].id, second[3].id);
  assert.equal(first[4].id, second[4].id); assert.equal(preview.shots[0].size, '1024x1536'); assert.equal(providerCalls, 0);
});

test('preview validation rejects invalid images, kinds and cross-origin requests before any provider access', async t => {
  let calls = 0;
  const base = await start(t, { apiKey: '', fetchImpl: async () => { calls++; throw new Error('Unexpected provider access'); } });
  const invalid = sheetRequest(); invalid.photos[0].dataUrl = 'data:image/png;base64,bm90IGFuIGltYWdl';
  assert.equal((await postPreview(base, 'model-sheet', invalid)).status, 400);
  assert.equal((await postPreview(base, 'other', request())).status, 400);
  assert.equal((await postPreview(base, 'editorial', request(), { Origin: 'https://unrelated.example' })).status, 403);
  const missing = request(); missing.identity.body = null;
  assert.equal((await postPreview(base, 'editorial', missing)).status, 400);
  assert.equal(calls, 0);
});

test('preview sources and prompt match the actual provider request for the same source model', async t => {
  let captured = null, calls = 0;
  const base = await start(t, { apiKey: 'mock-only', fetchImpl: async (_url, { body }) => {
    calls++; captured = { prompt: body.get('prompt'), size: body.get('size'), inputs: await Promise.all(body.getAll('image[]').map(blob => blob.arrayBuffer().then(value => Buffer.from(value)))) };
    return { ok: true, json: async () => ({ data: [{ b64_json: Buffer.from('mock-provider-result-image').toString('base64') }] }) };
  } });
  const source = sheetRequest();
  const preview = await (await postPreview(base, 'model-sheet', source)).json(); assert.equal(calls, 0);
  const { jobId } = await (await postSheet(base, source)).json();
  await waitForJob(base, jobId, job => job.status === 'completed');
  assert.equal(calls, 1); assert.equal(captured.prompt, preview.shots[0].prompt); assert.equal(captured.size, preview.shots[0].size);
  const ordered = preview.shots[0].inputIds.map(id => preview.inputs.find(input => input.id === id));
  assert.deepEqual(captured.inputs, ordered.map(input => Buffer.from(input.dataUrl.split(',')[1], 'base64')));
});
