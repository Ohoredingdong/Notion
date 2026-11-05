(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const uid = () => crypto.randomUUID?.() || `model-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const fields = {name:'model-name',hair:'model-hair',eyes:'model-eyes',skin:'model-skin',bodyNotes:'model-body-notes',notes:'model-notes'};
  const roles = {face:'기준 정면 얼굴',body:'전신 · 정면',side:'측면',back:'후면',extra:'보조 사진'};
  const expressions = ['중립','옅은 미소','환한 미소','차분함','진지함','호기심','놀람','눈을 감은 평온함'];
  const assets = './assets/editorial-studio/';
  const defaultCrops = {eyes:{x:.12,y:.23,w:.76,h:.18},mouth:{x:.25,y:.51,w:.5,h:.17},skin:{x:.26,y:.39,w:.28,h:.19}};
  const fresh = () => ({profile:{id:uid(),name:'나의 모델',hair:'',eyes:'',skin:'',bodyNotes:'',notes:''},photos:[],revision:1,sheet:null,cropSettings:structuredClone(defaultCrops)});
  let state = fresh();
  let details = {};
  let previewManifest = null, previewPending = false;
  let uploadingPhotos = false, uploadFeedback = '';
  let palette = ['#d7c7b5','#a58f79','#746755','#3c3933','#ede8df'];
  let jobId = null, jobRevision = null, jobEpoch = null, sourceEpoch = 0, polling = null, pending = false, ready = false;
  let db = null, storageBroken = false, saveQueue = Promise.resolve(), toastTimer, deriveToken = 0;
  const front = () => state.photos.find(photo => photo.role === 'face' && photo.primary);
  const body = () => state.photos.find(photo => photo.role === 'body');

  function toast(message) {
    const el = $('#toast');
    if (!el) return;
    clearTimeout(toastTimer); el.textContent = message; el.hidden = false; el.classList.add('is-visible');
    toastTimer = setTimeout(() => { el.hidden = true; el.classList.remove('is-visible'); }, 5200);
  }
  function status(message) { if ($('#model-generation-status')) $('#model-generation-status').textContent = message; }
  function storageStatus(message) { if ($('#model-storage-status')) $('#model-storage-status').textContent = message; }
  function modal(title, content) {
    const dialog = $('#model-dialog'); if (!dialog) return;
    $('#model-dialog-title').textContent = title;
    $('#model-dialog-content').innerHTML = content;
    if (!dialog.open) dialog.showModal();
  }
  const closeModal = () => $('#model-dialog')?.close();
  function activeSheet() { return state.sheet?.approved && state.sheet.sourceRevision === state.revision; }
  function changed(reason, {derive = false} = {}) {
    const hadSheet = !!state.sheet;
    state.revision++; sourceEpoch++; state.sheet = null;
    window.dispatchEvent(new CustomEvent('muse:model-changed', {detail:{id:state.profile.id,revision:state.revision,reason}}));
    persist(); render();
    if (derive) derivePhotos();
    if (hadSheet) toast('기준 정보가 바뀌어 이전 시트 승인을 해제했어요. 변경된 사진으로 다시 확인해주세요.');
  }
  function payload(navigate = true) {
    const f = front(), b = body(); if (!f || !b) return null;
    return {
      navigate,
      identity:{face:{name:f.name,dataUrl:f.dataUrl},body:{name:b.name,dataUrl:b.dataUrl}},
      identityProfile:{...state.profile,revision:state.revision,sheetApproved:!!activeSheet(),sheetOrigin:activeSheet()?state.sheet.origin||'unknown':undefined},
      identitySheet:activeSheet() ? {name:`${state.profile.name} 기준 시트`,dataUrl:state.sheet.dataUrl,origin:state.sheet.origin||'unknown'} : undefined,
      supportingPhotos:state.photos.filter(photo => photo.id !== f.id && photo.id !== b.id).map(({id,role,name,dataUrl}) => ({id,role,name,dataUrl}))
    };
  }
  function useModel(navigate = true) {
    if (uploadingPhotos) { toast('사진을 읽는 중입니다. 업로드가 끝나면 다음 단계로 이동할 수 있어요.'); return; }
    const data = payload(navigate);
    if (!data) {
      toast(!front() && !body() ? '기준 얼굴과 전신 사진이 필요합니다. 사진을 추가한 뒤 역할을 확인해주세요.' : !body() ? '전신 사진이 필요합니다. 두 번째 사진을 추가하거나 사진 역할을 전신으로 지정해주세요.' : '기준 얼굴이 필요합니다. 사진 역할을 기준 정면 얼굴로 지정해주세요.');
      $('#model-next-status')?.scrollIntoView({block:'nearest',behavior:'smooth'});
      $('#model-add-required-photo')?.focus({preventScroll:true});
      return;
    }
    window.dispatchEvent(new CustomEvent('muse:model-approved', {detail:data}));
    if (navigate) toast(activeSheet() ? '승인한 기준 시트를 화보 촬영에 연결했어요.' : '원본 모델 사진을 화보 촬영에 연결했어요. 아직 승인한 AI 기준 시트는 없습니다.');
  }

  async function initStorage() {
    try {
      db = await new Promise((resolve,reject) => {
        const request = indexedDB.open('muse-model-library-v1',1);
        request.onupgradeneeded = () => request.result.createObjectStore('profiles');
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
        request.onblocked = () => reject(new Error('storage blocked'));
      });
      db.onversionchange = () => { db.close(); db = null; storageBroken = true; storageStatus('다른 탭의 저장소 변경 · 파일로 백업해주세요'); };
      const saved = await new Promise((resolve,reject) => {
        const request = db.transaction('profiles').objectStore('profiles').get('current');
        request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
      });
      if (saved) { const restored = validateKit(saved); await validateSources(restored); state = restored; }
      storageStatus(saved ? '이 기기에 저장한 모델을 불러왔어요' : '모델 사진은 이 브라우저에 자동 저장됩니다');
    } catch {
      storageBroken = true;
      storageStatus('자동 저장 불가 · 모델 파일로 내려받아 보관해주세요');
    }
    ready = true; fillFields(); render(); await derivePhotos();
    if (activeSheet()) useModel(false);
  }
  let saveRequested = false, saveRunning = false;
  function persist() {
    if (!db || storageBroken) return Promise.resolve(false);
    saveRequested = true;
    if (saveRunning) return saveQueue;
    saveRunning = true;
    saveQueue = (async () => {
      let saved = false;
      while (saveRequested && db && !storageBroken) {
        saveRequested = false;
        const snapshot = structuredClone(state);
        saved = await new Promise(resolve => {
          try {
            const transaction = db.transaction('profiles','readwrite');
            transaction.objectStore('profiles').put(snapshot,'current');
            transaction.oncomplete = () => { storageStatus('이 기기에 저장됨 · 사진은 서버로 자동 전송되지 않아요'); resolve(true); };
            transaction.onerror = transaction.onabort = () => { storageBroken = true; storageStatus('저장 공간을 확인하고 모델 파일로 백업해주세요'); resolve(false); };
          } catch { storageBroken = true; storageStatus('자동 저장 불가 · 모델 파일로 백업해주세요'); resolve(false); }
        });
      }
      saveRunning = false;
      return saved;
    })();
    return saveQueue;
  }
  function validImage(dataUrl, max = 14 * 1024 * 1024) {
    return typeof dataUrl === 'string' && dataUrl.length < max && /^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(dataUrl);
  }
  function validateKit(input) {
    const kit = input?.format === 'muse-model-kit-v1' ? input.model : input;
    if (!kit || typeof kit !== 'object' || !Array.isArray(kit.photos) || kit.photos.length > 10 || !kit.profile || typeof kit.profile !== 'object') throw new Error('MUSE 모델 파일 형식이 아닙니다.');
    const profile = {id:String(kit.profile.id || uid()).slice(0,100)};
    for (const key of Object.keys(fields)) profile[key] = String(kit.profile[key] || '').slice(0,key === 'notes' ? 3000 : key === 'bodyNotes' ? 1000 : key === 'name' ? 100 : 500);
    const ids = new Set(); let total = 0;
    const photos = kit.photos.map(photo => {
      if (!photo || !roles[photo.role] || !validImage(photo.dataUrl,8*1024*1024) || ids.has(photo.id) || typeof photo.id !== 'string' || !photo.id || photo.id.length > 100) throw new Error('모델 사진 정보가 올바르지 않습니다.');
      ids.add(photo.id); total += photo.dataUrl.length;
      return {id:photo.id.slice(0,100),name:String(photo.name || '모델 사진').slice(0,100),role:photo.role,primary:photo.role === 'face' && photo.primary === true,dataUrl:photo.dataUrl};
    });
    if (total > 45*1024*1024 || photos.filter(photo => photo.primary).length > 1) throw new Error('모델 파일 용량 또는 기준 얼굴 정보를 확인해주세요.');
    if (photos.some(photo => photo.role === 'face') && !photos.some(photo => photo.primary)) photos.find(photo => photo.role === 'face').primary = true;
    const revision = Number.isSafeInteger(kit.revision) && kit.revision > 0 ? kit.revision : 1;
    let sheet = null;
    if (kit.sheet) {
      if (!validImage(kit.sheet.dataUrl,18*1024*1024)) throw new Error('기준 시트 이미지가 올바르지 않습니다.');
      const provenance=kit.sheet.provenance && typeof kit.sheet.provenance==='object' ? kit.sheet.provenance : {};
      sheet = {dataUrl:kit.sheet.dataUrl,sourceRevision:Number(kit.sheet.sourceRevision),approved:kit.sheet.approved === true && Number(kit.sheet.sourceRevision) === revision,createdAt:String(kit.sheet.createdAt || ''),origin:['manual','api'].includes(kit.sheet.origin)?kit.sheet.origin:'unknown',provenance:{profileId:String(provenance.profileId||profile.id).slice(0,100),profileRevision:Number.isSafeInteger(provenance.profileRevision)?provenance.profileRevision:revision,sourceFingerprint:/^[a-f0-9]{64}$/.test(provenance.sourceFingerprint||'')?provenance.sourceFingerprint:'',sourcePhotoIds:Array.isArray(provenance.sourcePhotoIds)?provenance.sourcePhotoIds.filter(id=>typeof id==='string').slice(0,10).map(id=>id.slice(0,100)):[],confirmation:provenance.confirmation==='user-confirmed-current-sources'?'user-confirmed-current-sources':'',filename:String(provenance.filename||'').slice(0,120)}};
      if (sheet.approved && (!photos.find(photo => photo.primary) || !photos.find(photo => photo.role === 'body'))) throw new Error('승인 시트의 기준 원본 사진이 없습니다.');
    }
    const cropSettings = structuredClone(defaultCrops);
    for (const key of Object.keys(cropSettings)) for (const axis of ['x','y','w','h']) {
      const value = Number(kit.cropSettings?.[key]?.[axis]);
      if (Number.isFinite(value) && value >= 0 && value <= 1) cropSettings[key][axis] = value;
    }
    return {profile,photos,revision,sheet,cropSettings};
  }
  async function validateSources(kit) {
    for (const source of [...kit.photos.map(photo => photo.dataUrl), ...(kit.sheet ? [kit.sheet.dataUrl] : [])]) {
      try { const image = await imageElement(source); if (!image.naturalWidth || !image.naturalHeight || image.naturalWidth * image.naturalHeight > 50000000) throw new Error(); image.src = ''; }
      catch { throw new Error('모델 파일에 손상되었거나 지원하지 않는 사진이 있습니다. 현재 작업은 유지됩니다.'); }
    }
  }
  async function fileImage(file) {
    if (!window.MuseImages) throw new Error('사진 업로드 기능을 불러오지 못했습니다. 새로고침해주세요.');
    return window.MuseImages.read(file);
  }
  async function addPhotos(files) {
    if (!ready) { toast('저장한 모델을 불러오는 중입니다. 잠시 기다려주세요.'); return; }
    if (uploadingPhotos) { toast('현재 사진을 읽는 중입니다. 완료 후 추가해주세요.'); return; }
    if (!files.length) return;
    uploadingPhotos = true;
    let added = 0;
    const failures = [];
    render();
    for (const file of files) {
      if (state.photos.length >= 10) { failures.push('모델 사진은 최대 10장입니다.'); break; }
      uploadFeedback = `${file.name} 읽는 중… 큰 사진은 작업용 사본으로 자동 조절합니다.`;
      if ($('#model-upload-status')) $('#model-upload-status').textContent = uploadFeedback;
      try {
        const dataUrl = await fileImage(file);
        const role = !front() ? 'face' : !body() ? 'body' : 'extra';
        state.photos.push({id:uid(),name:file.name,role,primary:role === 'face',dataUrl}); added++;
        render();
      } catch (error) { failures.push(`${file.name}: ${error.message || '사진을 읽지 못했습니다.'}`); }
    }
    uploadingPhotos = false;
    uploadFeedback = [added ? `${added}장 추가 완료. 기기의 원본 파일은 바꾸지 않았어요.` : '', ...failures].filter(Boolean).join(' ');
    if (added) changed('photos-added',{derive:true}); else render();
    if (uploadFeedback) toast(uploadFeedback);
  }
  function rolePhoto(id,role) {
    const photo = state.photos.find(photo => photo.id === id); if (!photo || !roles[role]) return;
    if (role === 'face' || role === 'body') state.photos.forEach(item => { if (item.role === role) {item.role = 'extra';item.primary = false;} });
    photo.role = role; photo.primary = role === 'face';
    changed('photo-role',{derive:true});
  }
  function fillFields() { for (const [key,id] of Object.entries(fields)) if ($('#'+id)) $('#'+id).value = state.profile[key]; }
  function renderLibrary() {
    const root = $('#model-photo-list'); if (!root) return;
    if ($('#model-photo-count')) $('#model-photo-count').textContent = `${state.photos.length}/10`;
    root.innerHTML = state.photos.length ? state.photos.map((photo,index) => `<article class="model-photo-card ${photo.primary ? 'is-primary' : ''}" data-photo-id="${escape(photo.id)}"><img src="${escape(photo.dataUrl)}" alt="${escape(photo.name)}"><div class="model-photo-info"><strong>${escape(photo.name)}</strong><small>${photo.primary ? 'IDENTITY ANCHOR · 기준 얼굴' : `SOURCE ${String(index+1).padStart(2,'0')}`}</small><label class="model-role-label">사진 역할<select data-model-role="${escape(photo.id)}" aria-label="${escape(photo.name)} 사진 역할">${Object.entries(roles).map(([role,label]) => `<option value="${role}" ${photo.role === role ? 'selected' : ''}>${label}</option>`).join('')}</select></label></div><div class="model-photo-controls"><button data-model-action="primary" data-id="${escape(photo.id)}" ${photo.primary ? 'disabled' : ''} title="이 사진을 기준 얼굴로 지정">${photo.primary ? '기준' : '기준 얼굴로'}</button><button data-model-action="up" data-id="${escape(photo.id)}" ${index === 0 ? 'disabled' : ''} aria-label="${escape(photo.name)} 앞으로 이동">↑</button><button data-model-action="remove" data-id="${escape(photo.id)}" aria-label="${escape(photo.name)} 삭제">×</button></div></article>`).join('') : '<div class="model-library-empty"><span>01 — 10</span><p>같은 모델의 사진을 여러 장 모아주세요.<br>정면 얼굴과 전신이 기준이 됩니다.</p></div>';
  }
  function viewCell(photo,label,description) {
    return `<figure class="model-view-cell ${photo ? 'has-photo' : 'is-missing'}">${photo ? `<img src="${escape(photo.dataUrl)}" alt="${label} 원본 사진">` : `<div class="model-board-placeholder"><span>＋</span><p>${description}</p></div>`}<figcaption>${label}<small>${photo ? '업로드한 원본' : '사진 없음 · 생성 시 추정 영역'}</small></figcaption></figure>`;
  }
  function renderBoard() {
    const root = $('#model-board'); if (!root) return;
    const demo = !state.photos.length;
    const f = front(), b = body();
    const faceUrl = f?.dataUrl || (demo ? assets+'portrait.jpg' : '');
    const viewBody = b || (demo ? {dataUrl:assets+'editorial.jpg'} : null);
    const side = state.photos.find(photo => photo.role === 'side'), back = state.photos.find(photo => photo.role === 'back');
    root.innerHTML = `<header class="model-board-header"><div><span>IDENTITY REFERENCE / ${demo ? 'EXAMPLE' : 'SOURCE PHOTOS'}</span><h3>${escape(demo ? 'The quiet muse' : state.profile.name || '나의 모델')}</h3></div><div class="model-board-id">M—${String(state.revision).padStart(2,'0')}<small>${demo ? '예시 사진 · 기준 시트 구성' : '원본 정리 보드 · AI 생성 전'}</small></div></header><div class="model-board-content"><section class="model-front-anchor"><div class="model-board-section-title"><span>01</span><h4>기준 얼굴</h4><small>IDENTITY FIRST</small></div>${faceUrl ? `<img src="${escape(faceUrl)}" alt="${demo ? '예시 정면 얼굴' : '모든 뷰의 기준이 되는 원본 얼굴'}">` : '<div class="model-board-placeholder"><span>＋</span><p>기준 정면 얼굴을 지정해주세요</p></div>'}<div class="model-anchor-caption"><span>${demo ? 'EXAMPLE PHOTO' : f ? 'PRIMARY FACE · 원본 기준' : 'NO FACE SELECTED'}</span><p>눈·코·입 위치와 얼굴형의 기준.<br>다른 뷰에서 새 얼굴을 만들지 않아요.</p></div></section><div class="model-board-sections"><section class="model-threeviews-section"><div class="model-board-section-title"><span>02</span><h4>3면 뷰</h4><small>FRONT / SIDE / BACK</small></div><div class="model-threeviews">${viewCell(viewBody,'정면','전신 정면 사진 추가')}${viewCell(side,'측면','측면 사진 추가 권장')}${viewCell(back,'후면','후면 사진 추가 권장')}</div><p class="model-board-footnote">${demo ? '예시 전신 사진입니다. 측면·후면은 실제 사진을 추가하면 표시돼요.' : '원본 사진의 구도는 서로 다를 수 있어요. AI 시트는 동일 축척의 3면 뷰를 요청합니다.'}</p></section><section class="model-expression-section"><div class="model-board-section-title"><span>03</span><h4>표정 8가지</h4><small>STRUCTURE UNCHANGED</small></div><div class="model-expressions">${expressions.map((name,index) => `<div class="model-expression"><span>${String(index+1).padStart(2,'0')}</span><i aria-hidden="true">${index === 0 ? '−' : index === 1 || index === 2 ? '⌣' : '·'}</i><strong>${name}</strong><small>생성할 표정</small></div>`).join('')}</div></section><section class="model-detail-section"><div class="model-board-section-title"><span>04</span><h4>얼굴 디테일</h4><small>ORIGINAL PHOTO CROPS</small></div><div class="model-details">${[['eyes','눈'],['mouth','입'],['skin','피부']].map(([key,label]) => `<button class="model-detail" data-model-crop="${key}" ${!f ? 'disabled' : ''}>${details[key] ? `<img src="${details[key]}" alt="원본 얼굴 사진의 ${label} 참고 영역">` : '<span class="model-detail-empty">원본 영역</span>'}<span>${label}<small>${f ? '영역 조절 ↗' : '기준 얼굴 추가'}</small></span></button>`).join('')}</div><p class="model-board-footnote">얼굴을 자동 분석한 수치가 아닌, 기준 사진에서 위치를 직접 조절할 수 있는 참고 영역입니다.</p></section><section class="model-palette-section"><div class="model-board-section-title"><span>05</span><h4>컬러 팔레트</h4><small>${f ? 'PHOTO SAMPLE' : 'EXAMPLE COLORS'}</small></div><div class="model-colors">${palette.map(color => `<div class="model-color"><i style="background:${color}"></i><span>${color.toUpperCase()}</span></div>`).join('')}</div><p class="model-board-footnote">${f ? '원본 사진의 주요 색상입니다. 피부·눈 색을 자동 판정하지 않습니다.' : '예시 색상 · 사진을 추가하면 원본에서 추출합니다.'}</p></section></div></div><footer class="model-board-footer">FACE CONSISTENCY → THREE VIEWS → EXPRESSION → LAYOUT<span>${demo ? 'DEMO / NOT AN AI RESULT' : 'SOURCE BOARD / NOT AN AI RESULT'}</span></footer>`;
  }
  function renderGenerated() {
    const root = $('#model-generated-preview'); if (!root) return;
    const sheet = state.sheet;
    root.hidden = !sheet;
    if (!sheet) { root.innerHTML=''; return; }
    root.innerHTML = `<div class="model-result-heading"><div><span>${sheet.origin==='manual'?'EXTERNAL RESULT / MANUAL REVIEW':sheet.origin==='api'?'API REFERENCE SHEET':'REFERENCE SHEET / SOURCE UNVERIFIED'}</span><h3>${sheet.approved ? '승인한 모델 기준 시트' : '생성 결과를 기준 얼굴과 비교해주세요'}</h3><p>${sheet.approved ? '이 시트와 원본 사진을 함께 다음 화보에 참조합니다.' : '정면·측면의 얼굴 구조, 머리 모양, 전신 비율을 확인한 후 승인해주세요.'}</p></div><strong class="model-approved-label">${sheet.approved ? 'APPROVED' : '검토 대기'}</strong></div><div class="model-generated-comparison"><figure><img src="${escape(front()?.dataUrl || '')}" alt="비교용 원본 기준 얼굴"><figcaption>원본 기준 얼굴</figcaption></figure><button type="button" class="model-sheet-image" data-model-action="zoom-sheet" aria-label="생성한 기준 시트 확대"><img src="${escape(sheet.dataUrl)}" alt="생성한 모델 기준 시트, 승인 전 원본과 비교 필요"></button></div><p class="model-result-origin">${sheet.origin==='manual'?'외부 생성 · 수동 검토 — 사이트 API의 생성 결과가 아닙니다.':sheet.origin==='api'?'연결한 이미지 API에서 생성한 결과입니다.':'이전에 저장한 시트입니다. 생성 경로는 확인되지 않았습니다.'}</p><p class="model-result-note">AI 생성 결과는 얼굴·비율의 완전한 고정을 보장하지 않습니다. 확인한 시트만 이후 촬영에 사용하세요.</p><div class="model-result-actions"><button data-model-action="download-sheet">시트 이미지 저장 ↓</button><button data-model-action="approve-sheet" ${sheet.approved ? 'disabled' : ''}>${sheet.approved ? '승인 완료' : '얼굴과 비율 확인 · 이 시트 승인'}</button></div>`;
  }
  function render() {
    renderLibrary(); renderBoard(); renderGenerated();
    const hasAnchors = !!front() && !!body();
    if ($('#model-upload-status')) $('#model-upload-status').textContent = uploadFeedback || '장당 50MB까지 · 작업용 사본을 자동 조절하며 원본 파일은 유지합니다.';
    if ($('#model-next-status')) $('#model-next-status').textContent = uploadingPhotos ? '사진을 읽는 중입니다…' : hasAnchors ? '얼굴·전신 준비 완료. 다음 단계에서 시안을 추가하세요.' : !state.photos.length ? '얼굴과 전신 사진을 올려주세요. 측면·후면은 선택입니다.' : !body() ? '다음 단계에는 전신 사진이 필요해요. 사진을 추가하거나 역할을 전신으로 지정해주세요.' : '다음 단계에는 기준 정면 얼굴이 필요해요. 사진 역할을 확인해주세요.';
    if ($('#model-next-button')) $('#model-next-button').disabled = uploadingPhotos;
    if ($('#model-add-required-photo')) { $('#model-add-required-photo').hidden = hasAnchors || uploadingPhotos; $('#model-add-required-photo').textContent = !state.photos.length ? '얼굴·전신 사진 추가' : !body() ? '전신 사진 추가' : '기준 얼굴 사진 추가'; }
    if ($('#model-photos-upload')) $('#model-photos-upload').disabled = uploadingPhotos;
    if ($('#model-clear')) $('#model-clear').disabled = uploadingPhotos;
    if ($('#model-kit-import-button')) $('#model-kit-import-button').disabled = uploadingPhotos;
    if ($('#model-kit-import')) $('#model-kit-import').disabled = uploadingPhotos;
    if ($('#model-sheet-generate')) {
      $('#model-sheet-generate').disabled = !hasAnchors || uploadingPhotos || !!jobId || pending || previewPending;
      $('#model-sheet-generate > span').textContent = window.EditorialStudio?.snapshot().configured ? 'AI 기준 시트 만들기' : '기준 시트 제작자료 만들기';
    }
    if ($('#model-use-photos')) { $('#model-use-photos').disabled=uploadingPhotos; $('#model-use-photos').textContent = activeSheet() ? '이 모델로 화보 만들기 →' : '원본 사진으로 화보 기획 →'; }
    if ($('#model-sheet-approve')) { $('#model-sheet-approve').disabled = !state.sheet || activeSheet() || state.sheet.sourceRevision !== state.revision; $('#model-sheet-approve').hidden = !state.sheet || activeSheet(); }
    if ($('#model-sheet-cancel')) $('#model-sheet-cancel').hidden = !jobId;
    if ($('#model-kit-export')) $('#model-kit-export').disabled = !state.photos.length || uploadingPhotos;
    if ($('#model-board-export')) $('#model-board-export').disabled = !front() || uploadingPhotos;
    if ($('#model-dev-preview')) $('#model-dev-preview').disabled=!hasAnchors || uploadingPhotos || !!jobId || pending || previewPending;
    if ($('#model-sheet-import-button')) $('#model-sheet-import-button').disabled=!hasAnchors || uploadingPhotos || !!jobId || pending;
    if (!jobId && !pending) status(activeSheet() ? '기준 시트 승인됨 · 이후 촬영에 사용 가능' : state.sheet ? '생성 시트 검토 대기' : hasAnchors ? (window.EditorialStudio?.snapshot().configured ? '원본 준비 완료 · AI 기준 시트 생성 가능' : '원본 준비 완료 · 제작자료를 저장할 수 있어요') : '정면 얼굴과 전신 사진을 지정해주세요');
  }
  async function imageElement(source) { const image = new Image(); image.src=source; await image.decode(); return image; }
  async function derivePhotos() {
    const token=++deriveToken, f=front(); details={};
    if (!f) { palette=['#d7c7b5','#a58f79','#746755','#3c3933','#ede8df']; renderBoard(); return; }
    try {
      const image=await imageElement(f.dataUrl); const local={};
      for (const [key,rect] of Object.entries(state.cropSettings)) local[key]=cropImage(image,rect);
      const canvas=document.createElement('canvas');canvas.width=48;canvas.height=48;const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,48,48);
      const pixels=ctx.getImageData(0,0,48,48).data, bins=new Map();
      for(let i=0;i<pixels.length;i+=4) { const values=[pixels[i],pixels[i+1],pixels[i+2]], key=values.map(v=>Math.floor(v/32)).join(','); const bin=bins.get(key)||{n:0,r:0,g:0,b:0};bin.n++;bin.r+=values[0];bin.g+=values[1];bin.b+=values[2];bins.set(key,bin); }
      const colors=[...bins.values()].sort((a,b)=>b.n-a.n).slice(0,5).map(bin=>'#'+[bin.r,bin.g,bin.b].map(v=>Math.round(v/bin.n).toString(16).padStart(2,'0')).join(''));
      if(token===deriveToken) {details=local;palette=colors;renderBoard();}
    } catch { if(token===deriveToken) {details={};renderBoard();} }
  }
  function cropImage(image,rect) {
    const canvas=document.createElement('canvas');
    const x=Math.min(.99,rect.x), y=Math.min(.99,rect.y), w=Math.max(.01,Math.min(rect.w,1-x)),h=Math.max(.01,Math.min(rect.h,1-y));
    const pixelWidth=w*image.naturalWidth,pixelHeight=h*image.naturalHeight,scale=Math.min(380/pixelWidth,240/pixelHeight);
    canvas.width=Math.max(1,Math.round(pixelWidth*scale));canvas.height=Math.max(1,Math.round(pixelHeight*scale));
    canvas.getContext('2d').drawImage(image,x*image.naturalWidth,y*image.naturalHeight,pixelWidth,pixelHeight,0,0,canvas.width,canvas.height);
    return canvas.toDataURL('image/jpeg',.9);
  }
  async function editCrop(key) {
    const photo=front();if(!photo||!defaultCrops[key])return;
    const titles={eyes:'눈',mouth:'입',skin:'피부'};
    modal(`${titles[key]} 원본 영역 조절`,`<p>원본 사진에서 참고할 위치를 직접 골라요. 얼굴 구조를 새로 생성하지 않습니다.</p><div class="model-crop-preview"><img id="model-crop-preview-image" src="${details[key]||photo.dataUrl}" alt="선택한 원본 참고 영역"></div>${[['x','가로 위치'],['y','세로 위치'],['w','가로 범위'],['h','세로 범위']].map(([axis,label])=>`<label>${label}<input id="model-crop-${axis}" type="range" min="${axis==='w'||axis==='h'?1:0}" max="99" value="${Math.round(state.cropSettings[key][axis]*100)}"></label>`).join('')}<div class="model-dialog-actions"><button id="model-crop-done">이 영역으로 저장</button></div>`);
    const image=await imageElement(photo.dataUrl), draft={...state.cropSettings[key]};
    const update=()=>{for(const axis of ['x','y','w','h'])draft[axis]=Number($('#model-crop-'+axis).value)/100;$('#model-crop-preview-image').src=cropImage(image,draft);};
    for(const axis of ['x','y','w','h'])$('#model-crop-'+axis).addEventListener('input',update);
    $('#model-crop-done').addEventListener('click',()=>{state.cropSettings[key]=draft;persist();derivePhotos();closeModal();});
  }

  function sheetSubmission() {
    return {profile:{...state.profile,revision:state.revision},photos:state.photos.map(photo=>({...photo})),expressionCount:8};
  }
  async function devPreview() {
    if (jobId || pending || previewPending) return;
    if (!front() || !body()) { toast('현재 모델의 기준 얼굴과 전신 사진을 먼저 지정해주세요. 예시 사진은 사용하지 않습니다.'); return; }
    const previewRevision=state.revision, previewEpoch=sourceEpoch;
    previewPending=true;render();
    try {
      if (!window.MusePrompts) throw new Error('제작자료 기능을 불러오지 못했습니다. 페이지를 새로고침해주세요.');
      const manifest=await window.MusePrompts.buildPreview('model-sheet',sheetSubmission());
      if (manifest.billable!==false || manifest.kind!=='model-sheet' || !manifest.shots?.[0]?.prompt || !Array.isArray(manifest.inputs) || !Array.isArray(manifest.shots[0].inputIds)) throw new Error('검증 응답 형식이 올바르지 않습니다. 유료 생성은 실행하지 않았습니다.');
      if (previewRevision!==state.revision || previewEpoch!==sourceEpoch) throw new Error('준비 중 모델 원본이 바뀌었습니다. 현재 사진으로 다시 검증 프롬프트를 준비해주세요.');
      const byId=new Map(manifest.inputs.map(input=>[input.id,input]));
      const ordered=manifest.shots[0].inputIds.map(id=>byId.get(id));
      if (ordered.some(input=>!input || !validImage(input.dataUrl,9*1024*1024))) throw new Error('검증용 참조 사진을 확인하지 못했습니다.');
      previewManifest={manifest,revision:previewRevision,epoch:previewEpoch};
      modal('API 결제 없이 기준 시트 검증',`<div class="model-dev-notice"><strong>이 단계에서는 이미지 생성 API를 호출하지 않습니다.</strong><p>아래 사진을 순서대로 ChatGPT에 첨부하고 프롬프트를 붙여 넣으세요. ChatGPT의 이미지 생성 가능 플랜과 사용 한도가 적용됩니다. 별도 API 요금은 없지만 무료·무제한 사용을 뜻하지 않습니다.</p><p>ChatGPT에서 만든 결과는 구도와 얼굴 유지 가능성을 검토하는 데 사용합니다. 사이트에 연결할 API 모델의 실제 품질·속도·비용이 검증되는 것은 아닙니다.</p></div><ol class="model-dev-steps"><li>아래 원본 사진을 내려받아 표시된 순서로 첨부</li><li>프롬프트를 복사해 ChatGPT에 입력</li><li>실제 생성된 시트를 저장하고 ‘외부 결과 불러오기’로 비교·승인</li></ol><div class="model-dev-inputs">${ordered.map((input,index)=>`<figure class="model-dev-input"><img src="${escape(input.dataUrl)}" alt="첨부 ${index+1}: ${escape(input.name)}"><figcaption><strong>이미지 ${index+1}</strong><span>${escape(input.name)}</span><small>${escape(roles[input.role] || input.role)}</small></figcaption><button type="button" data-model-dev-download="${escape(input.id)}">사진 ${index+1} 저장 ↓</button></figure>`).join('')}</div><label class="model-dev-prompt-label" for="model-dev-prompt">실제 API 요청과 같은 생성 프롬프트</label><textarea id="model-dev-prompt" rows="12" readonly>${escape(manifest.shots[0].prompt)}</textarea><p class="model-dev-fingerprint">모델 ${escape(state.profile.name)} · 원본 버전 ${previewRevision} · ${ordered.length}장 참조</p><div class="model-dialog-actions"><button id="model-dev-copy">프롬프트 복사</button><button id="model-dev-export">사진 포함 검증 파일 저장</button><button id="model-dev-close">보드로 돌아가기</button></div>`);
      $('#model-dev-copy').addEventListener('click',async()=>{
        try { await navigator.clipboard.writeText(manifest.shots[0].prompt);toast('프롬프트를 복사했어요. 원본 사진도 함께 첨부해주세요.'); }
        catch { const input=$('#model-dev-prompt');input.focus();input.select();toast('프롬프트를 선택했어요. 복사 단축키로 복사해주세요.'); }
      });
      $('#model-dev-export').addEventListener('click',()=>download(new Blob([JSON.stringify({format:'muse-dev-preview-v1',version:1,exportedAt:new Date().toISOString(),sourceRevision:previewRevision,...manifest},null,2)],{type:'application/json'}),'muse-model-dev-preview.json'));
      $('#model-dev-close').addEventListener('click',closeModal);
      $('#model-dialog-content').querySelectorAll('[data-model-dev-download]').forEach(button=>button.addEventListener('click',()=>{
        const index=ordered.findIndex(input=>input.id===button.dataset.modelDevDownload),input=ordered[index];if(!input)return;
        const extension=input.dataUrl.startsWith('data:image/png')?'png':input.dataUrl.startsWith('data:image/webp')?'webp':'jpg';
        download(input.dataUrl,`${String(index+1).padStart(2,'0')}-${input.role}.${extension}`);
      }));
    } catch(error) { toast(error.message || '검증 준비 중 오류가 발생했습니다. 유료 API는 호출하지 않았습니다.'); }
    finally {previewPending=false;render();}
  }
  async function importManualSheet(file) {
    if (!file) return;
    if (jobId || pending) { toast('진행 중인 기준 시트 생성을 완료하거나 취소한 후 가져와주세요.'); return; }
    if (!front() || !body()) { toast('이 결과에 사용한 기준 얼굴과 전신 사진을 먼저 지정해주세요.'); return; }
    if (previewManifest && (previewManifest.revision!==state.revision || previewManifest.epoch!==sourceEpoch)) { toast('검증 프롬프트를 준비한 뒤 원본이 바뀌었습니다. 현재 원본으로 검증 프롬프트를 다시 준비해주세요.'); return; }
    const revision=state.revision, epoch=sourceEpoch, profileId=state.profile.id;
    try {
      const dataUrl=await fileImage(file);
      if (revision!==state.revision || epoch!==sourceEpoch) throw new Error('결과를 읽는 동안 기준 사진이 바뀌었습니다. 현재 원본을 확인하고 다시 가져와주세요.');
      modal('외부에서 생성한 기준 시트 가져오기',`<p>이 이미지를 <strong>외부 생성 · 수동 검토</strong> 결과로 보관합니다. 사이트의 이미지 API가 만든 결과로 표시하지 않습니다.</p><img class="model-manual-preview" src="${escape(dataUrl)}" alt="외부에서 생성해 가져온 기준 시트"><label class="model-manual-confirm-label"><input type="checkbox" id="model-manual-confirm"> 이 결과가 현재 기준 얼굴·전신 사진으로 생성됐음을 확인했습니다.</label><p>사진의 일치 여부를 자동 검증하지 않습니다. 가져온 뒤 원본 얼굴·체형과 직접 비교하고 승인해주세요. 다른 도구에서 만든 결과는 API 품질이나 속도를 검증하지 않습니다.</p><div class="model-dialog-actions"><button id="model-manual-import-back">돌아가기</button><button id="model-manual-import-confirm" disabled>비교할 결과로 가져오기</button></div>`);
      $('#model-manual-confirm').addEventListener('change',event=>{$('#model-manual-import-confirm').disabled=!event.target.checked;});
      $('#model-manual-import-back').addEventListener('click',closeModal);
      $('#model-manual-import-confirm').addEventListener('click',()=>{
        if (!$('#model-manual-confirm').checked) return;
        if (revision!==state.revision || epoch!==sourceEpoch || profileId!==state.profile.id) {closeModal();toast('확인 중 기준 원본이 바뀌어 가져오기를 중단했습니다.');return;}
        const manifest=previewManifest?.manifest;
        state.sheet={dataUrl,sourceRevision:revision,approved:false,createdAt:new Date().toISOString(),origin:'manual',provenance:{profileId,profileRevision:revision,sourceFingerprint:manifest?.sourceFingerprint||'',sourcePhotoIds:state.photos.map(photo=>photo.id),confirmation:'user-confirmed-current-sources',filename:file.name.slice(0,120)}};
        persist();render();closeModal();$('#model-generated-preview')?.scrollIntoView({behavior:'smooth',block:'start'});toast('외부 결과를 가져왔어요. 아직 승인되지 않았습니다. 원본과 비교해주세요.');
      });
    } catch(error) {toast(error.message || '외부 시트 이미지를 읽지 못했습니다.');}
  }

  async function generate() {
    if(jobId||pending||previewPending)return;
    if(!front()||!body()) {toast('정면 얼굴과 전신 사진을 지정해주세요.');return;}
    try {
      const response=await fetch('/api/studio/status',{signal:AbortSignal.timeout(5000)});const data=await response.json();
      if(!response.ok||!data.configured)throw new Error('not configured');
    } catch {
      await devPreview();
      return;
    }
    const missing=['side','back'].filter(role=>!state.photos.some(photo=>photo.role===role)).map(role=>roles[role]);
    modal('모델 기준 시트를 생성할까요?',`<p>원본 ${state.photos.length}장으로 한 장의 기준 보드를 생성합니다. <strong>고화질 이미지 API 유료 요청 1회</strong>가 발생하며 사진이 이미지 생성 서비스로 전송됩니다.</p><ol><li>얼굴 일관성 최우선</li><li>같은 축척의 정면·측면·후면</li><li>얼굴 구조를 유지한 표정 8개</li><li>눈·입·피부 디테일과 간결한 팔레트</li></ol>${missing.length?`<p class="model-warning">${missing.join('·')} 사진이 없습니다. 이 각도는 추정되므로 실제 사진을 추가할수록 기준이 명확해집니다.</p>`:''}<p>얼굴 구조나 비율의 완전한 고정을 보장할 수 없습니다. 생성 후 기준 얼굴과 비교·승인하는 단계를 거칩니다.</p><div class="model-dialog-actions"><button id="model-generation-back">사진 더 확인하기</button><button id="model-generation-confirm">유료 1회 · 시트 생성</button></div>`);
    $('#model-generation-back').addEventListener('click',closeModal);
    $('#model-generation-confirm').addEventListener('click',()=>{closeModal();startJob();},{once:true});
  }
  async function startJob() {
    if(jobId||pending)return;pending=true;jobRevision=state.revision;jobEpoch=sourceEpoch;render();status('기준 시트 생성을 요청하고 있어요…');
    let lastError = '';
    const submitted=sheetSubmission();
    try {
      const response=await fetch('/api/studio/model-sheet',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(submitted),signal:AbortSignal.timeout(30000)});
      const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.message||'기준 시트 요청에 실패했습니다.');
      if(!data.jobId||typeof data.jobId!=='string')throw new Error('작업 정보를 받지 못했습니다.');
      jobId=data.jobId;status('3면 뷰와 표정 시트를 만들고 있어요…');pollJob();
    } catch(error) {lastError=error.message;toast(error.message);} finally {pending=false;render();if(lastError)status(lastError);}
  }
  async function pollJob() {
    if(!jobId)return;const current=jobId;
    try {
      const response=await fetch('/api/studio/jobs/'+encodeURIComponent(current),{signal:AbortSignal.timeout(15000)});
      const data=await response.json().catch(()=>({}));
      if(response.status===404){jobId=null;render();status('작업이 만료되었거나 서버가 재시작되었습니다. 다시 생성해주세요.');toast('시트 작업을 찾지 못했습니다. 다시 생성해주세요.');return;}
      if(!response.ok)throw new Error(data.message||'시트 생성 상태를 확인하지 못했습니다.');
      if(['completed','cancelled','failed'].includes(data.status)){
        jobId=null;const shot=data.shots?.find(shot=>shot.status==='completed'&&validImage(shot.dataUrl,18*1024*1024));
        if(data.status==='cancelled'){toast('기준 시트 생성을 취소했어요. 이미 전송한 요청에는 비용이 발생할 수 있습니다.');render();return;}
        if(shot&&jobRevision===state.revision&&jobEpoch===sourceEpoch){await imageElement(shot.dataUrl);state.sheet={dataUrl:shot.dataUrl,sourceRevision:jobRevision,approved:false,createdAt:new Date().toISOString(),origin:'api'};persist();render();$('#model-generated-preview')?.scrollIntoView({behavior:'smooth',block:'start'});toast('기준 시트가 완성됐어요. 원본 얼굴과 비교한 후 승인해주세요.');}
        else if(shot){toast('생성 도중 모델 기준이 바뀌어 이 결과를 승인할 수 없습니다. 변경된 기준으로 다시 생성해주세요.');render();}
        else{render();status(data.shots?.[0]?.error||'기준 시트를 생성하지 못했습니다.');toast(data.shots?.[0]?.error||'기준 시트 생성에 실패했습니다.');}
        return;
      }
      status('3면 뷰와 표정 시트를 만들고 있어요…');
    }catch(error){status(error.message+' 잠시 후 다시 확인합니다.');}
    if(jobId===current)polling=setTimeout(pollJob,2500);
  }
  async function cancel() {
    if(!jobId)return;
    try{const response=await fetch('/api/studio/jobs/'+encodeURIComponent(jobId),{method:'DELETE'});if(!response.ok)throw new Error();status('시트 생성 취소를 요청했습니다.');}catch{toast('취소 요청을 보내지 못했습니다. 다시 시도해주세요.');}
  }
  function approve() {
    if(!state.sheet||state.sheet.sourceRevision!==state.revision){toast('현재 원본 사진과 일치하는 생성 시트가 없습니다.');return;}
    state.sheet.approved=true;persist();render();useModel(true);
  }
  function download(source,name) {const blob=source instanceof Blob,url=blob?URL.createObjectURL(source):source;const anchor=document.createElement('a');anchor.href=url;anchor.download=name;document.body.append(anchor);anchor.click();anchor.remove();if(blob)setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function exportKit() {
    if(!state.photos.length){toast('모델 사진을 먼저 추가해주세요.');return;}
    modal('사진을 포함한 모델 파일 저장',`<p>모델 사진 ${state.photos.length}장${state.sheet?'과 생성한 기준 시트':''}, 설명·승인 정보를 하나의 JSON 파일로 저장합니다. 다음 작업에서 이 파일을 가져오면 같은 원본과 기준 시트를 다시 사용할 수 있어요.</p><p>개인 사진이 포함된 파일이므로 본인이 관리하는 위치에 보관해주세요.</p><div class="model-dialog-actions"><button id="model-export-cancel">취소</button><button id="model-export-confirm">모델 파일 내려받기</button></div>`);
    $('#model-export-cancel').addEventListener('click',closeModal);
    $('#model-export-confirm').addEventListener('click',()=>{download(new Blob([JSON.stringify({format:'muse-model-kit-v1',version:1,exportedAt:new Date().toISOString(),model:state})],{type:'application/json'}),`muse-model-${state.profile.id}.json`);closeModal();toast('사진을 포함한 모델 파일을 저장했어요.');});
  }
  async function importKit(file) {
    if (uploadingPhotos) { toast('사진 업로드가 끝난 뒤 모델 파일을 불러와주세요.'); return; }
    if(!file)return;
    try {
      if(file.size>65*1024*1024)throw new Error('모델 파일은 65MB 이하만 가져올 수 있습니다.');
      const imported=validateKit(JSON.parse(await file.text()));
      await validateSources(imported);
      modal('이 모델 파일을 가져올까요?',`<p><strong>${escape(imported.profile.name||'나의 모델')}</strong> · 사진 ${imported.photos.length}장 · ${imported.sheet?.approved?'승인한 기준 시트 포함':imported.sheet?'검토할 기준 시트 포함':'원본 사진 보드'}</p><p>현재 기기의 모델 작업을 대체합니다. 필요한 현재 작업은 먼저 모델 파일로 저장해주세요.</p><div class="model-dialog-actions"><button id="model-import-back">돌아가기</button><button id="model-import-confirm">이 모델 가져오기</button></div>`);
      $('#model-import-back').addEventListener('click',closeModal);
      $('#model-import-confirm').addEventListener('click',()=>{
        state=imported;sourceEpoch++;previewManifest=null;details={};fillFields();persist();render();derivePhotos();closeModal();
        window.dispatchEvent(new CustomEvent('muse:model-changed',{detail:{id:state.profile.id,revision:state.revision,reason:'import'}}));
        if(activeSheet())useModel(false);toast('모델 파일을 불러왔어요. 원본과 시트 승인을 확인해주세요.');
      });
    }catch(error){toast(error.message||'모델 파일을 읽을 수 없습니다.');}
  }
  function clearModel() {
    if (uploadingPhotos) { toast('사진 업로드가 끝난 뒤 초기화해주세요.'); return; }
    modal('이 기기의 모델 작업 지우기','<p>사진과 기준 시트의 로컬 작업을 지웁니다. 이미 내려받은 모델 파일은 유지됩니다. 필요한 작업은 먼저 저장해주세요.</p><div class="model-dialog-actions"><button id="model-clear-back">유지하기</button><button id="model-clear-confirm">이 기기에서 지우기</button></div>');
    $('#model-clear-back').addEventListener('click',closeModal);$('#model-clear-confirm').addEventListener('click',()=>{state=fresh();sourceEpoch++;previewManifest=null;details={};fillFields();persist();render();derivePhotos();closeModal();window.dispatchEvent(new CustomEvent('muse:model-changed',{detail:{reason:'clear'}}));toast('이 기기의 모델 사진을 지웠어요.');});
  }
  async function exportBoard() {
    const f=front();if(!f){toast('기준 정면 얼굴을 지정해주세요.');return;}
    try {
      const canvas=document.createElement('canvas');canvas.width=2000;canvas.height=1500;const ctx=canvas.getContext('2d');
      ctx.fillStyle='#f7f7f1';ctx.fillRect(0,0,2000,1500);ctx.fillStyle='#2e3928';ctx.font='38px sans-serif';ctx.fillText(state.profile.name||'나의 모델',65,83);ctx.font='17px sans-serif';ctx.fillStyle='#7b8868';ctx.fillText('SOURCE PHOTO BOARD / 원본 정리 보드 — AI 생성 결과가 아닙니다',65,118);
      async function draw(source,x,y,w,h,contain=false){const image=await imageElement(source);const ratio=contain?Math.min(w/image.naturalWidth,h/image.naturalHeight):Math.max(w/image.naturalWidth,h/image.naturalHeight);ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.drawImage(image,x+(w-image.naturalWidth*ratio)/2,y+(h-image.naturalHeight*ratio)/2,image.naturalWidth*ratio,image.naturalHeight*ratio);ctx.restore();}
      await draw(f.dataUrl,65,160,550,860,true);ctx.fillStyle='#526144';ctx.font='21px sans-serif';ctx.fillText('01 기준 정면 얼굴 · 원본',65,1060);
      const views=[body(),state.photos.find(p=>p.role==='side'),state.photos.find(p=>p.role==='back')];
      for(let i=0;i<3;i++){const x=690+i*420;ctx.strokeStyle='#d3dbc5';ctx.strokeRect(x,160,375,480);if(views[i])await draw(views[i].dataUrl,x+12,172,351,430,true);ctx.fillStyle='#72835c';ctx.font='20px sans-serif';ctx.fillText(['정면','측면','후면'][i]+(views[i]?' · 원본':' · 사진 없음'),x+12,625);}
      ctx.fillStyle='#566946';ctx.font='22px sans-serif';ctx.fillText('03 표정 8가지 — 생성할 표정 계획',690,710);
      for(let i=0;i<8;i++){const x=690+(i%4)*315,y=745+Math.floor(i/4)*150;ctx.strokeStyle='#d7dfcd';ctx.strokeRect(x,y,285,125);ctx.fillStyle='#83926f';ctx.font='20px sans-serif';ctx.fillText(expressions[i],x+20,y+47);ctx.font='14px sans-serif';ctx.fillText('표정 이미지 미생성',x+20,y+80);}
      for(const [index,key]of ['eyes','mouth','skin'].entries()){if(details[key])await draw(details[key],65+index*205,1120,185,100);ctx.fillStyle='#7a876a';ctx.font='16px sans-serif';ctx.fillText(['눈 · 원본 영역','입 · 원본 영역','피부 · 원본 영역'][index],65+index*205,1249);}
      palette.forEach((color,index)=>{ctx.fillStyle=color;ctx.fillRect(720+index*220,1135,180,85);ctx.fillStyle='#7b886c';ctx.font='16px sans-serif';ctx.fillText(color,720+index*220,1250);});
      ctx.fillStyle='#8c987b';ctx.font='17px sans-serif';ctx.fillText('얼굴 일관성 → 3면 정확도 → 자연스러운 표정 → 균일한 레이아웃',65,1390);ctx.font='15px sans-serif';ctx.fillText('업로드하지 않은 각도와 표정은 이 원본 보드에 임의로 만들지 않습니다.',65,1430);
      canvas.toBlob(blob=>{if(blob)download(blob,'muse-source-reference-board.png');},'image/png');
    }catch{toast('원본 보드 저장에 실패했습니다. 모델 파일로 보관해주세요.');}
  }

  $('#model-photos-upload')?.addEventListener('change',event=>{addPhotos([...event.target.files]);event.target.value='';});
  const dropzone=$('#model-upload-zone') || $('#model-photo-dropzone');
  dropzone?.addEventListener('dragover',event=>{event.preventDefault();dropzone.classList.add('dragover');});
  dropzone?.addEventListener('dragleave',()=>dropzone.classList.remove('dragover'));
  dropzone?.addEventListener('drop',event=>{event.preventDefault();dropzone.classList.remove('dragover');addPhotos([...event.dataTransfer.files]);});
  $('#model-photo-list')?.addEventListener('change',event=>{if(event.target.matches('[data-model-role]'))rolePhoto(event.target.dataset.modelRole,event.target.value);});
  $('#model-photo-list')?.addEventListener('click',event=>{const button=event.target.closest('[data-model-action]');if(!button)return;const index=state.photos.findIndex(p=>p.id===button.dataset.id);if(index<0)return;
    if(button.dataset.modelAction==='primary'){rolePhoto(button.dataset.id,'face');return;}
    if(button.dataset.modelAction==='remove')state.photos.splice(index,1);
    if(button.dataset.modelAction==='up'&&index>0)[state.photos[index-1],state.photos[index]]=[state.photos[index],state.photos[index-1]];
    changed('photos-modified',{derive:true});
  });
  for(const[key,id]of Object.entries(fields))$('#'+id)?.addEventListener('input',event=>{state.profile[key]=event.target.value.slice(0,key==='notes'?3000:key==='bodyNotes'?1000:key==='name'?100:500);changed('profile-modified');});
  $('#model-board')?.addEventListener('click',event=>{const button=event.target.closest('[data-model-crop]');if(button)editCrop(button.dataset.modelCrop);});
  $('#model-generated-preview')?.addEventListener('click',event=>{const action=event.target.closest('[data-model-action]')?.dataset.modelAction;
    if(action==='approve-sheet')approve();
    if(action==='download-sheet'&&state.sheet)download(state.sheet.dataUrl,'muse-model-reference.'+(state.sheet.dataUrl.startsWith('data:image/png')?'png':state.sheet.dataUrl.startsWith('data:image/webp')?'webp':'jpg'));
    if(action==='zoom-sheet'&&state.sheet)modal('생성한 모델 기준 시트',`<img class="model-sheet-zoom" src="${escape(state.sheet.dataUrl)}" alt="원본과 비교할 모델 기준 시트"><p>정면 기준 얼굴·3면 비율·표정의 구조가 일치하는지 확인해주세요.</p>`);
  });
  $('#model-dev-preview')?.addEventListener('click',devPreview);
  $('#model-sheet-import-button')?.addEventListener('click',()=>$('#model-sheet-import')?.click());
  $('#model-sheet-import')?.addEventListener('change',event=>{importManualSheet(event.target.files[0]);event.target.value='';});
  $('#model-sheet-generate')?.addEventListener('click',generate);
  $('#model-sheet-cancel')?.addEventListener('click',cancel);
  $('#model-sheet-approve')?.addEventListener('click',approve);
  $('#model-use-photos')?.addEventListener('click',()=>useModel(true));
  $('#model-next-button')?.addEventListener('click',()=>useModel(true));
  $('#model-add-required-photo')?.addEventListener('click',()=>$('#model-photos-upload')?.click());
  $('#model-kit-export')?.addEventListener('click',exportKit);
  $('#model-board-export')?.addEventListener('click',exportBoard);
  $('#model-kit-import-button')?.addEventListener('click',()=>$('#model-kit-import')?.click());
  $('#model-kit-import')?.addEventListener('change',event=>{importKit(event.target.files[0]);event.target.value='';});
  $('#model-clear')?.addEventListener('click',clearModel);
  $('#model-dialog-close')?.addEventListener('click',closeModal);
  window.addEventListener('muse:connection',render);
  $('#model-dialog')?.addEventListener('click',event=>{if(event.target===event.currentTarget){const r=event.currentTarget.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)closeModal();}});
  window.MuseModel={ready:initStorage(),flush:persist,use:useModel,snapshot:()=>({profile:{...state.profile},photoCount:state.photos.length,revision:state.revision,hasFace:!!front(),hasBody:!!body(),uploadingPhotos,approved:!!activeSheet(),hasSheet:!!state.sheet,sheetOrigin:state.sheet?.origin || null,hasDevPreview:!!previewManifest,devPreviewCurrent:!!previewManifest&&previewManifest.revision===state.revision&&previewManifest.epoch===sourceEpoch,jobId,storageAvailable:!!db&&!storageBroken})};
})();
