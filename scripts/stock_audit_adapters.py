"""Strict table adapters tested against captured public statements; no embedded values."""
import re
from bs4 import BeautifulSoup
import stock_official_audit as a
base_compare=a.compare

def numeric_cells(cells):
 out=[];pending=False
 for raw in cells:
  text=re.sub(r'\s+','',raw).replace('$','').replace('₩','')
  if text.endswith('원'):text=text[:-1]
  if text in ('','(',')'):
   if text=='(':pending=True
   continue
  if text in ('—','–','-'):out.append(0.0);pending=False;continue
  if text.startswith('('):pending=True;text=text[1:]
  text=text.rstrip(')')
  if re.fullmatch(r'[-+−]?\d[\d,]*(?:\.\d+)?',text):
   value=a.num(text)
   if value is not None:out.append(-abs(value) if pending else value)
   pending=False
 return out

def from_release(body,target,cfg,record,spec):
 soup=BeautifulSoup(body,'html.parser');plain=a.compact(soup.get_text(' ',strip=True))
 if not any(a.compact(x) in plain[:60000] for x in cfg.get('aliases',[])):
  raise a.SourceError('issuer_mismatch','기업 공식 발표의 회사명이 다릅니다.')
 index=spec['index'];prior=spec['prior_index'];facts={};found={}
 names={k:list(v) for k,v in a.US_NAMES.items()}
 names['operating_cash_flow']+=['netcashfromoperations','netcashprovidedbyoperatingactivities']
 for table in soup.find_all('table'):
  rows=list(a.table_rows(table));header=a.compact(table.get_text(' ',strip=True))[:900]
  if any(x in header[:500] for x in ('non-gaap','asadjusted','segmentresults','segmentinformation','supplemental')):continue
  if not any(x in header for x in ('twelvemonthsended','yearended','yearsend','fiscalyearended')):continue
  if target[:4] not in header:continue
  before=a.compact(' '.join(table.find_all_previous(string=True,limit=30)))
  if 'million' not in header and 'million' not in before:continue
  labels={a.label(x[0]) for x in rows if len(x[0])<200}
  cf=any(x in labels for x in names['operating_cash_flow'])
  income=any(x in labels for x in names['revenue']) and any(x in labels for x in names['operating_income']) and ('incomestatements' in header or 'statementsofoperations' in header or 'statementsofincome' in header or 'totalcostofrevenue' in labels or 'costofsales' in labels)
  if not(cf or income):continue
  eps_context=False
  for raw,cells in rows:
   lab=a.label(raw)
   if len(lab)>220:continue
   if 'earningspershare' in lab or 'netincomepershare' in lab:eps_context=True
   if 'weightedaverage' in lab or 'sharesused' in lab:eps_context=False
   vals=numeric_cells(cells)
   if len(vals)!=max(index,prior)+1:continue
   for key,aliases in names.items():
    if lab not in aliases:continue
    if key=='eps' and lab=='diluted' and not eps_context:continue
    if key in ('ppe','operating_cash_flow') and not cf:continue
    if key not in ('ppe','operating_cash_flow') and not income:continue
    scale=1 if key=='eps' else 1000000
    x=a.fact(vals[index]*scale,raw,'USD/shares' if key=='eps' else 'USD',spec['period'],record,resolution=.01 if key=='eps' else scale)
    found.setdefault(key,[]).append(x)
    if key=='revenue':found.setdefault('revenue_previous',[]).append(a.fact(vals[prior]*scale,raw,'USD',str(int(spec['period'][:4])-1)+spec['period'][4:],record,resolution=scale))
 for key,xs in found.items():
  value=a.unique(xs)
  if value:facts[key]=value
 if not facts:raise a.SourceError('parse_error','GAAP 전체 연결재무제표의 연간 열을 식별하지 못했습니다.')
 a.derive(facts)
 return {'period':spec['period'],'kind':'기업 공식 실적발표 GAAP (최종 감사보고서 아님)','facts':facts,'document':record}

def from_kind(body,target,cfg,record,kind='kind_html'):
 soup=BeautifulSoup(body,'html.parser');plain=a.compact(soup.get_text(' ',strip=True))
 if not any(a.compact(x) in plain[:60000] for x in cfg.get('aliases',[])):
  raise a.SourceError('issuer_mismatch','공시에서 대상 회사명을 확인하지 못했습니다.')
 year=int(target[:4]);state=None;context={};buffer='';found={};attribution=None
 aliases={k:list(v) for k,v in a.KR_NAMES.items()}
 aliases['net_income']+=['지배기업의소유주지분','지배기업소유주지분순이익','지배기업소유주에게귀속되는당기순이익손실']
 aliases['eps']+=['희석주당이익손실','희석주당이익손실단위원','보통주희석주당이익손실','보통주희석주당이익손실단위원','희석주당이익단위원']
 for node in soup.find_all(['p','table','h1','h2','h3']):
  if node.find_parent('table') is not None:continue
  text=node.get_text(' ',strip=True);short=a.compact(text[:250])
  if any(w in short for w in ('연결자본변동표','연결재무제표주석','연결재무제표에대한주석')):state=None;context={}
  for title,newstate in [('연결포괄손익계산서','income'),('연결손익계산서','income'),('연결현금흐름표','cash'),('연결재무상태표','balance')]:
   if title in short:state=newstate;context={};attribution=None;buffer='';break
  else:
   if ('연결' not in short and any(w in short for w in ('포괄손익계산서','손익계산서','현금흐름표','재무상태표'))) or re.match(r'4[.．]재무제표',short):state=None
  if node.name!='table':buffer=(buffer+' '+text)[-2200:];continue
  n=a.compact(buffer+' '+text[:650])
  if re.search(r'단위[:：]?백만원',n):context['scale']=1000000
  elif re.search(r'단위[:：]?천원',n):context['scale']=1000
  elif re.search(r'단위[:：]?원',n):context['scale']=1
  if re.search(str(year)+r'(?:[.]0?1[.]0?1|년0?1월0?1일)',n):context['annual']=True
  if re.search(str(year)+r'(?:[.]12[.]31|년12월31일)',n):context['end']=True
  if state not in ('income','cash') or not all(context.get(k) for k in ('scale','annual','end')):
   if len(text)<700:buffer=(buffer+' '+text)[-2200:]
   continue
  rows=list(a.table_rows(node));note_column=any(a.label(raw)=='과목' and cells and a.label(cells[0])=='주석' for raw,cells in rows)
  for raw,cells in rows:
   lab=a.label(raw)
   if lab in ('당기순이익의귀속','당기순이익손실의귀속','연결당기순이익의귀속'):attribution='net'
   elif lab in ('총포괄이익의귀속','총포괄손익의귀속','포괄이익의귀속','포괄손익의귀속'):attribution='comprehensive'
   vals=numeric_cells(cells[1:] if note_column else cells)
   if not vals:continue
   for key,names in aliases.items():
    if lab not in names:continue
    if key=='net_income' and not any(w in lab for w in ('순이익','당기손익')) and attribution!='net':continue
    if (state=='cash')!=(key in ('operating_cash_flow','ppe','intangible')):continue
    scale=1 if key.startswith('eps') else context['scale']
    x=a.fact(vals[0]*scale,raw,'KRW/shares' if key.startswith('eps') else 'KRW',target,record,str(year)+'-01-01',scale)
    found.setdefault(key,[]).append(x)
    if key=='revenue' and len(vals)>1:found.setdefault('revenue_previous',[]).append(a.fact(vals[1]*scale,raw,'KRW',str(year-1)+'-12-31',record,str(year-1)+'-01-01',scale))
  if len(text)<700:buffer=(buffer+' '+text)[-2200:]
 facts={}
 for key,xs in found.items():
  x=a.unique(xs)
  if x:facts[key]=x
 if not facts:raise a.SourceError('parse_error','연결 재무표·계정·단위·연간기간 식별 실패; 추정하지 않음')
 a.derive(facts)
 return {'period':target,'start':str(year)+'-01-01','kind':'KIND 주총 참고서류의 재무표 (최종 감사보고서 아님)' if kind=='kind_proxy' else 'KIND 사업보고서 연결재무제표','facts':facts,'document':record}

def compare(row,source):
 fields=base_compare(row,source)
 for item in fields:
  # Preserve exact differences but avoid urgent alerts for insignificant provider truncation.
  if item['status']=='mismatch' and item.get('official_value') and abs(item.get('difference',0)/item['official_value'])<=1e-8:
   item.update(status='minor_difference',reason='원문과 매우 작은 금액 차이가 있습니다(0.000001% 이하). 제공처 표준화·절사 오차를 확인하세요. 완전 일치로 표시하지 않습니다.')
 return fields

def install():
 a.from_kind=from_kind;a.from_release=from_release;a.compare=compare
