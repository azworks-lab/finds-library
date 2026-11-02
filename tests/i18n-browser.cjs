const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [320,390,1280]){
   const context=await browser.newContext({viewport:{width,height:800}});
   const page=await context.newPage();
   const errors=[];const englishRequests=[];
   page.on('pageerror',e=>errors.push(e.message));
   page.on('request',request=>{if(request.url().includes('/data/products.en.json'))englishRequests.push(request.url())});
   await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});
   await page.locator('#cards .card').first().waitFor({timeout:15000});
   assert.equal(errors.length,0,'initial JS errors: '+errors.join('; '));
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'horizontal overflow at '+width+'px');
   const before=await page.locator('#cards .card').count();assert(before>0);
   assert.equal(englishRequests.length,0,'English catalog fetched before EN selection');
   await page.locator('#cards .card summary').first().click();
   assert.equal(await page.locator('#cards .card[open]').count(),1);
   await page.locator('#enLanguage').click();
   await page.waitForFunction(()=>document.documentElement.lang==='en');
   await page.waitForFunction(()=>Object.keys(englishProducts).length>0);
   assert(englishRequests.length>0,'English translations were not requested on EN selection');
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
   await page.locator('#filterOpen').click();
   await page.locator('#status').selectOption({label:'Куплено'});
   await page.locator('#applyFilters').click();
   const filtered=await page.locator('#cards .card').count();
   assert(filtered>0&&filtered<=before,'Status filter invalid');
   await page.locator('#filterOpen').click();
   await page.locator('#resetAll').click();
   await page.locator('#applyFilters').click();
   assert.equal(await page.locator('#cards .card').count(),before,'Reset did not restore all products');
   console.log('PASS filters',width,'filtered',filtered);
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
    assert((await page.locator('#cards .card .title').first().innerText()).length>0,'Offline product title missing');
    assert.equal(await page.locator('#search').getAttribute('placeholder'),'Search the library…','Offline English UI missing');
    assert.equal(errors.length,0,'Offline JS errors: '+errors.join('; '));
    await context.setOffline(false);
    console.log('PASS offline PWA');
   }
   await context.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
