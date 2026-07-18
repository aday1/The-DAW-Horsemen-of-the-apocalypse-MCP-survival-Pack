@echo off
setlocal EnableExtensions
REM ============================================================
REM  DAW HORSEMEN - CARE PACKAGE (GitHub clones: one shot)
REM  Always: heal bridges/paths/OSC/Mackie + desktop shortcut + health
REM  If git behind origin: pull first (UPDATE deps), then heal
REM ============================================================
cd /d "%~dp0"
set "PACK=%~dp0"
set "PACK=%PACK:~0,-1%"
where py >nul 2>nul && set "PY=py" || set "PY=python"

echo.
echo  == THE DAW HORSEMEN - CARE ==
echo  Pack: %PACK%
echo.

REM --- optional git update ---
where git >nul 2>nul
if not errorlevel 1 (
  if exist "%PACK%\.git" (
    echo  [1] Checking GitHub for updates...
    git fetch origin main --quiet 2>nul
    for /f %%i in ('git rev-list HEAD..origin/main --count 2^>nul') do set BEHIND=%%i
    if "%BEHIND%"=="" set BEHIND=0
    if not "%BEHIND%"=="0" (
      echo       %BEHIND% new commit(s) - pulling...
      git pull --ff-only origin main
      if errorlevel 1 (
        echo       [!] pull failed - local edits? Heal will still run.
      ) else (
        echo       Refreshing pip/npm deps...
        %PY% -m pip install --user -q -r packages\reaper-mcp\requirements.txt
        %PY% -m pip install --user -q "mcp[cli]>=1.4.1" python-osc pydantic pydantic-settings uvicorn starlette anyio
        pushd packages\renoise-mcp-bridge & call npm install --silent & popd
      )
    ) else (
      echo       Already up to date with origin/main
    )
  ) else (
    echo  [1] No .git - skip pull ^(zip download OK^)
  )
) else (
  echo  [1] git not on PATH - skip pull
)

echo.
echo  [2] HEAL bridges, Bitwig OSC ports, Mackie template, MCP paths...
echo      Close Bitwig if open so prefs patch sticks.
%PY% "%PACK%\scripts\heal_daw_bridges.py"
if errorlevel 1 echo      [!] heal reported errors

echo.
echo  [3] Desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PACK%\scripts\make_desktop_shortcut.ps1" -PackRoot "%PACK%"

echo.
echo  [4] Health check...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PACK%\scripts\health_check.ps1"

echo.
echo  ============================================================
echo   CARE DONE
echo  ============================================================
echo   - Bitwig OSC: DawpocalypseMCP  recv 8005 / send 9001
echo   - X-Touch: Controllers -^> MCU - Control Universal ^(MIDI^)
echo   - Agents: mcp.generated.json + shared SSE http://127.0.0.1:8080/sse
echo   - Read: IDE_SETUP.txt  and  packages\mackie-xtouch\SETUP_MACKIE.txt
echo   - Day-to-day: Desktop "DAW MCP Launchers"
echo.
pause
