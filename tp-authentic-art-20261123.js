/* THE PLAY ARCHIVE · 26 illustrated authentic game props.
   No generic AI photography, no external hosts or borrowed broadcast stills. */
(()=>{
'use strict';
const gold='#d9b57b',line='#bc9061',cream='#f5e4c9',dark='#16131b';
const r=(x,y,w,h,fill='url(#felt)',radius=10,stroke='#a37b56',sw=2)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
const c=(x,y,R,fill,stroke='#dab98c',sw=2)=>`<circle cx="${x}" cy="${y}" r="${R}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
const l=(x,y,x2,y2,stroke=gold,sw=3)=>`<path d="M${x} ${y} L${x2} ${y2}" fill="none" stroke="${stroke}" stroke-width="${sw}" stroke-linecap="round"/>`;
const t=(x,y,s,sz=38,color=cream,weight=600,anchor='middle')=>`<text x="${x}" y="${y}" fill="${color}" font-family="Georgia,'Noto Serif KR',serif" font-size="${sz}" font-weight="${weight}" text-anchor="${anchor}" dominant-baseline="middle">${s}</text>`;
const g=(x,y,ang,body)=>`<g transform="translate(${x},${y}) rotate(${ang})">${body}</g>`;
const card=(x,y,w,h,value,opts={})=>g(x,y,opts.ang||0,
  `<rect x="7" y="10" width="${w}" height="${h}" rx="12" fill="#050306" opacity=".75" filter="url(#shadow)"/>`+
  r(0,0,w,h,opts.face||'url(#paper)',12,opts.edge||'#d7bd9b',3)+r(8,8,w-16,h-16,'none',7,opts.ink||'#ae8c68',1.5)+
  (opts.content??t(w/2,h/2+7,value,opts.size||90,opts.color||'#312530',600)));
const stone=(x,y,cl='#e7dbc7',R=20)=>c(x+2,y+5,R,'#09070b','#070609',1)+c(x,y,R,cl,'#f4e1bd',1.8)+c(x-5,y-7,R*.26,'#ffffff2c','none',0);
const board=(x,y,w,h,cols,rows,opt={})=>{
 let z=r(x,y,w,h,opt.fill||'url(#wood)',8,'#a4825a',4);
 for(let i=1;i<cols;i++)z+=l(x+i*w/cols,y+9,x+i*w/cols,y+h-9,'#a77c58c9',2);
 for(let j=1;j<rows;j++)z+=l(x+9,y+j*h/rows,x+w-9,y+j*h/rows,'#a77c58c9',2);
 return z;
};
const playcard=(x,y,v,color,ang=0)=>card(x,y,112,155,v,{ang,face:'#1e1820',edge:color,ink:color,color:color,size:78});
const tile=(x,y,v,fill,ink=cream)=>g(x,y,0,r(0,0,84,86,fill,8,'#c49a6e',2)+t(42,44,v,48,ink));
const circTile=(x,y,fill)=>r(x,y,70,70,'#d9cab9',8,'#ae8c70',2)+c(x+35,y+35,19,fill,'#0000',0);
const morris=()=>{let s=r(128,95,364,364,'url(#wood)',10,'#c29e70',5);for(const b of [0,1,2]){
 let i=155+b*53,j=122+b*53,e=465-b*53,f=432-b*53;s+=`<path d="M${i} ${j}H${e}V${f}H${i}Z" fill="none" stroke="#30242b" stroke-width="7"/>`;
 for(const [px,py] of [[i,j],[i,(j+f)/2],[i,f],[(i+e)/2,j],[(i+e)/2,f],[e,j],[e,(j+f)/2],[e,f]])s+=c(px,py,5,'#241c23','#a8865f',1);
 }for(const [x,y,x2,y2] of [[310,122,310,228],[310,326,310,432],[155,277,261,277],[359,277,465,277]])s+=l(x,y,x2,y2,'#30242b',7);
 for(const [x,y,cl] of [[155,122,'#f0dbb6'],[310,122,'#f0dbb6'],[465,277,'#f0dbb6'],[261,277,'#24252b'],[261,228,'#24252b'],[359,326,'#24252b'],[208,175,'#f0dbb6'],[310,432,'#24252b']])s+=stone(x,y,cl,18);return s;
};
const quarto=()=>{let s=card(80,166,118,193,'8',{face:'#5c1828',edge:'#e2a6a6',color:'#fae9d9',ang:-9});s+=card(187,130,118,193,'3',{face:'#183e68',edge:'#8fb6e5',color:'#eaf1ff',ang:-3});s+=card(304,134,118,193,'6',{face:'#214c37',edge:'#a3c69e',color:'#eaf1ee',ang:3});s+=card(417,175,118,193,'9',{face:'#8e6a1f',edge:'#ebd28b',color:'#fff2ca',ang:10});return s};
const hex=(x,y,R,fill='url(#wood)',stroke='#a98d6c')=>{let q=[];for(let i=0;i<6;i++){const a=(Math.PI/3*i)+Math.PI/6;q.push(`${x+R*Math.cos(a)},${y+R*Math.sin(a)}`)}return `<polygon points="${q.join(' ')}" fill="${fill}" stroke="${stroke}" stroke-width="3"/>`};
const cube=(x,y,w=53,h=30)=>`<path d="M${x} ${y} l${w} -${h} l${w} ${h} l-${w} ${h}Z" fill="#edd7b7" stroke="#705a51" stroke-width="2"/><path d="M${x} ${y} l${w} ${h} v${w} l-${w} -${h}Z" fill="#a98868" stroke="#705a51" stroke-width="2"/><path d="M${x+w} ${y+h} l${w} -${h} v${w-h} l-${w} ${h}Z" fill="#cbad89" stroke="#705a51" stroke-width="2"/>`;
const abGrid=(opts={})=>{const n=opts.n||7,x=146,y=103,st=47;let s=r(x-12,y-11,(n-1)*st+24,(n-1)*st+24,'url(#wood)',8,'#c6a272',4);
 for(let i=0;i<n;i++)s+=l(x+i*st,y,x+i*st,y+(n-1)*st,'#72513d',2)+l(x,y+i*st,x+(n-1)*st,y+i*st,'#72513d',2);
 return {s,x,y,st};};
const motifs={
 '흑과 백':()=>card(95,168,165,244,'5',{ang:-12,face:'#15141b',edge:'#cfaa7e',color:'#f4e5d6',size:145})+card(353,160,164,245,'7',{ang:10,face:'#f1e5d4',edge:'#d5b691',color:'#2c2229',size:145})+r(264,208,76,120,'#382630',12,'#d4ab7c',2)+t(302,271,'VS',32,gold),
 '인디언 포커':()=>card(118,118,157,226,'?',{ang:-11,face:'#221924',edge:'#be975f',color:gold,size:112})+card(350,123,156,228,'6',{ang:11,face:'#ead9bc',color:'#2a2430',size:118})+Array.from({length:5},(_,i)=>stone(207+i*40,426-i%2*8,'#c5a476',17)).join(''),
 '결! 합!':()=>{let s='';const shapes=['●','▲','■','▲','■','●','■','●','▲'];const colors=['#b96f69','#b9a35e','#639e9c','#aa8aaf'];for(let i=0;i<9;i++){const x=134+(i%3)*124,y=93+Math.floor(i/3)*124;s+=r(x,y,108,109,'url(#paper)',9,'#b59b7c',3)+t(x+54,y+57,shapes[i],67,colors[(i+Math.floor(i/3))%4])}return s},
 '십이장기':()=>{let s=board(157,92,310,408,3,4);const q=[['相',0,0],['王',1,0],['將',2,0],['子',0,1],['子',2,2],['將',0,3],['王',1,3],['相',2,3]];for(const [str,c0,r0] of q){s+=g(208+c0*102,142+r0*100,0,hex(0,0,34,r0<2?'#d8b58a':'#39242a','#b68c65')+t(0,2,str,31,r0<2?'#38252a':'#f6d6ab'))}return s},
 '1·2·3 게임':()=>card(116,182,130,200,'1',{ang:-10,size:135,face:'#eee2d1',color:'#292431'})+card(250,138,130,200,'2',{size:135,face:'#f5e8d4',color:'#28212b'})+card(383,184,130,200,'3',{ang:10,size:135,face:'#eee2d1',color:'#292431'}),
 '마이너스 경매':()=>card(137,131,202,251,'−17',{ang:-6,face:'#efe0c9',color:'#4c252c',size:105})+Array.from({length:4},(_,i)=>stone(405+(i%2)*51,339+Math.floor(i/2)*42,'#c7a16e',24)).join('')+t(418,265,'−',110,'#d9b57b'),
 '나인 멘스 모리스':morris,
 '콰트로':quarto,
 '헥사곤':()=>{let s='';for(let r0=-2;r0<=2;r0++)for(let q=-2;q<=2;q++){if(Math.abs(q+r0)>2)continue;const x=307+(q+r0/2)*90,y=280+r0*79;s+=hex(x,y,49,['#30212b','#58413b','#3d404d'][(q+2*r0+12)%3],'#c9a16d')+t(x,y+3,((q*3+r0*2+17)%9)+1,35,'#f5e1be')}return s},
 '같은 숫자 찾기':()=>card(119,137,152,215,'8',{ang:-9,face:'#ecdac3',color:'#29212b',size:121})+card(310,137,152,215,'8',{ang:9,face:'#ecdac3',color:'#29212b',size:121})+card(256,282,116,156,'?',{face:'#261b28',color:gold,size:92}),
 '같은 그림 찾기':()=>card(106,153,150,212,'◆',{ang:-9,face:'#eadac6',color:'#936b75',size:120})+card(360,151,150,212,'◆',{ang:9,face:'#eadac6',color:'#936b75',size:120})+card(253,189,118,166,'?',{face:'#211926',color:gold,size:108}),
 '연승게임':()=>card(110,145,149,220,'2',{ang:-8,face:'#d9c9ae',color:'#2c2330',size:123})+card(351,145,149,220,'3',{ang:8,face:'#d9c9ae',color:'#2c2330',size:123})+t(309,251,'VS',35,gold)+Array.from({length:3},(_,i)=>c(249+i*58,417,16,'#c9a373')).join(''),
 '블라인드 오목':()=>{let B=abGrid({n:7}),s=B.s;for(const [i,j,col] of [[1,1,'#151319'],[2,2,'#f1e0bf'],[3,3,'#151319'],[4,4,'#f1e0bf'],[4,2,'#151319'],[2,3,'#f1e0bf'],[5,3,'#151319']])s+=stone(B.x+i*B.st,B.y+j*B.st,col,15);return s+r(392,111,75,45,'#20141b',5)+t(430,135,'?',36,gold)},
 '기사의 여행':()=>{let s=r(113,79,390,391,'#28202c',7,'#c9a87a',4);for(let y=0;y<8;y++)for(let x=0;x<8;x++)s+=r(120+x*47,86+y*47,47,47,(x+y)%2?'#40313d':'#ddc7a6',0,'none',0);s+=t(260,302,'♞',112,'#251c28');for(const [x,y,n] of [[0,0,1],[1,2,2],[3,3,3],[5,4,4],[6,6,5]])s+=t(143+x*47,110+y*47,n,22,'#a16f45');return s},
 '시간 경매':()=>r(135,134,350,270,'#271b23',26,'#bb986c',6)+c(310,252,115,'url(#clock)','#d3ae7b',6)+Array.from({length:12},(_,i)=>{const a=i*Math.PI/6;return c(310+92*Math.sin(a),252-92*Math.cos(a),3.5,'#f3d5a3','#f3d5a3',1)}).join('')+l(310,252,310,182,cream,8)+l(310,252,359,282,cream,8)+c(310,252,9,gold)+r(250,397,122,51,'#b98d5e',13,'#e3c093',3),
 '큐브 세기':()=>{let s='';const levels=[[1,3],[2,3],[3,2],[4,1],[0,1]];for(let z=0;z<3;z++){for(const [x,y] of levels){if((x+y+z)%4===0)continue;s+=cube(131+(x+y)*51,330+(y-x)*31-z*62,40,24)}}return s},
 '네모 세기':()=>{let s=board(129,108,361,358,5,5,{fill:'#241a23'});for(let y=0;y<5;y++)for(let x=0;x<5;x++)s+=t(165+x*72,145+y*70,((y*4+x*3)%7)+1,35,'#edd2ac');return s+r(201,178,214,142,'#bc986128',4,'#e0b477',6)},
 '4인 3목':()=>{let s=board(141,102,343,343,7,7,{fill:'#271d27'});for(const [x,y,col] of [[1,1,'#b85f63'],[2,1,'#b85f63'],[3,1,'#b85f63'],[0,5,'#b9ab69'],[4,4,'#b9ab69'],[3,3,'#6e9ba9'],[5,2,'#779c7b'],[1,4,'#779c7b']])s+=stone(165+x*49,126+y*49,col,18);return s},
 '바그찰':()=>{let B=abGrid({n:5}),s=B.s;for(let j=0;j<4;j++)for(let i=0;i<4;i++)if((i+j)%2===0){s+=l(B.x+i*B.st,B.y+j*B.st,B.x+(i+1)*B.st,B.y+(j+1)*B.st,'#72513d',2);s+=l(B.x+(i+1)*B.st,B.y+j*B.st,B.x+i*B.st,B.y+(j+1)*B.st,'#72513d',2)}for(const [x,y] of [[0,0],[4,0],[0,4],[4,4]])s+=stone(B.x+x*B.st,B.y+y*B.st,'#744536',19);for(const [x,y] of [[2,1],[2,2],[2,3],[1,2],[3,2],[1,1]])s+=stone(B.x+x*B.st,B.y+y*B.st,'#e3ca9d',16);return s},
 '몽타주':()=>{let s='';for(const [x,hair] of [[112,'#53424d'],[330,'#292027']]){s+=r(x,114,165,274,'url(#paper)',12,'#b99c75',3)+`<ellipse cx="${x+83}" cy="232" rx="52" ry="72" fill="#b9a18b"/>`+`<path d="M${x+31} 202 Q${x+37} 111 ${x+93} 149 Q${x+139} 135 ${x+137} 214 Q${x+103} 183 ${x+31} 202" fill="${hair}"/>`+l(x+62,236,x+77,236,'#483640',3)+l(x+91,236,x+105,236,'#483640',3)+l(x+75,290,x+98,290,'#74545a',3)}return s+r(265,247,88,58,'#281f28',6,'#bc9876',2)+t(309,281,'?',48,gold)},
 '신의 판결':()=>{let dots='';for(const [x,y] of [[39,39],[117,39],[77,78],[39,117],[117,117]])dots+=c(x,y,10,'#422d3b','#422d3b',1);let s=g(172,160,-12,r(0,0,156,156,'url(#paper)',15,'#d2aa7f',4)+dots);s+=g(344,220,11,r(0,0,142,142,'url(#paper)',15,'#d2aa7f',4)+c(38,37,12,'#422d3b','#422d3b',1)+c(105,102,12,'#422d3b','#422d3b',1));return s},
 '미스터리 사인':()=>card(132,136,151,205,'7',{ang:-7,face:'#e8dbc6',color:'#2c222b',size:115})+card(337,135,151,205,'?',{ang:7,face:'#e8dbc6',color:'#2c222b',size:115})+t(309,238,'×',68,gold)+t(312,430,'12   24   48',31,gold),
 '벽바둑':()=>{let s=board(124,93,366,366,7,7,{fill:'#2b2225'});for(const [x,y,col] of [[1,1,'#b95761'],[5,4,'#6299a8'],[2,2,'#b95761'],[4,5,'#6299a8']])s+=stone(152+x*49,121+y*49,col,17);for(const [x,y,x2,y2] of [[2,3,4,3],[1,5,1,6],[4,1,4,3]])s+=l(152+x*49,121+y*49,152+x2*49,121+y2*49,'#f2ce8b',8);return s},
 '해 달 별':()=>tile(123,180,'☀','#502c36','#efbd6e')+tile(267,163,'☾','#30405b','#e5ddd1')+tile(412,180,'★','#4d3d33','#f2d39a')+Array.from({length:5},(_,i)=>stone(223+i*42,415,'#bd9461',15)).join(''),
 '하나 빼기':()=>card(121,151,155,230,'3',{face:'#eee0c8',color:'#29202a',ang:-9,size:115})+card(349,151,155,230,'8',{face:'#eee0c8',color:'#29202a',ang:9,size:115})+t(310,258,'→',52,gold)+l(380,408,486,408,'#c45e69',9),
 '벽바둑 2':()=>{let s=board(124,93,366,366,7,7,{fill:'#2b2225'});for(const [x,y,col,shape] of [[1,1,'#bc5e61','c'],[5,4,'#699ba7','c'],[2,2,'#bc5e61','s'],[4,5,'#699ba7','s']]){const px=152+x*49,py=121+y*49;s+=shape==='c'?stone(px,py,col,18):r(px-18,py-18,36,36,col,4,'#eee1ce',2)}for(const [x,y,x2,y2] of [[2,3,4,3],[1,5,1,6],[4,1,4,3]])s+=l(152+x*49,121+y*49,152+x2*49,121+y2*49,'#f2ce8b',8);return s}
};
const defs=`<defs><radialGradient id="bg" cx="50%" cy="24%" r="80%"><stop stop-color="#51313a"/><stop offset=".52" stop-color="#261821"/><stop offset="1" stop-color="#100b11"/></radialGradient><linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#9b7454"/><stop offset=".38" stop-color="#77543e"/><stop offset="1" stop-color="#48302b"/></linearGradient><linearGradient id="paper" x1="0" y1="0" x2=".85" y2="1"><stop stop-color="#fff2dc"/><stop offset=".6" stop-color="#e5d2b4"/><stop offset="1" stop-color="#bb9f81"/></linearGradient><linearGradient id="felt" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#352330"/><stop offset="1" stop-color="#140e16"/></linearGradient><radialGradient id="clock"><stop stop-color="#5e4b44"/><stop offset="1" stop-color="#281d27"/></radialGradient><linearGradient id="vignette" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".3"/></linearGradient><filter id="shadow"><feGaussianBlur stdDeviation="7"/></filter></defs>`;
function svgFor(name){const fn=motifs[name];if(!fn)return '';return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 620" width="620" height="620" role="img" aria-label="${name} 실제 게임 도구 모티브"><rect width="620" height="620" fill="url(#bg)"/>${defs}<path d="M0 90Q310 -25 620 90" stroke="#d9ac6c" opacity=".16" fill="none" stroke-width="2"/><ellipse cx="310" cy="568" rx="332" ry="104" fill="#0c090d" opacity=".63"/><ellipse cx="310" cy="563" rx="325" ry="98" fill="none" stroke="#b48453" opacity=".24" stroke-width="3"/><g filter="url(#shadow)" opacity=".65"><ellipse cx="310" cy="458" rx="218" ry="24" fill="#09060b"/></g>${fn()}<rect width="620" height="620" fill="url(#vignette)" pointer-events="none"/></svg>`}
const art={};Object.keys(motifs).forEach(n=>art[n]='data:image/svg+xml;charset=UTF-8,'+encodeURIComponent(svgFor(n)));
window.tpAuthenticArt=art;
const renderPrevious=window.showHome;
if(typeof renderPrevious==='function'){
 window.showHome=function(...args){const result=renderPrevious.apply(this,args);const root=document.querySelector('.tp-home');if(!root)return result;
   const list=typeof tpGames==='function'?tpGames().slice(tpPage*4,tpPage*4+4):[];
   root.querySelectorAll('.tp-gallery .tp-game').forEach((element,i)=>{const url=art[list[i]],img=element.querySelector('.tp-image');if(img&&url){img.style.backgroundImage=`url("${url}")`;img.setAttribute('role','img');img.setAttribute('aria-label',`${list[i]} 게임 도구 일러스트`);}});
   const recent=root.querySelector('.tp-recent-image');if(recent&&typeof tpRecent==='string'&&art[tpRecent])recent.style.backgroundImage=`url("${art[tpRecent]}")`;
   return result;
 };
 window.showHome();
}
})();