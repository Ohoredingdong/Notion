/* Strict gate presentation. Called by the existing renderer; no observer overlay. */
(()=>{'use strict';
const version='strict-green-1.0';
const ids=['inputs','official','cash_quality','working_capital','earnings_quality','debt','business','valuation','macro','governance','forecast','liquidity'];
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const money=(x,c)=>finite(x)?(c==='KRW'?Math.floor(x).toLocaleString('ko-KR')+'원':'$'+x.toLocaleString('en-US',{maximumFractionDigits:2})):'아직 계산하지 않았어요';
const date=s=>new Date(s||'').toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false});
const link=(url,label)=>{try{const u=new URL(url);if(u.protocol!=='https:'||['crtfc_key','token','api_key'].some(k=>u.searchParams.has(k)))return '';return '<a href="'+E(u.href)+'" target="_blank" rel="noopener noreferrer">'+E(label)+' ↗</a>'}catch{return ''}};
function normalise(c,r,d){if(!c)return null;const g=c.green_review,t=Date.now(),checked=Date.parse(g?.reviewed_at||''),expires=Date.parse(g?.valid_until||'');
 const aligned=g?.version===version&&g.source_generated_at===d.generated_at&&g.input_price===r.price&&g.input_price_session===r.price_session&&g.input_forecast_eps===(r.forecasts?.next_fy?.avg??null)&&Number.isFinite(checked)&&checked<=t+300000&&t-checked<=18*3600000&&Number.isFinite(expires)&&expires>t;
 const checks=Array.isArray(g?.checks)?g.checks:[];
 const all=aligned&&g.green_eligible===true&&checks.length===ids.length&&new Set(checks.map(x=>x.id)).size===ids.length&&ids.every(id=>checks.some(x=>x.id===id&&x.status==='pass'));
 if(c.state==='attractive'&&!all)return {...c,state:'conditional',label:'기존 긍정 평가 · 엄격 검증은 확인 전',confidence:'초록 기준 미충족',strict_ui_blocked:true,green_verified:false,missing:[...(c.missing||[]),'현재 자료에 대한 12개 엄격 검증이 완료되지 않았어요.']};
 if(g&&!aligned)return {...c,state:'insufficient',label:'새 자료로 엄격 검증을 다시 해야 해요',confidence:'검증 기한·입력값 불일치',strict_ui_blocked:true,green_verified:false,missing:[...(c.missing||[]),'엄격 검증 기록의 날짜나 입력값이 현재 자료와 맞지 않아요.']};
 const risks=[...(c.risks||[]).filter(x=>x.origin!=='strict_green'),...checks.filter(x=>x.status==='review').map(x=>({origin:'strict_green',type:'엄격 검증에서 확인한 신호',field:'strict_'+x.id,text:x.term+' → '+x.explanation,source_url:x.source_urls?.[0]}))];
 const missing=[...new Set([...(c.missing||[]),...checks.filter(x=>['missing','blocked'].includes(x.status)).map(x=>'엄격 검증: '+x.term+' → '+x.explanation)])];
 return {...c,risks,missing,green_verified:all,strict_ui_blocked:!g};
}
function description(c){if(!c?.green_review||c.strict_ui_blocked)return '기존 자료의 좋은 점과 엄격 검증 완료는 달라요. 현재 입력에 맞는 검증 기록이 없으면 초록색으로 표시하지 않아요.';
 const g=c.green_review;if(c.green_verified)return '명시한 12개 실사 조건을 통과했어요. 확인한 사실과 평가 가정을 공개하지만, 미래 수익이나 손실 한도를 보장하는 뜻은 아니에요.';
 const review=(g.checks||[]).filter(x=>x.status==='review');
 return '필수 12개 중 '+g.passed+'개를 확인했어요. '+(review.length?'위험 신호 '+review.length+'개는 원인 확인이 먼저예요.':'아직 확인하지 못한 항목이 남아 있어요. ')+'빠진 근거를 괜찮다고 가정하지 않아요.';
}
function panel(c,r){const g=c?.green_review;if(!g)return '<div class="sg-box"><b>엄격 검증 결과를 아직 받지 못했어요.</b><p>예전의 긍정 점수만으로 초록색을 붙이지 않아요.</p></div>';
 const statuses={pass:'확인',review:'위험 원인 확인',missing:'근거 부족',blocked:'기준 불일치'};const tasks=(g.checks||[]).filter(x=>x.status!=='pass');
 return '<section class="sg-box" aria-label="초록색 검증 기준"><div class="sg-title"><b>실사(Due diligence) · 핵심 검증</b><span>'+E(g.passed)+' / 12 확인</span></div><p>→ 가격만 보는 게 아니라 회사와 위험까지 확인하는 과정이에요.</p><p class="sg-disclaimer">초록색 = 명시한 검증 통과. <strong>수익 보장·상승확률·원금 안전 표시는 아니에요.</strong></p><div class="sg-tasks">'+tasks.slice(0,3).map(x=>'<div><strong>'+E(x.term)+'</strong><span>→ '+E(x.meaning)+'</span><p>'+E(x.explanation)+'</p>'+link(x.source_urls?.[0],'이 회사에서 확인할 원문')+'</div>').join('')+'</div><details><summary>12개 검증과 빠진 근거 모두 보기</summary><div class="details-inner">'+(g.checks||[]).map(x=>'<div class="sg-check"><span class="sg-status '+E(x.status)+'">'+E(statuses[x.status]||'미확인')+'</span><b>'+E(x.term)+'</b><span>→ '+E(x.meaning)+'</span><p>'+E(x.explanation)+'</p>'+(x.source_urls||[]).slice(0,2).map(u=>link(u,'자료 원문')).join(' ')+'</div>').join('')+'<p>확인 시각 '+E(date(g.reviewed_at))+' KST · 유효기한 '+E(date(g.valid_until))+' KST. 새 공시·주가·이익 전망이 반영되면 다시 검사해요.</p><p>30일·80%·10%p·20% 등의 문턱은 이 도구의 점검 정책이지 보편적인 회계기준이나 최적 투자법이 아니에요.</p><p>'+E(g.record_limit)+'</p></div></details><p class="sg-disclaimer">이 규칙의 실제 투자성과·백테스트는 아직 검증하지 않았어요. 과거 숫자가 맞는 것과 앞으로 돈을 버는 것은 별개예요.</p></section>';
}
function prices(r,c,compact=false){const g=c?.green_review,v=g?.valuation||{},valid=!c.strict_ui_blocked&&finite(v.reference_price)&&finite(r.price)&&r.price>0;
 const cell=(term,meaning,value,note)=>'<div class="plain-price-item"><span class="finance-term">'+E(term)+'</span><span class="finance-meaning">→ '+E(meaning)+'</span><strong>'+E(value)+'</strong><small>'+E(note)+'</small></div>';
 let body='<div class="plain-price-guide'+(compact?' compact':'')+'">'+cell('종가','이번 분석에 사용한 주가',money(r.price,r.currency),(r.price_session||'날짜 미확인')+' · 실시간 가격이 아니에요')+cell('애널리스트 목표가','전문가가 예상한 가격',money(r.targets?.median,r.currency),'의견의 중앙값 · 이 숫자만으로 초록을 주지 않아요')+cell('독립평가 매수 참고선','다른 방식으로도 계산했는지',valid?money(v.reference_price,r.currency)+' 이하':'평가 근거 확인 전','이익 가치와 주주 현금흐름 평가를 따로 확인해요')+'</div>';
 body+='<p class="plain-caution">예상 가격까지 안 오르거나 지금보다 떨어질 수 있어요. 검증이 끝나지 않은 참고선을 매수 지시로 표시하지 않아요.</p>';
 if(valid&&!compact)body+='<details><summary>가격·하락 시나리오 계산 확인</summary><div class="details-inner"><p>보수적 이익가치 '+E(money(v.conservative?.earnings_model,r.currency))+' / 주주 현금흐름 가치 '+E(money(v.conservative?.fcfe_model,r.currency))+'. 둘 중 낮은 값에서 20% 할인한 참고선이에요.</p><p>하락 가정의 가격 '+E(money(v.stress?.lower_value,r.currency))+' · 현재 대비 '+E(finite(v.stress_change_pct)?v.stress_change_pct.toFixed(1)+'%':'미확인')+'. <b>실제 손실은 이 가정보다 커질 수 있어요.</b></p><p>정상화 EPS → 일시적인 손익을 구분한 주당이익. FCFE → 빚과 관련된 현금까지 반영한 뒤 보통주 주주에게 남는 현금. 가정이 틀리면 평가도 바뀌어요.</p></div></details>';
 return body;
}
const style=document.createElement('style');style.textContent='.sg-box{border:1px solid var(--line);background:var(--soft);border-radius:15px;padding:17px;margin:16px 0}.sg-title{display:flex;gap:10px;justify-content:space-between;align-items:center}.sg-title b{font-size:13px}.sg-title span{font-size:11px;white-space:nowrap;color:var(--blue)}.sg-box p{font-size:12px!important;line-height:1.9!important}.sg-disclaimer{color:var(--muted)}.sg-tasks>div,.sg-check{padding:13px 0;border-top:1px solid var(--line);margin-top:10px}.sg-tasks strong,.sg-check>b{display:block;color:var(--blue);font-size:12px}.sg-tasks span,.sg-check>span:not(.sg-status){display:block;font-size:12px;margin:3px 0}.sg-tasks a,.sg-check a{font-size:11px}.sg-status{font-size:10px;display:inline-block;padding:3px 7px;background:var(--amber-soft);color:var(--amber);border-radius:6px;margin-bottom:6px}.sg-status.pass{background:var(--green-soft);color:var(--green)}.sg-status.blocked,.sg-status.review{background:var(--red-soft);color:var(--red)}.plain-price-item.buy{background:var(--soft)}@media(max-width:640px){.sg-box{padding:13px}.sg-title{align-items:flex-start}.sg-title b{font-size:12px}.sg-title span{font-size:10px}}';document.head.append(style);
window.StockGreenReview={version,ids,normalise,description,panel,prices};
})();
