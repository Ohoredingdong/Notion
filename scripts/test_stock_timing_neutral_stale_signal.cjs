/* Synthetic fixed-clock test of the ACTUAL neutral operating-home script. No market data or orders. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('assets/stock-radar-neutral.js','utf8');
const marker = 'window.StockRadarV2Bridge={';
assert.ok(source.includes(marker),'neutral-production instrument anchor must be reviewed');
const instrumented = source.replace(marker, `window.__neutralTimingResearch={setData:v=>{data=v},setOnly:v=>{flowOnly=v},flowForecast,flowState,flowCompanies,flowRows,forecastOf,forecastLabel};\n${marker}`);
const now = Date.parse('2026-11-03T13:00:00Z');
class FixedDate extends Date { static now(){return now;} }
const win = {};
const doc = {readyState:'loading',addEventListener(){}};
const storage = {getItem(){return null;}};
vm.runInNewContext(instrumented,{window:win,document:doc,localStorage:storage,Date:FixedDate,console},{filename:'assets/stock-radar-neutral.js',timeout:2500});
const {setData,setOnly,flowForecast,flowState,flowCompanies,flowRows,forecastOf,forecastLabel}=win.__neutralTimingResearch;
const rec=(symbol,mode,end,direction='up',status='research_prediction')=>({
 symbol,market:'US',mode,status,direction:status==='research_prediction'?direction:null,
 probabilities:status==='research_prediction'?{down:direction==='down'?0.60:0.20,flat:0.20,up:direction==='up'?0.60:0.20}:null,
 issued_at:'2026-11-02T21:30:00Z',
 target:{start:'2026-11-03T12:30:00Z',...(end===null?{}:{end})}
});
const symbols=['AAPL','NVDA','MSFT','TSLA','AMD','GOOG'];
const dataset={
 raw:{companies:symbols.map(symbol=>({symbol,name:symbol,market:'US',currency:'USD',price:100,priority:{score:1}}))},
 direction:{records:[
  rec('AAPL','daily','2026-11-03T12:00:00Z','up'),
  rec('NVDA','daily','2026-11-03T14:00:00Z','up'),
  rec('MSFT','daily','2026-11-03T14:00:00Z','up','no_call'),
  rec('TSLA','daily',null,'up'),
  rec('AMD','daily','2026-11-03T14:00:00Z','down'),
  rec('GOOG','daily','2026-11-03T12:00:00Z','up'),
  rec('GOOG','intraday','2026-11-03T13:30:00Z','down')
 ]}
};
const snapshot=JSON.stringify(dataset);
setData(dataset);
const pick=filter=>{setOnly(filter);return Array.from(flowCompanies(),c=>c.symbol);};
const by=s=>dataset.raw.companies.find(c=>c.symbol===s);
assert.deepEqual(pick('all'),symbols,'history must remain inspectable without rewriting');
console.log('neutral 1/7: all records preserved');
assert.deepEqual(pick('ai'),['NVDA','AMD','GOOG'],'expired, unknown and no-call must be excluded from current AI filter');
console.log('neutral 2/7: AI current filter excludes invalid/expired/unknown');
assert.equal(flowForecast(by('GOOG')).mode,'intraday','live intraday must outrank expired daily');
assert.equal(flowForecast(by('GOOG')).direction,'down');
console.log('neutral 3/7: cross-mode live forecast precedence');
assert.equal(flowState(flowForecast(by('NVDA'))).current,true);
assert.equal(flowState(flowForecast(by('AAPL'))).expired,true);
assert.equal(flowState(flowForecast(by('TSLA'))).unknown,true);
console.log('neutral 4/7: current/expired/unknown explicitly separated');
pick('all');
const rows=flowRows();
const button=s=>rows.match(new RegExp('data-nr-select="'+s+'"[\\s\\S]*?<\\/button>'))?.[0]||'';
assert.match(button('AAPL'),/지난 예측/,'expired signal kept but labelled as historical');
assert.doesNotMatch(button('AAPL'),/상승 60/,'historical record cannot display an actionable UP chip');
assert.match(button('TSLA'),/시간 미확인/,'unknown-end signal must be explicitly marked');
assert.match(button('NVDA'),/상승 60/,'live UP signal is retained');
assert.match(button('AMD'),/하락 60/,'live DOWN signal is retained');
console.log('neutral 5/7: all-view pills distinguish live vs past/unknown');
assert.match(forecastLabel(forecastOf(by('AAPL'))).label,/지난 예측/);
assert.equal(forecastLabel(forecastOf(by('AAPL'))).prob,null);
assert.match(forecastLabel(forecastOf(by('TSLA'))).label,/시간 미확인/);
assert.equal(forecastOf(by('GOOG')).mode,'intraday');
assert.match(forecastLabel(forecastOf(by('GOOG'))).label,/하락/);
console.log('neutral 6/7: other neutral screens do not mislabel expired forecasts');
assert.equal(JSON.stringify(dataset),snapshot,'original records and probabilities cannot be edited');
console.log('neutral 7/7: all frozen synthetic inputs unchanged');
