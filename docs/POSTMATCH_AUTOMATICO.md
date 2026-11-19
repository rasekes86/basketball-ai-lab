# NBA · comprobaciones pospartido automáticas

Basketball AI Lab consulta resultados NBA sin intervención manual mediante GitHub Actions:

- Primera comprobación: 09:17 UTC (10:17 en Madrid durante el horario de invierno).
- Segunda comprobación: 14:17 UTC (15:17 en Madrid durante el horario de invierno).
- Estas horas se desplazan una hora local en verano. GitHub Actions puede ejecutar los cron con cierto retraso.
- El panel GitHub Pages se publica automáticamente tras un workflow NBA satisfactorio.

## Qué verifica
1. ESPN scoreboard devuelve partido FINAL y marcador consistente.
2. La API ESPN summary devuelve las estadísticas de cada equipo: triples, rebotes y asistencias.
3. `settle_one` compara cada predicción prepartido congelada contra su contrato original. Si no hay estadísticas suficientes, permanece `PENDIENTE` y no computa como pérdida.
4. Se liquidan solamente las tres selecciones originales y la adicional registrada con cuota real, separando los balances hipotéticos.
5. El historial permanece inmutable salvo el estado de liquidación, y se publican CSV, estado y panel.

## Reintentos y límites
- Se respeta una espera de al menos cinco horas desde el inicio antes de solicitar un box score.
- Si falta una estadística necesaria para una predicción **ya finalizada**, el summary se vuelve a intentar a partir de cuatro horas desde el intento previo, durante cuatro días tras el inicio.
- Para backfill histórico antiguo, los reintentos fallidos siguen espaciados siete días.
- El total de consultas ESPN está limitado por el presupuesto del workflow. Si no hay datos, se conserva PENDIENTE.
- The Odds API mantiene **una consulta como máximo por día UTC** y su presupuesto mensual conservador, independientemente de estas dos revisiones.

## Dónde mirar
- GitHub Actions: https://github.com/rasekes86/basketball-ai-lab/actions/workflows/nba-daily.yml
- PWA: https://rasekes86.github.io/basketball-ai-lab/
- `data/status.json`: `new_settlements`, `top3_evaluated`, `extras_evaluated`, `pending_postmatch_selections`, `pending_postmatch_team_stats` y balance teórico.

Nota: los pronósticos Top 3 usan cuotas equivalentes matemáticas (no precios ofrecidos); la adicional tiene una cuota real observada, pero el beneficio calculado es igualmente una simulación y no una apuesta efectivamente realizada.
