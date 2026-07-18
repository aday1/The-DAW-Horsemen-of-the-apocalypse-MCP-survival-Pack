@echo off
setlocal
REM ============================================================
REM  DAW HORSEMEN - INSTALL (run from inside the cloned repo)
REM  Installs deps, places the Bitwig extension + REAPER bridge,
REM  prints MCP config paths for THIS machine.
REM ============================================================
cd /d "%~dp0"
echo.
echo  == THE DAW HORSEMEN - INSTALL ==
echo  Repo: %~dp0
echo.

where git >nul 2>nul || echo  [!] git not found - installs still work, UPDATE.bat won't.
where py >nul 2>nul && set "PY=py" || set "PY=python"

echo  [1/5] Python deps (REAPER + Bitwig)...
%PY% -m pip install --user -q -r packages\reaper-mcp\requirements.txt
%PY% -m pip install --user -q "mcp[cli]>=1.4.1" python-osc pydantic pydantic-settings uvicorn starlette

echo  [2/5] Node deps (Renoise bridge)...
pushd packages\renoise-mcp-bridge
call npm install --silent
popd

echo  [3/5] Bitwig extension -> Documents\Bitwig Studio\Extensions
set "EXTDIR=%USERPROFILE%\Documents\Bitwig Studio\Extensions"
if not exist "%EXTDIR%" mkdir "%EXTDIR%"
copy /Y drivebymossvaday.bwextension "%EXTDIR%\" >nul && echo        ok

echo  [4/5] REAPER Lua bridge -> %%APPDATA%%\REAPER\Scripts
if exist "%APPDATA%\REAPER" (
  if not exist "%APPDATA%\REAPER\Scripts" mkdir "%APPDATA%\REAPER\Scripts"
  copy /Y packages\reaper-mcp\reaper_mcp_bridge.lua "%APPDATA%\REAPER\Scripts\" >nul && echo        ok
) else (
  echo        REAPER not found - skipped
)

echo  [5/5] Your MCP client config paths (paste into .mcp.json / Cursor):
echo.
echo    reaper : %PY% %~dp0packages\reaper-mcp\reaper_mcp_server.py
echo    renoise: node bridge.js   (cwd = %~dp0packages\renoise-mcp-bridge)
echo    bitwig : http://127.0.0.1:8080/sse   (SSE - start the shared server:)
echo             %~dp0packages\bitwig-mcp-server\run_bitwig_mcp_shared.bat
echo.
echo  In Bitwig: Settings ^> Controllers ^> add DrivenByMoss "Open Sound Control"
echo             Receive 8005 / Send 9001 / host 127.0.0.1
echo.
echo  DONE. Ride.
pause
