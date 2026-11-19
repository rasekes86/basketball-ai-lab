# Instrucciones permanentes para agentes · Basketball AI Lab

Proyecto NBA independiente de Football AI Lab. Antes de cambiar el modelo leer `README.md` y `docs/SKILLS_NBA_Y_BACKTEST.md`.

## Skills específicas de Codex

- Para datos, NBA, ESPN, fuentes y jugadores: `.agents/skills/nba-data-research/SKILL.md`.
- Para validación, calidad de mercados, calibración y backtesting: `.agents/skills/nba-model-validation/SKILL.md`.

Codex descubre skills de proyecto en `.agents/skills` si está trabajando dentro de este repositorio. En entornos que no las enumeren automáticamente, leer esos SKILL.md explícitamente.

## Invariantes no negociables

- No cambiar, recalcular ni reescribir apuestas Top 3 +1 ya iniciadas, selecciones congeladas, probabilidades, cuotas, casas o timestamps.
- No usar etiquetas finales, box scores o informes de lesiones posteriores a T como predictores prepartido.
- No presentar retrospectivas como resultados prospectivos ni cuotas matemáticas como ofertas reales.
- El backtesting es autónomo y solo escribe `research/`. Nunca debe alterar el calendario, la web, los secretos ni los balances.
- No utilizar datos falsos en la producción. Las pruebas pueden usar fixtures sintéticos etiquetados como tales.
- No instalar ni ejecutar paquetes/scripts externos sin revisión de origen, permisos, licencia y costes.
- Evitar nuevas peticiones externas en GitHub Actions. No usar credenciales del repositorio de fútbol.
- Ejecutar las pruebas unitarias y CI antes de integrar una mejora.
