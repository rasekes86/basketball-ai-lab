$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
$env:PYTHONPATH='src'
$env:ENABLE_ODDS='false'
Write-Host 'Primera lectura NBA sin ninguna clave. Si ESPN bloquea la red, NO se intenta saltar el bloqueo.'
py -m basketball_ai_lab update --output data --site site/data
if ($LASTEXITCODE -ne 0) { throw 'No se pudo contactar con ESPN. No se ha inventado ningún pronóstico.' }
Write-Host 'Abriendo dashboard local en http://localhost:8000'
Start-Process 'http://localhost:8000'
py -m http.server 8000 --directory site
