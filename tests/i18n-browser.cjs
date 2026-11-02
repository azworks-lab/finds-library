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
   await page.locator('#status').selectOption('Куплено');
   await page.locator('#applyFilters').click();
   const filtered=await page.locator('#cards .card').count();
   assert(filtered>0&&filtered<=before,'Status filter invalid');
   await page.locator('#filterOpen').click();
   await page.locator('#resetAll').click();
   assert.equal(await page.locator('#cards .card').count(),before,'Reset did not restore all products');
   const linked=page.locator('#cards .card').filter({has:page.locator('[data-related]')}).first();
   await linked.locator('summary').first().click();
   const linkedName=await linked.locator('.title').innerText();
   await linked.locator('[data-related]').first().click();
   assert.equal(await page.locator('#cards .card').count(),1,'Related-product navigation did not focus');
   await page.locator('#goBack').click();
   assert.equal(await page.locator('#cards .card').count(),before,'In-app back did not restore catalog');
   assert.equal(await page.locator('#cards .card').filter({hasText:linkedName}).count()>0,true,'Original product missing after in-app back');
   await page.goForward({waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>document.querySelectorAll('#cards .card').length===1);
   assert.equal(await page.locator('#cards .card').count(),1,'Browser forward did not restore focused product');
   await page.goBack({waitUntil:'domcontentloaded'});
   await page.waitForFunction(expected=>document.querySelectorAll('#cards .card').length===expected,before);
   assert.equal(await page.locator('#cards .card').count(),before,'Browser back did not restore catalog');
   console.log('PASS browser back/forward',width);
   console.log('PASS related navigation',width);
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
    const cacheReport=await page.evaluate(async()=>{
     const keys=await caches.keys();
     const current=keys.find(k=>k.startsWith('finds-library-v2-i18n-preview-'));
     if(!current)throw Error('Expected current PWA cache missing');
     const cache=await caches.open(current);
     const paths=(await cache.keys()).map(r=>new URL(r.url).pathname);
     return {current,paths};
    });
    for(const path of ['/index.html','/data/products.json','/data/products.en.json','/version.json']){
     assert(cacheReport.paths.some(p=>p.endsWith(path)),'Missing offline cache asset: '+path);
    }
    await page.evaluate(async()=>{const old=await caches.open('finds-library-obsolete-test');await old.put('./obsolete-test',new Response('old'))});
    assert(await page.evaluate(async()=>(await caches.keys()).includes('finds-library-obsolete-test')));
    await page.evaluate(async()=>{
     const reg=await navigator.serviceWorker.getRegistration();
     await reg.unregister();
     await navigator.serviceWorker.register('./sw.js?test-reinstall='+Date.now());
     await navigator.serviceWorker.ready;
    });
    await page.waitForFunction(async()=>!(await caches.keys()).includes('finds-library-obsolete-test'),{timeout:20000});
    await context.setOffline(true);
    await page.reload({waitUntil:'domcontentloaded',timeout:15000});
    await page.locator('#cards .card').first().waitFor({timeout:12000});
    await context.setOffline(false);
    console.log('PASS PWA cache migration and offline after SW reinstall');
    console.log('PASS offline PWA');
   }
   await context.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
