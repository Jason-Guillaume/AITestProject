param(
  [ValidateSet("smoke", "regression", "full")]
  [string]$Suite = "full",
  [switch]$HtmlReport,
  [switch]$AllureReport
)

$ErrorActionPreference = "Stop"

if (-not $env:TEST_API_USERNAME -or -not $env:TEST_API_PASSWORD) {
  Write-Host "请先设置 TEST_API_USERNAME / TEST_API_PASSWORD" -ForegroundColor Yellow
  exit 1
}

$args = @("tests/api")
switch ($Suite) {
  "smoke" { $args = @("-m", "smoke", "tests/api") }
  "regression" { $args = @("-m", "regression", "tests/api") }
  default { $args = @("tests/api") }
}

if ($HtmlReport) {
  New-Item -ItemType Directory -Force -Path "reports" | Out-Null
  $args += @("--html=reports/api-test-report.html", "--self-contained-html")
}

if ($AllureReport) {
  New-Item -ItemType Directory -Force -Path "reports\allure-results" | Out-Null
  $args += @("--alluredir=reports/allure-results")
}

python -m pytest @args
