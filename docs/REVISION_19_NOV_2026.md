# Revisión NBA del 19-11-2026 · MIL–POR y adicionales reales

## Incidencia constatada

Los dos Top 3 de MIL–POR con probabilidad inferior al 55 % se archivaron el 18/11/2026 a las 23:11:36 UTC, **antes** de la publicación del nuevo selector de probabilidad mínima de 55 % (commit `2cf41d0307`, 23:58:10 UTC).

- `POR: UNDER 47.5 rebotes`: 53,0144 %.
- `Gana POR`: 53,3473 %.

Son selecciones heredadas de otra política, no prueba de que el algoritmo actual vuelva a generar pronósticos por debajo del mínimo.

## Corrección prepartido excepcional

El usuario ha autorizado revisar estas selecciones antes de su inicio. La solicitud de actualización limita el refresco **exclusivamente** al encuentro ESPN `401910020` (MIL–POR). El motor guarda las tres selecciones anteriores en `data/superseded_top3.json` con motivo `USER_REQUESTED_PREGAME_RESELECTION`. Los otros tres encuentros permanecen congelados.

Las nuevas selecciones únicamente se archivan al recibir el calendario real en la ejecución y si pasan el selector actual. Si hay menos de tres candidatas admisibles, no se inventan otras.

## Cuatro adicionales con precio real

Los partidos ESPN `401910019` (MEM–GSW), `401910020` (MIL–POR), `401910021` (MIN–NYK) y `401910022` (SAS–LAC) comienzan el 20/11/2026 a la 01:00 UTC (02:00 Madrid).

El proveedor ya se consultó el 19/11 UTC. Por autorización explícita se permite **una única segunda consulta extraordinaria ese mismo día**, siempre que quede presupuesto interno del mes (3 créditos esperados), antes del inicio. La nueva captura queda señalada en `odds_recheck_day` y no puede repetirse sin cambiar la fecha; la solicitud se marca procesada aunque no aparezca ninguna selección válida.

Solo se guarda una adicional si coincide el ID/correspondencia del partido, local/visitante, hora, precio real prepartido superior a 1,50, `probability >= 0.53`, EV experimental >= 2,5 %, y no repite un contrato original. Ninguna cuota ausente se sustituye con precios teóricos.

El campo `odds_quoted_outcomes_this_run` indica cuántos precios se recibieron y `odds_recheck_result` indica el estado de la solicitud. Ninguna acción modifica resultados ya liquidables ni el funcionamiento de Football AI Lab.

## Pruebas

```bash
PYTHONPATH=src python -m unittest discover -s tests -q
PYTHONPATH=src python -m basketball_ai_lab doctor --require-live
```
