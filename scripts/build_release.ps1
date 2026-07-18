# Build a clean release ZIP from the current git HEAD (no local junk).
# Output: dist\DAW-Horsemen-<VERSION>.zip
param(
  [string]$PackRoot = (Split-Path $PSScriptRoot -Parent),
  [string]$Tag = ''
)

$ErrorActionPreference = 'Stop'
Set-Location $PackRoot

$ver = (Get-Content (Join-Path $PackRoot 'VERSION') -Raw).Trim()
if (-not $Tag) { $Tag = "v$ver" }

$dist = Join-Path $PackRoot 'dist'
New-Item -ItemType Directory -Path $dist -Force | Out-Null

$zipName = "DAW-Horsemen-$ver.zip"
$zipPath = Join-Path $dist $zipName
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }

# git archive = committed tree only (respects .gitattributes export-ignore if any)
$prefix = "DAW-Horsemen-$ver/"
git archive --format=zip --prefix=$prefix -o $zipPath HEAD
if ($LASTEXITCODE -ne 0) { throw "git archive failed: $LASTEXITCODE" }

$bytes = (Get-Item $zipPath).Length
Write-Host "OK  $zipPath  ($([math]::Round($bytes/1MB, 1)) MB)"
Write-Host "TAG $Tag"
Write-Host "ZIP $zipPath"
