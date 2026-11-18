/* Reproducible pregame team context from finalized ESPN scoreboards.
   This is NOT advanced player, possession or injury data. Do not infer any
   retrospective win probability from these values. */
const DAY_MS=86_400_000;
const SAFE_FINAL_LAG_MS=5 * 3_600_000;
const MADRID='Europe/Madrid';
const partsFormatter=new Intl.DateTimeFormat('en-GB',{
  timeZone:MADRID,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',hourCycle:'h23'
});

export function nightKeyMadrid(when) {
  const ms=Date.parse(when instanceof Date?when.toISOString():String(when));
  if(!Number.isFinite(ms))return '';
  const parts=Object.fromEntries(partsFormatter.formatToParts(new Date(ms)).map(p=>[p.type,p.value]));
  const day=Date.UTC(+parts.year,+parts.month-1,+parts.day);
  return new Date(day-(+parts.hour<12?DAY_MS:0)).toISOString().slice(0,10);
}

export function archivedCutoff(game,picks){
  const rows=Object.values(picks||{}).filter(p=>p&&p.event_id===game.id);
  // Compatibility with original archives without event_id in unit fixtures.
  if(!rows.length)rows.push(...['winner','total','handicap'].map(m=>picks?.[game.id+'|'+m]).filter(Boolean));
  const first=rows.length===3?Math.min(...rows.map(p=>Date.parse(p.created_utc))):NaN;
  const kick=Date.parse(game.start_utc);
  // Never reconstruct an archive from a future snapshot. Historical stats must
  // predate the exact original Top 3 creation time.
  return Number.isFinite(first)&&Number.isFinite(kick)&&first<kick?first:null;
}

export function matchupSnapshot(game,games,picks){
  const asof=archivedCutoff(game,picks);
  if(asof===null)return null;
  const history=Object.values(games||{}).filter(g=>{
    if(!g||g.status!=='FINAL'||g.id===game.id)return false;
    const kick=Date.parse(g.start_utc);
    // A completed score without a final timestamp could have become known
    // after creation. Conservatively require the start >=5h before archive.
    return Number.isFinite(kick)&&kick<=asof-SAFE_FINAL_LAG_MS
      &&Number.isInteger(g.home_score)&&Number.isInteger(g.away_score)
      &&g.home_score>=50&&g.home_score<=200&&g.away_score>=50&&g.away_score<=200;
  }).sort((a,b)=>Date.parse(b.start_utc)-Date.parse(a.start_utc));
  function profile(code){
    const played=history.filter(g=>g.home===code||g.away===code);
    const recent=played.slice(0,10);
    if(!recent.length)return null;
    const scores=recent.map(g=>{
      const atHome=g.home===code;
      const scored=atHome?g.home_score:g.away_score;
      const allowed=atHome?g.away_score:g.home_score;
      return {scored,allowed,win:scored>allowed,home:atHome};
    });
    const avg=(xs)=>Math.round((xs.reduce((s,x)=>s+x,0)/xs.length)*10)/10;
    const last5=scores.slice(0,5);
    const meanScored=avg(scores.map(x=>x.scored));
    const meanAllowed=avg(scores.map(x=>x.allowed));
    const rest=Math.max(0,Math.floor((Date.parse(game.start_utc)-Date.parse(played[0].start_utc))/DAY_MS)-1);
    return {team:code,season_games:played.length,recent_games:recent.length,
      wins10:scores.filter(x=>x.win).length,losses10:scores.filter(x=>!x.win).length,
      wins5:last5.filter(x=>x.win).length,losses5:last5.filter(x=>!x.win).length,
      points_for:meanScored,points_against:meanAllowed,
      differential:Math.round((meanScored-meanAllowed)*10)/10,
      rest_days:rest,home_games:scores.filter(x=>x.home).length,
      away_games:scores.filter(x=>!x.home).length};
  }
  return {asof_utc:new Date(asof).toISOString(),source:'ESPN · resultados previos',
    caveat:'Indicadores descriptivos, no todos los factores del modelo; sin lesiones ni estadísticas individuales',
    home:profile(game.home),away:profile(game.away)};
}
