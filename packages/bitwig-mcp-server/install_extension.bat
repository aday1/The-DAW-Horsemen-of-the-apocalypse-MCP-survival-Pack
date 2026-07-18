@echo off
REM Copies the DrivenByMoss (aday build) Bitwig extension into your Bitwig
REM Extensions folder so Bitwig can load it and expose an OSC controller.
cd /d "%~dp0"
set "EXTDIR=%USERPROFILE%\Documents\Bitwig Studio\Extensions"
echo Target: %EXTDIR% > ext_log.txt
if not exist "%EXTDIR%" mkdir "%EXTDIR%"
copy /Y "%~dp0..\..\drivebymossvaday.bwextension" "%EXTDIR%\drivebymossvaday.bwextension" >> ext_log.txt 2>&1
echo EXITCODE=%ERRORLEVEL% >> ext_log.txt
dir "%EXTDIR%\drivebymossvaday.bwextension" >> ext_log.txt 2>&1
echo FINISHED >> ext_log.txt
echo Done. Now restart Bitwig, then Settings ^> Controllers ^> Add DrivenByMoss / Open Sound Control.
