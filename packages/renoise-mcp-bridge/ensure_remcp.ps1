# Ensure ReMCP is reachable on port 19714 (default).
# Renoise must be running; ReMCP pauses HTTP when unfocused unless transport is playing.
param(
  [int]$Port = 19714,
  [int]$TimeoutSec = 3
)

$healthUrl = "http://127.0.0.1:$Port/health"

function Test-RemcpHealth {
  try {
    $r = Invoke-WebRequest -Uri $healthUrl -TimeoutSec $TimeoutSec -UseBasicParsing
    return ($r.StatusCode -eq 200)
  } catch {
    return $false
  }
}

if (Test-RemcpHealth) {
  Write-Host "ReMCP OK: $healthUrl"
  exit 0
}

$renoise = Get-Process -Name Renoise -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $renoise) {
  Write-Host "Renoise is not running. Start Renoise first."
  exit 1
}

Write-Host "ReMCP not answering on $Port. Waking Renoise (focus + play)..."
Add-Type -AssemblyName System.Windows.Forms
$ws = New-Object -ComObject WScript.Shell
if (-not $ws.AppActivate($renoise.MainWindowTitle)) {
  $ws.AppActivate('Renoise') | Out-Null
}
Start-Sleep -Milliseconds 400
# Tools -> Renoise MCP (opens panel; auto-starts server on 19714)
[System.Windows.Forms.SendKeys]::SendWait('%{T}')
Start-Sleep -Milliseconds 250
[System.Windows.Forms.SendKeys]::SendWait('R')
Start-Sleep -Milliseconds 800
# Space = transport play (keeps MCP alive when you switch back to Cursor)
[System.Windows.Forms.SendKeys]::SendWait(' ')
Start-Sleep -Milliseconds 500

if (Test-RemcpHealth) {
  Write-Host "ReMCP OK after wake: $healthUrl"
  Write-Host "Switch back to Cursor now; keep transport playing."
  exit 0
}

Write-Host "Still no response. In Renoise: Tools -> Renoise MCP -> port $Port -> Start Server -> Play -> switch away."
exit 2