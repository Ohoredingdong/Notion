const a=require('../assets/stock-pattern-evidence.js'),assert=require('node:assert/strict');let c=0;function t(n,f){f();console.log('PASS '+n);c++}const now=Date.parse('2026-11-17T12:00:00Z');function data(){const bars=Array.from({length:80},(_,i)=>({date:new Date(Date.UTC(2026,7,1+i)).toISOString().slice(0,10),open:100,high:102,low:98,close:100,volume:100}));return{symbol:'TEST',bars,evidence:{symbol:'TEST',identity_verified:true,exchange_sessions_verified:true,adjustment_verified:true,corporate_actions_reviewed:true,use_rights_verified:true,source_url:'https://example.com/synthetic-test',price_basis:'split_adjusted',observed_at:'2026-11-17T11:59:00Z',expected_session:bars.at(-1).date}}}
t('valid synthetic contract',()=>assert.deepEqual(a.validate(data(),now),[]));
t('no OHLC cannot pass',()=>{let d=data();delete d.bars[0].high;assert.equal(a.analyze(d,now).status,'blocked')});
t('every unverified gate blocked',()=>{for(let k of ['identity_verified','exchange_sessions_verified','adjustment_verified','corporate_actions_reviewed','use_rights_verified']){let d=data();d.evidence[k]=false;assert.ok(a.validate(d,now).includes(k))}});
t('identity mismatch',()=>{let d=data();d.evidence.symbol='OTHER';assert.ok(a.validate(d,now).includes('symbol_mismatch'))});
t('bad high low',()=>{let d=data();d.bars[0].high=90;assert.ok(a.validate(d,now).includes('invalid_ohlcv'))});
t('negative volume',()=>{let d=data();d.bars[0].volume=-1;assert.ok(a.validate(d,now).includes('invalid_ohlcv'))});
t('unadjusted held',()=>{let d=data();d.evidence.price_basis='raw';assert.ok(a.validate(d,now).includes('price_basis_unverified'))});
t('stale held',()=>{let d=data();d.evidence.observed_at='2025-01-01';assert.ok(a.validate(d,now).includes('stale_observation'))});
t('future held',()=>{let d=data();d.evidence.observed_at='2027-01-01';assert.ok(a.validate(d,now).includes('stale_observation'))});
t('forming final pivots excluded',()=>{let d=data();d.bars.at(-2).low=80;assert.ok(!a.pivots(d.bars).some(p=>p.index===78))});
t('flat not imaginary pattern',()=>assert.equal(a.analyze(data(),now).patterns.length,0));
t('double bottom recognizable only after confirmation',()=>{let d=data();d.bars[20].low=90;d.bars[40].low=91;let r=a.analyze(d,now);assert.ok(r.patterns.some(x=>x.kind==='double_bottom'&&x.state==='forming'&&x.confirmed_at===43));assert.equal(r.orders_enabled,false);assert.equal(r.probability,null)});
t('breakout volume required',()=>{let d=data();d.bars[20].low=90;d.bars[40].low=91;Object.assign(d.bars[79],{close:105,high:106,volume:200});assert.ok(a.analyze(d,now).patterns.some(x=>x.kind==='double_bottom'&&x.state==='breakout_volume_confirmed'))});
t('reference lines do not authorize trade',()=>assert.equal(a.analyze(data(),now).orders_enabled,false));console.log(c+' passed');
t('symmetrical triangle evidence',()=>{let d=data();[[10,115],[30,113],[50,111]].forEach(([i,v])=>d.bars[i].high=v);[[20,85],[40,87],[60,89]].forEach(([i,v])=>d.bars[i].low=v);const r=a.analyze(d,now);assert.ok(r.patterns.some(x=>x.kind==='symmetrical_triangle'&&x.state==='forming'))});
