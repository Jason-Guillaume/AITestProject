@echo off
setlocal

cd /d "%~dp0frontend"

echo [Frontend] Working dir: %cd%
echo [Frontend] Starting Vite dev server (default http://localhost:5173/)
echo.

if not exist "node_modules" (
  echo [Frontend] node_modules not found, running npm install...
  npm install
)

npm run dev

endlocal

