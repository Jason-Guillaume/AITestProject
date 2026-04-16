param(
  [switch]$SkipFrontendBuild,
  [switch]$SkipUi
)

$ErrorActionPreference = "Stop"

Set-Location -Path (Resolve-Path (Join-Path $PSScriptRoot ".."))

$Root = (Get-Location).Path
$FrontendDir = Join-Path $Root "frontend"
$ReportsDir = Join-Path $Root "reports"

function Write-Step([string]$msg) {
  Write-Host "`n== $msg ==" -ForegroundColor Cyan
}

function Must-Env([string]$name) {
  $v = ([Environment]::GetEnvironmentVariable($name) | ForEach-Object { "$_".Trim() })
  if (-not $v) { throw "Missing env $name" }
  return $v
}

function Wait-TcpPort([string]$host, [int]$port, [int]$timeoutSeconds = 60) {
  $deadline = (Get-Date).AddSeconds($timeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $ok = Test-NetConnection -ComputerName $host -Port $port -InformationLevel Quiet
      if ($ok) { return }
    } catch { }
    Start-Sleep -Milliseconds 500
  }
  throw "Timeout waiting for ${host}:$port"
}

function Stop-PortProcess([string]$hostPort, [string]$expectedCmdRegex) {
  try {
    $lines = netstat -ano | Select-String "$hostPort\s+.*LISTENING\s+(\d+)" -AllMatches
  } catch {
    return
  }
  if (-not $lines) { return }
  $pids = @()
  foreach ($m in $lines.Matches) { $pids += [int]$m.Groups[1].Value }
  $pids = $pids | Sort-Object -Unique
  foreach ($pid in $pids) {
    try {
      $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pid"
      $cmd = ($proc.CommandLine -as [string])
      if ($cmd -and $cmd -match $expectedCmdRegex) {
        Stop-Process -Id $pid -Force
      }
    } catch { }
  }
}

function Resolve-PythonExe() {
  $venvPy = Join-Path $Root ".venv\Scripts\python.exe"
  if (Test-Path $venvPy) { return $venvPy }
  return "python"
}

function Resolve-NpmCmd() {
  $npm = "npm"
  if ($env:OS -like "*Windows*") { $npm = "npm.cmd" }
  return $npm
}

$PyExe = Resolve-PythonExe
$NpmCmd = Resolve-NpmCmd

# Ensure required env for API + UI smoke (same credentials).
if (-not $env:TEST_API_BASE_URL) { $env:TEST_API_BASE_URL = "http://127.0.0.1:8000/api" }
Must-Env "TEST_API_USERNAME" | Out-Null
Must-Env "TEST_API_PASSWORD" | Out-Null

New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null

$backendProc = $null
$previewProc = $null

try {
  Write-Step "Pre-clean ports (8000, 4173)"
  Stop-PortProcess "127.0.0.1:8000" ([Regex]::Escape($Root) + ".*manage\.py\s+runserver")
  Stop-PortProcess "127.0.0.1:4173" "vite\s+preview|node\.exe.*vite"

  Write-Step "Start backend (Django runserver)"
  $backendProc = Start-Process -FilePath $PyExe -ArgumentList @("manage.py", "runserver", "127.0.0.1:8000") -WorkingDirectory $Root -PassThru -WindowStyle Hidden
  Wait-TcpPort "127.0.0.1" 8000 90

  Write-Step "Run backend API smoke tests (pytest -m smoke)"
  & $PyExe -m pytest -m smoke tests/api --html="$ReportsDir/api-test-report.html" --self-contained-html

  if (-not $SkipFrontendBuild) {
    Write-Step "Frontend install + build"
    Push-Location $FrontendDir
    try {
      & $NpmCmd ci
      & $NpmCmd run build
    } finally {
      Pop-Location
    }
  }

  Write-Step "Start frontend preview (Vite preview)"
  $env:UI_BASE_URL = "http://127.0.0.1:4173"
  $previewProc = Start-Process -FilePath $NpmCmd -ArgumentList @("run", "preview", "--", "--host", "127.0.0.1", "--port", "4173", "--strictPort") -WorkingDirectory $FrontendDir -PassThru -WindowStyle Hidden
  Wait-TcpPort "127.0.0.1" 4173 60

  if (-not $SkipUi) {
    Write-Step "Run UI smoke tests (Playwright)"
    Push-Location $FrontendDir
    try {
      & $NpmCmd run e2e:install
      & $NpmCmd run e2e:smoke
    } finally {
      Pop-Location
    }
  } else {
    Write-Host "[smoke] UI smoke skipped (-SkipUi)" -ForegroundColor DarkGray
  }

  Write-Step "Smoke finished (PASS)"
  Write-Host "Reports: $ReportsDir" -ForegroundColor Green
} finally {
  Write-Step "Cleanup"
  if ($previewProc -and -not $previewProc.HasExited) {
    try { Stop-Process -Id $previewProc.Id -Force } catch { }
  }
  if ($backendProc -and -not $backendProc.HasExited) {
    try { Stop-Process -Id $backendProc.Id -Force } catch { }
  }
}

