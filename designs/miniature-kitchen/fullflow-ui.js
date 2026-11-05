/* Screen identifiers and shared presentation; never seeds or rewrites records. */
(() => {
 'use strict';
 const body=document.body,tray=document.getElementById('tray');
 const pageIds={recommendation:'B1',plans:'B4',nutrition:'C1',supplements:'C2',monthly:'C3',budget:'C4',growth:'D1',decor:'D5'};
 const routes={add:'A2',photos:'A3',photoReview:'A4',manualAdd:'A4',item:'A6',recipe:'B2',plan:'B3',logMeal:'B5',mealSuccess:'B6',nutrition:'C1',supplements:'C2',supplementDetail:'C2',monthly:'C3',budget:'C4',shopping:'C5',purchase:'C6',receipt:'C6',book:'D2',firstRecord:'D3',rewards:'D4'};
 function sync(){
  const home=body.dataset.home,fridge=document.getElementById('panel-fridge');
  const temporary=window.KitchenJournal?.status==='temporary'&&['plan','logMeal','purchase','mealSuccess'].includes(tray.dataset.workflowRoute);
  const title=document.getElementById('trayTitle');title.toggleAttribute('data-temporary',temporary);if(temporary)title.title='임시 미리보기예요. 새로고침 전 내 부엌의 설정·백업에서 기록을 내보내 주세요.';else title.removeAttribute('title');
  if(home==='fridge'&&fridge.dataset.screenId!=='D6')fridge.dataset.screenId=body.dataset.fridgeState==='saved'?'A5':'A1';
  let id=home==='fridge'?fridge.dataset.screenId:pageIds[body.dataset.homePage]||'';
  if(tray.open)id=tray.dataset.screenId||routes[tray.dataset.workflowRoute]||id;
  if(body.dataset.screenId!==id)body.dataset.screenId=id;
 }
 new MutationObserver(sync).observe(body,{attributes:true,attributeFilter:['data-home','data-home-page','data-fridge-state']});
 new MutationObserver(sync).observe(tray,{attributes:true,attributeFilter:['open','data-workflow-route','data-screen-id']});
 for(const name of ['mini-kitchen:change','mini-kitchen:layout'])window.addEventListener(name,sync);
 window.addEventListener('mini-kitchen:decor-applied',()=>{delete body.dataset.fridgeState;sync();});
 sync();
})();
