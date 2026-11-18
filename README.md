# Basketball AI Lab · NBA

Proyecto experimental **nuevo e independiente** de Football AI Lab. Versión 0.2.0 (18/11/2026).

**Objetivo:** pronosticar partidos de NBA antes de su inicio, archivar tres mercados teóricos, liquidar los resultados cuando se confirme el marcador y, en una fase opcional, registrar una apuesta experimental adicional con **cuota real prepartido superior a 1,50**. No ejecuta apuestas ni promete resultados.

## Qué incluye ahora

- Fuente inicial **sin registro ni clave**: calendario y marcadores del endpoint público no documentado de ESPN.
- Identificación exacta de las **30 franquicias NBA** y sus logos obtenidos del catálogo/partidos ESPN. Si un escudo falla, aparece la abreviatura, **sin inventar imágenes**.
- Motor propio de puntos a favor/en contra con regularización y ponderación de partidos recientes. No usa Poisson de fútbol ni datos posteriores al pronóstico.
- **Top 3** por encuentro: ganador, puntos totales y hándicap **teóricos**; no confundir con mercados/cuotas ofrecidos. Si faltan al menos 5 encuentros anteriores por equipo, se abstiene.
- Archivo inmutable de pronósticos con sello temporal; evaluación postpartido de **solo** esos tres mercados.
- Preparación de adicional >1,50 con **The Odds API**, desactivada por defecto. Requiere una clave del proveedor y activación voluntaria, no hay cuotas fabricadas.
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

## Publicar en GitHub: intervención futura del propietario

Esta entrega contiene **todos los archivos**, pero no está conectada a un repositorio remoto nuevo porque la integración GitHub disponible en esta sesión **no tiene la operación de crear repositorios** y no se debe tocar `football-ai-lab`.

1. Crear un repositorio **público** vacío denominado `basketball-ai-lab` en tu cuenta de GitHub. No marcar README automático (ya existe).
2. **Descomprimir el ZIP y subir sus archivos** al repositorio nuevo, conservando `.github/workflows` (por Git, GitHub Desktop o Codex). No subas el ZIP sin descomprimir. Tienes pasos detallados en [`docs/SOLO_SUBIR_GITHUB.md`](docs/SOLO_SUBIR_GITHUB.md).
3. En GitHub: **Settings → Actions → General**, verificar que se permiten las acciones y que los workflows tienen permiso para escribir contenido si se requiere (el workflow declara `contents: write`).
4. En **Settings → Pages → Build and deployment → Source**, seleccionar **GitHub Actions**.
5. En **Actions**, ejecutar manualmente `Basketball AI Lab · actualización NBA` si la ejecución inicial no arranca con el primer push.
6. Verificar `data/status.json`: `source_successful_days > 0`, `logo_coverage` y `top3_archived`. Una vez publicada, la web estará habitualmente en `https://TU-USUARIO.github.io/basketball-ai-lab/`.

**No es necesario crear claves ni Google Sheets** para el calendario, historial y los Top 3. Véase [PLAN_DE_ACTIVACION](docs/PLAN_DE_ACTIVACION.md).

## Límites y honestidad

- El estado inicial de `site/data` no contiene partidos inventados, pronósticos ni cuotas. La captura en vivo no ha sido validada desde este entorno de ejecución por falta de acceso DNS en el contenedor; **32 pruebas Python y 5 pruebas Node** usan fuentes simuladas o inspeccionan el código. Además se probó la web con Chromium y datos en memoria en tres tamaños de pantalla. Nada de esos datos sintéticos se publica en `site/data`.
- Los endpoints ESPN son accesibles públicamente, **no una API formal para terceros**; su estabilidad y condiciones de uso no están garantizadas. Las marcas y escudos de las franquicias pertenecen a sus titulares. El uso y exposición pública requieren revisar licencias y términos.
- Las predicciones son **NO CALIBRADAS**. Las probabilidades `1/p` solo generan cuotas matemáticas teóricas, nunca ganancias verificadas.
- Sin ofertas reales válidas antes del salto inicial, la adicional queda **ausente**. No se mezclan apuestas exploradas con el 3+1.
- No se modifica, referencia ni reutiliza ningún workflow ni secreto de Football AI Lab.

Fuentes y límites verificados: [docs/FUENTES_Y_COSTES.md](docs/FUENTES_Y_COSTES.md).
