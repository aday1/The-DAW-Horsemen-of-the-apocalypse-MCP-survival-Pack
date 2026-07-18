# Build DAW-Horsemen-<ver>.msi from git HEAD (clean tree) via WiX 7.
# Requires: wix on PATH (winget install WiXToolset.WiXCLI), EULA accepted (wix eula accept wix7)
param(
  [string]$PackRoot = (Split-Path $PSScriptRoot -Parent),
  [string]$Tag = ''
)

$ErrorActionPreference = 'Stop'
Set-Location $PackRoot

$ver = (Get-Content (Join-Path $PackRoot 'VERSION') -Raw).Trim()
if (-not $Tag) { $Tag = "v$ver" }

# Windows Installer wants Major.Minor.Build.Revision
$parts = $ver.Split('.')
while ($parts.Count -lt 4) { $parts += '0' }
$msiVer = ($parts[0..3] -join '.')

$wix = Get-Command wix -ErrorAction SilentlyContinue
if (-not $wix) {
  throw "wix CLI not on PATH. Install: winget install --id WiXToolset.WiXCLI -e"
}

$dist = Join-Path $PackRoot 'dist'
New-Item -ItemType Directory -Path $dist -Force | Out-Null

$stageRoot = Join-Path $env:TEMP ("daw-horsemen-msi-stage-" + [guid]::NewGuid().ToString('N'))
$payload = Join-Path $stageRoot 'payload'
New-Item -ItemType Directory -Path $payload -Force | Out-Null

try {
  # Prefer committed tree (clean release). Fall back to working tree if
  # installer/VERSION are newer than HEAD (dev iterate before commit).
  $useWork = $true
  # After first commit of installer/, prefer git archive when VERSION matches HEAD
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  $headVer = (git show HEAD:VERSION 2>$null | Out-String).Trim()
  git cat-file -e "HEAD:installer/Product.wxs" 2>$null | Out-Null
  $hasInstaller = ($LASTEXITCODE -eq 0)
  $ErrorActionPreference = $prevEap
  if ($hasInstaller -and $headVer -and ($headVer -eq $ver)) { $useWork = $false }

  if ($useWork) {
    Write-Host "Staging WORKING TREE -> $payload  (VERSION/installer ahead of HEAD)"
    $exclude = @(
      '/XD', '.git', 'dist', '__pycache__', 'node_modules', '.cursor', '.venv', 'venv',
      '/XF', '*.pyc', '*.log', 'publish_log.txt', 'mcp.generated.json',
      'mcp.claude_desktop.snippet.json', 'DawpocalypseMCP.bwextension', 'JANITOR_vector.bat'
    )
    & robocopy $PackRoot $payload /E /NFL /NDL /NJH /NJS /nc /ns /np @exclude | Out-Null
    # robocopy exit 0-7 = success-ish
    if ($LASTEXITCODE -ge 8) { throw "robocopy stage failed: $LASTEXITCODE" }
  } else {
    Write-Host "Staging git HEAD -> $payload"
    $tar = Join-Path $stageRoot 'payload.tar'
    git archive --format=tar -o $tar HEAD
    if ($LASTEXITCODE -ne 0) { throw "git archive failed: $LASTEXITCODE" }
    & tar -xf $tar -C $payload
    if ($LASTEXITCODE -ne 0) { throw "tar extract failed: $LASTEXITCODE" }
  }

  if (-not (Test-Path (Join-Path $payload 'CARE.bat'))) {
    throw "Stage missing CARE.bat - archive/stage empty?"
  }

  $msiName = "DAW-Horsemen-$ver.msi"
  $msiPath = Join-Path $dist $msiName
  if (Test-Path $msiPath) { Remove-Item -Force $msiPath }

  $wxs = Join-Path $PackRoot 'installer\Product.wxs'

  Write-Host "wix build  ProductVersion=$msiVer"
  & wix build `
    -o $msiPath `
    -arch x64 `
    -define "ProductVersion=$msiVer" `
    -b "Payload=$payload" `
    $wxs
  if ($LASTEXITCODE -ne 0) { throw "wix build failed: $LASTEXITCODE" }

  $bytes = (Get-Item $msiPath).Length
  Write-Host "OK  $msiPath  ($([math]::Round($bytes/1MB, 1)) MB)"
  Write-Host "TAG $Tag"
  Write-Host "MSI $msiPath"
}
finally {
  if (Test-Path $stageRoot) {
    Remove-Item -Recurse -Force $stageRoot -ErrorAction SilentlyContinue
  }
}
