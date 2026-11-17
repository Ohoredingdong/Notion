/* Research edition only. Renderer never fetches files, computes signals or mutates storage. */
(function (root) {
  'use strict';
  const escape = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {contract:'계약', convertible:'CB·BW', buyback:'자사주', reorganization:'인수·합병·분할'};
  const metricLabels = {contract_amount:'총 계약금액',deposit_amount:'계약금·선수금',revenue_ratio_pct:'연매출 대비 계약규모 (%)',contract_days:'계약기간 (일)',annualized_scale_pct:'단순 연환산 규모 (%)',potential_new_shares_current:'현재 조건 잠재 신주',potential_new_shares_floor:'하한 조건 잠재 신주',new_to_existing_pct:'기존 유통주식 대비 (%)',fully_diluted_new_pct:'완전희석 후 신주 비중 (%)',floor_to_initial_pct:'최초가 대비 리픽싱 하한 (%)',price_premium_pct:'현재가/전환가 괴리 (%)',exercise_window_open:'행사기간 내',balance_as_of:'잔액 기준일',acquired_shares:'취득 완료 주식',cancelled_shares:'소각 완료 주식'};
  const source = value => {try {const u=new URL(value);return u.protocol==='https:' && ['dart.fss.or.kr','opendart.fss.or.kr','kind.krx.co.kr','www.sec.gov','sec.gov','data.sec.gov'].includes(u.hostname) && !u.username && !u.password && !/(key|token|secret)=/i.test(u.search);} catch (_) {return false;}};
  const format = value => value == null ? '미확인' : typeof value==='boolean' ? (value?'예':'아니요') : typeof value==='number' ? (Number.isFinite(value)?value.toLocaleString('ko-KR',{maximumFractionDigits:2}):'미확인') : escape(value);
  function render(company) {
    if (!company) return '<section class="corporate-evidence"><h3>공시·기업행위</h3><p>이 종목의 공식 공시 수집 상태가 아직 연결되지 않았습니다. 자료 없음은 위험 없음이 아닙니다.</p></section>';
    const filings=company.filings||{}, coverage=filings.coverage||{}, analyses=Array.isArray(company.analyses)?company.analyses:[];
    let html='<section class="corporate-evidence"><h3>공시·기업행위</h3><p>공시 목록: '+(coverage.complete?'지정 범위 수집 완료':'미완료')+' · 원문 분석: '+analyses.length+'건</p><p>목록 수집 완료는 모든 공시의 의미를 분석했다는 뜻이 아닙니다. 없는 자료는 안전·호재로 판단하지 않습니다.</p>';
    if (coverage.start || coverage.end) html+='<p>수집 범위 '+escape(coverage.start||'미확인')+' ~ '+escape(coverage.end||'미확인')+'</p>';
    if (!analyses.length) html+='<p>계약·CB/BW·자사주·M&A의 근거 기반 분석은 아직 없습니다.</p>';
    for(const a of analyses) {
      html+='<details><summary>'+escape(labels[a.kind]||a.kind)+' · '+escape(a.assessment||'판단 미완료')+' · '+(a.status==='evidence_bound'?'입력 근거 연결':'추가 확인 필요')+'</summary>';
      if (a.acquired_and_cancelled_confirmed === true && a.status==='evidence_bound') html+='<p>동일 프로그램 취득·소각 완료 근거 연결</p>';
      html+='<dl>';
      for(const [key,value] of Object.entries(a.metrics||{})) html+='<dt>'+escape(metricLabels[key]||key)+'</dt><dd>'+format(value)+'</dd>';
      html+='</dl><ul>'+(a.notes||[]).map(x=>'<li>'+escape(x)+'</li>').join('')+'</ul>';
      if((a.unknowns||[]).length) html+='<p>미확인: '+a.unknowns.map(escape).join(' · ')+'</p>';
      html+='<p>'+(a.source_urls||[]).filter(source).map((u,i)=>'<a target="_blank" rel="noopener noreferrer" href="'+escape(u)+'">공식 근거 '+(i+1)+'</a>').join(' · ')+'</p></details>';
    }
    const rows=Array.isArray(filings.items)?filings.items:[];
    html+='<details><summary>수집한 공시 목록 '+rows.length+'건</summary><ul>';
    for(const r of rows) html+='<li>'+escape(r.filed_on)+' · '+(source(r.source_url)?'<a target="_blank" rel="noopener noreferrer" href="'+escape(r.source_url)+'">'+escape(r.title)+'</a>':escape(r.title))+(r.amendment?' [정정]':'')+(r.withdrawal?' [철회]':'')+' · 원문 분석 '+(r.semantic_status==='not_parsed'?'미완료':escape(r.semantic_status||'미확인'))+'</li>';
    return html+'</ul></details></section>';
  }
  const api={render};
  if(typeof module==='object' && module.exports) module.exports=api;
  else root.StockCorporateActions=api;
})(typeof globalThis==='object'?globalThis:this);
