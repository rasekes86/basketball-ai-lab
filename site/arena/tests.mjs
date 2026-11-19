import test from 'node:test';
import assert from 'node:assert/strict';
import {MODULES,AVAILABLE,getModule,filterModules,parseStatus} from './catalog.js';

test('two active modules and expandable catalogue',()=>{
 assert.equal(AVAILABLE.length,2);
 assert.equal(MODULES.length,5);
 assert.equal(getModule('football').name,'Football AI Lab');
 assert.equal(getModule('basketball').name,'Basketball AI Lab');
 assert.equal(getModule('tennis'),null);
 assert.deepEqual(filterModules('FÚTBOL').map(x=>x.id),['football']);
 assert.deepEqual(filterModules('NBA').map(x=>x.id),['basketball']);
});
test('trusted URLs and no secret in modules',()=>{
 for(const m of AVAILABLE){
  assert.match(m.url,/^https:\/\/rasekes86\.github\.io\//);
  assert.match(m.status,/^https:\/\/rasekes86\.github\.io\//);
  assert.match(m.repo,/^https:\/\/github\.com\/rasekes86\//);
  assert.doesNotMatch(JSON.stringify(m),/token|api[_-]?key|password/i);
 }
});
test('realistic football and NBA status parsing, never invent numbers',()=>{
 const f=getModule('football'), b=getModule('basketball');
 assert.deepEqual(parseStatus(f,{finalizadas:15,global:{acierto_pct:93.33},calculado_utc:'2026-11-19T09:00:00Z'}),{evaluated:15,accuracy:93.33,updated:'2026-11-19T09:00:00Z'});
 assert.deepEqual(parseStatus(b,{top3_evaluated:31,top3_accuracy:.8065,updated_utc:'2026-11-19T09:00:00Z'}),{evaluated:31,accuracy:80.65,updated:'2026-11-19T09:00:00Z'});
 assert.equal(parseStatus(b,{}),null);
 assert.equal(parseStatus(f,{finalizadas:0,global:{acierto_pct:0}}).accuracy,null);
});
