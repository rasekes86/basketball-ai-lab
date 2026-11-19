# Investigación de skills NBA y laboratorio de validación

Fecha de revisión: 19 de noviembre de 2026.

## Fuentes contrastadas

1. **Machina Sports · nba-data** — https://github.com/machina-sports/sports-skills/tree/main/skills/nba-data — licencia MIT en su repositorio. Skill/documentación para consultar ESPN y NBA Stats. La CLI `sports-skills` no se ha instalado ni ejecutado en GitHub Actions. Al usar NBA Stats y ESPN conjuntamente los IDs de partido son distintos y requieren cruce cuidadoso. El acceso público no garantiza disponibilidad permanente, permiso de redistribución ni datos as-of.
2. **WalrusQuant · sports-analytic-skills** — https://github.com/WalrusQuant/sports-analytic-skills — licencia MIT. Revisadas `validation-design`, `leakage-audit` y `baseline-models`: splits temporales, comprobación de fuga de objetivos, modelos de referencia, métricas y control de promoción de modelos. No se copian ni ejecutan sus scripts, varios requieren pandas/scikit-learn.
3. **SportsDataverse Python** — https://github.com/sportsdataverse/sportsdataverse-py — referencia futura para acceso a datos y análisis. No se instala ni se presenta como fuente activa; requiere revisar versión, dependencias y términos concretos del proveedor de datos.

Se han incorporado dos skills propias, independientes y auditables en `.agents/skills`, a partir de estas ideas. No implican suscripciones, claves ni nuevos procesos persistentes.

## Auditoría de seguridad y dependencias

- Los archivos upstream revisados son guías e instrucciones, no dependencias ejecutadas. Las skills locales son únicamente Markdown y no solicitan credenciales ni invocan redes.
- No se usa `pip install sports-skills`, `npx skills add`, ni se añade `sportsdataverse-py` al entorno de producción. Evitamos introducir código/SDK ajeno a GitHub Actions sin evaluar su cadena de suministro.
- Para nuevas capturas: validar ID de evento, fecha en UTC, equipos, proveedor, sesgos de cobertura, privacidad y términos; proteger la cuenta frente a API keys y revisar rate limits.
- Se preservan `data/games.json`, `data/picks.json`, `data/extras.json`, `data/boxscores.json`, `site/` y toda la liquidación 3+1.

## Carta de validación v0.1

**Unidad:** un partido NBA, sus 1–3 selecciones generadas antes de T con líneas fijadas. Toda comparación se hace a partir del mismo contrato de la línea.

**Momento T:** cinco minutos antes del salto inicial; un juego previo solo es candidato a historial cuando empezó hace más de cinco horas.

**Datos:** los marcadores ya archivados de ESPN y box scores verificados. Dos modos de análisis que NO se mezclan:
- `strict_captured`: datos estadísticos realmente capturados (`retrieved_utc <= T`). Es el único modo con evidencia de fecha de descarga, aunque no prueba por sí solo todas las características del proveedor en ese instante.
- `historical_reconstruction`: box scores históricos capturados más tarde, usando únicamente partidos anteriores a T y simulando su disponibilidad después del embargo. **NO ES una evaluación as-of verificable**. Se etiqueta exploratoria, y nunca activa mercados automáticamente.

**Primario:** Brier medio binario por línea. **Secundarios:** logloss, ECE por intervalos, tasa de acierto, comparación de baseline y cobertura por partidos únicos. **Baselines:** frecuencia pre-evento suavizada de victoria local, total de puntos, margen local, o rendimiento previo del equipo en esa estadística y umbral.

**Partición:** rolling-origin en orden temporal; agrupación de selecciones por ID de partido. Resultados por ventana temporal y categoría. Sin tuning sobre el conjunto evaluado. Mantener un futuro holdout de nuevas predicciones archivadas para promover modelos.

**Puerta de promoción:** la investigación nunca cambia el selector operativo. Un mercado necesita más encuentros y evidencia prospectiva independiente, comprobación de calibración y revisión humana antes de modificarlo.

**Límites:** los históricos disponibles son recientes, varias selecciones de un partido se correlacionan, se desconoce la versión exacta de algunos box scores antiguos en T y faltan lesiones/rotaciones. Ninguna prueba retrospectiva demuestra ventaja sobre cuotas reales.

## Ejecutar sin instalar nada

```bash
PYTHONPATH=src python -m basketball_ai_lab.research --games data/games.json --boxscores data/boxscores.json --output research/walkforward_report.json
PYTHONPATH=src python -m unittest discover -s tests -q
```

El archivo `research/walkforward_report.json` se publica en el repositorio para revisión, sin incorporarse al ROI ni a los pronósticos de la PWA. La automatización de estudio es independiente de la actualización/puja de cuotas NBA.
