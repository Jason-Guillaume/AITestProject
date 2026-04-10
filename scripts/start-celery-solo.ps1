Param(
  [string]$App = "AITestProduct",
  [string]$LogLevel = "info"
)

$ErrorActionPreference = "Stop"

Set-Location -Path (Join-Path $PSScriptRoot "..")

Write-Host "[Celery] working dir: $(Get-Location)"
Write-Host "[Celery] starting worker (solo): celery -A $App worker -l $LogLevel -P solo"

python -m celery -A $App worker -l $LogLevel -P solo
