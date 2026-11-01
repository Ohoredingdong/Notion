const test=require('node:test');
const assert=require('node:assert/strict');
const P=require('../designs/miniature-kitchen/photo-reader.js');

test('OCR candidates keep product text, explicit quantity and expiry separate',()=>{
  const r=P.parseText('신선한 우유\n총 내용량 500 mL\n영양정보\n탄수화물 24g\n단백질 15g','소비기한 2026.11.30 까지');
  assert.deepEqual(r.nameCandidates,['신선한 우유']);assert.deepEqual(r.quantityCandidates,['500mL']);assert.deepEqual(r.expiryCandidates,['2026-11-30']);
  assert.equal(r.dateCandidates[0].label,'expiry');assert.match(r.text.product,/탄수화물 24g/);assert.match(r.warnings[0],/원본/);
});
test('manufacturing dates are not offered as expiry and multiple expiry candidates need review',()=>{
  const r=P.parseText('두부\n제조일 2026-10-01','제조일 2026-10-01\n소비기한 2026-11-02\nEXP 2026/11/03');
  assert.deepEqual(r.expiryCandidates,['2026-11-02','2026-11-03']);assert.equal(r.dateCandidates.filter(x=>x.label==='manufactured').length,1);assert.ok(r.warnings.some(x=>x.includes('여러 개')));
  const manufacturing=P.parseText('계란','제조일 2026-11-01');assert.deepEqual(manufacturing.expiryCandidates,[]);assert.ok(manufacturing.warnings.some(x=>x.includes('제조일')));
  const lineBreak=P.parseText('두부','제조일\n2026.11.01');assert.deepEqual(lineBreak.expiryCandidates,[]);assert.equal(lineBreak.dateCandidates[0].label,'manufactured');
});
test('date parsing validates real calendar dates and never silently repairs OCR characters',()=>{
  assert.deepEqual(P.parseDates('2026.02.29 2026.04.31 2026.13.01 2O26.11.O1'),[]);
  assert.equal(P.parseDates('소비기한 2028년 2월 29일')[0].date,'2028-02-29');
  assert.equal(P.parseDates('2026-11-01')[0].label,'unknown');
  assert.deepEqual(P.parseDates('LOT 20261101'),[]);assert.equal(P.parseDates('소비기한 20261101')[0].date,'2026-11-01');
});
test('short years remain an explicit reviewed interpretation and dates are not duplicated',()=>{
  const r=P.parseText('계란','소비기한 26.11.01\nEXP 2026.11.01');assert.deepEqual(r.expiryCandidates,['2026-11-01']);assert.ok(r.warnings.some(x=>x.includes('두 자리 연도')));
  assert.equal(P.parseDates('제조일 2026.10.01 소비기한 2026.11.01')[0].date,'2026-11-01');
});
test('quantity candidates exclude nutrition rows and retain only observed package values',()=>{
  assert.deepEqual(P.quantities('총 내용량 1,5 L\n나트륨 300mg\n당류 20g\n열량 200kcal'),['1.5L']);
  assert.deepEqual(P.quantities('계란 6개\n-100g\n0ml'),['6개']);
  assert.deepEqual(P.quantities('총 내용량 200g\n100g'),['200g','100g']);
  assert.deepEqual(P.names('신선한 우유\n종 내용량 500 mL'),['신선한 우유']);
});
test('parser treats untrusted strings as data and never invents missing names or dates',()=>{
  const r=P.parseText('', '읽기 어려운 날짜');assert.deepEqual(r.nameCandidates,[]);assert.deepEqual(r.expiryCandidates,[]);
  assert.equal(P.names('<script>alert(1)</script>')[0],'<script>alert(1)</script>');
  assert.equal(P.parseText('우유','').quantityCandidates.length,0);
});
test('recognition rejects external image URLs and incomplete photos before loading a worker',async()=>{
  await assert.rejects(P.read({product:'https://example.com/product.jpg',expiry:'data:image/png;base64,AAAA'}),/각각 선택/);
  await assert.rejects(P.read({product:'data:image/svg+xml;base64,AAAA',expiry:'data:image/png;base64,AAAA'}),/각각 선택/);
  await assert.rejects(P.read({product:'data:image/png;base64,AAAA'}),/각각 선택/);
  const c=new AbortController();c.abort();await assert.rejects(P.read({signal:c.signal}),{name:'AbortError'});
});
test('canceling active recognition terminates its worker without reading the second photo',async()=>{
  const previous=globalThis.Tesseract;let finish,calls=0,terminated=0;
  globalThis.Tesseract={createWorker:async()=>({setParameters:async()=>{},recognize:()=>{calls++;return new Promise(resolve=>finish=resolve);},terminate:async()=>{terminated++;}})};
  const controller=new AbortController(),data='data:image/png;base64,AAAA';
  try{
    const pending=P.read({product:data,expiry:data,signal:controller.signal});
    while(!finish)await new Promise(resolve=>setImmediate(resolve));
    await assert.rejects(P.read({product:data,expiry:data}),/읽는 중/);
    controller.abort();await assert.rejects(pending,{name:'AbortError'});
    finish({data:{text:'우유',confidence:90}});await new Promise(resolve=>setImmediate(resolve));
    assert.equal(calls,1);assert.ok(terminated>=1);
  }finally{if(previous===undefined)delete globalThis.Tesseract;else globalThis.Tesseract=previous;}
});
test('a worker finishing initialization after cancellation is still terminated',async()=>{
  const previous=globalThis.Tesseract;let initialized,terminated=0;
  globalThis.Tesseract={createWorker:()=>new Promise(resolve=>initialized=resolve)};
  const controller=new AbortController(),data='data:image/png;base64,AAAA';
  try{
    const pending=P.read({product:data,expiry:data,signal:controller.signal});
    while(!initialized)await new Promise(resolve=>setImmediate(resolve));
    controller.abort();await assert.rejects(pending,{name:'AbortError'});
    initialized({terminate:async()=>{terminated++;}});await new Promise(resolve=>setImmediate(resolve));
    assert.equal(terminated,1);
  }finally{if(previous===undefined)delete globalThis.Tesseract;else globalThis.Tesseract=previous;}
});
