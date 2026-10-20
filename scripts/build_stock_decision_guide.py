"""Build a macro-to-company decision path without changing the existing verdict."""
from __future__ import annotations
import hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
NOW=datetime.now(timezone.utc)

def read(name,default):
 try:return json.loads(Path(name).read_text())
 except (OSError,ValueError):return default

def num(x):
 if isinstance(x,bool):return None
 try:
  n=float(x);return n if math.isfinite(n) else None
 except (ValueError,TypeError):return None

def pct(x):return f'{x:+.1f}%' if num(x) is not None else '자료 없음'
def term(name,meaning,value=None,reading=None,status='info',source=None):return {'term':name,'meaning':meaning,'value':value,'reading':reading,'status':status,'source_url':source}
BUSINESS=[
 (('반도체','semiconductor','전자부품'),('반도체·장비·소재를 고객사에 판매해 돈을 버는 구조예요.','출하량·판매단가·고객 설비투자·재고 사이클','수율·가동률·원재료·고정비·CAPEX','HBM·AI·자동차 등 실제 수요가 일시적인지, 고객이 누구인지 확인')),
 (('software','소프트웨어','cloud','클라우드','플랫폼','internet'),('구독료·클라우드 사용료·광고·중개수수료 등 디지털 서비스를 팔아 돈을 버는 구조예요.','사용자 수·구독 유지율·사용량·광고 경기·가격 인상','서버·AI CAPEX·인건비·마케팅비','사용자 증가가 실제 매출과 현금으로 이어지는지 확인')),
 (('bio','바이오','medical','의료','제약'),('의약품·의료기기·임상·위탁생산 서비스를 판매해 돈을 버는 구조예요.','수주·허가·제품 채택·공장 가동률·임상 진행','연구개발비·품질관리·생산수율·설비투자','허가·임상·품질 문제와 특정 고객 의존도를 확인')),
 (('auto','자동차','vehicle','부품'),('자동차·부품·관련 서비스를 판매해 돈을 버는 구조예요.','판매량·평균판매가격·신차 출시·환율','원재료·인센티브·공장 가동률·보증비','가격 인하로 판매량만 늘고 이익률은 나빠지는지 확인')),
 (('food','식품','consumer','소비재','apparel','신발','화장품'),('소비자에게 제품을 판매해 돈을 버는 구조예요.','판매량·가격·브랜드력·유통채널·해외 매출','원재료·물류비·광고비·환율','가격 인상이 물량 감소로 이어지는지, 재고가 쌓이는지 확인')),
 (('energy','에너지','oil','정유','화학'),('에너지·원재료를 생산하거나 가공해 판매하는 구조예요.','원자재 가격·정제마진·생산량·수요 사이클','원재료·설비보수·환경규제·CAPEX','상품가격 상승 덕인지 본업 경쟁력 개선인지 구분')),
 (('industrial','산업','기계','전력','전기장비','construction','건설'),('기업 고객에게 장비·부품·설비·공사를 판매해 돈을 버는 구조예요.','수주잔고·납품량·고객 CAPEX·프로젝트 진행률','원재료·납기·인건비·공장 가동률','수주가 실제 매출·현금으로 바뀌는 속도를 확인'))]

def business_profile(row):
 b=row.get('business') or {};hay=' '.join(str(x or '') for x in (row.get('sector'),b.get('sector'),b.get('industry'))).lower();profile=('제품·서비스를 고객에게 판매해 돈을 버는 구조예요.','판매량·가격·고객 수요','원가·인건비·투자비','공식 사업보고서에서 주요 제품·고객·원재료를 확인')
 for keys,value in BUSINESS:
  if any(k.lower() in hay for k in keys):profile=value;break
 return {'term':'사업구조','meaning':'이 회사가 누구에게 무엇을 팔아 돈을 버는지','sentence':f"{row.get('name')}은(는) {profile[0]} 매출은 {profile[1]}에, 이익은 {profile[2]}에 크게 영향을 받을 수 있어요.",'revenue_drivers':profile[1],'profit_drivers':profile[2],'check':profile[3],'basis':'업종·산업분류로 만든 일반 설명이에요. 회사별 제품·고객 비중은 공식 사업보고서에서 확인해야 해요.','source_url':(row.get('sources') or {}).get('profile') or (row.get('sources') or {}).get('official')}

def cash_reading(row):
 h=row.get('history') or {};items=[];flags=list(h.get('quality_flags') or []);ni=num(h.get('net_income'));cfo=num(h.get('cfo'));capex=num(h.get('capex'));fcf=num(h.get('fcf'));ratio=num(h.get('cfo_to_net_income'));src=row.get('sources') or {}
 if ni is not None and cfo is not None:
  ok=ni>0 and cfo>0 and (ratio is None or ratio>=.7);items.append(term('영업현금흐름(CFO)','본업에서 실제로 들어오고 나간 현금',cfo,'순이익이 실제 영업현금으로 잘 들어오는 편이에요.' if ok else '순이익과 영업현금흐름의 차이를 확인해야 해요.','good' if ok else 'caution',src.get('cashflow')))
 items.append(term('자본적지출(CAPEX)','공장·장비·시스템 등에 쓴 투자비',capex,'투자비가 늘었다면 무엇을 짓고 언제 돈을 벌기 시작하는지 확인해요.','info',src.get('cashflow')))
 items.append(term('FCF(잉여현금흐름)','영업현금흐름에서 CAPEX를 뺀 돈',fcf,'설비투자 후에도 현금이 남았어요.' if fcf is not None and fcf>0 else '투자 후 현금이 남지 않았어요. 성장투자인지 현금 부족인지 확인해요.','good' if fcf is not None and fcf>0 else 'caution',src.get('cashflow')))
 rg=num(h.get('revenue_growth'));ar=num(h.get('accounts_receivable_growth'));inv=num(h.get('inventory_growth'))
 items.append(term('매출채권','외상으로 팔고 아직 받지 못한 돈',h.get('accounts_receivable'),('매출채권 증가율 '+pct(ar)+' / 매출 성장률 '+pct(rg)) if ar is not None else '자료가 없어요.','caution' if ar is not None and rg is not None and ar-rg>10 else 'info',src.get('balance')))
 items.append(term('재고자산','아직 팔리지 않고 쌓여 있는 제품·원재료',h.get('inventory'),('재고 증가율 '+pct(inv)+' / 매출 성장률 '+pct(rg)) if inv is not None else '자료가 없어요.','caution' if inv is not None and rg is not None and inv-rg>10 else 'info',src.get('balance')))
 return {'items':items,'flags':flags}

def valuation_reading(row,case):
 v=row.get('valuation') or {};h=row.get('history') or {};peer=case.get('peer_context') or {};src=row.get('sources') or {};trailing=num(v.get('trailing_pe'));forward=num(v.get('forward_pe')) or num((row.get('forecasts') or {}).get('next_fy_pe'));pbr=num(v.get('price_to_book'));roe=num(v.get('return_on_equity_pct')) or num(h.get('roe'))
 items=[term('PER(주가수익비율)','주가가 1주당 이익의 몇 배인지',trailing,'낮다고 무조건 싼 주식은 아니에요. 이익이 줄어들 것으로 예상되면 낮아질 수 있어요.','info',src.get('estimates')),term('예상 PER','주가가 앞으로의 예상 EPS의 몇 배인지',forward,('같은 업종 예상 PER 중앙값 '+f"{peer.get('median'):.1f}배" if num(peer.get('median')) is not None else '같은 업종 비교자료가 부족해요.'),'info',src.get('estimates')),term('PBR(주가순자산비율)','주가가 장부상 주주 몫의 몇 배인지',pbr,'PBR만 낮으면 싸다고 보지 말고 ROE와 함께 봐요.','info',src.get('balance')),term('ROE(자기자본이익률)','주주 몫의 자본으로 얼마나 잘 벌었는지',roe,'자기자본 100원으로 순이익 약 '+f'{roe:.1f}원'+'을 낸 셈이에요.' if roe is not None else '같은 주주범위의 순이익·자기자본 자료가 필요해요.','good' if roe is not None and roe>=15 else 'info',src.get('balance'))]
 warnings=[]
 if roe is not None and roe>=20 and num(h.get('equity_growth')) is not None and h['equity_growth']<0:warnings.append('ROE가 높지만 자기자본이 줄어 올라간 것인지 확인해야 해요.')
 if pbr is not None and pbr<1 and (roe is None or roe<5):warnings.append('PBR이 낮아도 ROE가 낮으면 자산을 잘 활용하지 못하는 가치함정일 수 있어요.')
 if num(h.get('eps')) is not None and h['eps']<=0:warnings.append('적자기업의 음수 PER은 싸다는 뜻이 아니에요.')
 return {'items':items,'warnings':warnings,'historical_per':{'status':'not_connected','reading':'과거 PER 범위는 아직 자동 연결하지 않았어요. 현재는 같은 업종 예상 PER과 과거 실적을 함께 봐요.'}}

def macro_exposure(row,macro):
 i=macro.get('indicators') or {};interp=macro.get('interpretation') or {};sector=str(row.get('sector') or '').lower();lev=num((row.get('balance') or {}).get('net_debt_ebitda'));notes=[];ten=num((i.get('us_10y') or {}).get('value'));fx=num((i.get('usdkrw') or {}).get('change_20_sessions_pct'))
 if any(k in sector for k in ('소프트웨어','플랫폼','바이오','ai','반도체')) and ten is not None and ten>=4.5:notes.append('장기금리가 높아 먼 미래 이익을 크게 기대하는 성장주의 PER에는 부담이 될 수 있어요.')
 if lev is not None and lev>1 and ten is not None and ten>=4.5:notes.append('빚이 있는 기업은 높은 금리가 이자·차환 부담으로 이어질 수 있어요.')
 if row.get('market')=='KR' and fx is not None:notes.append('원/달러 환율 변화가 매출과 원가에 어떻게 작용하는지는 수출 매출 통화와 수입 원가 통화를 확인해야 해요.')
 if not notes:notes.append('현재 거시환경이 이 기업에 유리한지 단정할 자료가 부족해요. 금리 민감도와 매출·비용 통화를 확인하세요.')
 return {'term':'거시환경','meaning':'금리·국채금리·환율이 이 기업의 돈 조달과 가치평가에 주는 영향','market_label':interp.get('label'),'notes':notes,'not_causality':interp.get('not_causality'),'sources':[x.get('source_url') for x in (i.get('fed_policy',{}),i.get('us_10y',{}),i.get('usdkrw',{})) if x.get('source_url')]}

def basis_checks(row,case):
 h=row.get('history') or {};f=row.get('forecasts') or {};proof=case.get('official_comparison') or [];basis=str(h.get('basis') or '')
 return [{'term':'연결·별도','meaning':'연결은 자회사 포함, 별도는 해당 법인만','value':'연결(CFS)' if any(x.get('basis')=='CFS' for x in proof) or '연결' in basis else '개별·별도 또는 미확인','check':'올해와 지난해를 같은 범위로 비교했는지 확인'},{'term':'분기·누적','meaning':'3개월 실적과 연초부터 누적 실적을 구분','value':'연간 '+str(h.get('filing_period') or '미확인'),'check':'6개월·9개월 누적을 1년 실적과 바로 비교하지 않기'},{'term':'실적·예상','meaning':'A는 이미 발표된 실적, E는 앞으로의 예상','value':'과거 EPS '+str(h.get('eps') if h.get('eps') is not None else '미확인')+' / 다음 FY 예상 EPS '+str((f.get('next_fy') or {}).get('avg') if (f.get('next_fy') or {}).get('avg') is not None else '미확인'),'check':'예상 PER은 예상 EPS가 바뀌면 같이 바뀜'},{'term':'주가 기준일','meaning':'어느 날의 가격으로 계산했는지','value':str(row.get('price_session') or '미확인')+' 장 마감 가격','check':'실시간 주문가격과 다를 수 있음'},{'term':'적자·자기자본 음수','meaning':'일반 PER·PBR·ROE가 잘 작동하지 않는 경우','value':'과거 EPS '+('0 이하' if num(h.get('eps')) is not None and h['eps']<=0 else '양수 또는 미확인')+' / 자기자본 '+('0 이하' if num(h.get('equity')) is not None and h['equity']<=0 else '양수 또는 미확인'),'check':'음수 PER을 싸다고 해석하지 않기'}]

def main():
 raw=Path('stock-opportunity-data.json').read_bytes();op=json.loads(raw);cases=read('stock-investment-cases.json',{});macro=read('stock-market-context.json',{});case_by={x['symbol']:x for x in cases.get('companies',[])};companies=[]
 for row in op.get('companies',[]):
  case=case_by.get(row.get('symbol'),{});h=row.get('history') or {};cash=cash_reading(row);valuation=valuation_reading(row,case);src=row.get('sources') or {}
  companies.append({'symbol':row.get('symbol'),'name':row.get('name'),'source_symbol':row.get('source_symbol'),'currency':row.get('currency'),'market':row.get('market'),'sector':row.get('sector'),'generated_from':op.get('generated_at'),'case_state':case.get('state'),'case_label':case.get('label'),'business':business_profile(row),'macro':macro_exposure(row,macro),'performance':{'revenue':term('매출액','물건·서비스를 팔아 올린 총금액',h.get('revenue'),'전년보다 '+pct(h.get('revenue_growth')),'good' if num(h.get('revenue_growth')) is not None and h['revenue_growth']>0 else 'caution',src.get('official')),'operating_income':term('영업이익','본업 비용을 빼고 남은 이익',h.get('operating_income'),'영업이익률 '+pct(h.get('operating_margin')),'good' if num(h.get('operating_income')) is not None and h['operating_income']>0 else 'caution',src.get('official')),'net_income':term('순이익','이자·세금 등까지 모두 빼고 남은 최종 이익',h.get('net_income'),'전년보다 '+pct(h.get('net_income_growth')),'good' if num(h.get('net_income')) is not None and h['net_income']>0 else 'caution',src.get('official')),'growth_cause_check':'얼마나 늘었는지뿐 아니라 판매량·가격·환율·일회성 이익 중 무엇 때문인지 사업보고서에서 확인해요.'},'cashflow':cash,'debt':term('순차입금/EBITDA','차입금에서 현금을 뺀 금액이 현금창출력의 몇 배인지',(row.get('balance') or {}).get('net_debt_ebitda'),(row.get('balance') or {}).get('basis'),'good' if num((row.get('balance') or {}).get('net_debt_ebitda')) is not None and row['balance']['net_debt_ebitda']<=1 else 'caution',src.get('balance')),'valuation':valuation,'expectations':{'eps_growth':term('예상 EPS 성장률','앞으로 주식 1주당 이익이 얼마나 늘거나 줄지에 대한 예상',(row.get('forecasts') or {}).get('eps_growth_next_fy_pct'),'한 달 전보다 예상이 '+pct((row.get('forecasts') or {}).get('eps_revision30_pct')),'good' if num((row.get('forecasts') or {}).get('eps_growth_next_fy_pct')) is not None and row['forecasts']['eps_growth_next_fy_pct']>0 else 'caution',src.get('estimates')),'price_expectation':term('목표가 중앙값','전문가 목표가격을 낮은 순서로 놓은 가운데 값',(row.get('targets') or {}).get('median'),'현재 가격과 차이 '+pct((row.get('targets') or {}).get('median_gap_pct'))+'. 실제 도달 보장은 없어요.','info',src.get('estimates')),'actual_vs_expectation':'작년보다 좋아졌는지뿐 아니라 시장 예상보다 좋았는지, 다음 전망이 상향·하향됐는지 같이 봐요.'},'basis_checks':basis_checks(row,case),'final_questions':['이 회사의 이익이 앞으로 늘어날 수 있는 근거가 있나요?','이익이 실제 현금으로 들어오고, 재무구조가 버틸 수 있나요?','지금 주가에는 어느 정도 성장이 이미 반영돼 있나요?'],'one_sentence':f"{row.get('name')}은(는) {pct(h.get('revenue_growth'))} 매출 성장, {pct(h.get('operating_margin'))} 영업이익률, FCF {'양수' if num(h.get('fcf')) is not None and h['fcf']>0 else '비양수 또는 미확인'}예요. 성장 원인·현금 전환·현재 가격의 기대 수준을 순서대로 확인하세요.",'glossary_version':'1.0'})
 glossary=[['기준금리','중앙은행이 정하는 돈의 기본 가격'],['국채금리','정부가 돈을 빌릴 때 시장이 요구하는 금리'],['환율','1달러를 사는 데 필요한 원화'],['매출액','물건·서비스를 팔아 올린 총금액'],['영업이익','본업 비용을 빼고 남은 이익'],['순이익','이자·세금까지 빼고 남은 최종 이익'],['영업현금흐름(CFO)','본업에서 실제로 들어오고 나간 현금'],['자본적지출(CAPEX)','공장·장비·시스템 등에 쓴 투자비'],['FCF(잉여현금흐름)','CFO에서 CAPEX를 뺀 돈'],['EPS(주당순이익)','주식 1주당 순이익'],['PER','주가가 EPS의 몇 배인지'],['PBR','주가가 장부상 1주당 주주 몫의 몇 배인지'],['ROE','주주 자본 100원으로 순이익을 몇 원 냈는지']]
 out={'version':'decision-guide-1.0','generated_at':NOW.isoformat(),'source_generated_at':op.get('generated_at'),'case_generated_at':cases.get('generated_at'),'macro_generated_at':macro.get('generated_at'),'source_sha256':hashlib.sha256(raw).hexdigest(),'companies':companies,'glossary':[{'term':x,'meaning':y} for x,y in glossary],'scope':'현재 수집된 숫자를 금리→사업구조→실적→현금·부채→가치평가→예상 순서로 재배치한 학습·판단 보조자료. 기존 투자판정은 변경하지 않음.','warnings':['과거 PER 범위는 아직 자동 연결하지 않았어요.','환율 영향은 기업별 매출·비용 통화가 확인되지 않으면 방향을 단정하지 않아요.','PER·PBR·ROE는 같은 업종·같은 기간·같은 주주 범위로 비교해야 해요.']}
 Path('stock-decision-guide.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n');Path('stock-decision-guide-summary.json').write_text(json.dumps({'generated_at':out['generated_at'],'source_generated_at':out['source_generated_at'],'companies':len(companies),'macro_status':macro.get('status'),'glossary_terms':len(glossary)},ensure_ascii=False,indent=2)+'\n')
 print('decision guide',len(companies),'companies')
 if len(companies)!=len(op.get('companies',[])):raise SystemExit('기업 수 불일치')
if __name__=='__main__':main()
