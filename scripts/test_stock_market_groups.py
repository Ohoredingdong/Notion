import unittest,io,zipfile
from datetime import datetime,timezone
import update_stock_market_groups as m

class Groups(unittest.TestCase):
 def test_kospi(self):self.assertEqual(m.classify({'market':'KR','source_symbol':'005930.KS'}, {}, {})[0],'KOSPI')
 def test_kosdaq(self):self.assertEqual(m.classify({'market':'KR','source_symbol':'058470.KQ'}, {}, {})[0],'KOSDAQ')
 def test_korean_conflict(self):self.assertEqual(m.classify({'market':'KR','source_symbol':'058470.KQ','exchange':'KSC'}, {}, {})[0],'UNKNOWN')
 def test_nasdaq(self):self.assertEqual(m.classify({'market':'US','symbol':'TEST'}, {'TEST':'NASDAQ'}, {})[0],'NASDAQ')
 def test_nyse_not_dow(self):self.assertEqual(m.classify({'market':'US','symbol':'TEST'}, {'TEST':'NYSE'}, {})[0],'NYSE')
 def test_no_name_guess(self):self.assertEqual(m.classify({'market':'US','symbol':'TECHAI'}, {}, {})[0],'UNKNOWN')
 def test_provider_fallback(self):self.assertEqual(m.classify({'market':'US','symbol':'TEST'}, {}, {'TEST':{'exchange':'NMS'}})[0],'NASDAQ')
 def test_directory(self):
  stamp=m.NOW.strftime('%m%d%Y')
  body=('Symbol|Security Name|Test Issue\nTEST|Test Corp|N\nBAD|Test security|Y\nFile Creation Time: '+stamp+'12:00||\n').encode()
  rows,day=m.directory(body,'nasdaq');self.assertEqual(rows,{'TEST':'NASDAQ'})
 def test_stale_directory(self):
  with self.assertRaises(ValueError):m.directory(b'Symbol|Test Issue\nTEST|N\nFile Creation Time: 0101202012:00|\n','nasdaq')
 def workbook(self,n=30):
  def cell(col,value):return '<c r="'+col+'" t="inlineStr"><is><t>'+value+'</t></is></c>'
  rows=['<row>'+cell('A1','SPDR Dow Jones Industrial Average ETF Trust')+'</row>','<row>'+cell('A2','As of Date')+cell('B2',m.NOW.date().isoformat())+'</row>','<row>'+cell('A3','Name')+cell('B3','Ticker')+'</row>']
  for i in range(n):rows.append('<row>'+cell('A'+str(i+4),'Company '+str(i))+cell('B'+str(i+4),'TEST'+str(i))+'</row>')
  xml='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(rows)+'</sheetData></worksheet>'
  buffer=io.BytesIO()
  with zipfile.ZipFile(buffer,'w') as z:z.writestr('xl/worksheets/sheet1.xml',xml)
  return buffer.getvalue()
 def test_full_membership(self):self.assertEqual(len(m.holdings(self.workbook())[0]),30)
 def test_partial_is_not_complete(self):
  with self.assertRaises(ValueError):m.holdings(self.workbook(10))
 def test_not_membership_by_exchange(self):
  # Membership is deliberately absent from classify(): listing never implies an index.
  self.assertEqual(len(m.classify({'market':'US','symbol':'TEST'},{'TEST':'NASDAQ'},{})),3)

if __name__=='__main__':unittest.main(verbosity=2)
