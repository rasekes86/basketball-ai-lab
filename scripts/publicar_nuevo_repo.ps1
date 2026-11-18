# Run AFTER creating a NEW, empty public repository named basketball-ai-lab.
# This script intentionally refuses other repository names (especially football).
param([Parameter(Mandatory=$true)][string]$RepositoryUrl)
$ErrorActionPreference='Stop'
if ($RepositoryUrl -notmatch '^https://github\.com/[^/]+/basketball-ai-lab(?:\.git)?$') {
  throw 'La URL debe ser https://github.com/USUARIO/basketball-ai-lab (REPO NUEVO).'
}
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
if (-not (Test-Path 'src/basketball_ai_lab/pipeline.py') -or -not (Test-Path '.github/workflows/nba-daily.yml')) {
  throw 'No estás dentro de la carpeta Basketball AI Lab completa. No se ha enviado nada.'
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git no está disponible. Usa GitHub Desktop o Codex.' }
if (-not (Test-Path .git)) {
  git init -b main
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo inicializar Git.' }
}
$remotes=@(git remote)
if ($remotes -contains 'origin') {
  $existing=(git remote get-url origin)
  if ($existing -ne $RepositoryUrl -and $existing -ne ($RepositoryUrl + '.git') -and ($existing + '.git') -ne $RepositoryUrl) {
    throw "Ya existe origin apuntando a otro proyecto ($existing). No se tocará."
  }
} else {
  git remote add origin $RepositoryUrl
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo añadir el repositorio remoto.' }
}
$env:PYTHONPATH='src'
py -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw 'Pruebas fallidas; abortando la publicación.' }
py -m basketball_ai_lab doctor
if ($LASTEXITCODE -ne 0) { throw 'Auditoría fallida; abortando la publicación.' }
git add -A
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar los archivos.' }
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  git commit -m 'Basketball AI Lab: NBA independiente, motor, 30 equipos y web'
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo confirmar el commit; revisa identidad de Git.' }
}
git branch -M main
if ($LASTEXITCODE -ne 0) { throw 'No se pudo seleccionar main.' }
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'GitHub rechazó la subida: revisa acceso al NUEVO repositorio.' }
Write-Host 'Basketball AI Lab publicado en el repositorio nuevo. Football AI Lab no ha sido modificado.'
