@echo off
cd /d "%~dp0"
echo Installing REAPER MCP Python deps (mcp, httpx)... > install_log.txt
(py -m pip install --user mcp httpx 2>&1) >> install_log.txt
if errorlevel 1 (python -m pip install --user mcp httpx 2>&1) >> install_log.txt
echo. >> install_log.txt
echo EXITCODE=%ERRORLEVEL% >> install_log.txt
(py -c "import mcp, httpx; print('IMPORT_OK', mcp.__name__, httpx.__version__)" 2>&1) >> install_log.txt
if errorlevel 1 (python -c "import mcp, httpx; print('IMPORT_OK')" 2>&1) >> install_log.txt
echo FINISHED >> install_log.txt
