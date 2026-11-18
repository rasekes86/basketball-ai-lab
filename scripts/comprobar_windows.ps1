$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
$env:PYTHONPATH='src'
Write-Host '== Pruebas Python sin conexión =='
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Las pruebas Python fallaron' }
if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host '== Pruebas de la web =='
    node --test site/tests.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Las pruebas JS fallaron' }
} else {
    Write-Host 'Node no instalado; las pruebas web quedan disponibles en GitHub Actions.'
}
Write-Host 'Pruebas terminadas. No se ha llamado a ESPN ni a la API de cuotas.'
