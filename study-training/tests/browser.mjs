import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
import {chromium} from 'playwright-core';

const htmlPath=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../index.html');
const url=pathToFileURL(htmlPath).href;
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',args:['--no-sandbox','--disable-dev-shm-usage']});
const checks=[];const errors=[];
const page=await browser.newPage({viewport:{width:1440,height:900}});
page.on('pageerror',err=>errors.push('desktop: '+err.message));
await page.goto(url,{waitUntil:'load'});await page.waitForSelector('.gh-card[data-go="math"]');
checks.push('home');
assert.ok(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),'desktop no horizontal overflow');
await page.locator('.gh-card[data-go="math"]').click();
await page.waitForSelector('.gh-game-card[data-id="twosum"]');
assert.equal(await page.locator('.gh-game-card').count(),8,'math catalog shows eight games');
checks.push('math catalog');
await page.locator('.gh-game-card[data-id="targetsum"]').click();
await page.waitForSelector('#modal');
await page.locator('#modal [data-count="5"]').click();
await page.locator('#begin').click();
for(let i=0;i<5;i++){
 await page.waitForFunction(number=>document.querySelector('.sd-progress-row strong')?.textContent?.includes('문제 '+number),i+1,{timeout:5500});
 await page.locator('#challenge [data-answer]').first().click();
 await page.waitForFunction(number=>{
  const text=document.querySelector('.sd-progress-row strong')?.textContent||'';
  return !!document.querySelector('#sd-next-question')||!!document.querySelector('.sd-results-panel')||text.includes('문제 '+number);
 },i+2,{timeout:4000});
 if(await page.locator('#sd-next-question').isVisible())await page.locator('#sd-next-question').click();
}
await page.waitForSelector('.sd-results-panel',{timeout:6000});
const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('mindroom_v1')||'{}'));
assert.ok(saved.sessions?.length>=1,'session saved');
assert.ok(Number.isFinite(saved.progress?.xp),'durable XP saved');
checks.push('five-question gameplay and results');
await page.locator('#back-home').click();await page.waitForSelector('.gh-card');
await page.locator('[data-test="academy"]').first().click();
await page.waitForSelector('#modal');
assert.match(await page.locator('#setup-title').innerText(),/종합 테스트/);
await page.locator('#cancel').click();
checks.push('balanced test setup');
await page.locator('.gh-card[data-go="reading"]').click();
await page.locator('.gh-game-card[data-id="verbal"]').click();
await page.locator('#begin').click();
await page.waitForSelector('.sd-task-title .qtitle');
assert.doesNotMatch(await page.locator('.sd-task-title .qtitle').innerText(),/번째 단어는/,'no answer target in preview');
await page.waitForFunction(()=>document.querySelector('.sd-task-title .qtitle')?.textContent?.includes('번째 단어는'),null,{timeout:5500});
checks.push('verbal preview question hidden');
await page.locator('#quit').click();await page.waitForSelector('#quit-dialog');
await page.locator('#quit-resume').click();
await page.locator('#quit').click();await page.locator('#quit-exit').click();
checks.push('pause / quit / resume');
for(const width of [390,1111]){
 const mobile=await browser.newPage({viewport:{width,height:844}});
 mobile.on('pageerror',err=>errors.push(width+': '+err.message));
 await mobile.goto(url);await mobile.waitForSelector('.gh-card');
 assert.ok(!await mobile.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),width+' home overflow');
 await mobile.locator('.gh-card[data-go="reading"]').click();await mobile.waitForSelector('.gh-game-card');
 assert.ok(!await mobile.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),width+' reading catalog overflow');
 await mobile.close();
}
checks.push('390px and 1111px layouts');
assert.deepEqual(errors,[],'no JavaScript errors');
console.log(JSON.stringify({ok:true,checks,errors},null,2));
await browser.close();