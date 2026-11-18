# Guía definitiva · Subir Basketball AI Lab a GitHub

## Antes de subir (sin pagar ni contratar nada)

El paquete **Basketball_AI_Lab_NBA_LISTO_PARA_GITHUB.zip** incluye archivos sueltos en la raíz del ZIP: `.github/`, `src/`, `site/`, `tests/`, `data/`, `docs/`, `scripts/` y `README.md`.

**No subas el ZIP como un único archivo al repositorio**: GitHub no lo descomprime. Extrae el ZIP primero y publica el contenido de la carpeta, con `.github` incluida.

### Vía A: GitHub web + Codex/GitHub Desktop

1. En GitHub, pulsa `+` → **New repository**. Nombre **basketball-ai-lab**; **Public**; sin README ni .gitignore automáticos.
2. En tu equipo, descomprime el ZIP en una carpeta `basketball-ai-lab`.
3. Sube los archivos de esa carpeta por GitHub Desktop o utilizando uno de los scripts siguientes. Ten en cuenta que `.github` es una carpeta que empieza por punto: no debes omitirla.
4. Tras la subida, revisa **Actions**. El flujo `Basketball AI Lab · actualización NBA` arranca con el primer push; descarga datos reales de ESPN y crea los informes. Si está deshabilitado, habilita Actions y ejecútalo manualmente con **Run workflow**.
5. En el nuevo repositorio: **Settings → Pages → Build and deployment → Source → GitHub Actions**. Abre Actions → `Basketball AI Lab · publicar web` → **Run workflow** si la publicación inicial se produjo antes de habilitar Pages.
6. Visita `https://rasekes86.github.io/basketball-ai-lab/` (si el repositorio se crea en la cuenta `rasekes86`). Prueba los dos temas y la vista de **30 equipos**.
7. Revisa `data/status.json`: `source_successful_days > 0`, `games > 0`, `logo_coverage`, `top3_archived`, `review_required_count`.

### Vía B: PowerShell (Windows, sin instalar Python ni Node si ya están disponibles)

En la carpeta descomprimida, con Git y Python disponibles:

```powershell
.\scripts\comprobar_windows.ps1
.\scripts\publicar_nuevo_repo.ps1 -RepositoryUrl 'https://github.com/rasekes86/basketball-ai-lab'
```

El script verifica el nombre del repositorio, las pruebas, el auditor y **se niega a publicar en Football AI Lab**.

### Vía C: terminal Linux/macOS / Codex

```bash
cd basketball-ai-lab
bash scripts/publicar_nuevo_repo.sh https://github.com/rasekes86/basketball-ai-lab
```

**Instrucción lista para pegar en Codex cuando el repositorio nuevo exista:**

> Abre la carpeta Basketball AI Lab que he descomprimido. Comprueba `python -m unittest discover -s tests -q`, `python -m basketball_ai_lab doctor` con `PYTHONPATH=src` y `node --test site/tests.mjs` si Node está disponible. Publica **exclusivamente** el contenido de esta carpeta en el repositorio NUEVO público `rasekes86/basketball-ai-lab` en la rama `main`. No abras, leas ni modifiques `rasekes86/football-ai-lab`. Confirma que `.github/workflows` y `site/reports` se han incluido. Verifica Actions y Pages; no configures ninguna clave de cuotas ni habilites `ENABLE_ODDS`.

## ¿Qué necesita tu intervención después?

- Solo **crear el repositorio nuevo y habilitar Pages** (GitHub no permite crear ese repositorio desde la conexión disponible en el chat).
- **No se necesita** tarjeta, suscripción, API key, Google Sheets, Telegram ni Cloudflare para arrancar el motor sin cuotas.
- Las cuotas reales son **opcionales** y permanecerán desactivadas; solo se activarían con una cuenta gratuita tuya, tras revisar términos y límites.

## Comprobación posterior (sin red adicional)

En GitHub Actions, cada actualización ejecuta automáticamente:

```bash
PYTHONPATH=src python -m basketball_ai_lab doctor --require-live
```

La auditoría señala escudos ausentes, fuentes desconectadas, pronósticos hechos tarde, posibles errores de liquidación y encuentros reprogramados. Es conservadora y **nunca modifica pronósticos**.

**Limitación:** ESPN es un endpoint público no oficial para terceros. No se ha podido validar desde el entorno de esta entrega porque no hay acceso DNS a ESPN. El primer runner en GitHub será la prueba real; si ESPN lo bloquea, el workflow fallará de forma segura y mantendrá los informes previos sin inventar datos.
