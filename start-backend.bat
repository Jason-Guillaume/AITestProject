@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo [Backend] Working dir: %cd%

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo [Backend] Using: %PY%
echo [Backend] Starting Django at http://127.0.0.1:8000/
echo.

%PY% manage.py runserver 127.0.0.1:8000

endlocal

