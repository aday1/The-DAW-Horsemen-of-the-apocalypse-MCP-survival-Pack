@echo off
setlocal EnableExtensions
title DAW MCP Launchers

REM Source of truth: this repo (aday1/The-DAW-Horsemen-...).
REM Bitwig = ONE shared SSE server so Cursor + Claude + Claude CLI all share OSC.
REM REAPER / Renoise = start the DAW + bridge; agents also stdio-spawn MCP as needed.

set "PACK=%~dp0"
set "SCRIPTS=%PACK%scripts"
set "PS=powershell -NoProfile -ExecutionPolicy Bypass"

:menu
cls
echo.
echo  ========================================
echo   DAW MCP Launchers
echo  ========================================
echo.
echo  Pack: %PACK%
echo  Bitwig agents: http://127.0.0.1:8080/sse
echo  (repo .mcp.json + .cursor\mcp.json)
echo.
echo   --- Health ---
echo   H. Health check (DAWs + agents + git pack)
echo.
echo   --- Start DAW + MCP ---
echo   1. Bitwig Studio + SHARED MCP (SSE :8080)
echo   2. REAPER + bridge lua + MCP
echo   3. Renoise + ReMCP wake + bridge
echo   4. ALL three DAWs + MCPs
echo.
echo   --- MCP only (DAW already open) ---
echo   5. Bitwig SHARED MCP only
echo   6. Stop all Bitwig MCP processes
echo   7. Reaper MCP server window
echo   8. Renoise MCP bridge window
echo.
echo   --- Notes / install ---
echo   9. Open Bitwig shared-server notes
echo   D. Recreate Desktop shortcut
echo   E. Open IDE_SETUP.txt  (Cursor / Claude / CLI / VS Code)
echo   I. Run INSTALL.bat (sync bridges into DAWs)
echo   U. Run UPDATE.bat (git pull from GitHub)
echo.
echo   Q. Quit
echo.
set /p CHOICE=Choose: 

if /i "%CHOICE%"=="H" goto health
if /i "%CHOICE%"=="1" goto bitwig_full
if /i "%CHOICE%"=="2" goto reaper_full
if /i "%CHOICE%"=="3" goto renoise_full
if /i "%CHOICE%"=="4" goto all_full
if /i "%CHOICE%"=="5" goto bitwig_mcp
if /i "%CHOICE%"=="6" goto bitwig_stop
if /i "%CHOICE%"=="7" goto reaper_mcp
if /i "%CHOICE%"=="8" goto renoise_mcp
if /i "%CHOICE%"=="9" goto bitwig_notes
if /i "%CHOICE%"=="D" goto desktop
if /i "%CHOICE%"=="E" goto ide_setup
if /i "%CHOICE%"=="I" goto install
if /i "%CHOICE%"=="U" goto update
if /i "%CHOICE%"=="Q" exit /b 0
goto menu

:health
%PS% -File "%SCRIPTS%\health_check.ps1"
echo.
pause
goto menu

:bitwig_full
%PS% -File "%SCRIPTS%\start_stack.ps1" -Target bitwig
echo.
pause
goto menu

:reaper_full
%PS% -File "%SCRIPTS%\start_stack.ps1" -Target reaper
echo.
pause
goto menu

:renoise_full
%PS% -File "%SCRIPTS%\start_stack.ps1" -Target renoise
echo.
pause
goto menu

:all_full
%PS% -File "%SCRIPTS%\start_stack.ps1" -Target all
echo.
pause
goto menu

:bitwig_mcp
call "%PACK%packages\bitwig-mcp-server\stop_bitwig_servers.bat"
start "Bitwig MCP SHARED (SSE :8080)" cmd /k "cd /d "%PACK%packages\bitwig-mcp-server" && run_bitwig_mcp_shared.bat"
echo Started. Health: http://127.0.0.1:8080/healthz
pause
goto menu

:bitwig_stop
call "%PACK%packages\bitwig-mcp-server\stop_bitwig_servers.bat"
pause
goto menu

:reaper_mcp
start "Reaper MCP Server" cmd /k "cd /d "%PACK%packages\reaper-mcp" && run_reaper_mcp.bat"
goto menu

:renoise_mcp
start "Renoise MCP Bridge" cmd /k "cd /d "%PACK%packages\renoise-mcp-bridge" && run_renoise_mcp.bat"
goto menu

:bitwig_notes
if exist "%PACK%packages\bitwig-mcp-server\SHARED_SERVER.md" (
  start "" notepad "%PACK%packages\bitwig-mcp-server\SHARED_SERVER.md"
) else (
  echo Missing SHARED_SERVER.md
  pause
)
goto menu

:desktop
%PS% -File "%SCRIPTS%\make_desktop_shortcut.ps1" -PackRoot "%PACK%"
pause
goto menu

:ide_setup
if exist "%PACK%IDE_SETUP.txt" (
  start "" notepad "%PACK%IDE_SETUP.txt"
) else (
  echo Missing IDE_SETUP.txt
  pause
)
goto menu

:install
call "%PACK%INSTALL.bat"
goto menu

:update
call "%PACK%UPDATE.bat"
goto menu
