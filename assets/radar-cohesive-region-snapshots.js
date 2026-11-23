/* Dated, attributed research snapshots, not a real-time feed. Taiwan stock
   index facts come only from the FMTQIK public-data resource listed in dataset 11672. */
(()=>{
'use strict';
const cpi=(value,previous_value,released,source_name,source_url,license_url,previous_source_url='',updated='')=>({label:'소비자물가 · 전년동월비',unit:'%',period:'2026-10',previous_period:'2026-09',value,previous_value,released,source_name,source_url,license_url,previous_source_url,updated});
window.RadarCohesiveRegionSnapshots={
 taiex:{
  value:36811.89,previous_value:36033.29,change_value:778.60,
  session:'2026-11-23',previous_session:'2026-11-20',
  source_name:'TWSE 공개 데이터',source_url:'https://data.gov.tw/en/datasets/11672',
  dataset_url:'https://www.twse.com.tw/exchangeReport/FMTQIK?response=open_data',
  license_url:'https://data.gov.tw/license',
  attribution:'대만 금융감독위원회 증권선물국 / TWSE (2026), Daily market transaction information (11672) · Open Government Data License v1.0 적용'
 },
 macro:{
  JP:cpi(2.3,2.1,'2026-11-20','일본 통계청','https://www.e-stat.go.jp/stat-search/files?layout=datalist&lid=000001494870','https://www.stat.go.jp/english/info/riyou.htm'),
  CN:cpi(.7,.9,'2026-11-09','중국 국가통계국','https://www.stats.gov.cn/sj/zxfb/202611/t20261109_1965795.html','','https://www.stats.gov.cn/english/PressRelease/202610/t20261015_1965500.html'),
  HK:cpi(2.2,1.9,'2026-11-20','홍콩 C&SD','https://www.info.gov.hk/gia/general/202611/20/P2026112000312.htm','https://www.censtatd.gov.hk/en./page_31.html'),
  TW:cpi(2.33,2.73,'2026-11-05','대만 DGBAS','https://eng.dgbas.gov.tw/News_Content.aspx?n=4438&s=236838','https://eng.stat.gov.tw/cp.aspx?n=2313','https://www.dgbas.gov.tw/News_Content.aspx?n=3602&s=236759'),
  GB:cpi(3.6,3.5,'2026-11-18','영국 ONS','https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/consumerpriceinflation/october2026','https://www.ons.gov.uk/help/terms-conditions'),
  DE:cpi(2.8,3.3,'2026-11-11','독일 Destatis','https://www.destatis.de/EN/Press/2026/11/PE26_392_611.html','https://www.destatis.de/EN/Service/OpenData/opendata-einleitung.html','','2026-11-17'),
  VN:cpi(5.09,5.08,'2026-11-03','베트남 NSO','https://www.nso.gov.vn/en/data-and-statistics/2026/11/consumer-price-index-cpi-gold-price-index-and-us-dollar-price-index-in-october-and-ten-months-of-2026/','','https://www.nso.gov.vn/en/data-and-statistics/2026/11/press-release-socio-economic-performance-in-the-q3-and-the-nine-months-of-2026/'),
  SG:cpi(1.9,2.2,'2026-11-23','싱가포르 통계청','https://www.singstat.gov.sg/news/singapore-consumer-price-index-oct2026','')
 }
};
})();
