@echo off
cd /d "%~dp0"
echo Testing REAPER MCP bridge round-trip... > verify_log.txt
(py test_connection.py 2>&1) >> verify_log.txt
echo EXITCODE=%errorlevel% >> verify_log.txt
echo FINISHED >> verify_log.txt
