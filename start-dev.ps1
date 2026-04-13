$ErrorActionPreference = "Stop"

Write-Host "== AITesta 本地开发一键启动 ==" -ForegroundColor Cyan

# 统一到脚本所在目录，避免从其他路径运行时找不到 manage.py
Set-Location -Path $PSScriptRoot

# 固定使用项目虚拟环境解释器，避免系统 Python 与 .venv 混用导致依赖缺失。
$PyExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (!(Test-Path $PyExe)) {
    Write-Host "未找到虚拟环境解释器：$PyExe" -ForegroundColor Red
    Write-Host "请先创建并安装依赖：python -m venv .venv && .\\.venv\\Scripts\\python -m pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

function Run-Step($name, $cmd) {
    Write-Host "`n[步骤] $name" -ForegroundColor Yellow
    Write-Host "命令: $cmd" -ForegroundColor DarkGray
    Invoke-Expression $cmd
}

function Stop-StaleRunserverProcesses {
    Write-Host "`n[预处理] 清理残留 Django runserver 进程..." -ForegroundColor Yellow
    $escapedRoot = [Regex]::Escape($PSScriptRoot)
    $targets = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "python.exe" -and
        $_.CommandLine -and
        $_.CommandLine -match "manage\.py\s+runserver" -and
        $_.CommandLine -match $escapedRoot
    }

    if (-not $targets) {
        Write-Host "未发现需要清理的 runserver 残留进程。" -ForegroundColor DarkGray
        return
    }

    foreach ($p in $targets) {
        try {
            Stop-Process -Id $p.ProcessId -Force
            Write-Host ("已结束 runserver 进程 PID={0}" -f $p.ProcessId) -ForegroundColor DarkGray
        } catch {
            Write-Host ("结束进程失败 PID={0}: {1}" -f $p.ProcessId, $_.Exception.Message) -ForegroundColor Red
        }
    }
}

# 1) 基础依赖（可重复执行，已安装会自动跳过）
Run-Step "安装 Celery-MySQL 关键依赖" "& '$PyExe' -m pip install sqlalchemy pymysql django-celery-results"

# 2) 数据库迁移
Run-Step "执行数据库迁移" "& '$PyExe' manage.py migrate"

# 3) Django 配置检查
Run-Step "执行 Django 自检" "& '$PyExe' manage.py check"

# 4) 清理残留 runserver 进程，避免端口占用
Stop-StaleRunserverProcesses

# 5) 启动服务（新开两个窗口，分别跑 Django 与 Celery Worker）
Write-Host "`n[启动] 拉起 Django 与 Celery Worker..." -ForegroundColor Green

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$PSScriptRoot'; & '$PyExe' manage.py runserver 0.0.0.0:8000"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$PSScriptRoot'; & '$PyExe' -m celery -A AITestProduct worker -l info -P solo"
)

Write-Host "`n启动完成：" -ForegroundColor Cyan
Write-Host "1) Django: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "2) Celery Worker: 新开的 PowerShell 窗口" -ForegroundColor White
Write-Host "`n如需停止，请分别关闭两个窗口或在窗口内按 Ctrl+C。" -ForegroundColor DarkYellow
