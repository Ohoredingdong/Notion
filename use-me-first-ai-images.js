(()=>{
  const FOOD_IMAGES={
    '두부김치':'assets/use-me-first/dubu-kimchi.webp',
    '김치볶음밥':'assets/use-me-first/kimchi-fried-rice.webp',
    '두부 김치덮밥':'assets/use-me-first/dubu-kimchi-rice.webp',
    '닭가슴살 양파 간장볶음':'assets/use-me-first/chicken-onion-soy-stirfry.webp'
  };
  const nameEl=document.getElementById('rn');
  const img=document.getElementById('img');
  const fallback=document.getElementById('fb');
  const source=document.getElementById('src');
  if(nameEl&&img){
    function applyFoodImage(){
      const name=(nameEl.textContent||'').trim();
      const src=FOOD_IMAGES[name];
      if(!src)return;
      img.onerror=()=>{img.style.display='none';fallback?.classList.add('on');};
      img.onload=()=>{img.style.display='block';fallback?.classList.remove('on');if(source)source.textContent='AI 생성 이미지';};
      img.src=src;
    }
    new MutationObserver(()=>requestAnimationFrame(applyFoodImage)).observe(nameEl,{childList:true,subtree:true,characterData:true});
    document.getElementById('next')?.addEventListener('click',()=>setTimeout(applyFoodImage,0));
    setTimeout(applyFoodImage,60);
  }
  if(!document.querySelector('link[href*="use-me-first-horizontal.css"]')){
    const link=document.createElement('link');link.rel='stylesheet';link.href='use-me-first-horizontal.css?v=1';document.head.appendChild(link);
  }
  if(!document.querySelector('script[src*="use-me-first-horizontal.js"]')){
    const s=document.createElement('script');s.src='use-me-first-horizontal.js?v=1';s.defer=false;document.body.appendChild(s);
  }
})();