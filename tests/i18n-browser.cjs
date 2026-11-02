const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [390,1280]){
   const context=await browser.newContext({viewport:{width,height:800}});
   const page=await context.newPage();
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
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
   console.log('PASS viewport',width,'products',before);
   await context.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
