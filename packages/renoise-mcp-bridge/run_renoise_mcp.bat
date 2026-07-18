@echo off
REM Launches the Renoise MCP bridge (stdio). Renoise must be running with
REM Tools -> Renoise MCP -> START before the bridge can connect.
cd /d "%~dp0"
node bridge.js
pause