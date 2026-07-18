@echo off
setlocal EnableExtensions
REM DAW Horsemen GUI launcher. Old text menu: launch_daw_mcp_cli.bat
cd /d "%~dp0"

if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
  start "" "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" "%~dp0launcher_gui.py" %*
  exit /b 0
)
where pythonw >nul 2>nul && (
  start "" pythonw "%~dp0launcher_gui.py" %*
  exit /b 0
)
where py >nul 2>nul && (
  start "" py -3 "%~dp0launcher_gui.py" %*
  exit /b 0
)
where python >nul 2>nul && (
  start "" python "%~dp0launcher_gui.py" %*
  exit /b 0
)
echo Python not found on PATH. Install Python 3, then re-run.
pause
exit /b 1
