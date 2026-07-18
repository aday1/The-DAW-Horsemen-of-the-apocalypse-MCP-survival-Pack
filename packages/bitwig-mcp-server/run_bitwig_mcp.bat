@echo off
REM Launches the Bitwig MCP server (stdio). Bitwig must be running with the
REM OSC controller enabled (send 8005 / receive 9001) for tools to work.
cd /d "%~dp0"
set BITWIG_MCP_BITWIG_HOST=127.0.0.1
set BITWIG_MCP_BITWIG_SEND_PORT=8005
set BITWIG_MCP_BITWIG_RECEIVE_PORT=9001
py -m bitwig_mcp_server
if errorlevel 1 python -m bitwig_mcp_server
