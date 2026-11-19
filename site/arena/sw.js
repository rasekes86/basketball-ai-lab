const CACHE='pulse-arena-shell-v1';
const SHELL=['./','./index.html','./styles.css','./app.js','./catalog.js','./icon.svg','./icon-192.png','./icon-512.png','./manifest.webmanifest'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)));self.skipWaiting();});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('pulse-arena-shell-')&&k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim();});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  // Never intercept the child laboratories or other sibling GitHub Pages apps.
  const prefix=new URL('./',self.registration.scope).pathname;
  if(url.origin!==self.location.origin || !url.pathname.startsWith(prefix))return;
  event.respondWith(fetch(event.request).then(response=>{
    if(response.ok){const clone=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,clone));}
    return response;
  }).catch(()=>caches.match(event.request).then(hit=>hit || (event.request.mode==='navigate'?caches.match('./index.html'):Response.error()))));
});
