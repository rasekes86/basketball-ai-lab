# Basketball AI Lab · NBA

Proyecto experimental **nuevo e independiente** de Football AI Lab. Versión 0.3.0 (18/11/2026).

**Objetivo:** pronosticar partidos de NBA antes de su inicio, archivar tres mercados teóricos, liquidar los resultados cuando se confirme el marcador y, en una fase opcional, registrar una apuesta experimental adicional con **cuota real prepartido superior a 1,50**. No ejecuta apuestas ni promete resultados.

## Qué incluye ahora

- Fuente inicial **sin registro ni clave**: calendario y marcadores del endpoint público no documentado de ESPN.
- Identificación exacta de las **30 franquicias NBA** y sus logos obtenidos del catálogo/partidos ESPN. Si un escudo falla, aparece la abreviatura, **sin inventar imágenes**.
- Motor propio de puntos a favor/en contra con regularización y ponderación de partidos recientes. No usa Poisson de fútbol ni datos posteriores al pronóstico.
- **Top 3 original inmutable**: conserva los mercados anteriores en eventos ya archivados. Para próximos partidos, después de recabar suficientes box scores ESPN reales, puede seleccionar ganador y dos mercados diferentes entre triples, rebotes y asistencias **de equipo**, puntos totales o hándicap. Las líneas teóricas no son cuotas ofrecidas. Sin 5 partidos estadísticos previos verificables por equipo, vuelve al modelo de puntos original.
- **Jugadores**: no se publican aún pronósticos de triples individuales sin verificación de disponibilidad, minutos y datos históricos del jugador.
- Archivo inmutable de pronósticos con sello temporal; evaluación postpartido de **solo** esos tres mercados.
- Preparación de adicional >1,50 con **The Odds API** (ganador, hándicap y total, con líneas ofrecidas), desactivada por defecto. Requiere una clave del proveedor y activación voluntaria, no hay cuotas fabricadas.
- Identificación de **sorpresas del modelo**: favorito archivado >=60 % que perdió; no equivale a anomalía de casas de apuestas.
- Informes CSV para **Excel** sin conectar Google Sheets: `data/reports/{top3,adicional_150,sorpresas}.csv` y sus copias descargables en `site/reports/`.
- Auditoría **por mercado** (ganador, total y hándicap), acierto y Brier, además del global.
- Protección de archivo ante **partidos reprogramados, cambios de rival y marcadores finales corregidos**: se registran en `data/review_flags.json` y quedan pendientes de revisión, sin liquidaciones automáticas contra datos contradictorios.
- Circuit breaker de ESPN: se detiene ante 403/429 o tres fallos de red consecutivos; no agota solicitudes ni reescribe el pasado.
- Comando `doctor` para comprobar estado, integridad de archivo, escudos, archivos web, fechas y CSV sin acceso a internet.
- Web móvil responsive y PWA con tema **claro/oscuro**, logos grandes, ficha por partido y vista de resultados.
- Workflows GitHub Actions **independientes** para pruebas, una actualización diaria y publicación Pages.
- Pruebas reproducibles y sin llamadas reales a terceros.

## Estructura

| Ruta | Función |
|---|---|
| `src/basketball_ai_lab/` | Motor, normalización, proveedores, cuotas opcionales y auditoría |
| `tests/` | Pruebas con calendarios y precios simulados, sin usar claves |
| `data/` | Archivo original de pronósticos, resultados, equipos y CSV (no se mezcla con fútbol) |
| `site/` | Dashboard HTML/CSS/JS, PWA y datos JSON publicables |
| `.github/workflows/` | CI, actualización diaria, GitHub Pages |
| `docs/` | Fuentes, costes, permisos y siguientes pasos |

## Ejecutar localmente

Sin dependencias de Python fuera de la biblioteca estándar:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
node --test site/tests.mjs
PYTHONPATH=src python -m basketball_ai_lab doctor
PYTHONPATH=src python -m basketball_ai_lab update --output data --site site/data
PYTHONPATH=src python -m basketball_ai_lab doctor --require-live
python -m http.server 8000 --directory site
```

En Windows PowerShell:

```powershell
$env:PYTHONPATH = 'src'
py -m unittest discover -s tests -v
py -m basketball_ai_lab doctor
py -m basketball_ai_lab update --output data --site site/data
py -m basketball_ai_lab doctor --require-live
py -m http.server 8000 --directory site
```

Abrir `http://localhost:8000` en el navegador. La **primera ejecución real necesita conexión a internet** y que la fuente ESPN sea accesible. Si el endpoint devuelve errores o bloquea GitHub Actions, el proyecto debe conservar archivos e indicar la incidencia; no se engaña al usuario con datos inventados.

## Proyecto publicado e instalación móvil

El repositorio ya está publicado en [rasekes86/basketball-ai-lab](https://github.com/rasekes86/basketball-ai-lab) y su web/PWA está en **https://rasekes86.github.io/basketball-ai-lab/**.

En Android, abre la web desde Chrome y toca **Instalar**. Si no aparece un aviso automático, pulsa el menú ⋮ → Instalar aplicación (o Añadir a pantalla de inicio). El icono quedará entre tus apps; la web se abre sin barra del navegador. El panel utiliza conexión para actualizar cuotas y resultados, aunque el interfaz básico queda cacheado.

GitHub Actions ejecuta actualización NBA diaria, pruebas y publicación Pages. El Top 3 conserva resultados verificables y los antiguos sustituidos a petición expresa se separan del balance. Los logos de las 30 franquicias se muestran desde la fuente ESPN o se sustituyen por las siglas si no cargan.

## Límites y honestidad

- El estado inicial de `site/data` no contiene partidos inventados, pronósticos ni cuotas. La captura en vivo no ha sido validada desde este entorno de ejecución por falta de acceso DNS en el contenedor; **32 pruebas Python y 5 pruebas Node** usan fuentes simuladas o inspeccionan el código. Además se probó la web con Chromium y datos en memoria en tres tamaños de pantalla. Nada de esos datos sintéticos se publica en `site/data`.
- Los endpoints ESPN son accesibles públicamente, **no una API formal para terceros**; su estabilidad y condiciones de uso no están garantizadas. Las marcas y escudos de las franquicias pertenecen a sus titulares. El uso y exposición pública requieren revisar licencias y términos.
- Las predicciones son **NO CALIBRADAS**. Las probabilidades `1/p` solo generan cuotas matemáticas teóricas, nunca ganancias verificadas.
- Sin ofertas reales válidas antes del salto inicial, la adicional queda **ausente**. No se mezclan apuestas exploradas con el 3+1.
- No se modifica, referencia ni reutiliza ningún workflow ni secreto de Football AI Lab.

Fuentes y límites verificados: [docs/FUENTES_Y_COSTES.md](docs/FUENTES_Y_COSTES.md).

## Activar The Odds API y consultar el 3+1

La captura se habilita **automáticamente** cuando existe el secreto de repositorio `ODDS_API_KEY` en GitHub Actions. No hace falta crear otra variable. Sin clave no se realizan solicitudes al proveedor, ni se muestran cuotas ficticias. Las capturas son de `basketball_nba`, mercados `h2h,spreads,totals` y región `us`; el consumo interno está limitado a una captura por día UTC y 100 créditos mensuales.

1. Consigue la clave en https://the-odds-api.com/.
2. Guarda `ODDS_API_KEY` en [Actions Secrets](https://github.com/rasekes86/basketball-ai-lab/settings/secrets/actions).
3. Ejecuta `Basketball AI Lab · actualización NBA` desde la pestaña Actions y confirma `odds_status` en `data/status.json`.
4. Consulta la **adicional +1,50** de cada ficha. Si no hay una oferta real que pase los filtros, el cuarto pronóstico queda vacío; no se inventa.

Guía móvil y activación detallada: [docs/ACTIVAR_ODDS_API_PWA.md](docs/ACTIVAR_ODDS_API_PWA.md).

Las probabilidades son experimentales, no calibradas para apostar dinero. Las cotizaciones de la región estadounidense pueden no corresponder a operadores disponibles en España. Football AI Lab permanece independiente.
