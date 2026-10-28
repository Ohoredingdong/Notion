const {chromium}=require('@playwright/test');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [1280,390]){
   const page=await browser.newPage({viewport:{width,height:900}});
   await page.goto('http://127.0.0.1:8765/stock-value-radar.html',{waitUntil:'domcontentloaded'});
   await page.locator('.entry-tabs').waitFor({timeout:45000});
   assert.match(await page.locator('.rec-root h2').innerText(),/투자 조건과 진입 타이밍/);
   assert.match(await page.locator('.entry-badge').innerText(),/검증 단계/);
   assert.equal(await page.locator('.rec-root .rec-card,.rec-root .rec-real').count(),0);
   await page.locator('[data-entry-tab="market"]').click();
   assert.match(await page.locator('.rec-root').innerText(),/확률을 임의로/);
   await page.locator('[data-entry-tab="record"]').click();
   assert.match(await page.locator('.rec-root').innerText(),/실거래 유효성 미검증/);
   await page.locator('[data-entry-tab="entry"]').click();
   const bounds=await page.locator('.rec-root').boundingBox();
   assert.ok(bounds.x>=-1 && bounds.x+bounds.width<=width+1,'entry panel overflows viewport');
   await page.screenshot({path:`entry-${width}.png`,fullPage:true});
   await page.close();
  }
  console.log('Desktop and mobile entry UI checks passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
