# Create/update "DAW MCP Launchers" desktop shortcut -> launch_daw_mcp.bat
param(
  [string]$PackRoot = (Split-Path $PSScriptRoot -Parent)
)

$launcher = Join-Path $PackRoot 'launch_daw_mcp.bat'
if (-not (Test-Path -LiteralPath $launcher)) {
  Write-Error "Missing launcher: $launcher"
  exit 1
}

function Get-DesktopPath {
  $candidates = @(
    [Environment]::GetFolderPath('Desktop'),
    (Join-Path $env:USERPROFILE 'Desktop'),
    (Join-Path $env:USERPROFILE 'OneDrive\Desktop'),
    (Join-Path $env:USERPROFILE 'OneDrive - Personal\Desktop')
  )
  foreach ($c in $candidates) {
    if ($c -and (Test-Path -LiteralPath $c)) { return $c }
  }
  return [Environment]::GetFolderPath('Desktop')
}

$desktop = Get-DesktopPath
$lnkPath = Join-Path $desktop 'DAW MCP Launchers.lnk'
$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($lnkPath)
$sc.TargetPath = $launcher
$sc.WorkingDirectory = $PackRoot
$sc.WindowStyle = 1
$sc.Description = 'DAW Horsemen - start DAWs + MCP servers (Bitwig shared SSE, REAPER, Renoise)'
$sc.IconLocation = 'C:\Windows\System32\shell32.dll,165'
$sc.Save()

Write-Host "Desktop shortcut OK: $lnkPath"
Write-Host "Target: $launcher"
exit 0
