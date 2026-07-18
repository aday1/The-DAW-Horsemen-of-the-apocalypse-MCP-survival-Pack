@echo off
REM Launches the Reaper MCP server (stdio). REAPER must be running with
REM reaper_mcp_bridge.lua loaded (Actions -> Load ReaScript) for tools to work.
cd /d "%~dp0"
set "PYTHON=C:\Users\aday\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PYTHON%" (
  "%PYTHON%" reaper_mcp_server.py
) else (
  py reaper_mcp_server.py
  if errorlevel 1 python reaper_mcp_server.py
)
pause