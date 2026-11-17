const assert=require('node:assert/strict');
const {render}=require('../assets/stock-corporate-actions.js');
assert.match(render(null),/자료 없음은 위험 없음이 아닙니다/);
const html=render({filings:{coverage:{complete:true},items:[{title:'<script>bad</script>',source_url:'javascript:alert(1)',amendment:true,semantic_status:'not_parsed'}]},analyses:[{kind:'contract',assessment:'<img onerror=x>',status:'partial',metrics:{contract_amount:null},notes:['<b>x</b>'],source_urls:['https://www.sec.gov/x?token=secret','https://www.sec.gov/Archives/x.htm'],unknowns:['미확인']}]});
assert.ok(!html.includes('<script>'));assert.ok(!html.includes('javascript:'));assert.ok(!html.includes('token=secret'));assert.ok(html.includes('&lt;img'));assert.ok(html.includes('미확인'));assert.ok(html.includes('[정정]'));assert.ok(html.includes('원문 분석 미완료'));assert.ok(html.includes('rel="noopener noreferrer"'));console.log('9 renderer assertions passed');
