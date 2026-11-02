const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [390,1280]){
   const context=await browser.newContext({viewport:{width,height:800}});
   const page=await context.newPage();
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   const perf=await page.evaluate(()=>({start:performance.now()}));
   await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});
   await page.locator('#cards .card').first().waitFor({timeout:15000});
   assert.equal(errors.length,0,'initial JS errors: '+errors.join('; '));
   const before=await page.locator('#cards .card').count();assert(before>0);
   await page.locator('#cards .card summary').first().click();
   assert.equal(await page.locator('#cards .card[open]').count(),1);
   await page.locator('#enLanguage').click();
   await page.waitForFunction(()=>document.documentElement.lang==='en');
   await page.waitForFunction(()=>Object.keys(englishProducts).length>0);
   assert.equal(await page.locator('#cards .card[open]').count(),1,'open card lost after EN');
   assert.equal(await page.locator('#search').getAttribute('placeholder'),'Search the library…');
   await page.locator('#ruLanguage').click();
   assert.equal(await page.locator('#cards .card[open]').count(),1,'open card lost after RU');
   await page.reload();
   assert.equal(await page.locator('html').getAttribute('lang'),'ru');
   assert.equal(errors.length,0,'JS errors: '+errors.join('; '));
   await page.locator('#enLanguage').click();await page.waitForFunction(()=>Object.keys(englishProducts).length>0);
   const englishName=await page.locator('#cards .card .title').first().innerText();
   await page.locator('#search').fill(englishName);
   assert((await page.locator('#cards .card').count())>0,'English product name search failed');
   await page.locator('#search').fill('');
   await page.reload();assert.equal(await page.locator('html').getAttribute('lang'),'en','English preference not persisted');
   assert.equal(errors.length,0,'JS errors after English reload: '+errors.join('; '));
   const timing=await page.evaluate(()=>({domReady:Math.round(performance.getEntriesByType('navigation')[0]?.domContentLoadedEventEnd||0),transfer:performance.getEntriesByType('resource').reduce((n,r)=>n+(r.transferSize||0),0)}));
   console.log('PASS viewport',width,'products',before,'DOM ready ms',timing.domReady,'resource transfer bytes',timing.transfer);
   if(width===390){
    await page.goto('http://127.0.0.1:8765/');
    await page.waitForFunction(()=>navigator.serviceWorker.controller!==null,{timeout:15000}).catch(()=>{});
    await page.evaluate(async()=>{const reg=await navigator.serviceWorker.getRegistration();if(!reg)throw Error('PWA service worker not registered');await Promise.race([navigator.serviceWorker.ready,new Promise((_,reject)=>setTimeout(()=>reject(Error('Service worker activation timeout')),20000))])});
    await page.reload();await page.locator('#cards .card').first().waitFor();
    await context.setOffline(true);
    await page.reload({waitUntil:'domcontentloaded',timeout:15000});
    await page.locator('#cards .card').first().waitFor({timeout:12000});
    assert.equal(await page.locator('html').getAttribute('lang'),'en','Offline language preference lost');
    assert.equal(errors.length,0,'Offline JS errors: '+errors.join('; '));
    await context.setOffline(false);
    console.log('PASS offline PWA');
   }
   await context.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
