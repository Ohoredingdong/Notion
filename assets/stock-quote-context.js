/* Saved research closes are not live quotes. Provider widgets never feed our model. */
(function(root){
 'use strict';
 const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const upper=v=>String(v??'').trim().toUpperCase();
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 function session(c,now=Date.now()){
  const value=String(c?.price_session||''),country=upper(c?.country||c?.market);
  const valid=/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
  const today=new Date(now).toLocaleDateString('sv-SE',{timeZone:country==='KR'?'Asia/Seoul':'America/New_York'});
  return valid&&value<=today?value:null;
 }
 function providerSymbol(c){
  // No guessed exchange, fuzzy company matching or share-class conversion.
  const country=upper(c?.country||c?.market),symbol=upper(c?.symbol).replace(/\.(KS|KQ)$/,'');
  const proof=c?.price_source,meta=proof?.source_metadata||{};
  if(proof?.source_identity_verified!==true)return null;
  const source=upper(proof.provider_symbol||meta.symbol);
  if((proof.market&&upper(proof.market)!==country)||(proof.currency&&proof.currency!==c.currency)||(meta.symbol&&upper(meta.symbol)!==source))return null;
  if(!source||source!==upper(c?.source_symbol||c?.symbol))return null;
  if(country==='US'&&c.currency==='USD'&&/^[A-Z]{1,6}$/.test(symbol)){
   const exchange=upper(meta.exchangeName||c?.catalog_entry?.exchange||c?.exchange);
   if(['NMS','NGM','NCM','NASDAQ','NASDAQGS','NASDAQGM','NASDAQCM'].includes(exchange))return 'NASDAQ:'+symbol;
   if(['NYQ','NYSE'].includes(exchange))return 'NYSE:'+symbol;
  }
  if(country==='KR'&&c.currency==='KRW'&&/^[0-9A-Z]{6}$/.test(symbol)){
   const exchange=upper(meta.exchangeName||c?.catalog_entry?.exchange||c?.exchange);
   if(['KSC','KOE','KOSPI','KOSDAQ'].includes(exchange)&&/\.(KS|KQ)$/.test(source))return 'KRX:'+symbol;
  }
  return null;
 }
 function render(c,now=Date.now()){
  const date=session(c,now),id=String(c?.selection_id||c?.universe_key||c?.symbol||'');
  const label=date?date+' 정규장 종가':'저장 가격 · 기준일 미확인';
  const known=providerSymbol(c);
  return '<span class="radar-quote-context" data-quote-context><small data-quote-session title="분석에 사용하는 저장 종가입니다. 표시된 등락률도 해당 정규장 기준이며 지금 거래 중인 가격이 아닙니다.">'+escape(label)+'</small><button type="button" data-quote-view="'+escape(id)+'" title="저장 종가와 분리된 외부 시세 창 · 제공처 지연 가능">'+(known?'외부 시세':'시세 연결 안내')+' ↗</button></span>';
 }
 const api={session,providerSymbol,render};
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.StockQuoteContext=api;
 if(!root.document)return;
 const doc=root.document;
 let dialog=null,opener=null,timer=null,observer=null;
 function close(){
  clearTimeout(timer);observer?.disconnect();observer=null;
  if(dialog){const current=dialog;dialog=null;if(current.open)current.close();current.remove();}
  if(opener?.isConnected)opener.focus();opener=null;
 }
 function resolve(id){
  const ctx=root.StockRadarV2Bridge?.snapshot?.();
  if(!ctx)return null;
  return root.StockCatalogUI?.resolve?.(id,ctx)||(ctx.data?.raw?.companies||[]).find(c=>String(c.symbol)===id)||null;
 }
 function open(c,button){
  close();opener=button;
  const symbol=providerSymbol(c),label=c?.name||c?.symbol||'선택 종목';
  dialog=doc.createElement('dialog');dialog.className='radar-quote-dialog';dialog.setAttribute('aria-labelledby','radar-quote-dialog-title');
  const sourceHref=symbol?'https://www.tradingview.com/symbols/'+symbol.replace(':','-')+'/':null;
  dialog.innerHTML='<div class="radar-quote-dialog-head"><div><h2 id="radar-quote-dialog-title">'+escape(label)+' · 외부 시세</h2><p>자동 갱신은 제공처 기준 · 지연 가능</p></div><button type="button" data-quote-close aria-label="시세 창 닫기">닫기</button></div><div class="radar-quote-dialog-body"><p class="radar-quote-notice">레이더의 저장 종가·AI 분석과 분리된 화면입니다. 거래 시각과 장 구분은 제공처에서 확인하세요. 야간거래 지원이나 실시간 체결가는 보장하지 않습니다.</p><div class="radar-quote-provider-host"></div><p class="radar-quote-load-status" role="status">'+(symbol?'외부 시세 화면 불러오는 중…':'거래소·종목 연결을 확인할 수 없어 시세를 요청하지 않았습니다.')+'</p>'+(sourceHref?'<a class="radar-quote-source-link" href="'+escape(sourceHref)+'" target="_blank" rel="noopener noreferrer">제공처 원본에서 시각·장 구분 확인 ↗</a>':'')+'<p class="radar-quote-footnote">증권사 주문 화면의 가격과 다를 수 있습니다. 이 창의 값은 레이더 계산이나 예측 원장에 저장하지 않습니다.</p></div>';
  doc.body.append(dialog);
  dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
  dialog.addEventListener('click',event=>{if(event.target===dialog||event.target.closest('[data-quote-close]'))close();});
  dialog.showModal();
if(symbol&&/^(NASDAQ|NYSE):[A-Z]{1,6}$/.test(symbol)){
 const alternate=doc.createElement('a');alternate.className='radar-quote-alt-source';
 alternate.href='https://finance.yahoo.com/quote/'+encodeURIComponent(symbol.split(':')[1])+'/';
 alternate.target='_blank';alternate.rel='noopener noreferrer';alternate.textContent='Yahoo 시세·시간외 원본 ↗';
 dialog.querySelector('.radar-quote-footnote').before(alternate);
}
if(!symbol)return;
  const active=dialog,host=active.querySelector('.radar-quote-provider-host'),status=active.querySelector('.radar-quote-load-status');
  const override=new URLSearchParams(root.location.search).get('tvwidgetsymbol');
if(override&&upper(override)!==symbol){status.textContent='URL의 외부 종목 설정이 달라 시세 로드를 중단했습니다. 위 종목의 제공처 원본을 이용하세요.';return;}
  const container=doc.createElement('div');container.className='tradingview-widget-container';
  const widget=doc.createElement('div');widget.className='tradingview-widget-container__widget';container.append(widget);
  // Preserve mandatory TradingView attribution. Do not scrape/export its frame.
  const attribution=doc.createElement('div');attribution.className='tradingview-widget-copyright';
  const link=doc.createElement('a');link.href=sourceHref;link.target='_blank';link.rel='noopener nofollow';link.textContent='Track all markets on TradingView';attribution.append(link);container.append(attribution);host.append(container);
  const script=doc.createElement('script');script.type='text/javascript';script.async=true;
  script.src='https://s3.tradingview.com/external-embedding/embed-widget-symbol-info.js';
  script.textContent=JSON.stringify({symbol,width:'100%',locale:'kr',colorTheme:'light',isTransparent:false});
  script.onerror=()=>{if(dialog===active)status.textContent='외부 시세를 불러오지 못했습니다. 제공처 원본에서 확인하세요.';};
  observer=new MutationObserver(()=>{
   const frame=host.querySelector('iframe');
   if(!frame||dialog!==active)return;
   frame.title=label+' 제공처 시세 · 지연 가능';
   status.textContent='제공처 화면입니다. 데이터 제공 여부·거래 시각·지연 표시는 아래 원본에서도 확인할 수 있습니다.';
   clearTimeout(timer);observer.disconnect();observer=null;
  });
  observer.observe(host,{childList:true,subtree:true});
  timer=setTimeout(()=>{if(dialog===active)status.textContent='외부 시세 응답이 늦거나 차단됐을 수 있습니다. 제공처 원본에서 확인하세요.';},12000);
  container.append(script);
 }
 doc.addEventListener('click',event=>{
  const button=event.target.closest?.('[data-quote-view]');if(!button)return;
  const c=resolve(button.dataset.quoteView);if(c)open(c,button);
 });
 api.close=close;
})(typeof window==='object'?window:globalThis);
