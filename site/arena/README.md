# PULSE ARENA

PWA hub for Football AI Lab and Basketball AI Lab. One shell, two independent connected applications, expandable via catalog.js.

## Hosting

Currently hosted inside `rasekes86/basketball-ai-lab/site/arena/` and published by its existing GitHub Pages workflow. This is an isolated subdirectory and does not change the NBA model, workflow or data. The shell's service worker only controls `/basketball-ai-lab/arena/`, never the two independent labs.

## How to add another sport

Add a module to `catalog.js` with a unique id, trusted `https://` url, status URL (optional), public repository, category/tags, and `available:true`. To support a third live module, add the id to the routing allow-list in `app.js` and its sidebar entry in `index.html`, and supply an illustration fallback. Embed works for publicly frameable sites, with a permanent 'Abrir original' fallback.

## Privacy and data

Only public, same-owner GitHub Pages endpoints are read. No login, tokens, scraping or new API credentials. The lab stats are from public archived reports. The fields are informative, not directly comparable across sports and not a profitability claim. No advertising or analytics. Refreshing data is automatic on opening the portal.

## Local preview

`python -m http.server 8000 --directory .` and visit `http://localhost:8000`.

## Tests

`node --test tests.mjs` validates data registry, filtering, statuses and module URLs.
