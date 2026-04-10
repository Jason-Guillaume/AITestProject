param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$cmdArgs = @("manage.py", "resequence_case_numbers")
if ($DryRun) {
  $cmdArgs += "--dry-run"
}

Write-Host ("执行: python " + ($cmdArgs -join " ")) -ForegroundColor Cyan
python @cmdArgs

if ($LASTEXITCODE -ne 0) {
  Write-Host "编号修复失败" -ForegroundColor Red
  exit $LASTEXITCODE
}

Write-Host "编号修复命令执行完成" -ForegroundColor Green
