# Extract Horsemen MCP pack pieces to typical Windows install locations.
# Run from repo root: powershell -ExecutionPolicy Bypass -File .\scripts\extract_to_machine.ps1
param(
    [switch]$BitwigOnly,
    [switch]$ReaperScriptsOnly,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BitwigDest = Join-Path $env:USERPROFILE "Documents\Bitwig Studio\Extensions\bitwig-mcp-server"
$ReaperScripts = Join-Path $env:APPDATA "REAPER\Scripts"

function Copy-Tree($Src, $Dst) {
    if (-not (Test-Path $Src)) { Write-Warning "Missing: $Src"; return }
    if ($WhatIf) { Write-Host "WHATIF: robocopy $Src -> $Dst"; return }
    New-Item -ItemType Directory -Path $Dst -Force | Out-Null
    # /E copy subdirs; no /MIR so we do not delete extra files already in your Extensions folder
    robocopy $Src $Dst /E /XD .git __pycache__ .venv venv node_modules .pytest_cache .eggs .tox target /NFL /NDL /NJH /NJS /nc /ns /np
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed: $LASTEXITCODE" }
}

if (-not $ReaperScriptsOnly) {
    Write-Host "Bitwig MCP -> $BitwigDest"
    Copy-Tree (Join-Path $Root "packages\bitwig-mcp-server") $BitwigDest
}

if (-not $BitwigOnly) {
    $lua = Join-Path $Root "packages\reaper-mcp\reaper_mcp_bridge.lua"
    if (Test-Path $lua) {
        if ($WhatIf) { Write-Host "WHATIF: copy reaper_mcp_bridge.lua -> $ReaperScripts" }
        else {
            New-Item -ItemType Directory -Path $ReaperScripts -Force | Out-Null
            Copy-Item -Force $lua (Join-Path $ReaperScripts "reaper_mcp_bridge.lua")
            Write-Host "Copied reaper_mcp_bridge.lua -> $ReaperScripts"
        }
    }
}

Write-Host "Done. Renoise bridge stays in the repo; point Cursor at packages\renoise-mcp-bridge\bridge.js"
Write-Host "Read SETUP.txt for Cursor MCP env and next steps."
