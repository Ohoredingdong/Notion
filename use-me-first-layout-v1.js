(()=>{
  const w=document.querySelector('.w');
  if(!w||w.querySelector(':scope > .umf-left')) return;
  const head=w.querySelector(':scope > .head');
  const tabs=w.querySelector(':scope > .tabs');
  const fridge=w.querySelector(':scope > #fridge');
  const season=w.querySelector(':scope > #season');
  const recipe=w.querySelector(':scope > .recipeSec');
  if(!head||!tabs||!fridge||!season||!recipe) return;
  const left=document.createElement('div');
  left.className='umf-left';
  left.append(head,tabs,fridge,season);
  w.insertBefore(left,recipe);
  w.classList.add('umf-wide-layout');
})();
