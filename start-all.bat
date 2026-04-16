@echo off
setlocal

cd /d "%~dp0"

echo [All] Launching backend and frontend in new windows...

REM 注意：cmd /k 需要用双层引号包裹整个命令字符串
start "AITestProduct Backend" cmd /k ""%~dp0start-backend.bat""
start "AITestProduct Frontend" cmd /k ""%~dp0start-frontend.bat""

endlocal

