# Ensure shared Bitwig MCP SSE is running (CARE / OOTB).
$ErrorActionPreference = 'Continue'
$Pack = if ($args[0]) { $args[0] } else { Split-Path $PSScriptRoot -Parent }
$BitwigDir = Join-Path $Pack 'packages\bitwig-mcp-server'

$sse = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'serve_sse' }
if ($sse) {
  Write-Host "      already up PID $($sse.ProcessId -join ',')"
} else {
  Write-Host '      starting run_bitwig_mcp_shared.bat ...'
  Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "cd /d `"$BitwigDir`" && run_bitwig_mcp_shared.bat"
  Start-Sleep -Seconds 2
}

try {
  $r = Invoke-WebRequest 'http://127.0.0.1:8080/healthz' -UseBasicParsing -TimeoutSec 4
  Write-Host "      healthz: $($r.Content)"
} catch {
  Write-Host '      healthz not ready yet (SSE window may still be starting)'
}
