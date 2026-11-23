/* Research-only foreign issuer metadata. Country qualified IDs cannot resolve
   through the legacy KR/US engine. No recommendation or valuation synthesis. */
(()=>{
'use strict';
const key=/^[A-Z0-9][A-Z0-9.-]{0,14}$/;
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().startsWith(x);
const num=x=>typeof x==='number'&&Number.isFinite(x);
const txt=x=>typeof x==='string'?x.trim().slice(0,230):'';
const https=x=>{try{const u=new URL(x);return u.protocol==='https:'&&!u.username&&!u.password?u.href:''}catch{return ''}};
const all=['JP','CN','HK','TW','GB','DE','VN','SG'];
const has=k=>all.includes(k);
let tw=null, twState='loading', cached=null;
const sample=window.RadarCohesiveForeignSamples||[];
const industry=window.RadarCohesiveForeignIndustry||{};
const states=new Map();
function ui(country){if(!states.has(country))states.set(country,{sector:'',query:'',companyQuery:'',limit:70});return states.get(country)}
function rows(){
 if(cached)return cached;
 const records=[], seen=new Set();
 for(const item of [...sample,...(tw?.items||[]).map(x=>({...x,country:'TW'}))]){
  const c=item.country,symbol=txt(item.symbol),name=txt(item.name),sector=txt(item.sector),id=c+':'+symbol;
  if(!has(c)||!key.test(symbol)||!name||!sector||seen.has(id))continue;
  const twse=c==='TW'&&tw;
  const source=https(twse?twse.source_url:item.source_url), exchange=txt(twse?twse.exchange:item.exchange), verified=twse?twse.listed_day:item.verified_on;
  if(!source||!exchange||!day(verified)||Date.parse(verified)>Date.now())continue;
  const priced=twse&&num(item.price)&&item.price>0&&day(twse.price_day)&&Date.parse(twse.price_day)<=Date.now();
  const aliases=Array.isArray(item.aliases)?item.aliases.map(txt).filter(Boolean):[];
  if(c==='TW'&&symbol==='2330')aliases.push('대만 TSMC','타이완 반도체','대만반도체');
  records.push({foreign_catalog:true,catalog_only:true,country:c,market:c,selection_id:id,symbol,name,sector,exchange,aliases,
    ...(priced?{price:item.price,currency:'TWD',price_session:twse.price_day,turnover:num(item.turnover)&&item.turnover>0?item.turnover:null}:{}),
    sources:{profile:source},business_summary:txt(item.business),
    industry_metadata:{industry:sector,checked_at:verified,source_url:source},
    foreign:{industryCode:item.industry_code,basis:twse?'TWSE 공식 업종 분류 · 한국어 번역':txt(item.basis),verified,source,exchange,
      price_source_url:priced?https(twse.price_source_url):'',license_url:twse?https(twse.license_url):''}});
  seen.add(id);
 }
 cached=records;
 return records;
}
function setTW(payload){
 if(payload?.country!=='TW'||payload.coverage!=='exchange'||payload.exchange!=='TWSE'||payload.source_url!=='https://data.gov.tw/en/datasets/18419'||payload.price_source_url!=='https://data.gov.tw/en/datasets/11549'||payload.license_url!=='https://data.gov.tw/license'||!day(payload.listed_day)||!day(payload.price_day)||!Array.isArray(payload.items)||payload.items.length<900||payload.items.length>1500)throw Error('unverified TWSE catalog');
 tw=payload;cached=null;twState='ready';
}
function load(done){
 fetch('./stock-research-twse-catalog.json?v=20261123-foreign1',{cache:'no-cache',credentials:'same-origin'}).then(r=>{if(!r.ok)throw Error('TWSE catalog unavailable');return r.json()}).then(setTW).catch(()=>{twState='error'}).finally(done);
}
function search(c){return [c.name,c.symbol,c.selection_id,c.exchange,c.sector,...(c.aliases||[])].filter(Boolean).join(' ')}
const normalized=v=>String(v??'').normalize('NFKC').trim().toLowerCase();
const matches=(v,q)=>normalized(v).includes(normalized(q));
function summary(c,items){
 const priced=items.filter(x=>num(x.price)).length;
 if(c==='TW'&&!items.length)return twState==='loading'?'TWSE 상장 명부 불러오는 중':'TWSE 상장 명부를 불러오지 못했습니다.';
 if(c==='TW')return 'TWSE 상장기업 '+items.length.toLocaleString()+'개 · TDR·ETF 제외 · 저장 종가 '+priced.toLocaleString()+'개 ('+tw.price_day+')';
 return '공식 출처 확인 표본 '+items.length+'개 · 전체 상장기업 아님 · 개별 수치 미연결';
}
function sourceLine(c){
 const {esc:E,link}=window.RadarCohesive;
 if(c!=='TW'||!tw)return '';
 return '<p class="rc-source-mini rc-tw-source">'+E(tw.attribution)+' · 명부 '+E(tw.listed_day)+' · '+link(tw.source_url,'상장 명부')+' · '+link(tw.price_source_url,'종가·거래대금')+' · '+link(tw.sector_source_url,'산업 지수')+' · '+link(tw.classification_source_url,'분류 기준')+' · '+link(tw.license_url,'이용 조건')+'</p>';
}
function sectorRows(items){
 const groups=new Map();
 for(const c of items){
  const g=groups.get(c.sector)||{sector:c.sector,industryCode:c.foreign?.industryCode,count:0,priced:0,value:0,turnoverCount:0};
  g.count++;if(num(c.price))g.priced++;
  if(num(c.turnover)){g.value+=c.turnover;g.turnoverCount++}
  groups.set(c.sector,g);
 }
 return [...groups.values()].sort((a,b)=>b.count-a.count||a.sector.localeCompare(b.sector,'ko'));
}
function econ(country){
 const x=industry[country]; if(!x||!https(x.url)||!Array.isArray(x.rows))return '';
 const {esc:E,fmt,link}=window.RadarCohesive;
 return '<section class="rcm-card rc-region-industry-econ"><header><h2>공식 산업 지표</h2><span>'+E(x.basis)+'</span></header><div class="rc-region-econ-rows">'+x.rows.filter(row=>Array.isArray(row)&&txt(row[0])&&num(row[1])).map(([k,v])=>'<div><b>'+E(k)+'</b><strong>'+(v>0?'+':'')+fmt(v)+E(x.unit||'%')+'</strong></div>').join('')+'</div><small>'+E(x.period)+' 기준 · '+E(x.released)+' 발표 · '+link(x.url,x.agency)+' · '+E(x.note)+'</small></section>';
}
function homeIndustry(ctx){
 const {card,esc:E,fmt,empty}=window.RadarCohesive;
 const companies=ctx.companies, s=sectorRows(companies);
 const body=s.slice(0,6).map(g=>'<article class="rc-brief-row"><div class="rc-industry-line"><b>'+E(g.sector)+'</b><span>'+fmt(g.count,0)+'개</span></div><small>'+E(ctx.country==='TW'?'TWSE 명부 기준':'검증 표본 기준')+'</small></article>').join('');
 return card('산업 핵심','<small>'+E(summary(ctx.country,companies))+'</small><div class="rc-minilist rc-industry-list" tabindex="0" aria-label="선택 국가 업종별 기업 수">'+(body||empty('연결된 업종을 확인하지 못했습니다.'))+'</div><button type="button" data-rc-tab="market">산업 비교 ›</button>');
}
function renderMarket(ctx,overview){
 const H=window.RadarCohesive,{esc:E,fmt,link}=H,c=ctx.country,u=ui(c),companies=ctx.companies,twse=c==='TW';
 const groups=sectorRows(companies), visGroups=groups.filter(g=>matches(g.sector,u.query));
 if(u.sector&&!groups.some(g=>g.sector===u.sector))u.sector='';
 const pool=companies.filter(x=>!u.sector||x.sector===u.sector);
 const filtered=pool.filter(x=>matches(search(x),u.companyQuery));
 const favorites=companies.filter(x=>ctx.favorites.includes(H.id(x)));
 const tabRow=(label,stat,extras='')=>'<tr><th scope="row"><button type="button" data-rc-foreign-sector="'+E(label)+'" aria-pressed="'+(u.sector===label)+'">'+E(label)+'</button></th><td>'+fmt(stat,0)+'개</td>'+extras+'</tr>';
 const sectors=visGroups.map(g=>{
  const i=tw?.sector_prices?.[g.industryCode], v=i?.change_pct;
  const move=num(v)?'<span class="rc-foreign-move '+(v>0?'rc-compare-up':v<0?'rc-compare-down':'rc-compare-flat')+'">'+(v>0?'+':'')+fmt(v)+'%</span>':'—';
  return tabRow(g.sector,g.count,twse?'<td>'+move+'</td><td>'+fmt(g.priced,0)+'개</td><td>'+(g.turnoverCount?fmt(g.value/1e8)+'억 TWD':'—')+'</td>':'');
 }).join('');
 const tbody=sectors||'<tr><td colspan="'+(twse?5:2)+'">해당 업종이 없습니다.</td></tr>';
 const table='<section class="rcm-card rc-foreign-sector-panel"><header><h2>산업 비교</h2><span>'+E(twse?'거래소 분류 · '+(tw?.price_day||'미확인')+' 저장 종가':'확인 기업의 업종 분포 · 수익률·순위 아님')+'</span></header><div class="rcm-toolbar"><input data-rcm-search="sector" aria-label="산업 검색" placeholder="산업 검색" value="'+E(u.query)+'"><button data-rc-foreign-sector="" type="button" aria-pressed="'+(!u.sector)+'">전체 업종</button></div><div class="rcm-industry-scroll"><table><thead><tr><th>산업</th><th>'+(twse?'상장기업':'표본 기업')+'</th>'+(twse?'<th>공식 산업 지수 등락</th><th>종가 확인</th><th>거래대금 합계</th>':'')+'</tr></thead><tbody>'+tbody+'</tbody></table></div><p class="rcm-muted">'+E(twse?'등락은 TWSE 공식 산업별 가격지수의 발표값입니다. 거래대금은 별도로 확인 종목만 합산했습니다. 자동 갱신 아님.':'기업 수는 선별 표본의 구성입니다. 시장 전체 규모·주도산업·투자 매력도를 뜻하지 않습니다.')+'</p>'+sourceLine(c)+'</section>';
 const side='<section class="rcm-card rc-foreign-companies"><header><h2>기업 선택</h2><span>'+E(twse?'TWSE 명부':'공식 확인 표본')+'</span></header><input data-rcm-search="company" aria-label="기업명 종목 검색" placeholder="기업명·종목 검색" value="'+E(u.companyQuery)+'"><h3>관심종목</h3>'+(favorites.length?H.stockRows(favorites,{max:3,showPrice:false,ctx}):'<p class="rcm-muted">목록에서 별을 누르면 추가됩니다.</p>')+'<h3>'+E(u.sector||'전체 업종')+' <small>'+fmt(filtered.length,0)+'개</small></h3><div class="rcm-companies">'+H.stockRows(filtered,{max:u.limit,showPrice:twse,ctx})+'</div>'+(filtered.length>u.limit?'<button type="button" data-rc-foreign-more>다음 '+Math.min(70,filtered.length-u.limit)+'개 보기</button>':'')+'<p class="rcm-muted">'+E(summary(c,companies))+'</p></section>';
 return '<div class="rcm-layout rc-foreign-market"><div class="rcm-main"><div class="rcm-top">'+overview+'</div>'+table+(econ(c)||'')+'</div><aside>'+side+'</aside></div>';
}
function handle(e,ctx){
 const ctl=e.target?.closest?.('[data-rc-foreign-sector],[data-rcm-search],[data-rc-foreign-more]');
 if(!ctl)return false;
 const u=ui(ctx.country), d=ctl.dataset;
 if('rcmSearch' in d){
  if(e.type!=='input'&&e.type!=='change')return false;
  u[d.rcmSearch==='sector'?'query':'companyQuery']=ctl.value;u.limit=70;
 }else{
  if(e.type!=='click')return false;
  if('rcForeignMore' in d)u.limit+=70;
  else{u.sector=d.rcForeignSector;u.companyQuery='';u.limit=70;}
 }
 return true;
}
function companyNote(c,page){
 const {card,esc:E,link,fmt}=window.RadarCohesive,p=c.foreign;
 const absent=({finance:'재무제표·비율',value:'실적 전망·가치 평가',filings:'공시 수집·분석',chart:'차트·종가 이력'})[page];
 const quote=num(c.price)?'<p>저장 종가 <b>'+fmt(c.price)+' TWD</b> · '+E(c.price_session)+' · '+link(p.price_source_url,'TWSE 종가 원문')+'</p>':'<p>개별 시세 미연결</p>';
 return card('상장 기업 자료','<p><b>'+E(c.name)+'</b> · '+E(c.exchange)+' '+E(c.symbol)+' · '+E(c.sector)+'</p><p>'+E(p.basis)+' · '+E(p.verified)+' 확인 · '+link(p.source,'기업·명부 원문')+'</p>'+quote+(page==='quality'&&c.business_summary?'<p>'+E(c.business_summary)+'</p>':'')+(absent?'<p>'+E(absent)+'은 아직 연결되지 않았습니다.</p>':'<p>사업·실적 상세 자료는 명부와 별도입니다.</p>')+sourceLine(c.country),'mint');
}
window.RadarCohesiveForeign={reset:c=>states.delete(c),has,rows,search,summary,sourceLine,renderMarket,homeIndustry,companyNote,handle,load};
})();
