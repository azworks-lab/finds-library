// FINDS: network-first updates with offline shell fallback.
const CACHE="finds-library-v2-price-compare-20261027";
const SHELL=["./","./index.html","./manifest.webmanifest","./icon.svg","./finds-mark.svg","./data/products.json","./version.json"];
self.addEventListener("install",event=>{
 event.waitUntil((async()=>{
  const cache=await caches.open(CACHE);
  await cache.addAll(SHELL.map(path=>new Request(path,{cache:"reload"})));
  try {
   const response=await fetch(new Request("./data/products.json",{cache:"no-store"}));
   if(response.ok){
    const catalog=await response.json();
    const photos=[...new Set((catalog.products||[]).map(p=>p.photo).filter(p=>typeof p==="string"&&p.startsWith("images/")))];
    await Promise.all(photos.map(async path=>{
     try{
      const image=await fetch(new Request("./"+path,{cache:"reload"}));
      if(image.ok)await cache.put("./"+path,image);
     }catch(error){console.warn("Offline image cache:",path,error)}
    }));
   }
  }catch(error){console.warn("Offline image precache:",error)}
  await self.skipWaiting();
 })());
});
self.addEventListener("activate",event=>{
 event.waitUntil((async()=>{
  const keys=await caches.keys();
  await Promise.all(keys.filter(key=>key.startsWith("finds-library-")&&key!==CACHE).map(key=>caches.delete(key)));
  await self.clients.claim();
 })());
});
self.addEventListener("fetch",event=>{
 const request=event.request;
 const url=new URL(request.url);
 if(request.method!=="GET"||url.origin!==self.location.origin)return;
 event.respondWith((async()=>{
  try{
   const response=await fetch(request.mode==="navigate"?new Request(request,{cache:"no-store"}):request);
   if(response.ok){
    const cache=await caches.open(CACHE);
    const key=request.mode==="navigate"?"./index.html":request;
    await cache.put(key,response.clone());
   }
   return response;
  }catch(error){
   if(request.mode==="navigate"){
    return (await caches.match("./index.html"))||(await caches.match("./"))||Response.error();
   }
   return (await caches.match(request))||Response.error();
  }
 })());
});
