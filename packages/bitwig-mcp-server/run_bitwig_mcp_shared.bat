@echo off
REM ============================================================================
REM  ONE shared Bitwig MCP server for ALL clients (Claude CLI/Code, Cursor,
REM  Cowork, Claude Desktop). Owns the SINGLE OSC link to Bitwig (send 8005 /
REM  recv 9001) and serves MCP over HTTP-SSE at http://127.0.0.1:8080/sse.
REM
REM  Run EXACTLY ONE of these. Kill leftover stdio servers first:
REM     stop_bitwig_servers.bat
REM  Bitwig must be running with the DrivenByMoss "Open Sound Control"
REM  controller enabled (Receive 8005 / Send 9001 / host 127.0.0.1).
REM ============================================================================
cd /d "%~dp0"
set BITWIG_MCP_BITWIG_HOST=127.0.0.1
set BITWIG_MCP_BITWIG_SEND_PORT=8005
set BITWIG_MCP_BITWIG_RECEIVE_PORT=9001
set BITWIG_MCP_MCP_PORT=8080
title Bitwig MCP SHARED server (SSE :8080)
py serve_sse.py
if errorlevel 1 python serve_sse.py
