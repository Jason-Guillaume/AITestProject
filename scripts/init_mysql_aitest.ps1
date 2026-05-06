# 创建 .env 中的 aitest 账号并授权 ai_test_product（仅需执行一次）
# 用法（在项目根目录）: .\scripts\init_mysql_aitest.ps1

$ErrorActionPreference = "Stop"
$mysql = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
if (-not (Test-Path $mysql)) {
  Write-Error "未找到 mysql.exe，请修改脚本中的 `$mysql 路径。"
}
$sqlPath = Join-Path $PSScriptRoot "init_mysql_aitest.sql"
if (-not (Test-Path $sqlPath)) {
  Write-Error "未找到 $sqlPath"
}

Write-Host "请输入本机 MySQL root 密码（输入过程不可见）："
$sec = Read-Host -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try {
  $plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
} finally {
  [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
}

$env:MYSQL_PWD = $plain
try {
  Get-Content -LiteralPath $sqlPath -Raw -Encoding UTF8 | & $mysql -u root --default-character-set=utf8mb4
  if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    exit $LASTEXITCODE
  }
  Write-Host "OK: aitest 用户与数据库已就绪。"
} finally {
  Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
}
