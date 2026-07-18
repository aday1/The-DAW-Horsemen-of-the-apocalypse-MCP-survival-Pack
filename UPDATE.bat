@echo off
setlocal
REM ============================================================
REM  DAW HORSEMEN - UPDATE (checks GitHub, pulls if behind)
REM ============================================================
cd /d "%~dp0"
echo  == THE DAW HORSEMEN - UPDATE CHECK ==
set /p LOCALVER=<VERSION
echo  Local version: %LOCALVER%
git fetch origin main --quiet
for /f %%i in ('git rev-list HEAD..origin/main --count') do set BEHIND=%%i
if "%BEHIND%"=="0" (
  echo  Up to date. Nothing to do.
  pause & exit /b 0
)
echo  %BEHIND% new commit(s) on GitHub - updating...
git pull --ff-only origin main || (echo  [!] pull failed - local edits? Commit or stash first. & pause & exit /b 1)
set /p NEWVER=<VERSION
echo  Now at version: %NEWVER%
echo  Refreshing deps + healing bridges/paths for THIS machine...
where py >nul 2>nul && set "PY=py" || set "PY=python"
%PY% -m pip install --user -q -r packages\reaper-mcp\requirements.txt
%PY% -m pip install --user -q "mcp[cli]>=1.4.1" python-osc pydantic pydantic-settings uvicorn starlette anyio pystray pillow
pushd packages\renoise-mcp-bridge & call npm install --silent & popd
%PY% "%~dp0scripts\heal_daw_bridges.py"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\make_desktop_shortcut.ps1" -PackRoot "%~dp0"
echo  UPDATED %LOCALVER% -> %NEWVER%. Restart Bitwig + MCP clients.
echo  Bitwig controller name: DawpocalypseMCP  (recv 8005 / send 9001)
pause
