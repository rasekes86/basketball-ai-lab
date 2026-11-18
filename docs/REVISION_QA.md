# Revisión técnica de entrega — 18/11/2026

## Resultados comprobados sin servicios externos

- **32 pruebas Python** de motor, proveedor, normalización, seguridad, calendarios, histórico 3+1, cuotas opcionales, CSV y auditoría.
- **5 pruebas Node.js** de web, catálogo de equipos, diseño, rutas PWA y ausencia de dependencias inseguras.
- Compilación y sintaxis de Python y JavaScript correctas.
- **Prueba real de interfaz Chromium** en escritorio de 1440 px y móviles de 390 y 360 px. Navegación, cambio claro/oscuro, pantalla de 30 equipos y calidad por mercado sin errores JS ni scroll horizontal.
- Las pruebas visuales usaron **datos de prueba en memoria y URLs de escudos simuladas** únicamente para probar el fallback de siglas. No son resultados ni logos publicados.
- `doctor` sin red devuelve **PENDING_LIVE**, que es intencionado antes del primer calendario real.

## Aspectos que quedan pendientes de verificación externa

1. **Primer acceso real a ESPN desde GitHub Actions**. Aquí el entorno no resuelve DNS, así que no afirmamos que la fuente responda desde un runner.
2. **Carga visual de los 30 escudos reales**. El código procesa las URLs proporcionadas por ESPN y no inventa enlaces. La cifra de `logo_coverage` mide URLs, no imágenes descargadas ni HTTP 200.
3. **Despliegue de GitHub Pages** después de crear el repositorio y elegir la fuente GitHub Actions en Settings.
4. **Cuotas reales**: sin clave, 0 consultas. La primera consulta real es voluntaria y se realizará más adelante, tras revisar las condiciones del plan gratis.

## Protecciones relevantes

- No modifica Football AI Lab ni utiliza rutas, tokens ni datos del fútbol.
- Circuit breaker de ESPN en 403/429 o tres errores de red y ante esquema de calendario inválido.
- Si fallan todos los calendarios, conserva los archivos originales y no genera pronósticos nuevos.
- Solo predice partidos realmente observados en la ronda actual.
- No entrena con pretemporada ni con partidos posteriores a la fecha del pronóstico.
- No reescribe pronósticos archivados. Reprogramaciones o marcadores corregidos quedan en `data/review_flags.json` para revisión.
- El Top 3 tiene líneas **teóricas**. Una adicional requiere oferta real, equipo/casa/evento/hora identificados, EV teórico y cuota >1,50.
- El CSV publicado en `site/reports/` coincide con las rutas de descarga de la web.
- Imágenes externas solo desde dominios de escudos admitidos y sin credenciales embebidas.

## Comprobación tras la subida

GitHub ejecutará las pruebas. Tras descargar el primer calendario, el workflow ejecuta:

```bash
PYTHONPATH=src python -m basketball_ai_lab doctor --require-live
```

Debe devolver **OK** o mostrar advertencias de cobertura. Si devuelve **ERROR**, la publicación de datos se detendrá y será necesario consultar los logs. En cualquier caso, no se suplantan estadísticas faltantes por cifras inventadas.
