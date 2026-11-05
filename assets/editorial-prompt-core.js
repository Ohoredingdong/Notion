/* Shared MUSE input validation and prompt preparation. No network or image generation. */
(function (root, factory) {
  const shared = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = shared;
  else root.MusePrompts = shared.createCore();
})(typeof globalThis === 'object' ? globalThis : this, function (root) {
  'use strict';
  function createCore(adapters = {}) {
    const MAX_BODY = 32 * 1024 * 1024;
    const MAX_SHEET_BODY = 64 * 1024 * 1024;
    const MAX_IMAGE = 6 * 1024 * 1024;
    const randomUUID = adapters.randomUUID || (() => {
      if (!root.crypto?.randomUUID) throw new Error('안전한 브라우저에서 다시 열어주세요.');
      return root.crypto.randomUUID();
    });
    const decodeBase64 = adapters.decodeBase64 || (encoded => {
      const binary = root.atob(encoded);
      return Uint8Array.from(binary, char => char.charCodeAt(0));
    });
    const encodeBase64 = adapters.encodeBase64 || (bytes => {
      let binary = '';
      for (let offset = 0; offset < bytes.length; offset += 0x8000) {
        binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
      }
      return root.btoa(binary);
    });
    const sha256 = adapters.sha256 || (value => {
      if (!root.crypto?.subtle) throw new Error('이 브라우저에서는 검증 자료를 만들 수 없습니다. 최신 브라우저의 HTTPS 주소에서 다시 열어주세요.');
      const bytes = typeof value === 'string' ? new root.TextEncoder().encode(value) : value;
      return root.crypto.subtle.digest('SHA-256', bytes).then(hash => Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join(''));
    });
    const chain = (value, next) => value && typeof value.then === 'function' ? value.then(next) : next(value);
    const all = values => values.some(value => value && typeof value.then === 'function') ? Promise.all(values) : values;
    function assertPayloadSize(value, maxBytes) {
      let serialized;
      try { serialized = JSON.stringify(value); } catch { throw new RequestError(400, '요청 형식이 올바르지 않습니다.'); }
      if (typeof serialized !== 'string') throw new RequestError(400, '요청 형식이 올바르지 않습니다.');
      if (new root.TextEncoder().encode(serialized).byteLength > maxBytes) {
        throw new RequestError(413, `최대 업로드 용량은 ${maxBytes / 1024 / 1024}MB입니다.`);
      }
    }
const POSES = ['standing with relaxed shoulders', 'walking naturally', 'seated, turning slightly', 'a subtle three-quarter turn', 'leaning gently against an architectural element', 'a quiet over-the-shoulder moment', 'a close portrait with relaxed hands', 'a low-angle full-body stance', 'a candid motion with a fabric movement', 'a spacious environmental portrait'];

class RequestError extends Error {
  constructor(status, message, code = 'invalid_request') { super(message); this.status = status; this.code = code; }
}

function decodeImage(input, label) {
  if (!input || typeof input.dataUrl !== 'string') throw new RequestError(400, `${label} 사진이 필요합니다.`);
  const match = /^data:(image\/(?:png|jpeg|webp));base64,([A-Za-z0-9+/]+={0,2})$/.exec(input.dataUrl);
  if (!match || match[2].length > Math.ceil(MAX_IMAGE / 3) * 4) throw new RequestError(400, `${label}: JPG·PNG·WebP 이미지(6MB 이하)를 사용해 주세요.`);
  let bytes;
  try { bytes = decodeBase64(match[2]); } catch { throw new RequestError(400, `${label}: 유효한 이미지 파일이 아닙니다.`); }
  if (encodeBase64(bytes).replace(/=+$/, '') !== match[2].replace(/=+$/, '') || (match[2].includes('=') && match[2].length % 4 !== 0)) {
    throw new RequestError(400, `${label}: 유효한 이미지 파일이 아닙니다.`);
  }
  const jpeg = bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  const png = [137, 80, 78, 71, 13, 10, 26, 10].every((value, index) => bytes[index] === value);
  const webp = [82, 73, 70, 70].every((value, index) => bytes[index] === value) && [87, 69, 66, 80].every((value, index) => bytes[index + 8] === value);
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

function validateSheetPayload(data) {
  assertPayloadSize(data, MAX_SHEET_BODY);
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

function buildSheetPrompt(payload) {
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

function validatePayload(data) {
  assertPayloadSize(data, MAX_BODY);
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

function buildPrompt(payload, shot) {
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

function buildPreview(kind, source, model = 'gpt-image-1') {
  if (!['model-sheet', 'editorial'].includes(kind)) throw new RequestError(400, '기준 시트 또는 화보 검증 종류를 선택해 주세요.');
  assertPayloadSize({ kind, payload: source }, kind === 'model-sheet' ? MAX_SHEET_BODY : MAX_BODY);
  const payload = kind === 'model-sheet' ? validateSheetPayload(source) : validatePayload(source);
  // Preserve image-role identity even when two originals contain identical bytes.
  // Register shared originals once, in their first provider-input appearance order.
  const registered = []; const registry = new Map();
  const addInput = (image, role) => {
    if (!registry.has(image)) { registry.set(image, registered.length); registered.push({ image, role }); }
    return registry.get(image);
  };
  const planned = payload.shots.map(shot => {
    const reference = kind === 'model-sheet' ? null : payload.references.find(ref => ref.id === shot.referenceId);
    const roles = kind === 'model-sheet'
      ? ['face', 'body', ...payload.supportingPhotos.map(photo => `support-${photo.role}`)]
      : ['face', 'body', ...(payload.identitySheet ? ['identity-sheet'] : []), 'reference', ...payload.supportingPhotos.map(photo => `support-${photo.role}`)];
    return { id: shot.id, referenceId: shot.referenceId,
      prompt: kind === 'model-sheet' ? buildSheetPrompt(payload) : buildPrompt(payload, shot),
      size: providerSize(payload), inputIndexes: providerInputs(payload, reference).map((image, index) => addInput(image, roles[index])) };
  });
  return chain(all(registered.map(({ image }) => sha256(image.bytes))), hashes => {
    const inputs = registered.map(({ image, role }, index) => ({
      id: `${role}-${hashes[index].slice(0, 16)}-${index + 1}`, index: index + 1, role, name: image.name,
      dataUrl: `data:${image.mime};base64,${encodeBase64(image.bytes)}`, sha256: hashes[index]
    }));
    const shots = planned.map(({ inputIndexes, ...shot }) => ({ ...shot, inputIds: inputIndexes.map(index => inputs[index].id) }));
    const profile = kind === 'model-sheet' ? payload.profile : payload.identityProfile;
    const revision = kind === 'model-sheet' ? source?.profile?.revision : source?.identityProfile?.revision;
    const profileRevision = Number.isSafeInteger(revision) && revision > 0 ? revision : null;
    const fingerprintValue = JSON.stringify({ kind, profile, profileRevision,
      inputs: inputs.map(({ role, sha256 }) => ({ role, sha256 })),
      shots: shots.map(({ prompt, inputIds, size }) => ({ prompt, inputIds, size })) });
    return chain(sha256(fingerprintValue), sourceFingerprint => ({
      kind, billable: false, model, requestedQuality: 'high',
      instructions: '선택한 컷의 프롬프트를 ChatGPT에 붙여넣고 inputIds 순서대로 번호를 붙인 원본 사진을 첨부해 이미지 생성을 요청하세요. 이 미리보기는 이미지 API를 호출하지 않습니다. ChatGPT 이미지 생성은 사용 중인 플랜과 사용 한도를 따릅니다. ChatGPT와 이 사이트 API의 모델·처리 방식은 다를 수 있으므로 API 품질·속도·비용이 검증된 것은 아닙니다.',
      profileId: profile?.id || null, profileRevision, sourceFingerprint, inputs, shots
    }));
  });
}
    return Object.freeze({ RequestError, validatePayload, validateSheetPayload, buildPrompt, buildSheetPrompt, providerSize, providerInputs, buildPreview,
      limits: Object.freeze({ MAX_BODY, MAX_SHEET_BODY, MAX_IMAGE }) });
  }
  return Object.freeze({ createCore });
});
