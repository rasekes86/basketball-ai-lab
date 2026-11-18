# Recuperación de 30 escudos NBA

1. Identificar franquicias por abreviatura oficial conocida (`teams.py`), no por similitud textual de nombres parciales.
2. Consultar una vez al inicio y aproximadamente una vez por mes el catálogo `ESPN /teams`.
3. Extraer `team.logos[].href` o `team.logo` **solo si la propia respuesta incluye una URL HTTPS de `a.espncdn.com`, `a1.espncdn.com` o `cdn.nba.com`**; no se fabrican enlaces a base de nombres.
4. Si el catálogo falla, conservar logos previos y aprovechar la imagen publicada en cada equipo dentro del `scoreboard`.
5. Guardar en `data/teams.json` y copiar a `site/data/teams.json`. El número de URLs de escudos recuperadas estará en `data/status.json`, `logo_coverage`. Esta cifra mide **URLs válidas**, no garantiza que las 30 imágenes respondan HTTP 200 en cada país o navegador; la carga visual debe verificarse en la PWA.
6. UI: escudos de **62px escritorio, 54px móvil, 49px móviles estrechos**; cuadrícula de equipos con emblemas de 64–82px.
7. Si la URL externa deja de cargar, sustituir por las siglas `ATL`, `BOS`, etc. Ningún icono roto ni escudo de otro club.
8. No descargar ni empaquetar imágenes con copyright sin permiso: los logos son propiedad intelectual de sus titulares. Validar condiciones para publicar externamente.

La lista local contiene las **30 franquicias** incluso antes de contactar con ESPN, pero sus campos `logo` permanecen vacíos. No se afirma que los 30 iconos se hayan obtenido hasta que `logo_coverage = 30` tras una ejecución real.
