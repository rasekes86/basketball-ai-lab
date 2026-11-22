import {nightKeyMadrid,matchupSnapshot} from './matchup-stats.mjs';
import {activeFixturePicks,activePicksFromRecords} from './selection_policy.mjs';
import {auditSnapshot,healthSnapshot,renderAudit,renderHealth} from './audit_insights.mjs';
/* Basketball AI Lab · zero-dependency static NBA dashboard */
const $=id=>document.getElementById(id);
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const names={ATL:'Atlanta Hawks',BOS:'Boston Celtics',BKN:'Brooklyn Nets',CHA:'Charlotte Hornets',CHI:'Chicago Bulls',CLE:'Cleveland Cavaliers',DAL:'Dallas Mavericks',DEN:'Denver Nuggets',DET:'Detroit Pistons',GSW:'Golden State Warriors',HOU:'Houston Rockets',IND:'Indiana Pacers',LAC:'LA Clippers',LAL:'Los Angeles Lakers',MEM:'Memphis Grizzlies',MIA:'Miami Heat',MIL:'Milwaukee Bucks',MIN:'Minnesota Timberwolves',NOP:'New Orleans Pelicans',NYK:'New York Knicks',OKC:'Oklahoma City Thunder',ORL:'Orlando Magic',PHI:'Philadelphia 76ers',PHX:'Phoenix Suns',POR:'Portland Trail Blazers',SAC:'Sacramento Kings',SAS:'San Antonio Spurs',TOR:'Toronto Raptors',UTA:'Utah Jazz',WAS:'Washington Wizards'};
const number=x=>new Intl.NumberFormat('es-ES').format(Number(x)||0);
const probability=x=>Number.isFinite(+x)?new Intl.NumberFormat('es-ES',{style:'percent',maximumFractionDigits:1}).format(+x):'—';
const date=x=>{const d=new Date(x);return Number.isFinite(d.getTime())?new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}).format(d):'Fecha sin verificar'};
const gameTime=x=>Number(new Date(x))||Infinity;
const safeLogo=x=>{try{const u=new URL(x);return u.protocol==='https:'&&!u.username&&!u.password&&!u.hash&&(u.port===''||u.port==='443')&&['a.espncdn.com','a1.espn.com','a1.espncdn.com','cdn.nba.com'].includes(u.hostname)?u.href:''}catch{return ''}};
const state={games:{},teams:{},picks:{},extras:{},theoretical_extras:{},boxscores:{},status:{},view:'inicio'};
const themeKey='bal-theme';
function appearance(x){
  const theme=x==='light'?'light':'dark';
  document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme;
  const button=$('themeToggle');button.innerHTML=theme==='light'?'☀ <span>Claro</span>':'☽ <span>Oscuro</span>';
  button.setAttribute('aria-pressed',String(theme==='light'));
  button.setAttribute('aria-label',theme==='light'?'Activar tema oscuro':'Activar tema claro');
  $('theme-color')?.setAttribute('content',theme==='light'?'#f3f6fa':'#091622');
  return theme;
}
function savedTheme(){try{return localStorage.getItem(themeKey)==='light'?'light':'dark'}catch{return 'dark'}}
function toggleTheme(){const t=appearance(document.documentElement.dataset.theme==='light'?'dark':'light');try{localStorage.setItem(themeKey,t)}catch{}}
function crest(team){
  const logo=safeLogo(state.teams[team]?.logo);
  return `<span class="crest" data-team="${escape(team)}" aria-label="${escape('Escudo de '+(names[team]||team))}">${logo?`<img src="${escape(logo)}" alt="" loading="lazy" decoding="async">`:escape(team)}</span>`;
}
function originalFixturePicks(id){
  // Retain the three original picks unchanged for audit.
  return Object.values(state.picks).filter(p=>p&&p.event_id===id)
    .sort((a,b)=>(Number(b.probability)||0)-(Number(a.probability)||0)||String(a.market).localeCompare(String(b.market))).slice(0,3);
}
function fixturePicks(id){
  // When the REAL extra matches a frozen contract, count it only as extra.
  return activeFixturePicks(originalFixturePicks(id),extraPick(id));
}
function extraPick(id){return state.extras[id+'|extra']||state.theoretical_extras[id+'|extra_teorica']||null}
function isTheoretical(extra){return extra?.real_price_status==='CUOTA_JUSTA_TEORICA_NO_OFRECIDA'}
function pill(status){const cls=status==='ACIERTO'?'win':status==='FALLO'?'lose':status==='ANULADA'?'void':'';return `<span class="status-chip ${cls}">${escape(status||'PENDIENTE')}</span>`}
function stat(title,value,foot){return `<div class="stat"><span>${escape(title)}</span><strong>${escape(value)}</strong><small>${escape(foot)}</small></div>`}
function fairPrice(p){const prob=Number(p?.probability);return Number.isFinite(prob)&&prob>0&&prob<=1?1/prob:null}
function euros(amount){return new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR',minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:'always'}).format(amount)}
function pickLine(p){
  const fair=fairPrice(p);
  const settled=p.status==='ACIERTO'||p.status==='FALLO';
  const net=settled&&fair!==null?(p.status==='ACIERTO'?fair-1:-1):null;
  return `<div class="pick-row"><span>${escape(p.selection)}<small class="fair-note">Cuota equivalente ${fair===null?'—':fair.toFixed(2).replace('.',',')} · no ofrecida por casa</small></span><div class="pick-meta"><b>${probability(p.probability)}</b>${pill(p.status)}${net!==null?`<small class="simulated-net ${net>=0?'positive':'negative'}">${euros(net)} / 1 € simulado</small>`:''}</div></div>`;
}
function fixture(g){
  const picks=fixturePicks(g.id);const extra=extraPick(g.id);const done=g.status==='FINAL';
  const sample=matchupSnapshot(g,state.games,state.picks);
  const form=sample?.home&&sample?.away?`<div class="fixture-form"><span>Últimos 5: <b>${sample.home.wins5}-${sample.home.losses5}</b> / <b>${sample.away.wins5}-${sample.away.losses5}</b></span><span>Puntos a favor (10): <b>${sample.home.points_for}</b> / <b>${sample.away.points_for}</b></span></div>`:'';
  const value=extra?(isTheoretical(extra)?`<div><strong>${escape(extra.selection)}</strong><small>CUARTA SELECCIÓN TEÓRICA · cuota justa estimada, no ofrecida</small></div><span class="price">${Number(extra.fair_odds).toFixed(2)}*</span>`:`<div><strong>${escape(extra.selection)}</strong><small>Oferta ${escape(extra.bookmaker||'')} · cuota prepartido registrada</small></div><span class="price">${Number(extra.real_price).toFixed(2)}</span>`):
    '<div><strong>Sin cuarta selección archivada</strong><small>Modelo o captura prepartido todavía no disponible; no se inventa</small></div>';
  const review=state.status.review_required?.[g.id];
  const label=review?'REVISIÓN PENDIENTE':done?'FINAL':gameTime(g.start_utc)>Date.now()?'PRÓXIMO PARTIDO':'SIN VERIFICAR';
  return `<article class="fixture"><div class="fixture-meta"><span>NBA · ${label}</span><time>${escape(date(g.start_utc))}</time></div>
    <div class="teams"><div class="team">${crest(g.home)}<strong>${escape(names[g.home]||g.home)}</strong></div>
    <b class="team-versus ${done?'score':''}">${done?`${Number(g.home_score)} – ${Number(g.away_score)}`:'VS'}</b>
    <div class="team">${crest(g.away)}<strong>${escape(names[g.away]||g.away)}</strong></div></div>
    ${form}<div class="extra-row">${value}</div>
    <details class="top3"><summary>${picks.length===2&&originalFixturePicks(g.id).length===3?'Top 2 activo + adicional coincidente':'Top 3 activo'} (${picks.length})</summary>${picks.length?picks.map(pickLine).join(''):'<p class="fineprint">Pendiente de historial suficiente o de ejecución prepartido.</p>'}</details>
    <button class="open-match" data-open-id="${escape(g.id)}">Abrir ficha del partido ›</button></article>`;
}
function resultItem(g){
  const all=[...fixturePicks(g.id),...(extraPick(g.id)?[extraPick(g.id)]:[])];
  const done=all.filter(p=>p.status==='ACIERTO'||p.status==='FALLO');
  const voids=all.filter(p=>p.status==='ANULADA').length;
  const hits=done.filter(p=>p.status==='ACIERTO').length;
  const review=state.status.review_required?.[g.id];
  return `<button class="result-item" data-open-id="${escape(g.id)}">
    <span class="result-with-crests">${crest(g.home)}${crest(g.away)}</span>
    <span class="result-team-text"><strong>${escape(names[g.home]||g.home)} – ${escape(names[g.away]||g.away)}</strong>
    <small>${escape(date(g.start_utc))} · ${escape(g.home_score)}–${escape(g.away_score)} · ${done.length}/${all.length} selecciones archivadas verificadas${voids?' · '+voids+' anulada(s)':''}${review?' · REVISAR':''}</small></span>
    <b>${hits}/${done.length||'—'}</b></button>`;
}
function alertBox(heading,msg){return `<div class="empty"><strong>${escape(heading)}</strong>${escape(msg)}</div>`}
function render(){
  const now=Date.now(),all=Object.values(state.games).filter(g=>g&&Number.isFinite(gameTime(g.start_utc))).sort((a,b)=>gameTime(a.start_utc)-gameTime(b.start_utc));
  const upcoming=all.filter(g=>gameTime(g.start_utc)>now && g.status==='SCHEDULED');
  const recent=all.filter(g=>g.status==='FINAL'&&fixturePicks(g.id).some(p=>p.status==='ACIERTO'||p.status==='FALLO')).sort((a,b)=>gameTime(b.start_utc)-gameTime(a.start_utc));
  const picks=activePicksFromRecords(state.picks,state.extras), checked=picks.filter(p=>p.status==='ACIERTO'||p.status==='FALLO');
  const wins=checked.filter(p=>p.status==='ACIERTO').length;
  const extras=Object.values(state.extras), extraDone=extras.filter(p=>p.status==='ACIERTO'||p.status==='FALLO');
  const winExtra=extraDone.filter(p=>p.status==='ACIERTO').length;
  // Keep the new prospective V3 record separate from historical V1/V2 picks.
  const v3Checked=checked.filter(p=>p.model_version==='NBA_CONTEXT_V3');
  const v3Wins=v3Checked.filter(p=>p.status==='ACIERTO').length;
  const v3Extras=extras.filter(p=>p.model_version==='NBA_CONTEXT_V3_MARKET_GUARD');
  const v3ExtraDone=v3Extras.filter(p=>p.status==='ACIERTO'||p.status==='FALLO');
  $('updated').textContent=state.status.updated_utc?'Datos: '+date(state.status.updated_utc):'Aún sin publicación';
  const failed=Number(state.status.source_failed_days)||0;
  const age=Date.now()-Date.parse(state.status.updated_utc||'');
  const stale=state.status.updated_utc && age>24*3600*1000;
  const reviews=Number(state.status.review_required_count)||0;
  const indicator=$('connection');
  indicator.className='connection'+(state.status.updated_utc?(failed||stale||reviews?' warn':' ready'):'');
  const syncLabel=!state.status.updated_utc?'Sin captura inicial':stale?'Datos antiguos':reviews?'Partidos por revisar':failed?'Fuentes parciales':'Datos publicados';
  indicator.innerHTML='<span class="connection-dot"></span>'+escape(syncLabel);
  $('updated').textContent=(stale?'⚠ Información antigua · ':reviews?'⚠ Revisar '+reviews+' partido(s) · ':'')+$('updated').textContent;
  // NBA tip-offs take place after midnight in Madrid. A single 'night'
  // spans noon-to-noon local time, keeping the complete US slate together.
  const key=nightKeyMadrid(new Date());
  const tonight=all.filter(g=>nightKeyMadrid(g.start_utc)===key);
  const focus=tonight.length?tonight:upcoming.slice(0,12);
  const top3Tonight=tonight.reduce((n,g)=>n+fixturePicks(g.id).length,0);
  $('nightCount').textContent=tonight.length?`· ${tonight.length} partidos`:'';
  $('nightLabel').textContent=tonight.length?`Jornada NBA del ${key.split('-').reverse().join('/')} · ${top3Tonight} pronósticos Top 3 archivados · horarios de Madrid`:'Próximos encuentros NBA · horarios de Madrid';
  $('stats').innerHTML=stat('PARTIDOS ESTA NOCHE',number(tonight.length),'Todos los de la jornada NBA')+stat('TOP 3 ESTA NOCHE',number(top3Tonight),'3 por partido, cuando hay muestra')+stat('ACIERTOS TOP 3 V3',v3Checked.length?probability(v3Wins/v3Checked.length):'—',`${v3Wins} de ${v3Checked.length} · sin mezclar modelos`)+stat('CUARTAS SELECCIONES',`${Number(state.status.extras_displayed)||0}`,`${extras.length} reales · ${Object.keys(state.theoretical_extras).length} referencias teóricas archivadas`);
  $('featured').innerHTML=focus.length?focus.map(fixture).join(''):alertBox('Aún no hay próximos encuentros comprobados','Una ejecución del motor descargará el calendario real; no mostramos partidos ficticios.');
  $('recent').innerHTML=recent.length?recent.slice(0,5).map(resultItem).join(''):alertBox('Pendiente de primeras liquidaciones','Los resultados solo aparecen aquí después de archivar pronósticos y verificar el partido.');
  const tb=state.status.top3_theoretical_balance||{};
  const top3Net=Number(tb.net_eur);
  const simText=Number(tb.settled)>0&&Number.isFinite(top3Net)?euros(top3Net):'—';
  const realNet=extraDone.length?euros(Number(state.status.extras_unit_profit)||0):'—';
  $('resultStats').innerHTML=stat('HISTÓRICO TOP 3',`${checked.length}/${picks.length}`,'Incluye modelos anteriores')+stat('ACIERTOS V3',v3Checked.length?probability(v3Wins/v3Checked.length):'—',`${v3Wins} de ${v3Checked.length} desde el cambio de modelo`)+stat('BALANCE TOP 3 SIMULADO',simText,Number(tb.settled)>0?`${tb.roi_pct}% · 1 € por pick a cuota 1/p`:'Sin resultados liquidados')+stat('ADICIONALES V3 +1,50',`${v3ExtraDone.length}/${v3Extras.length}`,'Solo ofertas verificadas con filtro V3')+stat('SIMULACIÓN HISTÓRICA',realNet,'1 € hipotético · incluye anteriores')+stat('PENDIENTES TRAS FINAL',Number(state.status.pending_postmatch_selections)||0,(Number(state.status.pending_postmatch_team_stats)||0)+' requieren estadísticas de equipo');
  const insights=auditSnapshot(state,{days:Number($('auditDaysFilter').value),model:$('auditModelFilter').value});
  const auditHtml=renderAudit(insights);
  $('auditSummary').innerHTML=auditHtml.totals;
  $('auditNights').innerHTML=auditHtml.nights;
  $('auditMarkets').innerHTML=auditHtml.markets;
  $('auditModels').innerHTML=auditHtml.models;
  $('auditCalibration').innerHTML=auditHtml.calibration;
  $('healthSummary').innerHTML=renderHealth(healthSnapshot(state.status,new Date()));
  const marketNames={winner:'Ganador',total:'Puntos totales',handicap:'Hándicap',team_threes:'Triples (equipo)',team_rebounds:'Rebotes (equipo)',team_assists:'Asistencias (equipo)'};
  const marketRows=state.status.market_metrics||{};
  $('marketResults').innerHTML=Object.entries(marketNames).map(([key,label])=>{
    const m=marketRows[key]||{};
    const evaluated=Number(m.evaluated)||0;
    const bm=tb.by_market?.[key];
    const simulated=Number(bm?.settled)>0?` · Sim. ${euros(Number(bm.net_eur)||0)} (${Number(bm.roi_pct).toFixed(1)}%)`:'';
    return `<article class="market-quality"><small>${escape(label)} · histórico</small><strong>${evaluated?probability(m.accuracy):'—'}</strong><span>${evaluated} evaluadas · Brier ${evaluated?Number(m.brier).toFixed(3):'—'}${simulated}</span></article>`;
  }).join('');
  const results=all.filter(g=>g.status==='FINAL').sort((a,b)=>gameTime(b.start_utc)-gameTime(a.start_utc));
  $('fullResults').innerHTML=results.length?results.slice(0,60).map(resultItem).join(''):alertBox('Todavía no hay resultados descargados','Se cargarán automáticamente después de la primera ingestión.');
  const upsets=Object.values(state.picks).filter(p=>p?.market==='winner' && p.status==='FALLO' && Number(p.probability)>=.60 && state.games[p.event_id]?.status==='FINAL');
  $('upsets').innerHTML=upsets.length?upsets.sort((a,b)=>gameTime(b.start_utc)-gameTime(a.start_utc)).slice(0,20).map(p=>{
    const g=state.games[p.event_id];return `<button class="result-item" data-open-id="${escape(g.id)}"><span><strong>${escape(names[g.home])} – ${escape(names[g.away])}</strong><small>Favorito del modelo: ${escape(names[p.contract.team])} · ${probability(p.probability)}</small></span><b class="status-chip lose">SORPRESA</b></button>`;
  }).join(''):alertBox('Sin sorpresas registradas','Se detectan cuando un favorito archivado por encima del 60 % pierde y el marcador está confirmado.');
  const q=$('teamFilter').value.trim().toLowerCase(),period=$('periodFilter').value;
  const displayed=all.filter(g=>(!q||[names[g.home],names[g.away],g.home,g.away].some(x=>String(x||'').toLowerCase().includes(q)))&&(period==='all'||period==='night'&&nightKeyMadrid(g.start_utc)===key||period==='final'&&g.status==='FINAL'||period==='future'&&g.status==='SCHEDULED'&&gameTime(g.start_utc)>now));
  // Never bury upcoming events behind the first 90 completed fixtures.
  const ordered=period==='all'?displayed.sort((a,b)=>{const af=gameTime(a.start_utc)>=now?0:1,bf=gameTime(b.start_utc)>=now?0:1;return af-bf||(af?gameTime(b.start_utc)-gameTime(a.start_utc):gameTime(a.start_utc)-gameTime(b.start_utc));}):displayed.sort((a,b)=>period==='final'?gameTime(b.start_utc)-gameTime(a.start_utc):gameTime(a.start_utc)-gameTime(b.start_utc));
  $('allFixtures').innerHTML=ordered.length?ordered.slice(0,90).map(fixture).join(''):alertBox('Sin partidos para estos filtros','Prueba con otro equipo o con el histórico.');
  $('teamGrid').innerHTML=Object.keys(names).sort().map(code=>`<div class="team-card">${crest(code)}<strong>${escape(names[code])}</strong><small>${escape(code)}${state.teams[code]?.logo?' · escudo recuperado':' · pendiente de escudo'}</small></div>`).join('');
}
async function fetchJson(filename){
  const controller=new AbortController();const id=setTimeout(()=>controller.abort(),9000);
  try{const res=await fetch('./data/'+filename+'.json?v='+Date.now(),{cache:'no-store',signal:controller.signal});if(!res.ok)throw Error('HTTP '+res.status);const obj=await res.json();return obj&&typeof obj==='object'&&!Array.isArray(obj)?obj:{}}finally{clearTimeout(id)}
}
async function refresh(){
  $('refresh').disabled=true;
  const files=['games','picks','extras','theoretical_extras','teams','status','boxscores'];
  const values=await Promise.allSettled(files.map(fetchJson));
  let failures=0;values.forEach((x,i)=>{if(x.status==='fulfilled')state[files[i]]=files[i]==='teams'?x.value.teams||{}:x.value;else failures++});
  $('refresh').disabled=false;render();
  if(failures){$('connection').className='connection warn';$('connection').innerHTML='<span class="connection-dot"></span>'+failures+' fuentes sin respuesta';}
}
function navigate(view){
  const views=['inicio','partidos','resultados','equipos','modelo'];
  if(!views.includes(view))return;
  state.view=view;
  document.querySelectorAll('.page').forEach(x=>x.hidden=x.id!=='view-'+view);
  document.querySelectorAll('[data-view]').forEach(b=>{const active=b.dataset.view===view;b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});
  if(location.hash!=='#'+view)history.replaceState(null,'','#'+view);
  window.scrollTo({top:0,behavior:'instant'});
}
function matchupStatsHTML(g){
  const snap=matchupSnapshot(g,state.games,state.picks);
  if(!snap)return '<p class="fineprint">Las estadísticas prepartido solo se muestran para encuentros con Top 3 completo y archivado antes del inicio.</p>';
  if(!snap.home||!snap.away)return '<p class="fineprint">Muestra histórica insuficiente para comparar los dos equipos.</p>';
  const rows=[['Partidos disponibles',snap.home.season_games,snap.away.season_games],['Últimos 5 (V-D)',`${snap.home.wins5}-${snap.home.losses5}`,`${snap.away.wins5}-${snap.away.losses5}`],['Últimos 10 (V-D)',`${snap.home.wins10}-${snap.home.losses10}`,`${snap.away.wins10}-${snap.away.losses10}`],['Puntos anotados / partido',snap.home.points_for,snap.away.points_for],['Puntos recibidos / partido',snap.home.points_against,snap.away.points_against],['Diferencia media',snap.home.differential,snap.away.differential],['Días de descanso estimados',snap.home.rest_days,snap.away.rest_days]];
  return `<div class="stats-context"><p>Datos históricos disponibles antes de archivar el Top 3 · ${escape(date(snap.asof_utc))}</p><div class="stats-table" role="table" aria-label="Comparativa histórica"><div class="stats-table-head" role="row"><span>Indicador</span><b>${escape(g.home)}</b><b>${escape(g.away)}</b></div>${rows.map(([label,h,a])=>`<div class="stats-table-row" role="row"><span>${escape(label)}</span><b>${escape(h)}</b><b>${escape(a)}</b></div>`).join('')}</div><small>Fuente: marcadores finales ESPN. Últimos 10 partidos; descanso aproximado. Los datos estadísticos no incluyen lesiones, pace ni jugadores. Muestra conservadora: se excluyen partidos iniciados menos de 5 h antes de archivar.</small></div>`;
}
function openGame(id){
  const g=state.games[id];if(!g)return;
  const p=fixturePicks(id),extra=extraPick(id);
  const review=state.status.review_required?.[id];
  $('dialogBody').innerHTML=`${review?`<p class="review-banner">⚠ Partido pendiente de revisión (${escape(review.code)}). No se liquidarán pronósticos hasta contrastar el cambio.</p>`:''}<div class="teams"><div class="team">${crest(g.home)}<strong>${escape(names[g.home])}</strong></div><span class="team-versus score">${g.status==='FINAL'?`${Number(g.home_score)} – ${Number(g.away_score)}`:'VS'}</span><div class="team">${crest(g.away)}<strong>${escape(names[g.away])}</strong></div></div><div class="dialog-stats"><div><span>Fecha en Madrid</span><strong>${escape(date(g.start_utc))}</strong></div><div><span>Estado fuente</span><strong>${escape(g.status)}</strong></div></div><h3>Estadísticas previas del encuentro</h3>${matchupStatsHTML(g)}<h3>${p.length===2&&originalFixturePicks(id).length===3?'Top 2 activo · apuesta repetida pasa a adicional':'Top 3 activo'}</h3><div class="dialog-picks">${p.length?p.map(pickLine).join(''):alertBox('Sin Top 3','Historial insuficiente o análisis todavía no ejecutado.')}</div><h3>Cuarta selección · real o teórica</h3>${extra?(isTheoretical(extra)?`<div class="extra-row"><div><strong>${escape(extra.selection)}</strong><small>CUOTA JUSTA TEÓRICA · no ofrecida por casa de apuestas</small></div><span class="price">${Number(extra.fair_odds).toFixed(2)}*</span></div><p>${pill(extra.status)}</p>`:`<div class="extra-row"><div><strong>${escape(extra.selection)}</strong><small>${escape(extra.provider)} · ${escape(extra.bookmaker)} · ${escape(date(extra.quote_updated_utc))}</small></div><span class="price">${Number(extra.real_price).toFixed(2)}</span></div><p>${pill(extra.status)}</p>`):'<p class="fineprint">Sin cuarta selección prepartido archivada: faltan datos para estimarla sin inventar.</p>'}<p class="fineprint">Cuando aparecen triples, rebotes o asistencias se basan en box scores reales de equipos anteriores al pronóstico. Los mercados de jugadores requieren una fase específica de alineaciones y minutos. Probabilidades de un modelo experimental sin calibración prospectiva demostrada. Los mercados Top 3 usan líneas teóricas, no cuotas ejecutables. No constituye consejo de apuestas.</p>`;
  $('matchDialog').showModal();
}
// Browser-owned installation prompt: never install without an explicit tap.
let deferredInstallPrompt=null;
const installed=()=>window.matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
function refreshInstallButton(){
  $('installApp').hidden=installed();
}
window.addEventListener('beforeinstallprompt',event=>{
  event.preventDefault();
  deferredInstallPrompt=event;
  refreshInstallButton();
});
window.addEventListener('appinstalled',()=>{
  deferredInstallPrompt=null;
  refreshInstallButton();
});
$('installApp').addEventListener('click',async()=>{
  if(installed())return;
  if(deferredInstallPrompt){
    const prompt=deferredInstallPrompt;
    deferredInstallPrompt=null;
    await prompt.prompt();
    // The user decides whether to accept; a dismissed prompt is not success.
    try{await prompt.userChoice;}catch{}
    refreshInstallButton();
    return;
  }
  const ios=/iPad|iPhone|iPod/i.test(navigator.userAgent);
  $('installInstructions').textContent=ios
    ?'En Safari, toca Compartir y después Añadir a pantalla de inicio.'
    :'En Chrome para Android, abre el menú de tres puntos (⋮) y pulsa Instalar aplicación o Añadir a pantalla de inicio. Si no aparece, abre la web directamente en Chrome.';
  $('installDialog').showModal();
});
$('closeInstallDialog').addEventListener('click',()=>$('installDialog').close());
$('installDialog').addEventListener('click',event=>{
  if(event.target===$('installDialog'))$('installDialog').close();
});
refreshInstallButton();
$('themeToggle').addEventListener('click',toggleTheme);
$('refresh').addEventListener('click',refresh);
$('teamFilter').addEventListener('input',render);
$('periodFilter').addEventListener('change',render);
$('auditDaysFilter').addEventListener('change',render);
$('auditModelFilter').addEventListener('change',render);
$('closeDialog').addEventListener('click',()=>$('matchDialog').close());
$('matchDialog').addEventListener('click',e=>{if(e.target===$('matchDialog'))$('matchDialog').close()});
document.addEventListener('error',e=>{const img=e.target;if(img?.tagName==='IMG'&&img.closest('.crest')){const container=img.closest('.crest');container.textContent=container.dataset.team||'NBA'}},true);
document.addEventListener('click',e=>{const goto=e.target.closest('[data-view]');if(goto){navigate(goto.dataset.view);return}const game=e.target.closest('[data-open-id]');if(game)openGame(game.dataset.openId)});
window.addEventListener('hashchange',()=>navigate(location.hash.slice(1)||'inicio'));
appearance(savedTheme());navigate(location.hash.slice(1)||'inicio');refresh();
if('serviceWorker' in navigator)navigator.serviceWorker.register('./sw.js').catch(()=>{});
