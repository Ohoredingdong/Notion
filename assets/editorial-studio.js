(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const assets = './assets/editorial-studio/';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const uid = prefix => `${prefix}-${crypto.randomUUID?.() || Date.now().toString(36) + Math.random().toString(36).slice(2)}`;
  const state = {
    mode: 'editorial', aspectRatio: '3:4', identity: { face: null, body: null },
    references: [{ id: 'reference-demo', name: 'The quiet muse', url: assets + 'editorial.jpg', dataUrl: null, demo: true }],
    layers: [], selectedLayer: null, selectedReference: 'reference-demo', configured: false,
    shots: [], jobId: null, polling: null, favorites: new Set(), filterFavorites: false, view: 'board', jobAspectRatio: '3:4'
  };
  const outputCache = new Map();
  let toastTimer;
  let dialogCleanup = null;
  let generationPending = false;
  let devPreviewPending = false;
  const modeNames = { editorial: '에디토리얼', campaign: '브랜드 캠페인', wedding: '웨딩' };
  const variations = [
    ['편안하게 정면으로 서기', '렌즈 정면', '전신 · 넓은 여백'],
    ['의자 끝에 자연스럽게 앉기', '화면 왼쪽', '무릎 위 미디엄'],
    ['천천히 한 걸음 걷기', '렌즈 너머', '전신 · 낮은 시점'],
    ['벽에 살짝 기대기', '아래로', '허리 위 · 사선'],
    ['어깨를 뒤로 살짝 돌리기', '어깨 너머 렌즈', '상반신 · 후면 3/4'],
    ['손을 느슨하게 모으기', '화면 오른쪽', '허리 위 · 눈높이'],
    ['앉아서 한쪽 팔 내려놓기', '렌즈 정면', '전신 · 약간 높은 시점'],
    ['옷자락을 가볍게 움직이기', '화면 바깥', '전신 · 측면'],
    ['턱을 조금 낮추고 정지하기', '렌즈 옆', '얼굴 클로즈업'],
    ['뒤돌아 천천히 멈추기', '먼 곳', '전신 · 건축적 와이드']
  ];

  function toast(message) {
    const el = $('#toast');
    if (!el) return;
    el.textContent = message;
    el.hidden = false;
    el.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.classList.remove('is-visible'); el.hidden = true; }, 4500);
  }
  function savePreferences() {
    try { localStorage.setItem('muse-studio-preferences-v1', JSON.stringify({ mode: state.mode, aspectRatio: state.aspectRatio, brief: $('#brief')?.value || '' })); } catch { /* Private mode can disallow storage. */ }
  }
  function applyPreferences() {
    try {
      const saved = JSON.parse(localStorage.getItem('muse-studio-preferences-v1') || '{}');
      if (modeNames[saved.mode]) state.mode = saved.mode;
      if (['3:4', '4:5', '1:1'].includes(saved.aspectRatio)) state.aspectRatio = saved.aspectRatio;
      if ($('#brief') && typeof saved.brief === 'string') $('#brief').value = saved.brief;
    } catch { /* Recover with defaults. */ }
    syncControls();
  }
  function syncControls() {
    $$('[data-mode]').forEach(button => { const active = button.dataset.mode === state.mode; button.classList.toggle('is-active', active); button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active)); });
    $$('[data-ratio]').forEach(button => { const active = button.dataset.ratio === state.aspectRatio; button.classList.toggle('is-active', active); button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active)); });
    $('#composition-stage')?.setAttribute('data-aspect-ratio', state.aspectRatio);
    const count = state.references.length * 10;
    if ($('#generate-button')) {
      const button = $('#generate-button');
      button.disabled = !!state.jobId || generationPending || devPreviewPending;
      const label = $(':scope > span', button);
      if (label) label.innerHTML = state.jobId ? '화보를 만드는 중…' : devPreviewPending ? '제작자료 준비 중…' : `<b id="shot-count">${count || 10}</b>컷 ${state.configured ? '생성하기' : '제작자료 만들기'}`;
    }
  }
  function modal(title, content) {
    const dialog = $('#app-dialog');
    if (!dialog) return;
    cleanupDialog();
    $('#dialog-title').textContent = title;
    $('#dialog-body').innerHTML = content;
    if (!dialog.open) dialog.showModal();
  }
  function cleanupDialog() { dialogCleanup?.(); dialogCleanup = null; }
  function closeModal() { cleanupDialog(); $('#app-dialog')?.close(); }

  function renderReferences() {
    const root = $('#reference-list');
    if (!root) return;
    root.innerHTML = state.references.map((ref, i) => `<article class="reference-card ${ref.id === state.selectedReference ? 'is-active' : ''}" data-reference-id="${escape(ref.id)}">
      <button type="button" class="reference-image-button" data-action="select-reference" data-id="${escape(ref.id)}" aria-label="${escape(ref.name)} 시안 선택"><img src="${escape(ref.url || ref.dataUrl)}" alt="${escape(ref.name)} 레퍼런스" draggable="false">${ref.sourceVideo ? '<span class="reference-video">▶ 영상 프레임</span>' : ''}</button>
      <div class="reference-meta"><span class="reference-number">${String(i + 1).padStart(2, '0')}</span><span class="reference-name">${escape(ref.name)}</span><span class="reference-shots">10컷</span></div>
      <button type="button" class="reference-remove" data-action="remove-reference" data-id="${escape(ref.id)}" aria-label="${escape(ref.name)} 삭제">×</button>
      <button type="button" class="reference-add" data-action="add-reference-layer" data-id="${escape(ref.id)}" aria-label="${escape(ref.name)} 보드에 배치">＋ 보드에 놓기</button>
      ${ref.demo ? '<span class="reference-demo">예시 시안</span>' : ''}</article>`).join('');
    if (!state.references.length) root.innerHTML = '<p class="empty-note">마음에 드는 사진이나 영상을 올려보세요.<br>시안 하나에서 서로 다른 10컷을 구상해요.</p>';
    syncControls();
  }
  function selectReference(id) {
    const ref = state.references.find(r => r.id === id);
    if (!ref) return;
    state.selectedReference = id;
    const hero = $('#stage-main');
    if (hero) { hero.hidden = false; hero.src = ref.url || ref.dataUrl; hero.alt = `${ref.name} · 구성 미리보기용 레퍼런스`; }
    renderReferences();
  }
  function resetMainPhoto() {
    const hero = $('#stage-main');
    if (!hero) return;
    hero.removeAttribute('src'); hero.hidden = true; hero.alt = '레퍼런스를 추가해 구성을 시작하세요';
    state.selectedReference = null;
  }
  async function readImage(file) {
    if (!window.MuseImages) throw new Error('사진 업로드 기능을 불러오지 못했습니다. 새로고침해주세요.');
    return window.MuseImages.read(file);
  }
  async function uploadIdentity(slot, file) {
    if (!file) return;
    try {
      const dataUrl = await readImage(file);
      state.identityProfile = null; state.identitySheet = null; state.supportingPhotos = [];
      updateModelBadge();
      state.identity[slot] = { name: file.name, dataUrl };
      const preview = $(`#${slot}-preview`); if (preview) preview.src = dataUrl;
      const card = $(`label[for="${slot}-upload"]`); card?.classList.add('has-upload'); card?.setAttribute('data-uploaded', 'true');
      if (preview) preview.alt = `${slot === 'face' ? '얼굴' : '전신'} 업로드 사진`;
      if (card && $('.photo-tag', card)) $('.photo-tag', card).textContent = '업로드됨';
      toast(`${slot === 'face' ? '얼굴' : '전신'} 사진을 추가했어요. 사진은 현재 브라우저에만 보관됩니다.`);
    } catch (error) { toast(error.message || '이미지를 읽지 못했습니다. 다른 사진을 선택해 주세요.'); }
  }
  function insertReference(file, dataUrl, sourceVideo = false) {
    if (state.references.filter(r => !r.demo).length >= 3) { toast('시안은 최대 3개까지 추가할 수 있어요.'); return; }
    if (state.references.some(r => r.demo)) {
      state.references = state.references.filter(r => !r.demo);
      state.layers = state.layers.filter(layer => !layer.demo);
      renderLayers();
    }
    const ref = { id: uid('ref'), name: file.name.replace(/\.[^.]+$/, ''), dataUrl, url: dataUrl, sourceVideo };
    state.references.push(ref); selectReference(ref.id);
    toast(sourceVideo ? '선택한 영상 프레임을 시안으로 추가했어요.' : '새 시안을 추가했어요. 같은 무드로 10컷을 설계합니다.');
  }
  function videoPicker(file) {
    if (file.size > 60 * 1024 * 1024) { toast('영상은 60MB 이하로 올려주세요.'); return; }
    const url = URL.createObjectURL(file);
    modal('영상에서 마음에 드는 순간 고르기', `<p class="dialog-description">영상의 한 프레임을 골라 조명·색감·스타일의 레퍼런스로 사용해요. 결과물은 이미지입니다.</p><video id="video-source" class="video-source" src="${escape(url)}" controls muted playsinline preload="metadata"></video><label class="dialog-field">장면 선택 <output id="frame-time">0.0초</output><input id="frame-seek" type="range" min="0" max="1" step="0.1" value="0" aria-label="프레임 시간"></label><button type="button" class="dialog-primary" id="capture-frame" disabled>이 장면을 시안으로 사용</button>`);
    const video = $('#video-source');
    const seek = $('#frame-seek'); const capture = $('#capture-frame');
    dialogCleanup = () => { video.pause(); video.removeAttribute('src'); video.load(); URL.revokeObjectURL(url); };
    video.addEventListener('loadedmetadata', () => { if (Number.isFinite(video.duration)) seek.max = String(Math.max(0.1, video.duration - 0.05)); });
    video.addEventListener('loadeddata', () => { capture.disabled = false; });
    video.addEventListener('error', () => { capture.disabled = true; toast('이 영상 형식을 재생할 수 없습니다. MP4 또는 WebM을 사용해 주세요.'); });
    video.addEventListener('timeupdate', () => { seek.value = String(video.currentTime); $('#frame-time').textContent = `${video.currentTime.toFixed(1)}초`; });
    seek.addEventListener('input', () => { video.pause(); capture.disabled = true; video.currentTime = Number(seek.value); $('#frame-time').textContent = `${Number(seek.value).toFixed(1)}초`; });
    video.addEventListener('seeked', () => { capture.disabled = false; });
    capture.addEventListener('click', () => {
      if (!video.videoWidth || video.seeking) return;
      const canvas = document.createElement('canvas'), scale = Math.min(1, 1536 / Math.max(video.videoWidth, video.videoHeight));
      canvas.width = Math.round(video.videoWidth * scale); canvas.height = Math.round(video.videoHeight * scale);
      canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
      insertReference(file, dataUrl, true); closeModal();
    });
  }
  async function uploadReferences(files) {
    for (const file of files) {
      if (state.references.filter(r => !r.demo).length >= 3) { toast('시안은 최대 3개까지 추가할 수 있어요.'); break; }
      if (file.type.startsWith('video/')) { videoPicker(file); if (files.length > 1) toast('영상은 한 번에 하나씩 장면을 골라주세요. 나머지 파일은 다시 추가할 수 있어요.'); break; }
      try { insertReference(file, await readImage(file)); } catch (error) { toast(error.message || '시안을 읽지 못했습니다.'); }
    }
  }
  function addLayer(ref, options = {}) {
    if (state.layers.length >= 8) { toast('보드에는 최대 8개 요소를 배치할 수 있어요.'); return; }
    state.layers.push({ id: uid('layer'), referenceId: ref.id, label: ref.name, url: ref.url || ref.dataUrl, x: options.x ?? 76, y: options.y ?? 32, scale: options.scale ?? 25, rotation: options.rotation ?? 6, demo: !!options.demo });
    state.selectedLayer = state.layers.at(-1).id; renderLayers();
  }
  function renderLayers() {
    const stage = $('#composition-stage'); if (!stage) return;
    $$('.stage-layer', stage).forEach(el => el.remove());
    state.layers.forEach(layer => {
      const el = document.createElement('div');
      el.className = `stage-layer ${state.selectedLayer === layer.id ? 'is-selected' : ''}`;
      el.tabIndex = 0; el.dataset.layerId = layer.id; el.setAttribute('role', 'group');
      el.setAttribute('aria-label', `${layer.label}. 드래그 또는 방향키로 이동, Delete로 삭제, Enter로 크기와 각도 조절`);
      el.innerHTML = `<img src="${escape(layer.url)}" alt="${escape(layer.label)} 배치 요소" draggable="false"><span class="layer-caption">${escape(layer.label)}</span><button type="button" class="layer-remove" aria-label="이 요소 삭제">×</button>`;
      placeLayer(el, layer); stage.append(el);
      el.addEventListener('pointerdown', event => startDrag(event, layer));
      el.addEventListener('keydown', event => {
        if (event.target !== el) return;
        const move = event.shiftKey ? 5 : 1;
        const directions = { ArrowLeft: [-move, 0], ArrowRight: [move, 0], ArrowUp: [0, -move], ArrowDown: [0, move] };
        if (directions[event.key]) { event.preventDefault(); layer.x = clamp(layer.x + directions[event.key][0]); layer.y = clamp(layer.y + directions[event.key][1]); placeLayer(el, layer); }
        if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); removeLayer(layer.id); }
        if (event.key === 'Enter') { event.preventDefault(); editLayer(layer.id); }
      });
      el.addEventListener('dblclick', () => editLayer(layer.id));
      $('.layer-remove', el).addEventListener('click', () => removeLayer(layer.id));
    });
  }
  function clamp(n) { return Math.min(94, Math.max(6, n)); }
  function placeLayer(el, layer) { el.style.left = layer.x + '%'; el.style.top = layer.y + '%'; el.style.width = layer.scale + '%'; el.style.transform = `translate(-50%, -50%) rotate(${layer.rotation}deg)`; }
  function removeLayer(id) { state.layers = state.layers.filter(l => l.id !== id); if (state.selectedLayer === id) state.selectedLayer = null; renderLayers(); }
  function startDrag(event, layer) {
    if (event.target.closest('button') || event.button !== 0) return;
    const el = event.currentTarget, stage = $('#composition-stage');
    const rect = stage.getBoundingClientRect();
    const initial = { x: layer.x, y: layer.y, clientX: event.clientX, clientY: event.clientY };
    state.selectedLayer = layer.id;
    $$('.stage-layer', stage).forEach(item => item.classList.toggle('is-selected', item === el));
    el.setPointerCapture(event.pointerId); el.focus({ preventScroll: true });
    const move = e => { layer.x = clamp(initial.x + (e.clientX - initial.clientX) / rect.width * 100); layer.y = clamp(initial.y + (e.clientY - initial.clientY) / rect.height * 100); placeLayer(el, layer); };
    const end = () => { el.removeEventListener('pointermove', move); el.removeEventListener('pointerup', end); el.removeEventListener('pointercancel', cancel); };
    const cancel = () => { layer.x = initial.x; layer.y = initial.y; placeLayer(el, layer); end(); };
    el.addEventListener('pointermove', move); el.addEventListener('pointerup', end); el.addEventListener('pointercancel', cancel);
  }
  function editLayer(id) {
    const layer = state.layers.find(l => l.id === id); if (!layer) return;
    modal('구성 요소 조절', `<p class="dialog-description">보드에서 배치한 위치와 크기를 생성 방향에 함께 전달해요. 완성 사진은 이 구성을 참고해 새롭게 촬영됩니다.</p><label class="dialog-field">크기<input type="range" id="layer-scale" min="12" max="65" value="${layer.scale}"></label><label class="dialog-field">기울기<input type="range" id="layer-rotation" min="-30" max="30" value="${layer.rotation}"></label><button type="button" class="dialog-primary" id="layer-done">배치 완료</button>`);
    const update = () => { layer.scale = Number($('#layer-scale').value); layer.rotation = Number($('#layer-rotation').value); const el = $(`[data-layer-id="${layer.id}"]`); if (el) placeLayer(el, layer); };
    $('#layer-scale').addEventListener('input', update); $('#layer-rotation').addEventListener('input', update); $('#layer-done').addEventListener('click', closeModal);
  }
  function buildPlan() {
    return state.references.flatMap((ref, referenceIndex) => variations.map(([pose, gaze, framing], i) => ({
      id: `${ref.id}-shot-${i + 1}`, referenceId: ref.id, pose, gaze, framing,
      prompt: `${modeNames[state.mode]} 시안 ${referenceIndex + 1}, 컷 ${i + 1}. ${pose}. 시선: ${gaze}. 구도: ${framing}. 업로드된 얼굴의 특징과 전신의 체형·체격·비율을 유지. 원본 시안의 무드·조명·색감을 해석하되 의상·액세서리·포즈·배경 디테일을 새롭게 디자인. 자연스러운 피부 결, 현실적인 신체 비율과 손, 실제 카메라와 렌즈로 촬영한 듯한 사진. ${state.mode === 'wedding' ? '실제 웨딩 화보처럼 정교한 드레스 소재와 자연스러운 표정. ' : ''}${$('#brief')?.value?.trim() || ''}`
    })));
  }
  function planModal(showConnection = false) {
    const shots = buildPlan();
    modal(showConnection ? '촬영 플랜을 먼저 확인해보세요' : '서로 다른 시선, 10개의 장면', `<p class="dialog-description">${showConnection ? '현재는 구성 미리보기 모드예요. 실제 이미지 생성은 생성 서비스 연결 후 사용할 수 있습니다. ' : ''}시안마다 포즈·시선·구도를 달리한 10컷을 설계합니다. 예시 사진은 생성 결과가 아닙니다.</p><div class="plan-summary"><span>${escape(modeNames[state.mode])}</span><span>${escape(state.aspectRatio)}</span><strong>총 ${shots.length}컷</strong></div><div class="shot-plan-list">${shots.map((shot, i) => `<article class="shot-plan-row"><span>${String(i + 1).padStart(2, '0')}</span><div><strong>${escape(shot.pose)}</strong><p>${escape(shot.gaze)} · ${escape(shot.framing)}</p></div><span class="shot-plan-tag">시안 ${Math.floor(i / 10) + 1}</span></article>`).join('') || '<p>시안을 먼저 추가해주세요.</p>'}</div><p class="dialog-note">얼굴·체형 유지와 사실적인 표현을 요청하지만 완전한 일치를 보장하지는 않습니다. 완성된 컷을 직접 확인해주세요.</p><div class="dialog-actions"><button type="button" class="dialog-secondary" id="export-plan">촬영 플랜 저장</button><button type="button" class="dialog-primary" id="plan-done">보드로 돌아가기</button></div>`);
    $('#export-plan').addEventListener('click', exportPlan); $('#plan-done').addEventListener('click', closeModal);
  }
  function exportPlan() {
    download(new Blob([JSON.stringify({ title: 'MUSE STUDIO 촬영 플랜', mode: state.mode, aspectRatio: state.aspectRatio, brief: $('#brief')?.value || '', identityProfile: state.identityProfile || null, identity: { face: state.identity.face?.name || null, body: state.identity.body?.name || null }, references: state.references.map(({ id, name, demo, sourceVideo }) => ({ id, name, demo: !!demo, sourceVideo: !!sourceVideo })), layers: state.layers.map(({ url, ...layer }) => layer), shots: buildPlan() }, null, 2)], { type: 'application/json' }), 'muse-shoot-plan.json');
    toast('촬영 플랜을 저장했어요. 원본 사진은 포함하지 않습니다.');
  }
  function download(source, name) {
    const isBlob = source instanceof Blob, url = isBlob ? URL.createObjectURL(source) : source;
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; document.body.append(anchor); anchor.click(); anchor.remove();
    if (isBlob) setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function setView(view) {
    if (view === 'board' && state.view === 'model') {
      const model = window.MuseModel?.snapshot();
      if (model?.uploadingPhotos) { toast('사진을 읽는 중입니다. 업로드가 끝나면 다음 단계로 이동할 수 있어요.'); return; }
      if (model?.hasFace && model.hasBody) window.MuseModel.use(false);
    }
    state.view = view;
    $$('[data-view]').forEach(button => { const active = button.dataset.view === view; button.classList.toggle('is-active', active); button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active)); button.removeAttribute('aria-selected'); });
    if ($('#board-view')) $('#board-view').hidden = view !== 'board';
    if ($('#results-view')) $('#results-view').hidden = view !== 'results';
    if ($('#model-view')) $('#model-view').hidden = view !== 'model';
    const title = $('.workspace-heading h1'), subtitle = $('.workspace-heading p');
    if (title) title.innerHTML = view === 'model' ? '같은 당신으로, 무한한 장면을<span>.</span>' : '당신의 다음 화보를 그려보세요<span>.</span>';
    if (subtitle) subtitle.textContent = view === 'model' ? '모델의 기준을 먼저 만들고, 모든 화보에 같은 얼굴과 체형을 참조하세요.' : '당신의 모습에 새로운 무드를 더해, 세상에 없던 한 장으로.';
    if (view === 'results') renderResults();
  }
  function renderResults() {
    const grid = $('#results-grid'); if (!grid) return;
    const shots = state.filterFavorites ? state.shots.filter(s => state.favorites.has(s.id)) : state.shots;
    const complete = state.shots.filter(s => s.status === 'completed').length;
    if ($('#result-count')) $('#result-count').textContent = complete;
    if ($('#cancel-button')) $('#cancel-button').hidden = !state.jobId;
    if (!shots.length) { grid.innerHTML = `<div class="results-empty"><span class="empty-orbit">✳</span><h3>${state.filterFavorites ? '아직 선택한 컷이 없어요' : '다음 화보의 첫 장면을 기다려요'}</h3><p>${state.filterFavorites ? '완성된 이미지의 하트를 눌러 모아보세요.' : '모델 사진과 시안을 준비하고 새로운 10컷을 만들어보세요.'}</p><button type="button" class="dialog-secondary" data-action="show-plan">촬영 플랜 미리보기 ↗</button></div>`; return; }
    grid.innerHTML = shots.map((shot, index) => `<article class="result-card ${shot.status === 'completed' ? 'is-complete' : ''}" data-shot-id="${escape(shot.id)}">${shot.dataUrl ? `<button type="button" class="result-image" data-action="preview-shot" data-id="${escape(shot.id)}" aria-label="${index + 1}번 컷 크게 보기"><img src="${escape(shot.dataUrl)}" alt="${shot.origin === 'manual' ? '외부에서 가져온 화보' : '생성된 화보'} ${index + 1}번 컷"></button>` : `<div class="result-placeholder"><span>${shot.status === 'failed' ? '!' : shot.status === 'cancelled' ? '—' : '✳'}</span><p>${{ queued: '촬영 대기', running: '장면을 만들고 있어요', failed: '생성 실패', cancelled: '취소됨', 'manual-pending': '외부 결과 가져오기 대기' }[shot.status] || '대기 중'}</p>${shot.error ? `<small>${escape(shot.error)}</small>` : ''}</div>`}<div class="result-meta"><span>SHOT ${String(index + 1).padStart(2, '0')}</span>${shot.origin === 'manual' ? '<small class="result-origin">외부 생성 · 수동 검증</small>' : ''}${shot.dataUrl ? `<button type="button" data-action="favorite-shot" data-id="${escape(shot.id)}" aria-label="${state.favorites.has(shot.id) ? '선택 해제' : '마음에 드는 컷 선택'}" aria-pressed="${state.favorites.has(shot.id)}">${state.favorites.has(shot.id) ? '♥' : '♡'}</button><button type="button" data-action="download-shot" data-id="${escape(shot.id)}" aria-label="${index + 1}번 컷 다운로드">↓</button>` : ''}</div></article>`).join('');
  }
  async function checkConnection() {
    try { const response = await fetch('/api/studio/status', { signal: AbortSignal.timeout(4500) }); if (!response.ok) throw new Error(); const data = await response.json(); state.configured = data.configured === true; }
    catch { state.configured = false; }
    if ($('#connection-status')) { $('#connection-status').textContent = state.configured ? '생성 설정 있음' : '미리보기 모드'; $('#connection-status').classList.toggle('is-connected', state.configured); }
    if ($('#studio-generation-notice')) $('#studio-generation-notice').hidden = state.configured;
    syncControls();
    window.dispatchEvent(new CustomEvent('muse:connection', { detail: { configured: state.configured } }));
    return state.configured;
  }
  function generationPayload() {
    return { mode: state.mode, aspectRatio: state.aspectRatio, brief: $('#brief')?.value || '', identity: state.identity, identityProfile: state.identityProfile || undefined, identitySheet: state.identitySheet || undefined, supportingPhotos: state.supportingPhotos || [], references: state.references.map(({ id, name, dataUrl }) => ({ id, name, dataUrl })), layers: state.layers.filter(layer => !layer.demo).map(({ url, ...layer }) => layer), shots: buildPlan() };
  }
  function preflightGeneration() {
    const images = [state.identity.face?.dataUrl, state.identity.body?.dataUrl, ...state.references.map(ref => ref.dataUrl)];
    if (!state.references.length || state.references.length > 3 || images.some(image => typeof image !== 'string' || !image.startsWith('data:image/'))) throw new Error('얼굴·전신 사진과 레퍼런스를 모두 올려주세요.');
    const payload = generationPayload();
    const json = JSON.stringify(payload);
    if (new Blob([json]).size > 32 * 1024 * 1024) throw new Error('사진 용량이 너무 큽니다. 더 작은 사진을 선택하거나 시안 수를 줄여주세요.');
    return { payload, json };
  }
  async function generate() {
    if (generationPending || state.jobId) return;
    if (!state.references.length) { toast('레퍼런스 사진 또는 영상을 먼저 추가해 주세요.'); return; }
    if (!state.configured) {
      if (state.identity.face && state.identity.body && !state.references.some(ref => ref.demo)) await studioDevPreview();
      else planModal(true);
      return;
    }
    if (!state.identity.face || !state.identity.body || state.references.some(r => r.demo)) { toast('나의 얼굴·전신 사진과 새 레퍼런스를 모두 올려주세요. 예시 사진으로는 생성하지 않습니다.'); return; }
    try { preflightGeneration(); } catch (error) { toast(error.message); return; }
    const count = state.references.length * 10;
    modal('새로운 화보를 생성할까요?', `<p class="dialog-description">레퍼런스 ${state.references.length}개에서 총 <strong>${count}컷</strong>을 만듭니다. 고화질 이미지 생성 API에 <strong>${count}개의 유료 요청</strong>을 전송하며, 요금은 연결한 서비스의 요금제에 따라 청구됩니다.</p><div class="plan-summary"><span>${escape(modeNames[state.mode])}</span><span>${escape(state.aspectRatio)}</span><strong>${count}컷</strong></div><p class="dialog-note">업로드한 모델 사진과 레퍼런스가 이미지 생성 서비스로 전송됩니다. 완성된 사진은 선택한 비율에 맞춰 중앙 크롭합니다.</p><div class="dialog-actions"><button type="button" class="dialog-secondary" id="generation-back">조금 더 수정하기</button><button type="button" class="dialog-primary" id="confirm-generation">${count}컷 유료 생성 시작</button></div>`);
    $('#generation-back').addEventListener('click', closeModal);
    $('#confirm-generation').addEventListener('click', () => { closeModal(); beginGeneration(); }, { once: true });
  }
  async function beginGeneration() {
    if (generationPending || state.jobId) return;
    generationPending = true; syncControls();
    const shots = buildPlan();
    state.jobAspectRatio = state.aspectRatio;
    outputCache.clear();
    try {
      const { json } = preflightGeneration();
      const response = await fetch('/api/studio/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: json });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || data.error || '이미지 생성을 시작하지 못했습니다. 잠시 후 다시 시도해주세요.');
      state.jobId = data.jobId; state.shots = shots.map(shot => ({ ...shot, status: 'queued' }));
      setView('results'); toast('새로운 촬영을 시작했어요. 각 컷이 완성되는 대로 보여드릴게요.'); pollJob();
    } catch (error) { toast(error.message); } finally { generationPending = false; syncControls(); }
  }
  async function pollJob() {
    if (!state.jobId) return;
    const jobId = state.jobId;
    try {
      const response = await fetch(`/api/studio/jobs/${encodeURIComponent(jobId)}`, { signal: AbortSignal.timeout(15000) });
      if (response.status === 404) {
        state.jobId = null; clearTimeout(state.polling);
        state.shots = state.shots.map(shot => ['queued', 'running'].includes(shot.status) ? { ...shot, status: 'failed', error: '생성 세션이 만료되었거나 서버가 재시작되었습니다.' } : shot);
        syncControls(); renderResults(); toast('생성 세션을 찾을 수 없어요. 완성된 컷을 저장하고 새로 생성해주세요.'); return;
      }
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || '생성 상태를 확인하지 못했습니다.');
      state.shots = await Promise.all(data.shots.map(normalizeOutput));
      renderResults();
      if (['completed', 'cancelled', 'failed'].includes(data.status)) { const completed = state.shots.filter(shot => shot.status === 'completed').length, failed = state.shots.filter(shot => shot.status === 'failed').length; state.jobId = null; syncControls(); renderResults(); toast(data.status === 'cancelled' ? '남은 촬영을 취소했어요.' : `${completed}컷이 완성됐어요.${failed ? ` ${failed}컷은 생성에 실패했습니다.` : ''}`); return; }
    } catch (error) { toast(`${error.message} 잠시 후 다시 확인합니다.`); }
    if (state.jobId === jobId) state.polling = setTimeout(pollJob, 2500);
  }
  async function normalizeOutput(shot) {
    if (!shot.dataUrl || shot.status !== 'completed') return shot;
    if (outputCache.has(shot.id)) return { ...shot, dataUrl: outputCache.get(shot.id) };
    try {
      const image = new Image(); image.src = shot.dataUrl; await image.decode();
      const [rw, rh] = state.jobAspectRatio.split(':').map(Number);
      const ratio = rw / rh;
      const sourceWidth = image.naturalWidth, sourceHeight = image.naturalHeight;
      const cropWidth = Math.min(sourceWidth, sourceHeight * ratio);
      const cropHeight = Math.min(sourceHeight, sourceWidth / ratio);
      const units = Math.max(1, Math.floor(Math.min(cropWidth / rw, cropHeight / rh)));
      const canvas = document.createElement('canvas'); canvas.width = units * rw; canvas.height = units * rh;
      canvas.getContext('2d').drawImage(image, (sourceWidth - cropWidth) / 2, (sourceHeight - cropHeight) / 2, cropWidth, cropHeight, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
      outputCache.set(shot.id, dataUrl);
      return { ...shot, dataUrl };
    } catch {
      return { ...shot, status: 'failed', dataUrl: undefined, error: '완성 이미지를 읽거나 선택한 비율로 변환하지 못했습니다. 다시 생성해주세요.' };
    }
  }
  function shotFilename(shot) {
    const extension = shot.dataUrl?.startsWith('data:image/jpeg') ? 'jpg' : shot.dataUrl?.startsWith('data:image/webp') ? 'webp' : 'png';
    return `muse-${shot.id}.${extension}`;
  }
  async function cancelJob() {
    if (!state.jobId) return;
    try { const response = await fetch(`/api/studio/jobs/${encodeURIComponent(state.jobId)}`, { method: 'DELETE' }); if (!response.ok) throw new Error(); toast('남은 컷의 생성을 중단하고 있어요.'); } catch { toast('취소 요청을 전송하지 못했습니다. 다시 시도해주세요.'); }
  }
  function help() {
    modal('아이디어에서 나만의 화보까지', '<div class="help-steps"><article><span>01</span><div><h3>나의 모델을 준비해요</h3><p>필터 없는 선명한 얼굴 사진과 몸 전체가 보이는 전신 사진을 각각 올려주세요. 본인 또는 사용 권한을 가진 사진을 사용해 주세요.</p></div></article><article><span>02</span><div><h3>마음에 드는 무드를 모아요</h3><p>화보·광고·웨딩 사진이나 영상의 한 장면을 최대 3개 추가하세요. 의상과 액세서리는 원본을 그대로 복제하지 않고 새롭게 해석합니다.</p></div></article><article><span>03</span><div><h3>직접 배치하고 방향을 정해요</h3><p>보드 위 사진을 드래그해 배치하거나 방향키로 미세 조절하세요. 더블클릭하면 크기와 각도를 바꿀 수 있어요. Delete 키로 지울 수 있습니다.</p></div></article><article><span>04</span><div><h3>같은 무드, 다른 10개의 장면</h3><p>생성 서비스 연결 후 시안마다 포즈·시선·구도가 다른 이미지를 생성해요. 얼굴과 체형 유지를 요청하며 결과마다 직접 확인할 수 있습니다. 영상은 레퍼런스 입력으로만 사용합니다.</p></div></article></div><p class="dialog-note">사진은 생성 요청 전까지 브라우저 안에서만 사용됩니다. 모델 기준 시트에 등록한 사진·승인 시트는 이 브라우저에 저장됩니다. 모델 키트로 내려받아 다음 작업에서 불러올 수 있어요. 화보 화면에서 직접 올린 사진은 임시로 사용합니다.</p>');
  }
  function settings() {
    modal('생성 서비스', `<div class="connection-card"><span class="connection-dot ${state.configured ? 'is-connected' : ''}"></span><strong>${state.configured ? '이미지 생성 설정이 있어요' : '구성 미리보기 모드입니다'}</strong><p>${state.configured ? '서버에 이미지 생성 설정이 있습니다. 실제 인증과 사용 가능 여부는 생성 요청 시 확인합니다. 완성된 이미지는 페이지를 닫기 전에 다운로드해주세요.' : '사진 업로드·시안 보드·촬영 플랜을 먼저 사용할 수 있어요. 실제 이미지를 만들려면 서버의 이미지 생성 서비스 연결이 필요합니다. 연결 정보는 브라우저에 입력하거나 저장하지 않습니다.'}</p></div><button type="button" class="dialog-primary" id="recheck-connection">설정 상태 다시 확인</button><p class="dialog-note">예시 사진은 화면 구성을 설명하기 위한 샘플이며 생성 결과가 아닙니다. AI 생성 특성상 얼굴·체형의 완전한 일치를 보장하지 않으므로 완성된 컷을 확인해주세요.</p>`);
    $('#recheck-connection').addEventListener('click', async () => { await checkConnection(); settings(); toast(state.configured ? '서버의 생성 설정을 확인했어요.' : '아직 생성 서비스 설정이 없어요.'); });
  }

  $('#face-upload')?.addEventListener('change', event => { uploadIdentity('face', event.target.files[0]); event.target.value = ''; });
  $('#body-upload')?.addEventListener('change', event => { uploadIdentity('body', event.target.files[0]); event.target.value = ''; });
  $('#reference-upload')?.addEventListener('change', event => { uploadReferences([...event.target.files]); event.target.value = ''; });
  $('#reference-list')?.addEventListener('click', event => {
    const button = event.target.closest('[data-action]'); if (!button) return;
    const ref = state.references.find(r => r.id === button.dataset.id); if (!ref) return;
    if (button.dataset.action === 'select-reference') selectReference(ref.id);
    if (button.dataset.action === 'remove-reference') { state.references = state.references.filter(r => r.id !== ref.id); state.layers = state.layers.filter(l => l.referenceId !== ref.id); renderLayers(); if (state.references.length) selectReference(state.references[0].id); else { resetMainPhoto(); renderReferences(); } }
    if (button.dataset.action === 'add-reference-layer') { addLayer(ref); toast('사진을 드래그해서 원하는 곳에 놓아보세요.'); }
  });
  $$('[data-mode]').forEach(button => button.addEventListener('click', () => { state.mode = button.dataset.mode; syncControls(); savePreferences(); if (state.references.length && state.references.every(r => r.demo) && $('#stage-main')) $('#stage-main').src = assets + (state.mode === 'wedding' ? 'bridal.jpg' : 'editorial.jpg'); }));
  $$('[data-ratio]').forEach(button => button.addEventListener('click', () => { state.aspectRatio = button.dataset.ratio; syncControls(); savePreferences(); }));
  $$('[data-view]').forEach(button => button.addEventListener('click', () => {
    if (button.hasAttribute('data-model-next') && window.MuseModel) window.MuseModel.use(true);
    else setView(button.dataset.view);
  }));
  $('#brief')?.addEventListener('input', savePreferences);
  $$('[data-brief]').forEach(button => button.addEventListener('click', () => {
    const input = $('#brief'); if (!input) return;
    const text = button.dataset.brief;
    if (!input.value.split(/[,，]\s*/).includes(text)) input.value = [input.value.trim(), text].filter(Boolean).join(', ').slice(0, input.maxLength > 0 ? input.maxLength : 1500);
    savePreferences(); input.focus();
  }));
  $('#generate-button')?.addEventListener('click', generate);
  $('#plan-button')?.addEventListener('click', () => planModal());
  $('#help-button')?.addEventListener('click', help);
  $('#settings-button')?.addEventListener('click', settings);
  $('#save-button')?.addEventListener('click', exportPlan);
  $('#cancel-button')?.addEventListener('click', cancelJob);
  $('#remove-layer-button')?.addEventListener('click', () => { if (state.selectedLayer) removeLayer(state.selectedLayer); else toast('먼저 보드에서 삭제할 사진을 선택해주세요.'); });
  $('#edit-layer-button')?.addEventListener('click', () => { if (state.selectedLayer) editLayer(state.selectedLayer); else toast('먼저 보드에서 조절할 사진을 선택해주세요.'); });
  $('#add-layer-button')?.addEventListener('click', () => { const ref = state.references.find(r => r.id === state.selectedReference) || state.references[0]; if (ref) addLayer(ref); else $('#reference-upload')?.click(); });
  $('#clear-references-button')?.addEventListener('click', () => { state.references = []; state.layers = []; resetMainPhoto(); renderLayers(); renderReferences(); });
  $('#dialog-close')?.addEventListener('click', closeModal);
  $('#app-dialog')?.addEventListener('close', cleanupDialog);
  $('#app-dialog')?.addEventListener('click', event => { if (event.target === event.currentTarget) { const rect = event.currentTarget.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeModal(); } });
  $('#results-grid')?.addEventListener('click', event => {
    const button = event.target.closest('[data-action]'); if (!button) return;
    if (button.dataset.action === 'show-plan') { planModal(); return; }
    const shot = state.shots.find(s => s.id === button.dataset.id); if (!shot) return;
    if (button.dataset.action === 'download-shot' && shot.dataUrl) download(shot.dataUrl, shotFilename(shot));
    if (button.dataset.action === 'favorite-shot') { if (state.favorites.has(shot.id)) state.favorites.delete(shot.id); else state.favorites.add(shot.id); renderResults(); }
    if (button.dataset.action === 'preview-shot' && shot.dataUrl) { modal('완성된 장면', `<img class="shot-preview" src="${escape(shot.dataUrl)}" alt="선택한 비율의 화보 이미지"><button type="button" class="dialog-primary" id="download-preview">화보 이미지 다운로드 ↓</button>`); $('#download-preview').addEventListener('click', () => download(shot.dataUrl, shotFilename(shot))); }
  });
  $$('[data-results-filter]').forEach(button => button.addEventListener('click', () => { state.filterFavorites = button.dataset.resultsFilter === 'favorites'; $$('[data-results-filter]').forEach(b => { b.classList.toggle('is-active', b === button); b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); }); renderResults(); }));
  const uploadZone = $('#reference-dropzone');
  uploadZone?.addEventListener('dragover', event => { event.preventDefault(); uploadZone.classList.add('dragover'); });
  uploadZone?.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
  uploadZone?.addEventListener('drop', event => { event.preventDefault(); uploadZone.classList.remove('dragover'); if (event.dataTransfer.files.length) uploadReferences([...event.dataTransfer.files]); });
  const stage = $('#composition-stage');
  stage?.addEventListener('dragover', event => { event.preventDefault(); stage.classList.add('is-dragover'); });
  stage?.addEventListener('dragleave', () => stage.classList.remove('is-dragover'));
  stage?.addEventListener('drop', event => { event.preventDefault(); stage.classList.remove('is-dragover'); if (event.dataTransfer.files.length) uploadReferences([...event.dataTransfer.files]); });
  // These tools prepare or import real test artifacts. They never call an image provider.
  let devPreview = null;
  async function payloadSignature(payload) {
    const hash = await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(payload)));
    return [...new Uint8Array(hash)].map(byte=>byte.toString(16).padStart(2,'0')).join('');
  }
  function realSourcesReady() {
    if (!state.identity.face || !state.identity.body || !state.references.length || state.references.some(ref=>ref.demo)) {
      toast('실제 얼굴·전신 사진과 무드 레퍼런스를 먼저 추가해주세요. 예시 사진은 테스트 자료로 내보내지 않습니다.'); return false;
    }
    return true;
  }
  async function studioDevPreview() {
    if (devPreviewPending || generationPending || state.jobId) return;
    if (!realSourcesReady()) return;
    devPreviewPending = true;
    if ($('#studio-dev-preview')) $('#studio-dev-preview').disabled = true;
    syncControls();
    try {
      const submitted = generationPayload(); const signature = await payloadSignature(submitted);
      if (!window.MusePrompts) throw new Error('제작자료 기능을 불러오지 못했습니다. 페이지를 새로고침해주세요.');
      const manifest = await window.MusePrompts.buildPreview('editorial', submitted);
      if (manifest.billable !== false || !Array.isArray(manifest.shots) || !Array.isArray(manifest.inputs)) throw new Error('검증 자료 형식이 올바르지 않습니다.');
      if (await payloadSignature(generationPayload()) !== signature) throw new Error('준비하는 동안 모델·시안·방향이 바뀌었습니다. 현재 사진으로 다시 제작자료를 만들어주세요.');
      devPreview = {manifest,signature,aspectRatio:submitted.aspectRatio,plan:structuredClone(submitted.shots)};
      showStudioDevPreview();
    } catch (error) { toast(error.message || '검증 자료를 준비하지 못했습니다.'); }
    finally { devPreviewPending = false; if ($('#studio-dev-preview')) $('#studio-dev-preview').disabled = false; syncControls(); }
  }
  function showStudioDevPreview() {
    const {manifest} = devPreview;
    modal('API 결제 없이 화보 동작 검증',`<p class="dev-notice">① 아래 프롬프트를 복사하고, 번호 순서대로 사진을 ChatGPT에 첨부해 이미지를 만드세요. ② 결과를 내려받아 사이트의 ‘외부에서 만든 화보 가져오기’로 넣으세요.<br><strong>이 자료를 준비하는 과정은 이미지 API를 호출하지 않습니다.</strong> ChatGPT의 이용 플랜·이미지 생성 한도는 적용됩니다. ChatGPT 결과가 연결할 API의 품질과 비용을 보장하지는 않습니다.</p><label for="studio-dev-shot">확인할 컷</label><select id="studio-dev-shot" class="dev-shot-picker">${manifest.shots.map((shot,index)=>`<option value="${index}">SHOT ${String(index+1).padStart(2,'0')} · ${escape(devPreview.plan[index]?.pose || shot.id)}</option>`).join('')}</select><div id="studio-dev-sources" class="dev-source-grid"></div><label for="studio-dev-prompt">실제 API 요청과 같은 프롬프트</label><textarea readonly id="studio-dev-prompt"></textarea><p class="dialog-note">테스트 자료 파일에는 원본 사진이 포함됩니다. 실제 화보 품질은 직접 생성한 결과의 얼굴·체형·손·의상 디테일을 확인해주세요.</p><div class="dialog-actions"><button id="studio-dev-copy">프롬프트 복사</button><button id="studio-dev-export">원본 포함 테스트 자료 저장</button></div>`);
    const renderShot = () => {
      const shot = manifest.shots[Number($('#studio-dev-shot').value)];
      $('#studio-dev-prompt').value = shot.prompt;
      const sources = shot.inputIds.map(id=>manifest.inputs.find(input=>input.id===id)).filter(Boolean);
      $('#studio-dev-sources').innerHTML = sources.map((input,index)=>`<article class="dev-source-card"><img src="${escape(input.dataUrl)}" alt="첨부 ${index+1}: ${escape(input.role)}"><strong>첨부 ${index+1} · ${escape(input.role)}</strong><small>${escape(input.name)}</small><button data-dev-download="${escape(input.id)}">이 사진 저장 ↓</button></article>`).join('');
    };
    renderShot(); $('#studio-dev-shot').addEventListener('change',renderShot);
    $('#studio-dev-sources').addEventListener('click',event=>{
      const button=event.target.closest('[data-dev-download]');if(!button)return;
      const input=manifest.inputs.find(item=>item.id===button.dataset.devDownload);if(!input)return;
      const shot=manifest.shots[Number($('#studio-dev-shot').value)], index=shot.inputIds.indexOf(input.id)+1;
      download(input.dataUrl,`attach-${String(index).padStart(2,'0')}-${input.role.replace(/[^a-z0-9-]/gi,'_')}.${input.dataUrl.startsWith('data:image/png')?'png':input.dataUrl.startsWith('data:image/webp')?'webp':'jpg'}`);
    });
    $('#studio-dev-copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('#studio-dev-prompt').value);toast('프롬프트를 복사했어요. 사진도 표시된 순서대로 첨부해주세요.');}catch{$('#studio-dev-prompt').focus();$('#studio-dev-prompt').select();toast('선택한 프롬프트를 복사해주세요.');}});
    $('#studio-dev-export').addEventListener('click',()=>download(new Blob([JSON.stringify({...manifest,format:'muse-development-kit-v1',createdAt:new Date().toISOString()},null,2)],{type:'application/json'}),'muse-development-kit.json'));
  }
  async function importStudioResults(files) {
    if (!files.length) return;
    if (state.jobId || generationPending) {toast('진행 중인 생성이 끝나거나 취소된 후 가져와주세요.');return;}
    if (!devPreview) {toast('먼저 현재 모델과 시안으로 ChatGPT 테스트 자료를 꺼내주세요.');return;}
    const preview = devPreview;
    try {
      if (await payloadSignature(generationPayload()) !== preview.signature) throw new Error('모델·시안·방향이 변경됐어요. 현재 설정으로 테스트 자료를 다시 꺼내주세요.');
      if (files.length>preview.plan.length) throw new Error(`현재 촬영 플랜에는 ${preview.plan.length}컷까지만 가져올 수 있습니다.`);
      const imported = await Promise.all(files.map(async file=>({name:file.name,dataUrl:await readImage(file)})));
      if (await payloadSignature(generationPayload()) !== preview.signature) throw new Error('사진을 읽는 동안 설정이 바뀌었습니다. 다시 확인해주세요.');
      const available=preview.plan.map((shot,index)=>({shot,index})).filter(({shot})=>!state.shots.some(existing=>existing.id===shot.id&&existing.dataUrl));
      const order=[...available,...preview.plan.map((shot,index)=>({shot,index})).filter(item=>!available.some(a=>a.index===item.index))];
      modal('외부에서 만든 화보 가져오기',`<p class="dev-notice">현재 모델·시안의 프롬프트와 참조 사진으로 직접 만든 결과를 선택해주세요. 파일은 고른 컷에 연결되고 <strong>외부 생성 · 수동 검증</strong>으로 표시됩니다. 이 사이트에서 생성하거나 얼굴 일치를 자동 검증한 결과가 아닙니다.</p><div class="dev-import-list">${imported.map((item,index)=>`<div class="dev-import-row"><img src="${escape(item.dataUrl)}" alt="가져올 결과 ${index+1}"><span>${escape(item.name)}</span><select data-import-index="${index}" aria-label="${escape(item.name)}에 연결할 컷">${preview.plan.map((shot,i)=>`<option value="${i}" ${order[index].index===i?'selected':''}>SHOT ${String(i+1).padStart(2,'0')} · ${escape(shot.pose)}</option>`).join('')}</select></div>`).join('')}</div><label class="dev-confirm-check"><input id="studio-manual-confirm" type="checkbox">현재 모델과 시안으로 만든 결과이며, 원본과 얼굴·체형을 직접 확인할 이미지임을 확인합니다.</label><div class="dialog-actions"><button id="studio-manual-back">돌아가기</button><button id="studio-manual-import-confirm" disabled>선택한 컷으로 가져오기</button></div>`);
      $('#studio-manual-confirm').addEventListener('change',event=>{$('#studio-manual-import-confirm').disabled=!event.target.checked;});
      $('#studio-manual-back').addEventListener('click',closeModal);
      $('#studio-manual-import-confirm').addEventListener('click',async()=>{
        const button=$('#studio-manual-import-confirm');button.disabled=true;
        try {
          if (state.jobId || generationPending || await payloadSignature(generationPayload())!==preview.signature) throw new Error('현재 촬영 설정이 바뀌었습니다. 테스트 자료부터 다시 확인해주세요.');
          const mapping=$$('[data-import-index]').map(select=>Number(select.value));
          if(new Set(mapping).size!==mapping.length)throw new Error('같은 컷을 중복 선택하지 말아주세요.');
          const previous=state.manualSignature===preview.signature?state.shots:[];
          const merged=preview.plan.map(shot=>previous.find(item=>item.id===shot.id)||{...shot,status:'manual-pending',origin:'manual'});
          state.jobAspectRatio=preview.aspectRatio;
          for(let index=0;index<imported.length;index++){
            const target=mapping[index];outputCache.delete(merged[target].id);
            merged[target]=await normalizeOutput({...merged[target],status:'completed',dataUrl:imported[index].dataUrl,origin:'manual',sourceFingerprint:preview.manifest.sourceFingerprint,originalFilename:imported[index].name});
          }
          if (state.jobId || generationPending || await payloadSignature(generationPayload())!==preview.signature) throw new Error('이미지를 처리하는 동안 모델이나 촬영 설정이 바뀌었습니다. 다시 가져와주세요.');
          state.shots=merged;state.manualSignature=preview.signature;state.filterFavorites=false;
          $$('[data-results-filter]').forEach(b=>{const active=b.dataset.resultsFilter==='all';b.classList.toggle('active',active);b.classList.toggle('is-active',active);b.setAttribute('aria-pressed',String(active));});
          closeModal();setView('results');toast(`${imported.length}장을 수동 검증 결과로 가져왔어요. 이미지 API는 호출하지 않았습니다.`);
        }catch(error){toast(error.message);button.disabled=false;}
      });
    } catch(error){toast(error.message||'이미지를 가져오지 못했습니다.');}
  }
  $('#studio-dev-preview')?.addEventListener('click',studioDevPreview);
  $('#studio-manual-import-button')?.addEventListener('click',()=>$('#studio-manual-import')?.click());
  $('#studio-manual-import')?.addEventListener('change',event=>{importStudioResults([...event.target.files]);event.target.value='';});
  $('#dev-test-button')?.addEventListener('click',()=>{
    modal('결제 전 개발 검증',`<p class="dev-notice">최종 화보를 목표로, API 비용 없이 사이트 동작과 이미지 제작 조건을 나누어 확인합니다. 모의 테스트의 통과는 실제 사진 품질을 보장하지 않습니다.</p><ol><li>기준 얼굴·전신과 시안을 올립니다.</li><li>테스트 자료에서 프롬프트와 번호 순서의 참조 사진을 꺼냅니다.</li><li>사용 중인 ChatGPT에서 이미지를 생성합니다. 플랜과 생성 한도가 적용됩니다.</li><li>그 결과를 사이트에 가져와 기준 시트 승인·10컷 갤러리·다운로드를 확인합니다.</li></ol><p>ChatGPT와 실제 API의 모델·처리가 다를 수 있어, 최종 API 연결 시에는 적은 수의 실제 생성으로 품질·비용을 따로 확인해야 합니다.</p><div class="dialog-actions"><button id="dev-open-model">모델 기준 검증</button><button id="dev-open-studio">화보 검증</button></div>`);
    $('#dev-open-model').addEventListener('click',()=>{closeModal();setView('model');$('#model-dev-preview')?.scrollIntoView({block:'center'});});
    $('#dev-open-studio').addEventListener('click',()=>{closeModal();setView('board');$('#studio-dev-preview')?.scrollIntoView({block:'center'});});
  });

  function updateModelBadge() {
    const badge = $('#active-model-name');
    if (badge) badge.textContent = state.identityProfile ? `${state.identityProfile.name || '나의 모델'} · ${state.identitySheet ? '승인 기준 시트' : '원본 기준'}` : '모델 기준 시트 만들기';
  }
  window.addEventListener('muse:model-approved', event => {
    const payload = event.detail;
    if (!payload?.identity?.face?.dataUrl || !payload?.identity?.body?.dataUrl) return;
    state.identity = structuredClone(payload.identity);
    state.identityProfile = structuredClone(payload.identityProfile || null);
    state.identitySheet = payload.identitySheet ? structuredClone(payload.identitySheet) : null;
    state.supportingPhotos = structuredClone(payload.supportingPhotos || []);
    for (const slot of ['face', 'body']) {
      const preview = $(`#${slot}-preview`); if (preview) { preview.src = state.identity[slot].dataUrl; preview.alt = `${state.identityProfile?.name || '선택한 모델'} ${slot === 'face' ? '기준 얼굴' : '전신 원본'}`; }
      const card = $(`label[for="${slot}-upload"]`); if (card && $('.photo-tag', card)) $('.photo-tag', card).textContent = '기준 원본';
    }
    updateModelBadge();
    if (payload.navigate !== false) { setView('board'); toast('모델 기준을 적용했어요. 이제 무드 레퍼런스를 추가해주세요.'); }
  });
  window.addEventListener('muse:model-changed', event => {
    if (!state.identityProfile) return;
    state.identityProfile = null; state.identitySheet = null; state.supportingPhotos = [];
    state.identity = { face:null, body:null };
    for (const [slot, file] of [['face','portrait.jpg'], ['body','editorial.jpg']]) {
      const preview = $(`#${slot}-preview`); if (preview) { preview.src = assets + file; preview.alt = `${slot === 'face' ? '얼굴' : '전신'} 사진 예시`; }
      const card = $(`label[for="${slot}-upload"]`); if (card && $('.photo-tag', card)) $('.photo-tag', card).textContent = '예시';
    }
    updateModelBadge();
  });
  window.addEventListener('muse:navigate', event => { if (['model','board','results'].includes(event.detail?.view)) setView(event.detail.view); });
  // Model inputs never persist in localStorage. Only non-image direction settings do.
  applyPreferences(); renderReferences();
  if (state.mode === 'wedding' && $('#stage-main')) $('#stage-main').src = assets + 'bridal.jpg';
  addLayer({ id: 'demo-portrait', name: 'BEAUTY DIRECTION', url: assets + 'portrait.jpg' }, { x: 77, y: 29, scale: 24, rotation: 7, demo: true });
  state.selectedLayer = null; renderLayers(); setView('model'); checkConnection();
  window.EditorialStudio = { buildPlan, snapshot: () => ({ mode: state.mode, aspectRatio: state.aspectRatio, referenceCount: state.references.length, layerCount: state.layers.length, configured: state.configured, hasFace: !!state.identity.face, hasBody: !!state.identity.body, modelId: state.identityProfile?.id || null, sheetApproved: !!state.identitySheet }) };
})();
