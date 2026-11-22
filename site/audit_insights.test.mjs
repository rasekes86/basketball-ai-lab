import test from 'node:test';
import assert from 'node:assert/strict';
import {auditSnapshot,healthSnapshot,renderAudit,renderHealth} from './audit_insights.mjs';

const at=new Date('2026-11-22T10:30:00Z');
const start='2026-11-21T20:00:00Z';
function fixture(){
  return {
    games:{g1:{id:'g1',status:'FINAL',start_utc:start}},
    picks:{
      'g1|winner':{id:'g1|winner',event_id:'g1',start_utc:start,status:'ACIERTO',
        market:'winner',probability:.80,contract:{type:'winner',team:'ATL'},model_version:'NBA_CONTEXT_V3'},
      'g1|total':{id:'g1|total',event_id:'g1',start_utc:start,status:'FALLO',
        market:'total',probability:.62,contract:{type:'total',line:230},model_version:'NBA_CONTEXT_V3'},
      'g1|handicap':{id:'g1|handicap',event_id:'g1',start_utc:start,status:'ACIERTO',
        market:'handicap',probability:.55,contract:{type:'spread',line:4},model_version:'NBA_CONTEXT_V2'}
    },
    extras:{
      'g1|extra':{id:'g1|extra',event_id:'g1',start_utc:start,status:'FALLO',
        market:'extra_totals',probability:.62,real_price:1.9,
        real_price_status:'OFRECIDA_API_REGISTRADA',contract:{type:'total',line:230},
        model_version:'NBA_CONTEXT_V3_MARKET_GUARD'}
    },
    theoretical_extras:{
      'g1|extra_teorica':{id:'g1|extra_teorica',status:'ACIERTO',real_price:99}
    }
  };
}

test('separates 3+1, excludes overlap with real additional and ignores theoretical price',()=>{
  const s=fixture(),before=JSON.stringify(s);
  const x=auditSnapshot(s,{days:7,at});
  assert.equal(x.top.archived,2);
  assert.equal(x.top.checked,2);
  assert.equal(x.top.wins,2);
  assert.equal(x.extra.archived,1);
  assert.equal(x.extra.losses,1);
  assert.equal(x.extra.net,-1);
  assert.equal(x.nights.length,1);
  assert.equal(JSON.stringify(s),before,'the original history must never mutate');
});

test('filters a model version without mixing previous prospective experiments',()=>{
  const x=auditSnapshot(fixture(),{days:7,model:'V3',at});
  assert.equal(x.top.checked,1);
  assert.equal(x.extra.checked,1);
  assert.equal(x.calibration.reduce((n,b)=>n+b.count,0),1);
  assert.equal(x.models.length,2);
});

test('missing source date is neither an incorrect loss nor invented fixture',()=>{
  const s=fixture();
  s.picks.x={id:'x',event_id:'missing',market:'winner',status:'FALLO'};
  const x=auditSnapshot(s,{days:7,at});
  assert.equal(x.missingDate,1);
  assert.equal(x.top.losses,0);
});

test('health uses published timestamp, reports planned schedule as unconfirmed',()=>{
  const h=healthSnapshot({updated_utc:'2026-11-21T00:00:00Z',pending_postmatch_selections:2},at);
  assert.equal(h.state,'STALE');
  assert.equal(h.pending,2);
  assert.ok(h.next>at);
  assert.match(renderHealth(h),/puede retrasar el cron/);
});

test('renders supplied market text escaped and never a theoretical ROI',()=>{
  const x=auditSnapshot(fixture(),{days:7,at});
  const html=renderAudit(x);
  assert.match(html.totals,/TOP 3 ORIGINAL/);
  assert.match(html.models,/NBA_CONTEXT_V3/);
  assert.doesNotMatch(html.totals,/99/);
});
