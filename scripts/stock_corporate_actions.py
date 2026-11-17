"""Research-only official filing index and evidence-bound corporate-action analysis.
No buy signal, inferred event facts or secret-bearing URLs are emitted. Listing
coverage is distinct from source-document/semantic analysis coverage.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

VERSION = 'corporate-actions-evidence-1'
OFFICIAL_HOSTS = {'dart.fss.or.kr', 'opendart.fss.or.kr', 'kind.krx.co.kr', 'www.sec.gov', 'sec.gov', 'data.sec.gov'}
KINDS = ('contract', 'convertible', 'buyback', 'reorganization')

def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = float(str(value).replace(',', '').strip())
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None

def day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None

def official_url(value):
    try:
        u = urlparse(str(value))
        return u.scheme == 'https' and u.hostname in OFFICIAL_HOSTS and not u.username and not u.password and not re.search(r'(key|token|secret)=', u.query, re.I)
    except ValueError:
        return False

def fact(record, key, missing):
    """Only consume fields with a specific official-document evidence reference."""
    evidence = record.get('evidence', {}).get(key, {})
    if not (official_url(evidence.get('url')) and str(evidence.get('locator') or '').strip() and
            evidence.get('symbol') == record.get('symbol') and bool(record.get('symbol'))):
        missing.append(key + ':공식 원문 위치 미확인')
        return None
    value = record.get('facts', {}).get(key)
    if value is None or value == '':
        missing.append(key + ':값 미확인')
        return None
    return value

def numeric(record, key, missing, positive=False):
    value = number(fact(record, key, missing))
    if value is None or (positive and value <= 0):
        missing.append(key + ':유효한 수치 필요')
        return None
    return value

def ratio(a, b):
    return a / b * 100 if a is not None and b is not None and b > 0 else None

def analyze_contract(record):
    missing, notes = [], []
    amount = numeric(record, 'contract_amount', missing, True)
    revenue = numeric(record, 'prior_annual_revenue', missing, True)
    currencies = [fact(record, k, missing) for k in ('contract_currency', 'revenue_currency')]
    # Entity/consolidation bases must be explicitly comparable, not guessed.
    bases = [fact(record, k, missing) for k in ('contract_entity_basis', 'revenue_entity_basis')]
    comparable = all(currencies) and currencies[0] == currencies[1] and all(bases) and bases[0] == bases[1]
    if not comparable:
        missing.append('계약·연매출의 통화/기업범위 비교 불가')
    start = day(fact(record, 'start_date', missing))
    end = day(fact(record, 'end_date', missing))
    days = (end-start).days+1 if start and end and end >= start else None
    if days is None:
        missing.append('유효한 계약기간 미확인')
    pct = ratio(amount, revenue) if comparable else None
    annualized = pct * 365.25 / days if pct is not None and days else None
    status = fact(record, 'event_status', missing)
    margin = fact(record, 'profitability_assessment', missing)
    terms = fact(record, 'payment_terms', missing)
    cancellation = fact(record, 'termination_conditions', missing)
    deposit = fact(record, 'deposit_amount', [])  # Optional, never substitute total amount.
    if status in ('terminated', 'withdrawn'):
        notes.append('계약 종료/철회: 신규 수주 호재로 분류하지 않음')
    elif pct is not None:
        notes.append('계약 규모는 매출 대비 중요도이며 수익·현금유입·주가 상승을 뜻하지 않음')
    if days and days < 365:
        notes.append('단기 계약: 납기·생산능력·이행비용 확인 필요, 짧다고 자동 호재 아님')
    return {'metrics': {'contract_amount': amount, 'deposit_amount': number(deposit), 'revenue_ratio_pct': pct,
                        'contract_days': days, 'annualized_scale_pct': annualized},
            'assessment': '종료/철회' if status in ('terminated','withdrawn') else '규모 확인·사업영향 검토 필요',
            'unknowns': missing, 'notes': notes + ['연환산은 규모 비교용 단순 계산이며 실제 매출 인식 전망이 아님'],
            'context': {'profitability': margin, 'payment_terms': terms, 'termination_conditions': cancellation}}

def analyze_convertible(record, as_of):
    missing, notes = [], []
    kind = fact(record, 'instrument_type', missing)
    if kind not in ('CB', 'BW'):
        missing.append('CB/BW 종류 미확인')
    # BW debt redemption does not extinguish detached warrants. Use remaining right units.
    remaining = numeric(record, 'outstanding_conversion_principal' if kind == 'CB' else 'outstanding_exercise_amount', missing)
    price = numeric(record, 'current_conversion_price' if kind == 'CB' else 'current_exercise_price', missing, True)
    floor = numeric(record, 'adjustment_floor_price', missing, True)
    original = numeric(record, 'initial_price', missing, True)
    shares = numeric(record, 'shares_outstanding_ex_treasury', missing, True)
    cash_currency = fact(record, 'principal_currency', missing)
    price_currency = fact(record, 'conversion_price_currency', missing)
    if not cash_currency or cash_currency != price_currency:
        missing.append('원금·행사가격 통화 불일치/미확인'); remaining = None
    if remaining is not None and remaining < 0:
        missing.append('잔액 음수 오류'); remaining = None
    if floor is not None and price is not None and floor > price:
        missing.append('하한가격이 현재가격 초과: 정정·기업행위 확인'); floor = None
    current_new = remaining / price if remaining is not None and price else None
    floor_new = remaining / floor if remaining is not None and floor else None
    start = day(fact(record, 'exercise_start', missing)); end = day(fact(record, 'exercise_end', missing))
    valid_period = start and end and start <= end
    in_window = start <= as_of <= end if valid_period else None
    if not valid_period:
        missing.append('유효한 전환/행사기간 미확인')
    balance_date = day(fact(record, 'balance_as_of', missing))
    if not balance_date or balance_date > as_of:
        missing.append('잔액 기준일 미확인/미래일'); current_new = floor_new = None
    market_price = numeric(record, 'market_price', missing, True)
    market_currency = fact(record, 'market_price_currency', missing)
    price_date = day(fact(record, 'price_as_of', missing))
    premium = (market_price / price - 1)*100 if market_price and price and market_currency == price_currency and price_date == as_of else None
    if premium is None:
        missing.append('동일통화·판정일 현재가 미확인')
    if in_window and premium is not None and premium > 0:
        notes.append('전환/행사 기간 내 가격상 유인 존재. 실제 청구·매도 확률은 미산출')
    if floor and original:
        notes.append('리픽싱 하한비율이 낮을수록 잠재 발행물량이 증가할 수 있음')
    if kind == 'BW':
        notes.append('BW 잔존권리 기준: 사채 상환만으로 신주인수권 소멸을 가정하지 않음')
    return {'metrics': {'potential_new_shares_current': current_new, 'potential_new_shares_floor': floor_new,
                        'new_to_existing_pct': ratio(current_new, shares),
                        'fully_diluted_new_pct': ratio(current_new, shares+current_new) if shares is not None and current_new is not None else None,
                        'floor_to_initial_pct': ratio(floor, original), 'price_premium_pct': premium,
                        'exercise_window_open': in_window, 'balance_as_of': balance_date.isoformat() if balance_date else None},
            'assessment': '잠재희석·행사조건 검토', 'unknowns': missing, 'notes': notes,
            'conversion_probability': None, 'crash_probability': None}

def analyze_buyback(record):
    missing = []
    acquired = numeric(record, 'acquisition_completed_shares', missing)
    cancelled = numeric(record, 'cancellation_completed_shares', missing)
    purpose = fact(record, 'stated_purpose', missing)
    acquisition_status = fact(record, 'acquisition_status', missing)
    cancellation_status = fact(record, 'cancellation_status', missing)
    same_program = fact(record, 'same_program_confirmed', missing)
    both = bool(acquired is not None and acquired > 0 and cancelled is not None and cancelled > 0 and
                acquisition_status == 'completed' and cancellation_status == 'completed' and same_program is True)
    if (acquired is not None and acquired < 0) or (cancelled is not None and cancelled < 0):
        missing.append('취득/소각 주식수 음수 오류'); both = False
    if cancelled is not None and acquired is not None and cancelled > acquired and same_program is True:
        missing.append('동일 프로그램 소각량이 취득량 초과: 기존 보유분 범위 재확인'); both = False
    return {'metrics': {'acquired_shares': acquired, 'cancelled_shares': cancelled}, 'acquired_and_cancelled_confirmed': both,
            'assessment': '취득·소각 이행 확인' if both else '취득·소각 완료 근거 부족',
            'stated_purpose': purpose, 'unknowns': missing,
            'notes': ['취득/소각 결정과 실제 완료를 분리. 보상·처분·인수대가 활용 여부 별도 확인']}

def analyze_reorganization(record):
    missing = []
    values = {k:fact(record,k,missing) for k in ('transaction_type','event_status','stated_purpose','consideration',
                                                'financing','approvals','expected_closing','shareholder_effect')}
    return {'assessment':'공시된 거래조건·진행상태 확인', 'facts':values, 'unknowns':missing,
            'inferred_hidden_purpose':None, 'predicted_completion_probability':None,
            'notes':['공시 목적과 숨은 의도 추측을 분리. 인수/합병/분할 자체를 호재로 판정하지 않음',
                     '승인·자금조달·종결·통합비용·희석 조건이 충족되거나 바뀔 때 재평가']}

def analyze(record, as_of=None):
    as_of = as_of or date.today()
    kind = record.get('kind')
    if kind not in KINDS:
        raise ValueError('unsupported_event_kind')
    fn = {'contract':analyze_contract,'convertible':lambda r:analyze_convertible(r,as_of),
          'buyback':analyze_buyback,'reorganization':analyze_reorganization}[kind]
    result = fn(record)
    result['unknowns'] = sorted(set(result['unknowns']))
    lifecycle = record.get('filing_status')
    if lifecycle not in ('current','amended'):
        result['unknowns'].append('최신 정정/철회 상태 미확인 또는 비현재 자료')
        if 'acquired_and_cancelled_confirmed' in result:
            result['acquired_and_cancelled_confirmed'] = False
    result.update(event_id=record.get('event_id'), symbol=record.get('symbol'), kind=kind,
                  as_of=as_of.isoformat(), status='partial' if result['unknowns'] else 'evidence_bound',
                  filing_status=lifecycle, source_urls=sorted({e['url'] for e in record.get('evidence',{}).values() if official_url(e.get('url'))}),
                  buy_signal=False, purpose_inference=False)
    return result

# Read-only collectors. Never print exception details (URLs may contain a key).
def fetch_json(url, headers=None):
    try:
        with urlopen(Request(url, headers=headers or {'User-Agent':'StockResearch/1.0'}), timeout=20) as r:
            return json.loads(r.read(20_000_000))
    except Exception:
        raise ValueError('official_request_failed') from None

class DartIndex:
    def __init__(self, key, request=fetch_json, max_pages=100):
        self.key, self.request, self.max_pages = key, request, max_pages
    def collect(self, corp_code, start, end):
        if not re.fullmatch(r'\d{8}', str(corp_code)) or not re.fullmatch(r'\d{8}',start) or not re.fullmatch(r'\d{8}',end):
            raise ValueError('invalid_dart_identifier_or_date')
        items, seen, total, pages, error = [], set(), None, 0, None
        if not self.key:
            return {'status':'unavailable','error':'DART_API_KEY_missing','items':[], 'coverage':{'complete':False,'semantic_complete':False}}
        while pages < self.max_pages:
            query = urlencode({'crtfc_key':self.key,'corp_code':corp_code,'bgn_de':start,'end_de':end,
                               'last_reprt_at':'N','page_no':pages+1,'page_count':100})
            try:
                payload = self.request('https://opendart.fss.or.kr/api/list.json?'+query)
            except Exception:
                error='official_request_failed';break
            code = payload.get('status')
            if code == '013' and pages == 0:
                total = 0;break
            if code != '000':
                error = 'DART_'+str(code) if re.fullmatch(r'\d{3}',str(code)) else 'DART_invalid_status';break
            pages += 1
            count=number(payload.get('total_count'))
            if count is None or count < 0 or int(count)!=count:
                error='invalid_total_count';break
            if total is not None and total != int(count):
                error='index_changed_during_pagination';break
            total=int(count)
            rows=payload.get('list')
            if not isinstance(rows,list):error='invalid_list';break
            for row in rows:
                receipt=str(row.get('rcept_no',''))
                if str(row.get('corp_code')) != str(corp_code) or not re.fullmatch(r'\d{14}',receipt):
                    error='issuer_or_receipt_conflict';continue
                if receipt in seen:continue
                seen.add(receipt);title=str(row.get('report_nm') or '')
                items.append({'filing_id':receipt,'corp_code':corp_code,'title':title,'filed_on':row.get('rcept_dt'),
                              'source_url':'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+receipt,
                              'amendment': '정정' in title, 'withdrawal': '철회' in title,
                              'original_filing_id':None,'semantic_status':'not_parsed'})
            if error or len(items)>=total:break
            if not rows:error='empty_page_before_total';break
        complete=error is None and total is not None and len(items)==total
        return {'status':'ok' if complete else 'partial','items':items,'error':error,
                'coverage':{'complete':complete,'semantic_complete':False,'start':start,'end':end,'total_count':total,
                            'collected':len(items),'pages':pages,'amendments_included':True,
                            'note':'목록 수집 완료와 원문 분석 완료는 다름. 정정의 원본 연결은 원문 대조 필요'}}

def sec_items(payload):
    filings=payload.get('filings',{}).get('recent',payload)
    keys=('accessionNumber','filingDate','form','primaryDocument')
    if any(not isinstance(filings.get(k),list) for k in keys):raise ValueError('invalid_sec_columns')
    lengths={len(filings[k]) for k in keys}
    if len(lengths)!=1:raise ValueError('sec_column_length_mismatch')
    return [dict(zip(keys,values)) for values in zip(*(filings[k] for k in keys))]

def collect_sec(cik, user_agent, request=fetch_json, max_files=100):
    if not re.fullmatch(r'\d{1,10}',str(cik)):raise ValueError('invalid_cik')
    # SEC asks automated clients to identify themselves with a contact.
    contact = re.search(r'[A-Za-z0-9_.+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})', user_agent or '')
    if (not contact or contact.group(1).lower() in {'example.com','example.org','example.net'} or
            len(user_agent.replace(contact.group(0), '').strip(' ()<>/')) < 3):
        raise ValueError('SEC_USER_AGENT_contact_required')
    cik=str(cik).zfill(10);headers={'User-Agent':user_agent};items=[];error=None
    try:
        payload=request('https://data.sec.gov/submissions/CIK'+cik+'.json',headers)
        if str(payload.get('cik','')).lstrip('0')!=cik.lstrip('0'):raise ValueError('issuer_conflict')
        rows=sec_items(payload);files=payload.get('filings',{}).get('files',[])
        if not isinstance(files,list):raise ValueError('invalid_history_files')
        for f in files[:max_files]:
            name=f.get('name','')
            if not re.fullmatch(r'CIK'+cik+r'-submissions-\d+\.json',name):raise ValueError('invalid_history_file')
            time.sleep(.12)
            rows.extend(sec_items(request('https://data.sec.gov/submissions/'+name,headers)))
        seen=set()
        for row in rows:
            accession=row['accessionNumber'];document=row['primaryDocument']
            if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',str(accession)) or not re.fullmatch(r'[A-Za-z0-9_.-]+',str(document)):
                raise ValueError('invalid_filing_reference')
            if accession in seen:continue
            seen.add(accession)
            items.append({'filing_id':accession,'cik':cik,'title':row['form'],'filed_on':row['filingDate'],
                          'source_url':f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-","")}/{document}',
                          'amendment':str(row['form']).endswith('/A'),'original_filing_id':None,'semantic_status':'not_parsed'})
        complete=len(files)<=max_files
    except Exception:
        complete=False;error='SEC_index_incomplete'
    return {'status':'ok' if complete else 'partial','items':items,'error':error,
            'coverage':{'complete':complete,'semantic_complete':False,'collected':len(items),
                        'note':'SEC 공개 제출 이력. 비공개/미제출 정보 및 거래소 별도 공시 완전성 보장 아님'}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,help='JSON: companies [{symbol, market, corp_code/cik}], optional events')
    parser.add_argument('--output',default='stock-corporate-actions.json')
    parser.add_argument('--offline',action='store_true',help='Only analyze supplied evidence; do not claim filing coverage')
    args=parser.parse_args();data=json.loads(Path(args.input).read_text());key=os.getenv('DART_API_KEY','').strip()
    ua=os.getenv('SEC_USER_AGENT','').strip();now=datetime.now(timezone.utc);companies=[]
    for row in data.get('companies',[]):
        index={'status':'unavailable','items':[],'coverage':{'complete':False,'semantic_complete':False},'error':'offline_or_identifier_missing'}
        if not args.offline:
            if row.get('market')=='KR' and row.get('corp_code'):
                index=DartIndex(key).collect(row['corp_code'],data.get('start_date',f'{now.year}0101'),data.get('end_date',now.strftime('%Y%m%d')))
            elif row.get('market')=='US' and row.get('cik') and ua:
                index=collect_sec(row['cik'],ua)
        events=[analyze(e,now.date()) for e in data.get('events',[]) if e.get('symbol')==row.get('symbol')]
        companies.append({'symbol':row.get('symbol'),'filings':index,'analyses':events,
                          'no_events_is_not_no_risk':True,'semantic_analysis_count':len(events)})
    out={'version':VERSION,'generated_at':now.isoformat(),'research_only':True,'commercial_ready':False,
         'source_generated_at':data.get('generated_at'),'companies':companies,
         'scope':'공식 공시목록과 근거가 명시된 사건만 분석. 누락을 안전·호재·매수로 바꾸지 않음.'}
    text=json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if key and key in text:raise RuntimeError('secret_leakage_blocked')
    Path(args.output).write_text(text)
    print(json.dumps({'companies':len(companies),'complete_indexes':sum(c['filings']['coverage']['complete'] for c in companies)},ensure_ascii=False))
if __name__=='__main__':main()
