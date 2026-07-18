@echo off
setlocal EnableExtensions
REM ============================================================
REM  DAW HORSEMEN - CARE PACKAGE (one shot: update + heal + agents + SSE)
REM  Out of the box: clone, run me, restart IDEs once, open DAWs.
REM ============================================================
cd /d "%~dp0"
set "PACK=%~dp0"
set "PACK=%PACK:~0,-1%"
where py >nul 2>nul && set "PY=py" || set "PY=python"
set "PS=powershell -NoProfile -ExecutionPolicy Bypass"

echo.
echo  == THE DAW HORSEMEN - CARE (OUT OF THE BOX) ==
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
echo  [2] HEAL bridges, Bitwig OSC, Mackie, Cursor/Claude/Desktop MCP paths...
echo      Close Bitwig if open so prefs patch sticks.
%PY% "%PACK%\scripts\heal_daw_bridges.py"
if errorlevel 1 echo      [!] heal reported errors

echo.
echo  [3] Desktop shortcut...
%PS% -File "%PACK%\scripts\make_desktop_shortcut.ps1" -PackRoot "%PACK%"

echo.
echo  [4] Shared Bitwig SSE ^(required for every agent^)...
%PS% -Command ^
  "$sse = Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { $_.CommandLine -match 'serve_sse' };" ^
  "if ($sse) { Write-Host '      already up PID' ($sse.ProcessId -join ','); exit 0 };" ^
  "Write-Host '      starting run_bitwig_mcp_shared.bat ...';" ^
  "Start-Process cmd.exe -ArgumentList '/k','cd /d \"%PACK%\packages\bitwig-mcp-server\" && run_bitwig_mcp_shared.bat';" ^
  "Start-Sleep -Seconds 2;" ^
  "try { (Invoke-WebRequest http://127.0.0.1:8080/healthz -UseBasicParsing -TimeoutSec 3).Content } catch { Write-Host '      waiting for healthz...' }"

echo.
echo  [5] Health check...
%PS% -File "%PACK%\scripts\health_check.ps1"

echo.
echo  ============================================================
echo   CARE DONE - OUT OF THE BOX
echo  ============================================================
echo   Agents healed: Cursor (.cursor/mcp.json), Claude Code/CLI (.mcp.json),
echo                  Claude Desktop (mcp-remote -^> :8080/sse)
echo   DAWs healed:   Bitwig DawpocalypseMCP + OSC 8005/9001,
echo                  REAPER lua bridge, Renoise ReMCP tip, Mackie template
echo   Shared SSE:    http://127.0.0.1:8080/sse
echo.
echo   YOU STILL DO ONCE:
echo     - Restart Cursor / Claude Desktop / open a fresh Claude CLI session
echo     - Open Bitwig: Controllers -^> DawpocalypseMCP OSC on
echo     - Open REAPER: run reaper_mcp_bridge.lua if not auto-started
echo     - Open Renoise: Tools -^> Renoise MCP -^> Start
echo     - Day-to-day: Desktop "DAW MCP Launchers"
echo.
if /i "%CARE_NOPAUSE%"=="1" exit /b 0
pause
