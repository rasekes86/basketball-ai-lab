# Pendiente de intervención del propietario (priorizado)

## Bloque A · activar gratis, sin nuevos proveedores (necesario)

1. Crear en GitHub el repositorio público **basketball-ai-lab** y subir el ZIP **descomprimido**. Sigue `docs/SOLO_SUBIR_GITHUB.md`: la subida del ZIP intacto no extrae su contenido automáticamente.
2. Activar GitHub Pages → Source → GitHub Actions.
3. Lanzar **Basketball AI Lab · actualización NBA**. Revisar que la primera ejecución del nuevo repositorio acceda al calendario NBA, actualice `site/reports/` y recupere URLs de los escudos en `data/teams.json`. El workflow ejecuta `doctor --require-live` tras la captura.
4. Abrir la PWA, comprobar en el teléfono los 30 equipos, tema claro y oscuro, agenda y fichas. Si `logo_coverage < 30`, verificar conectividad de ESPN/imagen y mantener el fallback, sin inventar escudos.
5. Dejar el sistema sin cuotas reales durante varias jornadas. Medir el Top 3 de predicciones prospectivas y su Brier antes de sacar conclusiones.

## Bloque B · activar precios si decides registrar una clave gratuita (opcional)

1. Crear cuenta propia gratuita en The Odds API. Revisar que el plan sigue siendo gratuito, los mercados ofrecidos y restricciones para uso desde España.
2. Añadir `ODDS_API_KEY` en **Settings → Secrets and variables → Actions → New repository secret** del nuevo repositorio. Nunca pegar el token en el código o chat.
3. Añadir variable de repositorio **ENABLE_ODDS=true**. Por defecto está desactivada y no consume un solo crédito.
4. Ejecutar una actualización y comprobar `data/status.json`: `odds_status`, `odds_calls_month`; verificar que las ofertas registradas se asocian a la misma franquicia/localía y tienen sello anterior al inicio.
5. Las adicionales solo aparecerán si hay una oferta válida >1,50 que supera filtros conservadores del motor; de lo contrario, queda explícito «sin adicional».

## Bloque C · posibles ampliaciones, solo tras validar el núcleo

- Incorporar lesiones con fuentes contrastadas y capturas congeladas ANTES del análisis, sin usar novedades retrospectivas.
- Evaluar fuentes de datos de jugadores y mercados props únicamente si existen límites gratuitos suficientes.
- Integrar una hoja Google Sheets **independiente** del fútbol solo si aporta valor; CSV/Excel ya funciona sin esta cuenta.
- Crear bot de Telegram nuevo si se necesita; no compartir tokens ni chat ID del proyecto de fútbol.
- Verificar permisos de reproducción pública de logos y demás contenido de proveedores.

## Instrucción lista para Codex (cuando tengas el repositorio creado)

«Descomprime la carpeta basketball-ai-lab entregada, crea git en ella si todavía no existe, enlázala al repositorio NUEVO rasekes86/basketball-ai-lab y súbela a main sin modificar rasekes86/football-ai-lab. Comprueba las 32+ pruebas Python, las 5 pruebas Node, `doctor` y los workflows NBA y el despliegue Pages. No habilites ENABLE_ODDS ni uses cuotas si no existe una clave propia de ese repositorio. Revisa el primer status.json y los 30 logos; informa de cualquier 403/429 de ESPN sin intentar esquivarlos.»
