# DAW Horsemen - health check (agents + DAWs + GitHub pack)
# Exit 0 = all critical OK; 1 = something needs attention.
$ErrorActionPreference = 'Continue'
# scripts\ -> DAW-Horsemen\
$Pack = Split-Path $PSScriptRoot -Parent
$fail = 0

function Ok($msg) { Write-Host "  OK  $msg" -ForegroundColor Green }
function Bad($msg) { Write-Host "  BAD $msg" -ForegroundColor Red; $script:fail++ }
function Info($msg) { Write-Host "  ..  $msg" -ForegroundColor DarkGray }

Write-Host ''
Write-Host '== DAW HORSEMEN HEALTH =='
Write-Host "Pack: $Pack"

# --- git source of truth (clone) / skip for MSI-ZIP installs ---
Write-Host ''
Write-Host '[git]'
Push-Location $Pack
try {
  if (-not (Test-Path -LiteralPath (Join-Path $Pack '.git'))) {
    Info 'MSI/ZIP install (no .git) - reinstall from GitHub Releases to update'
  } else {
    $remote = (git remote get-url origin 2>$null)
    if ($remote -match 'The-DAW-Horsemen') { Ok "origin $remote" } else { Bad "unexpected origin: $remote" }
    git fetch origin --quiet 2>$null
    $counts = (git rev-list --left-right --count origin/main...HEAD 2>$null)
    if ($counts -eq '0	0' -or $counts -eq '0 0') { Ok 'in sync with origin/main' }
    else { Bad "ahead/behind origin/main: $counts (run UPDATE.bat or commit/push)" }
    $head = (git rev-parse --short HEAD)
    Info "HEAD $head"
  }
} finally { Pop-Location }

# --- packages present ---
Write-Host ''
Write-Host '[packages]'
@(
  'packages\bitwig-mcp-server\serve_sse.py',
  'packages\bitwig-mcp-server\run_bitwig_mcp_shared.bat',
  'packages\reaper-mcp\reaper_mcp_server.py',
  'packages\reaper-mcp\reaper_mcp_bridge.lua',
  'packages\renoise-mcp-bridge\bridge.js',
  'packages\renoise-mcp-bridge\com.renoise.ReMCP_v0.1_api6.xrnx',
  'packages\renoise-mcp-bridge\node_modules\@modelcontextprotocol\sdk\package.json',
  'drivebymossvaday.bwextension'
) | ForEach-Object {
  $p = Join-Path $Pack $_
  if (Test-Path -LiteralPath $p) { Ok $_ } else { Bad "missing $_" }
}

# --- installed bridges match pack ---
Write-Host ''
Write-Host '[installed bridges vs pack]'
function HashMatch($packPath, $instPath, $label) {
  if (-not (Test-Path -LiteralPath $packPath)) { Bad "$label pack missing"; return }
  if (-not (Test-Path -LiteralPath $instPath)) { Bad "$label NOT installed at $instPath (run INSTALL.bat)"; return }
  # .NET hash — works when Get-FileHash is blocked (constrained language)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $ba = [IO.File]::ReadAllBytes($packPath)
    $bb = [IO.File]::ReadAllBytes($instPath)
    $ha = [BitConverter]::ToString($sha.ComputeHash($ba)).Replace('-', '')
    $hb = [BitConverter]::ToString($sha.ComputeHash($bb)).Replace('-', '')
  } finally { $sha.Dispose() }
  if ($ha -eq $hb) { Ok "$label matches pack" } else { Bad "$label DRIFT vs pack - re-run INSTALL.bat / CARE.bat" }
}
HashMatch (Join-Path $Pack 'packages\reaper-mcp\reaper_mcp_bridge.lua') `
  (Join-Path $env:APPDATA 'REAPER\Scripts\reaper_mcp_bridge.lua') 'REAPER lua'
$extPack = Join-Path $Pack 'DawpocalypseMCP.bwextension'
if (-not (Test-Path -LiteralPath $extPack)) { $extPack = Join-Path $Pack 'drivebymossvaday.bwextension' }
$extInst = Join-Path $env:USERPROFILE 'Documents\Bitwig Studio\Extensions\DawpocalypseMCP.bwextension'
if (-not (Test-Path -LiteralPath $extInst)) {
  $extInst = Join-Path $env:USERPROFILE 'Documents\Bitwig Studio\Extensions\drivebymossvaday.bwextension'
}
HashMatch $extPack $extInst 'Bitwig extension'
$remcp = Join-Path $env:APPDATA 'Renoise\V3.5.4\Scripts\Tools\com.renoise.ReMCP.xrnx'
if (Test-Path -LiteralPath $remcp) { Ok "Renoise ReMCP present ($remcp)" } else { Bad "Renoise ReMCP missing - install pack xrnx" }

# --- agent configs ---
Write-Host ''
Write-Host '[agent MCP configs]'
$cfgRoots = @()
$parent = Split-Path $Pack -Parent
if ((Split-Path $parent -Leaf) -ne 'Programs') { $cfgRoots += $parent }
foreach ($cand in @('E:\ChiptuneClaude', (Join-Path $env:USERPROFILE 'ChiptuneClaude'))) {
  if ((Test-Path -LiteralPath $cand) -and ($cfgRoots -notcontains $cand)) { $cfgRoots += $cand }
}
$cfgRoots += $Pack
$seen = @{}
foreach ($root in $cfgRoots) {
  foreach ($rel in @('.mcp.json', '.cursor\mcp.json')) {
    $cfg = Join-Path $root $rel
    if ($seen.ContainsKey($cfg)) { continue }
    $seen[$cfg] = $true
    if (-not (Test-Path -LiteralPath $cfg)) {
      if ($root -eq $Pack) { Bad "missing $cfg (run CARE.bat)" }
      else { Info "skip missing $cfg" }
      continue
    }
    $raw = Get-Content -LiteralPath $cfg -Raw
    $name = "$($root | Split-Path -Leaf)/$(Split-Path $cfg -Leaf)"
    if ($raw -match '127\.0\.0\.1:8080/sse') { Ok "$name bitwig -> shared SSE :8080" }
    else { Bad "$name bitwig NOT pointing at http://127.0.0.1:8080/sse" }
    if ($raw -match 'DAW-Horsemen.+reaper-mcp') { Ok "$name reaper -> Horsemen pack" }
    elseif ($raw -match 'reaper.mcp|reaper_mcp') { Bad "$name reaper path not under DAW-Horsemen" }
    if ($raw -match 'DAW-Horsemen.+renoise-mcp-bridge') { Ok "$name renoise -> Horsemen pack" }
    elseif ($raw -match 'renoise.mcp|renoise-mcp') { Bad "$name renoise path not under DAW-Horsemen" }
    if ($raw -match 'bitwig_mcp_server' -and $raw -notmatch '8080/sse') {
      Bad "$name still has stdio bitwig_mcp_server without SSE (will fight UDP 9001)"
    }
  }
}

# Claude Code/CLI: project enables .mcp.json servers
try {
  $claude = Join-Path $env:USERPROFILE '.claude.json'
  if (Test-Path -LiteralPath $claude) {
    $d = Get-Content -LiteralPath $claude -Raw | ConvertFrom-Json
    $proj = $d.projects.'E:/ChiptuneClaude'
    if (-not $proj) { $proj = $d.projects.'E:\ChiptuneClaude' }
    $en = @($proj.enabledMcpjsonServers)
    $need = @('bitwig','reaper','renoise')
    $missing = $need | Where-Object { $en -notcontains $_ }
    if ($missing.Count -eq 0) { Ok "Claude Code enabledMcpjsonServers: $($en -join ', ')" }
    else { Bad "Claude Code missing enabled servers: $($missing -join ', ')" }
  } else { Info 'no ~/.claude.json (Claude Code may be unused)' }
} catch { Bad "Claude config parse: $_" }

# --- DAW binaries ---
Write-Host ''
Write-Host '[DAW installs]'
$bitwig = 'C:\Program Files\Bitwig Studio\Bitwig Studio.exe'
$reaper = 'C:\Program Files\REAPER (x64)\reaper.exe'
$renoise = 'C:\Program Files\Renoise 3.5.4\Renoise.exe'
foreach ($pair in @(@('Bitwig',$bitwig),@('REAPER',$reaper),@('Renoise',$renoise))) {
  if (Test-Path -LiteralPath $pair[1]) { Ok "$($pair[0]) $($pair[1])" } else { Bad "$($pair[0]) missing at $($pair[1])" }
}

# --- live processes / ports ---
Write-Host ''
Write-Host '[live]'
$bw = Get-Process -Name 'Bitwig Studio' -ErrorAction SilentlyContinue
$rp = Get-Process -Name 'reaper' -ErrorAction SilentlyContinue
$rn = Get-Process -Name 'Renoise' -ErrorAction SilentlyContinue
if ($bw) { Ok "Bitwig running (PID $($bw.Id -join ','))" } else { Info 'Bitwig not running' }
if ($rp) { Ok "REAPER running (PID $($rp.Id -join ','))" } else { Info 'REAPER not running' }
if ($rn) { Ok "Renoise running (PID $($rn.Id -join ','))" } else { Info 'Renoise not running' }

$sse = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'serve_sse' }
$stdioBw = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'bitwig_mcp_server' -and $_.CommandLine -notmatch 'serve_sse' }
if ($sse) { Ok "shared Bitwig SSE process PID $($sse.ProcessId -join ',')" }
else { Info 'shared Bitwig SSE not running (start option 1)' }
if ($stdioBw) { Bad "stdio bitwig_mcp_server still running: PID $($stdioBw.ProcessId -join ',') - kill via stop_bitwig_servers.bat" }

try {
  $h = Invoke-RestMethod 'http://127.0.0.1:8080/healthz' -TimeoutSec 2
  if ($h.ok) { Ok 'SSE healthz http://127.0.0.1:8080/healthz' } else { Bad "healthz weird: $($h | ConvertTo-Json -Compress)" }
} catch { Info 'SSE healthz down (expected if shared server not started)' }

try {
  $r = Invoke-WebRequest 'http://127.0.0.1:19714/health' -UseBasicParsing -TimeoutSec 2
  if ($r.StatusCode -eq 200) { Ok 'Renoise ReMCP http://127.0.0.1:19714/health' }
} catch { Info 'Renoise ReMCP not answering (Tools -> Renoise MCP -> START + Play)' }

Write-Host ''
if ($fail -eq 0) {
  Write-Host 'RESULT: healthy (or idle-ready). Shared Bitwig works for Cursor + Claude + Claude CLI when SSE is up and all point at :8080/sse.' -ForegroundColor Green
  exit 0
} else {
  Write-Host "RESULT: $fail issue(s). Fix BADs above." -ForegroundColor Yellow
  exit 1
}
