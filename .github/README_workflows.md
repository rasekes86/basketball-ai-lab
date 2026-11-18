- ci.yml: Python + Node checks on source-code changes.
- nba-daily.yml: one daily scheduled update; optional bookmaker feed disabled unless ENABLE_ODDS and ODDS_API_KEY.
- pages.yml: static GitHub Pages from site/; triggered when site/ files change.
All run independently of football-ai-lab.

- `ci.yml`: prueba Python, JavaScript, sintaxis y `doctor` sin tocar APIs externas.
- `nba-daily.yml`: una ronda NBA diaria, comprobación `doctor --require-live` y commit solo de datos NBA. Detiene consultas en 403/429 o tres errores de red.
- `pages.yml`: publica la web estática sin un servidor ni conexión al motor de fútbol.

Las cuotas (`ENABLE_ODDS`) están apagadas por defecto, sin secretos en la entrega.
