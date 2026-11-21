/* Cache only the application shell, NOT live results or provider data. */
const CURRENT='basketball-ai-lab-shell-v6';
const ROOT=new URL(self.registration.scope);
const SHELL=['./','index.html','styles.css','app.js','matchup-stats.mjs','selection_policy.mjs','assets/icon.svg','assets/icon-192.png','assets/icon-512.png','manifest.webmanifest'];
const URLS=SHELL.map(x=>new URL(x,ROOT).href);
const PATHS=new Set(URLS.map(x=>new URL(x).pathname));
self.addEventListener('install',event=>event.waitUntil((async()=>{
  const cache=await caches.open(CURRENT);await cache.addAll(URLS);await self.skipWaiting();
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
  await Promise.all((await caches.keys()).filter(x=>x.startsWith('basketball-ai-lab-shell-')&&x!==CURRENT).map(x=>caches.delete(x)));
  await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
  const req=event.request;if(req.method!=='GET')return;
  const u=new URL(req.url);
  if(u.origin!==ROOT.origin||!u.pathname.startsWith(ROOT.pathname))return;
  if(req.mode!=='navigate'&&!PATHS.has(u.pathname))return;
  event.respondWith((async()=>{
    const fallback=req.mode==='navigate'?new URL('index.html',ROOT).href:req.url;
    try{const r=await fetch(req);if(r.ok){const c=await caches.open(CURRENT);await c.put(fallback,r.clone())}return r}
    catch{const c=await caches.open(CURRENT);return await c.match(fallback)||Response.error()}
  })());
});
