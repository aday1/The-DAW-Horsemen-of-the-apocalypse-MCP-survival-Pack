@echo off
setlocal EnableExtensions
REM ============================================================
REM  DAW HORSEMEN - INSTALL (run from inside the cloned repo)
REM  Deps, Bitwig extension, REAPER bridge, desktop shortcut,
REM  machine-local mcp.generated.json for IDE paste.
REM ============================================================
cd /d "%~dp0"
set "PACK=%~dp0"
set "PACK=%PACK:~0,-1%"
set "PS=powershell -NoProfile -ExecutionPolicy Bypass"

echo.
echo  == THE DAW HORSEMEN - INSTALL ==
echo  Repo: %PACK%
echo.

where git >nul 2>nul || echo  [!] git not found - installs still work, UPDATE.bat won't.
where py >nul 2>nul && set "PY=py" || set "PY=python"
where node >nul 2>nul || echo  [!] node not found - Renoise bridge install will fail until Node is on PATH.

echo  [1/7] Python deps (REAPER + Bitwig)...
%PY% -m pip install --user -q -r packages\reaper-mcp\requirements.txt
%PY% -m pip install --user -q "mcp[cli]>=1.4.1" python-osc pydantic pydantic-settings uvicorn starlette anyio

echo  [2/7] Node deps (Renoise bridge)...
pushd packages\renoise-mcp-bridge
call npm install --silent
popd

echo  [3/7] Heal bridges + Bitwig OSC prefs ^(DawpocalypseMCP, ports 8005/9001^)
echo        Close Bitwig first if it is open - prefs patch sticks better.
%PY% "%PACK%\scripts\heal_daw_bridges.py"
if errorlevel 1 echo        [!] heal failed - see messages above

echo  [4/7] ^(heal already synced REAPER lua^)

echo  [5/7] Renoise ReMCP tool ^(open xrnx if not already installed^)
set "REMCP=%APPDATA%\Renoise\V3.5.4\Scripts\Tools\com.renoise.ReMCP.xrnx"
if exist "%REMCP%" (
  echo        already present
) else (
  echo        Opening pack xrnx - Renoise will prompt to install the tool...
  start "" "%PACK%\packages\renoise-mcp-bridge\com.renoise.ReMCP_v0.1_api6.xrnx"
)

echo  [6/7] Desktop shortcut "DAW MCP Launchers"
%PS% -File "%PACK%\scripts\make_desktop_shortcut.ps1" -PackRoot "%PACK%"
if errorlevel 1 echo        [!] shortcut failed - run scripts\make_desktop_shortcut.ps1 manually

echo  [7/7] mcp.generated.json already written by heal

echo.
echo  ============================================================
echo   NEXT
echo  ============================================================
echo.
echo   1. Desktop -^> "DAW MCP Launchers"  ^(or launch_daw_mcp.bat^)
echo   2. Read IDE_SETUP.txt  - Cursor / Claude / Claude CLI / VS Code / Desktop
echo   3. Paste mcp.generated.json into your IDE MCP config
echo      Bitwig MUST stay:  http://127.0.0.1:8080/sse
echo   4. Menu H = health check
echo.
echo   Bitwig OSC: Controllers -^> DrivenByMoss Open Sound Control
echo               Receive 8005 / Send 9001 / host 127.0.0.1
echo.
echo  DONE. Ride.
pause
