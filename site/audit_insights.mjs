/**
 * Auditoría exclusivamente de lectura del registro NBA 3+1.
 * Ninguna función recalcula, sustituye o escribe una selección archivada.
 * Los precios teóricos no son precios reales ni forman parte de las adicionales.
 */
import {nightKeyMadrid} from './matchup-stats.mjs';
import {activePicksFromRecords} from './selection_policy.mjs';

const completed=p=>p && (p.status==='ACIERTO'||p.status==='FALLO');
const win=p=>p.status==='ACIERTO';
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const money=n=>n===null?'—':new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR',signDisplay:'always'}).format(n);
const pct=(hits,n)=>n?(100*hits/n).toLocaleString('es-ES',{maximumFractionDigits:1})+' %':'—';
const dayFor=(p,games)=>{const t=games?.[String(p.event_id)]?.start_utc||p.start_utc;return t && !Number.isNaN(Date.parse(t))?nightKeyMadrid(t):null};
const zero=()=>({archived:0,checked:0,wins:0,losses:0,pending:0,net:0,priced:0});
function add(target,p,asExtra){
  target.archived++;
  if(!completed(p)){target.pending++;return;}
  target.checked++;
  if(win(p))target.wins++;else target.losses++;
  if(asExtra&&p.real_price_status==='OFRECIDA_API_REGISTRADA'){
    const quote=Number(p.real_price);
    if(Number.isFinite(quote)&&quote>1.5){
      target.priced++;
      target.net+=win(p)?quote-1:-1;
    }
  }
}
const finalize=x=>({...x,accuracy:x.checked?x.wins/x.checked:null,net:x.priced?Number(x.net.toFixed(3)):null});
const group=(map,key)=>{if(!map.has(key))map.set(key,{top:zero(),extra:zero()});return map.get(key)};
const eventModel=p=>String(p.model_version||'SIN_VERSION');
const labelDay=s=>{const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(s);return m?m[3]+'/'+m[2]+'/'+m[1]:s};
export function auditSnapshot(source={},options={}){
  const games=source.games||{}, archived=activePicksFromRecords(source.picks||{},source.extras||{});
  const extras=Object.values(source.extras||{}).filter(Boolean);
  const days=[7,30,90,365].includes(Number(options.days))?Number(options.days):30;
  const at=options.at instanceof Date?options.at:new Date();
  const cutoff=new Date(at.getTime()-(days-1)*86400000);
  const first=nightKeyMadrid(cutoff);
  const model=options.model==='V3'?'V3':'ALL';
  const keep=p=>model==='ALL'||eventModel(p).startsWith('NBA_CONTEXT_V3');
  const byNight=new Map(),byMarket=new Map(),byModel=new Map();
  const bins=[{key:'50–69 %',lower:0,upper:.7,n:0,prob:0,wins:0},{key:'70–84 %',lower:.7,upper:.85,n:0,prob:0,wins:0},{key:'85–100 %',lower:.85,upper:1.00001,n:0,prob:0,wins:0}];
  const top=zero(),extra=zero();
  let missingDate=0;
  for(const [type,records] of [['top',archived],['extra',extras]]){
    for(const p of records){
      if(!keep(p))continue;
      const night=dayFor(p,games);
      if(!night){missingDate++;continue;}
      if(night<first||night>nightKeyMadrid(at))continue;
      add(type==='top'?top:extra,p,type==='extra');
      add(group(byNight,night)[type],p,type==='extra');
      add(group(byMarket,String(p.market||'SIN_MERCADO'))[type],p,type==='extra');
      add(group(byModel,eventModel(p))[type],p,type==='extra');
      if(type==='top'&&completed(p)){
        const prob=Number(p.probability);
        if(Number.isFinite(prob)&&prob>=0&&prob<=1){
          const b=bins.find(b=>prob>=b.lower&&prob<b.upper);
          if(b){b.n++;b.prob+=prob;b.wins+=Number(win(p));}
        }
      }
    }
  }
  const finishMap=m=>[...m].map(([key,stats])=>({key,top:finalize(stats.top),extra:finalize(stats.extra)}));
  return {days,model,top:finalize(top),extra:finalize(extra),
    nights:finishMap(byNight).sort((a,b)=>b.key.localeCompare(a.key)),
    markets:finishMap(byMarket).sort((a,b)=>b.top.checked+b.extra.checked-a.top.checked-a.extra.checked),
    models:finishMap(byModel).sort((a,b)=>a.key.localeCompare(b.key)),
    calibration:bins.map(b=>({key:b.key,count:b.n,expected:b.n?b.prob/b.n:null,observed:b.n?b.wins/b.n:null})),
    missingDate};
}
export function healthSnapshot(status={},at=new Date()){
  const changed=Date.parse(status.updated_utc||'');
  const ageHours=Number.isFinite(changed)?(at.getTime()-changed)/3600000:null;
  const failures=Number(status.source_failed_days||0)+Number(status.review_required_count||0);
  const pending=Number(status.pending_postmatch_selections||0);
  let state='OK',label='Datos publicados';
  if(ageHours===null){state='UNKNOWN';label='No consta actualización';}
  else if(ageHours>24){state='STALE';label='Datos con más de 24 h';}
  else if(failures){state='WARN';label='Revisar incidencias de la fuente';}
  else if(pending){state='PENDING';label='Liquidaciones por completar';}
  // Horas UTC, solo programación nominal, NO prueba de ejecución.
  const times=[[5,37],[7,11],[9,23],[14,41],[19,47]];
  let next=null;
  for(let shift=0;shift<=1&&!next;shift++){
    const d=new Date(Date.UTC(at.getUTCFullYear(),at.getUTCMonth(),at.getUTCDate()+shift));
    for(const [hour,minute] of times){
      const t=new Date(d.getTime()+hour*3600000+minute*60000);
      if(t>at){next=t;break;}
    }
  }
  return {state,label,ageHours,pending,failures,next,updated:status.updated_utc||null};
}
function unit(s){
  return '<span class="audit-number">'+s.wins+'/'+s.checked+
    ' <small>('+pct(s.wins,s.checked)+')</small></span><small>'+
    s.losses+' fallos · '+s.pending+' pendientes</small>';
}
function row(key,s){
  return '<article class="audit-insight-row"><strong>'+safe(key)+'</strong>'+
    '<div><span>Top 3</span>'+unit(s.top)+'</div><div><span>Adicional real</span>'+unit(s.extra)+
    '<small>Simulación con cuotas archivadas: '+money(s.extra.net)+'</small></div></article>';
}
export function renderAudit(snapshot){
  const totals='<div class="audit-insight-totals">'+
    '<div><small>TOP 3 ORIGINAL</small>'+unit(snapshot.top)+'</div>'+
    '<div><small>ADICIONAL REAL</small>'+unit(snapshot.extra)+
    '<small>Balance hipotético a 1 €: '+money(snapshot.extra.net)+'</small></div></div>';
  const nights=snapshot.nights.length?snapshot.nights.slice(0,14).map(x=>row(labelDay(x.key),x)).join(''):'<p>Sin encuentros archivados en este periodo.</p>';
  const markets=snapshot.markets.length?snapshot.markets.map(x=>row(x.key,x)).join(''):'<p>Sin mercados evaluables.</p>';
  const models=snapshot.models.length?snapshot.models.map(x=>row(x.key,x)).join(''):'<p>Sin modelos evaluables.</p>';
  const calibration=snapshot.calibration.map(b=>
    '<article class="audit-calibration-row"><strong>'+safe(b.key)+'</strong><span>'+b.count+
    ' Top 3 · estimado '+(b.expected===null?'—':pct(b.expected,1))+
    ' · observado '+(b.observed===null?'—':pct(b.observed,1))+'</span></article>').join('');
  return {totals,nights,markets,models,calibration};
}
export function renderHealth(health){
  const dt=x=>x?new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}).format(new Date(x)):'—';
  const css=['STALE','WARN','UNKNOWN'].includes(health.state)?'audit-health-warn':'audit-health-ok';
  return '<div class="audit-health '+css+'"><strong>'+safe(health.label)+'</strong>'+
    '<span>Últimos datos: '+safe(dt(health.updated))+' · Próxima hora programada: '+
    safe(dt(health.next))+'</span><small>'+health.pending+' selecciones pendientes tras final'+
    ' · GitHub puede retrasar el cron; la programación no confirma su ejecución.</small></div>';
}
