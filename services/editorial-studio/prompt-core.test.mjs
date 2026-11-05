import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash, webcrypto } from 'node:crypto';
import vm from 'node:vm';
import promptCore from '../../assets/editorial-prompt-core.js';
import { buildPreview as serverPreview } from './server.mjs';

// Execute the actual browser bundle without CommonJS, Buffer, fetch, or a server.
const bundle = await readFile(new URL('../../assets/editorial-prompt-core.js', import.meta.url), 'utf8');
let networkCalls = 0;
const browser = vm.createContext({
  crypto: { subtle: webcrypto.subtle, randomUUID: () => 'deterministic-browser-id' },
  TextEncoder, Uint8Array, atob, btoa,
  fetch() { networkCalls++; throw new Error('Local preparation must not use a network'); }
});
vm.runInContext(bundle, browser);
const browserPreview = (...args) => browser.MusePrompts.buildPreview(...args);
const plain = value => JSON.parse(JSON.stringify(value));
const withoutSheetShotIds = manifest => ({ ...plain(manifest), shots: plain(manifest.shots).map(({ id, ...shot }) => shot) });
const image = { name: 'fixture.png', dataUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aY6sAAAAASUVORK5CYII=' };
const sheet = () => ({
  profile: { id: 'same-model', revision: 7, name: '기준 모델', hair: 'Keep the hair', notes: '같은 얼굴', bodyNotes: 'Keep the build' },
  photos: [
    { ...image, id: 'face-original', role: 'face', primary: true },
    { ...image, id: 'body-original', role: 'body' },
    { ...image, name: 'side.png', id: 'side-original', role: 'side' },
    { ...image, name: 'back.png', id: 'back-original', role: 'back' }
  ], expressionCount: 8
});
const editorial = () => ({
  mode: 'wedding', aspectRatio: '4:5', brief: 'Soft daylight',
  identity: { face: image, body: image },
  identityProfile: { id: 'same-model', revision: 7, sheetApproved: true, notes: '같은 얼굴', hair: 'Keep the hair' },
  identitySheet: { ...image, name: 'approved.png' },
  supportingPhotos: [{ ...image, role: 'side', name: 'side.png' }],
  references: [{ ...image, id: 'ref-a' }, { ...image, id: 'ref-b', name: 'mood-b.png' }],
  shots: ['ref-a', 'ref-b'].flatMap(referenceId => Array.from({ length: 10 }, (_, i) => ({
    id: `${referenceId}-shot-${i}`, referenceId, pose: `pose ${i}`, gaze: i % 2 ? 'camera' : 'away', framing: 'portrait'
  }))),
  layers: [{ label: '원본', x: 35, y: 50, scale: 30, rotation: 4 }]
});

test('server preview remains synchronous while the browser uses Web Crypto asynchronously', async () => {
  const source = sheet();
  const node = serverPreview('model-sheet', source);
  const pending = browserPreview('model-sheet', source);
  assert.equal(typeof node.then, 'undefined');
  assert.equal(typeof pending.then, 'function');
  const local = await pending;
  assert.deepEqual(withoutSheetShotIds(local), withoutSheetShotIds(node));
  assert.equal(networkCalls, 0);
  assert.equal(local.billable, false);
  assert.equal(local.jobId, undefined);
  assert.equal(local.shots[0].dataUrl, undefined);
});

test('browser and server preserve all prompts, source hashes, roles and reference order for twenty shots', async () => {
  const source = editorial();
  const node = serverPreview('editorial', source);
  const local = await browserPreview('editorial', source);
  assert.deepEqual(plain(local), plain(node));
  assert.equal(local.shots.length, 20);
  assert.equal(local.inputs.length, 6);
  for (const shot of local.shots) {
    const ordered = shot.inputIds.map(id => local.inputs.find(input => input.id === id));
    assert.deepEqual(plain(ordered.map(input => input.role)), ['face', 'body', 'identity-sheet', 'reference', 'support-side']);
    assert.equal(ordered[3].name, shot.referenceId === 'ref-a' ? 'fixture.png' : 'mood-b.png');
    assert.equal(shot.size, '1024x1536');
    assert.match(shot.prompt, /image 4 is mood inspiration ONLY/);
  }
  assert.equal(networkCalls, 0);
});

test('identical file bytes retain their separate authoritative face, body and mood roles', async () => {
  const local = await browserPreview('editorial', editorial());
  assert.equal(new Set(local.inputs.map(input => input.sha256)).size, 1);
  assert.equal(new Set(local.inputs.map(input => input.id)).size, 6);
  const digest = createHash('sha256').update(Buffer.from(image.dataUrl.split(',')[1], 'base64')).digest('hex');
  assert.equal(local.inputs[0].sha256, digest);
  assert.notEqual(local.inputs[0].id, local.inputs[1].id);
});

test('fingerprints are stable and change with source bytes, profile revision and direction', async () => {
  const source = editorial();
  const baseline = await browserPreview('editorial', source);
  assert.equal((await browserPreview('editorial', source)).sourceFingerprint, baseline.sourceFingerprint);
  const changedDirection = structuredClone(source); changedDirection.shots[0].gaze = 'a different direction';
  assert.notEqual((await browserPreview('editorial', changedDirection)).sourceFingerprint, baseline.sourceFingerprint);
  const changedRevision = structuredClone(source); changedRevision.identityProfile.revision++;
  assert.notEqual((await browserPreview('editorial', changedRevision)).sourceFingerprint, baseline.sourceFingerprint);
  const changedBytes = structuredClone(source);
  const original = Buffer.from(image.dataUrl.split(',')[1], 'base64'); original[original.length - 1] ^= 1;
  changedBytes.identity.face = { ...image, dataUrl: 'data:image/png;base64,' + original.toString('base64') };
  assert.notEqual((await browserPreview('editorial', changedBytes)).sourceFingerprint, baseline.sourceFingerprint);
});

test('browser applies the same profile normalization as the real provider', async () => {
  const source = sheet();
  source.profile.name = '이름'.repeat(100); source.profile.notes = 'n'.repeat(5000); source.profile.hair = 'h'.repeat(1000);
  source.profile.eyes = 'e'.repeat(1000); source.profile.skin = 's'.repeat(1000); source.profile.bodyNotes = 'b'.repeat(2000);
  const local = await browserPreview('model-sheet', source);
  const node = serverPreview('model-sheet', source);
  assert.equal(local.sourceFingerprint, node.sourceFingerprint);
  assert.equal(local.shots[0].prompt, node.shots[0].prompt);
  assert.ok(!local.shots[0].prompt.includes('n'.repeat(3001)));
  assert.ok(!local.shots[0].prompt.includes('b'.repeat(1001)));
});

test('browser and server reject invalid kinds, MIME, magic bytes, base64 and model evidence', () => {
  const cases = [
    ['other', sheet()],
    ['model-sheet', { ...sheet(), photos: sheet().photos.map(photo => ({ ...photo, primary: false })) }],
    ['model-sheet', { ...sheet(), expressionCount: 9 }],
    ['model-sheet', { ...sheet(), photos: sheet().photos.map(photo => ({ ...photo, role: 'face' })) }],
    ['editorial', { ...editorial(), identitySheet: undefined }],
    ['editorial', { ...editorial(), identityProfile: { id: 'same-model', sheetApproved: false } }]
  ];
  for (const dataUrl of ['data:image/svg+xml;base64,PHN2Zz4=', 'data:image/png;base64,bm90IGFuIGltYWdl', image.dataUrl + '=', 'data:image/jpeg;base64,' + image.dataUrl.split(',')[1]]) {
    const invalid = editorial(); invalid.identity.face = { dataUrl }; cases.push(['editorial', invalid]);
  }
  for (const [kind, source] of cases) {
    let serverError; let browserError;
    try { serverPreview(kind, source); } catch (error) { serverError = error; }
    try { browserPreview(kind, source); } catch (error) { browserError = error; }
    assert.ok(serverError && browserError, `Both environments must reject ${kind}`);
    assert.equal(browserError.status, serverError.status);
    assert.equal(browserError.message, serverError.message);
  }
  assert.equal(networkCalls, 0);
});

test('local preparation enforces the same per-image and total request size limits', () => {
  const tooLarge = editorial();
  const bytes = Buffer.alloc(6 * 1024 * 1024 + 1); Buffer.from(image.dataUrl.split(',')[1], 'base64').copy(bytes);
  tooLarge.identity.face = { dataUrl: 'data:image/png;base64,' + bytes.toString('base64') };
  for (const prepare of [serverPreview, browserPreview]) {
    assert.throws(() => prepare('editorial', tooLarge), error => error.status === 400 && /6MB/.test(error.message));
    assert.throws(() => prepare('editorial', { ...editorial(), ignoredOversizedField: 'x'.repeat(32 * 1024 * 1024) }), error => error.status === 413);
    assert.throws(() => prepare('model-sheet', { ...sheet(), ignoredOversizedField: 'x'.repeat(64 * 1024 * 1024) }), error => error.status === 413);
  }
});

test('asynchronous digest failure rejects instead of fabricating a fingerprint or result', async () => {
  const core = promptCore.createCore({
    randomUUID: () => 'fixed-id', decodeBase64: value => Buffer.from(value, 'base64'),
    encodeBase64: value => Buffer.from(value).toString('base64'),
    sha256: async () => { throw new Error('digest unavailable'); }
  });
  await assert.rejects(core.buildPreview('model-sheet', sheet()), /digest unavailable/);
});

test('sizes reflect portrait, square and landscape provider inputs without changing source roles', async () => {
  for (const [ratio, size] of [['1:1', '1024x1024'], ['4:5', '1024x1536'], ['16:9', '1536x1024']]) {
    const source = editorial(); source.aspectRatio = ratio;
    const local = await browserPreview('editorial', source);
    assert.equal(local.shots[0].size, size);
    assert.equal(local.sourceFingerprint, serverPreview('editorial', source).sourceFingerprint);
  }
});
