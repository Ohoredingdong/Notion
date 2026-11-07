/* Fictional auction practice. This desk never writes the real notebook. */
(() => {
  'use strict';
  const KEY = 'auction-simulation-v1';
  const STAGES = ['자료', '권리 확인', '입찰 계산', '결과'];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
  const moneyText = value => window.AuctionFormat.money(value);
  const money = value => {
    const formatted = window.AuctionFormat.parts(value);
    return `${esc(formatted.text)}${formatted.unit?`<small>${esc(formatted.unit)}</small>`:''}`;
  };
  const labels = {bid:'입찰가',loan:'예상 대출',available:'가용 현금'};
  const documentNames = {sale:'매각명세서',register:'등기부등본',occupancy:'현황조사서',appraisal:'감정평가서',building:'건축물대장',fees:'관리비 메모',comparables:'거래·지역',fieldnotes:'현장·사진'};
  const documentName = document => documentNames[document.kind] || document.title.split(' · ')[0];
  const field = (label, value, className='') => `<div class="sim-metric ${className}"><span>${esc(label)}</span><strong>${money(value)}</strong></div>`;

  class Simulation {
    constructor(callbacks={}) {
      this.callbacks = callbacks;
      this.cases = window.AuctionSimulationData?.cases || [];
      this.persistent = true;
      this.notice = '';
      this.storageNotice = '';
      this.storedSnapshot = null;
      this.hint = false;
      this.state = {version:1,caseId:this.cases[0]?.id,stage:0,pane:'document',records:{}};
      this.restore();
      document.addEventListener('click', event => this.click(event));
      document.addEventListener('change', event => this.change(event));
      document.addEventListener('input', event => this.input(event));
      window.addEventListener('storage', event => this.storageChanged(event));
    }

    scenario() { return this.cases.find(item => item.id === this.state.caseId) || this.cases[0]; }
    record(scenario=this.scenario()) {
      if (!scenario) return null;
      if (!this.state.records[scenario.id]) {
        this.state.records[scenario.id] = {
          documentId:scenario.documents[0]?.id,reviewed:[],answers:{},quizIndex:0,
          inputs:{bid:String(scenario.defaults.bid),loan:String(scenario.defaults.loan),available:String(scenario.defaults.available)},
          note:'',decision:'',submitted:false
        };
      }
      return this.state.records[scenario.id];
    }
    restore() {
      try {
        const raw = localStorage.getItem(KEY);
        this.storedSnapshot = raw;
        if (!raw) return;
        const parsed = JSON.parse(raw);
        if (!parsed || parsed.version !== 1 || !parsed.records || typeof parsed.records !== 'object' || Array.isArray(parsed.records)) throw Error('Invalid saved practice');
        if (this.cases.some(item => item.id === parsed.caseId)) this.state.caseId = parsed.caseId;
        if (Number.isInteger(parsed.stage) && parsed.stage >= 0 && parsed.stage < 4) this.state.stage = parsed.stage;
        if (['document','analysis'].includes(parsed.pane)) this.state.pane = parsed.pane;
        for (const scenario of this.cases) {
          const saved = parsed.records[scenario.id];
          if (!saved || typeof saved !== 'object' || Array.isArray(saved)) continue;
          const target = this.record(scenario);
          const ids = scenario.documents.map(item => item.id);
          if (ids.includes(saved.documentId)) target.documentId = saved.documentId;
          if (Array.isArray(saved.reviewed)) target.reviewed = [...new Set(saved.reviewed.filter(id => ids.includes(id)))];
          if (Number.isInteger(saved.quizIndex) && saved.quizIndex >= 0 && saved.quizIndex < scenario.quiz.length) target.quizIndex = saved.quizIndex;
          for (const question of scenario.quiz) {
            const answer = saved.answers?.[question.id];
            if (answer && question.choices.some(choice => choice.id === answer.choiceId)) {
              target.answers[question.id] = {choiceId:answer.choiceId,checked:answer.checked === true};
            }
          }
          for (const key of Object.keys(labels)) {
            const value = saved.inputs?.[key];
            if (typeof value === 'string' && value.length < 96) target.inputs[key] = value;
            else if (typeof value === 'number' && Number.isFinite(value)) target.inputs[key] = String(value);
          }
          if (typeof saved.note === 'string') target.note = saved.note.slice(0,10000);
          if (['bid','hold'].includes(saved.decision)) target.decision = saved.decision;
          target.submitted = saved.submitted === true;
        }
      } catch (_) {
        // Keep a corrupt or inaccessible original untouched; work remains usable in memory.
        this.storageFailed('연습 기록을 읽지 못했어요. 원본은 보존했어요. 이 화면의 초안은 새로고침 전에 보관하세요.');
      }
    }
    statusMessage() {
      return this.storageNotice || this.notice || '연습 기록은 이 브라우저에 저장돼요. 내 노트와 별도예요.';
    }
    updateStatus() {
      const notice = document.querySelector('.simulation-workspace .sim-live');
      if (!notice) return;
      notice.classList.toggle('has-notice',Boolean(this.storageNotice || this.notice));
      notice.querySelector('[data-sim-storage-message]').textContent = this.statusMessage();
      notice.querySelector('[data-sim-action="export-progress"]').hidden = this.persistent;
    }
    storageFailed(message) {
      this.persistent = false;
      this.storageNotice = message;
      // Updating only the status preserves an active input, caret and its draft.
      this.updateStatus();
      return false;
    }
    storageChanged(event) {
      if (!this.persistent || (event.key !== KEY && event.key !== null)) return;
      try {
        // Queued events can be stale; compare the current value with our last successful write.
        if (event.storageArea && event.storageArea !== localStorage) return;
        if (localStorage.getItem(KEY) !== this.storedSnapshot) this.storageFailed('다른 탭에서 기록이 바뀌어 저장을 중지했어요. 원본·이 화면의 초안은 유지돼요. 새로고침 전 보관하세요.');
      } catch (_) {
        this.storageFailed('연습 기록을 읽지 못했어요. 이 화면의 초안은 새로고침 전에 보관하세요.');
      }
    }
    save() {
      if (!this.persistent) { this.updateStatus(); return false; }
      try {
        if (localStorage.getItem(KEY) !== this.storedSnapshot) return this.storageFailed('다른 탭에서 기록이 바뀌어 저장을 중지했어요. 원본·이 화면의 초안은 유지돼요. 새로고침 전 보관하세요.');
        const serialized = JSON.stringify(this.state);
        localStorage.setItem(KEY,serialized);
        this.storedSnapshot = serialized;
        return true;
      }
      catch (_) {
        return this.storageFailed('저장하지 못했어요. 이 화면의 초안은 유지돼요. 새로고침 전 보관하세요.');
      }
    }
    calculation() {
      const scenario = this.scenario(), record = this.record();
      if (!window.AuctionModel?.calculate || !scenario) return {valid:false,errors:['계산 모듈을 불러오지 못했어요. 새로고침 후 다시 확인해 주세요.']};
      return AuctionModel.calculate({...scenario.defaults,...record.inputs});
    }
    unresolved() {
      const answer = this.scenario().answer;
      return answer.riskLevel === 'hold' || this.scenario().financialAssumptionsConfirmed === false || answer.financialAssumptionsConfirmed === false || answer.assumedCost === null;
    }

    render() {
      if (!this.cases.length) return '<section class="simulation-workspace"><p role="alert">자료를 불러오지 못했어요. 새로고침해 주세요. 내 노트는 유지돼요.</p></section>';
      const scenario = this.scenario(), record = this.record();
      return `<div class="simulation-workspace" data-sim-stage="${this.state.stage}" data-pane="${this.state.pane}">
        <div class="sim-toolbar"><label class="sim-case-picker" for="simulationCase"><span>연습 물건</span><select id="simulationCase">${this.cases.map(item => `<option value="${esc(item.id)}" ${item.id===scenario.id?'selected':''}>${esc(item.title)}</option>`).join('')}</select></label><span class="sim-fiction-label">서류 8종 · 현장 사진</span><button type="button" class="button small sim-download" data-sim-action="download">서류 받기 ↓</button></div>
        <nav class="sim-stages" aria-label="모의경매 연습 단계">${STAGES.map((title,index) => `<button type="button" data-sim-go-stage="${index}" aria-current="${this.state.stage===index?'step':'false'}"><span>${index+1}</span>${title}</button>`).join('')}</nav>
        <div class="sim-pane-tabs" role="group" aria-label="모의경매 화면 선택"><button type="button" data-sim-pane="document" aria-pressed="${this.state.pane==='document'}">서류·사진</button><button type="button" data-sim-pane="analysis" aria-pressed="${this.state.pane==='analysis'}">${esc(STAGES[this.state.stage])}</button></div>
        <div class="sim-layout">${this.documentPane(scenario,record)}<section class="sim-card sim-analysis" aria-label="연습 도우미"><div class="sim-scroll" data-sim-scroll="analysis">${[()=>this.overview(scenario,record),()=>this.questions(scenario,record),()=>this.bidding(scenario,record),()=>this.results(scenario,record)][this.state.stage]()}</div>${this.footer()}</section></div>
        <div class="sim-live ${this.storageNotice||this.notice?'has-notice':''}" role="status" aria-live="polite"><span data-sim-storage-message>${esc(this.statusMessage())}</span><button type="button" class="text-link" data-sim-action="export-progress" ${this.persistent?'hidden':''}>연습 기록 보관 ↓</button></div>
      </div>`;
    }

    documentPane(scenario,record) {
      const selected = scenario.documents.find(item => item.id === record.documentId) || scenario.documents[0];
      const isField = selected.kind === 'fieldnotes' || selected.id.includes('field') || selected.kind === '현장 조사';
      return `<section class="sim-card sim-documents" aria-label="가상 경매 서류와 현장 사진"><div class="sim-document-tabs" role="group" aria-label="서류 선택">${scenario.documents.map((item,index) => `<button type="button" data-sim-document="${esc(item.id)}" aria-pressed="${item.id===selected.id}" title="${esc(item.title)}" aria-label="${esc(item.title)}"><span>${String(index+1).padStart(2,'0')}</span>${esc(documentName(item))}${record.reviewed.includes(item.id)?'<i aria-label="확인 기록함">✓</i>':''}</button>`).join('')}</div><div class="sim-scroll sim-paper" data-sim-scroll="document"><div class="sim-paper-tag">가상 자료 · 실제 사건 아님</div><header class="sim-document-heading"><h2>${esc(selected.title)}</h2><p>${esc(this.documentPurpose(selected))}</p></header>${isField?this.photos(scenario):''}${this.documentSections(selected)}<p class="sim-document-disclaimer">미기재 권리·비용은 별도 확인이 필요해요.</p></div><footer class="sim-document-footer"><span>${record.reviewed.length} / ${scenario.documents.length}종 확인</span><button type="button" class="button small ${record.reviewed.includes(selected.id)?'':'primary'}" data-sim-action="review-document">${record.reviewed.includes(selected.id)?'확인 취소':'확인'}</button></footer></section>`;
    }
    documentSections(document) {
      return document.sections.map(section => `<section class="sim-document-section"><h3>${esc(section.title)}</h3><dl>${section.rows.map(row => `<div${row.focus&&this.state.stage===1&&this.hint?' class="sim-row-focus"':''}><dt>${esc(row.label)}</dt><dd>${esc(row.value)}</dd></div>`).join('')}</dl></section>`).join('');
    }
    documentPurpose(document) {
      return document.sourceExplanation.split('학습 역할:').pop().trim();
    }
    photoStyle(scenario,key='exterior') {
      const set = scenario.photoSet;
      if (!set || !/^\.\/assets\/auction-practice\/[a-z0-9_-]+\.(?:png|webp|jpe?g)$/i.test(set.src)
        || !Number.isInteger(set.columns) || set.columns < 1 || set.columns > 8
        || !Number.isInteger(set.rows) || set.rows < 1 || set.rows > 8) return '';
      const position = set.positions?.[key];
      if (typeof position !== 'string') return '';
      const axes = position.trim().split(/\s+/);
      if (axes.length !== 2 || axes.some(axis => !/^\d+(?:\.\d+)?%$/.test(axis) || Number(axis.slice(0,-1)) > 100)) return '';
      return `background-image:url('${set.src}');background-size:${set.columns*100}% ${set.rows*100}%;background-position:${position}`;
    }
    photos(scenario) {
      return `<section class="sim-photos" aria-label="가상 현장 사진">${scenario.observations.map(item => {
        const style = this.photoStyle(scenario,item.photoKey);
        return `<figure><div class="sim-photo ${style?'':'sim-photo-missing'}" role="img" aria-label="${esc(item.title)} · AI 가상 이미지" data-sim-photo-key="${esc(item.photoKey)}" data-sim-photo-source="${esc(scenario.photoSet?.src||'')}" style="${esc(style)}">${style?'':'이미지 미등록'}</div><figcaption><strong>${esc(item.title)}</strong><p>${esc(item.text)}</p><span>AI로 만든 가상 이미지 · 실매물 사진 아님</span></figcaption></figure>`;
      }).join('')}</section>`;
    }
    overview(scenario,record) {
      return `<div class="sim-section-heading"><h2>${esc(scenario.title)}</h2><p>${esc(scenario.summary)}</p></div>
        <p class="sim-address">${esc(scenario.address)} · 전용 ${esc(scenario.area)}㎡</p>
        <div class="sim-numbers">${field('감정가',scenario.appraised)}${field('최저 매각가격',scenario.minimum)}</div>
        <div class="sim-note"><strong>8종 서류를 비교해 보세요.</strong><p>날짜·권리·점유를 확인하고, 모르는 내용은 남겨두세요.</p></div>
        <div class="sim-source-list" aria-label="준비된 서류">${scenario.documents.map((item,index) => `<button type="button" data-sim-document="${esc(item.id)}" title="${esc(item.title)}"><span>${String(index+1).padStart(2,'0')}</span><strong>${esc(documentName(item))}</strong><em>${record.reviewed.includes(item.id)?'확인함':'보기'}</em></button>`).join('')}</div>
        <button type="button" class="sim-photo-link" data-sim-action="photos"><span class="sim-photo-preview" aria-hidden="true" style="${esc(this.photoStyle(scenario))}"></span><span><strong>사진·현장 메모</strong><small>AI로 만든 가상 이미지 · 실매물 사진 아님</small></span><b aria-hidden="true">↗</b></button>`;
    }
    questions(scenario,record) {
      const question = scenario.quiz[record.quizIndex];
      if (!question) return '<p>권리 확인 문제가 준비되지 않았어요. 서류를 먼저 확인해 주세요.</p>';
      const answer = record.answers[question.id], checked = answer?.checked === true;
      const correct = checked && answer.choiceId === question.answerId;
      const source = scenario.documents.find(item => item.id === question.documentId);
      const completed = scenario.quiz.filter(item => record.answers[item.id]?.checked).length;
      return `<div class="sim-section-heading"><h2>서류로 권리 확인</h2><p>모르는 권리·비용은 미확인으로 남겨두세요.</p></div><div class="sim-question-progress"><span>질문 ${record.quizIndex+1} / ${scenario.quiz.length}</span><span>해설 ${completed}개</span></div><div class="sim-question-dots" role="group" aria-label="권리 확인 문제 선택">${scenario.quiz.map((item,index) => `<button type="button" data-sim-question="${index}" aria-pressed="${index===record.quizIndex}" aria-label="${index+1}번 문제${record.answers[item.id]?.checked?', 해설 확인함':''}">${index+1}${record.answers[item.id]?.checked?' ✓':''}</button>`).join('')}</div><fieldset class="sim-question"><legend>${esc(question.question)}</legend>${question.choices.map(choice => `<label><input type="radio" name="simulation-choice" data-sim-choice="${esc(question.id)}" value="${esc(choice.id)}" ${answer?.choiceId===choice.id?'checked':''}><span>${esc(choice.text)}</span></label>`).join('')}</fieldset><div class="sim-question-actions"><button type="button" class="text-link" data-sim-action="hint">${this.hint?'힌트 접기':'힌트'}</button><button type="button" class="button primary small" data-sim-action="check-answer" ${answer?.choiceId?'':'disabled'}>해설 보기</button></div>${this.hint&&!checked?`<div class="sim-hint"><strong>${esc(source?documentName(source):'관련 서류')}에서 찾아보세요.</strong><p>날짜·금액·예외·빠진 기재를 비교하세요.</p><button type="button" class="text-link" data-sim-document="${esc(question.documentId)}">서류 보기 →</button></div>`:''}${checked?`<div class="sim-feedback ${correct?'correct':'review'}" role="status"><strong>${correct?'근거를 찾았어요.':'기재를 다시 확인하세요.'}</strong><p>${esc(question.explanation)}</p><button type="button" class="text-link" data-sim-document="${esc(question.documentId)}">${esc(source?documentName(source):'서류')} 보기 →</button></div>`:'<p class="sim-answer-placeholder">답을 고른 뒤 해설을 확인하세요.</p>'}<div class="sim-quiz-nav"><button type="button" class="button small" data-sim-question="${Math.max(0,record.quizIndex-1)}" ${record.quizIndex===0?'disabled':''}>이전 문제</button>${record.quizIndex<scenario.quiz.length-1?`<button type="button" class="button small" data-sim-question="${record.quizIndex+1}">다음 문제 →</button>`:'<button type="button" class="button small" data-sim-go-stage="2">입찰 계산 →</button>'}</div>`;
    }
    bidding(scenario,record) {
      const assumptions = [
        ['보증금 기준','최저 매각가 × '+scenario.defaults.depositRate+'%'],
        ['취득 관련 세율',scenario.defaults.acquisitionRate+'% (연습 가정)'],
        ['등기·법무',moneyText(scenario.defaults.legal)], ['수리',moneyText(scenario.defaults.repairs)],
        ['명도',moneyText(scenario.defaults.eviction)], ['체납 관리비',moneyText(scenario.defaults.arrears)],
        ['인수 금액',this.unresolved()&&scenario.answer.assumedCost===null?'미확인 · 계산에는 0 입력':moneyText(scenario.defaults.assumed)],
        ['대출 이자',scenario.defaults.loanRate+'% · '+scenario.defaults.months+'개월'],
        ['현금 예비비',moneyText(scenario.defaults.reserve)+' · 손익에서 제외'],
        ['예상 매도가',moneyText(scenario.defaults.sale)], ['보수적 매도가',moneyText(scenario.defaults.downside)],
        ['매도 비용',scenario.defaults.sellingRate+'% + 세금 '+moneyText(scenario.defaults.saleTax)],
        ['목표 이익',moneyText(scenario.defaults.targetProfit)]
      ];
      return `<div class="sim-section-heading"><h2>입찰가와 필요 현금</h2><p>입력 단위: 만원 · 실제 입찰은 진행되지 않아요.</p></div>
        ${this.unresolved()?'<div class="sim-warning"><strong>미확인 비용이 있어요.</strong><p>인수액·수리비가 빠진 계산입니다. 확인 전까지 입찰을 보류하세요.</p></div>':''}
        <div class="sim-bid-inputs">${Object.entries(labels).map(([key,label]) => `<label for="simulation-${key}">${label}<span><input id="simulation-${key}" data-sim-number="${key}" type="number" min="0" step="any" inputmode="decimal" value="${esc(record.inputs[key])}"><em>만원</em></span></label>`).join('')}</div>
        <div id="simulationCalculation" aria-live="polite" aria-atomic="true">${this.calculationHTML(this.calculation())}</div>
        <details class="sim-cost-assumptions"><summary>비용 가정</summary><dl>${assumptions.map(([label,value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl><p>세금·대출·매도가는 연습 가정입니다. 노트의 투자금 계산에서 조정하세요.</p></details>
        <fieldset class="sim-decision"><legend>내 판단</legend><label><input type="radio" name="simulation-decision" data-sim-decision value="bid" ${record.decision==='bid'?'checked':''}><span>추가 확인 후 입찰 검토</span></label><label><input type="radio" name="simulation-decision" data-sim-decision value="hold" ${record.decision==='hold'?'checked':''}><span>보류 · 추가 조사</span></label></fieldset>
        <label class="sim-note-input" for="simulationNote">판단 근거<textarea id="simulationNote" maxlength="10000" placeholder="근거 서류, 미확인 사항, 입찰 상한을 적어보세요.">${esc(record.note)}</textarea></label>
        <button type="button" class="button primary sim-submit" data-sim-action="submit">결과 보기 →</button><p class="sim-small">경쟁 입찰·낙찰 결과는 가정하지 않아요.</p>`;
    }
    calculationHTML(result) {
      if (!result.valid) return `<div class="sim-calculation-error" role="alert"><strong>입력값을 확인하세요.</strong><ul>${result.errors.map(error => `<li>${esc(error)}</li>`).join('')}</ul></div>`;
      const depositGap = result.depositGap ?? Math.max(0,result.deposit-result.input.available);
      const ceiling = window.AuctionFormat.floorBid(result.maxBid);
      const resetLoan = AuctionModel.compareAmounts(result.maxBid,result.input.loan) < 0;
      const belowMinimum = AuctionModel.compareAmounts(result.maxBid,result.input.minimum) < 0;
      return `<div class="sim-cash-result"><span>순투입 현금 · 예비비 포함${this.unresolved()?' · 미확인 비용 제외':''}</span><strong data-sim-result="cashNeeded">${money(result.cashNeeded)}</strong><p>낙찰가 + 취득·보유 비용 − 대출 + 예비비</p></div>
        <div class="sim-calculation-rows">
          <div><span>입찰 보증금</span><strong data-sim-result="deposit">${money(result.deposit)}</strong></div>
          <div><span>취득·보유 비용</span><strong data-sim-result="costs">${money(result.costs)}</strong></div>
          <div><span>순투입 현금 부족</span><strong data-sim-result="cashGap" class="${result.cashGap>0?'sim-negative':''}">${money(result.cashGap)}</strong></div>
          <div><span>선납 보증금 부족</span><strong data-sim-result="depositGap" class="${depositGap>0?'sim-negative':''}">${money(depositGap)}</strong></div>
          <div><span>예상 손익</span><strong data-sim-result="profit" class="${result.profit<0?'sim-negative':''}">${money(result.profit)}</strong></div>
          <div><span>보수적 손익</span><strong data-sim-result="downsideProfit" class="${result.downsideProfit<0?'sim-negative':''}">${money(result.downsideProfit)}</strong></div>
          <div><span>${resetLoan?'대출 재설정 참고값':'목표 이익 기준 상한'}</span><strong data-sim-result="maxBid">${money(ceiling)}</strong></div>
        </div>${resetLoan||belowMinimum?`<p class="sim-ceiling-note">${resetLoan?'현재 대출액으로는 유효한 입찰 상한이 없어요. 대출액을 다시 설정하세요.':'최저가에서도 목표 이익에 미달해요.'}</p>`:''}<p class="sim-small">보증금은 낙찰대금에 포함돼요. 두 부족액은 더하지 않아요. 대출 실행일·지급 일정은 별도 확인하세요. 상한은 대출·이자를 고정한 계산이며 손익은 추정치예요.</p>`;
    }
    results(scenario,record) {
      const answer = scenario.answer, result = this.calculation();
      const checked = scenario.quiz.filter(question => record.answers[question.id]?.checked);
      const correct = checked.filter(question => record.answers[question.id].choiceId === question.answerId);
      const missing = scenario.documents.filter(document => !record.reviewed.includes(document.id));
      const unresolved = this.unresolved();
      const cashInsufficient = result.valid && result.cashGap > 0;
      const depositGap = result.valid ? result.depositGap ?? Math.max(0,result.deposit-result.input.available) : 0;
      const loss = result.valid && result.profit < 0;
      const targetMissed = result.valid && AuctionModel.compareAmounts(result.profit,result.input.targetProfit) < 0;
      const downsideLoss = result.valid && result.downsideProfit < 0;
      const financialHold = cashInsufficient || depositGap > 0 || targetMissed || downsideLoss;
      const hold = unresolved || !result.valid || financialHold || missing.length > 0 || correct.length < scenario.quiz.length;
      const title = financialHold?'입찰가·자금을 다시 점검하세요.':hold?'확인 전까지 보류하세요.':'조건을 더 확인해 보세요.';
      const score = `<div class="sim-learning-score"><div><span>서류 확인</span><strong>${record.reviewed.length}<small> / ${scenario.documents.length}종</small></strong></div><div><span>해설 확인</span><strong>${checked.length}<small> / ${scenario.quiz.length}개</small></strong></div><div><span>정답</span><strong>${correct.length}<small> / ${checked.length}개</small></strong></div></div>`;
      if (!record.submitted) {
        return `<div class="sim-section-heading"><h2>내 판단을 먼저 남겨주세요.</h2><p>입찰가·판단을 제출하면 해설을 볼 수 있어요.</p></div><div class="sim-note"><p>확인한 서류와 입찰 근거를 적어보세요.</p><button type="button" class="button primary small" data-sim-go-stage="2">입찰 계산으로 →</button></div>${score}<p class="sim-small">학습 기록이며 투자 성공 가능성을 뜻하지 않아요.</p>`;
      }
      const reasons = [];
      if (!result.valid) reasons.push('입력 오류를 수정하세요. 유효하지 않은 금액으로 판단할 수 없어요.');
      if (unresolved) reasons.push('미확인 권리·인수액이 있어요. 계산상 이익이 나더라도 보류하세요. 빠진 비용을 0으로 확정하지 마세요.');
      if (cashInsufficient) reasons.push('예상 순투입 현금이 가용 현금보다 '+moneyText(result.cashGap)+' 부족해요.');
      if (depositGap > 0) reasons.push('선납 보증금이 가용 현금보다 '+moneyText(depositGap)+' 부족해요. 대출 전 현금을 준비해야 해요.');
      if (loss) reasons.push('예상 손익 '+moneyText(result.profit)+': 손실입니다. 입찰가·비용을 다시 계산하세요.');
      else if (targetMissed) reasons.push('목표 이익까지 '+moneyText(result.input.targetProfit-result.profit)+' 부족해요(예상 '+moneyText(result.profit)+' / 목표 '+moneyText(result.input.targetProfit)+').');
      if (downsideLoss) reasons.push('보수적 손익이 '+moneyText(result.downsideProfit)+'로 손실이에요. 가격 하락·추가 비용을 재검토하세요.');
      if (missing.length) reasons.push('미확인 서류 '+missing.length+'종을 대조하세요.');
      if (checked.length > correct.length) reasons.push('틀린 문제 '+(checked.length-correct.length)+'개를 서류·해설과 다시 비교하세요.');
      if (checked.length < scenario.quiz.length) reasons.push('미확인 해설 '+(scenario.quiz.length-checked.length)+'개를 확인하세요.');
      return `<div class="sim-section-heading"><h2>판단 비교</h2><p>자금·권리·놓친 항목을 확인하세요. 투자 승인이나 수익 보장이 아니에요.</p></div>
        ${score}
        <div class="sim-result-status ${hold?'hold':'review'}"><span>${hold?'보류 · 추가 확인':'조건부 검토'}</span><h3>${title}</h3><p>${hold?'아래 항목을 해결할 때까지 보류하세요.':esc(answer.plainConclusion)}</p>${reasons.length?`<ul class="sim-result-reasons">${reasons.map(reason => `<li>${esc(reason)}</li>`).join('')}</ul>`:''}</div>
        <section class="sim-recap"><h3>내 판단</h3><div class="sim-recap-row"><span>${record.decision==='hold'?'보류 · 추가 조사':'추가 확인 후 입찰 검토'}</span><strong>${money(result.valid?result.input.bid:NaN)}</strong></div><p class="sim-user-note">${esc(record.note||'작성한 근거가 없어요.')}</p></section>
        <section class="sim-findings"><h3>핵심 근거</h3><ul>${answer.mainFindings.map(text => `<li>${esc(text)}</li>`).join('')}</ul></section>
        <section class="sim-findings"><h3>입찰 전 확인</h3><ul>${answer.nextChecks.map(text => `<li>${esc(text)}</li>`).join('')}${missing.length?`<li>미확인 자료: ${missing.map(item => esc(documentName(item))).join(', ')}</li>`:''}${correct.length<scenario.quiz.length?'<li>풀지 않았거나 틀린 문제를 서류·해설과 다시 대조하세요.</li>':''}</ul></section>
        <div class="sim-import"><strong>연습 내용을 노트로 옮기기</strong><p>새 연습 노트를 만들며 기존 물건은 유지해요.</p><button type="button" class="button small" data-sim-action="copy">노트로 복사</button><button type="button" class="text-link" data-sim-go-stage="2">다시 계산 →</button></div>`;
    }
    footer() {
      return `<footer class="sim-navigation"><button type="button" class="button small" data-sim-go-stage="${Math.max(0,this.state.stage-1)}" ${this.state.stage===0?'disabled':''}>이전</button><span>${this.state.stage+1} / 4</span>${this.state.stage<3?`<button type="button" class="button small ${this.state.stage===0?'primary':''}" data-sim-go-stage="${this.state.stage+1}">${esc(STAGES[this.state.stage+1])} →</button>`:'<button type="button" class="button small" data-sim-go-stage="0">다시 보기</button>'}</footer>`;
    }

    paint(focusSelector) {
      const old = document.querySelector('.simulation-workspace');
      if (!old) return;
      const scroll = Object.fromEntries([...old.querySelectorAll('[data-sim-scroll]')].map(element => [element.dataset.simScroll,element.scrollTop]));
      const template = document.createElement('template');
      template.innerHTML = this.render();
      const fresh = template.content.firstElementChild;
      old.replaceWith(fresh);
      for (const element of fresh.querySelectorAll('[data-sim-scroll]')) element.scrollTop = scroll[element.dataset.simScroll] || 0;
      if (focusSelector) fresh.querySelector(focusSelector)?.focus({preventScroll:true});
    }
    goStage(value) {
      const stage = Number(value);
      if (!Number.isInteger(stage) || stage < 0 || stage > 3) return;
      this.state.stage = stage;
      this.state.pane = stage===0?'document':'analysis';
      this.hint = false; this.notice = ''; this.save();
      this.paint(`.sim-stages [data-sim-go-stage="${stage}"]`);
      document.querySelector('.simulation-workspace [data-sim-scroll="analysis"]')?.scrollTo(0,0);
    }
    openDocument(id) {
      if (!this.scenario().documents.some(item => item.id === id)) return;
      this.record().documentId = id; this.state.pane = 'document'; this.save();
      this.paint(`.sim-document-tabs [data-sim-document="${id}"]`);
      document.querySelector('.simulation-workspace [data-sim-scroll="document"]')?.scrollTo(0,0);
    }
    click(event) {
      const root = event.target.closest?.('.simulation-workspace');
      if (!root) return;
      const button = event.target.closest('button');
      if (!button || button.disabled) return;
      const data = button.dataset, record = this.record(), scenario = this.scenario();
      if (data.simGoStage !== undefined) return this.goStage(data.simGoStage);
      if (data.simDocument) return this.openDocument(data.simDocument);
      if (data.simPane) {
        this.state.pane = data.simPane; this.save();
        root.dataset.pane = data.simPane;
        root.querySelectorAll('[data-sim-pane]').forEach(element => element.setAttribute('aria-pressed',String(element.dataset.simPane===data.simPane)));
        return;
      }
      if (data.simQuestion !== undefined) {
        const index = Number(data.simQuestion);
        if (!Number.isInteger(index) || index < 0 || index >= scenario.quiz.length) return;
        record.quizIndex = index; this.hint = false; this.save();
        this.paint(`.sim-question-dots [data-sim-question="${index}"]`);
        return;
      }
      if (data.simAction === 'review-document') {
        record.reviewed = record.reviewed.includes(record.documentId)?record.reviewed.filter(id => id!==record.documentId):[...record.reviewed,record.documentId];
        this.notice = record.reviewed.includes(record.documentId)?'확인 기록을 남겼어요.':'확인 기록을 취소했어요.';
        this.save(); this.paint('[data-sim-action="review-document"]');
      } else if (data.simAction === 'hint') {
        this.hint = !this.hint; this.paint('[data-sim-action="hint"]');
      } else if (data.simAction === 'check-answer') {
        const question = scenario.quiz[record.quizIndex], answer = record.answers[question.id];
        if (!answer || !question.choices.some(choice => choice.id===answer.choiceId)) return;
        answer.checked = true; this.hint = false; this.save(); this.paint('[data-sim-action="check-answer"]');
      } else if (data.simAction === 'photos') {
        const document = scenario.documents.find(item => item.kind==='fieldnotes' || item.id.includes('field')) || scenario.documents[scenario.documents.length-1];
        this.openDocument(document.id);
      } else if (data.simAction === 'submit') {
        const result = this.calculation();
        if (!result.valid || !record.decision) {
          this.notice = !result.valid?'입찰가·대출·가용 현금을 확인하세요.':'내 판단을 선택하세요.';
          this.paint(!result.valid?'[data-sim-number="bid"]':'[data-sim-decision]');
          return;
        }
        record.submitted = true; this.save(); this.goStage(3);
      } else if (data.simAction === 'download') this.download();
      else if (data.simAction === 'export-progress') this.exportProgress();
      else if (data.simAction === 'copy') {
        if (!this.calculation().valid) {
          this.notice = '입력 오류가 있어 복사할 수 없어요. 입찰 계산에서 수정하세요.';
          this.paint('[data-sim-action="copy"]'); return;
        }
        if (typeof this.callbacks.copyToNotebook !== 'function') {
          this.notice = '노트 복사를 연결하지 못했어요. 연습 기록은 유지돼요.';
          this.paint('[data-sim-action="copy"]'); return;
        }
        try {
          const result = this.calculation();
          const copy = JSON.parse(JSON.stringify(scenario));
          copy.defaults = {...copy.defaults,...record.inputs};
          copy.practiceNote = record.note;
          copy.practiceDecision = record.decision;
          copy.practiceCalculationValid = result.valid;
          this.callbacks.copyToNotebook(copy);
        } catch (_) {
          this.notice = '복사하지 못했어요. 원래 노트와 연습 기록은 유지돼요.';
          this.paint('[data-sim-action="copy"]');
        }
      }
    }
    change(event) {
      if (!event.target.closest?.('.simulation-workspace')) return;
      const input = event.target, record = this.record();
      if (input.id === 'simulationCase') {
        if (!this.cases.some(item => item.id === input.value)) return;
        this.state.caseId = input.value; this.state.stage = 0; this.state.pane = 'document';
        this.notice = ''; this.hint = false; this.save(); this.paint('#simulationCase');
      } else if (input.dataset.simChoice) {
        const question = this.scenario().quiz.find(item => item.id === input.dataset.simChoice);
        if (!question || !question.choices.some(choice => choice.id===input.value)) return;
        record.answers[question.id] = {choiceId:input.value,checked:false};
        this.hint = false; this.save(); this.paint(`[data-sim-choice="${question.id}"][value="${input.value}"]`);
      } else if (input.hasAttribute('data-sim-decision') && ['bid','hold'].includes(input.value)) {
        record.decision = input.value; record.submitted = false; this.save();
      }
    }
    input(event) {
      if (!event.target.closest?.('.simulation-workspace')) return;
      const input = event.target, record = this.record();
      if (Object.hasOwn(labels,input.dataset.simNumber)) {
        record.inputs[input.dataset.simNumber] = input.value; record.submitted = false;
        this.save();
        const result = document.querySelector('.simulation-workspace #simulationCalculation');
        if (result) result.innerHTML = this.calculationHTML(this.calculation());
      } else if (input.id === 'simulationNote') {
        record.note = input.value.slice(0,10000); record.submitted = false; this.save();
      }
    }
    download() {
      const scenario = this.scenario();
      const sections = scenario.documents.map(item => `<article><p class="fiction">가상 학습 자료 · 실제 공적 서류 아님</p><h2>${esc(item.title)}</h2><p>${esc(item.sourceExplanation)}</p>${this.documentSections(item)}</article>`).join('');
      const html = `<!doctype html><html lang="ko"><meta charset="utf-8"><title>${esc(scenario.title)} · 가상 서류 세트</title><style>body{font:15px/1.7 sans-serif;max-width:850px;margin:40px auto;padding:0 20px;color:#191f28}h1{font-size:26px}h2{font-size:23px}h3{font-size:17px}article{page-break-before:always;margin:45px 0}.fiction{color:#95610f;background:#fff8e8;padding:12px}dl{border-top:1px solid #ddd}dl>div{display:grid;grid-template-columns:150px 1fr;border-bottom:1px solid #ddd;padding:12px;gap:18px}dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}dt{color:#626c7b}@media print{body{margin:0;max-width:none}article{break-before:page}}</style><h1>${esc(scenario.title)} · 모의경매 서류 세트</h1><p class="fiction">모든 사건·인물·금액·서류는 학습을 위한 가상 자료입니다. 실제 물건에 사용하지 마세요.</p><p>${esc(scenario.address)} · ${esc(scenario.summary)}</p><p>서류 ${scenario.documents.length}종 · 브라우저에서 열어 인쇄하거나 PDF로 저장할 수 있어요. 사진은 웹 연습 화면에서 확인해 주세요.</p>${sections}</html>`;
      try {
        const url = URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));
        const link = document.createElement('a'); link.href = url; link.download = `auction-practice-${scenario.id.replace(/[^a-zA-Z0-9_-]/g,'')}.html`; link.click();
        setTimeout(() => URL.revokeObjectURL(url),1000);
        this.notice = '서류 8종을 저장했어요. 파일을 열어 인쇄·PDF 저장할 수 있어요.';
      } catch (_) { this.notice = '서류를 받지 못했어요. 이 화면에서 계속 확인할 수 있어요.'; }
      this.paint('[data-sim-action="download"]');
    }
    exportProgress() {
      try {
        const payload = {type:'auction-simulation-progress',version:1,fictional:true,exportedAt:new Date().toISOString(),progress:this.state};
        const url = URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json;charset=utf-8'}));
        const link = document.createElement('a');
        link.href = url; link.download = 'auction-simulation-progress.json'; link.click();
        setTimeout(() => URL.revokeObjectURL(url),1000);
      } catch (_) {
        this.storageNotice = '파일을 만들지 못했어요. 새로고침 전 메모·금액을 직접 복사하세요. 저장된 원본은 유지돼요.';
        this.updateStatus();
      }
    }
  }
  window.AuctionSimulation = Object.freeze({create:callbacks => new Simulation(callbacks)});
})();
