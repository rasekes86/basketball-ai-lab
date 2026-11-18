# Activar cuotas The Odds API y usar Basketball AI Lab como app (Android)

## Estado del proyecto
- Repositorio: https://github.com/rasekes86/basketball-ai-lab
- App / PWA: https://rasekes86.github.io/basketball-ai-lab/
- El motor ya gestiona **3 selecciones teóricas** por partido y **como máximo 1 adicional** a cuota real mayor de 1,50.
- Las cuotas ofrecidas nunca se sustituyen por cuotas teóricas: si no hay una adicional validada, se indica claramente.
- Los partidos empezados no pueden recibir nuevas selecciones retrospectivas.

## Paso del propietario: obtener clave y guardarla (sin ponerla en el chat ni en ficheros)

1. Regístrate en https://the-odds-api.com/ en la modalidad gratuita que esté disponible y localiza tu API key en la cuenta.
2. En GitHub abre directamente: https://github.com/rasekes86/basketball-ai-lab/settings/secrets/actions
3. **New repository secret** → Nombre `ODDS_API_KEY` → en *Secret* pega la clave → **Add secret**.
4. No necesitas configurar `ENABLE_ODDS` aparte: el workflow detecta el secreto y activa automáticamente la captura. Sin secreto se desactiva y no realiza peticiones.
5. En https://github.com/rasekes86/basketball-ai-lab/actions/workflows/nba-daily.yml selecciona **Run workflow** sobre `main`. Espera a que la ejecución finalice.
6. Revisa `data/status.json` para `odds_status`, `odds_calls_month`, `new_extras`, `extras_archived`. `OK` significa que se capturaron ofertas del proveedor, **no** que exista necesariamente una apuesta adicional válida.
7. Abre la PWA, toca actualizar y comprueba la sección de cada partido. Una adicional registrada mostrará selección, casa y cuota; si no, la ausencia es correcta.

## Consumo y fiabilidad

- Consulta: `/v4/sports/basketball_nba/odds`, región `us`, mercados `h2h`, `spreads`, `totals`.
- Como protección, **máximo una captura al día UTC**, de coste esperado 3 créditos (tres mercados por una región), y tope **interno de 100 créditos/mes**. El límite del plan del proveedor puede cambiar; consulta el panel de su cuenta.
- La captura diaria está programada a las **09:17 UTC**. El propietario puede ejecutar el workflow manualmente; la segunda ejecución el mismo día reutiliza el resultado de estado y no consume otra llamada.
- No se consultan mercados individuales de jugadores (triples de jugadores, asistencias o rebotes personales). Las estadísticas de equipo sí forman parte del Top 3 gracias al histórico ESPN.
- Una selección adicional debe superar 1,50, haberse capturado antes del inicio y pasar el filtro experimental de probabilidad/valor. Ese filtro **no está calibrado para juego con dinero real**.
- La región `us` puede incluir operadores o mercados no disponibles para usuarios en España; se muestran como referencias históricas, no se ofrece acceso a casas de apuestas.
- No se usan ni comparten claves, workflows o balances de Football AI Lab.

## Instalación de la PWA

### Android — Chrome
1. Abre https://rasekes86.github.io/basketball-ai-lab/ en **Chrome**.
2. Toca el botón **Instalar** de la propia web; si Chrome no presenta una ventana de instalación, utiliza **⋮ → Instalar aplicación** o **Añadir a pantalla de inicio**.
3. Acepta la instalación. Encontrarás **Basket AI Lab** con icono propio en el lanzador y se abrirá sin la barra de Chrome.
4. Los recursos de interfaz pueden funcionar sin conexión, pero el calendario, nuevas cuotas y resultados necesitan conexión para actualizarse.

### Escritorio
Abre la web desde Chrome o Edge y utiliza su opción **Instalar aplicación** cuando aparezca. La PWA se ejecuta en su propia ventana.

## Verificación técnica
La web dispone de `manifest.webmanifest`, iconos PNG de 192/512, service worker para el shell, HTTPS por GitHub Pages, botón de instalación y navegación móvil. Las claves API **nunca** se exponen en la PWA: solo existen en el entorno privado de GitHub Actions.
