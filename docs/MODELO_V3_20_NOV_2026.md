# NBA_CONTEXT_V3 — cambio prospectivo del 20-11-2026

## Alcance autorizado
A partir de los encuentros aún no empezados después de la mañana del 20/11/2026,
retirar las selecciones archivadas antiguas y volver a construir el Top 3 con
el motor nuevo. Retirar también las apuestas adicionales anteriores; solo
se permitirá rearchivar una nueva adicional si existe una oferta real NUEVA
prepartido que supera las comprobaciones de mercado. **No se reescriben**
partidos comenzados, terminados, liquidados ni los informes retrospectivos.

La solicitud se aplica una sola vez por `data/refresh_top3_request.json`.
El proceso preserva versiones antiguas excluidas del rendimiento en
`data/superseded_top3.json` y `data/superseded_extras.json`.
Los partidos que todavía no tengan datos de ESPN suficientes quedan sin
pronóstico. Los próximos partidos que se incorporen después ya nacen con V3.

## Cambios de cálculo
- Proyección ataque/defensa de puntos y datos verificables de ESPN.
- Pequeño ajuste por descanso hasta el salto inicial, basado **solo** en
  partidos ya finalizados cuando se calcula el pronóstico.
- Dispersión del margen y el total con estimador regularizado de hasta 120
  resultados anteriores; sin introducir resultados futuros.
- Reducción conservadora de certeza aparente: `p = 0.5 + 0.70*(p_raw-0.5)`.
  **Esto NO es una calibración entrenada ni una garantía de acierto.**
- El Top 3 deja de priorizar líneas teóricas extremadamente alejadas del
  valor esperado: cada candidata se limita a +/-1,10 desviaciones típicas
  de la media prevista. Sigue habiendo una familia por selección.
- Las adicionales requieren la línea exacta y el resultado complementario
  cotizados por al menos dos casas independientes. Se elimina el margen
  de cada casa y se calcula la mediana de probabilidades de mercado.
  Diferencias modelo-mercado superiores a 15 puntos porcentuales se
  descartan; en las restantes, se usa un 80% de mercado y un 20% de
  estimación de modelo antes del filtro de valor esperado.
- Si falta una contraparte de precio, hay una sola casa, hay mucha
  discrepancia o no se supera el filtro: **no se publica adicional**.
- No se infieren lesiones, disponibilidad de jugadores ni cuotas que
  nuestras fuentes no entregan.

## Evaluación
Los resultados previos se conservan sin mezclar políticas. La versión
`NBA_CONTEXT_V3` se identifica en el archivo para evaluar sus futuras
predicciones de forma verdaderamente prospectiva. Hasta acumular una muestra
suficiente, el estado es **EXPERIMENTAL_NO_CALIBRADO**. Los resultados
retrospectivos de `research/walkforward_report.json` NO demuestran
rentabilidad.

## Lanzamiento
La actualización diaria se lanza al desplegar el nuevo motor; publica los
nuevos `site/data` y archivos CSV solo si el proveedor y las validaciones
responden correctamente. Si falla, conserva íntegro el estado previo y puede
reintentarse con el flujo programado. No se dispara una llamada extra a The
Odds API fuera de su presupuesto mensual.
