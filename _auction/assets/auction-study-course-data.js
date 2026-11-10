/* Beginner course. All cases and figures are fictional; portal links are lookup
 * starting points, not records of official legal review. No notebook or storage access.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./auction-study-model.js'));
  else root.AuctionCourseData = factory(root.AuctionModel);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (Model) {
  'use strict';

  if (!Model || typeof Model.compareAmounts !== 'function') throw new Error('AuctionCourseData requires AuctionModel.');

  const disclaimer = '학습용 가상 사례입니다. 실제 사건·서류가 아니며 법률 검수 완료 자료가 아닙니다.';
  const court = { name: '법원경매정보', href: 'https://www.courtauction.go.kr/', note: '실제 사건·최신 공고를 확인하는 입구입니다. 이 해설의 공식 검수 증빙은 아닙니다.' };
  const registry = { name: '인터넷등기소', href: 'https://www.iros.go.kr/', note: '최신 등기를 적법하게 열람하는 경로입니다. 실제 서류는 직접 확인해야 합니다.' };
  const document = (id, title, rows) => ({ id, title, rows: rows.map(row => ({ id: row[0], label: row[1], value: row[2], ...(row[3] ? { focus: true } : {}) })) });

  const lessons = [
    {
      id: 'auction-flow', title: '경매 흐름', goal: '허가·완납·등기·인도를 구분해요.',
      basics: {
        lead: '입찰 결과를 들었다고 바로 입주하는 것은 아니에요. 지금 어느 단계인지 먼저 확인해요.',
        terms: [
          { term: '입찰', text: '얼마에 사겠다는 금액과 필요한 서류를 내는 일이에요.' },
          { term: '매각허가', text: '법원이 매각을 허가할지 판단하는 절차예요. 대금 납부와는 달라요.' },
          { term: '완납', text: '매각대금을 모두 내는 일이에요. 이 연습에서는 완납 때 소유권(집주인으로서의 권리)을 취득해요.' },
          { term: '등기·인도', text: '등기는 권리 변동을 공적으로 기록하는 일, 인도는 실제 집을 넘겨받는 일이에요.' },
        ],
        takeaway: '서류·현장 확인 → 입찰 → 허가 → 완납으로 이어져요. 등기·인도는 각각 확인하고 실제 분기·기한은 공고를 봐요.',
      },
      example: {
        title: '가상봄아파트 · 허가는 났지만 대금은 남았어요', fictional: true,
        documents: [document('flow-example-record', '가상 사건 진행 메모', [
          ['flow-example-property', '물건', '연습시 가상봄아파트 101동 502호 · 소유권 전부 매각'],
          ['flow-example-permission', '허가', '매각허가결정 확정', true],
          ['flow-example-payment', '대금', '일부 미납 · 아직 완납하지 않음', true],
          ['flow-example-delivery', '인도', '점유자와 인도 일정 미협의'],
        ])],
        steps: [
          { title: '허가와 납부를 나눠 읽어요', text: '허가는 확정됐지만 대금은 아직 남아 있어요.', evidenceIds: ['flow-example-permission', 'flow-example-payment'] },
          { title: '권리 취득 시점을 확인해요', text: '허가 확정만으로 완납에 따른 권리 취득을 했다고 보지 않아요.', evidenceIds: ['flow-example-payment'] },
          { title: '등기와 인도도 따로 준비해요', text: '완납 후에도 이전등기와 실제 점유 인도는 별도로 확인해요.', evidenceIds: ['flow-example-delivery'] },
        ],
        answer: '아직 완납 전이에요. 허가가 났다는 이유로 바로 입주할 수 있다고 판단하지 않아요.',
        assumptions: ['일반적인 부동산 법원경매에서 소유권 전부를 매각하는 모의 상황이에요. 실제 진행·기한·매각 조건은 사건별로 확인해요.'],
        facts: { fullPayment: false, registrationComplete: false, deliveryComplete: false },
      },
      practice: {
        id: 'flow-practice', title: '연습가을빌라 · 대금은 모두 냈어요', fictional: true,
        documents: [document('flow-practice-record', '가상 사건 진행 메모', [
          ['flow-practice-property', '물건', '연습시 가을빌라 302호 · 소유권 전부 매각'],
          ['flow-practice-payment', '대금', '매각대금 전액 납부'],
          ['flow-practice-registration', '등기', '소유권이전등기 진행 중'],
          ['flow-practice-delivery', '인도', '현재 점유자와 인도 일정 협의 중'],
        ])],
        question: '완납했지만 등기·인도가 남았어요. 맞는 설명은?', type: 'choice',
        choices: [
          { id: 'paid-separate', text: '완납에 따른 권리 취득과 등기·인도를 나눠 확인해요.' },
          { id: 'permission-complete', text: '허가가 났던 날 모든 절차가 끝났어요.' },
          { id: 'move-in-now', text: '완납했으니 협의 없이 바로 입주해요.' },
        ],
        answerId: 'paid-separate', answerText: '완납에 따른 권리 취득과 등기·인도를 나눠 확인해요.',
        explanation: '이 모의 상황은 대금을 모두 냈지만 등기와 인도는 진행 중이에요. 완납이 실제 점유 인도까지 자동으로 마쳐 주지는 않아요.',
        evidenceIds: ['flow-practice-payment', 'flow-practice-registration', 'flow-practice-delivery'],
        facts: { fullPayment: true, registrationComplete: false, deliveryComplete: false },
      },
      references: [court],
    },
    {
      id: 'read-documents', title: '서류 확인', goal: '주소·동호수·면적·매각 범위를 맞춰 봐요.',
      basics: {
        lead: '같은 건물에도 여러 집이 있어요. 가격을 보기 전에 서류가 같은 물건을 가리키는지 맞춰요.',
        terms: [
          { term: '물건 표시', text: '주소·동호수·면적처럼 어느 부동산인지 가리키는 정보예요.' },
          { term: '매각 범위', text: '집 전체인지, 일부 지분(소유비율)인지 등 무엇을 얼마만큼 파는지예요.' },
          { term: '매각물건명세서', text: '법원이 매각 대상·점유·임대차·인수 관련 내용을 정리한 서류예요.' },
          { term: '등기사항전부증명서', text: '소유권과 등기된 권리의 기록이에요. 흔히 등기부등본이라고 불러요.' },
        ],
        takeaway: '물건 표시가 맞아도 권리·점유 확인이 끝난 것은 아니에요.',
      },
      example: {
        title: '가상누리아파트 · 두 서류를 나란히 읽어요', fictional: true,
        documents: [
          document('documents-example-sale', '가상 매각물건명세서 발췌', [
            ['documents-example-sale-address', '물건 표시', '연습시 누리아파트 103동 601호', true],
            ['documents-example-sale-area', '전용면적', '59.8㎡', true],
            ['documents-example-sale-scope', '매각 범위', '전유부분과 표시된 대지권 전부', true],
          ]),
          document('documents-example-register', '가상 등기 표제부·지분 발췌', [
            ['documents-example-register-address', '물건 표시', '연습시 누리아파트 103동 601호', true],
            ['documents-example-register-area', '전용면적', '59.80㎡', true],
            ['documents-example-register-scope', '권리·지분 표시', '소유권 1/1 · 대지권 표시 있음', true],
          ]),
        ],
        steps: [
          { title: '주소와 동호수를 맞춰요', text: '두 서류 모두 누리아파트 103동 601호예요.', evidenceIds: ['documents-example-sale-address', 'documents-example-register-address'] },
          { title: '면적과 범위도 읽어요', text: '59.8㎡와 59.80㎡는 같은 면적이에요. 명세서의 전부 매각과 등기의 지분 표시도 함께 봐요.', evidenceIds: ['documents-example-sale-area', 'documents-example-register-area', 'documents-example-sale-scope', 'documents-example-register-scope'] },
          { title: '일치 확인과 안전 판단을 구분해요', text: '물건 표시는 맞지만, 최신 권리·임대차·현재 점유는 아직 별도 확인해야 해요.' },
        ],
        answer: '이 발췌의 물건 표시는 일치해요. 입찰 판단까지 끝난 것은 아니에요.',
        assumptions: ['전유부분은 개별 집, 대지권은 그 집과 연결된 토지 권리를 뜻해요.', '학습용 발췌예요. 실제 물건은 최신 원문 전체와 매각 조건을 대조해요.'],
        facts: { sameAddress: true, sameUnit: true, sameArea: true, scopeCompared: true },
      },
      practice: {
        id: 'documents-practice', title: '연습해솔아파트 · 호수를 확인해요', fictional: true,
        documents: [
          document('documents-practice-sale', '가상 매각물건명세서 발췌', [
            ['documents-practice-sale-address', '물건 표시', '연습시 해솔아파트 202동 802호'],
            ['documents-practice-sale-area', '전용면적', '84㎡'],
            ['documents-practice-sale-scope', '매각 범위', '전유부분과 표시된 대지권 전부'],
          ]),
          document('documents-practice-register', '가상 등기 표제부 발췌', [
            ['documents-practice-register-address', '물건 표시', '연습시 해솔아파트 202동 803호'],
            ['documents-practice-register-area', '전용면적', '84.00㎡'],
          ]),
        ],
        question: '두 서류를 읽은 뒤 먼저 할 일은?', type: 'choice',
        choices: [
          { id: 'area-is-enough', text: '면적이 같으니 같은 집으로 보고 입찰해요.' },
          { id: 'reconcile-unit', text: '호수가 다른 이유와 원문을 확인할 때까지 판단을 멈춰요.' },
          { id: 'pick-one-unit', text: '마음에 드는 호수 하나를 골라 나머지 서류를 고쳐요.' },
        ],
        answerId: 'reconcile-unit', answerText: '호수가 다른 이유와 원문을 확인할 때까지 판단을 멈춰요.',
        explanation: '명세서는 802호, 등기는 803호예요. 면적만 같다고 같은 물건으로 볼 수 없으므로 자료를 임의로 맞추지 말고 원문부터 대조해요.',
        evidenceIds: ['documents-practice-sale-address', 'documents-practice-register-address'],
        facts: { sameAddress: true, sameUnit: false, sameArea: true, scopeCompared: false },
      },
      references: [court, registry],
    },
    {
      id: 'bid-deposit', title: '입찰보증금', goal: '공고의 최저가와 보증 비율로 계산해요.',
      basics: {
        lead: '입찰일에는 대출보다 먼저 준비해야 할 돈이 있어요. 공고가 정한 입찰보증금을 확인해요.',
        terms: [
          { term: '최저매각가격', text: '해당 매각기일에 입찰할 수 있는 최소 금액이에요.' },
          { term: '보증금 비율', text: '보증금 계산에 쓸 비율이에요. 모든 사건이 같지 않으므로 공고를 읽어요.' },
          { term: '입찰보증금', text: '입찰할 때 미리 준비하는 돈이에요. 매수인이 낸 보증금은 낙찰대금의 일부로 충당돼요.' },
          { term: '예상 낙찰가', text: '이 연습에서 내가 입찰하려는 금액이에요. 보증금의 기준 금액과 구분해요.' },
        ],
        takeaway: '이 연습의 공고 조건은 최저매각가격 × 보증금 비율이에요. 실제 공고의 조건을 먼저 확인해요.',
      },
      example: {
        title: '가상샘아파트 · 보증 비율 10%인 공고', fictional: true,
        documents: [document('deposit-example-notice', '가상 매각 공고·입찰 계획', [
          ['deposit-example-property', '물건', '연습시 샘아파트 101동 304호'],
          ['deposit-example-minimum', '최저매각가격', '10,000만원(1억원)', true],
          ['deposit-example-rate', '공고의 보증 조건', '최저매각가격의 10% · 이 모의 공고의 조건', true],
          ['deposit-example-bid', '내 예상 낙찰가', '12,000만원(1억 2,000만원)'],
        ])],
        steps: [
          { title: '기준 금액을 찾아요', text: '내 입찰 예정가가 아니라 공고에 적힌 최저가 10,000만원이 기준이에요.', evidenceIds: ['deposit-example-minimum', 'deposit-example-rate'] },
          { title: '비율을 곱해요', text: '10,000만원 × 10% = 1,000만원이에요.', evidenceIds: ['deposit-example-rate'] },
          { title: '낙찰대금에 다시 더하지 않아요', text: '12,000만원에 낙찰되면 보증금 1,000만원은 그 대금의 일부예요. 대금만 보면 11,000만원이 남아요.', evidenceIds: ['deposit-example-bid'] },
        ],
        answer: '입찰보증금은 1,000만원이에요. 낙찰대금과 별도 비용처럼 중복 합산하지 않아요.',
        assumptions: ['10%는 이 모의 공고에만 정한 값이에요. 재매각 등 보증 조건이 달라질 수 있으므로 실제 공고를 확인해요.'],
        inputs: { minimum: 10000, depositRate: 10, bid: 12000 },
      },
      practice: {
        id: 'deposit-practice', title: '연습별빛빌라 · 다른 보증 조건', fictional: true,
        documents: [document('deposit-practice-notice', '가상 매각 공고·입찰 계획', [
          ['deposit-practice-property', '물건', '연습시 별빛빌라 301호'],
          ['deposit-practice-minimum', '최저매각가격', '8,000만원'],
          ['deposit-practice-rate', '공고의 보증 조건', '최저매각가격의 20% · 이 모의 공고의 조건'],
          ['deposit-practice-bid', '내 예상 낙찰가', '9,500만원'],
        ])],
        question: '이 공고 조건에서 입찰보증금은 몇 만원인가요?', type: 'amount', unit: '만원',
        answerValue: 1600, answerText: '1,600만원',
        explanation: '8,000만원 × 20% = 1,600만원이에요. 예상 낙찰가 9,500만원을 기준으로 계산하지 않아요. 20%는 이 모의 공고의 조건이에요.',
        evidenceIds: ['deposit-practice-minimum', 'deposit-practice-rate'],
        inputs: { minimum: 8000, depositRate: 20, bid: 9500 },
      },
      references: [court],
    },
    {
      id: 'cash-needed', title: '필요 현금', goal: '낙찰대금·비용·대출·예비비를 나눠 계산해요.',
      basics: {
        lead: '낙찰가가 내가 준비할 현금과 같지는 않아요. 비용을 더하고 대출을 뺀 뒤 예비비를 남겨요.',
        terms: [
          { term: '낙찰대금', text: '낙찰받은 가격 전체예요. 앞서 낸 입찰보증금도 여기에 들어 있어요.' },
          { term: '부대비용', text: '취득·등기·이자·수리·인도와 별도 인수액 등 낙찰대금 밖의 지출이에요. 인수액은 기존 권리 때문에 추가로 부담할 수 있는 금액이에요.' },
          { term: '예상 대출', text: '계산에 넣은 대출 가정이에요. 실제 승인 금액과 실행 시점은 따로 확인해요.' },
          { term: '예비비', text: '아직 쓰지 않은 현금 여유분이에요. 필요한 현금에는 더하지만 지출한 비용처럼 이익에서 빼지는 않아요.' },
        ],
        takeaway: '필요 현금 = 낙찰대금 + 취득·보유 부대비용 − 예상 대출 + 예비비예요.',
      },
      example: {
        title: '가상초록아파트 · 현금을 네 부분으로 나눠요', fictional: true,
        documents: [document('cash-example-budget', '가상 자금 계획 메모', [
          ['cash-example-property', '물건', '연습시 초록아파트 105동 405호'],
          ['cash-example-bid', '낙찰대금 가정', '10,000만원(1억원)', true],
          ['cash-example-costs', '취득·보유 부대비용 합계', '700만원 · 세금·등기·이자·수리·인도·확인된 인수액을 포함한 모의 합계', true],
          ['cash-example-loan', '예상 대출', '6,000만원 · 승인·실행은 별도 확인할 가정', true],
          ['cash-example-reserve', '현금 예비비', '300만원', true],
          ['cash-example-deposit', '앞서 낸 입찰보증금', '1,000만원 · 낙찰대금의 일부'],
        ])],
        steps: [
          { title: '대금과 비용을 더해요', text: '10,000 + 700 = 10,700만원이에요.', evidenceIds: ['cash-example-bid', 'cash-example-costs'] },
          { title: '예상 대출을 빼요', text: '10,700 − 6,000 = 4,700만원이에요.', evidenceIds: ['cash-example-loan'] },
          { title: '예비비를 남겨요', text: '4,700 + 300 = 5,000만원이에요.', evidenceIds: ['cash-example-reserve'] },
          { title: '보증금과 실행 시점을 확인해요', text: '보증금 1,000만원은 이미 낙찰대금에 포함돼요. 대출 전에 준비할 돈과 실제 지급일별 현금은 따로 확인해요.', evidenceIds: ['cash-example-deposit', 'cash-example-loan'] },
        ],
        answer: '이 모의 조건의 예비비 포함 필요 현금은 5,000만원이에요.',
        assumptions: ['700만원은 필요한 취득·보유 부대비용이 모두 반영됐다고 한정한 모의 합계예요.', '추가 인수액·비용·대출이 미확정이면 완전한 필요 현금을 계산했다고 볼 수 없어요. 이 합계는 실제 순간 최대 유동성을 보장하지 않아요.'],
        inputs: { bid: 10000, costs: 700, loan: 6000, reserve: 300, deposit: 1000 },
      },
      practice: {
        id: 'cash-practice', title: '연습새싹아파트 · 다른 자금 계획', fictional: true,
        documents: [document('cash-practice-budget', '가상 자금 계획 메모', [
          ['cash-practice-property', '물건', '연습시 새싹아파트 203동 702호'],
          ['cash-practice-bid', '낙찰대금 가정', '15,000만원(1억 5,000만원)'],
          ['cash-practice-costs', '취득·보유 부대비용 합계', '900만원 · 세금·등기·이자·수리·인도·확인된 인수액을 포함한 모의 합계'],
          ['cash-practice-loan', '예상 대출', '9,000만원 · 승인·실행은 별도 확인할 가정'],
          ['cash-practice-reserve', '현금 예비비', '400만원'],
          ['cash-practice-deposit', '앞서 낸 입찰보증금', '1,500만원 · 낙찰대금의 일부'],
        ])],
        question: '부대비용이 모두 반영된 모의 조건에서 예비비 포함 필요 현금은 몇 만원인가요?', type: 'amount', unit: '만원',
        answerValue: 7300, answerText: '7,300만원',
        explanation: '15,000 + 900 − 9,000 + 400 = 7,300만원이에요. 보증금 1,500만원은 대금에 포함되므로 다시 더하지 않아요. 실제 대출·추가 비용과 지급 시점은 별도 확인해요.',
        evidenceIds: ['cash-practice-bid', 'cash-practice-costs', 'cash-practice-loan', 'cash-practice-reserve', 'cash-practice-deposit'],
        inputs: { bid: 15000, costs: 900, loan: 9000, reserve: 400, deposit: 1500 },
      },
      references: [court],
    },
    {
      id: 'verify-or-hold', title: '확인·보류', goal: '미확인을 0원이나 안전 판정으로 바꾸지 않아요.',
      basics: {
        lead: '모르는 정보가 남아 있으면 계산 숫자가 좋아 보여도 판단을 멈출 수 있어요.',
        terms: [
          { term: '점유', text: '누가 실제로 집을 쓰거나 살고 있는지에 관한 상태예요.' },
          { term: '인수액', text: '기존 권리 때문에 낙찰대금 밖에서 추가로 부담할 수 있는 금액이에요.' },
          { term: '폐문부재', text: '조사 때 문이 닫혀 사람을 만나지 못했다는 기록이에요. 빈집이라는 뜻은 아니에요.' },
          { term: '보류', text: '중요한 자료를 확인할 때까지 입찰 결정을 멈추는 선택이에요.' },
        ],
        takeaway: '점유나 인수액을 모른다면, 확인된 0원으로 처리하지 않아요.',
      },
      example: {
        title: '가상달빛빌라 · 닫힌 문 뒤의 상황은 몰라요', fictional: true,
        documents: [document('hold-example-status', '가상 현황조사·계산 점검 메모', [
          ['hold-example-property', '물건', '연습시 달빛빌라 202호'],
          ['hold-example-visit', '방문 결과', '폐문부재 · 조사 때 사람을 만나지 못함', true],
          ['hold-example-tenant', '점유·임대차 자료', '점유자·계약·보증금 미확인', true],
          ['hold-example-assumed', '계산 화면의 인수액', '0만원 · 확인 근거 없이 남아 있는 입력값', true],
        ])],
        steps: [
          { title: '관찰한 사실만 적어요', text: '문이 닫혀 있었다는 사실만 알아요. 빈집인지, 누가 사는지는 몰라요.', evidenceIds: ['hold-example-visit', 'hold-example-tenant'] },
          { title: '입력 숫자와 확인 결과를 구분해요', text: '화면에 0만원이 있어도 인수액이 확인된 것은 아니에요.', evidenceIds: ['hold-example-assumed'] },
          { title: '확인할 자료를 먼저 구해요', text: '현재 점유·임대차·보증금과 인수 관계를 확인하기 전에는 입찰 판단을 보류해요.', evidenceIds: ['hold-example-tenant'] },
        ],
        answer: '현재는 보류해요. 실제 점유·임대차·인수액의 근거부터 확인해요.',
        assumptions: ['점유·임대차·인수액을 확인할 자료가 없는 모의 상황이에요. 확인하지 못한 금액을 0원으로 확정하지 않아요.'],
        facts: { occupantContacted: false, assumedCost: null, displayedAssumed: 0 },
      },
      practice: {
        id: 'hold-practice', title: '연습바람아파트 · 이익 숫자는 양수예요', fictional: true,
        documents: [document('hold-practice-status', '가상 면담·계산 점검 메모', [
          ['hold-practice-property', '물건', '연습시 바람아파트 108동 604호'],
          ['hold-practice-occupant', '현장 면담', '한 사람이 거주 중이라고 답함'],
          ['hold-practice-tenancy', '임대차·인수액 자료', '계약·보증금 반환·배당(매각대금 배분) 자료 미확보 · 인수액 미확정'],
          ['hold-practice-profit', '계산 화면', '가정에 따른 예상 이익 +900만원 · 미확정 인수액 미반영'],
        ])],
        question: '현재 자료로 내릴 판단은?', type: 'choice',
        choices: [
          { id: 'profit-is-enough', text: '이익이 +900만원이니 바로 입찰해요.' },
          { id: 'unknown-is-zero', text: '자료가 없으니 인수액을 0원으로 확정해요.' },
          { id: 'hold-for-evidence', text: '인수액의 근거를 확인하기 전에는 입찰을 보류해요.' },
        ],
        answerId: 'hold-for-evidence', answerText: '인수액의 근거를 확인하기 전에는 입찰을 보류해요.',
        explanation: '사람을 만났다는 사실만으로 임대차·인수액이 확인되지는 않아요. 빠진 인수액을 반영하면 손익도 달라질 수 있으므로 근거를 확인한 뒤 다시 계산해요.',
        evidenceIds: ['hold-practice-occupant', 'hold-practice-tenancy', 'hold-practice-profit'],
        facts: { occupantContacted: true, assumedCost: null, modeledProfit: 900, decision: 'hold' },
      },
      references: [court, registry],
    },
  ];

  function freezeTree(value) {
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
      Object.values(value).forEach(freezeTree);
      Object.freeze(value);
    }
    return value;
  }
  freezeTree(lessons);
  const byId = new Map(lessons.map(lesson => [lesson.id, lesson]));

  function grade(lessonId, answer) {
    if (typeof lessonId !== 'string' || !byId.has(lessonId)) return { valid: false, correct: false };
    const practice = byId.get(lessonId).practice;
    if (practice.type === 'choice') {
      const valid = typeof answer === 'string' && practice.choices.some(choice => choice.id === answer);
      return { valid, correct: valid && answer === practice.answerId };
    }
    let value = NaN;
    if (typeof answer === 'number') value = answer;
    else if (typeof answer === 'string') {
      const text = answer.trim();
      // Accept ordinary decimal amounts and correctly grouped commas, never
      // implicit zero, booleans, coercible objects, hexadecimal or unit suffixes.
      if (/^(?:(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d*)?|\.\d+)$/.test(text)) value = Number(text.replaceAll(',', ''));
    }
    const valid = Number.isFinite(value) && value >= 0;
    return { valid, correct: valid && Model.compareAmounts(value, practice.answerValue) === 0 };
  }

  return freezeTree({ version: 1, fictional: true, disclaimer, lessons, grade });
});
