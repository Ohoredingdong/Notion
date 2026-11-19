(()=>{'use strict';
const state={sector:'',query:'',companyQuery:'',news:'all'};
const arr=x=>Array.isArray(x)?x:[];
const sector=c=>String(c.sector||c.industry||c.catalog_entry?.sector||'업종 미분류');
const safe=url=>{try{const u=new URL(url);return u.protocol==='https:'&&!u.username&&!u.password?u.href:null}catch{return null}};
function render(c,ctx){
 const H=window.RadarCohesive,E=H.esc,companies=arr(ctx.companies),D=ctx.data||{},groups=new Map();
 companies.forEach(x=>{const k=sector(x);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(x)});
 if(state.sector&&!groups.has(state.sector))state.sector='';
 const selected=state.sector,rows=selected?groups.get(selected):companies;
 const filtered=rows.filter(x=>(String(x.name||'')+' '+String(x.symbol||'')).toLowerCase().includes(state.companyQuery.toLowerCase()));
 const secRows=[...groups].filter(([s])=>s.toLowerCase().includes(state.query.toLowerCase())).sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0]));
 const section=(title,body,sub='')=>`<section class="rcm-card"><header><h2>${E(title)}</h2><span>${E(sub)}</span></header>${body}</section>`;
 const link=(url,label)=>safe(url)?`<a href="${E(safe(url))}" target="_blank" rel="noopener noreferrer">${E(label)}</a>`:E(label);
 const m=D.macro||{},ind=m.indicators||{},f=n=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString('ko-KR',{maximumFractionDigits:2}):'—';
 const datum=(v,keys,unit='%')=>{
  if(!v)return '<span class="rcm-muted">원자료 미연결</span>';
  const nums=keys.map(k=>v[k]);if(nums.some(n=>typeof n!=='number'||!Number.isFinite(n)))return '<span class="rcm-muted">수치 미확인</span>';
  return `<b>${nums.map(f).join(' ~ ')}${E(unit)}</b><small>${E(v.date||'기준일 미확인')} · ${link(v.source_url,'출처')}</small>`;
 };
 const age=Date.parse(m.generated_at||''),stale=!Number.isFinite(age)||Date.now()-age>(Number(m.max_age_hours)||18)*3600000;
 const macro=section('세계·한국 지표 비교',`<div class="rcm-tablewrap"><table><thead><tr><th>항목</th><th>미국 참고</th><th>한국</th><th>점검할 영향</th></tr></thead><tbody>
 <tr><th>경제성장</th><td>원자료 미연결</td><td>원자료 미연결</td><td>수출·내수</td></tr>
 <tr><th>정책금리</th><td>${datum(ind.fed_policy,['low','high'])}</td><td>${datum(ind.bok_policy,['value'])}</td><td>차입비용</td></tr>
 <tr><th>물가</th><td>${datum(ind.us_cpi,['yoy_pct'])}</td><td>원자료 미연결</td><td>마진·소비</td></tr>
 <tr><th>실업률</th><td>${datum(ind.us_unemployment,['value_pct'])}</td><td>원자료 미연결</td><td>고용·소비</td></tr>
 <tr><th>정치·정책</th><td colspan="2">정책별 원문 검증 필요</td><td>산업별 수혜·부담</td></tr></tbody></table></div><p class="rcm-note">미국 자료는 세계 전체를 대표하지 않습니다. 영향은 점검 항목이며 현재 수혜 판정이 아닙니다.</p><p class="rcm-muted">수집: ${E(m.generated_at||'미확인')} · ${stale?'갱신 확인 필요':'저장 자료 기준'}</p>`,stale?'갱신 확인 필요':'저장된 지표');
 const newsRows=arr(D.newsLink?.items).filter(n=>n&&typeof n.title==='string'&&Number.isFinite(Date.parse(n.published_at))&&Date.parse(n.published_at)<=Date.now()&&(state.news==='all'||n.region===state.news)).sort((a,b)=>Date.parse(b.published_at)-Date.parse(a.published_at)).slice(0,5);
 const news=section('경제·정책 뉴스',`<div class="rcm-tabs">${[['all','전체'],['us','미국'],['kr','한국']].map(([v,l])=>`<button data-rcm-news="${v}" aria-pressed="${state.news===v}">${l}</button>`).join('')}</div>${newsRows.length?newsRows.map(n=>`<article class="rcm-news"><span class="rcm-badge">${E(n.region==='kr'?'한국':n.region==='us'?'미국':n.region||'기타')}</span><div><strong>${link(n.url,n.title)}</strong><small>${E(n.source||'출처 미확인')} · ${E(n.published_at)} · RSS 제목 / 원문 검증 전</small></div></article>`).join(''):'<p class="rcm-muted">조건에 맞는 저장 뉴스가 없습니다.</p>'}<p class="rcm-note">뉴스 제목만으로 수혜 산업을 자동 확정하지 않습니다. 산업 영향 원문 분석은 미연결입니다.</p>`, '저장된 뉴스 · 실시간 아님');
 const industry=section('산업 비교',`<div class="rcm-toolbar"><input data-rcm-search="sector" aria-label="산업 검색" placeholder="산업 검색" value="${E(state.query)}"><button data-rcm-sector="" aria-pressed="${!selected}">전체 업종</button><span>산업 선택 → 오른쪽 기업 필터</span></div><div class="rcm-industry-scroll"><table><thead><tr><th>산업</th><th>등록 기업</th><th>수요</th><th>수익성</th><th>정책·위험</th><th>검토</th></tr></thead><tbody>${secRows.map(([s,list])=>`<tr class="${s===selected?'rcm-selected':''}"><th><button data-rcm-sector="${E(s)}" aria-pressed="${s===selected}">${E(s)}</button></th><td>${list.length.toLocaleString()}개</td><td>원자료 미연결</td><td>원자료 미연결</td><td>원문 검증 전</td><td>${s===selected?'선택됨':'미판정'}</td></tr>`).join('')||'<tr><td colspan="6">일치하는 산업이 없습니다.</td></tr>'}</tbody></table></div><p class="rcm-muted">분류 출처: 현재 국가 기업 데이터의 sector / industry 필드. 명부에 업종이 없는 기업은 미분류이며 임의 배정하지 않습니다. 기업 수는 산업 강도나 추천 순위가 아닙니다.</p>`);
 const detail=section('선택 산업: '+(selected||'전체 업종'),`<div class="rcm-detail">${[['수요','생산·수출·수주 원자료 미연결'],['공급','증설·가동률·재고 원자료 미연결'],['수익성','산업 이익률 시계열 미연결'],['주요 위험','정책·경쟁·노사 원문 분석 대기']].map(([t,b])=>`<div><strong>${t}</strong><p>${b}</p></div>`).join('')}</div>`, '확인되지 않은 수혜·주도산업 판정 없음');
 const fav=companies.filter(x=>arr(ctx.favorites).includes(H.id(x)));
 const side=section('기업 선택',`<input data-rcm-search="company" aria-label="기업명 종목 검색" placeholder="기업명·종목 검색" value="${E(state.companyQuery)}"><h3>관심종목</h3>${fav.length?H.stockRows(fav,{max:3,showPrice:false}):'<p class="rcm-muted">별을 눌러 관심종목을 추가하세요.</p>'}<h3>${E(selected||'전체 업종')} 기업 <small>${filtered.length.toLocaleString()}개</small></h3><div class="rcm-companies">${filtered.length?H.stockRows(filtered,{max:100,showPrice:false}):'<p>선택 조건에 맞는 기업이 없습니다.</p>'}</div>${filtered.length>100?'<p class="rcm-muted">상위 100개 표시 · 검색으로 범위를 좁혀주세요.</p>':''}<p class="rcm-note">산업을 바꾸면 기업 목록도 바뀝니다. 기업 선택은 공통 기업분석·공시·차트에 적용됩니다.</p>`, '선택 국가 기업');
 return `<div class="rcm-layout"><div class="rcm-main"><div class="rcm-top">${macro}${news}</div>${industry}${detail}</div><aside>${side}</aside></div>`;
}
function handle(event,ctx){
 const target=event.target?.closest?.('[data-rcm-sector],[data-rcm-news],[data-rcm-search]');if(!target)return false;
 if(target.hasAttribute('data-rcm-search')){if(event.type!=='input'&&event.type!=='change')return false;state[target.dataset.rcmSearch==='sector'?'query':'companyQuery']=target.value;return true;}
 if(event.type!=='click')return false;
 if(target.hasAttribute('data-rcm-sector')){state.sector=target.dataset.rcmSector;state.companyQuery='';return true;}
 state.news=target.dataset.rcmNews;return true;
}
window.RadarCohesiveMarket={render,handle};
})();
