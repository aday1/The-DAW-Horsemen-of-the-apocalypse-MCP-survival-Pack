@echo off
REM Launches the Renoise MCP bridge (stdio). Renoise must be running with
REM Tools -> Renoise MCP -> START before the bridge can connect.
cd /d "%~dp0"

if not exist "node_modules\@modelcontextprotocol\sdk" (
  echo [renoise] node_modules missing - running npm install...
  where node >nul 2>nul || (
    echo ERROR: Node.js not on PATH. Install Node LTS, then re-run.
    pause
    exit /b 1
  )
  call npm install
  if errorlevel 1 (
    echo ERROR: npm install failed
    pause
    exit /b 1
  )
)

node bridge.js
pause
