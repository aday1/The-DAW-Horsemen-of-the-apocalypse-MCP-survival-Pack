# Build release artifacts from git HEAD.
# Primary: dist\DAW-Horsemen-<VERSION>.msi
# Also:    dist\DAW-Horsemen-<VERSION>.zip  (optional mirror / non-Windows)
param(
  [string]$PackRoot = (Split-Path $PSScriptRoot -Parent),
  [string]$Tag = '',
  [switch]$ZipAlso
)

$ErrorActionPreference = 'Stop'
Set-Location $PackRoot

$ver = (Get-Content (Join-Path $PackRoot 'VERSION') -Raw).Trim()
if (-not $Tag) { $Tag = "v$ver" }

$dist = Join-Path $PackRoot 'dist'
New-Item -ItemType Directory -Path $dist -Force | Out-Null

# MSI is the ship artifact
& (Join-Path $PSScriptRoot 'build_msi.ps1') -PackRoot $PackRoot -Tag $Tag
if ($LASTEXITCODE -ne 0) { throw "build_msi failed: $LASTEXITCODE" }

if ($ZipAlso) {
  $zipName = "DAW-Horsemen-$ver.zip"
  $zipPath = Join-Path $dist $zipName
  if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
  $prefix = "DAW-Horsemen-$ver/"
  git archive --format=zip --prefix=$prefix -o $zipPath HEAD
  if ($LASTEXITCODE -ne 0) { throw "git archive zip failed: $LASTEXITCODE" }
  Write-Host "ZIP $zipPath"
}

Write-Host "TAG $Tag"
Write-Host "Primary artifact: MSI in $dist"
