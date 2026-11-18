# Fuentes, costes y licencias · revisión 18/11/2026

## Etapa sin claves: ESPN NBA (público, NO oficial para terceros)

- Calendario y marcadores: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD&limit=100`
- Catálogo con nombres, identificadores y logos: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams?limit=50`
- Una ejecución diaria; primer arranque **45 días anteriores + 7 posteriores** (hasta ~54 llamadas), después **4 días anteriores + 7 posteriores** (~13 llamadas/día); cap fijo de 65 solicitudes por ejecución.
- Nada de scraping masivo, proxies anti-bloqueo, peticiones paralelas ni reintentos frente a 403/429. Datos faltantes = datos faltantes.
- Los logos se almacenan como **enlaces HTTPS publicados por el proveedor**, no se descargan ni redistribuyen como archivos. La web mostrará iniciales si no están accesibles.
- ESPN puede bloquear los runners de GitHub, variar el JSON, revocar el acceso o limitar el uso sin aviso. **No está garantizado** el funcionamiento permanente.
- Se debe verificar la autorización para uso y publicación de logos/datos antes de dar visibilidad pública a gran escala. Son marcas de terceros.

Referencias:
- https://hoopr.sportsdataverse.org/articles/espn-endpoints.html
- https://sportsdataverse-py.sportsdataverse.org/docs/0.0.73/nba/reference/site
- https://www.espn.com/terms-of-use

## NBA.com / nba_api (futuro, no obligatorio)

`nba_api` ofrece estadísticas detalladas sin clave, pero `stats.nba.com` puede ralentizar o bloquear runners cloud. Por eso no es dependencia crítica de la versión inicial.

- https://github.com/swar/nba_api

## Cuotas opcionales: The Odds API

- https://the-odds-api.com/
- https://the-odds-api.com/liveapi/guides/v4/
- Plan gratuito publicitado: **500 créditos mensuales**. Solo se activaría previa inscripción del propietario y aceptación de condiciones.
- Código ya preparado para `basketball_nba`, región US, mercado `h2h` (ganador), **máximo una petición al día** con límite conservador de **100 créditos/mes**. Se guarda el consumo de los encabezados del proveedor.
- Sin `ENABLE_ODDS=true` y `ODDS_API_KEY`, número de consultas a esta API = **0**. No registra ni inventa cuotas; para totales y hándicaps los Top 3 solo muestran líneas teóricas.
- El plan y la disponibilidad de mercados varían: verificar antes de activar. Las cuotas ofertadas pueden no ser ejecutables en España.
- Una llamada fallida marca el intento del día para no reintentar indefinidamente consumiendo créditos; se deberá inspeccionar el proveedor antes de reintentar otro día.
- **Nunca** publicar secretos, URL de consulta con clave, headers con claves, ni compartir tokens con el motor de fútbol.

## GitHub Actions y Pages

- En repositorios **públicos**, los runners estándar GitHub Actions son gratuitos según la documentación actual; no implica ausencia de otros límites, restricciones de almacenamiento o servicios externos.
- Ejecutamos una actualización diaria y las pruebas solo al modificar código. No hay tareas cada pocos minutos.
- GitHub Pages con un workflow propio y contenido estático; sin servidor, base SQL, Cloudflare, VPS ni suscripción.
- Cada repositorio tiene workflows aislados, pero **las facturaciones de servicios externos pueden depender de la cuenta**, por eso no se reutiliza ninguna clave ni cuenta de cuotas de fútbol.
- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## ¿Es gratis al 100 %?

**El software entregado no exige pagos ni servicios de pago**, pero ESPN no garantiza acceso de terceros ni autorización para la redistribución. El proveedor opcional de cuotas requiere cuenta propia. No prometemos permanencia de fuentes ni disponibilidad de todos los mercados con un plan gratis.
