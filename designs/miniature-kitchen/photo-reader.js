/* On-device text recognition only. Candidates never write to inventory. */
(function(root,factory){
  const api=factory(root);
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.KitchenPhotoReader=api;
})(typeof window!=='undefined'?window:globalThis,function(root){
  'use strict';
  const ENGINE='https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js';
  const INTEGRITY='sha384-GJqSu7vueQ9qN0E9yLPb3Wtpd7OrgK8KmYzC8T1IysG1bcvxvIO4qtYR/D3A991F';
  const WORKER='https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/worker.min.js';
  const CORE='https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.1';
  const LANG='https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/87416418657359cb625c412a48b6e1d6d41c29bd';
  const clean=value=>String(value??'').normalize('NFKC').replace(/\r\n?/g,'\n').slice(0,50000);
  const unique=rows=>[...new Set(rows)];
  const abortError=()=>Object.assign(new Error('사진 읽기를 취소했어요.'),{name:'AbortError'});
  let enginePromise=null,busy=false;

  function validDate(year,month,day){
    const y=Number(year),m=Number(month),d=Number(day);
    if(y<1900||y>2099||m<1||m>12||d<1||d>31)return null;
    const value=new Date(Date.UTC(y,m-1,d));
    return value.getUTCFullYear()===y&&value.getUTCMonth()===m-1&&value.getUTCDate()===d
      ?`${String(y).padStart(4,'0')}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`:null;
  }
  function dateLabel(line,start,end){
    const before=line.slice(Math.max(0,start-45),start),after=line.slice(end,end+12);
    const hints=[...before.matchAll(/소비\s*기한|유통\s*기한|사용\s*기한|품질\s*유지\s*기한|EXP(?:IRY)?|BEST\s*BEFORE|제조(?:\s*일자|\s*일)?|생산(?:\s*일자|\s*일)?|MFG|PROD/gi)];
    if(hints.length)return /제조|생산|MFG|PROD/i.test(hints.at(-1)[0])?'manufactured':'expiry';
    return /^\s*(?:까지|소비\s*기한|유통\s*기한|EXP)/i.test(after)?'expiry':'unknown';
  }
  function parseDates(text){
    const rows=[];let previousLine='';
    for(const line of clean(text).split('\n')){
      const prefix=previousLine.length<40&&!/\d/.test(previousLine)&&/소비\s*기한|유통\s*기한|사용\s*기한|제조|생산|MFG|EXP|BEST\s*BEFORE/i.test(previousLine)?previousLine+' ':'';
      const labelAt=(start,end)=>dateLabel(prefix+line,start+prefix.length,end+prefix.length);
      const occupied=[];
      const patterns=[
        {pattern:/(^|[^\d])((?:19|20)\d{2})\s*(?:[./-]|년)\s*(\d{1,2})\s*(?:[./-]|월)\s*(\d{1,2})(?:\s*일)?(?!\d)/g,short:false},
        {pattern:/(^|[^\d])([0-9]{2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{1,2})(?!\d)/g,short:true},
      ];
      for(const {pattern,short} of patterns)for(const match of line.matchAll(pattern)){
        const start=match.index+match[1].length,end=match.index+match[0].length;
        if(occupied.some(([a,b])=>start<b&&end>a))continue;
        const date=validDate(short?2000+Number(match[2]):match[2],match[3],match[4]);
        if(!date)continue;
        occupied.push([start,end]);
        rows.push({date,raw:line.slice(start,end).trim(),label:labelAt(start,end),shortYear:short});
      }
      // Unseparated eight-digit lot numbers are not dates without a nearby date label.
      for(const match of line.matchAll(/(^|[^\d])((?:19|20)\d{2})(\d{2})(\d{2})(?!\d)/g)){
        const start=match.index+match[1].length,end=match.index+match[0].length,label=labelAt(start,end);
        if(label==='unknown'||occupied.some(([a,b])=>start<b&&end>a))continue;
        const date=validDate(match[2],match[3],match[4]);
        if(date)rows.push({date,raw:line.slice(start,end),label,shortYear:false});
      }
      previousLine=line.trim();
    }
    const rank={expiry:0,unknown:1,manufactured:2},seen=new Set();
    return rows.sort((a,b)=>rank[a.label]-rank[b.label]).filter(row=>{const id=row.date+'|'+row.label;if(seen.has(id))return false;seen.add(id);return true;}).slice(0,20);
  }
  function quantities(text){
    const rows=[];
    for(const line of clean(text).split('\n')){
      const labeled=/내용\s*량|총\s*량|용\s*량|중\s*량|NET\s*(?:WT|WEIGHT|CONTENT)?/i.test(line);
      if(!labeled&&/영양|탄수화물|단백질|지방|나트륨|당류|칼슘|콜레스테롤|식이섬유|열량|칼로리|1회\s*제공|기준치/i.test(line))continue;
      for(const match of line.matchAll(/(^|[^\d.,-])(\d+(?:[.,]\d+)?)\s*(kg|mg|g|mL|ml|L|리터|밀리리터|킬로그램|그램|개|팩|병|봉|모)(?![a-zA-Z가-힣])/gi)){
        const value=Number(match[2].replace(',','.'));if(!Number.isFinite(value)||value<=0||value>1e6)continue;
        const units={kg:'kg',mg:'mg',g:'g',ml:'mL',l:'L','리터':'L','밀리리터':'mL','킬로그램':'kg','그램':'g'};
        rows.push({quantity:match[2].replace(',','.')+(units[match[3].toLowerCase()]||match[3]),labeled});
      }
    }
    return unique(rows.sort((a,b)=>Number(b.labeled)-Number(a.labeled)).map(r=>r.quantity)).slice(0,8);
  }
  function names(text){
    return unique(clean(text).split('\n').map(s=>s.replace(/\s+/g,' ').trim()).filter(s=>{
      if(s.length<2||s.length>80||!/[가-힣a-zA-Z]/.test(s))return false;
      if(parseDates(s).length||/소비\s*기한|유통\s*기한|제조\s*일|생산\s*일|영양\s*정보|영양\s*성분|탄수화물|단백질|나트륨|콜레스테롤|원재료|알레르기|고객\s*상담|품목\s*보고|보관\s*방법|기준치|www\.|https?:|바코드|소비자|전화|제조원/i.test(s))return false;
      if(/^[\d\s.,%()/-]*(?:kg|mg|g|ml|l|개|팩|병|봉|모)[\d\s.,%()/-]*$/i.test(s)||/내용\s*량|중량|용량|NET\b/i.test(s))return false;
      return true;
    })).slice(0,6);
  }
  function parseText(productText,expiryText){
    const product=clean(productText),expiry=clean(expiryText),dateCandidates=parseDates(expiry+'\n'+product);
    const nameCandidates=names(product),quantityCandidates=quantities(product),expiryCandidates=unique(dateCandidates.filter(r=>r.label!=='manufactured').map(r=>r.date));
    const warnings=['읽은 내용은 후보예요. 제품 이름·수량·기한 종류를 원본 사진과 비교한 뒤 확인해 주세요.'];
    if(!nameCandidates.length)warnings.push('제품 이름을 읽지 못했어요. 직접 입력해 주세요.');
    if(!expiryCandidates.length)warnings.push('소비·유통기한 후보를 찾지 못했어요. 제조일만 읽혔는지도 확인해 주세요.');
    if(expiryCandidates.length>1)warnings.push('날짜가 여러 개 읽혔어요. 실제 기한을 직접 골라 주세요.');
    if(dateCandidates.some(r=>r.label==='manufactured'))warnings.push('제조일 후보는 기한으로 자동 선택하지 않아요.');
    if(dateCandidates.some(r=>r.shortYear))warnings.push('두 자리 연도는 20xx년 후보로 표시했어요. 연도를 확인해 주세요.');
    return {nameCandidates,quantityCandidates,expiryCandidates,dateCandidates,text:{product,expiry},warnings};
  }
  function sourceAllowed(source){
    return typeof source==='string'?source.length<=28*1024*1024&&/^data:image\/(?:jpeg|jpg|png|webp|bmp);base64,[A-Za-z0-9+/=]+$/.test(source)
      :typeof root.Blob==='function'&&source instanceof root.Blob&&/^image\/(?:jpeg|jpg|png|webp|bmp)$/i.test(source.type)&&source.size>0&&source.size<=20*1024*1024;
  }
  function loadEngine(){
    if(root.Tesseract?.createWorker)return Promise.resolve(root.Tesseract);
    if(enginePromise)return enginePromise;
    enginePromise=new Promise((resolve,reject)=>{
      if(!root.document){reject(new Error('사진 읽기는 브라우저에서 사용할 수 있어요.'));return;}
      const script=root.document.createElement('script');let timer;
      const fail=()=>{clearTimeout(timer);script.remove();reject(new Error('사진 읽기 도구를 불러오지 못했어요. 인터넷 연결을 확인하거나 직접 입력해 주세요.'));};
      script.src=ENGINE;script.integrity=INTEGRITY;script.crossOrigin='anonymous';script.async=true;
      script.onload=()=>{clearTimeout(timer);root.Tesseract?.createWorker?resolve(root.Tesseract):fail();};script.onerror=fail;
      timer=setTimeout(fail,30000);root.document.head.appendChild(script);
    }).catch(error=>{enginePromise=null;throw error;});
    return enginePromise;
  }
  async function read({product,expiry,onProgress,signal}={}){
    if(signal?.aborted)throw abortError();
    if(!sourceAllowed(product)||!sourceAllowed(expiry))throw new Error('제품 사진과 기한 사진을 각각 선택해 주세요. JPEG·PNG·WebP 사진을 사용할 수 있어요.');
    if(busy)throw new Error('앞의 사진을 읽는 중이에요. 완료하거나 취소한 뒤 다시 시도해 주세요.');
    busy=true;let worker,closed=false,timer,abortListener,phase='loading';
    const emit=(progress,message)=>{if(closed)return;try{onProgress?.({stage:phase,progress:Math.max(0,Math.min(1,Number(progress)||0)),message});}catch(_){}};
    const stop=()=>{closed=true;if(worker){try{Promise.resolve(worker.terminate()).catch(()=>{});}catch(_){}}};
    const canceled=new Promise((_,reject)=>{abortListener=()=>{stop();reject(abortError());};signal?.addEventListener('abort',abortListener,{once:true});});
    const timeout=new Promise((_,reject)=>{timer=setTimeout(()=>{stop();reject(new Error('사진 읽기 시간이 길어 중단했어요. 더 선명한 사진으로 다시 시도하거나 직접 입력해 주세요.'));},120000);});
    const work=(async()=>{
      emit(0,'기기 안에서 사진을 읽을 도구를 준비해요. 처음에는 다운로드가 필요해요.');
      const engine=await loadEngine();if(closed||signal?.aborted)throw abortError();
      const initialized=await engine.createWorker(['kor','eng'],1,{workerPath:WORKER,corePath:CORE,langPath:LANG,gzip:false,cacheMethod:'none',workerBlobURL:true,logger:message=>emit(message.progress,phase==='product'?'제품 사진의 글자를 읽고 있어요.':phase==='expiry'?'기한 사진의 글자를 읽고 있어요.':'한국어·영어 읽기 도구를 준비하고 있어요.')});
      worker=initialized;if(closed||signal?.aborted){stop();throw abortError();}
      await worker.setParameters({preserve_interword_spaces:'1'});
      phase='product';emit(0,'제품 사진의 글자를 읽고 있어요.');const a=await worker.recognize(product);
      if(closed||signal?.aborted)throw abortError();
      phase='expiry';emit(0,'기한 사진의 글자를 읽고 있어요.');const b=await worker.recognize(expiry);
      if(closed||signal?.aborted)throw abortError();
      const result=parseText(a.data?.text,b.data?.text);result.confidence={product:a.data?.confidence??null,expiry:b.data?.confidence??null};
      if(Object.values(result.confidence).some(v=>v!==null&&v<60))result.warnings.push('일부 글자가 흐리게 읽혔어요. 원문을 특히 주의해서 확인해 주세요.');
      emit(1,'읽은 후보를 원본과 비교해 주세요. 확인 전에는 재료를 저장하지 않아요.');return result;
    })();
    try{return await Promise.race([work,canceled,timeout]);}
    catch(error){if(error?.name==='AbortError')throw error;throw new Error(error?.message||'사진의 글자를 읽지 못했어요. 다시 촬영하거나 직접 입력해 주세요.');}
    finally{clearTimeout(timer);signal?.removeEventListener('abort',abortListener);stop();busy=false;}
  }
  return Object.freeze({read,parseText,parseDates,quantities,names});
});
