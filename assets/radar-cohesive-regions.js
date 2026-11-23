/* Research-only country links. Index snapshots and macro statistics have different
   sources and clocks; never substitute one for the other. */
(()=>{
'use strict';
const regions={
 JP:{name:'일본',index:'닛케이 225',key:'nikkei225',symbol:'^N225',official:'https://indexes.nikkei.co.jp/en/nkave',links:[['경제 통계 · 일본 통계청','https://www.stat.go.jp/english/data/'],['산업·거래 통계 · JPX','https://www.jpx.co.jp/english/markets/statistics-equities/'],['기업·공시 검색 · JPX','https://www.jpx.co.jp/english/listing/co-search/']]},
 CN:{name:'중국',index:'상하이 종합',key:'shanghai',symbol:'000001.SS',official:'https://www.sse.com.cn/market/sseindex/overview/',links:[['경제 통계 · 국가통계국','https://www.stats.gov.cn/english/'],['상하이 시장 통계 · SSE','https://english.sse.com.cn/news/publications/monthly/'],['상하이 기업 공시 · SSE','https://english.sse.com.cn/markets/dataservice/cpd/']]},
 HK:{name:'홍콩',index:'항셍 지수',key:'hang_seng',symbol:'^HSI',official:'https://www.hsi.com.hk/eng/indexes/all-indexes/index-details/?seriesCode=hsi',links:[['경제 통계 · C&SD','https://www.censtatd.gov.hk/en/'],['시장 통계 · HKEX','https://www.hkex.com.hk/Market-Data/Statistics?sc_lang=en'],['기업 공시 · HKEXnews','https://www.hkexnews.hk/']]},
 TW:{name:'대만',index:'대만 가권지수 (TAIEX)',official:'https://www.twse.com.tw/en/exchangeReport/FMTQIK?date=&response=html',links:[['경제 통계 · DGBAS','https://eng.stat.gov.tw/'],['시장·산업 자료 · TWSE','https://www.twse.com.tw/en/'],['기업 공시 · MOPS','https://mops.twse.com.tw/mops/']]},
 GB:{name:'영국',index:'FTSE 100',official:'https://www.londonstockexchange.com/en/indices/ftse-100',links:[['경제 통계 · ONS','https://www.ons.gov.uk/economy'],['시장 데이터 · LSE','https://www.londonstockexchange.com/en/market-data'],['상장종목 · LSE','https://www.londonstockexchange.com/en/market-data/equity'],['기업 공시 · LSE','https://www.londonstockexchange.com/news']]},
 DE:{name:'독일',index:'DAX',key:'dax',symbol:'^GDAXI',official:'https://stoxx.com/index/DAX/',links:[['경제 통계 · Destatis','https://www.destatis.de/EN/Home/_node.html'],['시장·업종 · Börse Frankfurt','https://www.boerse-frankfurt.de/equities'],['재무·공시 · Unternehmensregister','https://www.unternehmensregister.de/ureg/']]},
 VN:{name:'베트남',index:'VN-Index',official:'https://www.hsx.vn/',links:[['경제 통계 · NSO','https://nsdp.nso.gov.vn/index.htm'],['시장·산업 자료 · HOSE','https://www.hsx.vn/'],['상장·공시 원문 · HNX','https://www.hnx.vn/en-gb/']]},
 SG:{name:'싱가포르',index:'STI',official:'https://www.sgx.com/indices/products/sti',links:[['경제 통계 · SingStat','https://www.singstat.gov.sg/'],['시장·상장회사 · SGX','https://www.sgx.com/securities/equities'],['회사 공시 · SGX','https://www.sgx.com/securities/company-announcements']]}
};
const own=(obj,k)=>Object.hasOwn(obj,k);
const number=v=>typeof v==='number'&&Number.isFinite(v);
const day=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s).toISOString().startsWith(s);
function benchmark(country,data,now=Date.now()){
 if(!own(regions,country))return null;
 if(country==='TW'){
  const t=window.RadarCohesiveRegionSnapshots?.taiex;
  if(!day(t?.session)||!number(t?.value)||t.value<=0||Date.parse(t.session)>now||t.source_url!=='https://data.gov.tw/en/datasets/11672')return null;
  const verified=day(t.previous_session)&&t.previous_session<t.session&&number(t.previous_value)&&t.previous_value>0&&number(t.change_value)&&Math.abs(t.value-t.previous_value-t.change_value)<.001;
  return {...t,state:'공식 저장 종가 · 자동 갱신 미연결',verified,comparison:'직전 TWSE 거래일 '+(t.previous_session||'미확인')};
 }
 const spec=regions[country];
 if(!spec.key)return null;
 const i=data?.worldFlow?.indicators?.find(x=>x.id===spec.key);
 const s=i?.source;
 if(!day(i?.session)||Date.parse(i.session)>now||!number(i?.value)||i.value<=0||s?.identity_verified!==true||s.provider_symbol!==spec.symbol||s.response_symbol!==spec.symbol||i.quote_basis!=='exchange_regular_close'||!['current','stale'].includes(i.status))return null;
 const due=Date.parse(i.freshness?.next_check_after||'');
 const stale=i.status==='stale'||!Number.isFinite(due)||due<=now;
 const verified=i.comparison_verified===true&&i.comparison_basis==='previous_exchange_session'&&day(i.previous_session)&&i.previous_session<i.session&&number(i.previous_value)&&i.previous_value>0;
 return {value:i.value,session:i.session,expected_session:day(i.expected_session)&&i.expected_session>i.session?i.expected_session:null,previous_value:i.previous_value,verified,comparison:'직전 거래일 '+(i.previous_session||'미확인'),state:stale?'저장 종가 · 갱신 대기':'최근 확인 종가',source_url:s.url,source_name:s.provider};
}
function render(ctx){
 const c=ctx.country;if(!own(regions,c))return '';
 const spec=regions[c], b=benchmark(c,ctx.data),m=window.RadarCohesiveRegionSnapshots?.macro?.[c];
 const {esc:E,fmt,link,compare}=window.RadarCohesive;
 const entries=Array.isArray(ctx.companies)?ctx.companies:[];
 const count=entries.length, priced=entries.filter(x=>number(x.price)).length;
 const coverage=count?(fmt(count,0)+'종목 명부 · '+fmt(priced,0)+'종목 저장 시세 · 국가 전체 커버 아님'):'레이더 종목 명부·개별 시세·기업 분석 미연결';
 const reading=b?'<strong class="rc-region-value">'+fmt(b.value)+compare(b.value,b.previous_value,{verified:b.verified,label:b.comparison})+'</strong><small>'+E(b.session)+' 종가'+(b.expected_session?' · '+E(b.expected_session)+' 갱신 대기':'')+'</small>':'<strong class="rc-region-value">—</strong>';
 const source=(b?.source_url?link(b.source_url,b.source_name||'저장 수치 출처')+' · ':'')+link(spec.official,'지수 공식 원문');
 const macro=m&&number(m.value)&&m.period&&day(m.released)&&Date.parse(m.released)<=Date.now()?'<div class="rc-region-economy"><b>'+E(m.label)+'</b><strong>'+fmt(m.value)+E(m.unit)+compare(m.value,m.previous_value,{verified:number(m.previous_value)&&m.previous_period==='2026-09',label:m.previous_period+' 동일 CPI 전년동월비'})+'</strong><small>'+E(m.period)+' 기준 · '+E(m.released)+' 발표'+(m.updated?' · '+E(m.updated)+' 수정':'')+'</small><small>'+link(m.source_url,m.source_name)+(m.previous_source_url?' · '+link(m.previous_source_url,'비교 원문'):'')+(m.license_url?' · '+link(m.license_url,'이용 조건'):'')+'</small></div>':'';
 const attribution=b?.license_url?'<small class="rc-region-license">'+E(b.attribution)+' · '+link(b.license_url,'대만 정부 오픈데이터 v1.0')+'</small>':'';
 return '<section class="rc-card rc-region-overview" data-rc-region="'+c+'" aria-label="'+E(spec.name)+' 시장 개요"><header><h2>'+E(spec.name)+' 시장</h2><small class="rc-region-state">'+E(b?.state||'저장 지수 미연결')+'</small></header><div class="rc-region-details"><div class="rc-region-benchmark"><b>'+E(spec.index)+'</b>'+reading+'<small class="rc-region-source">'+source+'</small>'+attribution+'</div>'+macro+'<div class="rc-region-routes"><b>공식 원문 바로가기</b><div>'+spec.links.map(([name,url])=>link(url,name)).join('')+'</div></div></div><small class="rc-region-coverage">'+E(coverage)+' · 경제 수치는 발표 자료 스냅샷 · 원문 링크는 자동 수집이 아닙니다.</small></section>';
}
window.RadarCohesiveRegions={regions,benchmark,render,has:k=>own(regions,k)};
})();
