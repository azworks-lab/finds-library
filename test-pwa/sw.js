// FINDS PWA: network-first with explicit revalidation for app shell and catalog.
const CACHE='finds-library-test-pwa-autoupdate-v1';
const SHELL=['./index.html','../data/products.json','../icon.svg','../finds-mark.svg'];
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE).then(async cache=>{
   for(const url of SHELL){const response=await fetch(url,{cache:'reload'});if(!response.ok)throw Error('Precache failed: '+url);await cache.put(url,response);}
 }).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('finds-library-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
 const req=event.request,url=new URL(req.url);
 if(req.method!=='GET'||url.origin!==self.location.origin)return;
 // Ignore query parameters for offline fallback; never serve stale app shell while online.
 const shell=url.pathname.endsWith('/')||url.pathname.endsWith('/index.html')||url.pathname.endsWith('/data/products.json');
 event.respondWith((async()=>{
   try{
     const response=await fetch(req,shell?{cache:'no-store'}:undefined);
     if(response.ok){const cache=await caches.open(CACHE);await cache.put(req,response.clone());}
     return response;
   }catch(error){
     const cache=await caches.open(CACHE);
     return (await cache.match(req))||(req.mode==='navigate'?await cache.match('./index.html'):null)||Response.error();
   }
 })());
});
