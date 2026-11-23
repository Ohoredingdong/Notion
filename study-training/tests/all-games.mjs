import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {chromium} from 'playwright-core';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../index.html');
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',args:['--no-sandbox','--disable-dev-shm-usage']});
const page=await browser.newPage({viewport:{width:1440,height:900}});
let errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(pathToFileURL(root).href);await page.waitForSelector('.gh-card[data-go="math"]');
const report={math:0,brain:0,reading:0};
for(const group of ['math','brain','reading']){
 await page.locator(`.gh-card[data-go="${group}"]`).click();
 await page.waitForSelector('.gh-game-card');
 const ids=await page.locator('.gh-game-card').evaluateAll(els=>els.map(el=>el.dataset.id));
 for(const id of ids){
  await page.locator(`.gh-game-card[data-id="${id}"]`).click();
  await page.waitForSelector('#modal');
  if(await page.locator('#modal [data-count="5"]').count())await page.locator('#modal [data-count="5"]').click();
  await page.locator('#begin').click();
  await page.waitForSelector('.sd-task-title .qtitle',{timeout:5500});
  const text=await page.locator('.sd-task-title .qtitle').innerText();
  assert.ok(text.length>1,`${id}: question title`);
  assert.ok(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),`${id}: no horizontal overflow`);
  await page.locator('#quit').click();
  await page.waitForSelector('#quit-dialog');
  await page.locator('#quit-exit').click();
  await page.waitForSelector('.gh-game-card');
  report[group]++;
  if(errors.length)throw Error(`JavaScript error during ${id}: ${errors.join('; ')}`);
 }
 await page.locator('.gh-crumb [data-go="home"]').click();
 await page.waitForSelector('.gh-card[data-go="math"]');
}
assert.deepEqual(report,{math:8,brain:24,reading:17});
console.log(JSON.stringify({ok:true,gameStartChecks:49,report,errors},null,2));
await browser.close();