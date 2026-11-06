/* Fictional mock auctions, never actual court records or a user's property data.
 * All prices are in 만원. Tax, financing and distribution figures are study assumptions.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.AuctionSimulationData = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const disclaimer = '전체가 가상 학습 자료입니다. 실제 사건·등기·시세·현장 사진이 아니며, 공식 서류 원본이나 PDF를 재현하지 않았습니다.';
  const amount = value => value.toLocaleString('ko-KR', { maximumFractionDigits: 2 }) + '만원';
  const rows = pairs => pairs.map(pair => ({ label: pair[0], value: pair[1], ...(pair[2] ? { focus: true } : {}) }));
  const section = (title, pairs) => ({ title, rows: rows(pairs) });
  const document = (id, kind, title, role, sections) => ({
    id, kind, title: title + ' · 가상 발췌',
    sourceExplanation: disclaimer + ' 학습 역할: ' + role,
    sections,
  });

  function documentsFor(item, detail) {
    const prefix = item.id + '-';
    return [
      document(prefix + 'sale', 'sale', '매각물건명세서', '매각 대상·임차인 기재·특별매각조건 대조', [
        section('매각 대상과 기일', [
          ['물건 표시', item.address, true], ['매각 면적', '전용 ' + item.area + '㎡', true],
          ['가상 자료 기준일', item.facts.asOf], ['모의 입찰일', item.facts.bidDate],
          ['감정평가액', amount(item.appraised)], ['최저 매각가격', amount(item.minimum)],
          ['입찰보증금', '최저 매각가격의 ' + item.defaults.depositRate + '% · 낙찰대금의 일부'],
        ]),
        section('임대차와 매각 조건', detail.sale),
      ]),
      document(prefix + 'register', 'register', '등기사항전부증명서', '표제부·갑구·을구와 권리 접수일 비교', [
        section('표제부 · 물건 표시', [
          ['주소·동호수', item.address, true], ['전유부분', '전용 ' + item.area + '㎡'],
          ['대지권 표시', detail.landRights, true], ['가상 열람 기준', item.facts.asOf],
        ]),
        section('갑구·을구 · 학습용 권리 순서', detail.register),
      ]),
      document(prefix + 'occupancy', 'occupancy', '현황조사서', '조사 당시 점유와 현재 확인할 사실 구분', [
        section('방문 조사와 임대차', detail.occupancy),
      ]),
      document(prefix + 'appraisal', 'appraisal', '감정평가서', '평가 기준일·평가 조건·매각 대상 확인', [
        section('평가 개요', [
          ['평가 기준일', item.facts.appraisalDate], ['대상 면적', '전용 ' + item.area + '㎡'],
          ['감정평가액', amount(item.appraised)], ['자료 성격', '가상의 과거 평가액 · 현재 매도가 보장 아님'],
        ]),
        section('평가 조건과 관찰', detail.appraisal),
      ]),
      document(prefix + 'building', 'building', '건축물대장', '공부상 용도·면적과 현장 불일치 대조', [
        section('공부상 건물과 주의 사항', detail.building),
      ]),
      document(prefix + 'fees', 'fees', '관리비 확인 메모', '세대별 체납 내역과 계산에 넣는 금액 구분', [
        section('가상 관리주체 안내 · ' + item.facts.asOf, [
          ['공용부분 체납', amount(item.facts.fees.common), true],
          ['전유부분 체납', amount(item.facts.fees.private)],
          ['연체료', amount(item.facts.fees.late)],
          ['체납 합계', amount(item.facts.fees.common + item.facts.fees.private + item.facts.fees.late)],
          ['계산에 반영한 관리비', amount(item.defaults.arrears), true],
          ['인수 근거와 정산', detail.feeAssumption, true],
        ]),
        section('별도 비용과 자금 가정', [
          ['예상 낙찰가', amount(item.defaults.bid)], ['예상 대출', amount(item.defaults.loan) + ' · 실제 승인액 아님'],
          ['수리·명도 예산', amount(item.defaults.repairs) + ' / ' + amount(item.defaults.eviction)],
          ['별도 인수 금액', detail.assumedDescription, true],
          ['매도 세금 예상액', amount(item.defaults.saleTax) + ' · 학습용 추정치, 실제 세금 확인 필요'],
          ['예비비', amount(item.defaults.reserve) + ' · 현금 여유분이며 손익 비용에 중복 가산하지 않음'],
        ]),
      ]),
      document(prefix + 'comparables', 'comparables', '비교거래·지역 메모', '같은 조건의 거래인지 확인하고 매도 가정 검토', [
        section('가상 비교거래 · 실거래 조회 결과 아님', item.comparables.map((trade, index) => [
          '비교 ' + (index + 1), trade.date + ' · ' + trade.area + '㎡ · ' + amount(trade.price) + ' · ' + trade.description,
        ])),
        section('계산의 매도 가정', [
          ['기준 매도가', amount(item.defaults.sale)], ['보수적 매도가', amount(item.defaults.downside)],
          ['비교의 한계', detail.comparisonLimit, true],
        ]),
      ]),
      document(prefix + 'fieldnotes', 'fieldnotes', '현장 확인 메모', '사진으로 본 상태와 확인하지 못한 권리·하자 구분', [
        section('가상 답사 기록 · ' + item.facts.visitDate, item.observations.map(observation => [observation.title, observation.text])),
        section('사진 읽기', [
          ['사진 성격', '연출된 연습용 이미지 · 실제 주소나 세대의 사진이 아님', true],
          ['사진으로 확정할 수 없는 것', '대항력·실제 점유자·누수 원인·구조 안전·대지권·법적 인수액은 별도 자료와 조사 필요', true],
        ]),
      ]),
    ];
  }

  function question(item, id, documentKind, prompt, choices, answerId, explanation) {
    return {
      id: item.id + '-' + id, question: prompt,
      choices: choices.map(choice => ({ id: choice[0], text: choice[1] })),
      answerId, explanation, documentId: item.id + '-' + documentKind,
    };
  }

  const basic = {
    id: 'simulation-basic', title: '아파트 · 뒤에 들어온 임차인', level: '입문', fictional: true,
    address: '연습시 가상구 모의로 10, 연습누리 101동 803호', area: 59.8,
    summary: '물건 표시·권리·점유를 대조하고, 비용과 필요한 현금을 계산해요.',
    appraised: 32000, minimum: 25600, financialAssumptionsConfirmed: true,
    photoSet: {
      src: './assets/auction-practice/field-contact-sheet.png', columns: 3, rows: 2,
      fictional: true, aiGenerated: true, buildingType: 'apartment',
      positions: { exterior: '0% 0%', entrance: '50% 0%', interior: '100% 0%', neighborhood: '50% 100%' },
    },
    defaults: {
      bid: 27000, minimum: 25600, depositRate: 10, loan: 16200, loanRate: 4.5,
      months: 6, acquisitionRate: 1.1, legal: 120, repairs: 600, eviction: 250,
      arrears: 90, assumed: 0, reserve: 500, sale: 33000, downside: 30500,
      sellingRate: 0.5, saleTax: 400, targetProfit: 2000, available: 14000,
    },
    facts: {
      asOf: '2026-09-15', bidDate: '2026-10-20', appraisalDate: '2026-06-10', visitDate: '2026-09-12',
      mortgageDate: '2020-04-15', auctionStartDate: '2026-05-20',
      distributionDeadline: '2026-07-31',
      tenant: { moveInDate: '2023-03-02', fixedDate: '2023-03-03', distributionRequestDate: '2026-07-01', deposit: 6000 },
      fees: { common: 90, private: 50, late: 12 },
    },
    observations: [
      { id: 'basic-exterior', title: '단지 외관', photoKey: 'exterior', text: '아파트 외관이에요. 구조 안전은 사진으로 판단하지 않아요.' },
      { id: 'basic-entrance', title: '공동현관', photoKey: 'entrance', text: '공동현관 사진이에요. 현재 점유자는 조사 기록과 별도로 확인해요.' },
      { id: 'basic-interior', title: '실내 연출', photoKey: 'interior', text: '도배·바닥 수리를 가정한 실내예요. 수리비 600만원은 견적 전 예산이에요.' },
      { id: 'basic-neighborhood', title: '주변 보행 환경', photoKey: 'neighborhood', text: '보행 환경을 살펴봐요. 출퇴근 시간·소음·통학·상권은 시간대를 바꿔 조사해요.' },
    ],
    comparables: [
      { price: 32700, area: 59.8, date: '2026-08-03', description: '같은 단지 중층 · 보통 수리 · 가상 거래' },
      { price: 33500, area: 59.8, date: '2026-07-17', description: '같은 단지 고층 · 내부 수리 완료 · 가상 거래' },
      { price: 30800, area: 59.8, date: '2026-06-24', description: '같은 단지 저층 · 수리 필요 · 가상 거래' },
    ],
    answer: {
      riskLevel: 'review', assumedCost: 0,
      estimatedCostsDescription: '인수액 0만원·관리비 90만원은 명세서의 모의 조건이에요. 실제 권리·정산·세금·대출은 원문과 당사자 확인이 필요해요.',
      mainFindings: [
        '근저당 2020-04-15보다 전입 2023-03-02가 늦어요. 이 비교만으로 모든 권리 소멸이나 전액 배당을 확정하지 않아요.',
        '모의 조건은 별도 인수액을 0만원으로 놓지만, 인도 협의와 수리·관리비는 별도 비용이에요.',
        '입찰보증금은 2,560만원이며 낙찰대금에 포함돼요. 대출 실행 전에 이 현금을 준비해야 해요.',
        '체납 합계 152만원과 계산에 반영한 공용부분 90만원을 구분해요. 예비비는 손익 비용이 아니에요.',
      ],
      nextChecks: ['최신 등기·명세서·특별매각조건 재열람', '현재 점유자·인도 일정·수리 견적 확인', '공용 체납의 인수 근거와 실제 대출·세금 확인'],
      plainConclusion: '숫자상 검토를 이어갈 수 있어요. 양의 손익은 입찰 허가나 안전 보장이 아니므로 남은 권리·현장·자금을 확인해요.',
    },
  };

  basic.documents = documentsFor(basic, {
    landRights: '대지권 전부 표시 · 전유부분과 함께 매각하는 모의 조건',
    sale: [
      ['매각 범위', '전유부분 및 표시된 대지권 전부', true],
      ['임차인 A', '보증금 6,000만원 · 전입 2023-03-02 · 확정일자 2023-03-03'],
      ['배당요구', '2026-07-01 제출 · 종기 2026-07-31'],
      ['별도 인수 조건', '학습을 위해 기준근저당 유효·선순위 별도 인수권리 없음·임차인의 선순위 대항력 없음으로 가정', true],
      ['연습의 인수 가정', '보증금 별도 인수액 0만원 · 날짜만으로 산정한 결과가 아니며 실제 배당액은 계산하지 않음', true],
      ['실전에서 추가 확인', '권리 전체·점유와 전입의 실제 유지·최신 변동·특별매각조건'],
    ],
    register: [
      ['갑구 소유권', '가상 소유자 A · 2018-09-10 취득'],
      ['을구 근저당권', '2020-04-15 접수 · 채권최고액 21,600만원 · 기준권리 후보', true],
      ['갑구 가압류', '2024-02-06 접수 · 청구 1,200만원'],
      ['갑구 경매개시 기입', '2026-05-20'],
      ['확인 범위', '가상 주요 항목 발췌 · 실전에서는 말소 이력·권리 전체와 최신 변동 확인'],
    ],
    occupancy: [
      ['조사일', '2026-06-18'], ['방문 결과', '가상 임차인 A가 거주 중이라고 응답'],
      ['전입·점유 기재', '전입 2023-03-02 · 같은 날 점유 개시했다고 진술', true],
      ['임대차 기재', '보증금 6,000만원 · 확정일자 2023-03-03'],
      ['배당요구 자료', '2026-07-01 제출로 가정 · 제출과 전액 배당은 별개'],
      ['현재 확인할 것', '조사 후 점유 변동·인도 가능일·열쇠 인계·협의 비용', true],
    ],
    appraisal: [
      ['평가 대상', '전유부분과 표시된 대지권 · 전용 59.8㎡'],
      ['평가 당시 상태', '보통 관리 상태 · 내부는 일부 관찰했다는 가상 설정'],
      ['계산에 넣은 수리비', '600만원 · 현장 정밀점검과 실제 견적 전의 예산'],
      ['유의 사항', '감정가 32,000만원은 현재 거래가나 매도 보장이 아님', true],
    ],
    building: [
      ['대지 위치', basic.address], ['주용도', '공동주택 · 아파트'],
      ['사용승인', '2008-11-20'], ['전유 면적', '59.8㎡', true],
      ['위반건축 기재', '이 가상 발췌에는 표시 없음 · 실제 현장 일치까지 보증하지 않음', true],
      ['대조 항목', '등기·명세서의 주소·호수·면적·매각 범위와 대조'],
    ],
    feeAssumption: '모의 조건에서는 공용부분 90만원만 부담한다고 가정해요. 실제 공용·전유·연체료의 인수 범위는 항목별 근거와 정산일 확인이 필요해요.',
    assumedDescription: '0만원 · 명세서의 명시된 모의 조건에 한함',
    comparisonLimit: '층·향·수리·계약 조건을 맞춰야 해요. 33,000만원은 가상 비교거래에 근거해 선택한 연습 시나리오이지 확정 시세가 아니에요.',
  });
  basic.quiz = [
    question(basic, 'identity', 'sale', '서류 세트가 같은 물건을 가리키는지 가장 먼저 무엇을 맞출까요?', [
      ['match', '주소·동호수·면적·매각 범위를 등기와 대조한다'], ['price', '감정가와 최저가만 비교한다'], ['photo', '사진 분위기가 비슷하면 넘어간다'],
    ], 'match', '명세서·등기·건축물대장의 물건 표시를 함께 대조해요. 같은 건물이라도 다른 호수나 일부 지분일 수 있어요.'),
    question(basic, 'priority', 'register', '근저당이 전입보다 빠르다는 사실로 어디까지 판단할 수 있나요?', [
      ['automatic', '임차보증금은 반드시 전액 배당된다'], ['start', '기준권리 후보를 찾고 명세서·권리 종류·점유·대항요건을 더 대조한다'], ['skip', '다른 권리와 매각 조건을 볼 필요가 없다'],
    ], 'start', '이 사례의 인수 0만원은 명세서에 적은 추가 모의 조건까지 전제한 값이에요. 날짜 한 줄이나 배당요구만으로 소멸·배당·인수액을 확정하지 않아요.'),
    question(basic, 'occupancy', 'occupancy', '조사 때 임차인을 만났다면 즉시 인도 가능한가요?', [
      ['immediate', '낙찰 즉시 열쇠를 받을 수 있다'], ['current', '조사 후 변동과 실제 인도 일정·절차를 확인한다'], ['free', '명도 비용은 0만원이다'],
    ], 'current', '현황조사는 특정 시점의 기록이에요. 점유자·협의·인도 절차와 기간은 다시 확인하고, 비용은 연습에서도 별도로 넣어요.'),
    question(basic, 'fees', 'fees', '체납 합계 152만원과 계산의 관리비 90만원은 왜 다를까요?', [
      ['all', '연체료까지 언제나 낙찰자가 모두 낸다'], ['none', '관리비는 낙찰대금에 포함된다'], ['scope', '이 연습은 공용 90만원 부담을 가정했고, 실제 인수 범위는 항목별 확인이 필요하다'],
    ], 'scope', '공용 90 + 전유 50 + 연체료 12 = 체납 152만원이에요. 체납 합계와 법적 부담액을 혼동하지 말고, 계산에는 확인한 인수액을 넣어요.'),
    question(basic, 'deposit', 'sale', '보증금 비율이 10%인 이 연습의 입찰보증금은 얼마인가요?', [
      ['minimum', '최저가 기준 2,560만원 · 낙찰대금의 일부'], ['bid', '예상 낙찰가 기준 2,700만원 · 추가 비용'], ['loan', '대출 16,200만원의 10%'],
    ], 'minimum', '공고의 가상 보증금 조건은 최저가 25,600만원의 10%예요. 보증금은 낙찰대금에 충당되며 대출 전에 준비할 유동성도 확인해요.'),
    question(basic, 'photo', 'fieldnotes', '실내 연습 사진이 깔끔하면 수리 예산을 확정해도 될까요?', [
      ['check', '누수·설비·구조는 사진 밖의 조사와 견적을 받아 확인한다'], ['zero', '하자가 없으므로 수리비를 0으로 바꾼다'], ['guarantee', '사진이 수리 상태를 보증한다'],
    ], 'check', '연출된 사진은 관찰 연습 도구예요. 누수 원인·설비 상태·구조 안전이나 권리를 보증하지 않으므로 실제 점검 근거를 따로 확보해요.'),
  ];

  const senior = {
    id: 'simulation-senior', title: '빌라 · 먼저 들어온 임차인', level: '중급', fictional: true,
    address: '연습시 가상구 배움길 22, 모의마루 2동 302호', area: 54.2,
    summary: '모의 조건에서 미회수 보증금이 현금·손익에 미치는 영향을 살펴봐요.',
    appraised: 30000, minimum: 24000, financialAssumptionsConfirmed: true,
    photoSet: {
      src: './assets/auction-practice/multifamily-contact-sheet.png', columns: 2, rows: 4,
      fictional: true, aiGenerated: true, buildingType: 'multifamily', damageLocation: 'window',
      positions: { exterior: '0% 0%', entrance: '100% 0%', damage: '0% 33.333333%', neighborhood: '100% 33.333333%' },
    },
    defaults: {
      bid: 24500, minimum: 24000, depositRate: 10, loan: 14000, loanRate: 5,
      months: 9, acquisitionRate: 1.1, legal: 150, repairs: 700, eviction: 400,
      arrears: 120, assumed: 5000, reserve: 800, sale: 33000, downside: 30000,
      sellingRate: 0.5, saleTax: 500, targetProfit: 2000, available: 18000,
    },
    facts: {
      asOf: '2026-09-15', bidDate: '2026-10-22', appraisalDate: '2026-06-12', visitDate: '2026-09-13',
      mortgageDate: '2021-03-15', auctionStartDate: '2026-05-22',
      distributionDeadline: '2026-07-31',
      tenant: { moveInDate: '2019-02-18', fixedDate: '2019-02-19', distributionRequestDate: '2026-07-03', deposit: 12000, assumedDistribution: 7000, assumedUnpaid: 5000 },
      fees: { common: 120, private: 55, late: 15 },
    },
    observations: [
      { id: 'senior-exterior', title: '빌라 외관', photoKey: 'exterior', text: '저층 다세대 외관이에요. 대지권·내진 성능은 서류와 별도 조사로 확인해요.' },
      { id: 'senior-entrance', title: '공동현관·우편함', photoKey: 'entrance', text: '우편함이 보이는 공동현관이에요. 점유자·점유 기간은 전입·계약·현황 자료로 확인해요.' },
      { id: 'senior-damage', title: '창가 얼룩', photoKey: 'damage', text: '창틀 옆 얼룩과 들뜬 마감이 보여요. 결로·누수 원인과 수리 범위는 별도 점검이 필요해요.' },
      { id: 'senior-neighborhood', title: '골목 주차', photoKey: 'neighborhood', text: '좁은 골목에 주차된 차가 보여요. 야간 혼잡·주차 권리·매도 수요는 별도 조사해요.' },
    ],
    comparables: [
      { price: 33200, area: 54.2, date: '2026-08-08', description: '같은 가상 생활권 · 중층 · 수리 완료 · 가상 거래' },
      { price: 31800, area: 54.2, date: '2026-07-09', description: '인접 가상 빌라 · 보통 상태 · 주차 1대 · 가상 거래' },
      { price: 30200, area: 53.9, date: '2026-06-29', description: '인접 가상 빌라 · 저층 · 수리 필요 · 가상 거래' },
    ],
    answer: {
      riskLevel: 'review', assumedCost: 5000,
      estimatedCostsDescription: '가상 배당 7,000만원을 전제로 보증금 12,000만원 중 5,000만원 인수를 가정해요. 실제 배당표·선순위 채권·대항요건을 검토한 결과가 아니에요.',
      mainFindings: [
        '전입 2019-02-18이 근저당 2021-03-15보다 빠르며, 점유·대항요건이 유지된다는 모의 조건이 있어요.',
        '가상 조건의 보증금 잔액 12,000 − 7,000 = 5,000만원을 낙찰가 외 별도 인수액에 넣어야 해요.',
        '배당요구를 했다는 사실만으로 전액 회수나 임대차 종료를 보장하지 않아요.',
        '미회수 보증금을 반영하고 현재 입찰가·대출·가용 현금으로 목표 이익·보수적 손익·현금 여력을 비교해요.',
      ],
      nextChecks: ['대항요건 유지·계약서·보증금·점유와 전입의 실제 관계 확인', '배당표·선순위 채권·배당액과 인수 잔액을 전문가와 확인', '부족한 현금·인도 기간·수리 견적·매도 수요 재검토'],
      plainConclusion: '현재 가정으로는 입찰을 서두르지 않아요. 미회수 보증금·현금 부족·보수적 손실을 함께 검토해요.',
    },
  };
  senior.documents = documentsFor(senior, {
    landRights: '대지권 전부 표시 · 전유부분과 함께 매각하는 모의 조건',
    sale: [
      ['매각 범위', '전유부분 및 표시된 대지권 전부'],
      ['임차인 B', '보증금 12,000만원 · 전입 2019-02-18 · 확정일자 2019-02-19', true],
      ['배당요구', '2026-07-03 제출 · 종기 2026-07-31'],
      ['훈련을 위한 추가 조건', '임차인의 대항요건이 선순위로 성립·계속 유지되고 보증금 전액을 회수할 때까지 매수인에게 대항할 수 있다고 가정', true],
      ['가상 배당 연습값', '12,000만원 중 7,000만원 배당 가정 · 확정 배당표나 자동 산출액 아님', true],
      ['별도 인수 연습값', '미회수 보증금 5,000만원을 매수인이 부담하는 것으로 한정한 모의 조건', true],
      ['실전의 미확인 사항', '실제 배당액·우선 채권·보증금 반환·대항요건 유지와 매각 조건은 원문 검토 필요'],
    ],
    register: [
      ['갑구 소유권', '가상 소유자 B · 2017-04-11 취득'],
      ['을구 근저당권', '2021-03-15 접수 · 채권최고액 18,000만원 · 기준권리 후보', true],
      ['갑구 가압류', '2024-05-02 접수 · 청구 2,000만원'],
      ['갑구 경매개시 기입', '2026-05-22'],
      ['등기의 한계', '임차인의 전입·점유·배당과 보증금 반환은 이 등기 발췌만으로 확정할 수 없음', true],
    ],
    occupancy: [
      ['조사일', '2026-06-20'], ['현재 점유 기재', '가상 임차인 B가 거주한다고 진술'],
      ['점유·전입 시작', '2019-02-18부터 점유와 전입을 계속 유지했다고 가정', true],
      ['확정일자', '2019-02-19'], ['임대차 보증금', '12,000만원 · 계약 갱신으로 순위 변동은 없다는 모의 조건'],
      ['배당요구 자료', '2026-07-03 제출로 가정 · 전액 배당 의미 아님'],
      ['인도 일정', '보증금 회수·인수 잔액과 협의 필요 · 즉시 인도 합의 없음', true],
    ],
    appraisal: [
      ['평가 대상', '전유부분과 표시된 대지권 · 전용 54.2㎡'],
      ['평가 당시 상태', '창가 얼룩과 노후 마감이 있다는 가상 설정'],
      ['수리 예산', '700만원 · 누수 원인·공사 범위 확인 전의 연습 가정'],
      ['권리와 가격', '감정가 30,000만원은 미회수 보증금·인도·실제 매도 가능 가격을 보증하지 않음', true],
    ],
    building: [
      ['대지 위치', senior.address], ['주용도', '공동주택 · 다세대주택'],
      ['사용승인', '2010-05-14'], ['전유 면적', '54.2㎡', true],
      ['위반건축 기재', '이 가상 발췌에는 표시 없음 · 현장 불일치 확인은 별개'],
      ['대조 항목', '전유부분·대지권·주차장 용도와 현장 사용 상태 확인'],
    ],
    feeAssumption: '공용 체납 120만원 부담을 모의 조건으로 넣었어요. 실제 인수 근거와 세대별 기간·연체료·정산 시점은 별도로 확인해요.',
    assumedDescription: '5,000만원 · 보증금 12,000 − 가상 배당 7,000 · 낙찰대금과 별도',
    comparisonLimit: '빌라는 층·도로·주차·대지권·누수에 따라 차이가 커요. 수리 완료 거래 33,200만원만 보고 33,000만원 매도를 확신하지 않아요.',
  });
  senior.quiz = [
    question(senior, 'dates', 'occupancy', '2019년 전입과 2021년 근저당을 비교한 뒤 가장 중요한 추가 확인은?', [
      ['none', '전입이 빠르므로 다른 확인은 필요 없다'], ['conditions', '실제 점유·대항요건의 성립과 유지·계약·보증금·매각 조건을 대조한다'], ['refund', '배당요구를 했으니 보증금 전액 회수로 처리한다'],
    ], 'conditions', '전입일만으로 결론을 내리지 않아요. 이 훈련은 대항요건 유지 등 추가 조건을 명시해 5,000만원 인수 계산을 연습하도록 만든 가상 사례예요.'),
    question(senior, 'unpaid', 'sale', '명시된 모의 조건에서 별도 인수액은 얼마인가요?', [
      ['zero', '배당요구를 했으므로 0만원'], ['remaining', '보증금 12,000 − 가상 배당 7,000 = 5,000만원'], ['all', '가상 배당과 무관하게 12,000만원 전액을 추가한다'],
    ], 'remaining', '이 경우에 한해 미회수 5,000만원을 부담한다고 조건을 정했어요. 7,000만원 배당은 실제 배당표에서 나온 결과가 아니며 실제 사건에는 그대로 적용할 수 없어요.'),
    question(senior, 'cash', 'fees', '인수액 5,000만원을 계산에서 빠뜨리면 어떤 오류가 생기나요?', [
      ['same', '낙찰대금에 이미 포함되어 결과가 같다'], ['loan', '대출금만 5,000만원 줄어든다'], ['understate', '필요 현금이 5,000만원 작게, 예상 이익이 5,000만원 크게 표시된다'],
    ], 'understate', '다른 입력이 같을 때 별도 인수액은 낙찰대금 외 비용이에요. 현금과 손익 양쪽에 반영해야 하며 보증금·예비비와도 구분해요.'),
    question(senior, 'handover', 'occupancy', '현황조사에 임차인 거주와 보증금 미회수가 보이면 어떻게 준비하나요?', [
      ['plan', '인수 잔액·인도 협의·절차·기간·비용을 함께 검토한다'], ['keys', '낙찰 즉시 열쇠 인도를 전제한다'], ['remove', '점유 확인 없이 명도 예산을 없앤다'],
    ], 'plan', '배당과 보증금 회수 상황, 실제 점유자, 협의와 법적 인도 절차를 따로 확인해요. 강제 인도나 일정이 자동 보장되는 것은 아니에요.'),
    question(senior, 'damage', 'fieldnotes', '창가 얼룩 사진을 봤을 때 적절한 기록은?', [
      ['structural', '구조 결함 확정, 보수비도 확정'], ['nothing', '사진에서 작으니 비용 없음'], ['inspect', '얼룩 관찰 사실을 적고 누수·결로 원인과 공사 견적은 미확인으로 남긴다'],
    ], 'inspect', '사진으로 관찰한 사실과 원인 진단은 달라요. 연습의 700만원은 정밀 조사나 실제 견적을 대신하지 않아요.'),
    question(senior, 'market', 'comparables', '수리 완료 거래 33,200만원이 있으니 예상 매도가를 확정할까요?', [
      ['compare', '층·수리·주차·권리·거래 조건을 맞추고 보수적 시나리오도 확인한다'], ['fixed', '최고 거래가를 그대로 보장 가격으로 쓴다'], ['appraisal', '감정가보다 높으면 검토를 마친다'],
    ], 'compare', '비교거래는 가상 자료이며 매도가를 보장하지 않아요. 이 연습의 보수적 매도가 30,000만원에서 손실이 나는 이유까지 계산해 보세요.'),
  ];

  const hold = {
    id: 'simulation-hold', title: '다세대 · 대지권과 위반 표시', level: '주의', fictional: true,
    address: '연습시 가상구 확인길 7, 가상뜰 401호', area: 44.5,
    summary: '대지권·위반건축·점유 미확인을 읽고, 계산에서 빠진 비용을 찾아봐요.',
    appraised: 21000, minimum: 16800, financialAssumptionsConfirmed: false,
    photoSet: {
      src: './assets/auction-practice/multifamily-contact-sheet.png', columns: 2, rows: 4,
      fictional: true, aiGenerated: true, buildingType: 'multifamily', damageLocation: 'wall-ceiling',
      positions: { exterior: '0% 66.666667%', entrance: '100% 66.666667%', damage: '0% 100%', neighborhood: '100% 100%' },
    },
    defaults: {
      bid: 17000, minimum: 16800, depositRate: 10, loan: 8000, loanRate: 5.5,
      months: 12, acquisitionRate: 1.1, legal: 200, repairs: 1500, eviction: 600,
      arrears: 240, assumed: 0, reserve: 1000, sale: 23000, downside: 19000,
      sellingRate: 0.5, saleTax: 350, targetProfit: 1800, available: 14000,
    },
    facts: {
      asOf: '2026-09-15', bidDate: '2026-10-27', appraisalDate: '2026-06-15', visitDate: '2026-09-14',
      mortgageDate: '2022-08-09', auctionStartDate: '2026-05-25',
      distributionDeadline: '2026-07-31', tenant: null,
      fees: { common: 240, private: 80, late: 20 },
    },
    observations: [
      { id: 'hold-exterior', title: '외관·발코니', photoKey: 'exterior', text: '상층 발코니의 다른 창호가 보여요. 확장·허가 여부와 면적·구조는 도면과 관청 자료로 확인해요.' },
      { id: 'hold-entrance', title: '닫힌 출입문', photoKey: 'entrance', text: '닫힌 출입문이에요. 빈집인지, 어떤 권리가 있는지는 이 사진으로 알 수 없어요.' },
      { id: 'hold-damage', title: '천장·벽면 흔적', photoKey: 'damage', text: '천장·벽면 얼룩이 보여요. 수리비 1,500만원에는 미확정 원상복구·이행강제금·대지권 확보 비용이 빠져 있어요.' },
      { id: 'hold-neighborhood', title: '골목과 대지 경계', photoKey: 'neighborhood', text: '좁은 진입로예요. 통행권·경계·대지사용권은 등기·지적도·계약·측량 등으로 확인해요.' },
    ],
    comparables: [
      { price: 23100, area: 44.5, date: '2026-08-12', description: '대지권 표시 있고 위반 표시 없는 가상 비교물건' },
      { price: 21900, area: 45.1, date: '2026-07-22', description: '수리 보통·대지권 표시 있는 인접 가상 물건' },
      { price: 19200, area: 44.5, date: '2026-06-18', description: '저층·수리 필요·권리 정리된 인접 가상 물건' },
    ],
    answer: {
      riskLevel: 'hold', assumedCost: null,
      estimatedCostsDescription: '인수액은 미확정이에요. 계산의 0만원은 하한 가정이며, 확인된 0원이 아니에요. 대지권 확보·위반 시정·보증금·추가 정산 비용은 미반영이에요.',
      mainFindings: [
        '대지권 미등기는 대지사용권이 없다는 확정도, 있다는 보장도 아니에요. 미등기 원인과 매각 범위를 확인해야 해요.',
        '건축물대장의 위반 표시와 현장 확장 부분을 대조하고 시정·이행강제금·원상복구·대출 영향 등을 확인해야 해요.',
        '폐문부재와 전입 자료 미확인 상태여서 실제 점유·보증금·인도 가능 시점도 몰라요.',
        '0만원으로 놓은 미확정 인수액과 누락 비용 때문에 계산 결과가 좋아 보여도 입찰 판단에 사용할 수 없어요.',
      ],
      nextChecks: ['토지·집합건물 등기와 대지사용권의 원인·매각 범위 확인', '관청의 위반 내용·시정 절차·이행강제금·원상복구 견적 확인', '실제 점유·임대차·전입·보증금과 최신 명세서 대조', '확인된 비용과 가능한 대출액으로 자금 시나리오를 다시 계산'],
      plainConclusion: '입찰 보류예요. 미확정 금액을 0원으로 확정하지 말고 권리·위반·점유·비용을 확인한 뒤 다시 계산해요.',
    },
  };
  hold.documents = documentsFor(hold, {
    landRights: '대지권 표시 미등기 · 원인과 대지사용권 유무·매각 범위 미확인',
    sale: [
      ['기재된 대상', '전유부분 44.5㎡ · 대지권 표시 미등기'],
      ['대지권 관련 비고', '대지사용권·미등기 원인·토지 별도 권리와 매각 범위 추가 조사 필요', true],
      ['임대차 기재', '점유자·전입·보증금·배당요구 모두 확인되지 않은 모의 조건', true],
      ['건물 관련 비고', '건축물대장 위반 표시와 현장 확장 흔적 대조 필요'],
      ['인수 금액', '미확정 · 계산의 0만원은 확인된 금액이 아님', true],
      ['입찰 전에 필요한 자료', '최신 명세서와 특별매각조건·토지 및 집합건물 등기·위반 시정 자료·점유 자료'],
    ],
    register: [
      ['갑구 소유권', '가상 소유자 C · 2020-03-12 취득'],
      ['을구 근저당권', '2022-08-09 접수 · 채권최고액 12,000만원 · 기준권리 후보'],
      ['갑구 경매개시 기입', '2026-05-25'],
      ['대지권 표시', '미등기 · 대지사용권 유무와 이유는 이 발췌만으로 알 수 없음', true],
      ['토지 별도 등기', '자료 미확보 · 토지 소유자·사용권 원인·제한권리 미확인', true],
    ],
    occupancy: [
      ['조사일', '2026-06-23'], ['방문 결과', '폐문부재 · 연락하지 못함', true],
      ['점유자·전입일', '미확인 · 빈집이라고 판단할 수 없음', true],
      ['계약·보증금·확정일자', '자료 미확보 · 0원으로 간주하지 않음'],
      ['배당요구', '제출 여부 미확인 · 배당요구종기 2026-07-31'],
      ['현재 확인할 것', '점유자·전입세대 자료·임대차·인도 계획·조사 후 변동'],
    ],
    appraisal: [
      ['평가 기준', '대지사용권 확보를 가정한 평가라는 모의 조건', true],
      ['평가 구성', '건물 11,000만원 + 대지사용권 가정 부분 10,000만원 = 21,000만원'],
      ['권리와 평가의 차이', '평가에 토지가치가 들어갔다고 실제 권리 확보·매각 포함이 확정되지 않음', true],
      ['수리 예산의 누락', '1,500만원은 일반 마감 수리 가정 · 원상복구·이행강제금·권리 확보 비용 미포함', true],
    ],
    building: [
      ['대지 위치', hold.address], ['주용도', '공동주택 · 다세대주택'],
      ['사용승인', '2003-06-12'], ['공부상 전유 면적', '44.5㎡'],
      ['위반건축 표시', '있음 · 2025-09-03 기재 · 발코니 약 6㎡ 무단 확장이라는 모의 조건', true],
      ['시정·이행강제금', '현재 부과·시정 상태와 향후 부담 미확인', true],
      ['면적 대조', '위반 확장 약 6㎡는 공부상 전유 44.5㎡에 더해 정상 매각면적으로 계산하지 않음'],
    ],
    feeAssumption: '공용 240만원만 임시 하한 비용으로 넣었어요. 실제 인수 근거·추가 부과·정산액은 미확인이므로 이 금액으로 완전한 비용 계산을 했다고 볼 수 없어요.',
    assumedDescription: '미확정 · 입력 0만원은 계산 비교용 하한 가정, 확인된 인수액 0원 아님',
    comparisonLimit: '비교물건은 대지권이 표시되고 위반이 없는 조건이에요. 이 물건의 권리·위반을 해결하지 않은 채 같은 가격을 적용하면 안 돼요.',
  });
  hold.quiz = [
    question(hold, 'land', 'register', '“대지권 미등기”를 보고 가장 적절하게 기록하는 방법은?', [
      ['absent', '땅에 대한 권리가 절대로 없다'], ['included', '감정가에 토지가 들어가 있으니 권리도 자동 확보된다'], ['investigate', '미등기 원인·대지사용권·토지 등기·매각 범위를 확인 전까지 보류한다'],
    ], 'investigate', '미등기 표시는 조사 출발점이에요. 권리가 없다고 단정하거나, 감정평가에 포함됐으니 안전하다고 가정할 수 없어요.'),
    question(hold, 'violation', 'building', '위반건축 표시와 약 6㎡ 확장 흔적이 있으면 무엇을 확인하나요?', [
      ['remedy', '위반 내용·시정 현황·원상복구·이행강제금·대출 영향을 관청과 자료로 확인한다'], ['bonus', '면적이 넓어졌으니 시세를 올린다'], ['repair', '일반 수리비에 모두 포함됐다고 본다'],
    ], 'remedy', '공부상 44.5㎡와 위반 확장 약 6㎡를 구분해요. 처리 가능 여부·의무와 비용은 관청 자료·도면·견적으로 검토해야 해요.'),
    question(hold, 'empty', 'occupancy', '“폐문부재, 점유자 미확인”이면 어떤 의미인가요?', [
      ['empty', '빈집이며 인도 비용도 없다'], ['unknown', '조사 때 만나지 못했으며 현재 점유·임대차·보증금은 아직 모른다'], ['noTenant', '임차인이 없으므로 인수액은 확정 0원이다'],
    ], 'unknown', '사람을 만나지 못한 사실과 빈집·무권리 상태는 달라요. 전입·계약·점유 자료와 현황을 다시 확인해야 해요.'),
    question(hold, 'cost', 'fees', '계산기의 별도 인수액 0만원은 무엇을 뜻하나요?', [
      ['confirmed', '모든 권리를 확인했고 낼 돈이 없다는 확정'], ['minimumOnly', '미확정 비용을 빼고 비교하는 하한 가정이며, 최종 투자 판단에는 불충분하다'], ['free', '대지권 확보·위반 시정 비용은 무료다'],
    ], 'minimumOnly', '이 사례의 해설상 인수액은 미확정(null)이에요. 숫자 입력 0은 계산 연습을 위한 임시 가정일 뿐, 모르는 금액을 확인된 0원으로 바꾸지 않아요.'),
    question(hold, 'value', 'appraisal', '감정가 21,000만원에 대지사용권 가정 부분이 포함되면 무엇이 확정되나요?', [
      ['rights', '실제 대지사용권과 소유권 취득이 확정된다'], ['sale', '매도 23,000만원이 보장된다'], ['assumption', '평가의 조건만 알 수 있고 실제 권리·매각 범위는 별도 확인해야 한다'],
    ], 'assumption', '감정평가의 가격 가정은 권리 증명이 아니에요. 매각 범위·대지사용권과 토지 권리 자료를 따로 대조해야 해요.'),
    question(hold, 'compare', 'comparables', '대지권·위반 문제가 없는 비교물건의 가격을 바로 적용해도 될까요?', [
      ['hold', '조건이 다르므로 비용·권리와 매각 가능성을 확인할 때까지 입찰 판단을 보류한다'], ['same', '전용면적이 비슷하니 동일 가격을 쓴다'], ['positive', '계산 이익이 양수이면 불확실성은 무시한다'],
    ], 'hold', '권리·위반·점유와 그 비용을 해결하지 않은 상태에서는 양의 계산 결과도 안전성을 증명하지 않아요. 확인 후 매도·대출·비용을 함께 다시 넣어야 해요.'),
  ];

  function deepFreeze(value) {
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
      Object.values(value).forEach(deepFreeze);
      Object.freeze(value);
    }
    return value;
  }

  return deepFreeze({ version: 1, fictional: true, amountUnit: '만원', disclaimer, cases: [basic, senior, hold] });
});
