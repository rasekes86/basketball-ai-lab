import {MODULES, AVAILABLE, getModule, filterModules, parseStatus} from './catalog.js';

const $ = id => document.getElementById(id);
const formatPercent = x => x === null ? '—' : new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(x) + '%';
const fmtDate = str => {
  const date = new Date(str);
  return Number.isNaN(date.getTime()) ? 'Sin fecha' : new Intl.DateTimeFormat('es-ES',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Madrid'}).format(date);
};
const state = {route:'inicio', status:{}, embed: null};
const icons = {football: `<svg viewBox="0 0 160 160" fill="none" aria-hidden="true"><circle cx="80" cy="80" r="67" stroke="currentColor" stroke-width="2.5" opacity=".9"/><path d="M80 42 111 64 100 99H60L49 64zM80 42 63 24M80 42l17-18M111 64l30-3M100 99l15 28M60 99l-15 28M49 64l-30-3M63 24l-25-5M97 24l25-5M115 127l-1 14M45 127l1 14" stroke="currentColor" stroke-width="2.5" opacity=".65"/><path d="m80 42 31 22-11 35H60L49 64z" fill="currentColor" opacity=".24"/></svg>`, basketball: `<svg viewBox="0 0 160 160" fill="none" aria-hidden="true"><circle cx="80" cy="80" r="67" stroke="currentColor" stroke-width="2.6"/><path d="M13 80h134M80 13v134M29 34c31 10 59 49 51 113M131 34c-31 10-59 49-51 113M24 115c38-26 75-25 112 0M24 46c38 27 75 26 112 0" stroke="currentColor" stroke-width="2.5" opacity=".7"/></svg>`};

function sportCard(m) {
  const st = state.status[m.id];
  const note = st?.evaluated ? `<span class="sport-metric">${st.evaluated} Top 3 verificadas · ${formatPercent(st.accuracy)} aciertos</span>` : '<span class="sport-metric">Pronósticos, resultados y análisis en directo desde su propia web</span>';
  return `<a href="#${m.id}" class="sport-card ${m.accent}" aria-label="Abrir ${m.name}">
    <div class="card-top"><span class="card-category">${m.category}</span><span class="card-online"><i></i> DISPONIBLE</span></div>
    <div class="card-graphic">${icons[m.id]}</div>
    <div class="card-content"><span class="card-overline">${m.supertitle}</span><h3>${m.title}<span>.</span></h3><p>${m.summary}</p>
      <div class="card-tags">${m.tags.map(tag=>`<span>${tag}</span>`).join('')}</div>
      <div class="card-bottom"><div>${note}</div><span class="card-button" aria-hidden="true">↗</span></div>
    </div></a>`;
}
function catalogCard(m) {
  if (m.available) return `<a href="#${m.id}" class="catalog-card ${m.accent}"><span class="catalog-ordinal">${m.category}</span><span class="catalog-icon">${icons[m.id] || m.icon}</span><span class="catalog-type">LABORATORIO ACTIVO</span><h3>${m.title}<span>.</span></h3><p>${m.summary}</p><span class="catalog-bottom">ENTRAR EN EL LAB <b>↗</b></span></a>`;
  return `<article class="catalog-card is-soon ${m.accent}"><span class="catalog-ordinal">${m.category}</span><span class="catalog-icon simple">${m.icon}</span><span class="catalog-type">EN PREPARACIÓN</span><h3>${m.title}<span>.</span></h3><p>${m.summary}</p><span class="catalog-bottom">PRÓXIMAMENTE <b>＋</b></span></article>`;
}

function renderHome() { $('activeCards').innerHTML = AVAILABLE.map(sportCard).join(''); }
function renderCatalog() {
  const filtered = filterModules($('sportsSearch').value);
  $('catalogCards').innerHTML = filtered.map(catalogCard).join('');
  $('catalogCount').textContent = `${filtered.length} DISCIPLINAS`;
  $('emptySearch').hidden = filtered.length > 0;
}
function routeFromHash() {
  const route = location.hash.slice(1).split(/[/?]/)[0].toLowerCase();
  return ['inicio','catalogo','football','basketball'].includes(route) ? route : 'inicio';
}
function navigate() {
  const route = routeFromHash();
  state.route = route;
  $('breadcrumbCurrent').textContent = {inicio:'OVERVIEW',catalogo:'SPORTS DIRECTORY',football:'FOOTBALL AI LAB',basketball:'BASKETBALL AI LAB'}[route];
  document.querySelectorAll('[data-route]').forEach(link=>{
    const active = link.dataset.route === route;
    link.classList.toggle('active',active);
    if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
  });
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  const lab = getModule(route);
  if (lab) {
    $('page-lab').classList.add('active');
    $('labEyebrow').textContent = lab.category;
    $('labTitle').textContent = lab.title + ' AI LAB';
    $('labTitle').className = lab.accent;
    $('labDescription').textContent = lab.summary;
    $('labOpenExternal').href = lab.url;
    $('fallbackOpen').href = lab.url;
    $('embedUrl').textContent = lab.url.replace('https://','');
    const frame=$('labFrame');
    frame.title = lab.name;
    // The embedded app stays a separate application. Never rewrite its URLs.
    if (state.embed !== route) {frame.src = lab.url; state.embed=route;}
    $('frameFallback').hidden = true;
  } else {
    $('page-'+route).classList.add('active');
    const frame=$('labFrame');
    if(state.embed){frame.src='about:blank';state.embed=null;}
  }
  document.title = (lab ? lab.name + ' — ' : '') + 'PULSE ARENA';
  window.scrollTo({top:0,behavior:'instant'});
}
async function updateStatuses() {
  await Promise.all(AVAILABLE.map(async m => {
    const controller = new AbortController();
    const timeout = setTimeout(()=>controller.abort(),6000);
    try {
      const res = await fetch(m.status,{cache:'no-store',signal:controller.signal});
      if (!res.ok) throw new Error('Source unavailable');
      state.status[m.id] = parseStatus(m,await res.json());
    } catch { state.status[m.id] = null; }
    finally {clearTimeout(timeout);}
  }));
  // Live data are informational; no fake numbers or status success on errors.
  renderHome(); renderCatalog();
}

$('footerYear').textContent = new Date().getFullYear();
$('sportsSearch').addEventListener('input',renderCatalog);
$('labReload').addEventListener('click',()=>{
  const lab=getModule(state.route);if(!lab)return;
  $('labFrame').src=lab.url;
});
window.addEventListener('hashchange',navigate);

let installEvent=null;
window.addEventListener('beforeinstallprompt',event=>{
  event.preventDefault(); installEvent=event; $('installButton').hidden=false;
});
$('installButton').addEventListener('click',async()=>{
  if(!installEvent)return;
  const e=installEvent;installEvent=null; $('installButton').hidden=true;
  await e.prompt();
});
window.addEventListener('appinstalled',()=>{$('installButton').hidden=true;});
if('serviceWorker' in navigator) window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));

renderHome();renderCatalog();navigate();updateStatuses();
