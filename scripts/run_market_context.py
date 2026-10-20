"""Run the macro collector with a year-aware Federal Reserve table adapter."""
from __future__ import annotations
import re
from datetime import datetime
from bs4 import BeautifulSoup
try:
    from . import update_market_context as base
except ImportError:
    import update_market_context as base


def parse_fed_funds(html, year=None):
    soup=BeautifulSoup(html,'html.parser');rows=[]
    for table in soup.find_all('table'):
        table_year=None
        for node in table.find_all_previous(['h1','h2','h3','h4','h5','h6','p','div'],limit=35):
            text=re.sub(r'\s+',' ',node.get_text(' ',strip=True))
            match=re.fullmatch(r'(20\d{2})',text) or re.search(r'(?:^|\s)(20\d{2})(?:\s|$)',text)
            if match:
                table_year=int(match.group(1));break
        table_year=table_year or year
        if table_year is None:continue
        for tr in table.find_all('tr'):
            cells=[re.sub(r'\s+',' ',x.get_text(' ',strip=True)) for x in tr.find_all(['th','td'])]
            if len(cells)<4:continue
            level=next((x for x in reversed(cells) if re.fullmatch(r'\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?',x)),None)
            date=next((x for x in cells if re.fullmatch(r'[A-Za-z]+\s+\d{1,2}',x)),None)
            if not level or not date:continue
            lo,hi=[float(x) for x in re.split(r'[-–]',level)]
            numeric=[base.num(x) for x in cells[1:-1] if base.num(x) is not None]
            increase=numeric[0] if numeric else 0;decrease=numeric[1] if len(numeric)>1 else 0
            try:day=datetime.strptime(f'{date} {table_year}','%B %d %Y').date()
            except ValueError:continue
            if year is None and day>base.NOW.date():continue
            rows.append({'date':day.isoformat(),'low':lo,'high':hi,'increase_bp':increase or 0,'decrease_bp':decrease or 0})
    if not rows:raise ValueError('fed_rate_table_not_found')
    latest=max(rows,key=lambda x:x['date']);latest['direction']='인상' if latest['increase_bp'] else '인하' if latest['decrease_bp'] else '유지';latest['source_url']=base.FED_URL;latest['basis']='FOMC 목표금리 범위와 해당 회의의 인상·인하 폭; 연도별 표 제목을 함께 확인'
    return latest

base.parse_fed_funds=parse_fed_funds

if __name__=='__main__':base.main()
