Param(
  [string]$App = "AITestProduct",
  [string]$LogLevel = "info"
)

$ErrorActionPreference = "Stop"

Set-Location -Path (Join-Path $PSScriptRoot "..")

Write-Host "[Celery] working dir: $(Get-Location)"
Write-Host "[Celery] starting worker: celery -A $App worker -l $LogLevel"

python -m celery -A $App worker -l $LogLevel
