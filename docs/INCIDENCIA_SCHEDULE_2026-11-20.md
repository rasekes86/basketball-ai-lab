# Incidencia de programación NBA · 20/11/2026

## Diagnóstico verificable
- El repositorio principal contiene `.github/workflows/nba-daily.yml`.
- Cron anterior: `17 9,14 * * *` (UTC).
- No existe en el historial consultado ninguna ejecución `schedule` del día 20 a las 09:17 o 14:17 UTC. La última actualización fiable antes de corregir el problema era del 20/11 a las 06:58 UTC, activada por `push`.
- GitHub registró un `schedule` el 19/11 a las **18:16:32 UTC**, fuera de esas franjas. No es posible deducir con certeza su causa o la hora exacta a la que se entregó el evento.
- Los runs `push`, la validación, la publicación web y el procesamiento de ESPN sí se completaron con éxito.
- GitHub documenta que `schedule` se puede retrasar u omitir por carga; un evento perdido no crea un run fallido en el historial.
- No hay evidencia de que la causa sea un secreto vencido, una cuota mensual o un error del código.

## Mitigación
- Modificar cron (también reactiva un schedule que hubiera quedado desactivado) y escalonar tres horarios: **09:23, 14:41 y 19:47 UTC**.
- Conservar `workflow_dispatch` para ejecución manual y `push` para verificación inmediata.
- Conservar el límite de una petición de The Odds API diaria.
- Aviso de información antigua en la interfaz tras **24 horas** sin actualización.

## Limitación
No se puede demostrar que el scheduler se haya recuperado mediante una prueba iniciada por `push`. Solo una ejecución posterior con evento `schedule` validará el arreglo. Si los tres horarios dejan de llegar, hace falta un disparador/monitor externo independiente de GitHub (p. ej., cron externo o una comprobación programada externa) para garantizar un aviso.

Fuentes:
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://github.com/rasekes86/basketball-ai-lab/actions/workflows/nba-daily.yml
