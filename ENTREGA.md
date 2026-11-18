# Estado de la entrega · 18 de noviembre de 2026

## Hecho y comprobado en entorno local

- Proyecto nuevo, sin dependencia de football-ai-lab.
- Ingesta NBA ESPN sin claves, catálogo 30 equipos, tratamiento de marcadores y URLs seguras de sus escudos.
- Predicción original Top 3, archivo prospectivo inmutable, comparación postpartido, indicadores de acierto y Brier.
- Detección de sorpresas definida por el modelo con un umbral del 60 %.
- The Odds API opcional, desactivada por defecto; máximo un intento diario y 100 créditos/mes programados como límite conservador, sin compartir clave de fútbol.
- CSV de Excel sin conexión a Google Sheets, con rutas descargables reparadas (`site/reports/`), informe de cobertura de logos y errores del proveedor.
- Auditoría automática `doctor` que valida que el Top 3 se creó antes del partido, la trazabilidad de la adicional, resultados, estado web y escudos.
- Protección ante 403/429 y tres fallos consecutivos del proveedor. Partidos reprogramados o corregidos quedan señalados para revisión, sin recalcular ni modificar las predicciones originales.
- Acierto y Brier por mercado: ganador, puntos totales y hándicap.
- Dashboard claro/oscuro y PWA para móvil con escudos grandes, 30 clubes, resultados 3+1 y fichas.
- Workflows independientes: CI, cálculo diario y GitHub Pages.
- 32 pruebas Python y 5 pruebas JavaScript superadas (37 en total), todas sin claves ni consultas externas. Revisado el proyecto en Chromium con datos sintéticos exclusivamente en memoria, escritorio y dos tamaños de móvil (360 y 390 px), sin errores de ejecución ni desbordamientos horizontales.
- Revisión visual de tema claro/oscuro y cuadrícula de 30 equipos con datos iniciales vacíos.

## Pendiente por requerir intervención o acceso externo

1. Crear/repositorio público `basketball-ai-lab` en GitHub y subir estos archivos.
2. Activar Pages en dicho repositorio, seleccionar GitHub Actions como fuente. El paquete tiene scripts para subirlo sin tener que recrear los archivos manualmente.
3. Ejecutar la primera actualización en un runner con acceso a ESPN para validar de verdad el calendario y recuperar los escudos (aún no hay imágenes reales descargadas en esta entrega).
4. Observar varias jornadas para medir Brier/acierto y si ESPN limita la conexión.
5. Solo si se desean cuotas: registrar una clave propia gratuita, añadir secret `ODDS_API_KEY` y habilitar la variable `ENABLE_ODDS=true` en este nuevo repositorio.

**Importante:** esta entrega no asegura que el endpoint no oficial de ESPN responda desde GitHub Actions. Su acceso no está garantizado, y la publicación de datos y marcas requiere verificar derechos de uso. Mientras no haya actualización real, los paneles no enseñan partidos ficticios ni cifras simuladas como si fueran reales.

Para instrucciones detalladas: `README.md`, `docs/SOLO_SUBIR_GITHUB.md` y `docs/PLAN_DE_ACTIVACION.md`.

**Auditoría en esta entrega:** `PYTHONPATH=src python -m basketball_ai_lab doctor` devuelve **PENDING_LIVE**, que es el estado correcto antes de ejecutar una primera captura real desde GitHub. No es un fallo ni un falso éxito de conectividad.
