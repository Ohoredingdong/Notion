/* One host-sized widget frame; art and controls retain independent scales. */
(() => {
 'use strict';
 const shell=document.getElementById('kitchenWidget'),P=window.KitchenSceneProjection;
 const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
 function dimensions(width){
  const header=Math.max(88,width*194/720),nav=clamp(width*56/720,44,56);
  return {header,nav,art:(width-2)*P.world[1]/P.world[0],height:header+nav+(width-2)*P.world[1]/P.world[0]+2};
 }
 function fit(){
  const limitW=Math.max(1,Math.min(innerWidth,720)),limitH=Math.max(1,innerHeight);
  let width=limitW;if(dimensions(width).height>limitH){let low=1,high=width;for(let i=0;i<30;i++){const mid=(low+high)/2;if(dimensions(mid).height>limitH)high=mid;else low=mid;}width=low;}
  const d=dimensions(width),compact=width-2<560;
  document.body.dataset.refreshDensity=compact?'compact':'wide';
  const vars={'--refresh-side':width+'px','--refresh-frame-height':d.height+'px','--refresh-header':d.header+'px','--refresh-brand':(compact?44:clamp(width*52/720,44,52))+'px','--refresh-nav':d.nav+'px','--refresh-art':d.art+'px','--widget-side':width+'px','--widget-frame-width':width+'px','--widget-frame-height':d.height+'px','--workflow-frame-width':width+'px','--workflow-frame-height':d.height+'px','--home-ui-scale':'1','--hub-scale':'1'};
  // Dialogs are siblings of the shell, so both inherit the same fitted frame.
  for(const node of [document.body,shell])for(const [name,value]of Object.entries(vars))if(node.style.getPropertyValue(name)!==value)node.style.setProperty(name,value,'important');
  const rules={width:width+'px',height:d.height+'px',minHeight:'0px',maxHeight:d.height+'px',maxWidth:'100%',padding:'0 0 '+d.nav+'px',margin:'0 auto',display:'flex',flexDirection:'column',justifyContent:'flex-start',alignItems:'stretch'};
  for(const [name,value]of Object.entries(rules)){const css=name.replace(/[A-Z]/g,c=>'-'+c.toLowerCase());if(shell.style.getPropertyValue(css)!==value)shell.style.setProperty(css,value,'important');}
  const shelf=document.getElementById('homeSupplementsShelf'),parent=document.getElementById(compact?'refreshBrand':'homeOverview');
  if(shelf&&parent&&shelf.parentElement!==parent)parent.appendChild(shelf);
  return {width,...d,compact};
 }
 window.KitchenRefreshLayout=Object.freeze({fit,dimensions});fit();window.addEventListener('resize',fit);
})();
