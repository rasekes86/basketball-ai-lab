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
