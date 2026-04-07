# Maintainer: refresh packages/* from typical local paths (edit variables if yours differ).
# Run from repo root.

$ErrorActionPreference = "Stop"
$DestRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Sources = @{
    "reaper-mcp"            = "c:\aday.slop\ReaperMCP\twelvetake-reaper-mcp"
    "renoise-mcp-bridge"    = "C:\aday.slop\RenoiseMCP"
    "bitwig-mcp-server"     = "C:\Users\aday\Documents\Bitwig Studio\Extensions\bitwig-mcp-server"
}

$ExcludeDirs = @(
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    "temp_drivenbymoss", "temp_", ".cursor", ".pytest_cache",
    ".eggs", ".tox", "target"
)

foreach ($pair in $Sources.GetEnumerator()) {
    $name = $pair.Key
    $src = $pair.Value
    $dst = Join-Path $DestRoot "packages\$name"
    if (-not (Test-Path $src)) { Write-Warning "Skip (missing): $src"; continue }
    Write-Host "Updating $name"
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
    $rcArgs = @($src, $dst, "/E")
    foreach ($d in $ExcludeDirs) { $rcArgs += "/XD"; $rcArgs += $d }
    $rcArgs += @("/NFL", "/NDL", "/NJH", "/NJS", "/nc", "/ns", "/np")
    & robocopy @rcArgs
}

Write-Host "Done. Review git diff, then commit."
