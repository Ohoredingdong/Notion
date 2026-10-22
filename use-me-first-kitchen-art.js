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
 const key=String(name??'').normalize('NFKC').trim(), id='umf-season-'+(++seasoningSequence);
 const svg=(body)=>'<svg class="'+safeClass(cls)+' seasoning-art" viewBox="0 0 72 72" aria-hidden="true" focusable="false"><defs>'+
   '<filter id="'+id+'s" x="-35%" y="-35%" width="170%" height="190%"><feDropShadow dx="0" dy="3.2" stdDeviation="2.1" flood-color="#594732" flood-opacity=".25"/></filter>'+
   '<linearGradient id="'+id+'glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".84"/><stop offset=".22" stop-color="#fff" stop-opacity=".22"/><stop offset=".58" stop-color="#d7c7b2" stop-opacity=".08"/><stop offset="1" stop-color="#5f4a36" stop-opacity=".20"/></linearGradient>'+
   '<linearGradient id="'+id+'cream" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fffdf7"/><stop offset=".58" stop-color="#f2eadc"/><stop offset="1" stop-color="#d8cbb8"/></linearGradient>'+
   '<linearGradient id="'+id+'metal" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#756b60"/><stop offset=".2" stop-color="#e9e4dc"/><stop offset=".5" stop-color="#a79d92"/><stop offset=".8" stop-color="#eee9e0"/><stop offset="1" stop-color="#6d655c"/></linearGradient>'+
   '<linearGradient id="'+id+'pot" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f8eee0"/><stop offset=".45" stop-color="#c79b72"/><stop offset="1" stop-color="#8e6748"/></linearGradient>'+
   '</defs><ellipse cx="36" cy="63" rx="19" ry="4.5" fill="#6d5840" opacity=".14"/><g filter="url(#'+id+'s)">'+body+'</g></svg>';

 const label=(band='#9a7b55') =>
   '<rect x="25" y="35" width="22" height="13" rx="4" fill="#fffaf0" stroke="#d9cbb7" stroke-width=".8"/>'+
   '<rect x="27.5" y="38" width="17" height="2.4" rx="1.2" fill="'+band+'" opacity=".8"/>'+
   '<rect x="29" y="43" width="14" height="1.7" rx=".8" fill="#c8b99f" opacity=".9"/>';

 const glassBottle=(liquid='#5a3824',cap='#3f3b35',band='#9a7b55',shape='round')=>{
   const body = shape==='square'
     ? '<path d="M25 19h22l4 7v27c0 5-3.5 8-8.5 8h-13c-5 0-8.5-3-8.5-8V26Z" fill="'+liquid+'" stroke="#6c5947" stroke-width="1.1"/>'
     : '<path d="M29 17h14v6c0 2.2 1.6 4.1 4.1 6.6 2.1 2.1 3.4 5 3.4 8v15c0 5.4-4 8.5-9 8.5h-11c-5 0-9-3.1-9-8.5v-15c0-3 1.3-5.9 3.4-8 2.5-2.5 4.1-4.4 4.1-6.6Z" fill="'+liquid+'" stroke="#6c5947" stroke-width="1.1"/>';
   return svg(
     body+
     '<path d="M29 17h14v-6H29Z" fill="'+cap+'" stroke="#5c5147" stroke-width="1"/>'+
     '<rect x="28" y="9" width="16" height="4" rx="2" fill="url(#'+id+'metal)" opacity=".7"/>'+
     '<path d="M28 25c3-2.2 13-2.2 16 0" stroke="#fff" stroke-opacity=".5" stroke-width="1.4" stroke-linecap="round"/>'+
     '<path d="M27 29c-2 7-2 18-.5 24" stroke="#fff" stroke-opacity=".36" stroke-width="2.2" stroke-linecap="round"/>'+
     label(band)
   );
 };

 const oilBottle=(liquid='#c27d24',cap='#778862',band='#a58a52')=>svg(
   '<path d="M30 14h12v8c0 2 1.2 3.8 3 5.8 2.4 2.6 3.5 5.7 3.5 9.3v17c0 4.8-3.3 7.4-7.4 7.4H30.9c-4.1 0-7.4-2.6-7.4-7.4v-17c0-3.6 1.1-6.7 3.5-9.3 1.8-2 3-3.8 3-5.8Z" fill="'+liquid+'" stroke="#9a6f3e" stroke-width="1.05"/>'+
   '<path d="M30 14h12V8H30Z" fill="'+cap+'" stroke="#596450" stroke-width="1"/>'+
   '<ellipse cx="36" cy="9" rx="6" ry="2.2" fill="#b3be8f"/>'+
   '<path d="M27.5 29c2.2-2.5 14.8-2.5 17 0" stroke="#fff" stroke-opacity=".55" stroke-width="1.3"/>'+
   '<path d="M27 33c-1.4 7-1.5 15-.7 20" stroke="#fff" stroke-opacity=".42" stroke-width="2" stroke-linecap="round"/>'+
   label(band)
 );

 const pasteTub=(paste='#9a5f38',lid='#c9b99c',band='#9a7b55')=>svg(
   '<path d="M18 26h36l-2.4 26.5c-.5 5.5-4.7 8.5-10.2 8.5H30.6c-5.5 0-9.7-3-10.2-8.5Z" fill="url(#'+id+'glass)" stroke="#a89478" stroke-width="1.1"/>'+
   '<path d="M21 32h30l-1.7 18.5c-.3 3.4-3 5.4-6.4 5.4H29.1c-3.4 0-6.1-2-6.4-5.4Z" fill="'+paste+'" opacity=".93"/>'+
   '<ellipse cx="36" cy="27" rx="19.5" ry="6.7" fill="'+lid+'" stroke="#8f7a5c" stroke-width="1.1"/>'+
   '<ellipse cx="36" cy="25.5" rx="16.5" ry="4.5" fill="#fff" opacity=".22"/>'+
   '<path d="M23 38c6 2.3 20 2.3 26 0" stroke="#fff" stroke-opacity=".26" stroke-linecap="round"/>'+
   label(band)
 );

 const spiceJar=(powder='#ece4d6',lid='#c5b9a6',band='#8d7657',dark=false)=>svg(
   '<path d="M23 22h26v31.5c0 5-3.2 7.5-7.8 7.5H30.8c-4.6 0-7.8-2.5-7.8-7.5Z" fill="url(#'+id+'glass)" stroke="#a99a86" stroke-width="1.05"/>'+
   '<path d="M25.5 39h21v16H25.5Z" rx="3" fill="'+powder+'" opacity=".96"/>'+
   '<rect x="21.5" y="15" width="29" height="9" rx="4.5" fill="'+lid+'" stroke="#887b6d" stroke-width="1"/>'+
   '<path d="M25 28c2.5-1.4 19.5-1.4 22 0" stroke="#fff" stroke-opacity=".65" stroke-linecap="round"/>'+
   label(band)
 );

 const squeeze=(fill='#d85642',cap='#efe4cf',band='#a77654')=>svg(
   '<path d="M30 11h12l1.5 6-2 4v4c6.2 4.3 9 12.6 9 23.2 0 8.4-5.2 13-14.5 13s-14.5-4.6-14.5-13c0-10.6 2.8-18.9 9-23.2v-4l-2-4Z" fill="'+fill+'" stroke="#8f7866" stroke-width="1.05"/>'+
   '<path d="M29 10h14v8H29Z" rx="2" fill="'+cap+'" stroke="#9f8c75" stroke-width="1"/>'+
   '<path d="M27 32c4-2.5 14-2.5 18 0" stroke="#fff" stroke-opacity=".48" stroke-width="1.4" stroke-linecap="round"/>'+
   label(band)
 );

 if (/된장/.test(key)) return pasteTub('#a96f3f','#d4c09d','#7f603f');
 if (/쌈장/.test(key)) return pasteTub('#875538','#95a776','#687d55');
 if (/고추장/.test(key)) return pasteTub('#b9432e','#c94d38','#9e3628');
 if (/고춧가루/.test(key)) return spiceJar('#bb402c','#ccb998','#af3d2f');
 if (/후추/.test(key)) return spiceJar('#514840','#302d2a','#6f6358',true);
 if (/설탕/.test(key)) return spiceJar('#f4eee5','#d8c8ad','#b49973');
 if (/소금/.test(key)) return spiceJar('#fbfaf4','#d0c0a5','#91a4a5');
 if (/참기름/.test(key)) return oilBottle('#ad681f','#8fa06e','#a8732f');
 if (/들기름/.test(key)) return oilBottle('#9a6b31','#6f8561','#7c6239');
 if (/식용유|올리브유/.test(key)) return oilBottle('#c99b31','#789363','#9c823c');
 if (/식초/.test(key)) return glassBottle('#d9b657','#cfc3ad','#a88b62');
 if (/액젓|참치액/.test(key)) return glassBottle('#9d5c2a','#738568','#8c6b48');
 if (/맛술/.test(key)) return glassBottle('#c78f50','#b8a183','#9b7858');
 if (/굴소스/.test(key)) return glassBottle('#3e3028','#d3a249','#795938','square');
 if (/간장/.test(key)) return glassBottle('#392a24','#3e3934','#6f5b49','square');
 if (/올리고당|물엿/.test(key)) return squeeze('#d7b65b','#eee5d1','#c69f4d');
 if (/케첩/.test(key)) return squeeze('#c94535','#efe4d4','#b23a2c');
 if (/마요네즈/.test(key)) return squeeze('#eee1bd','#d8b342','#9d8b63');
 if (/다진마늘|마늘/.test(key)) return pasteTub('#e7d3a0','#aab88b','#7f8e67');
 return miniature(foodIdForName(key),'food-art '+safeClass(cls));
}
window.UMFKitchenArt=Object.freeze({icon,foodArt,dishArt,seasoningArt,foodIdForName,asset:ATLAS});
})();
