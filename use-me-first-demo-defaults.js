(()=>{
  const MARK='use-me-first-demo-kitchen-v2';
  if(localStorage.getItem(MARK)) return;
  const SK='use-me-first-seasonings-v1';
  const PK='use-me-first-pantry-v1';
  const read=k=>{try{const v=JSON.parse(localStorage.getItem(k));return Array.isArray(v)?v:[]}catch{return[]}};
  const season=read(SK), pantry=read(PK);
  if(!season.length&&!pantry.length){
    localStorage.setItem(SK,JSON.stringify(['소금','식용유','간장','참기름','고춧가루','다진마늘']));
    localStorage.setItem(PK,JSON.stringify(['밥/즉석밥']));
  }
  localStorage.setItem(MARK,'1');
})();
