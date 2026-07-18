@echo off
REM Kill every stdio/SSE bitwig_mcp_server python process so the shared server
REM can own the OSC (9001) + monitor (8765) ports cleanly. Safe to run anytime.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'bitwig_mcp_server|serve_sse' } | ForEach-Object { Write-Host ('Killing PID ' + $_.ProcessId + ': ' + $_.CommandLine); Stop-Process -Id $_.ProcessId -Force }"
echo.
echo Done. Now start exactly one: run_bitwig_mcp_shared.bat
