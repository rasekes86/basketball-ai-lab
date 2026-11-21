/** NBA Top 3 activo: si la cuota adicional repite exactamente el contrato
 * (ganador, linea de puntos, handicap, equipo), no contar esa predicción dos
 * veces. El JSON original sigue sin modificarse para auditoría.
 */
export function sameOutcome(a,b) {
  if (!a || !b || !a.event_id || a.event_id!==b.event_id) return false;
  const ac=a.contract,bc=b.contract;
  if (!ac || !bc || typeof ac!=="object" || typeof bc!=="object" || !Object.keys(ac).length) return false;
  const sorted=x=>JSON.stringify(Object.keys(x).sort().map(key=>[key,x[key]]));
  return sorted(ac)===sorted(bc);
}

export function activeFixturePicks(archived,extra) {
  return (archived||[]).filter(p=>!sameOutcome(p,extra));
}

export function activePicksFromRecords(picks={},extras={}) {
  return Object.values(picks).filter(p=>p &&
    !sameOutcome(p,extras[p.event_id+"|extra"]));
}
