@echo off
setlocal EnableExtensions
REM ============================================================
REM  DAW HORSEMEN - RELEASE PACKAGE
REM  Builds dist\DAW-Horsemen-<VERSION>.msi from git HEAD (WiX).
REM  Optional: create/upload GitHub release (needs gh auth).
REM ============================================================
cd /d "%~dp0"
set "PACK=%~dp0"
set "PACK=%PACK:~0,-1%"
set /p VER=<VERSION
set "TAG=v%VER%"
set "MSI=%PACK%\dist\DAW-Horsemen-%VER%.msi"

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

if not exist "%MSI%" (
  echo  MSI missing: %MSI%
  exit /b 1
)

where gh >nul 2>nul
if errorlevel 1 (
  echo  [!] gh not on PATH - MSI ready at:
  echo      %MSI%
  echo  Upload manually or install GitHub CLI.
  exit /b 0
)

echo.
echo  Publishing GitHub release %TAG% ...
gh release view %TAG% -R aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack >nul 2>&1
if not errorlevel 1 (
  echo  Release %TAG% already exists - uploading/replacing MSI...
  gh release upload %TAG% "%MSI%" -R aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack --clobber
) else (
  gh release create %TAG% "%MSI%" -R aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack --title "DAW Horsemen %VER%" --notes-file CHANGELOG.md --latest
)
if errorlevel 1 (
  echo  RELEASE PUBLISH FAILED
  exit /b 1
)

echo.
echo  DONE. MSI: %MSI%
echo  Install: double-click MSI  or  msiexec /i "%MSI%"
echo  Then: Start Menu - DAW Horsemen  or  CARE.bat from install folder
exit /b 0
