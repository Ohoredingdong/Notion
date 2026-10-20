"""Idempotent decision-only UI deployment. Training files remain untouched."""
from pathlib import Path
import re
page=Path('stock-value-radar.html');s=page.read_text(encoding='utf-8')
for marker in ('id="candidateSection"','id="view-analysis"','id="rows"'):
 if marker not in s:raise RuntimeError('Cannot safely install: '+marker)
s=re.sub(r'<script\s+src=[\"\']\./assets/stock-value-radar-v6\.js[\"\'][^>]*>\s*</script>','',s)
s=re.sub(r'<script\s+src=[\"\']\./assets/stock-decision-v7\.js[^\"\']*[\"\'][^>]*>\s*</script>','',s)
tag='<script src="./assets/stock-decision-v7.js?v=7.2" defer></script>'
s=s.replace('</body>',tag+'\n</body>',1)
if 'name="robots"' not in s:s=s.replace('</head>','<meta name="robots" content="noindex,nofollow">\n</head>',1)
assert s.count(tag)==1
page.write_text(s,encoding='utf-8')
js=Path('assets/stock-decision-v7.js');code=js.read_text(encoding='utf-8')
code=code.replace("fetch('./stock-decision-data.json?t='+Date.now()", "fetch('https://raw.githubusercontent.com/Ohoredingdong/Notion/main/stock-decision-data.json?t='+Date.now()")
# Preserve the old renderer hooks; relocate their output instead of suppressing a fault.
marker='// v7.2: keep intraday monitoring separate from completed-session decisions'
if marker not in code:
 anchor="const fresh=()=>"
 if anchor not in code:raise RuntimeError('Decision UI anchor changed')
 patch=r'''// v7.2: keep intraday monitoring separate from completed-session decisions
const legacyStatus=$('#systemBanner');
if(legacyStatus&&$('#view-monitor')){
 const fold=document.createElement('details');fold.className='dv7-details';
 fold.innerHTML='<summary>기존 장중 시세 감시 기록</summary><p class="dv7-notice">이 기록은 장중 시세 수집기의 검사 당시 상태입니다. 종가 기준 판단자료와 갱신 주기가 다릅니다. 새 판단자료 수집 시각은 첫 화면 및 기업 분석에서 별도로 확인하세요.</p>';
 $('#view-monitor').prepend(fold);fold.append(legacyStatus);
 const oldAudit=$('#officialAuditStatus');if(oldAudit)fold.append(oldAudit);
}
const historicalPanel=$('#detail');
if(historicalPanel){
 const fold=document.createElement('details');fold.className='dv7-details';
 fold.innerHTML='<summary>과거 확정 재무 수치 펼치기</summary>';
 historicalPanel.parentElement.insertBefore(fold,historicalPanel);fold.append(historicalPanel);
}
const overview=$('#view-overview'),table=$('#tableWrap');
if(overview&&table){
 const fold=document.createElement('details');fold.className='dv7-details';
 fold.innerHTML='<summary>기존 연간 재무 지표 전체 비교</summary>';
 overview.insertBefore(fold,table);
 for(const el of [...overview.querySelectorAll(':scope > .toolbar-label,:scope > .tool,:scope > #tableWrap,:scope > .table-bottom')])fold.append(el);
}
'''
 code=code.replace(anchor,patch+'\n'+anchor,1)
js.write_text(code,encoding='utf-8')
print('v7.2 installed; no raw financial values or training files modified')
