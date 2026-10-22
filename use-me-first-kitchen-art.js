/* Miniature food art generated from the user's reference; interface icons retain Han-kki Kitchen styling. */
(() => {
'use strict';
const safeClass=value=>String(value??'').split(/\s+/).filter(token=>/^[a-zA-Z0-9_-]+$/.test(token)).join(' ');
const paths = {
  fridge:'<rect x="5" y="2" width="14" height="20" rx="3"/><path d="M11 2v20M8 10v5M14 10v5"/>',
  snowflake:'<path d="M12 2v20M3.3 7l17.4 10M3.3 17 20.7 7M9 4l3 3 3-3M9 20l3-3 3 3M3.5 10l4-1-1-4M17.5 19l-1-4 4-1M3.5 14l4 1-1 4M17.5 5l-1 4 4 1"/>',
  recipes:'<path d="M6 8c-5-1-4-7 1-6 2-3 8-3 10 0 5-1 6 5 1 6v5H6Z"/><path d="M7 17h10M8 21h8"/>',
  diary:'<rect x="4" y="4" width="16" height="18" rx="3"/><path d="M8 2v5M16 2v5M4 10h16M8 14h2M14 14h2M8 18h2"/>',
  basket:'<path d="m3 9 3 12h12l3-12ZM8 9l4-7 4 7M9 13v4M15 13v4"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  arrow:'<path d="M4 12h15M13 5l7 7-7 7"/>',
  chevron:'<path d="m9 5 7 7-7 7"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  check:'<path d="m5 12 5 5L20 7"/>',
  leaf:'<path d="M20 3C5 1 0 14 8 18c6 4 13-3 12-15ZM4 22 16 9"/>',
  heart:'<path d="M12 21S1 14 2 7c1-6 8-6 10-1 2-5 9-5 10 1 1 7-10 14-10 14Z"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  settings:'<path d="m9 2-.6 3-3 1-2.6 2 2 3v3l-2 2 2 3 3-.2 2.5 1.5 1 2.7 3.5-.3.8-2.6 2.5-1.4 3 .2 1.7-3-2.1-2.2v-3l2-2.4-2-3-3 .3-2.7-1.4L14 2Z"/><circle cx="12" cy="12" r="3"/>',
  sparkles:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5ZM20 2v4M18 4h4"/>',
  shuffle:'<path d="M3 5h3c5 0 6 14 11 14h4M17 15l4 4-4 3M3 19h3c2 0 4-3 5-7M14 6c1-1 2-1 3-1h4M17 2l4 3-4 4"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v.5"/>',
  coin:'<circle cx="12" cy="12" r="9"/><path d="m6 8 3 9 3-7 3 7 3-9M5 12h14"/>',
  edit:'<path d="m4 16 12-12 4 4L8 20l-5 1ZM13 7l4 4"/>',
  trash:'<path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7"/>',
  download:'<path d="M12 3v12M7 10l5 5 5-5M4 15v6h16v-6"/>',
  upload:'<path d="M12 16V4M7 9l5-5 5 5M4 15v6h16v-6"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 1v2M12 21v2M1 12h2M21 12h2M4 4l2 2M18 18l2 2M4 20l2-2M18 6l2-2"/>',
  moon:'<path d="M20 15A9 9 0 0 1 9 3a9 9 0 1 0 11 12Z"/>',
  bowl:'<path d="M2 10h20c-1 7-4 10-10 10S3 17 2 10ZM8 20v2h8v-2M8 2c-3 2 3 3 0 5M15 2c-3 2 3 3 0 5"/>',
  bell:'<path d="M4 17h16l-2-3V8A6 6 0 0 0 6 8v6ZM9 21h6"/>',
  reset:'<path d="M3 10a9 9 0 1 1 2 8M3 3v7h7"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9 8a3 3 0 0 1 6 0c0 3-3 2-3 5M12 17h.01"/>',
};
function icon(name, cls='') {cls=safeClass(cls);return `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${(Object.prototype.hasOwnProperty.call(paths,name)?paths[name]:paths.leaf)}</svg>`;}
// One transparent atlas is cached once. Individual SVG viewports keep complete
// silhouettes (the generated sheet does not use perfectly uniform cell gutters).
const ATLAS = './assets/food-miniatures-v2.webp';
let miniatureSequence = 0;
const sprites = Object.freeze({
 egg:[10,53,229,174], milk:[256,19,138,204], tofu:[424,53,195,167],
 chicken:[624,64,220,157], onion:[852,64,192,162], scallion:[1054,26,192,205],
 carrot:[18,236,207,206], broccoli:[232,243,197,186], kimchi:[450,239,155,192],
 rice:[630,260,205,169], tomato:[849,257,198,173], mushroom:[1057,257,182,176],
 potato:[17,452,204,185], zucchini:[232,449,192,186], oil:[468,437,122,201],
 soy:[676,447,109,186], tuna:[853,479,182,151], garlic:[1065,469,176,170],
 salt:[57,657,119,168], cheese:[225,668,195,156], yogurt:[446,649,161,172],
 lettuce:[623,643,218,181], cucumber:[848,668,195,156], pepper:[1048,663,187,161],
 ingredient:[17,847,197,163], 'egg-rice':[218,848,205,171],
 'tofu-soup':[427,843,193,174], 'chicken-salad':[623,846,218,173],
 'zucchini-fritters':[839,859,208,156], 'egg-salad':[1047,848,198,169],
 'tofu-steak':[10,1053,213,155], 'mushroom-tofu':[223,1051,202,159],
 omelette:[427,1048,209,158], apple:[646,1048,189,164],
 banana:[844,1047,189,163], fish:[1037,1049,212,155]
});
const names = Object.freeze({
 '계란':'egg','달걀':'egg','우유':'milk','두부':'tofu','닭가슴살':'chicken','닭고기':'chicken',
 '양파':'onion','대파':'scallion','쪽파':'scallion','당근':'carrot','브로콜리':'broccoli','김치':'kimchi',
 '밥/즉석밥':'rice','밥':'rice','쌀':'rice','토마토':'tomato','방울토마토':'tomato','버섯':'mushroom',
 '표고버섯':'mushroom','양송이버섯':'mushroom','감자':'potato','애호박':'zucchini','식용유':'oil',
 '올리브유':'oil','참기름':'oil','간장':'soy','참치캔':'tuna','참치':'tuna','마늘':'garlic',
 '다진마늘':'garlic','소금':'salt','치즈':'cheese','요거트':'yogurt','그릭요거트':'yogurt',
 '상추':'lettuce','양상추':'lettuce','샐러드채소':'lettuce','시금치':'lettuce','깻잎':'lettuce',
 '오이':'cucumber','고추':'pepper','청양고추':'pepper','홍고추':'pepper','사과':'apple','바나나':'banana',
 '생선':'fish','흰살생선':'fish','대구':'fish','명태':'fish'
});
const dishes = Object.freeze({
 '계란 볶음밥':'egg-rice','두부 된장국':'tofu-soup','닭가슴살 샐러드':'chicken-salad',
 '애호박 계란전':'zucchini-fritters','요거트 계란 샐러드':'egg-salad','두부 스테이크':'tofu-steak',
 '버섯 두부볶음':'mushroom-tofu','토마토 치즈 오믈렛':'omelette'
});
const own = (value,key) => Object.prototype.hasOwnProperty.call(value,key);
function foodIdForName(name) {
 const key=window.UMFDomain?.canonical(name) || String(name??'').normalize('NFKC').trim();
 return own(names,key)?names[key]:'ingredient';
}
function miniature(name, cls) {
 const key=own(sprites,name)?name:'ingredient';
 const [x,y,width,height]=sprites[key], clip='umf-miniature-'+(++miniatureSequence);
 return `<svg class="${safeClass(cls)} miniature-art" viewBox="${sprites[key].join(' ')}" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false" data-miniature="${key}"><defs><clipPath id="${clip}"><rect x="${x}" y="${y}" width="${width}" height="${height}"/></clipPath></defs><image href="${ATLAS}" x="0" y="0" width="1254" height="1254" preserveAspectRatio="none" clip-path="url(#${clip})"/></svg>`;
}
function foodArt(name, cls='') { return miniature(name,'food-art '+safeClass(cls)); }
function dishArt(recipe, cls='') { return miniature(own(dishes,recipe?.id)?dishes[recipe.id]:'ingredient','dish-art '+safeClass(cls)); }

let seasoningSequence=0;
function seasoningArt(name, cls='') {
 const key=String(name??'').normalize('NFKC').trim();
 const textSafe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const short=textSafe(key.length>5?key.slice(0,5):key);
 const id='umf-season-'+(++seasoningSequence);
 const svg=(body)=>'<svg class="'+safeClass(cls)+' seasoning-art" viewBox="0 0 80 80" aria-hidden="true" focusable="false"><defs>'+
   '<filter id="'+id+'shadow" x="-40%" y="-40%" width="180%" height="200%"><feDropShadow dx="0" dy="4.2" stdDeviation="3" flood-color="#5f4d3b" flood-opacity=".22"/></filter>'+
   '<linearGradient id="'+id+'cream" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fffdf7"/><stop offset=".48" stop-color="#f2eadc"/><stop offset="1" stop-color="#d9cbb8"/></linearGradient>'+
   '<linearGradient id="'+id+'glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".88"/><stop offset=".2" stop-color="#fff" stop-opacity=".28"/><stop offset=".6" stop-color="#d4c4af" stop-opacity=".08"/><stop offset="1" stop-color="#604b38" stop-opacity=".2"/></linearGradient>'+
   '<linearGradient id="'+id+'metal" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6e675f"/><stop offset=".22" stop-color="#eee9e1"/><stop offset=".5" stop-color="#aaa198"/><stop offset=".8" stop-color="#f6f1e9"/><stop offset="1" stop-color="#655e57"/></linearGradient>'+
   '<radialGradient id="'+id+'shine" cx=".32" cy=".18" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset=".35" stop-color="#fff" stop-opacity=".15"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'+
   '</defs><ellipse cx="40" cy="69" rx="22" ry="5.5" fill="#6b563f" opacity=".12"/><g filter="url(#'+id+'shadow)">'+body+'</g></svg>';

 const sticker=(label,bg='#fff8ec',ink='#6d5a44',y=42,w=28)=>
   '<g><rect x="'+(40-w/2)+'" y="'+y+'" width="'+w+'" height="14" rx="5" fill="'+bg+'" opacity=".96"/>'+
   '<text x="40" y="'+(y+9.6)+'" text-anchor="middle" font-size="7.2" font-family="Apple SD Gothic Neo,Malgun Gothic,sans-serif" font-weight="700" fill="'+ink+'">'+label+'</text></g>';

 const cozyTub=(body='#e8dece',lid='#b8c1a0',accent='#9f6b3f',label=short)=>svg(
   '<path d="M19 28c0-5 4-8 9-8h24c5 0 9 3 9 8l-2.8 29c-.6 6-4.7 10-10.7 10h-15c-6 0-10.1-4-10.7-10Z" fill="url(#'+id+'cream)"/>'+
   '<ellipse cx="40" cy="28" rx="21" ry="7.5" fill="'+lid+'"/>'+
   '<ellipse cx="40" cy="27" rx="18" ry="5.3" fill="url(#'+id+'shine)" opacity=".7"/>'+
   '<path d="M24 36c7-3 25-3 32 0v12c-8 3-24 3-32 0Z" fill="'+accent+'" opacity=".88"/>'+
   '<path d="M24 36c7-3 25-3 32 0" stroke="#fff" stroke-opacity=".28" stroke-width="1.5" stroke-linecap="round"/>'+
   sticker(label)
 );

 const roundBottle=(liquid='#5a3824',cap='#6f7f62',label=short,labelInk='#6d5a44')=>svg(
   '<path d="M32 14h16v8c0 2 1.1 3.5 3.4 5.8 3 3 4.6 7 4.6 11v18c0 7-4.8 11-11.5 11h-9c-6.7 0-11.5-4-11.5-11V39c0-4 1.6-8 4.6-11 2.3-2.3 3.4-3.8 3.4-5.8Z" fill="'+liquid+'"/>'+
   '<rect x="31" y="9" width="18" height="9" rx="4" fill="'+cap+'"/>'+
   '<ellipse cx="40" cy="14" rx="7.5" ry="2.8" fill="#fff" opacity=".22"/>'+
   '<path d="M29 31c3.5-3 18.5-3 22 0" stroke="#fff" stroke-opacity=".35" stroke-width="1.8" stroke-linecap="round"/>'+
   '<path d="M29 36c-2 8-2 17-.7 24" stroke="#fff" stroke-opacity=".28" stroke-width="2.4" stroke-linecap="round"/>'+
   sticker(label,'#fff8ec',labelInk,43,26)
 );

 const oilBottle=(liquid='#bd7a25',cap='#84956d',label=short)=>svg(
   '<path d="M33 11h14v10c0 2.2 1.1 3.7 3 5.9 2.8 2.9 4.1 6.7 4.1 11v19.5c0 6.7-4.4 10.5-10.3 10.5h-7.6c-5.9 0-10.3-3.8-10.3-10.5V38c0-4.3 1.3-8.1 4.1-11 1.9-2.2 3-3.7 3-5.9Z" fill="'+liquid+'"/>'+
   '<rect x="32" y="8" width="16" height="7" rx="3" fill="'+cap+'"/>'+
   '<ellipse cx="40" cy="12" rx="7" ry="2.4" fill="#fff" opacity=".3"/>'+
   '<path d="M30 31c3-2.6 17-2.6 20 0" stroke="#fff" stroke-opacity=".4" stroke-width="1.6" stroke-linecap="round"/>'+
   '<path d="M30 36c-1.5 8-1.4 15-.7 21" stroke="#fff" stroke-opacity=".35" stroke-width="2.1" stroke-linecap="round"/>'+
   sticker(label,'#fff8ec','#6f5a3f',43,25)
 );

 const spiceJar=(powder='#f5f1e9',cap='#c9baa2',label=short,labelInk='#6f5d47')=>svg(
   '<rect x="23" y="22" width="34" height="42" rx="10" fill="url(#'+id+'glass)"/>'+
   '<rect x="26" y="38" width="28" height="20" rx="7" fill="'+powder+'" opacity=".95"/>'+
   '<rect x="21" y="15" width="38" height="12" rx="6" fill="'+cap+'"/>'+
   '<rect x="25" y="18" width="30" height="3" rx="1.5" fill="#fff" opacity=".24"/>'+
   '<path d="M27 30c5-2 21-2 26 0" stroke="#fff" stroke-opacity=".55" stroke-width="1.6" stroke-linecap="round"/>'+
   sticker(label,'#fff9ee',labelInk,43,26)
 );

 const squeeze=(fill='#d75743',cap='#eee1cc',label=short,labelInk='#6f5d47')=>svg(
   '<path d="M34 10h12l2 7-2 4v5c6 5 9 14 9 25 0 10-5.8 16-15 16s-15-6-15-16c0-11 3-20 9-25v-5l-2-4Z" fill="'+fill+'"/>'+
   '<rect x="32" y="9" width="16" height="10" rx="4" fill="'+cap+'"/>'+
   '<path d="M31 34c4-3 14-3 18 0" stroke="#fff" stroke-opacity=".35" stroke-width="1.8" stroke-linecap="round"/>'+
   sticker(label,'#fff9ef',labelInk,45,25)
 );

 if (/된장/.test(key)) return cozyTub('#eee4d5','#b8c5a0','#a16c3e',short);
 if (/쌈장/.test(key)) return cozyTub('#eee4d5','#94a779','#7f5238',short);
 if (/고추장/.test(key)) return cozyTub('#eee3d4','#c96855','#ad3f2f',short);
 if (/다진마늘|마늘/.test(key)) return cozyTub('#f0e7d9','#aebc92','#dfca93',short);
 if (/고춧가루/.test(key)) return spiceJar('#b93f2d','#c8b69a',short,'#9b3d31');
 if (/후추/.test(key)) return spiceJar('#4b443f','#2f2d2a',short,'#514942');
 if (/설탕/.test(key)) return spiceJar('#f3ede3','#d9c8ad',short);
 if (/소금/.test(key)) return spiceJar('#fcfbf4','#c9b99f',short,'#718082');
 if (/참기름/.test(key)) return oilBottle('#b16a20','#8a9a6e',short);
 if (/들기름/.test(key)) return oilBottle('#9c6d32','#70855f',short);
 if (/식용유|올리브유/.test(key)) return oilBottle('#c79b2f','#7c9367',short);
 if (/식초/.test(key)) return roundBottle('#d8b855','#d5c8b4',short);
 if (/액젓|참치액/.test(key)) return roundBottle('#9a5c2b','#77896c',short);
 if (/맛술/.test(key)) return roundBottle('#c68f51','#bba487',short);
 if (/굴소스/.test(key)) return roundBottle('#3f3027','#d4a248',short,'#6b4c34');
 if (/간장/.test(key)) return roundBottle('#3a2a24','#403a35',short,'#5e4b3c');
 if (/올리고당|물엿/.test(key)) return squeeze('#d5b65d','#efe5d2',short,'#8e7041');
 if (/케첩/.test(key)) return squeeze('#c94737','#f0e3d2',short,'#a44235');
 if (/마요네즈/.test(key)) return squeeze('#eee1bd','#d8b342',short,'#8d7853');
 return miniature(foodIdForName(key),'food-art '+safeClass(cls));
}
window.UMFKitchenArt=Object.freeze({icon,foodArt,dishArt,seasoningArt,foodIdForName,asset:ATLAS});
})();
