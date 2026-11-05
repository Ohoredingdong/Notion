'use strict';
/* Actual archived advanced-page entry-plan navigation. Offline checkout bytes,
   isolated browser contexts, no market collection, publisher or real order. */
const {chromium}=require('@playwright/test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const crypto=require('node:crypto');

const digest=value=>crypto.createHash('sha256').update(value).digest('hex');
function resolvePath(value){
 const result=path.resolve(value);
 return fs.existsSync(result)?fs.realpathSync(result):path.join(resolvePath(path.dirname(result)),path.basename(result));
}
function inside(root,file){const relative=path.relative(root,file);return !relative.startsWith('..'+path.sep)&&relative!=='..'&&!path.isAbsolute(relative);}
function args(values){
 const result={root:process.cwd(),output:'/tmp/notion-radar-entry',browserExecutable:process.env.NOTION_BROWSER_EXECUTABLE||process.env.BROWSER_EXECUTABLE};
 const names={'--root':'root','--output':'output','--browser-executable':'browserExecutable'};
 for(let index=0;index<values.length;index++){
  const flag=values[index];
  if(flag==='--help'){console.log('node tests/stock-entry-browser.cjs --root CHECKOUT --output EXTERNAL_DIR --browser-executable CHROMIUM');return null;}
  if(!names[flag]||!values[index+1]||values[index+1].startsWith('--'))throw new Error('Unknown or incomplete argument: '+flag);
  result[names[flag]]=values[++index];
 }
 result.root=resolvePath(result.root);result.output=resolvePath(result.output);
 if(inside(result.root,result.output))throw new Error('Keep browser artifacts outside the source checkout');
 return result;
}
function safeFile(root,name){
 const target=resolvePath(path.resolve(root,name));
 if(!inside(root,target))throw new Error('Requested file escapes the checkout: '+name);
 return target;
}
function sourceFiles(root){
 const html=fs.readFileSync(path.join(root,'stock-value-radar-advanced.html'),'utf8');
 const names=new Set(['stock-value-radar-advanced.html']);
 for(const match of html.matchAll(/<(?:script|link)\b[^>]*(?:src|href)=["']([^"']+)["']/g)){
  const url=new URL(match[1],'http://fixture/stock-value-radar-advanced.html');
  if(url.origin==='http://fixture')names.add(decodeURIComponent(url.pathname).replace(/^\/+/,''));
 }
 return Object.fromEntries([...names].sort().map(name=>[name,digest(fs.readFileSync(safeFile(root,name)))]));
}

async function main(){
 const options=args(process.argv.slice(2));if(!options)return 0;
 fs.mkdirSync(options.output,{recursive:true});
 const report={passed:false,scope:'Archived advanced entry-plan UI over exact captured checkout JSON. Isolated read-only browser examples; no live provider, broker, publication or deployment verification.',cases:[],blockedRequests:[],dataRequests:[],errors:[]};
 const captured=new Map();let server,browser;
 const data=name=>{
  if(!captured.has(name))captured.set(name,fs.readFileSync(safeFile(options.root,name)));
  return captured.get(name);
 };
 try{
  const raw=JSON.parse(data('stock-opportunity-data.json'));
  const plan=JSON.parse(data('stock-entry-plan-summary.json'));
  assert(Array.isArray(raw.companies)&&raw.companies.length,'Actual collected companies are required');
  assert.equal(plan.version,'entry-plan-1.1','Actual entry policy version');
  const clock=Math.max(Date.parse(raw.generated_at),Date.parse(plan.generated_at))+60000;
  assert(Number.isFinite(clock),'Captured generation times must be valid');
  report.clock=new Date(clock).toISOString();report.sourceFilesBefore=sourceFiles(options.root);
  const mime={'.html':'text/html; charset=utf-8','.js':'application/javascript','.css':'text/css','.json':'application/json','.jsonl':'application/x-ndjson','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon'};
  server=http.createServer((req,res)=>{
   try{
    if(!['GET','HEAD'].includes(req.method)){res.writeHead(405);res.end();return;}
    const name=decodeURIComponent(new URL(req.url,'http://fixture').pathname).replace(/^\/+/,''),file=safeFile(options.root,name);
    const value=/\.jsonl?$/.test(name)?data(name):fs.readFileSync(file);
    res.writeHead(200,{'Content-Type':mime[path.extname(name)]||'application/octet-stream','Content-Length':value.length});res.end(req.method==='HEAD'?undefined:value);
   }catch(error){res.writeHead(404,{'Content-Type':'text/plain'});res.end('Checkout resource unavailable');}
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const origin='http://127.0.0.1:'+server.address().port;
  const launch={headless:true};if(options.browserExecutable)launch.executablePath=options.browserExecutable;
  browser=await chromium.launch(launch);
  for(const width of [1280,390]){
   const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage();
   const errors=[];page.on('pageerror',error=>errors.push(error.message));
   const row={width,passed:false,errors,screenshots:[]};
   await page.clock.setFixedTime(new Date(clock));
   await page.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url());
    const local=url.origin===origin;
    const ownedRaw=url.origin==='https://raw.githubusercontent.com'&&url.pathname.startsWith('/Ohoredingdong/Notion/main/');
    if(!['GET','HEAD'].includes(request.method())||(!local&&!ownedRaw)){
     report.blockedRequests.push({url:url.origin+url.pathname,method:request.method()});await route.abort();return;
    }
    const name=local?decodeURIComponent(url.pathname).replace(/^\/+/, ''):decodeURIComponent(url.pathname.slice('/Ohoredingdong/Notion/main/'.length));
    if(/\.jsonl?$/.test(name)){
     try{
      const value=data(name);report.dataRequests.push({file:name,sha256:digest(value)});
      await route.fulfill({status:200,contentType:'application/json',headers:{'access-control-allow-origin':'*'},body:value});
     }catch(error){report.blockedRequests.push({url:url.pathname,reason:'Captured checkout data unavailable'});await route.abort();}
    }else if(local)await route.continue();
    else{report.blockedRequests.push({url:url.origin+url.pathname,reason:'Non-data external resource'});await route.abort();}
   });
   try{
    await page.goto(origin+'/stock-value-radar-advanced.html',{waitUntil:'domcontentloaded'});
    // This literal still matches the actual entry module. Do not weaken it to
    // hide a failed or missing data response.
    const neutral=page.locator('.nr-rail [data-nr-view="discover"]');
    if(await neutral.count()){await neutral.first().waitFor({timeout:45000});await neutral.first().click();}
    else if(await page.locator('#tab-discover').count())await page.locator('#tab-discover').click();
    await page.locator('.entry-tabs').waitFor({state:'visible',timeout:45000});
    assert.match(await page.locator('.rec-root h2').innerText(),/투자 조건과 진입 타이밍/);
    assert.match(await page.locator('.entry-badge').innerText(),/검증 단계/);
    assert.equal(await page.locator('.rec-root .rec-card,.rec-root .rec-real').count(),0);
    await page.locator('[data-entry-tab="market"]').click();
    assert.match(await page.locator('.rec-root').innerText(),/확률을 임의로/);
    await page.locator('[data-entry-tab="record"]').click();
    assert.match(await page.locator('.rec-root').innerText(),/실거래 유효성 미검증/);
    await page.locator('[data-entry-tab="entry"]').click();
    await page.waitForFunction(()=>document.querySelectorAll('#companySelect option').length>0,{},{timeout:45000});
    await page.locator('#cards article').first().waitFor({timeout:45000});
    const open=page.locator('[data-entry-open]').first(),symbol=await open.getAttribute('data-entry-open');
    assert(raw.companies.some(company=>String(company.symbol)===symbol),'Entry detail must name a real captured company');
    await open.click();
    await page.locator('#view-detail').waitFor({state:'visible',timeout:15000});
    assert.equal(await page.locator('#companySelect').inputValue(),symbol,'Entry plan opens the same selected company');
    if(await page.locator('.nr-rail [data-nr-view="discover"]').count())await page.locator('.nr-rail [data-nr-view="discover"]').first().click();
    else await page.locator('#tab-discover').click();
    await page.locator('.entry-tabs').waitFor({state:'visible',timeout:15000});
    assert.deepEqual(errors,[],'Runtime page errors');
    const bounds=await page.locator('.rec-root').boundingBox();
    assert(bounds&&bounds.x>=-1&&bounds.x+bounds.width<=width+1,'Entry panel overflows viewport');
    const shot=path.join(options.output,`entry-${width}.png`);await page.screenshot({path:shot,fullPage:true});row.screenshots.push(shot);
    row.passed=true;
   }catch(error){
    row.error=String(error);row.traceback=error.stack;row.diagnostics=await page.evaluate(()=>({status:document.querySelector('#liveStatus')?.textContent,entry:document.querySelector('.rec-root')?.textContent?.slice(0,800),discoverHidden:document.querySelector('#view-discover')?.hidden})).catch(()=>null);
    const shot=path.join(options.output,`entry-${width}-failure.png`);await page.screenshot({path:shot,fullPage:true}).then(()=>row.screenshots.push(shot)).catch(()=>{});
   }finally{report.cases.push(row);await context.close();}
  }
  assert.equal(report.blockedRequests.length,0,'Unrecorded external or writable requests');
  report.sourceFilesAfter=sourceFiles(options.root);
  assert.deepEqual(report.sourceFilesAfter,report.sourceFilesBefore,'Advanced source changed during browser verification');
  report.capturedDataSha256=Object.fromEntries([...captured].map(([name,value])=>[name,digest(value)]));
  for(const [name,value]of captured)assert.equal(digest(fs.readFileSync(safeFile(options.root,name))),digest(value),'Testing rewrote captured source data: '+name);
  report.passed=report.cases.length===2&&report.cases.every(row=>row.passed);
 }catch(error){report.errors.push(String(error));report.traceback=error.stack;}
 finally{
  if(browser)await browser.close();
  if(server)await new Promise(resolve=>server.close(resolve));
 }
 fs.writeFileSync(path.join(options.output,'results.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({passed:report.passed,cases:report.cases.length,output:options.output,errors:report.errors}));
 return report.passed?0:1;
}
if(require.main===module)main().then(code=>{process.exitCode=code;}).catch(error=>{console.error(error);process.exitCode=1;});
