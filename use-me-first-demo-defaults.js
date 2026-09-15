(()=>{
  const MARK='use-me-first-demo-kitchen-v3';
  if(localStorage.getItem(MARK)) return;

  const IK='use-me-first-v4', SK='use-me-first-seasonings-v1', PK='use-me-first-pantry-v1';
  const QK='use-me-first-quantities-v1', LOG='use-me-first-meal-log-v1';
  const read=(k,f)=>{try{const v=JSON.parse(localStorage.getItem(k));return v??f}catch{return f}};
  const write=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
  const iso=n=>{const d=new Date;d.setHours(0,0,0,0);d.setDate(d.getDate()+n);return`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
  const today=()=>iso(0);

  const referenceItems=[
    {name:'우유',expiry:iso(2)},
    {name:'두부',expiry:iso(1)},
    {name:'계란',expiry:iso(0)},
    {name:'양파',expiry:iso(10)},
    {name:'애호박',expiry:iso(7)},
    {name:'닭가슴살',expiry:iso(1)},
    {name:'요거트',expiry:iso(8)}
  ];
  const referenceQty={우유:'900ml',두부:'300g',계란:'10개',양파:'3개',애호박:'1개',닭가슴살:'300g',요거트:'1개'};
  const referenceSeason=['소금','후추','식용유','간장','된장','참기름','다진마늘'];
  const referencePantry=['밥/즉석밥'];

  const current=read(IK,[]);
  const demoNames=new Set(['두부','시금치','닭가슴살','김치','우유','양파','계란','애호박','요거트']);
  const demoLike=!current.length||current.every(x=>demoNames.has(String(x?.name||'').trim()));
  let seeded=false;

  if(demoLike){
    write(IK,referenceItems);
    write(QK,referenceQty);
    write(SK,referenceSeason);
    write(PK,referencePantry);
    seeded=true;
  }else{
    const qty=read(QK,{});
    current.forEach(x=>{const n=String(x?.name||'').trim();if(referenceQty[n]&&!qty[n])qty[n]=referenceQty[n]});
    write(QK,qty);
    if(!read(SK,[]).length)write(SK,referenceSeason);
    if(!read(PK,[]).length)write(PK,referencePantry);
  }

  if(seeded){
    const logs=read(LOG,[]);
    if(!logs.some(x=>x?.day===today())){
      const t=new Date;t.setHours(12,30,0,0);
      logs.unshift({name:'계란 볶음밥',ts:t.getTime(),day:today()});
      write(LOG,logs.slice(0,40));
    }
    setTimeout(()=>{
      const all=document.getElementById('all');
      if(all&&/전체 재료/.test(all.textContent||''))all.click();
    },320);
  }

  localStorage.setItem(MARK,'1');
})();
