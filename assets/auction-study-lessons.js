/* Fictional reading exercises. These records never update a user's notebook. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.AuctionLessons = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const caption = '가상 학습 발췌 · 실제 사건이나 원문 서류를 옮긴 자료가 아닙니다.';
  const source = {
    court: {name: '법원경매정보 · 매각 서류', href: 'https://www.courtauction.go.kr/'},
    registry: {name: '인터넷등기소 · 등기 확인', href: 'https://www.iros.go.kr/'},
    building: {name: '정부24 · 건축물대장', href: 'https://www.gov.kr/'},
    land: {name: '토지이음 · 토지·규제', href: 'https://www.eum.go.kr/'},
    management: {name: 'K-apt · 단지 관리비 참고', href: 'https://www.k-apt.go.kr/'},
  };
  const topics = [
    {id: 'identity', label: '서류 대조'},
    {id: 'priority', label: '말소·인수'},
    {id: 'tenant', label: '임차보증금'},
    {id: 'occupancy', label: '점유·인도'},
    {id: 'costs', label: '추가 비용'},
    {id: 'exceptions', label: '현장·예외'},
  ];
  const cases = [
    {
      id: 'practice-apartment-basics', title: '기본부터 읽는 아파트', level: '입문', fictional: true,
      summary: '연습아파트 101동 803호의 가상 자료로, 같은 물건인지부터 비용·현장 확인까지 차례로 읽어요.',
      steps: [
        {
          id: 'identity', title: '가격보다 물건 표시부터 맞춰요',
          documentTitle: '매각물건명세서와 등기 표제부', documentCaption: caption,
          rows: [
            {label: '명세서 물건 표시', value: '연습아파트 101동 803호 · 전용 84㎡', focus: true},
            {label: '등기 표제부', value: '연습아파트 101동 803호 · 전용 84.00㎡', focus: true},
            {label: '명세서 매각 범위', value: '전유부분과 대지권 전부 · 가상 설정', focus: true},
            {label: '명세서 작성일', value: '2026-10-10'},
            {label: '등기 열람일', value: '2026-10-20'},
          ],
          question: '두 서류에서 같은 물건인지 판단할 때 무엇을 대조할까요?',
          choices: [
            {id: 'basic-identity-area', text: '면적이 같으니 다른 항목은 생략한다'},
            {id: 'basic-identity-match', text: '주소·동호수·면적·매각 범위를 함께 대조한다'},
            {id: 'basic-identity-price', text: '감정가가 비슷하면 같은 물건으로 본다'},
          ],
          correctChoice: 'basic-identity-match', hint: '가격보다 물건 표시와 매각 범위가 같은지 먼저 보세요.',
          explanation: '동·호수와 면적을 두 서류에서 대조하고 매각 범위까지 확인해요. 같은 주소라도 공유지분만 매각될 수 있습니다.',
          evidencePrompt: '내 물건의 서류명·열람일과 대조한 주소·면적·지분을 기록하세요.',
          checklist: ['명세서와 등기의 물건 표시 대조', '매각 지분·범위와 자료 기준일 확인'],
          sources: [source.court, source.registry],
        },
        {
          id: 'priority', title: '기준권리 후보와 인수 판단을 구분해요',
          documentTitle: '등기 갑구·을구와 명세서 비고', documentCaption: caption,
          rows: [
            {label: '을구 근저당권', value: '2020-04-15 접수', focus: true},
            {label: '갑구 가압류', value: '2023-02-03 접수', focus: true},
            {label: '경매개시 기입', value: '2026-06-10'},
            {label: '명세서 비고', value: '이 발췌에는 별도 인수 조건 기재 없음'},
            {label: '원문 확인 범위', value: '권리 전체·최신 변동·특별매각조건은 추가 확인', focus: true},
          ],
          question: '말소기준권리의 후보를 찾은 다음 무엇을 확인해야 할까요?',
          choices: [
            {id: 'basic-priority-compare', text: '근저당을 후보로 두고 권리 종류·매각 조건을 대조한다'},
            {id: 'basic-priority-date', text: '접수일이 늦은 권리는 모두 자동 소멸한다고 결론 낸다'},
            {id: 'basic-priority-auction', text: '경매개시일만 읽고 나머지 권리는 생략한다'},
          ],
          correctChoice: 'basic-priority-compare', hint: '날짜의 앞뒤뿐 아니라 갑구·을구와 명세서를 함께 읽으세요.',
          explanation: '이 발췌에서는 근저당을 후보로 찾을 수 있어요. 실제 소멸·인수 판단은 권리 종류, 선순위 권리와 특별매각조건까지 대조해야 합니다.',
          evidencePrompt: '기준권리 후보의 종류·접수일·등기 순위와 추가 확인할 매각 조건을 적으세요.',
          checklist: ['기준권리 후보의 종류와 접수일 확인', '선순위 권리·특별매각조건과 대조'],
          sources: [source.registry, source.court],
        },
        {
          id: 'tenant', title: '날짜 다음에 확인할 임차인 자료를 찾아요',
          documentTitle: '매각물건명세서 임대차 항목과 등기', documentCaption: caption,
          rows: [
            {label: '근저당권 접수일', value: '2020-04-15', focus: true},
            {label: '임차인 전입일', value: '2022-03-02', focus: true},
            {label: '확정일자', value: '2022-03-04'},
            {label: '임차보증금', value: '5,000만원 · 가상 설정'},
            {label: '배당요구 기재', value: '2026-07-01 제출 · 종기 2026-08-10'},
            {label: '현재 점유·배당 가능액', value: '추가 확인 필요', focus: true},
          ],
          question: '위 날짜를 비교한 것만으로 보증금 검토를 끝내도 될까요?',
          choices: [
            {id: 'basic-tenant-zero', text: '전입일이 늦으니 추가 확인 없이 인수액은 0원이다'},
            {id: 'basic-tenant-paid', text: '배당요구를 했으니 보증금이 전액 배당된다'},
            {id: 'basic-tenant-evidence', text: '점유·대항요건과 배당자료까지 확인한 뒤 판단한다'},
          ],
          correctChoice: 'basic-tenant-evidence', hint: '날짜와 제출 기재로 확인된 사실, 아직 모르는 사실을 나눠 보세요.',
          explanation: '날짜 비교는 출발점이에요. 실제 점유·대항요건, 기준권리의 효력과 배당자료를 대조하기 전에는 인수금액을 확정하지 않아요.',
          evidencePrompt: '점유·전입·확정일자·배당요구의 근거와 배당 가능액의 미확인 부분을 적으세요.',
          checklist: ['임차인 자료와 기준권리의 효력 대조', '점유·대항요건·배당요구·배당 가능액 확인'],
          sources: [source.court, source.registry],
        },
        {
          id: 'occupancy', title: '조사 당시의 기록과 현재 점유를 구분해요',
          documentTitle: '현황조사서의 방문·점유 기록', documentCaption: caption,
          rows: [
            {label: '현황조사일', value: '2026-09-12'},
            {label: '조사 메모', value: '방문 시 폐문부재 · 현장에서 접촉하지 못함', focus: true},
            {label: '명세서 임대차', value: '임차인 기재 있음 · 보증금 5,000만원'},
            {label: '열쇠·인도 일정', value: '미확인', focus: true},
            {label: '조사 후 변동', value: '현재 점유자·임대차 변동은 추가 확인 필요'},
          ],
          question: '현황조사서에 적힌 “폐문부재”는 무엇을 뜻하나요?',
          choices: [
            {id: 'basic-occupancy-empty', text: '비어 있는 집이라 바로 입주할 수 있다'},
            {id: 'basic-occupancy-check', text: '방문 때 만나지 못했으며 현재 점유는 추가 확인해야 한다'},
            {id: 'basic-occupancy-rights', text: '임차인의 권리가 모두 소멸한 상태다'},
          ],
          correctChoice: 'basic-occupancy-check', hint: '조사 때 관찰한 사실과 지금의 점유 상태는 같다고 단정할 수 없어요.',
          explanation: '폐문부재는 조사 당시 문이 닫혀 접촉하지 못했다는 기록이에요. 빈집·인도 가능일을 뜻하지 않으므로 현재 점유자와 인도 절차를 확인합니다.',
          evidencePrompt: '조사일·현장 확인일·실제 점유자·인도 계획과 남은 질문을 기록하세요.',
          checklist: ['현황조사와 현재 점유 상태 대조', '인도 시점·협의·법적 절차와 비용 검토'],
          sources: [source.court],
        },
        {
          id: 'costs', title: '체납 총액과 내가 부담할 금액을 나눠요',
          documentTitle: '관리사무소 확인 내역과 별도 비용 점검표', documentCaption: caption,
          rows: [
            {label: '내역 기준일', value: '2026-10-21 · 관리사무소 가상 안내'},
            {label: '공용부분 체납', value: '80만원', focus: true},
            {label: '전유부분 체납', value: '40만원', focus: true},
            {label: '연체료', value: '10만원', focus: true},
            {label: '별도 인수·인도 비용', value: '아직 미확인'},
          ],
          question: '관리비 합계 130만원을 그대로 확정 인수액으로 넣어도 될까요?',
          choices: [
            {id: 'basic-costs-separated', text: '공용·전유·연체료와 인수 근거를 나눠 확인한다'},
            {id: 'basic-costs-all', text: '체납 총액 130만원을 반드시 전부 인수한다'},
            {id: 'basic-costs-included', text: '관리비는 낙찰대금에 포함되므로 확인할 필요가 없다'},
          ],
          correctChoice: 'basic-costs-separated', hint: '관리사무소의 세대별 내역을 읽으세요. 단지 공시와 세대 체납은 달라요.',
          explanation: '체납 합계와 낙찰자가 부담할 금액은 같다고 단정할 수 없어요. 공용·전유 구분, 부과 내역과 인수 근거를 확인한 금액만 계산에 반영합니다.',
          evidencePrompt: '관리사무소의 세대별 내역·기준일·인수 근거와 확인된 추가 비용을 기록하세요.',
          checklist: ['세대별 체납 내역과 인수 근거 확인', '확인한 추가 부담만 투자금에 직접 반영'],
          sources: [source.court, source.management],
        },
        {
          id: 'exceptions', title: '발췌에 없는 사실도 확인 대상으로 남겨요',
          documentTitle: '등기·건축물대장과 현장 확인 항목', documentCaption: caption,
          rows: [
            {label: '매각 대상', value: '전유부분과 대지권 전부 · 가상 설정'},
            {label: '등기·명세서 대조', value: '대지권 표시 있음'},
            {label: '건축물대장 발췌', value: '이 발췌 범위에 위반건축 표시 없음', focus: true},
            {label: '현장 점검', value: '아직 진행하지 않음', focus: true},
            {label: '추가 확인 범위', value: '토지별도등기·현장 변경·특별매각조건'},
          ],
          question: '발췌에 위반건축 표시가 없으면 예외 확인을 마쳐도 될까요?',
          choices: [
            {id: 'basic-exceptions-price', text: '감정가가 높으면 법적 예외는 무시해도 된다'},
            {id: 'basic-exceptions-clear', text: '발췌에 없으므로 현장과 대지권도 자동으로 정상이다'},
            {id: 'basic-exceptions-verify', text: '최신 원문과 현장을 대조하고 미확인 사항을 남긴다'},
          ],
          correctChoice: 'basic-exceptions-verify', hint: '“이 발췌에 없음”과 “모두 확인함”을 구분해 보세요.',
          explanation: '발췌에 표시가 없다는 사실만으로 모든 예외가 사라지지는 않아요. 최신 등기·건축물대장·매각 조건과 현장을 대조하고 남은 질문을 기록합니다.',
          evidencePrompt: '대지권·토지별도등기·위반건축·현장 상태에서 확인한 근거와 질문을 적으세요.',
          checklist: ['최신 등기·건축물대장·매각 조건 대조', '현장 불일치와 전문가에게 물을 질문 기록'],
          sources: [source.registry, source.building, source.land],
        },
      ],
    },
    {
      id: 'practice-earlier-tenant', title: '전입이 더 빠른 임차인', level: '응용', fictional: true,
      summary: '연습빌라 202호의 가상 자료로, 앞선 전입일과 미확인 배당·비용을 어떻게 읽을지 공부해요.',
      steps: [
        {
          id: 'identity', title: '같은 호수라도 매각 범위를 따로 읽어요',
          documentTitle: '매각물건명세서와 등기 표제부', documentCaption: caption,
          rows: [
            {label: '명세서 물건 표시', value: '연습빌라 202호 · 전용 59.50㎡', focus: true},
            {label: '등기 표제부', value: '연습빌라 202호 · 전용 59.50㎡', focus: true},
            {label: '명세서 매각 범위', value: '전유부분과 대지권 전부 · 가상 설정', focus: true},
            {label: '등기 지분 표시', value: '소유권 1/1 · 대지권 표시 있음'},
            {label: '자료 기준일', value: '명세서 2026-10-12 · 등기 열람 2026-10-23'},
          ],
          question: '이 사례에서 매각 범위를 확인할 근거는 어느 부분인가요?',
          choices: [
            {id: 'tenant-identity-deposit', text: '임차보증금 액수만 확인한다'},
            {id: 'tenant-identity-range', text: '명세서 매각 범위와 등기의 권리·지분 표시를 대조한다'},
            {id: 'tenant-identity-area', text: '전용면적이 같으니 매각 범위는 생략한다'},
          ],
          correctChoice: 'tenant-identity-range', hint: '물건 표시가 일치하는지와 무엇이 얼마만큼 매각되는지는 다른 질문이에요.',
          explanation: '이 연습 자료에는 전부 매각과 소유권 1/1이 표시돼 있어요. 실제 물건도 명세서의 매각 범위와 등기 권리·지분을 각각 확인해야 합니다.',
          evidencePrompt: '같은 물건인지 대조한 내용과 전부·지분 매각의 근거를 따로 적으세요.',
          checklist: ['주소·동호수·면적의 일치 확인', '전부·지분 매각 범위와 등기 지분 대조'],
          sources: [source.court, source.registry],
        },
        {
          id: 'priority', title: '전입일과 등기 권리의 성격을 구분해요',
          documentTitle: '등기 권리와 명세서 임차인 날짜 대조', documentCaption: caption,
          rows: [
            {label: '임차인 전입일', value: '2018-03-02', focus: true},
            {label: '을구 근저당권', value: '2020-04-15 접수', focus: true},
            {label: '갑구 가압류', value: '2023-02-03 접수'},
            {label: '을구 전세권', value: '이 발췌에는 기재 없음'},
            {label: '명세서 비고', value: '임대차와 인수 관계는 추가 검토 필요'},
          ],
          question: '전입일이 더 빠르면 그 날짜가 곧 말소기준권리가 되나요?',
          choices: [
            {id: 'tenant-priority-first', text: '가장 빠른 전입일이 곧 말소기준권리다'},
            {id: 'tenant-priority-ignore', text: '근저당이 있으므로 임차인은 검토에서 제외한다'},
            {id: 'tenant-priority-kind', text: '전입일과 등기 권리의 성격을 구분해 기준권리 후보를 찾는다'},
          ],
          correctChoice: 'tenant-priority-kind', hint: '권리의 종류와 임차인의 대항요건을 한 날짜 목록으로 섞지 마세요.',
          explanation: '전입일은 근저당 접수일과 성격이 달라요. 등기 권리에서 기준권리 후보를 찾고, 임차인의 대항요건과 인수 가능성은 별도로 대조합니다.',
          evidencePrompt: '등기 권리의 종류·접수일과 임차인 날짜를 구분해 근거를 남기세요.',
          checklist: ['등기 권리에서 기준권리 후보 확인', '임차인의 대항요건과 선후 관계 별도 검토'],
          sources: [source.registry, source.court],
        },
        {
          id: 'tenant', title: '앞선 전입일을 인수금액으로 바꾸지 않아요',
          documentTitle: '명세서 임대차 항목과 미확인 배당자료', documentCaption: caption,
          rows: [
            {label: '임차인 전입일', value: '2018-03-02', focus: true},
            {label: '확정일자', value: '2018-03-05'},
            {label: '근저당권 접수일', value: '2020-04-15'},
            {label: '임차보증금', value: '1억 2,000만원 · 가상 설정'},
            {label: '배당요구', value: '원문 확인 전 · 이 발췌에는 없음', focus: true},
            {label: '현재 점유·예상 배당액', value: '미확인', focus: true},
          ],
          question: '전입일이 더 빠른 이 사례에서 우선 할 일은 무엇인가요?',
          choices: [
            {id: 'tenant-tenant-verify', text: '점유·대항요건·배당요구와 예상 배당 부족액을 확인한다'},
            {id: 'tenant-tenant-all', text: '전입일만 보고 보증금 1억 2,000만원 전액 인수를 확정한다'},
            {id: 'tenant-tenant-zero', text: '경매에서는 항상 전액 배당되므로 인수액은 0원이다'},
          ],
          correctChoice: 'tenant-tenant-verify', hint: '전입일이 앞선 사실과 배당요구·배당 가능액을 확인한 사실은 달라요.',
          explanation: '앞선 전입일은 추가 검토의 신호예요. 현재 점유 등 대항요건, 배당요구와 배당 가능액을 확인하기 전에는 전액 인수나 0원을 단정하지 않아요.',
          evidencePrompt: '대항요건·배당요구·배당 가능액의 확인 근거와 아직 모르는 항목을 적으세요.',
          checklist: ['현재 점유 등 대항요건의 근거 확인', '배당요구·배당 가능액과 부족액 검토'],
          sources: [source.court, source.registry],
        },
        {
          id: 'occupancy', title: '거주 진술과 인도 합의는 달라요',
          documentTitle: '현황조사서의 면담 기록과 인도 확인 항목', documentCaption: caption,
          rows: [
            {label: '현황조사일', value: '2026-09-15'},
            {label: '조사 당시 면담', value: '임차인이 거주 중이라고 진술', focus: true},
            {label: '진술의 범위', value: '조사 당시 당사자 진술 요약 · 가상 설정'},
            {label: '인도 합의', value: '인도일·합의금·이사비 확약 없음', focus: true},
            {label: '조사 후 변동', value: '최신 점유·임대차 변동 여부 미확인'},
          ],
          question: '거주 기록만으로 인도 일정과 비용을 확정할 수 있나요?',
          choices: [
            {id: 'tenant-occupancy-free', text: '조사에 응했으니 잔금일 무상 인도가 확정된다'},
            {id: 'tenant-occupancy-plan', text: '최신 점유와 합의·법적 절차를 따로 확인해 계획한다'},
            {id: 'tenant-occupancy-never', text: '임차인이 있으면 검토 없이 인도가 항상 불가능하다'},
          ],
          correctChoice: 'tenant-occupancy-plan', hint: '누가 거주한다고 진술했는지와 언제 어떤 조건으로 인도하는지 구분하세요.',
          explanation: '거주 진술은 인도 합의가 아니에요. 현재 점유를 다시 확인하고 협의·법적 절차, 일정과 예상 비용을 각각 검토해야 합니다.',
          evidencePrompt: '점유 진술의 출처·조사일, 최신 점유와 인도 합의·절차의 확인 내용을 적으세요.',
          checklist: ['과거 진술과 현재 점유 상태 대조', '인도 합의·일정·절차·비용의 근거 확인'],
          sources: [source.court],
        },
        {
          id: 'costs', title: '모르는 비용을 0원 확정으로 숨기지 않아요',
          documentTitle: '임차보증금·관리비·인도 비용 점검표', documentCaption: caption,
          rows: [
            {label: '임차보증금', value: '1억 2,000만원'},
            {label: '예상 배당액', value: '미확인', focus: true},
            {label: '보증금 인수액', value: '미확정 · 별도 권리 검토 필요', focus: true},
            {label: '관리비 내역', value: '공용 60 · 전유 30 · 연체료 10만원 · 가상 설정'},
            {label: '인도 비용', value: '합의·절차 전 · 미확정', focus: true},
          ],
          question: '인수보증금이 미확정이면 투자금 계산에 어떻게 접근할까요?',
          choices: [
            {id: 'tenant-costs-zero', text: '모르는 비용은 0원으로 두고 수익이 좋으면 입찰한다'},
            {id: 'tenant-costs-all', text: '보증금·체납 합계를 확정 인수액으로 자동 합산한다'},
            {id: 'tenant-costs-range', text: '미확정 항목을 표시하고 근거 있는 범위별 금액을 검토한다'},
          ],
          correctChoice: 'tenant-costs-range', hint: '확인된 비용과 아직 모르는 비용을 한 숫자로 섞지 마세요.',
          explanation: '미확정 비용을 0원 확정으로 취급하지 않아요. 추가 확인 질문을 남기고 인수금액·관리비·인도비의 근거 있는 범위를 나눠 자금 여력을 검토합니다.',
          evidencePrompt: '확정한 비용의 근거와 미확정 항목·추가 확인 질문을 나눠 기록하세요.',
          checklist: ['인수보증금·관리비·인도비를 구분', '미확정 금액과 자금 여력의 확인 질문 기록'],
          sources: [source.court, source.registry],
        },
        {
          id: 'exceptions', title: '위반 표시를 확인 질문으로 연결해요',
          documentTitle: '건축물대장·대지권과 현장 확인 항목', documentCaption: caption,
          rows: [
            {label: '매각 대상', value: '연습빌라 202호 전부 · 가상 설정'},
            {label: '건축물대장 표시', value: '위반건축물 · 가상 기재', focus: true},
            {label: '위반 세부·정리 비용', value: '해당 원문과 부담 내용 추가 확인 필요', focus: true},
            {label: '대지권 등기', value: '표시 있음 · 최신 원문 대조 필요'},
            {label: '현장 상태', value: '이 발췌만으로 알 수 없음'},
          ],
          question: '위반건축물 표시를 발견했다면 다음 확인은 무엇인가요?',
          choices: [
            {id: 'tenant-exceptions-detail', text: '위반 내용·시정 가능성·비용과 실제 현장을 확인한다'},
            {id: 'tenant-exceptions-erased', text: '낙찰받으면 위반 표시와 관련 비용이 자동으로 사라진다'},
            {id: 'tenant-exceptions-skip', text: '임차인 날짜를 확인했으니 건축물대장은 생략한다'},
          ],
          correctChoice: 'tenant-exceptions-detail', hint: '표시의 존재를 찾은 다음에는 구체적인 내용과 부담을 확인해야 해요.',
          explanation: '위반 표시를 찾았어도 내용과 부담이 확정된 것은 아니에요. 원문과 현장을 대조하고 시정 가능성·비용을 확인할 질문을 구체화합니다.',
          evidencePrompt: '위반 내용·현장 차이·시정 가능성과 비용에 대해 확인할 질문을 남기세요.',
          checklist: ['건축물대장·등기·현장의 불일치 확인', '전문가에게 물을 시정 가능성·부담 질문 기록'],
          sources: [source.building, source.registry, source.land],
        },
      ],
    },
  ];

  function deepFreeze(value) {
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
      Object.values(value).forEach(deepFreeze);
      Object.freeze(value);
    }
    return value;
  }
  deepFreeze(topics);
  deepFreeze(cases);
  const byId = new Map(cases.map(item => [item.id, item]));

  function validateAnswer(caseId, stepIndex, choiceId) {
    if (typeof caseId !== 'string' || !Number.isInteger(stepIndex) ||
        typeof choiceId !== 'string') return {valid: false, correct: false};
    const item = byId.get(caseId);
    if (!item || stepIndex < 0 || stepIndex >= item.steps.length) return {valid: false, correct: false};
    const step = item.steps[stepIndex];
    if (!step.choices.some(choice => choice.id === choiceId)) return {valid: false, correct: false};
    return {valid: true, correct: choiceId === step.correctChoice};
  }

  return Object.freeze({cases, topics, validateAnswer});
});
