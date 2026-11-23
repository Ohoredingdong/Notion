"""Normalize two licensed TWSE CSV files; does not fetch or publish.
Download #18419 and #11549 from the Taiwan Open Data catalog. Only the
public listing identity, official classification and validated close/turnover
are kept. No personal/contact fields, forecast or accounting inference.
"""
from __future__ import annotations
import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

SECTORS = {
 '01':'시멘트','02':'식품','03':'플라스틱','04':'섬유','05':'전기기계','06':'전선·케이블',
 '08':'유리·세라믹','09':'제지','10':'철강','11':'고무','12':'자동차','14':'건설·건자재',
 '15':'운송','16':'관광·숙박','17':'금융·보험','18':'유통·소비재','19':'종합','20':'기타',
 '21':'화학','22':'바이오·의료','23':'가스·전력','24':'반도체','25':'컴퓨터·주변기기',
 '26':'광전자','27':'통신·인터넷','28':'전자부품','29':'전자제품 유통','30':'정보서비스',
 '31':'기타 전자','35':'친환경 에너지·환경','36':'디지털·클라우드','37':'스포츠·레저','38':'주거·생활',
}
INDEX_NAMES=dict(zip(
 ['01','02','03','04','05','06','08','09','10','11','12','14','15','16','17','18','20','21','22','23','24','25','26','27','28','29','30','31','35','36','37','38'],
 ['水泥','食品','塑膠','紡織纖維','電機機械','電器電纜','玻璃陶瓷','造紙','鋼鐵','橡膠','汽車','建材營造','航運','觀光餐旅','金融保險','貿易百貨','其他','化學','生技醫療','油電燃氣','半導體','電腦及週邊設備','光電','通信網路','電子零組件','電子通路','資訊服務','其他電子','綠能環保','數位雲端','運動休閒','居家生活']))
INDEX_CODES={v+'類指數':k for k,v in INDEX_NAMES.items()}
COLUMNS = {'出表日期','公司代號','公司名稱','公司簡稱','產業別','英文簡稱'}
PRICE_COLUMNS = {'日期','證券代號','證券名稱','成交股數','成交金額','收盤價'}
CODES = re.compile(r'[0-9]{4}[A-Z]?')
ROOT = 'https://data.gov.tw/en/datasets/'
LICENSE = 'https://data.gov.tw/license'

def normalize_day(s):
    s = s.strip()
    if re.fullmatch(r'\d{7}', s):
        return date(int(s[:3])+1911,int(s[3:5]),int(s[5:])).isoformat()
    if re.fullmatch(r'\d{8}', s):
        return date(int(s[:4]),int(s[4:6]),int(s[6:])).isoformat()
    raise ValueError('unexpected TWSE date')

def read_csv(file, required):
    with file.open(encoding='utf-8-sig',newline='') as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('unexpected dataset columns')
        rows=list(reader)
        if any(None in r or any(r.get(k) is None for k in required) for r in rows):
            raise ValueError('truncated or overflowing row')
        return rows

def finite(s, *, integer=False):
    try:
        value=Decimal(s.strip().replace(',', ''))
        if not value.is_finite() or value<=0 or (integer and value!=value.to_integral_value()):
            return None
        out=int(value) if integer else float(value)
        if out > 10**15:
            return None
        return out
    except (InvalidOperation,ValueError,OverflowError):
        return None

def sector_index(path, expected):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        out={}
        for row in csv.DictReader(stream):
            name=row.get('指數/報酬指數') or ''
            code=INDEX_CODES.get(name)
            if not code: continue
            if code in out or normalize_day(row['日期'])!=expected:
                raise ValueError('duplicate or mismatched sector index')
            close=finite(row['收盤指數'])
            pct=float(Decimal(row['漲跌百分比(%)'].strip().replace(',', '')))
            sign=row['漲跌(+/-)'].strip()
            if close is None or not -100<pct<100 or (pct>0 and sign!='+') or (pct<0 and sign!='-'):
                raise ValueError('invalid official sector reading')
            out[code]={'label':name,'value':close,'change_pct':pct}
    if len(out)<30:
        raise ValueError('incomplete sector price index published table')
    return out

def build(catalog, prices, asof, minimum=900, sectors=None):
    companies=read_csv(catalog,COLUMNS)
    quotes=read_csv(prices,PRICE_COLUMNS)
    if len(companies)<minimum or len(quotes)<minimum:
        raise ValueError('incomplete dataset')
    catalogue_days={normalize_day(r['出表日期']) for r in companies}
    quote_days={normalize_day(r['日期']) for r in quotes}
    if len(catalogue_days)!=1 or len(quote_days)!=1 or max(catalogue_days|quote_days)>asof:
        raise ValueError('unknown or future session')
    listed_day=catalogue_days.pop();quote_day=quote_days.pop()
    lookup={}
    for row in quotes:
        k=row['證券代號'].strip()
        if k in lookup:
            raise ValueError('duplicate quote code')
        lookup[k]=row
    items=[]; seen=set()
    for row in companies:
        symbol=row['公司代號'].strip(); name=row['公司簡稱'].strip() or row['公司名稱'].strip()
        if row["產業別"].strip()=="91": continue  # Depository receipts, not TWSE common-company listings.
        abbr=row['英文簡稱'].strip(); full=row['公司名稱'].strip()
        if not CODES.fullmatch(symbol) or not name or symbol in seen:
            raise ValueError('invalid or duplicate listed identifier')
        seen.add(symbol); code=row['產業別'].strip().zfill(2)
        item={'symbol':symbol,'name':name,'aliases':list(dict.fromkeys(v for v in (abbr,full) if v and v!=name)),
              'industry_code':code,'sector':SECTORS.get(code,'업종 미확인')}
        q=lookup.get(symbol)
        # Exact short name agreement prevents many ticker collision errors.
        if q and q['證券名稱'].strip()==name:
            close=finite(q['收盤價'])
            if close is not None:
                item['price']=close
                item['turnover']=finite(q['成交金額'],integer=True)
        items.append(item)
    if len(seen)<minimum or sum('price' in x for x in items)<minimum*.85:
        raise ValueError('implausible verified overlap')
    items.sort(key=lambda r:r['symbol'])
    return {'country':'TW','name':'TWSE 상장기업 명부 · TDR·ETF 제외','coverage':'exchange', 'exchange':'TWSE',
            'listed_day':listed_day,'price_day':quote_day,'currency':'TWD','source_url':ROOT+'18419',
            'price_source_url':ROOT+'11549','license_url':LICENSE,
            'agency':'대만 금융감독위원회 증권선물국 / TWSE',
            'attribution':'대만 금융감독위원회 증권선물국 / TWSE (2026) · Basic information of listed companies (18419), Daily Trading Information of Listed Stocks (11549), Daily closing market information – Market statistics (11555). 대만 정부 개방 데이터 이용조건 v1.0에 따라 제공됩니다.',
            'sector_source_url':ROOT+'11555','sector_prices':sector_index(sectors,quote_day) if sectors else {},
            'classification_source_url':'https://twse-regulation.twse.com.tw/EN/law/DOC01.aspx?FLCODE=FL007104&FLNO=2',
            'items':items}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',type=Path,required=True)
    p.add_argument('--prices',type=Path,required=True)
    p.add_argument('--sectors',type=Path)
    p.add_argument('--asof',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();date.fromisoformat(a.asof)
    result=build(a.catalog,a.prices,a.asof,sectors=a.sectors)
    a.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
if __name__=='__main__': main()
