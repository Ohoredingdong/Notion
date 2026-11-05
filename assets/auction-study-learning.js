/* Source-first exercises and a local document desk. Practice never edits a case. */
(() => {
  'use strict';
  const KEY = 'auction-study-lessons-v1';
  const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>';

  class LearningDesk {
    constructor(callbacks) {
      this.callbacks = callbacks;
      this.mode = 'practice';
      this.step = 0;
      this.pane = 'document';
      this.sources = new Map();
      this.hint = false;
      this.persistent = true;
      this.progress = {version:1,caseId:AuctionLessons.cases[0].id,answers:{}};
      try {
        const raw = localStorage.getItem(KEY);
        if (raw) {
          const data = JSON.parse(raw);
          if (!data || data.version !== 1 || !data.answers || typeof data.answers !== 'object' || Array.isArray(data.answers)) throw Error('Invalid progress');
          // Restore known lessons and real choice IDs only, never user HTML.
          if (AuctionLessons.cases.some(item => item.id === data.caseId)) this.progress.caseId = data.caseId;
          for (const lesson of AuctionLessons.cases) {
            for (const [index, step] of lesson.steps.entries()) {
              const answer = data.answers[lesson.id]?.[step.id];
              if (answer && AuctionLessons.validateAnswer(lesson.id,index,answer.choiceId).valid) {
                this.answers(lesson.id)[step.id] = {choiceId:answer.choiceId,checked:answer.checked === true};
              }
            }
          }
        }
      } catch (_) { this.persistent = false; }
      document.addEventListener('click', event => this.click(event));
      document.addEventListener('change', event => this.change(event));
      document.addEventListener('input', event => {
        if (event.target.id === 'studySourceURL' && this.current) this.source().draft = event.target.value;
      });
    }

    answers(id=this.progress.caseId) { return this.progress.answers[id] ||= {}; }
    lesson() { return AuctionLessons.cases.find(item => item.id === this.progress.caseId); }
    source() {
      if (!this.sources.has(this.current.id)) this.sources.set(this.current.id,{url:'',name:'',draft:'',error:''});
      return this.sources.get(this.current.id);
    }
    save() {
      if (!this.persistent) return;
      try { localStorage.setItem(KEY,JSON.stringify(this.progress)); }
      catch (_) { this.persistent = false; }
    }
    render(current) {
      this.current = current;
      const lesson = this.lesson(), step = lesson.steps[this.step];
      const answer = this.answers()[step.id];
      const checked = answer?.checked === true;
      const grade = checked ? AuctionLessons.validateAnswer(lesson.id,this.step,answer.choiceId) : null;
      const count = Object.values(this.answers()).filter(item => item.checked).length;
      const practice = this.mode === 'practice';
      return `<div class="learning-workspace" data-mode="${this.mode}" data-pane="${this.pane}">
        <div class="study-toolbar"><div class="study-mode-switch" role="group" aria-label="공부할 자료 선택"><button type="button" data-study-mode="practice" aria-pressed="${practice}">해설 있는 연습 사례</button><button type="button" data-study-mode="case" aria-pressed="${!practice}">내 경매 자료로 분석</button></div>${practice?`<label class="study-case-select"><span class="sr-only">연습 사례 선택</span><select id="studyCaseSelect">${AuctionLessons.cases.map(item=>`<option value="${item.id}" ${item.id===lesson.id?'selected':''}>${escapeHTML(item.title)}</option>`).join('')}</select></label>`:`<span class="study-current-case" title="${escapeHTML(current.name)}">${current.demo?'<span class="badge amber">연습 노트</span> ':''}${escapeHTML(current.name)}</span>`}<span class="study-progress">${practice?`학습 ${count} / 6${this.persistent?'':' · 저장 안 됨'}`:'내 기록에 직접 저장'}</span></div>
        <div class="study-steps" role="group" aria-label="서류 읽기 단계">${AuctionLessons.topics.map((topic,index)=>`<button type="button" data-study-step="${index}" aria-pressed="${index===this.step}"><span>${String(index+1).padStart(2,'0')}</span>${escapeHTML(topic.label)}${practice&&this.answers()[topic.id]?.checked?'<i aria-label="해설 확인함">✓</i>':''}</button>`).join('')}</div>
        <div class="study-pane-tabs" role="group" aria-label="학습 화면 선택"><button type="button" data-study-pane="document" aria-pressed="${this.pane==='document'}">자료 보기</button><button type="button" data-study-pane="guide" aria-pressed="${this.pane==='guide'}">${practice?'함께 분석':'내 기록'}</button></div>
        <div class="study-layout">${practice?this.practiceDocument(lesson,step,checked||this.hint):this.realDocument()}${practice?this.practiceGuide(lesson,step,answer,grade):this.realGuide(step)}</div>
      </div>`;
    }

    practiceDocument(lesson,step,revealed) {
      return `<section id="studyDocumentPane" class="study-card study-document"><header class="study-card-header"><div><span class="study-kicker">READ THE DOCUMENT</span><h2>${escapeHTML(step.documentTitle)}</h2></div><span class="badge amber">가상 학습 자료 · 실매물 아님</span></header><div class="study-document-body"><p class="study-document-caption">${escapeHTML(step.documentCaption)}</p><dl class="study-document-rows">${step.rows.map(row=>`<div class="study-document-row ${row.focus&&revealed?'focused':''}"><dt>${escapeHTML(row.label)}</dt><dd>${escapeHTML(row.value)}</dd></div>`).join('')}</dl><div class="study-document-note"><strong>${revealed?'표시된 줄을 근거로 읽어 보세요.':'먼저, 서류에서 근거를 찾아보세요.'}</strong><p>${revealed?escapeHTML(step.hint):'오른쪽 질문을 읽고, 판단에 필요한 기재와 빠진 정보를 찾아보세요. 답을 확인하면 관련 줄이 표시됩니다.'}</p></div><p class="study-fiction-note">공부를 위해 만든 발췌입니다. 실제 법원 서류나 현재 매각 물건이 아닙니다.</p></div></section>`;
    }

    practiceGuide(lesson,step,answer,grade) {
      const checked = answer?.checked === true;
      return `<section id="studyGuidePane" class="study-card study-guide"><header class="study-card-header"><div><span class="study-kicker">STEP ${this.step+1} · 직접 읽고 판단하기</span><h2>${escapeHTML(step.title)}</h2></div></header><div class="study-guide-body"><fieldset class="study-question"><legend>${escapeHTML(step.question)}</legend><div class="study-options">${step.choices.map(choice=>`<label><input type="radio" name="studyAnswer" value="${escapeHTML(choice.id)}" ${answer?.choiceId===choice.id?'checked':''}><span>${escapeHTML(choice.text)}</span></label>`).join('')}</div></fieldset><div class="study-answer-actions"><button type="button" class="text-link" data-study-action="hint">근거 찾기 힌트</button><button type="button" class="button primary small" data-study-action="check" ${answer?.choiceId?'':'disabled'}>답과 해설 확인</button></div><div class="study-feedback-slot"><div id="studyFeedback" class="study-feedback ${grade?.correct?'correct':'review'}" data-correct="${grade?.correct===true}" role="status" ${checked?'':'hidden'}><strong>${grade?.correct?'자료 읽는 요점을 잡았어요.':'이 부분을 다시 읽어볼까요?'}</strong><p>${escapeHTML(step.explanation)}</p></div><p id="studyHint" class="study-hint" ${this.hint&&!checked?'':'hidden'}>${escapeHTML(step.hint)}</p>${!checked&&!this.hint?'<p class="study-answer-placeholder">답을 고르면 어느 기재가 근거인지 함께 확인해요.</p>':''}</div></div>${this.footer()}</section>`;
    }

    realDocument() {
      const source = this.source();
      return `<section id="studyDocumentPane" class="study-card study-document study-real-document" data-source="${escapeHTML(source.url)}"><header class="study-card-header"><div><span class="study-kicker">MY AUCTION DOCUMENT</span><h2>내가 확인할 경매 자료</h2></div><a class="text-link" href="https://www.courtauction.go.kr/" target="_blank" rel="noopener noreferrer">법원경매정보 열기 ${icon}</a></header><div class="study-real-body"><div class="study-source-link"><label class="sr-only" for="studySourceURL">경매 물건 원문 주소</label><input id="studySourceURL" type="url" value="${escapeHTML(source.draft)}" placeholder="보고 있는 경매 물건의 https:// 주소"><button type="button" class="button small" data-study-action="open-source">원문 열기</button></div><div class="study-upload-bar"><input id="studyDocument" class="sr-only" type="file" accept="application/pdf,.pdf"><label class="button small" for="studyDocument">${source.name?'PDF 바꾸기':'경매 서류 PDF 열기'}</label><span title="${escapeHTML(source.name)}">${escapeHTML(source.name||'매각물건명세서 · 현황조사서 · 등기')}</span></div><p id="studySourceError" class="study-source-error" role="alert" ${source.error?'':'hidden'}>${escapeHTML(source.error)}</p>${source.url?`<iframe id="studyPdf" title="선택한 경매 PDF 자료" src="${escapeHTML(source.url)}#toolbar=1&navpanes=0"></iframe>`:`<div class="study-source-empty"><span class="study-source-symbol" aria-hidden="true">↗</span><h3>실제 물건을 보고, 내 근거를 남겨보세요.</h3><p>법원경매정보나 이용 중인 경매 사이트에서 물건을 찾으세요. 내려받은 서류를 여기서 열면 분석 순서와 나란히 볼 수 있어요.</p><a href="https://www.iros.go.kr/" target="_blank" rel="noopener noreferrer">인터넷등기소에서 등기 확인 ${icon}</a></div>`}<p class="study-file-note">PDF는 이 화면에서만 열리며 노트 내보내기에는 포함되지 않습니다. 자료 내용과 확인 근거는 직접 대조하세요.</p></div></section>`;
    }

    realGuide(step) {
      const item = this.current.rights[this.step];
      return `<section id="studyGuidePane" class="study-card study-guide study-real-guide"><header class="study-card-header"><div><span class="study-kicker">STEP ${this.step+1} · 원문과 대조하기</span><h2>${escapeHTML(step.title)}</h2></div></header><div class="study-guide-body"><p class="study-real-prompt">${escapeHTML(step.evidencePrompt)}</p><ul class="study-read-checks">${step.checklist.map(text=>`<li>${escapeHTML(text)}</li>`).join('')}</ul><div class="study-source-links">${step.sources.map(source=>`<a href="${escapeHTML(source.href)}" target="_blank" rel="noopener noreferrer">${escapeHTML(source.name)} ↗</a>`).join('')}</div><div class="study-record-status"><label for="studyRightStatus">확인 상태</label><select id="studyRightStatus" data-right="${this.step}">${[['unknown','미확인'],['checking','확인 중'],['clear','확인 완료'],['risk','위험 발견']].map(([value,label])=>`<option value="${value}" ${item.status===value?'selected':''}>${label}</option>`).join('')}</select></div><label class="study-evidence-label" for="studyEvidence">내가 읽은 내용·확인 근거<textarea id="studyEvidence" data-evidence="${this.step}" rows="3" placeholder="서류명과 열람일, 해당 기재, 아직 확인하지 못한 내용을 남겨보세요.">${escapeHTML(item.evidence)}</textarea></label><p class="study-record-note">직접 기록한 내용만 내 물건에 저장돼요. 연습 문제의 답은 옮겨 적지 않아요.</p></div>${this.footer()}</section>`;
    }

    footer() {
      return `<footer class="study-navigation"><button type="button" class="button small" data-study-step="${Math.max(0,this.step-1)}" ${this.step===0?'disabled':''}>이전</button><span>${this.step+1} / 6</span>${this.step<5?`<button type="button" class="button primary small" data-study-step="${this.step+1}">다음 단계 ${icon}</button>`:`<button type="button" class="button primary small" data-study-action="finish">${this.mode==='practice'?'내 물건에 적용':'투자금 계산으로'} ${icon}</button>`}</footer>`;
    }

    paint() {
      const root = document.querySelector('.learning-workspace');
      if (!root) return;
      const temporary = document.createElement('template');
      temporary.innerHTML = this.render(this.current);
      const fresh = temporary.content.firstElementChild;
      root.dataset.mode = fresh.dataset.mode;
      root.dataset.pane = fresh.dataset.pane;
      for (const selector of ['.study-toolbar','.study-steps','.study-pane-tabs','#studyGuidePane']) root.querySelector(selector).replaceWith(fresh.querySelector(selector));
      const existing = root.querySelector('#studyDocumentPane');
      const next = fresh.querySelector('#studyDocumentPane');
      // Keep the native PDF viewer and its current page alive while changing steps.
      if (this.mode==='case' && existing.classList.contains('study-real-document') && existing.dataset.source===next.dataset.source) {
        existing.querySelector('#studySourceURL').value=this.source().draft;
        const error=existing.querySelector('#studySourceError');
        error.textContent=this.source().error;error.hidden=!this.source().error;
      } else existing.replaceWith(next);
    }

    click(event) {
      if (!document.querySelector('.learning-workspace')) return;
      const button = event.target.closest('[data-study-mode],[data-study-step],[data-study-pane],[data-study-action]');
      if (!button || button.disabled) return;
      const {studyMode,studyStep,studyPane,studyAction} = button.dataset;
      if (studyMode) { this.mode=studyMode;this.hint=false;this.pane='document';this.paint();document.querySelector(`[data-study-mode="${this.mode}"]`)?.focus({preventScroll:true}); }
      else if (studyStep!==undefined) { this.step=Math.max(0,Math.min(5,Number(studyStep)));this.hint=false;this.paint();document.querySelector(`.study-steps [data-study-step="${this.step}"]`)?.focus({preventScroll:true}); }
      else if (studyPane) { this.pane=studyPane;document.querySelector('.learning-workspace').dataset.pane=studyPane;document.querySelectorAll('[data-study-pane]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.studyPane===studyPane))); }
      else if (studyAction==='hint') { this.hint=!this.hint;this.paint();document.querySelector('[data-study-action=hint]')?.focus({preventScroll:true}); }
      else if (studyAction==='check') {
        const item=this.answers()[this.lesson().steps[this.step].id];
        if (!item) return;
        item.checked=true;this.save();this.hint=false;this.paint();document.querySelector('[data-study-action=check]')?.focus({preventScroll:true});
      } else if (studyAction==='finish') {
        if (this.mode==='practice') { this.mode='case';this.step=0;this.hint=false;this.pane='document';this.paint();document.querySelector(`[data-study-mode="${this.mode}"]`)?.focus({preventScroll:true}); }
        else this.callbacks.openPage('money');
      } else if (studyAction==='open-source') {
        const source=this.source();
        try {
          const url=new URL(source.draft);
          if (url.protocol!=='https:'||!url.hostname||url.username||url.password) throw Error('Invalid URL');
          source.error='';window.open(url.href,'_blank','noopener,noreferrer');
        } catch (_) { source.error='https://로 시작하는 원문 주소를 입력해 주세요.'; }
        this.paint();
      }
    }

    async change(event) {
      if (!document.querySelector('.learning-workspace')) return;
      const input=event.target;
      if (input.id==='studyCaseSelect') {
        if (!AuctionLessons.cases.some(item=>item.id===input.value)) return;
        this.progress.caseId=input.value;this.step=0;this.hint=false;this.save();this.paint();
      } else if (input.name==='studyAnswer') {
        const step=this.lesson().steps[this.step];
        if (!AuctionLessons.validateAnswer(this.lesson().id,this.step,input.value).valid) return;
        this.answers()[step.id]={choiceId:input.value,checked:false};this.hint=false;this.save();this.paint();
        document.querySelector(`input[name="studyAnswer"][value="${input.value}"]`)?.focus({preventScroll:true});
      } else if (input.id==='studyDocument'&&input.files[0]) {
        const caseId=this.current.id,source=this.source(),file=input.files[0];
        const requestId=(source.requestId||0)+1;
        source.requestId=requestId;
        try {
          if (file.size>20*1024*1024) throw Error('PDF는 20MB 이하로 선택해 주세요.');
          if (file.type && file.type!=='application/pdf') throw Error('PDF 형식의 파일을 선택해 주세요. 기존 자료는 그대로 유지됩니다.');
          const header=await file.slice(0,5).text();
          if (source.requestId!==requestId) return;
          if (header!=='%PDF-') throw Error('PDF 파일인지 확인해 주세요. 기존 자료는 그대로 유지됩니다.');
          const url=URL.createObjectURL(file);
          if (source.url) URL.revokeObjectURL(source.url);
          source.url=url;source.name=file.name;source.error='';
        } catch (error) { if (source.requestId!==requestId) return;source.error=error.message; }
        if (source.requestId===requestId) input.value='';
        if (this.current.id===caseId) this.paint();
      }
    }
  }
  window.AuctionStudyLearning={create:callbacks=>new LearningDesk(callbacks)};
})();
