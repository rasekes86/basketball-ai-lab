import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const html=fs.readFileSync(new URL('./index.html',import.meta.url),'utf8');
const css=fs.readFileSync(new URL('./styles.css',import.meta.url),'utf8');
const js=fs.readFileSync(new URL('./app.js',import.meta.url),'utf8');
const sw=fs.readFileSync(new URL('./sw.js',import.meta.url),'utf8');
test('home contains key sections and accessible dialog',()=>{
  for(const key of ['view-inicio','view-partidos','view-resultados','view-equipos','matchDialog','themeToggle'])assert.ok(html.includes(key));
});
test('all 30 NBA teams mapped and logos only from allow-listed host',()=>{
  assert.match(js,/ATL:'Atlanta Hawks'/);
  assert.match(js,/WAS:'Washington Wizards'/);
  assert.match(js,/safeLogo/);
  assert.match(js,/a\.espncdn\.com/);
});
test('mobile has large crests and explicit light theme',()=>{
  assert.match(css,/\.crest\{width:62px;height:62px/);
  assert.match(css,/\.crest\{width:54px;height:54px/);
  assert.match(css,/:root\[data-theme="light"\]/);
  assert.match(js,/bal-theme/);
});
test('PWA never caches odds, games, source feeds or live data',()=>{
  assert.match(sw,/Cache only the application shell/);
  assert.doesNotMatch(sw,/data\/games\.json/);
  assert.doesNotMatch(sw,/api\.espn\.com/);
  assert.doesNotMatch(sw,/odds-api\.com/);
});
test('no unsafe external dependencies in page',()=>{
  assert.doesNotMatch(html,/<script[^>]+src="https?:/);
  assert.doesNotMatch(html,/https?:\/\/.*bootstrap/);
});

test('whole Madrid-night slate and archived stats are exposed',()=>{
  assert.match(js,/tonight\.length\?tonight:upcoming\.slice\(0,12\)/);
  assert.match(js,/matchupSnapshot/);
  assert.match(html,/id="nightCount"/);
  assert.match(html,/option value="night"/);
  assert.match(css,/\.stats-table-row/);
});

test('PWA has an explicit install action and stable standalone identity',()=>{
  const manifest=JSON.parse(fs.readFileSync(new URL('./manifest.webmanifest',import.meta.url),'utf8'));
  assert.equal(manifest.display,'standalone');
  assert.equal(manifest.id,'./');
  assert.equal(manifest.scope,'./');
  assert.ok(manifest.icons.some(icon=>icon.sizes==='192x192'));
  assert.ok(manifest.icons.some(icon=>icon.sizes==='512x512'));
  assert.match(html,/id="installApp"/);
  assert.match(html,/id="installDialog"/);
  assert.match(html,/apple-touch-icon/);
  assert.match(js,/beforeinstallprompt/);
  assert.match(js,/appinstalled/);
  assert.match(js,/userChoice/);
  assert.match(css,/\.install-cta/);
});
test('The Odds API only activates when the GitHub secret is configured',()=>{
  const workflow=fs.readFileSync(new URL('../.github/workflows/nba-daily.yml',import.meta.url),'utf8');
  assert.match(workflow,/ENABLE_ODDS:.*secrets\.ODDS_API_KEY/);
  assert.match(workflow,/ODDS_API_KEY:.*secrets\.ODDS_API_KEY/);
  assert.doesNotMatch(js,/api\.the-odds-api\.com/);
});

test('V3 prospective results do not blend old forecasts',()=>{
  assert.match(js,/v3Checked=checked\.filter\(p=>p\.model_version==='NBA_CONTEXT_V3'\)/);
  assert.match(js,/v3Extras=extras\.filter\(p=>p\.model_version==='NBA_CONTEXT_V3_MARKET_GUARD'\)/);
  assert.match(js,/ACIERTOS TOP 3 V3/);
});

test('NBA update uses three off-peak schedule slots with a late fallback',()=>{
  const workflow=fs.readFileSync(new URL('../.github/workflows/nba-daily.yml',import.meta.url),'utf8');
  for(const cron of ["23 9 * * *","41 14 * * *","47 19 * * *"])
    assert.ok(workflow.includes("cron: '"+cron+"'"),'missing scheduled slot '+cron);
  assert.match(workflow,/workflow_dispatch:/);
  assert.match(workflow,/concurrency:/);
});
test('dashboard flags stale NBA data after one day',()=>{
  assert.match(js,/age>24\*3600\*1000/);
});
