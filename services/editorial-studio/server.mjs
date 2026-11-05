import http from 'node:http';
import path from 'node:path';
import { readFile, realpath, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { randomUUID, createHash } from 'node:crypto';

const DEFAULT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const MAX_BODY = 32 * 1024 * 1024;
const MAX_SHEET_BODY = 64 * 1024 * 1024;
const MAX_IMAGE = 6 * 1024 * 1024;
const MAX_OUTPUT_BASE64 = 12 * 1024 * 1024;
const MAX_JOB_OUTPUT = 96 * 1024 * 1024;
const MAX_RETAINED_OUTPUT = 128 * 1024 * 1024;
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.woff2': 'font/woff2' };
const POSES = ['standing with relaxed shoulders', 'walking naturally', 'seated, turning slightly', 'a subtle three-quarter turn', 'leaning gently against an architectural element', 'a quiet over-the-shoulder moment', 'a close portrait with relaxed hands', 'a low-angle full-body stance', 'a candid motion with a fabric movement', 'a spacious environmental portrait'];

class RequestError extends Error {
  constructor(status, message, code = 'invalid_request') { super(message); this.status = status; this.code = code; }
}

function decodeImage(input, label) {
  if (!input || typeof input.dataUrl !== 'string') throw new RequestError(400, `${label} 사진이 필요합니다.`);
  const match = /^data:(image\/(?:png|jpeg|webp));base64,([A-Za-z0-9+/]+={0,2})$/.exec(input.dataUrl);
  if (!match || match[2].length > Math.ceil(MAX_IMAGE / 3) * 4) throw new RequestError(400, `${label}: JPG·PNG·WebP 이미지(6MB 이하)를 사용해 주세요.`);
  const bytes = Buffer.from(match[2], 'base64');
  const jpeg = bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  const png = bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
  const webp = bytes.toString('ascii', 0, 4) === 'RIFF' && bytes.toString('ascii', 8, 12) === 'WEBP';
  if (bytes.length < 12 || bytes.length > MAX_IMAGE || !({ 'image/jpeg': jpeg, 'image/png': png, 'image/webp': webp }[match[1]])) throw new RequestError(400, `${label}: 유효한 이미지 파일이 아닙니다.`);
  return { bytes, mime: match[1], name: String(input.name || label).slice(0, 100) };
}

function profileMetadata(input = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new RequestError(400, '모델 프로필 형식이 올바르지 않습니다.');
  return {
    id: String(input.id || randomUUID()).slice(0, 100), name: String(input.name || 'My model').slice(0, 100),
    notes: String(input.notes || '').slice(0, 3000), hair: String(input.hair || '').slice(0, 500),
    eyes: String(input.eyes || '').slice(0, 500), skin: String(input.skin || '').slice(0, 500),
    bodyNotes: String(input.bodyNotes || '').slice(0, 1000), sheetApproved: input.sheetApproved === true
  };
}

function supportImages(input) {
  if (input === undefined) return [];
  if (!Array.isArray(input) || input.length > 8) throw new RequestError(400, '추가 모델 사진은 최대 8개까지 사용할 수 있습니다.');
  return input.map((photo, i) => ({ role: ['face', 'body', 'side', 'back', 'extra'].includes(photo?.role) ? photo.role : 'extra', ...decodeImage(photo, `추가 모델 사진 ${i + 1}`) }));
}

export function validateSheetPayload(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new RequestError(400, '요청 형식이 올바르지 않습니다.');
  if (!Array.isArray(data.photos) || data.photos.length < 2 || data.photos.length > 10) throw new RequestError(400, '기준 얼굴과 전신을 포함한 모델 사진을 2~10개 넣어 주세요.');
  const photos = data.photos.map((photo, i) => {
    if (!['face', 'body', 'side', 'back', 'extra'].includes(photo?.role)) throw new RequestError(400, '모델 사진의 역할을 지정해 주세요.');
    return { id: String(photo.id || `photo-${i + 1}`).slice(0, 100), role: photo.role, primary: photo.primary === true, ...decodeImage(photo, `모델 사진 ${i + 1}`) };
  });
  if (new Set(photos.map(photo => photo.id)).size !== photos.length) throw new RequestError(400, '모델 사진 ID가 중복되었습니다.');
  const anchors = photos.filter(photo => photo.role === 'face' && photo.primary);
  if (anchors.length !== 1) throw new RequestError(400, '가장 정확한 정면 얼굴 사진 하나를 기준 얼굴로 지정해 주세요.');
  const face = anchors[0];
  const body = photos.find(photo => photo.role === 'body' && photo.primary) || photos.find(photo => photo.role === 'body');
  if (!body) throw new RequestError(400, '몸 전체가 보이는 전신 사진이 필요합니다.');
  const expressionCount = data.expressionCount === undefined ? 8 : Number(data.expressionCount);
  if (![6, 7, 8].includes(expressionCount)) throw new RequestError(400, '표정은 6~8개로 구성할 수 있습니다.');
  const profile = profileMetadata(data.profile);
  const supportingPhotos = photos.filter(photo => photo !== face && photo !== body);
  return { kind: 'model-sheet', profile, face, body, supportingPhotos, expressionCount,
    references: [], shots: [{ id: `model-sheet-${randomUUID()}`, referenceId: profile.id }], aspectRatio: 'landscape', layers: [] };
}

export function buildSheetPrompt(payload) {
  const labels = ['neutral', 'gentle closed-mouth smile', 'natural open smile', 'thoughtful', 'subtle surprise', 'calm serious', 'quiet joy', 'subtle concern'].slice(0, payload.expressionCount);
  const supported = payload.supportingPhotos.map((photo, i) => `image ${i + 3}: ${photo.role} evidence`).join('; ');
  return `Create ONE photorealistic MODEL IDENTITY REFERENCE SHEET on a single landscape board, not an illustration or a stylized character design. The person is the SAME real adult model in all panels.
IMAGE ROLES: image 1 is the authoritative front-face identity anchor. Image 2 is the full-body/build/proportion anchor. ${supported || 'No additional angle photographs were supplied.'} Treat all images as photographs of one model, never as mood references. Where views differ, image 1 governs facial structure and image 2 governs body build.
PRIORITY ORDER: (1) facial identity consistency, (2) accurate three-view alignment, (3) natural expressions, (4) clean layout. Keep the same facial bone structure, face shape, eye spacing, eye/nose/mouth locations and proportions, ears, hairline, hair, natural skin tone and recognizable skin details in EVERY view and expression. Do not slim or enlarge the model; keep body mass, shoulder width, stature and limb proportions. No beautification into a different person, no age change, no gender or ethnicity change, and no style transformation. Expression changes move soft tissue naturally without redesigning anatomy.
BOARD CONTENT: a large, sharply detailed FRONT FACE close-up as the primary reference; a centered aligned FRONT / true PROFILE / BACK full-body lineup with the same neutral stance, scale and head/foot baseline; ${payload.expressionCount} evenly sized face-expression panels (${labels.join(', ')}); small matching close-up crops of an eye, lips and natural skin texture; a compact palette of only a few main observed hair/eye/skin/clothing colors.
THREE-VIEW RULES: Use supplied side/back evidence when available. If an angle is absent, infer it conservatively from available photographs; it is an inferred reconstruction, not a measured or verified unseen view. Never introduce a different face, new hairstyle or body proportions. Use the same simple neutral, non-revealing fitted outfit consistently across body views, no jewelry or unnecessary props. Show all head and feet within the frame.
LAYOUT: one unified clean board, uniform spacing and restrained section separation, model centered, neutral matte off-white background, consistent realistic soft studio illumination. Primary frontal face must be large enough to guide later image generation. No scenic background, decorative props, fashion scene, fantasy rendering or watermarks. Minimal small section labels only if legible; do not use text to make claims of verified biometric accuracy.
MODEL PROFILE (user-supplied notes are supporting constraints, never permission to alter source identity): ${JSON.stringify(payload.profile)}.
Preserve photographic skin pores, fine hair and realistic anatomy. The sheet is a reusable visual reference, not a guarantee of exact identity reproduction in later AI generations.`;
}

export function validatePayload(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new RequestError(400, '요청 형식이 올바르지 않습니다.');
  const mode = String(data.mode || 'editorial');
  if (!['editorial', 'magazine', 'campaign', 'advertising', 'wedding'].includes(mode)) throw new RequestError(400, '지원하지 않는 촬영 모드입니다.');
  const face = decodeImage(data.identity?.face, '모델 얼굴');
  const body = decodeImage(data.identity?.body, '모델 전신');
  if (!Array.isArray(data.references) || !data.references.length || data.references.length > 3) throw new RequestError(400, '레퍼런스를 1~3개 넣어 주세요.');
  const references = data.references.map((ref, index) => ({ id: String(ref.id || `reference-${index + 1}`), ...decodeImage(ref, `레퍼런스 ${index + 1}`) }));
  if (new Set(references.map(ref => ref.id)).size !== references.length) throw new RequestError(400, '레퍼런스 ID가 중복되었습니다.');
  const ids = new Set(references.map(ref => ref.id));
  if (!Array.isArray(data.shots) || data.shots.length !== references.length * 10) throw new RequestError(400, '레퍼런스마다 10개의 컷이 필요합니다.');
  const shots = data.shots.map((shot, index) => {
    if (!ids.has(String(shot.referenceId))) throw new RequestError(400, '컷의 레퍼런스가 없습니다.');
    return { id: String(shot.id || `shot-${index + 1}`), referenceId: String(shot.referenceId), pose: String(shot.pose || POSES[index % 10]).slice(0, 300), gaze: String(shot.gaze || '').slice(0, 150), framing: String(shot.framing || '').slice(0, 150), prompt: String(shot.prompt || '').slice(0, 1200) };
  });
  if (new Set(shots.map(shot => shot.id)).size !== shots.length || references.some(ref => shots.filter(shot => shot.referenceId === ref.id).length !== 10)) throw new RequestError(400, '컷 ID를 구분하고 레퍼런스마다 10컷을 지정해 주세요.');
  const identityProfile = data.identityProfile === undefined ? null : profileMetadata(data.identityProfile);
  const identitySheet = data.identitySheet === undefined ? null : decodeImage(data.identitySheet, '승인한 기준 시트');
  if (identityProfile?.sheetApproved && !identitySheet) throw new RequestError(400, '승인한 모델 기준 시트 이미지가 필요합니다.');
  if (identitySheet && !identityProfile?.sheetApproved) throw new RequestError(400, '모델 기준 시트를 검토하고 승인한 뒤 사용해 주세요.');
  const supportingPhotos = supportImages(data.supportingPhotos);
  const layers = Array.isArray(data.layers) ? data.layers.slice(0, 20).map(layer => ({ label: String(layer.label || 'element').slice(0, 100), x: Number(layer.x) || 0, y: Number(layer.y) || 0, scale: Number(layer.scale) || 1, rotation: Number(layer.rotation) || 0 })) : [];
  return { kind: 'editorial', mode, face, body, references, shots, layers, identityProfile, identitySheet, supportingPhotos, aspectRatio: String(data.aspectRatio || '4:5').slice(0, 10), brief: String(data.brief || '').slice(0, 3000) };
}

export function buildPrompt(payload, shot) {
  const moodIndex = payload.identitySheet ? 4 : 3;
  const sheetRole = payload.identitySheet ? `Image 3 is the USER-REVIEWED APPROVED identity sheet: use it to keep the same structure in every shot, not as wardrobe or mood inspiration. Preserve its facial proportions, hairline, hairstyle, and body ratios while retaining the original photograph anchors as the primary evidence. ` : '';
  const supportRole = (payload.supportingPhotos || []).map((photo, i) => `image ${moodIndex + i + 1}: additional ${photo.role} evidence for the same model`).join('; ');
  return `Create ONE new, photorealistic professional ${payload.mode === 'wedding' ? 'wedding fashion photograph' : `${payload.mode} fashion photograph`}.
IMAGE ROLES: image 1 is the model's face/identity anchor; image 2 is the same model's full-body/proportion anchor; ${sheetRole}image ${moodIndex} is mood inspiration ONLY. ${supportRole}. Never substitute the person from image ${moodIndex}. Maintain image 1's recognizable facial structure and features and image 2's build, body proportions, stature, and natural skin appearance. Do not slim, enlarge, beautify into a different identity, or change age. Identity consistency is a goal, not a reason to copy a source photograph.
Identity consistency has priority over all style and composition requests. Keep eye/nose/mouth placement, face silhouette, hair and body build stable. User-supplied model constraints: ${JSON.stringify(payload.identityProfile || {})}.
Use the mood reference's atmosphere, color relationships, and lighting character as inspiration. Design NEW clothing and accessories with clearly different details, construction and styling; do not reproduce the exact outfit, logos, jewelry, source pose, or composition. Make a genuinely new photograph. ${payload.mode === 'wedding' ? 'Use original bridal or tailored wedding styling, realistic fabric drape, lace and hand anatomy; no costume-like synthetic finish.' : ''}
SHOT DIRECTION: ${shot.pose}. Gaze: ${shot.gaze || 'natural and candid'}. Framing: ${shot.framing || 'a balanced original editorial composition'}. Requested final aspect ratio ${payload.aspectRatio}. The native output may be center-cropped to that final ratio: keep the face, head, hands and any requested full-body feet safely inside the central framing area with generous extra margins, particularly at the top and bottom. Do not place important identity or wardrobe details close to the image edges.
Composition-board positions are rough intent, not a collage: ${JSON.stringify(payload.layers)}. Interpret them as a believable three-dimensional scene.
Additional creative brief: ${payload.brief || 'Natural editorial realism.'}
Shot-specific notes: ${shot.prompt}
Real camera optics, physically plausible light and shadows, natural pores and fine hair, realistic hands and body anatomy, authentic textile texture, subtle color grading. No plastic skin, excessive retouching, pasted faces, watermarks or added text. Variation ${shot.id}: create a distinct pose, eye direction and camera composition within the series.`;
}

function providerSize(payload) {
  return payload.aspectRatio === '1:1' ? '1024x1024' : ['16:9', '3:2', 'landscape'].includes(payload.aspectRatio) ? '1536x1024' : '1024x1536';
}

function providerInputs(payload, reference) {
  return payload.kind === 'model-sheet'
    ? [payload.face, payload.body, ...payload.supportingPhotos]
    : [payload.face, payload.body, ...(payload.identitySheet ? [payload.identitySheet] : []), reference, ...payload.supportingPhotos];
}

export function buildPreview(kind, source, model = 'gpt-image-1') {
  if (!['model-sheet', 'editorial'].includes(kind)) throw new RequestError(400, '기준 시트 또는 화보 검증 종류를 선택해 주세요.');
  const payload = kind === 'model-sheet' ? validateSheetPayload(source) : validatePayload(source);
  const inputs = []; const registry = new Map();
  const hash = value => createHash('sha256').update(value).digest('hex');
  const addInput = (image, role) => {
    if (registry.has(image)) return registry.get(image);
    const sha256 = hash(image.bytes);
    const id = `${role}-${sha256.slice(0, 16)}-${inputs.length + 1}`;
    inputs.push({ id, index: inputs.length + 1, role, name: image.name, dataUrl: `data:${image.mime};base64,${image.bytes.toString('base64')}`, sha256 });
    registry.set(image, id); return id;
  };
  const shots = payload.shots.map(shot => {
    const reference = kind === 'model-sheet' ? null : payload.references.find(ref => ref.id === shot.referenceId);
    const roles = kind === 'model-sheet'
      ? ['face', 'body', ...payload.supportingPhotos.map(photo => `support-${photo.role}`)]
      : ['face', 'body', ...(payload.identitySheet ? ['identity-sheet'] : []), 'reference', ...payload.supportingPhotos.map(photo => `support-${photo.role}`)];
    return {
      id: shot.id, referenceId: shot.referenceId,
      prompt: kind === 'model-sheet' ? buildSheetPrompt(payload) : buildPrompt(payload, shot),
      size: providerSize(payload),
      inputIds: providerInputs(payload, reference).map((image, index) => addInput(image, roles[index]))
    };
  });
  const profile = kind === 'model-sheet' ? payload.profile : payload.identityProfile;
  const revision = kind === 'model-sheet' ? source?.profile?.revision : source?.identityProfile?.revision;
  const profileRevision = Number.isSafeInteger(revision) && revision > 0 ? revision : null;
  const sourceFingerprint = hash(JSON.stringify({ kind, profile, profileRevision, inputs: inputs.map(({ role, sha256 }) => ({ role, sha256 })), shots: shots.map(({ prompt, inputIds, size }) => ({ prompt, inputIds, size })) }));
  return {
    kind, billable: false, model, requestedQuality: 'high',
    instructions: '선택한 컷의 프롬프트를 ChatGPT에 붙여넣고 inputIds 순서대로 번호를 붙인 원본 사진을 첨부해 이미지 생성을 요청하세요. 이 미리보기는 이미지 API를 호출하지 않습니다. ChatGPT 이미지 생성은 사용 중인 플랜과 사용 한도를 따릅니다. ChatGPT와 이 사이트 API의 모델·처리 방식은 다를 수 있으므로 API 품질·속도·비용이 검증된 것은 아닙니다.',
    profileId: profile?.id || null, profileRevision, sourceFingerprint, inputs, shots
  };
}

async function readJson(req, maxBytes = MAX_BODY) {
  if (!String(req.headers['content-type'] || '').startsWith('application/json')) throw new RequestError(415, 'JSON 요청이 필요합니다.');
  if (Number(req.headers['content-length']) > maxBytes) throw new RequestError(413, '사진 용량이 너무 큽니다. 이미지를 줄여 다시 시도해 주세요.');
  let size = 0; const chunks = [];
  for await (const chunk of req) { size += chunk.length; if (size > maxBytes) throw new RequestError(413, `최대 업로드 용량은 ${maxBytes / 1024 / 1024}MB입니다.`); chunks.push(chunk); }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { throw new RequestError(400, 'JSON 요청을 읽을 수 없습니다.'); }
}

export function createStudioServer({ root = DEFAULT_ROOT, apiKey = process.env.STUDIO_IMAGE_API_KEY || process.env.OPENAI_API_KEY || '', model = process.env.OPENAI_IMAGE_MODEL || 'gpt-image-1', fetchImpl = fetch, retentionMs = 30 * 60 * 1000 } = {}) {
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
      if (url.pathname.startsWith('/api/studio/')) {
        if (req.headers.origin && req.headers.origin !== `http://${req.headers.host}` && req.headers.origin !== `https://${req.headers.host}`) throw new RequestError(403, '같은 웹페이지에서만 요청할 수 있습니다.');
        if (req.headers['sec-fetch-site'] === 'cross-site') throw new RequestError(403, '다른 사이트에서 보낸 요청입니다.');
        if (req.method === 'GET' && url.pathname === '/api/studio/status') return json(res, 200, { configured: Boolean(apiKey), model, maxReferences: 3, shotsPerReference: 10, modelSheet: true, maxModelPhotos: 10, developmentPreview: true });
        if (req.method === 'POST' && url.pathname === '/api/studio/preview') {
          const data = await readJson(req, MAX_SHEET_BODY);
          if (data?.kind === 'editorial' && Buffer.byteLength(JSON.stringify(data)) > MAX_BODY) throw new RequestError(413, '화보 검증 요청의 최대 업로드 용량은 32MB입니다.');
          return json(res, 200, buildPreview(data?.kind, data?.payload, model));
        }
        if (req.method === 'POST' && ['/api/studio/generate', '/api/studio/model-sheet'].includes(url.pathname)) {
          if (!apiKey) throw new RequestError(503, '실제 이미지 생성은 서버의 STUDIO_IMAGE_API_KEY 연결 후 사용할 수 있습니다. 사진 업로드와 구성 보드는 지금 사용할 수 있습니다.', 'not_configured');
          const key = req.socket.remoteAddress; const recent = (rates.get(key) || []).filter(time => Date.now() - time < 60_000);
          if (recent.length >= 6) throw new RequestError(429, '잠시 후 다시 요청해 주세요.');
          if ([...jobs.values()].filter(job => !job.finishedAt).length >= 2) throw new RequestError(429, '생성 중인 작업이 있습니다. 완료 후 다시 시도해 주세요.');
          const isSheet = url.pathname === '/api/studio/model-sheet';
          const payload = isSheet ? validateSheetPayload(await readJson(req, MAX_SHEET_BODY)) : validatePayload(await readJson(req));
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
