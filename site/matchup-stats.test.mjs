import test from 'node:test';
import assert from 'node:assert/strict';
import {nightKeyMadrid,archivedCutoff,matchupSnapshot} from './matchup-stats.mjs';
const game={id:'UP',home:'ATL',away:'BOS',start_utc:'2026-11-19T01:00:00Z',status:'SCHEDULED'};
const asof='2026-11-18T20:35:00Z';
const picks=Object.fromEntries(['winner','total','handicap'].map(m=>['UP|'+m,{created_utc:asof}]));
const history={};
for(let i=0;i<10;i++){
  const date=new Date(Date.parse('2026-11-05T02:00:00Z')+i*86_400_000).toISOString();
  history['past'+i]={id:'past'+i,home:'ATL',away:'BOS',status:'FINAL',start_utc:date,home_score:120+i%2,away_score:110+i%2};
}
test('Madrid night groups US Wednesday NBA slate on Thursday morning',()=>{
  assert.equal(nightKeyMadrid('2026-11-18T23:30:00Z'),'2026-11-18');
  assert.equal(nightKeyMadrid('2026-11-19T03:30:00Z'),'2026-11-18');
  assert.equal(nightKeyMadrid('2026-11-19T12:30:00Z'),'2026-11-19');
  assert.equal(nightKeyMadrid('invalid'),'');
});
test('archived cutoff requires three complete pregame markets',()=>{
  assert.equal(archivedCutoff(game,picks),Date.parse(asof));
  assert.equal(archivedCutoff(game,{'UP|winner':picks['UP|winner']}),null);
  assert.equal(archivedCutoff(game,Object.fromEntries(Object.entries(picks).map(([k,v])=>[k,{created_utc:'2026-11-19T02:00:00Z'}]))),null);
});
test('snapshot shows actual prior scored and allowed history',()=>{
  const x=matchupSnapshot(game,history,picks);
  assert.equal(x.home.recent_games,10);
  assert.equal(x.home.wins10,10);
  assert.equal(x.away.losses5,5);
  assert.equal(x.home.points_for,120.5);
  assert.equal(x.home.points_against,110.5);
  assert.equal(x.home.differential,10);
  assert.equal(x.away.differential,-10);
});
test('does not leak results posted or started too close to prediction time',()=>{
  const data={...history,later:{id:'later',home:'ATL',away:'BOS',status:'FINAL',start_utc:'2026-11-19T00:30:00Z',home_score:190,away_score:55},tooRecent:{id:'tooRecent',home:'ATL',away:'BOS',status:'FINAL',start_utc:'2026-11-18T16:30:00Z',home_score:50,away_score:190},live:{id:'live',home:'ATL',away:'BOS',status:'SCHEDULED',start_utc:'2026-11-01T00:00:00Z',home_score:50,away_score:200}};
  assert.deepEqual(matchupSnapshot(game,data,picks),matchupSnapshot(game,history,picks));
});
