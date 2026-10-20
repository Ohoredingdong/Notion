/* Beginner filing-reading order. Presentation only; no decision or value changes. */
(()=>{'use strict';
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pair=(term,meaning)=>'<span class="dg-term">'+E(term)+'</span><span class="dg-meaning">→ '+E(meaning)+'</span>';
const steps=[
 ['1. 사업의 내용','무엇을 누구에게 팔아서 돈을 버는지','주요 제품·고객·원재료·생산능력·가동률·주요 계약·위험요인을 확인해요.'],
 ['2. 최근 3년 손익','매출·영업이익·순이익의 흐름','얼마나 늘었는지뿐 아니라 판매량·가격·환율·일회성 이익 중 무엇 때문인지 확인해요.'],
 ['3. 영업현금흐름(CFO)','이익이 실제 현금으로 들어왔는지','순이익이 늘어도 영업현금흐름이 계속 나빠지면 외상매출·재고가 쌓이는지 확인해요.'],
 ['4. 재무상태','현금·외상대금·재고·빚의 규모','곧 갚아야 할 빚과 현금·영업현금흐름을 비교하고, 투자비를 빚으로 계속 채우는지 확인해요.'],
 ['5. 주석·감사의견','숫자가 갑자기 변한 이유와 회계상 주의점','일회성 이익·회수하기 어려운 채권·차입 조건·우발채무·감사의견을 확인해요.'],
 ['6. PER·PBR·ROE','실적을 확인한 뒤 현재 가격을 비교','같은 업종·같은 기간끼리 비교하고, 적자나 자기자본 음수일 때는 일반 비교를 멈춰요.']
];
function install(){const root=document.querySelector('#fullDecisionGuide');if(!root||document.querySelector('#reportReadingOrder'))return;const box=document.createElement('details');box.id='reportReadingOrder';box.className='dg-details';box.innerHTML='<summary>공시를 처음 읽을 때는 이 순서로 봐요</summary><div class="dg-details-body"><div class="dg-basis-grid">'+steps.map(x=>'<div class="dg-basis">'+pair(x[0],x[1])+'<p>'+E(x[2])+'</p></div>').join('')+'</div><div class="source-links"><a href="https://dart.fss.or.kr/" target="_blank" rel="noopener noreferrer">국내 기업 DART에서 찾기 ↗</a><a href="https://www.sec.gov/edgar/search/" target="_blank" rel="noopener noreferrer">미국 기업 SEC에서 찾기 ↗</a></div><p class="dg-tip">DART에서는 회사명을 검색한 뒤 사업보고서·반기보고서·분기보고서를 열어요. 미국 기업은 10-K가 연간, 10-Q가 분기 보고서예요. 연결·별도, 분기·누적, 실제·예상을 섞지 마세요.</p></div>';root.appendChild(box)}
const observer=new MutationObserver(install);observer.observe(document.documentElement,{childList:true,subtree:true});document.addEventListener('radar:cases-ready',install);document.querySelector('#companySelect')?.addEventListener('change',()=>setTimeout(install,0));install();
})();
