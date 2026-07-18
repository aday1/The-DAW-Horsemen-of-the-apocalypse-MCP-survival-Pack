# Start DAW(s) + their MCP side. Used by launch_daw_mcp.bat
param(
  [ValidateSet('bitwig','reaper','renoise','all','health')]
  [string]$Target = 'all',
  [switch]$NoMcpWindows
)

$Pack = Split-Path $PSScriptRoot -Parent
$BitwigExe = 'C:\Program Files\Bitwig Studio\Bitwig Studio.exe'
$ReaperExe = 'C:\Program Files\REAPER (x64)\reaper.exe'
$RenoiseExe = 'C:\Program Files\Renoise 3.5.4\Renoise.exe'
$BitwigDir = Join-Path $Pack 'packages\bitwig-mcp-server'
$ReaperDir = Join-Path $Pack 'packages\reaper-mcp'
$RenoiseDir = Join-Path $Pack 'packages\renoise-mcp-bridge'
$ReaperLua = Join-Path $env:APPDATA 'REAPER\Scripts\reaper_mcp_bridge.lua'
$ReaperLuaPack = Join-Path $ReaperDir 'reaper_mcp_bridge.lua'

function Ensure-File($path, $label) {
  if (-not (Test-Path -LiteralPath $path)) { throw "Missing $label : $path" }
}

function Start-IfNeeded($name, $exe, $argsList = @()) {
  $procName = switch ($name) {
    'Bitwig' { 'Bitwig Studio' }
    'REAPER' { 'reaper' }
    'Renoise' { 'Renoise' }
    default { $name }
  }
  $existing = Get-Process -Name $procName -ErrorAction SilentlyContinue
  if ($existing) {
    Write-Host "  $name already running (PID $($existing.Id -join ','))"
    return $existing
  }
  Ensure-File $exe $name
  Write-Host "  Starting $name ..."
  if ($argsList.Count -gt 0) {
    return Start-Process -FilePath $exe -ArgumentList $argsList -PassThru
  }
  return Start-Process -FilePath $exe -PassThru
}

function Start-BitwigStack {
  Write-Host '[Bitwig]'
  Start-IfNeeded 'Bitwig' $BitwigExe | Out-Null
  # Kill stdio leftovers so shared SSE owns UDP 9001
  & (Join-Path $BitwigDir 'stop_bitwig_servers.bat')
  $sse = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'serve_sse' }
  if ($sse) {
    Write-Host "  Shared SSE already up (PID $($sse.ProcessId -join ','))"
  } else {
    Write-Host '  Starting shared Bitwig MCP SSE :8080 ...'
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "cd /d `"$BitwigDir`" && run_bitwig_mcp_shared.bat"
  }
  Write-Host '  Agents: http://127.0.0.1:8080/sse'
  Write-Host '  In Bitwig: Controllers -> DrivenByMoss OSC -> Receive 8005 / Send 9001 / 127.0.0.1'
  Write-Host '             (toggle OFF/ON once if tools time out)'
}

function Start-ReaperStack {
  Write-Host '[REAPER]'
  # Keep Scripts copy in sync with pack
  if ((Test-Path -LiteralPath $ReaperLuaPack)) {
    $destDir = Split-Path $ReaperLua -Parent
    if (-not (Test-Path -LiteralPath $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
    Copy-Item -LiteralPath $ReaperLuaPack -Destination $ReaperLua -Force
  }
  $running = Get-Process -Name 'reaper' -ErrorAction SilentlyContinue
  if ($running) {
    Write-Host "  REAPER already running - launching bridge script into it ..."
    # REAPER 6.80+: pass script path to control existing/new instance
    Start-Process -FilePath $ReaperExe -ArgumentList "`"$ReaperLua`""
  } else {
    Write-Host '  Starting REAPER + MCP bridge lua ...'
    Start-Process -FilePath $ReaperExe -ArgumentList "`"$ReaperLua`""
  }
  if (-not $NoMcpWindows) {
    Write-Host '  Starting Reaper MCP server window (stdio; Cursor/Claude also auto-spawn) ...'
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "cd /d `"$ReaperDir`" && run_reaper_mcp.bat"
  }
  Write-Host '  If tools fail: Actions -> Show action list -> confirm bridge is running'
}

function Start-RenoiseStack {
  Write-Host '[Renoise]'
  $sdk = Join-Path $RenoiseDir 'node_modules\@modelcontextprotocol\sdk'
  if (-not (Test-Path -LiteralPath $sdk)) {
    Write-Host '  npm install (Renoise bridge deps missing)...'
    Push-Location $RenoiseDir
    try {
      & npm install
      if ($LASTEXITCODE -ne 0) { throw "npm install failed ($LASTEXITCODE)" }
    } finally { Pop-Location }
  }
  Start-IfNeeded 'Renoise' $RenoiseExe | Out-Null
  Write-Host '  Waiting for Renoise UI ...'
  Start-Sleep -Seconds 4
  $ensure = Join-Path $RenoiseDir 'ensure_remcp.ps1'
  if (Test-Path -LiteralPath $ensure) {
    Write-Host '  Waking ReMCP (Tools menu + Play) ...'
    & powershell -NoProfile -ExecutionPolicy Bypass -File $ensure
  } else {
    Write-Host '  Manual: Tools -> Renoise MCP -> START (port 19714) -> Play'
  }
  if (-not $NoMcpWindows) {
    Write-Host '  Starting Renoise MCP bridge window ...'
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "cd /d `"$RenoiseDir`" && run_renoise_mcp.bat"
  }
  Write-Host '  Keep Renoise transport playing when switching to Cursor (ReMCP focus quirk)'
}

switch ($Target) {
  'health' {
    & (Join-Path $PSScriptRoot 'health_check.ps1')
  }
  'bitwig' { Start-BitwigStack }
  'reaper' { Start-ReaperStack }
  'renoise' { Start-RenoiseStack }
  'all' {
    Start-BitwigStack
    Write-Host ''
    Start-ReaperStack
    Write-Host ''
    Start-RenoiseStack
  }
}

Write-Host ''
Write-Host 'Done. Run health (menu H) to verify.'
