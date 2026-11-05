/* Same-origin service sessions. Image API keys never enter the browser. */
(() => {
  'use strict';
  let required = false, authenticated = false, pending = false, allowAutomaticPrompt = true;
  let dialog, form, password, message, submit, successfulClose = false;

  function endpoint(path) {
    const url = new URL(path, window.location.href);
    if (url.origin !== window.location.origin || url.username || url.password || !url.pathname.startsWith('/api/studio/')) {
      throw new Error('같은 스튜디오의 생성 서비스만 사용할 수 있습니다.');
    }
    return url.href;
  }
  function notify() {
    window.dispatchEvent(new CustomEvent('muse:service-session', { detail: { authRequired: required, authenticated } }));
  }
  function ensureDialog() {
    if (dialog) return;
    dialog = document.createElement('dialog');
    dialog.id = 'studio-session-dialog'; dialog.className = 'app-dialog';
    dialog.setAttribute('aria-labelledby', 'studio-session-title');
    dialog.innerHTML = '<div class="dialog-heading"><div><span class="eyebrow">MUSE / PRIVATE STUDIO</span><h2 id="studio-session-title">스튜디오 로그인</h2></div><button type="button" class="icon-button" id="studio-session-close" aria-label="로그인 창 닫기">✕</button></div><p class="dialog-description">배포할 때 정한 스튜디오 접속 비밀번호를 입력하세요. 이미지 API 키는 이 화면에 입력하지 않습니다.</p><form id="studio-session-form"><label class="model-field" for="studio-session-password">접속 비밀번호<input id="studio-session-password" type="password" autocomplete="current-password" required maxlength="1024"></label><p id="studio-session-message" class="dialog-note" role="status" aria-live="polite"></p><button id="studio-session-submit" class="dialog-primary" type="submit">로그인</button></form><p class="dialog-note">로그인해도 이미지 생성은 자동으로 시작되지 않습니다. 생성 버튼에서 사진 전송과 유료 요청을 확인합니다.</p>';
    document.body.append(dialog);
    form = dialog.querySelector('form'); password = dialog.querySelector('input');
    message = dialog.querySelector('#studio-session-message'); submit = dialog.querySelector('#studio-session-submit');
    dialog.querySelector('#studio-session-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => {
      password.value = ''; message.textContent = '';
      if (!successfulClose) allowAutomaticPrompt = false;
      successfulClose = false;
    });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (pending || !form.reportValidity()) return;
      pending = true; submit.disabled = true; password.disabled = true;
      const body = JSON.stringify({ password: password.value }); password.value = '';
      message.textContent = '로그인 정보를 확인하고 있어요…';
      try {
        const response = await fetch(endpoint('/api/studio/session'), { method: 'POST', credentials: 'same-origin', cache: 'no-store', headers: { 'Content-Type': 'application/json' }, body, signal: AbortSignal.timeout(10000) });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.authenticated !== true) throw new Error(data.message || '비밀번호를 확인하고 다시 로그인해주세요.');
        required = data.authRequired !== false; authenticated = true; allowAutomaticPrompt = true;
        successfulClose = true; dialog.close(); notify();
      } catch (error) {
        message.textContent = error.name === 'TimeoutError' ? '로그인 응답이 늦어지고 있습니다. 잠시 후 다시 시도해주세요.' : error.message || '로그인하지 못했습니다.';
      } finally { pending = false; submit.disabled = false; password.disabled = false; if (dialog.open) password.focus(); }
    });
  }
  function signIn({ automatic = false } = {}) {
    if (automatic && !allowAutomaticPrompt) return;
    ensureDialog();
    if (!dialog.open) { message.textContent = ''; dialog.showModal(); password.focus(); }
  }
  async function request(path, options = {}) {
    const url = endpoint(path);
    const response = await fetch(url, { ...options, credentials: 'same-origin', cache: 'no-store' });
    if (response.status === 401) {
      required = true; authenticated = false; signIn({ automatic: true });
    } else if (response.ok && new URL(url).pathname === '/api/studio/status') {
      const data = await response.clone().json().catch(() => ({}));
      required = data.authRequired === true;
      authenticated = data.authenticated === true;
    }
    return response;
  }
  async function signOut() {
    const response = await fetch(endpoint('/api/studio/session'), { method: 'DELETE', credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error('로그아웃하지 못했습니다. 잠시 후 다시 시도해주세요.');
    authenticated = false; allowAutomaticPrompt = false; notify();
  }
  window.MuseService = Object.freeze({ request, signIn, signOut, session: () => ({ authRequired: required, authenticated }) });
})();
