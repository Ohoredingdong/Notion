'use strict';
/* Test actual news-card renderer without touching production CSS or browser storage. */
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('assets/stock-radar-flow-v2.js', 'utf8');
assert(source.includes('function fxV5StockNews(ctx,c)'));
const injected = source.replace(/\}\)\(\);\s*$/, 'globalThis.__testEventNews = fxV5StockNews;})();');
assert.notStrictEqual(injected, source);
const sandbox = {
  window: {}, URL, Date, console,
  document: {readyState:'loading', addEventListener(){}},
  localStorage:{getItem(){return null},setItem(){}}
};
vm.createContext(sandbox);
vm.runInContext(injected,sandbox);
assert.strictEqual(typeof sandbox.__testEventNews,'function');
const now = Date.now();
const tomorrow = new Date(now + 86400000).toISOString();
const event = {
  kind:'official_policy_schedule', id:'official-test', category:'rate',
  title:'공식 금리 발표', event_at: tomorrow, time_precision:'date_only',
  event_date: tomorrow.slice(0,10), source_url:'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'
};
const company = {symbol:'FSLR'};
const context = record => ({
  data:{
    eventOutlook:record,
    newsLink:{items:[],generated_at:new Date(now).toISOString()}
  }
});
const report = {
  version:'stock-event-outlook-v1',generated_at:new Date(now).toISOString(),
  research_only:true,automatic_orders:false,events:[event]
};
const positive = sandbox.__testEventNews(context(report),company);
assert(positive.includes('[예정]') && positive.includes('공식 금리 발표'));
assert(positive.includes('매수 신호 아님'));
const stale = {...report,generated_at:new Date(now-25*3600000).toISOString()};
assert(!sandbox.__testEventNews(context(stale),company).includes('[예정]'));
const unsafe = {...report,events:[{...event,source_url:'javascript:alert(1)'}]};
assert(!sandbox.__testEventNews(context(unsafe),company).includes('[예정]'));
const past = {...report,events:[{...event,time_precision:'minute',event_at:new Date(now-3600000).toISOString()}]};
assert(!sandbox.__testEventNews(context(past),company).includes('[예정]'));
console.log('EVENT_OUTLOOK_UI_TESTS_PASSED: future, stale, unsafe-url, already-reported guards');
