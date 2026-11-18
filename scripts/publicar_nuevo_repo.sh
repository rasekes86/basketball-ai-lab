#!/usr/bin/env bash
# Only for a NEW and EMPTY repo named basketball-ai-lab. No football-ai-lab writes.
set -euo pipefail
url="${1:-}"
if [[ ! "$url" =~ ^https://github\.com/[^/]+/basketball-ai-lab(\.git)?$ ]]; then
  echo "Uso: bash scripts/publicar_nuevo_repo.sh https://github.com/USUARIO/basketball-ai-lab" >&2
  exit 2
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ -f src/basketball_ai_lab/pipeline.py && -f .github/workflows/nba-daily.yml ]] || { echo 'Carpeta incompleta.' >&2; exit 2; }
export PYTHONPATH=src
python -m unittest discover -s tests -q
python -m basketball_ai_lab doctor
if [[ ! -d .git ]]; then git init -b main; fi
if git remote get-url origin >/dev/null 2>&1; then
  existing="$(git remote get-url origin)"
  [[ "${existing%.git}" == "${url%.git}" ]] || { echo 'Origen diferente; se aborta para proteger fútbol.' >&2; exit 2; }
else git remote add origin "$url"; fi
git add -A
if ! git diff --cached --quiet; then git commit -m 'Basketball AI Lab: motor NBA y PWA independientes'; fi
git branch -M main
git push -u origin main
printf '%s\n' 'Proyecto de baloncesto enviado; el de fútbol no ha sido modificado.'
