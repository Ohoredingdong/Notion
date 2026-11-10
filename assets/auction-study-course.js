/* Guided fictional lessons. Course progress never changes an auction notebook. */
(() => {
  'use strict';
  const KEY = 'auction-course-v1';
  const PANES = [{id:'basics',label:'기초'},{id:'example',label:'예제'},{id:'practice',label:'실습'}];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
  const owns = (value, key) => Object.prototype.hasOwnProperty.call(value,key);
  const isObject = value => value && typeof value === 'object' && !Array.isArray(value);

  class Course {
    constructor(callbacks={}) {
      this.callbacks = callbacks;
      this.data = window.AuctionCourseData;
      this.lessons = this.data?.lessons || [];
      this.persistent = true;
      this.savedRaw = null;
      this.storageNotice = '';
      this.answerError = '';
      this.progress = {version:1,lessonId:this.lessons[0]?.id || '',pane:'basics',records:{}};
      this.restore();
      document.addEventListener('click', event => this.click(event));
      document.addEventListener('input', event => this.input(event));
      document.addEventListener('change', event => this.input(event));
      document.addEventListener('keydown', event => this.keydown(event));
      document.addEventListener('submit', event => {
        if (!event.target.matches?.('.auction-course .course-answer-form')) return;
        event.preventDefault();this.check();
      });
      window.addEventListener('storage', event => this.storageChanged(event));
    }

    lesson() { return this.lessons.find(item => item.id === this.progress.lessonId) || this.lessons[0]; }
    record(lesson=this.lesson()) {
      if (!owns(this.progress.records,lesson.id)) {
        this.progress.records[lesson.id] = {answer:'',submitted:false,firstAttempt:null,lastAttempt:null,attempts:0};
      }
      return this.progress.records[lesson.id];
    }
    grade(lessonId,answer) {
      const result = this.data.grade(lessonId,answer);
      return {valid:result?.valid === true,correct:result?.valid === true && result.correct === true};
    }
    restoredAttempt(lessonId,attempt) {
      if (!isObject(attempt) || typeof attempt.answer !== 'string' || attempt.answer.length > 200 || typeof attempt.correct !== 'boolean') return null;
      const result = this.grade(lessonId,attempt.answer);
      return result.valid ? {answer:attempt.answer,correct:result.correct} : null;
    }
    restore() {
      try {
        const raw = localStorage.getItem(KEY);
        this.savedRaw = raw;
        if (raw === null) return;
        const parsed = JSON.parse(raw);
        if (!isObject(parsed) || parsed.version !== 1 || !isObject(parsed.records)
          || !this.lessons.some(lesson => lesson.id === parsed.lessonId)
          || !PANES.some(pane => pane.id === parsed.pane)) throw Error('Invalid course progress');
        const restored = {version:1,lessonId:parsed.lessonId,pane:parsed.pane,records:{}};
        for (const lesson of this.lessons) {
          if (!owns(parsed.records,lesson.id)) continue;
          const source = parsed.records[lesson.id];
          if (!isObject(source) || typeof source.answer !== 'string' || source.answer.length > 200
            || typeof source.submitted !== 'boolean' || !Number.isInteger(source.attempts)
            || source.attempts < 0 || source.attempts > 10000) throw Error('Invalid course record');
          const firstAttempt = this.restoredAttempt(lesson.id,source.firstAttempt);
          const lastAttempt = this.restoredAttempt(lesson.id,source.lastAttempt);
          if ((source.firstAttempt !== null && !firstAttempt) || (source.lastAttempt !== null && !lastAttempt)
            || Boolean(firstAttempt) !== Boolean(lastAttempt) || Boolean(firstAttempt) !== (source.attempts>0)
            || (source.submitted && (!lastAttempt || source.answer !== lastAttempt.answer))) throw Error('Invalid course attempt');
          restored.records[lesson.id] = {answer:source.answer,submitted:source.submitted,firstAttempt,lastAttempt,attempts:source.attempts};
        }
        this.progress = restored;
      } catch (_) {
        this.stopSaving('학습 기록을 불러오지 못했습니다. 기존 기록은 덮어쓰지 않으며 이번 진도는 이 화면에만 남습니다.');
      }
    }
    stopSaving(message) {
      this.persistent = false;
      this.storageNotice = message;
      const root = document.querySelector('.auction-course');
      if (!root) return;
      let warning = root.querySelector('#courseStorageWarning');
      if (!warning) {
        warning = document.createElement('div');
        warning.id = 'courseStorageWarning';
        warning.className = 'course-storage-warning';
        warning.setAttribute('role','alert');
        root.prepend(warning);
      }
      warning.textContent = message;
      const status = root.querySelector('.course-save-state');
      if (status) status.textContent = '저장 안 됨 · 현재 화면에만 유지';
      const backup = root.querySelector('[data-course-action="export"]');
      if (backup) backup.hidden = false;
    }
    conflict() {
      this.stopSaving('다른 탭에서 학습 기록이 변경되어 저장을 멈췄습니다. 저장된 기록과 현재 답은 유지됩니다. 새로고침 전에 현재 진도를 보관하세요.');
    }
    storageChanged(event) {
      if (!this.persistent || (event.key !== KEY && event.key !== null)) return;
      try {
        if (event.storageArea && event.storageArea !== localStorage) return;
        if (localStorage.getItem(KEY) !== this.savedRaw) this.conflict();
      } catch (_) {
        this.stopSaving('학습 기록에 접근할 수 없습니다. 현재 답은 이 화면에만 유지됩니다. 새로고침 전에 진도를 보관하세요.');
      }
    }
    save() {
      if (!this.persistent) return false;
      try {
        if (localStorage.getItem(KEY) !== this.savedRaw) { this.conflict(); return false; }
        const raw = JSON.stringify(this.progress);
        localStorage.setItem(KEY,raw);
        this.savedRaw = raw;
        return true;
      } catch (_) {
        this.stopSaving('학습 기록을 저장하지 못했습니다. 현재 답은 이 화면에만 유지됩니다. 새로고침 전에 진도를 보관하세요.');
        return false;
      }
    }

    render() {
      if (!this.lessons.length || typeof this.data?.grade !== 'function') {
        return '<section class="auction-course course-workspace"><p role="alert">기초 학습 자료를 불러오지 못했습니다. 새로고침해 확인하세요.</p></section>';
      }
      const lesson = this.lesson(), index = this.lessons.indexOf(lesson);
      const completed = this.lessons.filter(item => this.record(item).lastAttempt?.correct).length;
      const pane = this.progress.pane;
      return `<section class="auction-course course-workspace" data-course-pane="${pane}" aria-label="경매 기초 학습">
        ${this.storageNotice?`<div id="courseStorageWarning" class="course-storage-warning" role="alert">${esc(this.storageNotice)}</div>`:''}
        <header class="course-overview"><div><p class="course-overview-label">처음 시작하는 경매</p><p class="course-overview-copy">기초를 읽고 예제를 따라간 뒤, 다른 사례를 직접 풀어보세요.</p></div><div class="course-progress"><strong>${completed} / ${this.lessons.length}</strong><span>실습 정답 확인</span></div></header>
        <nav class="course-lessons" aria-label="학습 단원">${this.lessons.map((item,position) => `<button type="button" data-course-lesson="${esc(item.id)}" ${item.id===lesson.id?'aria-current="step"':''}><span class="course-lesson-number">${String(position+1).padStart(2,'0')}</span><span>${esc(item.title)}</span><span class="course-lesson-state" aria-label="${this.record(item).lastAttempt?.correct?'실습 정답 확인':'미완료'}">${this.record(item).lastAttempt?.correct?'✓':''}</span></button>`).join('')}</nav>
        <article class="course-lesson"><header class="course-lesson-heading"><p class="course-lesson-position">${index+1}단원</p><h2 id="courseLessonTitle" tabindex="-1">${esc(lesson.title)}</h2><p>${esc(lesson.goal)}</p></header>
          <div class="course-tabs" role="tablist" aria-label="학습 순서">${PANES.map(item => `<button type="button" id="course-tab-${item.id}" role="tab" data-course-tab="${item.id}" data-course-pane="${item.id}" aria-controls="course-panel" aria-selected="${item.id===pane}" tabindex="${item.id===pane?'0':'-1'}">${item.label}</button>`).join('')}</div>
          <section id="course-panel" class="course-panel" role="tabpanel" aria-labelledby="course-tab-${pane}">${pane==='basics'?this.basics(lesson):pane==='example'?this.example(lesson):this.practice(lesson)}${this.footer()}</section>
        </article>
      </section>`;
    }
    footer() {
      return `<footer class="course-footer"><div><p>다음 연습</p><div class="course-continue"><button type="button" class="text-link" data-course-open="simulation">모의경매 →</button><button type="button" class="text-link" data-course-open="learn">서류 연습 →</button></div></div><div class="course-storage"><span class="course-save-state">${this.persistent?'학습 진도는 이 브라우저에 저장':'저장 안 됨 · 현재 화면에만 유지'}</span><button type="button" class="text-link" data-course-action="export" ${this.persistent?'hidden':''}>현재 진도 보관 ↓</button></div></footer>`;
    }
    basics(lesson) {
      const basics = lesson.basics;
      return `<div class="course-basics"><p class="course-lead">${esc(basics.lead)}</p><dl class="course-terms">${basics.terms.map(item => `<div><dt>${esc(item.term)}</dt><dd>${esc(item.text)}</dd></div>`).join('')}</dl><div class="course-takeaway"><strong>기억할 점</strong><p>${esc(basics.takeaway)}</p></div>${this.references(lesson)}<div class="course-panel-navigation"><button type="button" class="button primary" data-course-action="example">예제 보기 →</button></div></div>`;
    }
    documents(lesson,documents,type,evidence=[]) {
      return `<div class="course-documents">${documents.map(document => `<section class="course-document" aria-label="${esc(document.title)}"><header><h3>${esc(document.title)}</h3><span class="course-fiction">학습용 가상</span></header><dl>${document.rows.map(row => {
        const focused = type==='example' ? row.focus === true : evidence.includes(row.id);
        return `<div id="course-row-${esc(lesson.id)}-${type}-${esc(row.id)}" class="course-document-row${focused?' is-evidence':''}" ${focused?'data-course-evidence="true"':''}><dt>${esc(row.label)}</dt><dd>${esc(row.value)}</dd></div>`;
      }).join('')}</dl></section>`).join('')}</div>`;
    }
    example(lesson) {
      const example = lesson.example;
      return `<div class="course-example"><div class="course-section-heading"><h3>${esc(example.title)}</h3><p>서류의 표시된 기재와 풀이를 순서대로 대조하세요.</p></div><div class="course-worked-example">${this.documents(lesson,example.documents,'example')}<section class="course-solution" aria-label="예제 풀이"><h3>풀이 순서</h3><ol>${example.steps.map(step => `<li><h4>${esc(step.title)}</h4><p>${esc(step.text)}</p></li>`).join('')}</ol><div class="course-example-answer"><strong>예제 결론</strong><p>${esc(example.answer)}</p></div>${example.assumptions?`<p class="course-assumptions">${esc(Array.isArray(example.assumptions)?example.assumptions.join(' '):example.assumptions)}</p>`:''}</section></div><div class="course-panel-navigation"><button type="button" class="button" data-course-action="basics">기초 보기</button><button type="button" class="button primary" data-course-action="practice">직접 풀기 →</button></div></div>`;
    }
    practice(lesson) {
      const practice = lesson.practice, record = this.record(lesson);
      const submitted = record.submitted && Boolean(record.lastAttempt);
      return `<div class="course-practice"><div class="course-section-heading"><h3>${esc(practice.title)}</h3><p>예제와 다른 사례입니다. 서류를 읽고 답을 제출하세요.</p></div><div class="course-practice-layout">${this.documents(lesson,practice.documents,'practice',submitted?practice.evidenceIds:[])}<div class="course-practice-answer"><form class="course-answer-form" novalidate><fieldset><legend>${esc(practice.question)}</legend>${practice.type==='amount'?`<label class="course-amount-label" for="courseAnswer">금액<span class="course-amount-input"><input id="courseAnswer" name="courseAnswer" type="text" inputmode="decimal" autocomplete="off" maxlength="200" value="${esc(record.answer)}" aria-describedby="courseAmountHelp${this.answerError?' courseAnswerError':''}" ${this.answerError?'aria-invalid="true"':''}><span>만원</span></span></label><p id="courseAmountHelp" class="course-answer-help">만원 단위로 입력하세요. 예: 1,000만원 → 1000</p>`:`<div class="course-choices">${practice.choices.map(choice => `<label><input type="radio" name="courseAnswer" value="${esc(choice.id)}" ${record.answer===choice.id?'checked':''}><span>${esc(choice.text)}</span></label>`).join('')}</div>`}</fieldset>${this.answerError?`<p id="courseAnswerError" class="course-answer-error" role="alert">${esc(this.answerError)}</p>`:''}<div class="course-answer-actions"><button type="button" class="text-link" data-course-action="example">예제 다시 보기</button><button type="button" class="button primary" data-course-action="check">답 확인</button></div></form>${submitted?this.feedback(lesson,record):'<p class="course-before-answer">제출 후 정답·근거·해설을 확인할 수 있습니다.</p>'}</div></div></div>`;
    }
    feedback(lesson,record) {
      const correct = record.lastAttempt.correct, practice = lesson.practice;
      const index = this.lessons.indexOf(lesson), last = index === this.lessons.length-1;
      const answer = practice.type==='amount' ? window.AuctionFormat.money(practice.answerValue) : practice.answerText;
      return `<section id="courseFeedback" class="course-feedback ${correct?'is-correct':'needs-review'}" data-correct="${correct}" role="status" tabindex="-1"><h3>${correct?'정답입니다.':'풀이를 다시 확인하세요.'}</h3><p class="course-correct-answer"><strong>정답</strong> ${esc(answer)}</p><p>${esc(practice.explanation)}</p><p class="course-first-attempt">첫 시도: ${record.firstAttempt.correct?'정답':'다시 확인'} · 제출 ${record.attempts}회</p><div class="course-feedback-navigation">${correct?`<button type="button" class="button primary" data-course-action="next">${last?'모의경매로 →':'다음 단원 →'}</button>`:'<button type="button" class="button" data-course-action="retry">다시 풀기</button>'}</div></section>`;
    }
    references(lesson) {
      if (!lesson.references?.length) return '';
      return `<details class="course-references"><summary>공식 안내</summary><ul>${lesson.references.map(reference => `<li><a href="${esc(reference.href)}" target="_blank" rel="noopener noreferrer">${esc(reference.name)} ↗</a><p>${esc(reference.note)}</p></li>`).join('')}</ul></details>`;
    }

    paint(focusSelector,resetScroll=false) {
      const root = document.querySelector('.auction-course');
      if (!root) return;
      const scroller = root.querySelector('#course-panel');
      const scrollTop = scroller?.scrollTop || 0;
      const pageScroller = root.closest('.page-content'), pageScrollTop = pageScroller?.scrollTop || 0;
      const template = document.createElement('template');
      template.innerHTML = this.render();
      root.replaceWith(template.content.firstElementChild);
      const nextScroller = document.querySelector('.auction-course #course-panel');
      if (nextScroller) nextScroller.scrollTop = resetScroll ? 0 : scrollTop;
      if (pageScroller && nextScroller && getComputedStyle(nextScroller).overflowY==='visible') pageScroller.scrollTop = resetScroll ? 0 : pageScrollTop;
      this.afterRender();
      if (focusSelector) document.querySelector(`.auction-course ${focusSelector}`)?.focus({preventScroll:!resetScroll});
    }
    afterRender() {
      const currentLesson = document.querySelector('.auction-course [data-course-lesson][aria-current="step"]');
      const lessonList = currentLesson?.closest('.course-lessons');
      if (currentLesson && lessonList && lessonList.scrollWidth>lessonList.clientWidth) {
        lessonList.scrollLeft = Math.max(0,currentLesson.offsetLeft-lessonList.offsetLeft-(lessonList.clientWidth-currentLesson.offsetWidth)/2);
      }
    }
    selectPane(pane,focusTab=false) {
      if (!PANES.some(item => item.id===pane)) return;
      this.progress.pane = pane;
      this.answerError = '';
      this.save();
      this.paint(focusTab?`[data-course-tab="${pane}"]`:'#courseLessonTitle',true);
    }
    selectLesson(id) {
      if (!this.lessons.some(lesson => lesson.id===id)) return;
      this.progress.lessonId = id;
      this.progress.pane = 'basics';
      this.answerError = '';
      this.save();
      this.paint('#courseLessonTitle',true);
    }
    check() {
      const lesson = this.lesson(), record = this.record();
      const result = this.grade(lesson.id,record.answer);
      if (!result.valid) {
        this.answerError = lesson.practice.type==='amount'?'0 이상의 금액을 만원 단위 숫자로 입력하세요.':'답을 선택하세요.';
        this.paint(lesson.practice.type==='amount'?'#courseAnswer':'input[name="courseAnswer"]');
        document.querySelector('.auction-course #courseAnswerError')?.scrollIntoView({block:'nearest'});
        return;
      }
      const attempt = {answer:record.answer,correct:result.correct};
      if (!record.firstAttempt) record.firstAttempt = {...attempt};
      record.lastAttempt = attempt;
      record.attempts = Math.min(10000,record.attempts+1);
      record.submitted = true;
      this.answerError = '';
      this.save();
      this.paint('#courseFeedback');
      document.querySelector('.auction-course #courseFeedback')?.scrollIntoView({block:'nearest'});
    }
    click(event) {
      const root = event.target.closest?.('.auction-course');
      if (!root) return;
      const button = event.target.closest('button');
      if (!button || button.disabled || !root.contains(button)) return;
      const {courseLesson,courseTab,courseAction,courseOpen} = button.dataset;
      if (courseLesson) return this.selectLesson(courseLesson);
      if (courseTab) return this.selectPane(courseTab,true);
      if (courseOpen) return this.callbacks.openPage?.(courseOpen);
      if (PANES.some(pane => pane.id===courseAction)) return this.selectPane(courseAction);
      if (courseAction==='check') return this.check();
      if (courseAction==='next') {
        if (!this.record().lastAttempt?.correct) return;
        const next = this.lessons[this.lessons.indexOf(this.lesson())+1];
        return next ? this.selectLesson(next.id) : this.callbacks.openPage?.('simulation');
      }
      if (courseAction==='retry') {
        const record = this.record();
        record.answer = '';record.submitted = false;this.answerError = '';this.save();
        this.paint(this.lesson().practice.type==='amount'?'#courseAnswer':'input[name="courseAnswer"]');
        document.querySelector('.auction-course .course-answer-form')?.scrollIntoView({block:'nearest'});
      } else if (courseAction==='export') this.exportProgress();
    }
    input(event) {
      if (!event.target.closest?.('.auction-course')) return;
      const input = event.target;
      if (input.name!=='courseAnswer' || (input.type==='radio' && !input.checked)) return;
      const record = this.record();
      if (record.answer===input.value) return;
      record.answer = input.value.slice(0,200);record.submitted = false;this.answerError = '';
      this.save();
      document.querySelector('.auction-course #courseFeedback')?.remove();
      document.querySelector('.auction-course #courseAnswerError')?.remove();
      input.removeAttribute('aria-invalid');
      if (input.id==='courseAnswer') input.setAttribute('aria-describedby','courseAmountHelp');
      document.querySelectorAll('.auction-course .course-practice .is-evidence').forEach(row => {
        row.classList.remove('is-evidence');row.removeAttribute('data-course-evidence');
      });
    }
    keydown(event) {
      const tab = event.target.closest?.('.auction-course [data-course-tab]');
      if (tab && ['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) {
        event.preventDefault();
        const index = PANES.findIndex(pane => pane.id===tab.dataset.courseTab);
        const next = event.key==='Home'?0:event.key==='End'?PANES.length-1:(index+(event.key==='ArrowRight'?1:-1)+PANES.length)%PANES.length;
        this.selectPane(PANES[next].id,true);
      } else if (event.key==='Enter' && event.target.id==='courseAnswer') {
        event.preventDefault();this.check();
      }
    }
    exportProgress() {
      const blob = new Blob([JSON.stringify(this.progress,null,2)],{type:'application/json'});
      const url = URL.createObjectURL(blob), anchor = document.createElement('a');
      anchor.href = url;anchor.download = 'auction-course-progress.json';anchor.click();
      setTimeout(() => URL.revokeObjectURL(url),1000);
    }
  }

  window.AuctionCourse = {create:callbacks => new Course(callbacks)};
})();
