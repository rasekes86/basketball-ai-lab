# Diseño conservador del motor NBA

## Fronteras respecto del fútbol

No se lee, escribe, importa o referencia ningún fichero de `football-ai-lab`, sus secrets, cron, API keys, Google Sheets o Telegram. El único elemento compartido es el lenguaje y el patrón metodológico general.

## Datos, predicción y liquidación

1. Calendarios por día (`ESPN scoreboard`); bootstrap 45 días retrospectivos y 7 futuros; después 4 retrospectivos y 7 futuros. Se conservan partidos anteriores de ejecuciones previas y nunca se degrada un encuentro FINAL a SCHEDULED. Solo se admiten partidos de temporada regular y playoffs; no se utilizan resultados de pretemporada como base estadística.
2. Escudos/identidades mediante catálogo ESPN mensual y fallback del propio marcador.
3. Pronósticos con datos de partidos confirmados *antes* de la hora de archivo. Media regularizada de puntos a favor/en contra, pesos temporales con semivida 24 días, prior equivalente a 7 partidos y ventaja local simplificada. **No se ha calibrado**, no incluye lesiones ni jugadores.
4. Exigir al menos 5 partidos anteriores por cada franquicia, y verificar que el evento concreto fue observado en la ronda actual (no basta con tener datos antiguos sobre el partido). Para cada encuentro futuro: congelar un `winner`, `total`, `handicap`, todos con probabilidad, fecha de archivo y contrato liquidable. No modificarlos después.
5. La adicional, si se habilita, exige cuota real de un bookmaker concreto, cruce idéntico de local/visitante, diferencia de horario <=1h y actualización de cuota anterior al partido. Solo moneyline en la primera versión. No se archiva si no supera 1,50 y otros filtros.
6. Liquidar únicamente el 3+1: acierto, fallo o pendiente. Los partidos sin marcador verificable permanecen pendientes y no se puntúan.
7. Publicar estado, resultado y CSV Excel en `data/reports/` y `site/reports/`; calcular acierto y Brier global y por mercado para pronósticos archivados, y ROI simulado únicamente con ofertas verificadas antes del partido.
8. Circuit breaker: tras 403, 429 o tres fallos consecutivos de red no se envían más peticiones a ESPN en esa ejecución. Si todas fallan, no se publican falsas actualizaciones.
9. Reprogramaciones de más de 2 h, cambios de rivales y correcciones de marcador tras archivar pronósticos pasan a `data/review_flags.json` y requieren revisión manual antes de seguir liquidando. Nunca se borra ni reescribe silenciosamente el Top 3.

## Metodología y restricciones

- Las líneas totales/hándicap del Top 3 son **teóricas**, calculadas por el modelo, NO equivalentes a líneas que un operador haya ofrecido.
- Un pronóstico no debe convertirse en recomendación de apuesta. El modelo no incorpora lesiones, alineaciones, descanso por viaje, ritmo ajustado de posesiones ni superioridad por rival de manera robusta.
- Los pronósticos pueden estar correlacionados; Top 3 no se presenta como tres eventos independientes.
- Brier y porcentajes solo incluyen picks realmente archivados prospectivamente; nada de «backtest» añadido al histórico como si fueran apuestas de aquella fecha.
- «Sorpresa» = favorito elegido con >=60 % que terminó derrotado; interpretación definida por modelo, no por casa de apuestas.
- Fuente ESPN es pública, no contrato técnico garantizado. No reintentar errores 403/429 ni rodear sistemas de acceso.
