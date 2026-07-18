@echo off
setlocal EnableExtensions
REM ============================================================
REM  DAW HORSEMEN - RELEASE PACKAGE
REM  Builds dist\DAW-Horsemen-<VERSION>.zip from git HEAD.
REM  Optional: create/upload GitHub release (needs gh auth).
REM ============================================================
cd /d "%~dp0"
set "PACK=%~dp0"
set "PACK=%PACK:~0,-1%"
set /p VER=<VERSION
set "TAG=v%VER%"
set "ZIP=%PACK%\dist\DAW-Horsemen-%VER%.zip"

echo.
echo  == THE DAW HORSEMEN - RELEASE ==
echo  Version: %VER%
echo  Tag:     %TAG%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%PACK%\scripts\build_release.ps1"
if errorlevel 1 (
  echo  BUILD FAILED
  exit /b 1
)

where gh >nul 2>nul
if errorlevel 1 (
  echo  [!] gh not on PATH - ZIP ready at:
  echo      %ZIP%
  echo  Upload manually or install GitHub CLI.
  exit /b 0
)

echo.
echo  Publishing GitHub release %TAG% ...
gh release view %TAG% -R aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack >nul 2>&1
if not errorlevel 1 (
  echo  Release %TAG% already exists - uploading/replacing asset...
  gh release upload %TAG% "%ZIP%" -R aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack --clobber
) else (
  gh release create %TAG% "%ZIP%" -R aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack --title "DAW Horsemen %VER%" --notes-file CHANGELOG.md --latest
)
if errorlevel 1 (
  echo  RELEASE PUBLISH FAILED
  exit /b 1
)

echo.
echo  DONE. ZIP: %ZIP%
echo  Reinstall on this machine: INSTALL.bat
echo  Fresh machine: unzip + CARE.bat  (or INSTALL.bat)
exit /b 0
