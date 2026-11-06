/* Fictional auction practice. This desk never writes the real notebook. */
(() => {
  'use strict';
  const KEY = 'auction-simulation-v1';
  const STAGES = ['자료 모음', '권리 확인', '모의 입찰', '결과 해설'];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
  const amount = value => Number.isFinite(value) ? value.toLocaleString('ko-KR',{maximumFractionDigits:2}) : '미확인';
  const money = value => `${amount(value)}<small>만원</small>`;
  const photoPosition = {exterior:'0% 0%', entrance:'50% 0%', interior:'100% 0%', damage:'0% 100%', neighborhood:'50% 100%', corridor:'100% 100%'};
  const labels = {bid:'모의 입찰가',loan:'예상 대출금',available:'내 가용 현금'};
  const documentNames = {sale:'매각명세서',register:'등기부등본',occupancy:'현황조사서',appraisal:'감정평가서',building:'건축물대장',fees:'관리비 메모',comparables:'거래·지역',fieldnotes:'현장·사진'};
  const documentName = document => documentNames[document.kind] || document.title.split(' · ')[0];
  const field = (label, value, className='') => `<div class="sim-metric ${className}"><span>${esc(label)}</span><strong>${money(value)}</strong></div>`;

  class Simulation {
    constructor(callbacks={}) {
      this.callbacks = callbacks;
      this.cases = window.AuctionSimulationData?.cases || [];
      this.persistent = true;
      this.notice = '';
      this.hint = false;
      this.state = {version:1,caseId:this.cases[0]?.id,stage:0,pane:'document',records:{}};
      this.restore();
      document.addEventListener('click', event => this.click(event));
      document.addEventListener('change', event => this.change(event));
      document.addEventListener('input', event => this.input(event));
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
        this.persistent = false;
        this.notice = '저장된 연습 기록을 읽지 못했어요. 원본은 보존하고, 이번 연습은 이 화면에서만 유지해요.';
      }
    }
    save() {
      if (!this.persistent) return;
      try { localStorage.setItem(KEY,JSON.stringify(this.state)); }
      catch (_) {
        this.persistent = false;
        this.notice = '브라우저에 연습 기록을 저장하지 못했어요. 이번 화면에서는 계속 연습할 수 있어요.';
        const notice = document.querySelector('.simulation-workspace .sim-live');
        if (notice) notice.textContent = this.notice;
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
      if (!this.cases.length) return '<section class="simulation-workspace"><p role="alert">모의경매 자료를 불러오지 못했어요. 새로고침 후 확인해 주세요. 실제 노트는 변경되지 않았어요.</p></section>';
      const scenario = this.scenario(), record = this.record();
      return `<div class="simulation-workspace" data-sim-stage="${this.state.stage}" data-pane="${this.state.pane}">
        <div class="sim-toolbar"><label class="sim-case-picker" for="simulationCase"><span>연습 물건</span><select id="simulationCase">${this.cases.map(item => `<option value="${esc(item.id)}" ${item.id===scenario.id?'selected':''}>${esc(item.title)}</option>`).join('')}</select></label><span class="sim-fiction-label">가상 사건 · 실제 투자 대상 아님</span><button type="button" class="button small sim-download" data-sim-action="download">서류 세트 받기 ↓</button></div>
        <nav class="sim-stages" aria-label="모의경매 연습 단계">${STAGES.map((title,index) => `<button type="button" data-sim-go-stage="${index}" aria-current="${this.state.stage===index?'step':'false'}"><span>${index+1}</span>${title}</button>`).join('')}</nav>
        <div class="sim-pane-tabs" role="group" aria-label="모의경매 화면 선택"><button type="button" data-sim-pane="document" aria-pressed="${this.state.pane==='document'}">서류 · 현장 사진</button><button type="button" data-sim-pane="analysis" aria-pressed="${this.state.pane==='analysis'}">${esc(STAGES[this.state.stage])} 도우미</button></div>
        <div class="sim-layout">${this.documentPane(scenario,record)}<section class="sim-card sim-analysis" aria-label="연습 도우미"><div class="sim-scroll" data-sim-scroll="analysis">${[()=>this.overview(scenario,record),()=>this.questions(scenario,record),()=>this.bidding(scenario,record),()=>this.results(scenario,record)][this.state.stage]()}</div>${this.footer()}</section></div>
        <p class="sim-live ${this.notice?'has-notice':''}" role="status" aria-live="polite">${esc(this.notice || (this.persistent?'연습 기록은 이 브라우저에만 저장돼요. 실제 내 노트와 분리되어 있어요.':'이번 연습 기록은 화면에서만 유지돼요.'))}</p>
      </div>`;
    }

    documentPane(scenario,record) {
      const selected = scenario.documents.find(item => item.id === record.documentId) || scenario.documents[0];
      const isField = selected.kind === 'fieldnotes' || selected.id.includes('field') || selected.kind === '현장 조사';
      return `<section class="sim-card sim-documents" aria-label="가상 경매 서류와 현장 사진"><div class="sim-document-tabs" role="group" aria-label="서류 선택">${scenario.documents.map((item,index) => `<button type="button" data-sim-document="${esc(item.id)}" aria-pressed="${item.id===selected.id}" title="${esc(item.title)}" aria-label="${esc(item.title)}"><span>${String(index+1).padStart(2,'0')}</span>${esc(documentName(item))}${record.reviewed.includes(item.id)?'<i aria-label="확인 기록함">✓</i>':''}</button>`).join('')}</div><div class="sim-scroll sim-paper" data-sim-scroll="document"><div class="sim-paper-tag">가상 학습 자료 · 실제 사건 아님</div><header class="sim-document-heading"><span>모의 사건 ${esc(scenario.id)}</span><h2>${esc(selected.title)}</h2><p>${esc(selected.sourceExplanation)}</p></header>${isField?this.photos(scenario):''}${this.documentSections(selected)}<p class="sim-document-disclaimer">학습을 위해 구성한 예시입니다. 실제 공적 서류·감정 결과·법원 판단이 아니며, 기재가 없으면 확인되지 않은 정보예요.</p></div><footer class="sim-document-footer"><span>${record.reviewed.length} / ${scenario.documents.length}종 확인 기록</span><button type="button" class="button small ${record.reviewed.includes(selected.id)?'':'primary'}" data-sim-action="review-document">${record.reviewed.includes(selected.id)?'확인 기록 취소':'이 서류 확인했어요'}</button></footer></section>`;
    }
    documentSections(document) {
      return document.sections.map(section => `<section class="sim-document-section"><h3>${esc(section.title)}</h3><dl>${section.rows.map(row => `<div${row.focus&&this.state.stage===1&&this.hint?' class="sim-row-focus"':''}><dt>${esc(row.label)}</dt><dd>${esc(row.value)}</dd></div>`).join('')}</dl></section>`).join('');
    }
    photos(scenario) {
      return `<section class="sim-photos" aria-label="가상 현장 사진">${scenario.observations.map(item => `<figure><div class="sim-photo" role="img" aria-label="${esc(item.title)} — AI로 만든 가상 이미지" style="background-position:${photoPosition[item.photoKey]||photoPosition.exterior}"></div><figcaption><strong>${esc(item.title)}</strong><p>${esc(item.text)}</p><span>AI로 만든 가상 현장 이미지 · 실매물 사진 아님</span></figcaption></figure>`).join('')}</section>`;
    }
    overview(scenario,record) {
      return `<div class="sim-section-heading"><span class="sim-kicker">01 · 먼저 자료부터</span><h2>${esc(scenario.title)}</h2><p>${esc(scenario.summary)}</p></div><p class="sim-address">${esc(scenario.address)} · 전용 ${esc(scenario.area)}㎡</p><div class="sim-numbers">${field('감정가',scenario.appraised)}${field('최저 매각가격',scenario.minimum)}</div><div class="sim-note"><strong>서류 8종과 현장을 함께 읽어보세요.</strong><p>서류를 열어 날짜·권리·점유를 대조한 뒤 확인 기록을 남겨요. 빠진 정보도 근거의 일부예요.</p></div><div class="sim-source-list" aria-label="준비된 서류">${scenario.documents.map((item,index) => `<button type="button" data-sim-document="${esc(item.id)}" title="${esc(item.title)}"><span>${String(index+1).padStart(2,'0')}</span><strong>${esc(documentName(item))}</strong><em>${record.reviewed.includes(item.id)?'확인함':'열어보기'}</em></button>`).join('')}</div><button type="button" class="sim-photo-link" data-sim-action="photos"><span class="sim-photo-preview" aria-hidden="true"></span><span><strong>현장 사진과 조사 메모</strong><small>외관 · 출입구 · 내부 · 하자 · 주변 환경</small><small>AI로 만든 가상 현장 이미지 · 실매물 사진 아님</small></span><b aria-hidden="true">↗</b></button><p class="sim-small">정답과 해설은 권리 확인 단계에서 직접 답을 고른 뒤 볼 수 있어요.</p>`;
    }
    questions(scenario,record) {
      const question = scenario.quiz[record.quizIndex];
      if (!question) return '<p>권리 확인 문제가 준비되지 않았어요. 서류를 먼저 확인해 주세요.</p>';
      const answer = record.answers[question.id], checked = answer?.checked === true;
      const correct = checked && answer.choiceId === question.answerId;
      const source = scenario.documents.find(item => item.id === question.documentId);
      const completed = scenario.quiz.filter(item => record.answers[item.id]?.checked).length;
      return `<div class="sim-section-heading"><span class="sim-kicker">02 · 서류로 근거 찾기</span><h2>권리 관계를 읽어볼까요?</h2><p>자료에서 확인한 내용만으로 답해 보세요. 미확인은 위험이 없다는 뜻이 아니에요.</p></div><div class="sim-question-progress"><span>질문 ${record.quizIndex+1} / ${scenario.quiz.length}</span><span>해설 확인 ${completed}개</span></div><div class="sim-question-dots" role="group" aria-label="권리 확인 문제 선택">${scenario.quiz.map((item,index) => `<button type="button" data-sim-question="${index}" aria-pressed="${index===record.quizIndex}" aria-label="${index+1}번 문제${record.answers[item.id]?.checked?', 해설 확인함':''}">${index+1}${record.answers[item.id]?.checked?' ✓':''}</button>`).join('')}</div><fieldset class="sim-question"><legend>${esc(question.question)}</legend>${question.choices.map(choice => `<label><input type="radio" name="simulation-choice" data-sim-choice="${esc(question.id)}" value="${esc(choice.id)}" ${answer?.choiceId===choice.id?'checked':''}><span>${esc(choice.text)}</span></label>`).join('')}</fieldset><div class="sim-question-actions"><button type="button" class="text-link" data-sim-action="hint">${this.hint?'힌트 접기':'근거 찾기 힌트'}</button><button type="button" class="button primary small" data-sim-action="check-answer" ${answer?.choiceId?'':'disabled'}>${checked?'해설 다시 확인':'답과 해설 확인'}</button></div>${this.hint&&!checked?`<div class="sim-hint"><strong>${esc(source?.title||'관련 서류')}에서 확인해 보세요.</strong><p>해당 기재의 날짜, 금액, 예외 사항과 조사되지 않은 내용을 함께 읽어보세요.</p><button type="button" class="text-link" data-sim-document="${esc(question.documentId)}">근거 서류 열기 →</button></div>`:''}${checked?`<div class="sim-feedback ${correct?'correct':'review'}" role="status"><strong>${correct?'근거를 잘 찾았어요.':'이 기재를 다시 읽어보세요.'}</strong><p>${esc(question.explanation)}</p><button type="button" class="text-link" data-sim-document="${esc(question.documentId)}">${esc(source?.title||'근거 서류')} 대조하기 →</button></div>`:'<p class="sim-answer-placeholder">답을 확인하기 전에는 해설이 표시되지 않아요.</p>'}<div class="sim-quiz-nav"><button type="button" class="button small" data-sim-question="${Math.max(0,record.quizIndex-1)}" ${record.quizIndex===0?'disabled':''}>이전 질문</button>${record.quizIndex<scenario.quiz.length-1?`<button type="button" class="button small" data-sim-question="${record.quizIndex+1}">다음 질문 →</button>`:'<button type="button" class="button small" data-sim-go-stage="2">입찰가 계산으로 →</button>'}</div>`;
    }
    bidding(scenario,record) {
      return `<div class="sim-section-heading"><span class="sim-kicker">03 · 비용까지 넣어보기</span><h2>얼마에, 왜 입찰할까요?</h2><p>모든 금액은 만원 단위예요. 실제 입찰이나 대출 신청은 진행되지 않아요.</p></div>${this.unresolved()?'<div class="sim-warning"><strong>미확인 비용이 있어요.</strong><p>아래 금액은 확인된 가정만 넣은 계산이에요. 인수·수리 등 빠진 금액을 확정하기 전에는 입찰을 보류해야 해요.</p></div>':''}<div class="sim-bid-inputs">${Object.entries(labels).map(([key,label]) => `<label for="simulation-${key}">${label}<span><input id="simulation-${key}" data-sim-number="${key}" type="number" min="0" step="0.1" inputmode="decimal" value="${esc(record.inputs[key])}"><em>만원</em></span></label>`).join('')}</div><div id="simulationCalculation" aria-live="polite" aria-atomic="true">${this.calculationHTML(this.calculation())}</div><details class="sim-cost-assumptions"><summary>계산에 적용한 비용 가정</summary><dl>${[['보증금 기준','최저 매각가 × '+scenario.defaults.depositRate+'%'],['취득 관련 세율',scenario.defaults.acquisitionRate+'% (연습 가정)'],['등기·법무',amount(scenario.defaults.legal)+'만원'],['수리',amount(scenario.defaults.repairs)+'만원'],['명도',amount(scenario.defaults.eviction)+'만원'],['체납 관리비',amount(scenario.defaults.arrears)+'만원'],['인수 금액',this.unresolved()&&scenario.answer.assumedCost===null?'미확인 · 계산에는 0 입력':amount(scenario.defaults.assumed)+'만원'],['대출 이자',scenario.defaults.loanRate+'% · '+scenario.defaults.months+'개월'],['현금 예비비',amount(scenario.defaults.reserve)+'만원 (이익에서 차감 안 함)'],['예상 매도가',amount(scenario.defaults.sale)+'만원'],['보수적 매도가',amount(scenario.defaults.downside)+'만원'],['매도 비용',scenario.defaults.sellingRate+'% + 세금 '+amount(scenario.defaults.saleTax)+'만원']].map(([label,value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl><p>연습용 입력값이며 세율·대출 가능액·매도가를 보장하지 않아요. 내 노트의 실제 투자금 탭에서는 모든 가정을 직접 조절할 수 있어요.</p></details><fieldset class="sim-decision"><legend>현재 자료로 내릴 내 판단</legend><label><input type="radio" name="simulation-decision" data-sim-decision value="bid" ${record.decision==='bid'?'checked':''}><span>추가 확인을 전제로 입찰 검토</span></label><label><input type="radio" name="simulation-decision" data-sim-decision value="hold" ${record.decision==='hold'?'checked':''}><span>입찰 보류 · 더 확인하기</span></label></fieldset><label class="sim-note-input" for="simulationNote">내 판단의 근거<textarea id="simulationNote" maxlength="10000" placeholder="근거 서류, 놓친 정보, 입찰 상한과 그 이유를 적어보세요.">${esc(record.note)}</textarea></label><button type="button" class="button primary sim-submit" data-sim-action="submit">내 판단과 해설 비교하기 →</button><p class="sim-small">경쟁 입찰자와 낙찰 결과를 만들어 내지 않아요. 자료를 읽고 자금과 위험을 점검하는 연습이에요.</p>`;
    }
    calculationHTML(result) {
      if (!result.valid) return `<div class="sim-calculation-error" role="alert"><strong>입력값을 확인해 주세요.</strong><ul>${result.errors.map(error => `<li>${esc(error)}</li>`).join('')}</ul></div>`;
      const depositGap = result.depositGap ?? Math.max(0,result.deposit-result.input.available);
      return `<div class="sim-cash-result"><span>예비비 포함 순투입 현금${this.unresolved()?' · 미확인 비용 제외':''}</span><strong>${money(result.cashNeeded)}</strong><p>낙찰가 + 취득·보유 비용 − 대출 + 예비비</p></div><div class="sim-calculation-rows"><div><span>입찰일 먼저 필요한 보증금</span><strong>${money(result.deposit)}</strong></div><div><span>취득·보유 비용 합계</span><strong>${money(result.costs)}</strong></div><div><span>가용 현금 대비 순투입 현금 부족액</span><strong class="${result.cashGap>0?'sim-negative':''}">${money(result.cashGap)}</strong></div><div><span>대출 전 선납 보증금 부족액</span><strong class="${depositGap>0?'sim-negative':''}">${money(depositGap)}</strong></div><div><span>예상 매도가 기준 손익</span><strong class="${result.profit<0?'sim-negative':''}">${money(result.profit)}</strong></div><div><span>보수적 매도가 기준 손익</span><strong class="${result.downsideProfit<0?'sim-negative':''}">${money(result.downsideProfit)}</strong></div></div><p class="sim-small">보증금은 낙찰대금의 일부로 중복 차감하지 않아요. 순투입 현금과 대출 전 선납 보증금의 부족액은 따로 비교하며, 서로 더하지 않아요. 실제 지급일별 자금·대출 실행 시점은 별도 확인해야 해요. 예상 손익은 수익 보장이 아니에요.</p>`;
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
      const targetMissed = result.valid && result.profit < result.input.targetProfit;
      const downsideLoss = result.valid && result.downsideProfit < 0;
      const financialHold = cashInsufficient || depositGap > 0 || targetMissed || downsideLoss;
      const hold = unresolved || !result.valid || financialHold || missing.length > 0 || correct.length < scenario.quiz.length;
      const title = financialHold?'입찰가와 자금 계획을 다시 점검하세요.':hold?'확인할 것이 남았어요. 지금은 보류.':'근거를 갖췄어요. 조건을 더 확인해 보세요.';
      const score = `<div class="sim-learning-score"><div><span>서류 확인 기록</span><strong>${record.reviewed.length}<small> / ${scenario.documents.length}종</small></strong></div><div><span>문제 해설 확인</span><strong>${checked.length}<small> / ${scenario.quiz.length}개</small></strong></div><div><span>맞힌 문제</span><strong>${correct.length}<small> / ${checked.length}개</small></strong></div></div>`;
      if (!record.submitted) {
        return `<div class="sim-section-heading"><span class="sim-kicker">04 · 내 판단과 비교하기</span><h2>먼저 내 판단을 남겨보세요.</h2><p>모의 입찰에서 금액과 판단을 제출하면 이 사례의 전체 해설을 볼 수 있어요.</p></div><div class="sim-note"><strong>아직 판단을 제출하지 않았어요.</strong><p>정답을 먼저 보기보다 서류의 근거, 입찰할 금액, 더 확인할 내용을 적어보세요.</p><button type="button" class="button primary small" data-sim-go-stage="2">입찰가와 내 판단 작성하기 →</button></div>${score}<p class="sim-small">해설을 확인한 문제만 학습 기록에 포함해요. 서류 확인 수나 정답 수는 투자 성공 가능성을 뜻하지 않아요.</p>`;
      }
      const reasons = [];
      if (!result.valid) reasons.push('계산 입력 오류를 먼저 수정해 주세요. 유효하지 않은 금액으로 투자 판단을 할 수 없어요.');
      if (unresolved) reasons.push('이 사례는 미확인 권리·인수액·비용 때문에 계산상 이익이 나더라도 보류하는 연습이에요. 빠진 비용을 0으로 확정하지 마세요.');
      if (cashInsufficient) reasons.push('예상 순투입 현금이 가용 현금보다 '+amount(result.cashGap)+'만원 부족해요. 자금 계획을 다시 세워야 해요.');
      if (depositGap > 0) reasons.push('대출 전 선납 보증금이 가용 현금보다 '+amount(depositGap)+'만원 부족해요. 나중의 대출과 별도로 입찰일 현금이 필요해요.');
      if (loss) reasons.push('예상 매도가 기준 손익이 '+amount(result.profit)+'만원으로 손실이에요. 입찰가·매도가·비용 가정을 다시 계산하세요.');
      else if (targetMissed) reasons.push('예상 매도가 기준 손익 '+amount(result.profit)+'만원이 목표 이익 '+amount(result.input.targetProfit)+'만원에 미달해요. 현재 입찰가를 다시 검토하세요.');
      if (downsideLoss) reasons.push('보수적 매도가 기준 손익이 '+amount(result.downsideProfit)+'만원으로 손실이에요. 가격 하락과 추가 비용을 감당할 수 있는지 재검토하세요.');
      if (missing.length) reasons.push('확인 기록을 남기지 않은 서류가 '+missing.length+'종 있어요. 자료가 있다고 확인을 마친 것은 아니에요.');
      if (checked.length > correct.length) reasons.push('틀린 권리 확인 답이 '+(checked.length-correct.length)+'개 남아 있어요. 해설과 원문 기재를 다시 대조하고 판단을 수정하세요.');
      if (checked.length < scenario.quiz.length) reasons.push('해설을 확인하지 않은 권리 문제가 '+(scenario.quiz.length-checked.length)+'개 남아 있어요. 아직 확인하지 않은 권리를 먼저 점검하세요.');
      return `<div class="sim-section-heading"><span class="sim-kicker">04 · 수익보다 근거를 먼저</span><h2>내 판단을 돌아보세요.</h2><p>낙찰 성공이나 투자 수익을 채점하지 않아요. 확인한 자료와 놓친 위험을 점검해요.</p></div>
        ${score}
        <div class="sim-result-status ${hold?'hold':'review'}"><span>${hold?'입찰 보류 / 추가 확인':'조건부 검토 연습'}</span><h3>${title}</h3><p>${hold?'아래 확인 항목과 계산 조건을 해결하기 전에는 현재 입력으로 입찰을 진행하지 않는 연습이에요.':esc(answer.plainConclusion)}</p>${reasons.length?`<ul class="sim-result-reasons">${reasons.map(reason => `<li>${esc(reason)}</li>`).join('')}</ul>`:''}</div>
        <section class="sim-recap"><h3>내가 제출한 판단</h3><div class="sim-recap-row"><span>${record.decision==='hold'?'입찰 보류':'추가 확인을 전제로 입찰 검토'}</span><strong>${money(result.valid?result.input.bid:NaN)}</strong></div><p class="sim-user-note">${esc(record.note||'판단 근거를 아직 적지 않았어요.')}</p></section>
        <section class="sim-findings"><h3>이 사례에서 놓치면 안 되는 근거</h3><ul>${answer.mainFindings.map(text => `<li>${esc(text)}</li>`).join('')}</ul></section>
        <section class="sim-findings"><h3>실제 입찰 전 남은 확인</h3><ul>${answer.nextChecks.map(text => `<li>${esc(text)}</li>`).join('')}${missing.length?`<li>아직 확인 기록을 남기지 않은 자료: ${missing.map(item => esc(item.title)).join(', ')}</li>`:''}${correct.length<scenario.quiz.length?'<li>풀지 않았거나 틀린 권리 확인 문제를 다시 확인하고 해설과 서류를 대조하세요.</li>':''}</ul></section>
        <div class="sim-import"><strong>연습 내용을 내 노트에 남길까요?</strong><p>버튼을 누를 때만 별도 연습 노트를 만들어요. 기존 내 물건은 덮어쓰지 않아요.</p><button type="button" class="button small" data-sim-action="copy">내 노트로 복사</button><button type="button" class="text-link" data-sim-go-stage="2">입찰가 바꿔 다시 계산 →</button></div>`;
    }
    footer() {
      return `<footer class="sim-navigation"><button type="button" class="button small" data-sim-go-stage="${Math.max(0,this.state.stage-1)}" ${this.state.stage===0?'disabled':''}>이전</button><span>${this.state.stage+1} / 4</span>${this.state.stage<3?`<button type="button" class="button small ${this.state.stage===0?'primary':''}" data-sim-go-stage="${this.state.stage+1}">${esc(STAGES[this.state.stage+1])} →</button>`:'<button type="button" class="button small" data-sim-go-stage="0">자료 다시 보기</button>'}</footer>`;
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
        this.notice = record.reviewed.includes(record.documentId)?'서류 확인 기록을 남겼어요. 기재 내용과 빠진 정보도 함께 점검해 주세요.':'이 서류의 확인 기록을 취소했어요.';
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
          this.notice = !result.valid?'입찰가·대출·가용 현금의 입력 오류를 먼저 수정해 주세요.':'현재 자료로 내릴 판단을 먼저 선택해 주세요.';
          this.paint(!result.valid?'[data-sim-number="bid"]':'[data-sim-decision]');
          return;
        }
        record.submitted = true; this.save(); this.goStage(3);
      } else if (data.simAction === 'download') this.download();
      else if (data.simAction === 'copy') {
        if (!this.calculation().valid) {
          this.notice = '입력 오류가 있는 금액은 복사할 수 없어요. 모의 입찰 단계에서 먼저 수정해 주세요.';
          this.paint('[data-sim-action="copy"]'); return;
        }
        if (typeof this.callbacks.copyToNotebook !== 'function') {
          this.notice = '내 노트 복사를 연결하지 못했어요. 연습 기록은 그대로 보존돼요.';
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
          this.notice = '내 노트에 복사하지 못했어요. 원래 노트와 연습 기록은 보존돼요.';
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
        this.notice = '가상 서류 8종을 HTML 파일로 저장했어요. 열어서 인쇄하거나 PDF로 저장할 수 있어요.';
      } catch (_) { this.notice = '서류를 내려받지 못했어요. 이 화면에서 자료를 계속 확인할 수 있어요.'; }
      this.paint('[data-sim-action="download"]');
    }
  }
  window.AuctionSimulation = Object.freeze({create:callbacks => new Simulation(callbacks)});
})();
