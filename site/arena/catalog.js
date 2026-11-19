/** PULSE ARENA module registry: add future sports here, never in page markup. */
export const MODULES = Object.freeze([
  Object.freeze({
    id: 'football', title: 'FOOTBALL', localeName: 'Fútbol', supertitle: 'FOOTBALL AI LAB',
    name: 'Football AI Lab', category: '01 / THE BEAUTIFUL GAME', icon: '⚽',
    accent: 'lime', subtitle: '6 ligas · 3+1 · cuotas y resultados',
    summary: 'Seis ligas, pronósticos Top 3 + adicional, cuotas reales y un histórico que evoluciona jornada a jornada.',
    tags: ['LALIGA', 'PREMIER LEAGUE', 'BUNDESLIGA'],
    url: 'https://rasekes86.github.io/football-ai-lab/',
    status: 'https://rasekes86.github.io/football-ai-lab/published/evaluacion_selecciones.json',
    repo: 'https://github.com/rasekes86/football-ai-lab', available: true
  }),
  Object.freeze({
    id: 'basketball', title: 'BASKETBALL', localeName: 'Baloncesto', supertitle: 'BASKETBALL AI LAB',
    name: 'Basketball AI Lab', category: '02 / ABOVE THE RIM', icon: '🏀',
    accent: 'orange', subtitle: 'NBA · 30 equipos · 3+1',
    summary: 'Toda la NBA en un solo radar: pronósticos previos, estadísticas de equipo, comprobación de resultados y laboratorio de fiabilidad.',
    tags: ['NBA', 'ESTADÍSTICAS', 'BACKTESTING'],
    url: 'https://rasekes86.github.io/basketball-ai-lab/',
    status: 'https://rasekes86.github.io/basketball-ai-lab/data/status.json',
    repo: 'https://github.com/rasekes86/basketball-ai-lab', available: true
  }),
  Object.freeze({ id: 'tennis', title: 'TENNIS', localeName: 'Tenis', category: '03 / BEYOND THE BASELINE', icon: '🎾', accent: 'violet', subtitle:'PRÓXIMAMENTE', summary: 'Un espacio para analizar el circuito ATP y WTA.', tags:['ATP','WTA'], available:false }),
  Object.freeze({ id: 'motorsport', title: 'MOTORSPORT', localeName: 'Motor', category: '04 / FULL THROTTLE', icon: '🏎️', accent: 'sky', subtitle:'PRÓXIMAMENTE', summary:'Ritmo, circuitos y estrategia para los apasionados del motor.', tags:['F1','MOTOR'], available:false }),
  Object.freeze({ id: 'esports', title: 'ESPORTS', localeName: 'Esports', category: '05 / NEXT GEN', icon: '🎮', accent: 'pink', subtitle:'PRÓXIMAMENTE', summary:'Un nuevo laboratorio para competiciones digitales.', tags:['COMPETICIÓN','DATOS'], available:false })
]);

export const AVAILABLE = MODULES.filter(m => m.available);
export function getModule(id) { return AVAILABLE.find(module => module.id === id) ?? null; }
export function filterModules(query = '') {
  const q = String(query).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es').trim();
  return MODULES.filter(m => [m.localeName,m.title,m.summary,...m.tags].join(' ').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es').includes(q));
}
export function parseStatus(module, payload) {
  if (!module?.available || !payload || typeof payload !== 'object') return null;
  if (module.id === 'football') {
    const evaluated = Number(payload.finalizadas);
    const accuracy = Number(payload.global?.acierto_pct);
    if (!Number.isFinite(evaluated) || evaluated < 0) return null;
    return {evaluated, accuracy: evaluated > 0 && Number.isFinite(accuracy) ? accuracy : null, updated: payload.calculado_utc || null};
  }
  if (module.id === 'basketball') {
    const evaluated = Number(payload.top3_evaluated);
    const accuracy = Number(payload.top3_accuracy);
    if (!Number.isFinite(evaluated) || evaluated < 0) return null;
    return {evaluated, accuracy: evaluated > 0 && Number.isFinite(accuracy) ? accuracy * 100 : null, updated: payload.updated_utc || null};
  }
  return null;
}
