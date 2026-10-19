"""Run audit with tested annual-table adapters and short-lived public fixtures."""
from pathlib import Path
import json
import stock_official_audit as audit
import stock_audit_adapters

stock_audit_adapters.install()
original=audit.Client.fetch
store=Path('audit-source-fixtures')
store.mkdir(exist_ok=True)
seen={}
def recording(self,url,params=None):
 result=original(self,url,params)
 body,charset,meta=result
 if 'corpCode' not in url:
  name=meta['sha256']+'.'+('json' if '.json' in url else 'html')
  (store/name).write_bytes(body)
  seen[url]={'file':name,'charset':charset,'meta':meta}
  (store/'index.json').write_text(json.dumps(seen,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return result

audit.Client.fetch=recording
if __name__=='__main__':audit.main()
