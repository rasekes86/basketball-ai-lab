---
name: nba-model-validation
description: Diseñar y auditar backtesting NBA, walk-forward, baselines, calibración y filtros de calidad para Basketball AI Lab sin contaminación futura ni revisión retroactiva de pronósticos.
---

# NBA Model Validation · Basketball AI Lab

Úsala para investigar por qué el Top 3 tiene probabilidades cercanas a 85 %, comparar con fútbol y evaluar nuevas variables/modelos.

## Protocolo de validación obligatorio

1. Fijar antes de analizar: objetivo, evento, hora T de predicción, mercado y contrato de línea, dataset, columnas, horizonte y separación entrenamiento/evaluación.
2. Agrupar todas las selecciones de un partido en un mismo test. Ordenar por `start_utc`, sin dividir aleatoriamente el tiempo.
3. Solo permitir entrenamiento y features de partidos anteriores a T con embargo apropiado. Las etiquetas, marcador y box scores del evento objetivo nunca entran como features.
4. Distinguir en todo informe **prospectivo archivado** de **retrospectivo reconstruido**. Si un box score fue descargado después de T, su valor puede apoyar un escenario reconstruido, pero NO prueba disponibilidad histórica en T; debe etiquetarse explícitamente.
5. Pre-registrar baseline sencillo por mercado; comparar sobre las mismas filas con Brier, logloss, ECE, frecuencia observada, cobertura y número de partidos distintos.
6. Reportar por mercado y por bloques temporales: resultados, umbrales evaluados, falta de muestras, filas descartadas y tasas faltantes. No esconder categorías perdedoras.
7. Nunca elegir líneas del test en función del resultado final. Se permiten líneas estáticas definidas antes del test y elegidas por el selector tal cual; no reoptimizar con el holdout.
8. **No promover ningún mercado automáticamente** por un backtest. Exigir protocolo de revisión, suficiente cobertura, evidencia retrospectiva replicable y validación prospectiva posterior.
9. Mantener el histórico Top 3 +1 y odds inmutables; los experimentos escriben SOLO en `research/`, nunca en `data/picks.json`, `data/extras.json`, `site/data` ni workflows de pronósticos.
10. Evitar falsos ROI: Top 3 a cuota `1/p` son hipótesis matemáticas, no precios ejecutables; el +1 usa precios observados sin demostrar ventaja.
11. No mezclar rendimiento de mercados seleccionados con los de todas las líneas exploradas.
12. Si hay filtración o incertidumbre de timestamps, emitir `REVIEW_REQUIRED` y suspender afirmaciones de ventaja.

## Ejecutar

```bash
PYTHONPATH=src python -m basketball_ai_lab.research --games data/games.json --boxscores data/boxscores.json --output research/walkforward_report.json
PYTHONPATH=src python -m unittest discover -s tests -q
```

## Métodos de referencia revisados

- WalrusQuant: `validation-design`, `leakage-audit`, `baseline-models`, `calibration-check`, `feature-rules`, https://github.com/WalrusQuant/sports-analytic-skills (MIT).
- Machina NBA Data: https://github.com/machina-sports/sports-skills/tree/main/skills/nba-data (MIT).

Estas reglas son propias de este proyecto. No se ejecutan scripts de terceros ni se añaden dependencias sin auditoría.
