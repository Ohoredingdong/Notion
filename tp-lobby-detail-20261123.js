/* Collection card details: retain existing filters, game start logic and browser records. */
(()=>{
 if(typeof showHome!=='function'||typeof tpMovePage!=='function')return;
 const oldShowHome=showHome;
 showHome=function(...args){
   const result=oldShowHome.apply(this,args);
   const root=document.querySelector('.tp-home');if(!root)return result;
   [...root.querySelectorAll('.tp-gallery .tp-game')].forEach((card,index)=>{
      const number=String(tpPage*4+index+1).padStart(2,'0');
      const tag=document.createElement('span');tag.className='tp-card-identity';
      tag.setAttribute('aria-hidden','true');
      tag.innerHTML='<span class="tp-card-index">NO. '+number+'</span>';
      card.appendChild(tag);
      const play=card.querySelector('.tp-play-icon');
      if(play){play.innerHTML='시작 <svg viewBox="0 0 18 18" aria-hidden="true"><path d="M3.5 9h10m-4-4 4 4-4 4"/></svg>';play.setAttribute('aria-hidden','true')}
   });
   const deck=root.querySelector('.tp-deck-nav');
   if(deck){
      const [back,label,forward]=deck.children;
      if(back&&label&&forward){
        const pages=Math.max(1,Math.ceil(tpGames().length/4));
        back.textContent='←';forward.textContent='→';
        label.className='tp-page-current';
        label.innerHTML=String(tpPage+1).padStart(2,'0')+' <em>/</em> '+String(pages).padStart(2,'0');
        const pips=document.createElement('span');
        pips.className='tp-page-pips';pips.setAttribute('aria-hidden','true');
        for(let i=0;i<pages;i++){const dot=document.createElement('i');if(i===tpPage)dot.className='is-current';pips.appendChild(dot);}
        deck.insertBefore(pips,forward);
      }
   }
   return result;
 };
 showHome();
})();