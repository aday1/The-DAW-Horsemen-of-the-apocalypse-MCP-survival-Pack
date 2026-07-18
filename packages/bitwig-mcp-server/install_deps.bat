@echo off
REM Installs the core Python deps for the Bitwig MCP server (lightweight set).
REM The heavy optional deps (chromadb, sentence-transformers) are only needed
REM for the browser-index / device-recommend extras and are NOT installed here.
cd /d "%~dp0"
echo Installing Bitwig MCP core deps... > install_log.txt
(py -m pip install --user "mcp[cli]>=1.4.1" python-osc pydantic pydantic-settings 2>&1) >> install_log.txt
if errorlevel 1 (python -m pip install --user "mcp[cli]>=1.4.1" python-osc pydantic pydantic-settings 2>&1) >> install_log.txt
echo. >> install_log.txt
echo EXITCODE=%ERRORLEVEL% >> install_log.txt
(py -c "import mcp, pythonosc, pydantic, pydantic_settings; print('IMPORT_OK')" 2>&1) >> install_log.txt
if errorlevel 1 (python -c "import mcp, pythonosc, pydantic, pydantic_settings; print('IMPORT_OK')" 2>&1) >> install_log.txt
echo FINISHED >> install_log.txt
