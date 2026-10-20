/* Artwork adapted from the original Han-kki Kitchen; no external runtime or assets are loaded. */
(() => {
'use strict';
const safeClass=value=>String(value??'').split(/\s+/).filter(token=>/^[a-zA-Z0-9_-]+$/.test(token)).join(' ');
let seq = 0;
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
function foodArt(name, cls='') {
 cls=safeClass(cls);
 const id='food-'+(++seq); let content='';
 const shell='fill="url(#'+id+'-cream)" stroke="#d6bd9d" stroke-width="1.5"';
 const green='fill="url(#'+id+'-green)"';
 switch(name){
 case 'egg':content=`<path d="M12 62 19 45h65l8 17-5 16H17Z" fill="#d8c4a3"/><path d="M15 62h75l-6 18H21Z" fill="#e6d6b6"/>${[28,50,72].map((x,i)=>`<path d="M${x-9} 53c0-12 4-23 10-23s11 12 11 23c0 15-21 15-21 0" fill="url(#${id}-egg)" stroke="#d4b494"/>`).join('')}<path d="M23 70h56" stroke="#c3ad8c" stroke-width="2"/>`;break;
 case 'milk':content=`<path d="M32 24h35l7 12v46H26V36Z" ${shell}/><path d="M32 24v-9h27l8 9Z" fill="#a3bbaa"/><path d="m32 24-6 12h34l7-12" fill="#dce9da"/><path d="M60 36h14v46H60" fill="#e6dfcd"/><rect x="30" y="46" width="25" height="25" rx="5" fill="#adc1a0"/><path d="M39 62c-4-4 1-8 4-5 3-3 8 1 4 5l-4 4Z" fill="#f7f4e4"/>`;break;
 case 'tofu':content=`<path d="m17 42 20-10 49 5 3 35-64 6Z" fill="#d2dacd" stroke="#a8b8a2"/><path d="m27 40 17-6 34 5v26l-47 5Z" ${shell}/><path d="m31 46 47-7v26l-47 5Z" fill="#fff3d8"/><path d="M24 73h58" stroke="#afc0a5"/><circle cx="40" cy="54" r="1" fill="#ddcfb6"/><circle cx="64" cy="58" r="1" fill="#ddcfb6"/>`;break;
 case 'chicken':content=`<path d="m14 46 11-15h53l11 40-11 9H22Z" fill="#d3ddd1" stroke="#a7b7a1"/><path d="M30 57c-7-8 3-26 17-22 15 3 14 26 3 31-9 4-15 0-20-9" fill="url(#${id}-pink)"/><path d="M49 61c-3-10 13-20 24-13 12 9 4 25-9 25-10 0-12-6-15-12" fill="url(#${id}-pink)"/><path d="M28 73h48" stroke="#bacbb6"/>`;break;
 case 'onion':content=`<path d="M49 19c-3 7 6 11 9 14 20 11 22 32 10 44-12 13-38 8-45-7-7-16 4-28 18-37 4-3 2-10 0-14" fill="url(#${id}-gold)" stroke="#c69956"/><path d="M46 34c-18 15-20 35-9 42M52 35c13 12 16 30 8 42M50 39v42" stroke="#dbb778" fill="none" stroke-width="1.5"/><path d="m44 21 1-11 5 8 6-8-3 14" fill="#7d9362"/>`;break;
 case 'scallion':content=`${[-14,0,13].map((r,i)=>`<g transform="rotate(${r} 50 60)"><path d="M${38+i*5} 64q-7-28-6-50h8q-2 26 3 51" ${green}/><path d="M${47+i*4} 64q4-25 14-47l7 3q-12 24-14 47" ${green}/><path d="M${40+i*3} 57h12l-2 29h-8Z" fill="url(#${id}-cream)"/><path d="m43 86-2 7m5-7v8m3-8 3 6" stroke="#bea47d"/></g>`).join('')}<path d="M30 65q18 5 35-1" stroke="#d9b269" stroke-width="4"/>`;break;
 case 'carrot':content=`<g transform="rotate(26 50 50)"><path d="M50 29C20 17 30 60 47 88c3 5 8-7 16-28s7-36-13-31" fill="url(#${id}-orange)" stroke="#ce7b3f"/><path d="m36 41 12 2M53 54l10 1M43 65l8 2" stroke="#d37e3d" stroke-width="2" stroke-linecap="round"/><path d="M45 30Q28 5 37 7q11 5 13 17Q47-1 56 5q7 8 0 22Q76 6 71 19L59 34" ${green}/></g>`;break;
 case 'broccoli':content=`<path d="m45 51-10 28q12 9 27 0L53 51Z" fill="#b1c58c"/><path d="m48 65-15-12m18 9 16-11" stroke="#76995c" stroke-width="5"/>${[[26,43,16],[43,31,20],[63,33,18],[76,48,17],[53,47,19],[33,54,16]].map(([x,y,r])=>`<circle cx="${x}" cy="${y}" r="${r}" ${green}/>`).join('')}<g fill="#a0ba7f" opacity=".65"><circle cx="35" cy="30" r="5"/><circle cx="60" cy="24" r="5"/><circle cx="70" cy="41" r="4"/></g>`;break;
 case 'kimchi':content=`<rect x="25" y="28" width="51" height="56" rx="12" fill="#e5d6b9" stroke="#cab18d"/><rect x="29" y="37" width="43" height="37" rx="7" fill="#d78150"/><path d="m35 45 16-2-7 10 20-4-11 13 13-2" stroke="#efb16a" stroke-width="6" fill="none"/><rect x="22" y="20" width="57" height="15" rx="5" fill="#ab8160"/><path d="M30 23h39" stroke="#cfa783" stroke-width="2"/>`;break;
 case 'rice':content=`<ellipse cx="50" cy="52" rx="35" ry="22" fill="#fff7e1" stroke="#ded3b9"/><path d="M15 53h70c-4 29-20 31-35 31S18 77 15 53" ${shell}/><path d="M37 82h26v5H37Z" fill="#d3b993"/><g stroke="#e3d7bd" stroke-width="3" stroke-linecap="round"><path d="m25 44 4-2m7 4 4 2m5-9 3 3m9-7 4 2m6 7 5 1m-20 2 3 2m-26-9 4 2"/></g>`;break;
 case 'tomato':content=`<path d="M50 29C14 17 9 64 30 79c16 12 42 5 50-14 11-26-6-45-30-36" fill="url(#${id}-red)" stroke="#bf6250"/><path d="m50 34-21-7 17-2 4-13 6 13 18-3-12 11 3 13-14-9-11 7Z" ${green}/><path d="M26 48c-5 7-5 14-2 19" stroke="#f5baa1" stroke-width="4" stroke-linecap="round"/>`;break;
 case 'mushroom':content=`<path d="m39 45-5 38q16 10 32-1l-7-37" ${shell}/><path d="M17 51C11 15 83 8 86 48q-32 17-69 3" fill="url(#${id}-brown)" stroke="#aa8060"/><path d="M22 51q30 12 61-2" stroke="#ddc2a5" stroke-width="3"/><circle cx="35" cy="32" r="5" fill="#d9bd9c" opacity=".65"/>`;break;
 case 'potato':content=`<path d="M24 34C32 19 65 21 78 40s3 40-20 44S13 73 14 55c1-9 6-12 10-21" fill="url(#${id}-gold)" stroke="#bea072"/><g fill="#b4986b"><ellipse cx="32" cy="46" rx="3" ry="2"/><ellipse cx="60" cy="36" rx="3" ry="2"/><ellipse cx="64" cy="64" rx="3" ry="2"/><ellipse cx="37" cy="70" rx="2" ry="2"/></g>`;break;
 case 'zucchini':content=`<g transform="rotate(34 50 50)"><rect x="31" y="14" width="39" height="76" rx="18" fill="url(#${id}-green)"/><path d="M39 26v48M50 21v61M62 25v50" stroke="#c2ca81" stroke-width="3" opacity=".7"/><path d="M44 17V7h12l2 12" fill="#6e8458"/></g>`;break;
 case 'oil':case 'soy':content=`<path d="M38 25h24v12l11 12v35H27V49l11-12Z" fill="${name==='oil'?'#dec785':'#836349'}" stroke="#b19666"/><rect x="35" y="13" width="30" height="16" rx="4" fill="${name==='oil'?'#8c9e73':'#b6895a'}"/><rect x="30" y="52" width="40" height="23" rx="3" fill="#f3e9cf"/><path d="M41 62h18M45 68h10" stroke="${name==='oil'?'#b69c55':'#98714c'}" stroke-width="3"/><path d="M33 46v-2l9-8" stroke="#f1e2b4" stroke-width="3" opacity=".55"/>`;break;
 case 'tuna':content=`<path d="M18 41v30c0 18 64 18 64 0V41" fill="#94b6a4" stroke="#799b87"/><ellipse cx="50" cy="40" rx="32" ry="13" fill="#d8ddd0" stroke="#aab6a4"/><ellipse cx="50" cy="40" rx="25" ry="8" fill="#c3cebd"/><path d="M43 39h13v4H43Z" fill="#a2b49f"/><path d="M18 51q33 11 64 0v18q-30 13-64 0Z" fill="#f3e7c9"/><path d="m40 60 12-6 10 6-10 6-12-6-8 6V54Z" fill="#87a38e"/>`;break;
 case 'garlic':content=`<path d="m49 15 5 17c29 9 33 31 19 45-13 12-37 12-50-2-11-12-6-30 18-43l3-18" ${shell}/><path d="M46 37C29 48 30 71 39 81M53 36c16 15 15 33 5 46M49 40v44" stroke="#decbb1" fill="none"/>`;break;
 case 'salt':content=`<rect x="29" y="31" width="43" height="52" rx="10" ${shell}/><path d="M30 35V24c0-10 40-10 40 0v11" fill="#c8c6b7"/><path d="M36 20h2m7-2h2m7 1h2m7 3h2" stroke="#8c9484" stroke-width="2"/><rect x="34" y="47" width="32" height="20" rx="3" fill="#e7d4b2"/><path d="M43 54h14M43 59h14" stroke="#bca580"/>`;break;
 default:content=`<path d="M27 79V38c-1-20 47-20 46 0v41Z" ${shell}/><path d="M33 55q8-26 29-13-6 23-29 13" ${green}/><path d="m38 57 17-11" stroke="#71845a"/>`;
 }
 return `<svg class="food-art ${cls}" viewBox="0 0 100 100" aria-hidden="true" focusable="false"><defs><linearGradient id="${id}-cream" x2=".9" y2="1"><stop stop-color="#fffdf1"/><stop offset="1" stop-color="#e8d9bb"/></linearGradient><radialGradient id="${id}-egg" cx=".3" cy=".25" r=".8"><stop stop-color="#f5dfbd"/><stop offset="1" stop-color="#cfac85"/></radialGradient><radialGradient id="${id}-green" cx=".3" cy=".25" r=".9"><stop stop-color="#b1c485"/><stop offset=".55" stop-color="#88a56a"/><stop offset="1" stop-color="#688452"/></radialGradient><radialGradient id="${id}-orange" cx=".3" cy=".3"><stop stop-color="#f1ba73"/><stop offset="1" stop-color="#df914e"/></radialGradient><radialGradient id="${id}-red" cx=".3" cy=".3"><stop stop-color="#efae87"/><stop offset="1" stop-color="#ce7560"/></radialGradient><radialGradient id="${id}-gold" cx=".3" cy=".3"><stop stop-color="#f0ddaf"/><stop offset="1" stop-color="#d2b077"/></radialGradient><radialGradient id="${id}-pink" cx=".3" cy=".3"><stop stop-color="#f8d9bb"/><stop offset="1" stop-color="#dbab99"/></radialGradient><radialGradient id="${id}-brown" cx=".3" cy=".3"><stop stop-color="#d8bb94"/><stop offset="1" stop-color="#ac8462"/></radialGradient></defs><ellipse cx="50" cy="88" rx="32" ry="5" fill="#705a3a" opacity=".12"/>${content}</svg>`;
}
function dishArt(recipe,cls='') {
 cls=safeClass(cls);
 const id='dish-'+(++seq), ids=recipe?.ingredients?.map(i=>i.foodId)||['egg','rice','scallion'];
 const soup=recipe?.illustration==='soup',salad=recipe?.illustration==='salad';
 const toppings=ids.filter(x=>!['rice','oil','soy','salt','garlic','milk'].includes(x));
 const seed=String(recipe?.id||'rice').split('').reduce((s,c)=>s+c.charCodeAt(0),0);
 const grain=Array.from({length:38},(_,i)=>{let a=i*2.399,r=10+Math.sqrt(i/38)*55;let x=140+Math.cos(a)*r,y=94+Math.sin(a)*r*.43;return `<ellipse cx="${x}" cy="${y}" rx="${3+i%3}" ry="2" transform="rotate(${i*47} ${x} ${y})" fill="${i%3===0?'#d5bc88':'#f5e2b8'}"/>`;}).join('');
 const bits=Array.from({length:22},(_,i)=>{let a=i*2.399+seed,r=15+Math.sqrt(i/22)*58,x=140+Math.cos(a)*r,y=93+Math.sin(a)*r*.44;let type=toppings[i%toppings.length];let col={egg:'#eabd57',carrot:'#d59554',scallion:'#829968',broccoli:'#839e61',tofu:'#efe5c7',chicken:'#d9ba91',tomato:'#c8795e',kimchi:'#c98752',onion:'#e5d7b7',potato:'#d9c796',mushroom:'#a79071',tuna:'#b39784',zucchini:'#b7bc79'}[type]||'#8f9f74';return type==='scallion'?`<ellipse cx="${x}" cy="${y}" rx="5" ry="3" fill="${col}"/><ellipse cx="${x}" cy="${y}" rx="2" ry="1.5" fill="#d2d5a1"/>`:`<rect x="${x-5}" y="${y-3}" width="${type==='chicken'?17:10}" height="${type==='tofu'?9:7}" rx="${type==='egg'?5:2}" transform="rotate(${i*39} ${x} ${y})" fill="${col}"/>`;}).join('');
 return `<svg class="dish-art ${cls}" viewBox="0 0 280 190" aria-hidden="true"><defs><linearGradient id="${id}-bowl" x2=".5" y2="1"><stop stop-color="#fffaf0"/><stop offset="1" stop-color="#d9c7a7"/></linearGradient><radialGradient id="${id}-food"><stop stop-color="${salad?'#bdcc96':soup?'#e5c58a':'#ead6a6'}"/><stop offset="1" stop-color="${salad?'#869f68':soup?'#cdae75':'#cdb77e'}"/></radialGradient></defs><ellipse cx="143" cy="157" rx="88" ry="12" fill="#786b4a" opacity=".1"/><path d="m38 104 41 42 85 13 68-42-49-35Z" fill="#e2c99f" opacity=".4"/><path d="M57 94c4 51 45 57 83 57s79-10 83-57" fill="url(#${id}-bowl)" stroke="#cbbda1"/><ellipse cx="140" cy="91" rx="84" ry="39" fill="#fbf5df" stroke="#dac8a4" stroke-width="2"/><ellipse cx="140" cy="92" rx="70" ry="29" fill="url(#${id}-food)"/>${grain}${bits}<path d="M84 123q48 28 103 0" stroke="#ede2c9" stroke-width="3" fill="none"/><path d="m233 54 18 100m-10-106 17 104" stroke="#b99c76" stroke-width="4" stroke-linecap="round"/>${soup?'<path d="M121 42q-12-12 0-24m24 22q-12-12 0-24" stroke="#dbd1ba" stroke-width="3" fill="none" opacity=".6"/>':''}</svg>`;
}

window.UMFKitchenArt=Object.freeze({icon,foodArt,dishArt});
})();
